import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installer', ROOT / 'setup/install_tools.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class Installation(unittest.TestCase):
    def test_manifest_has_both_architectures_and_hashes(self):
        manifest = json.loads((ROOT / 'setup/tools.json').read_text())
        for tool, entry in manifest.items():
            if 'assets' not in entry:
                continue
            if 'file' not in entry:
                self.assertEqual(set(entry['assets']), {'x86_64', 'aarch64'})
            for asset in entry['assets'].values():
                self.assertRegex(asset['sha256'], r'^[0-9a-f]{64}$')
                self.assertTrue(asset['url'].startswith('https://'))

    def test_bad_hash_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'archive'
            dest.write_bytes(b'corrupt')
            with patch.object(installer.subprocess, 'run'):
                with self.assertRaisesRegex(ValueError, 'Checksum mismatch'):
                    installer.download({'url': 'https://invalid', 'sha256': '0'*64}, dest)

    def test_http_failure_propagates(self):
        with patch.object(installer.subprocess, 'run', side_effect=subprocess.CalledProcessError(22, 'curl')):
            with self.assertRaises(subprocess.CalledProcessError):
                installer.download({'url': 'https://invalid'}, Path('/unused'))

    def test_existing_executable_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / '.local/bin/demo'
            target.parent.mkdir(parents=True)
            target.write_text('#!/bin/sh\necho existing\n')
            target.chmod(0o755)
            with patch.object(installer.shutil, 'which', return_value=None), patch.object(installer, 'download') as download:
                installer.install('demo', {'version': '1'}, 'x86_64', Path(tmp))
                download.assert_not_called()
            self.assertIn('existing', target.read_text())

    def test_archive_failure_cleans_staging(self):
        with tempfile.TemporaryDirectory() as tmp:
            def fake_download(asset, path):
                path.write_bytes(b'not a tar archive')
            with patch.object(installer.shutil, 'which', return_value=None), patch.object(installer, 'download', side_effect=fake_download):
                with self.assertRaises(tarfile.ReadError):
                    installer.install('demo', {'assets': {'x86_64': {}}, 'version': '1'}, 'x86_64', Path(tmp))
            self.assertEqual(list((Path(tmp)/'.local/bin').iterdir()), [])

    def test_links_preserve_backups_and_restore_on_failure(self):
        setup = (ROOT / 'setup.sh').read_text()
        function = setup[setup.index('link_file() {'):setup.index('# Install individual shell files')]
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(['bash', '-eu', '-c', '''
                success() { :; }; warn() { :; }
                ''' + function + '''
                src="$1/source"; dst="$1/dest"
                echo source > "$src"
                echo first > "$dst"
                link_file "$src" "$dst"
                link_file "$src" "$dst"
                rm "$dst"
                ln -s missing "$dst"
                link_file "$src" "$dst"
                rm "$dst"; echo restore > "$dst"
                ln() { return 1; }
                if link_file "$src" "$dst"; then exit 1; fi
                test "$(cat "$dst")" = restore
                ''', 'test', tmp], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            backups = list(Path(tmp).glob('dest.bak.*/original'))
            self.assertEqual(len(backups), 2)
            self.assertTrue(any(p.is_symlink() for p in backups))



if __name__ == '__main__':
    unittest.main()
