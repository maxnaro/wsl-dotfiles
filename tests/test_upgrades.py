"""Offline fixtures for transactional upgrades; never install into the real home."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'setup'))
import upgrades
import install_tools


def archive(tool, version='2.0', runtime=False):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w:gz') as package:
        script = ('#!/bin/sh\ncase "$1" in completion|gen-completions) echo "# generated completion";; '
                  f'*) echo "{tool} {version}";; esac\n').encode()
        info = tarfile.TarInfo(f'{tool}/bin/{tool}' if runtime else tool)
        info.size = len(script)
        info.mode = 0o755
        package.addfile(info, io.BytesIO(script))
        if runtime:
            info = tarfile.TarInfo(f'{tool}/share/nvim/runtime/fixture.vim')
            info.size = 1
            package.addfile(info, io.BytesIO(b'x'))
    return stream.getvalue()


class Upgrades(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.payloads = {}
        self.manifest = {}
        self.which = patch.object(upgrades.shutil, 'which', return_value=None)
        self.which.start()
        self.addCleanup(self.which.stop)

    def add_tool(self, tool='demo', version='2.0', runtime=False):
        payload = archive(tool, version, runtime)
        self.payloads[tool] = payload
        self.manifest[tool] = {'version': version, 'assets': {'x86_64': {
            'url': tool, 'sha256': hashlib.sha256(payload).hexdigest()}}}

    def download(self, asset, target):
        target.write_bytes(self.payloads[asset['url']])
        if hashlib.sha256(target.read_bytes()).hexdigest() != asset['sha256']:
            raise ValueError('Checksum mismatch')

    def old(self, tool='demo', version='1.0'):
        target = self.home / '.local/bin' / tool
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f'#!/bin/sh\necho "{tool} {version}"\n')
        target.chmod(0o755)
        return target

    def upgrade(self, *names, dry_run=False):
        return upgrades.upgrade(list(names or ['demo']), self.manifest, 'x86_64', self.home,
                                self.download, dry_run)

    def test_repeat_and_newer_skip_without_download(self):
        self.add_tool()
        self.old(version='2.0')
        with patch.object(self, 'download', side_effect=AssertionError('download')):
            self.assertIsNone(self.upgrade())
            self.old(version='3.0')
            self.assertIsNone(self.upgrade())
        self.assertEqual(list((self.home / '.local/state/dotfiles/upgrades').glob('*/journal.json')), [])

    def test_dry_run_changes_nothing(self):
        self.add_tool()
        self.upgrade(dry_run=True)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_absent_target_upgrade_and_rollback(self):
        self.add_tool()
        transaction = self.upgrade()
        target = self.home / '.local/bin/demo'
        self.assertEqual(upgrades.version(target, 'demo'), '2.0')
        upgrades.rollback(transaction, self.home)
        self.assertFalse(target.exists())
        upgrades.rollback(transaction, self.home)

    def test_existing_file_and_relative_symlink_restore(self):
        self.add_tool()
        target = self.old()
        real = target.with_name('previous')
        target.rename(real)
        target.symlink_to('previous')
        transaction = self.upgrade()
        upgrades.rollback(transaction, self.home)
        self.assertTrue(target.is_symlink())
        self.assertEqual(os.readlink(target), 'previous')
        self.assertEqual(upgrades.version(target, 'demo'), '1.0')

    def test_changed_destination_blocks_all_rollback(self):
        self.add_tool()
        self.add_tool('other')
        self.old()
        self.old('other')
        transaction = self.upgrade('demo', 'other')
        other = self.home / '.local/bin/other'
        other.write_text('edited')
        with self.assertRaisesRegex(RuntimeError, 'modified destination'):
            upgrades.rollback(transaction, self.home)
        self.assertEqual(upgrades.version(self.home / '.local/bin/demo', 'demo'), '2.0')
        self.assertEqual(other.read_text(), 'edited')

    def test_hash_and_archive_failures_leave_old_targets(self):
        self.add_tool()
        target = self.old()
        for payload in (b'bad hash', b'not an archive'):
            self.payloads['demo'] = payload
            if payload == b'not an archive':
                self.manifest['demo']['assets']['x86_64']['sha256'] = hashlib.sha256(payload).hexdigest()
            with self.assertRaises((ValueError, tarfile.ReadError)):
                self.upgrade()
            self.assertEqual(upgrades.version(target, 'demo'), '1.0')

    def test_wrong_candidate_version_does_not_activate_any_tool(self):
        self.add_tool()
        self.add_tool('other', '3.0')
        self.manifest['other']['version'] = '2.0'
        target = self.old()
        with self.assertRaisesRegex(ValueError, 'candidate reports'):
            self.upgrade('demo', 'other')
        self.assertEqual(upgrades.version(target, 'demo'), '1.0')
        self.assertFalse((self.home / '.local/bin/other').exists())

    def test_failed_activation_restores_entire_transaction(self):
        self.add_tool()
        self.add_tool('other')
        target = self.old()
        replace = upgrades.replace
        calls = []
        def fail_second(source, destination):
            calls.append(destination)
            if len(calls) == 2:
                raise OSError('activation failed')
            return replace(source, destination)
        with patch.object(upgrades, 'replace', side_effect=fail_second):
            with self.assertRaisesRegex(OSError, 'activation failed'):
                self.upgrade('demo', 'other')
        self.assertEqual(upgrades.version(target, 'demo'), '1.0')
        self.assertFalse((self.home / '.local/bin/other').exists())

    def test_interrupted_activation_recovers_before_version_selection(self):
        self.add_tool()
        target = self.old()
        transaction = self.upgrade()
        root = self.home / '.local/state/dotfiles/upgrades'
        directory = root / transaction
        journal = json.loads((directory / 'journal.json').read_text())
        journal['status'] = 'activating'
        upgrades.save_journal(directory, journal)
        # Recovery restores old version before planning, so a fresh upgrade occurs.
        next_transaction = self.upgrade()
        self.assertNotEqual(next_transaction, transaction)
        self.assertEqual(json.loads((directory / 'journal.json').read_text())['status'], 'rolled_back')
        self.assertEqual(upgrades.version(target, 'demo'), '2.0')

    def test_fzf_groups_both_shell_files(self):
        self.add_tool('fzf')
        for tool, filename in [('fzf-completion', 'completion.bash'), ('fzf-key-bindings', 'key-bindings.bash')]:
            self.payloads[tool] = b'# shell fixture\n'
            self.manifest[tool] = {'version': '2.0', 'file': filename, 'assets': {'all': {
                'url': tool, 'sha256': hashlib.sha256(self.payloads[tool]).hexdigest()}}}
        transaction = self.upgrade('fzf')
        for filename in ('completion.bash', 'key-bindings.bash'):
            self.assertTrue((self.home / '.local/share/fzf' / filename).is_file())
        upgrades.rollback(transaction, self.home)
        self.assertFalse((self.home / '.local/share/fzf/completion.bash').exists())

    def test_sesh_completions_roll_back_with_binary(self):
        self.add_tool('sesh')
        transaction = self.upgrade('sesh')
        completion = self.home / '.local/share/fish/vendor_completions.d/sesh.fish'
        self.assertIn('generated', completion.read_text())
        upgrades.rollback(transaction, self.home)
        self.assertFalse(completion.exists())

    def test_neovim_runtime_survives_staging_and_rollback(self):
        self.add_tool('nvim', runtime=True)
        transaction = self.upgrade('nvim')
        target = self.home / '.local/bin/nvim'
        self.assertTrue(target.is_symlink())
        runtime = target.resolve().parent.parent
        self.assertTrue((runtime / 'share/nvim/runtime/fixture.vim').is_file())
        upgrades.rollback(transaction, self.home)
        self.assertFalse(target.exists())
        self.assertTrue(runtime.exists())

    def test_tmux_missing_prerequisites_fail_before_download(self):
        self.manifest['tmux'] = {'version': '3.8', 'source': {'url': 'tmux', 'sha256': '0' * 64}}
        with patch.object(self, 'download') as download:
            with self.assertRaisesRegex(RuntimeError, 'tmux build needs cc'):
                self.upgrade('tmux')
            download.assert_not_called()

    def test_tmux_build_failure_keeps_target(self):
        self.old('tmux', '3.7')
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w:gz') as package:
            info = tarfile.TarInfo('tmux-3.8/configure')
            info.size = 0
            info.mode = 0o755
            package.addfile(info, io.BytesIO())
        self.payloads['tmux'] = stream.getvalue()
        self.manifest['tmux'] = {'version': '3.8', 'source': {'url': 'tmux', 'sha256': hashlib.sha256(stream.getvalue()).hexdigest()}}
        original_run = subprocess.run
        def run(command, **kwargs):
            if command[0] == './configure':
                raise subprocess.CalledProcessError(1, command)
            return original_run(command, **kwargs)
        with patch.object(upgrades, 'preflight_tmux'), patch.object(upgrades.subprocess, 'run', side_effect=run):
            with self.assertRaises(subprocess.CalledProcessError):
                self.upgrade('tmux')
        self.assertEqual(upgrades.version(self.home / '.local/bin/tmux', 'tmux'), '3.7')

    def test_tmux_build_publishes_versioned_prefix(self):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w:gz') as package:
            info = tarfile.TarInfo('tmux-3.8/configure')
            info.mode = 0o755
            package.addfile(info, io.BytesIO())
        self.payloads['tmux'] = stream.getvalue()
        self.manifest['tmux'] = {'version': '3.8', 'source': {
            'url': 'tmux', 'sha256': hashlib.sha256(stream.getvalue()).hexdigest()}}
        original_run = subprocess.run
        commands = []
        prefix = None
        def build(command, **kwargs):
            nonlocal prefix
            commands.append(command)
            if command[0] == './configure':
                prefix = Path(command[1].split('=', 1)[1])
            elif command[:2] == ['make', 'install']:
                destdir = Path(command[2].split('=', 1)[1])
                binary = destdir / prefix.relative_to('/') / 'bin/tmux'
                binary.parent.mkdir(parents=True)
                binary.write_text('#!/bin/sh\necho "tmux 3.8"\n')
                binary.chmod(0o755)
            elif command[0] != 'make':
                return original_run(command, **kwargs)
            return subprocess.CompletedProcess(command, 0)
        with patch.object(upgrades, 'preflight_tmux'), patch.object(upgrades.subprocess, 'run', side_effect=build):
            transaction = self.upgrade('tmux')
        target = self.home / '.local/bin/tmux'
        self.assertTrue(target.is_symlink())
        self.assertEqual(target.resolve().parent.parent, prefix)
        self.assertEqual(upgrades.version(target, 'tmux'), '3.8')
        self.assertFalse(any('sudo' in command for command in commands))
        upgrades.rollback(transaction, self.home)
        self.assertFalse(target.exists())

    def test_tmux_library_preflight_precedes_download(self):
        self.manifest['tmux'] = {'version': '3.8', 'source': {'url': 'tmux', 'sha256': '0' * 64}}
        def which(command):
            return '/usr/bin/' + command if command != 'tmux' else None
        with patch.object(upgrades.shutil, 'which', side_effect=which), patch.object(
                upgrades.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)), patch.object(self, 'download') as download:
            with self.assertRaisesRegex(RuntimeError, 'libevent development files'):
                self.upgrade('tmux')
            download.assert_not_called()

    def test_lock_prevents_second_upgrade(self):
        self.add_tool()
        with upgrades.locked(self.home):
            with self.assertRaisesRegex(RuntimeError, 'Another dotfiles upgrade'):
                self.upgrade()

    def test_archive_traversal_is_rejected(self):
        self.add_tool()
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w:gz') as package:
            info = tarfile.TarInfo('../../escape')
            info.size = 1
            package.addfile(info, io.BytesIO(b'x'))
        self.payloads['demo'] = stream.getvalue()
        self.manifest['demo']['assets']['x86_64']['sha256'] = hashlib.sha256(stream.getvalue()).hexdigest()
        with self.assertRaises(tarfile.OutsideDestinationError):
            self.upgrade()
        self.assertFalse((self.home / '.local/bin/demo').exists())

    def test_newer_nightly_is_kept_and_unknown_suffix_fails_closed(self):
        self.add_tool(version='0.12.6')
        target = self.old(version='0.13.0-dev')
        with patch.object(self, 'download', side_effect=AssertionError('download')):
            self.assertIsNone(self.upgrade())
            self.old(version='0.13.0~dev')
            with self.assertRaisesRegex(ValueError, 'Cannot safely compare'):
                self.upgrade()
        self.assertEqual(upgrades.version(target, 'demo'), '0.13.0~dev')
        self.assertTrue(upgrades.newer('1.0.0', '1.0.0-rc.1'))
        self.assertTrue(upgrades.newer('1.0.0-rc.10', '1.0.0-rc.2'))
        self.assertFalse(upgrades.newer('1.0.0-dev', '1.0.0'))

    def test_candidate_version_suffix_cannot_match_partial_pin(self):
        self.add_tool(version='2.0~custom')
        self.manifest['demo']['version'] = '2.0'
        with self.assertRaisesRegex(ValueError, 'candidate reports 2.0~custom'):
            self.upgrade()
        self.assertFalse((self.home / '.local/bin/demo').exists())

    def test_bootstrap_preserves_fzf_shell_files_when_binary_pin_differs(self):
        self.old('fzf', '1.0').write_text('#!/bin/sh\necho "1.0 (fixture)"\n')
        for tool, filename in [('fzf-completion', 'completion.bash'), ('fzf-key-bindings', 'key-bindings.bash')]:
            target = self.home / '.local/share/fzf' / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('# matching old fzf')
            spec = {'version': '2.0', 'file': filename, 'assets': {'all': {}}}
            with patch.object(install_tools, 'download', side_effect=AssertionError('download')):
                install_tools.install(tool, spec, 'x86_64', self.home)
            self.assertEqual(target.read_text(), '# matching old fzf')

    def test_bootstrap_refreshes_shell_file_when_fzf_pin_matches(self):
        self.old('fzf', '2.0').write_text('#!/bin/sh\necho "2.0 (fixture)"\n')
        payload = b'# shell fixture'
        spec = {'version': '2.0', 'file': 'completion.bash', 'assets': {'all': {}}}
        with patch.object(install_tools, 'download', side_effect=lambda asset, path: path.write_bytes(payload)):
            install_tools.install('fzf-completion', spec, 'x86_64', self.home)
        self.assertEqual((self.home / '.local/share/fzf/completion.bash').read_bytes(), payload)

    def test_tmux_dry_run_checks_dependencies_without_writes(self):
        self.manifest['tmux'] = {'version': '3.8', 'source': {'url': 'tmux', 'sha256': '0' * 64}}
        with patch.object(self, 'download', side_effect=AssertionError('download')):
            with self.assertRaisesRegex(RuntimeError, 'tmux build needs cc'):
                self.upgrade('tmux', dry_run=True)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_completion_journal_failure_restores_activated_targets(self):
        self.add_tool()
        self.add_tool('other')
        target = self.old()
        save = upgrades.save_journal
        def fail_completed(directory, journal):
            if journal['status'] == 'complete':
                raise OSError('journal fsync failed')
            save(directory, journal)
        with patch.object(upgrades, 'save_journal', side_effect=fail_completed):
            with self.assertRaisesRegex(OSError, 'journal fsync failed'):
                self.upgrade('demo', 'other')
        self.assertEqual(upgrades.version(target, 'demo'), '1.0')
        self.assertFalse((self.home / '.local/bin/other').exists())
        journals = list((self.home / '.local/state/dotfiles/upgrades').glob('*/journal.json'))
        self.assertEqual(json.loads(journals[0].read_text())['status'], 'rolled_back')

    def test_version_output_quotes_and_formatting_are_delimiters(self):
        outputs = [
            "commit='unknown', buildDate='unknown', version='0.57.0+ds1-1', os='linux', arch='amd64', git version='2.47.3'",
            'version="0.57.0+ds1-1"; os=linux',
            '\x1b[32mlazygit 0.57.0+ds1-1\x1b[0m',
            '[0.57.0+ds1-1]',
        ]
        for output in outputs:
            with self.subTest(output=output), patch.object(upgrades.subprocess, 'run', return_value=
                    subprocess.CompletedProcess([], 0, stdout=output, stderr='')):
                actual = upgrades.version('/usr/bin/lazygit', 'lazygit')
                self.assertEqual(actual, '0.57.0+ds1-1')
                self.assertFalse(upgrades.newer(actual, '0.58.0'))

    def test_archive_completion_basename_is_not_an_executable_candidate(self):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w:gz') as package:
            for name, mode, payload in [
                    ('usr/bin/fastfetch', 0o755, b'#!/bin/sh\necho "fastfetch 2.0"\n'),
                    ('usr/share/bash-completion/completions/fastfetch', 0o644, b'#!/usr/bin/env bash\n# bash completion fixture\n')]:
                info = tarfile.TarInfo(name)
                info.mode = mode
                info.size = len(payload)
                package.addfile(info, io.BytesIO(payload))
        self.payloads['fastfetch'] = stream.getvalue()
        self.manifest['fastfetch'] = {'version': '2.0', 'assets': {'x86_64': {
            'url': 'fastfetch', 'sha256': hashlib.sha256(stream.getvalue()).hexdigest()}}}
        transaction = self.upgrade('fastfetch')
        target = self.home / '.local/bin/fastfetch'
        self.assertEqual(upgrades.version(target, 'fastfetch'), '2.0')
        upgrades.rollback(transaction, self.home)
        with patch.object(install_tools, 'download', side_effect=self.download):
            install_tools.install('fastfetch', self.manifest['fastfetch'], 'x86_64', self.home)
        self.assertEqual(upgrades.version(target, 'fastfetch'), '2.0')

    def test_unknown_tool_rejected_without_home_mutation(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported upgrade'):
            self.upgrade('pokemon')
        self.assertEqual(list(self.home.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
