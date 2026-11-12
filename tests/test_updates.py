"""Release updater tests use fixtures only; no GitHub requests or live upgrades."""
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('updater', ROOT / 'setup/update_tools.py')
updater = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(updater)


class FixtureClient:
    def __init__(self, tool='fzf', tag='v1.2.4'):
        self.tool, self.tag = tool, tag
        self.data, self.calls = {}, []
        self.release = {'tag_name': tag, 'draft': False, 'prerelease': False, 'assets': []}
        for arch, name in updater.asset_names(tool, tag).items():
            url = updater.release_url(tool, tag, name)
            content = (arch + tag).encode()
            self.data[url] = content
            self.release['assets'].append({'name': name, 'browser_download_url': url,
                                           'digest': 'sha256:' + hashlib.sha256(content).hexdigest()})
        self.data[self.tag_url] = self.release
        self.data[self.list_url] = [self.release]
        if tool == 'fzf':
            for filename in updater.FZF_FILES.values():
                self.data[updater.script_url(tag, filename)] = (filename + tag).encode()

    @property
    def tag_url(self):
        return f'https://api.github.com/repos/{updater.UPSTREAM[self.tool][0]}/releases/tags/{self.tag}'

    @property
    def list_url(self):
        return f'https://api.github.com/repos/{updater.UPSTREAM[self.tool][0]}/releases?per_page=100&page=1'

    def json(self, url):
        self.calls.append(url)
        return copy.deepcopy(self.data[url])

    def read(self, url):
        self.calls.append(url)
        return self.data[url]


def fixture_manifest(tool='fzf', tag='v1.2.3'):
    assets = {arch: {'url': updater.release_url(tool, tag, name), 'sha256': 'a' * 64}
              for arch, name in updater.asset_names(tool, tag).items()}
    manifest = {tool: {'version': tag, 'assets': assets}, 'pokemon': {'commit': 'untouched'}}
    if tool == 'tmux':
        manifest[tool] = {'version': tag, 'source': assets['x86_64']}
    if tool == 'fzf':
        for companion, filename in updater.FZF_FILES.items():
            manifest[companion] = {'version': tag, 'file': filename, 'assets': {'all': {
                'url': updater.script_url(tag, filename), 'sha256': 'b' * 64}}}
    return manifest


class Versions(unittest.TestCase):
    def test_strict_versions_and_classification(self):
        self.assertEqual(updater.parse_version('v1.2.3'), (1, 2, 3))
        for invalid in ('1.2', 'v01.2.3', '1.2.3-rc1', '1.2.3+build', '1.2.3\n', 'release-1.2.3', 'v3.8a'):
            self.assertIsNone(updater.parse_version(invalid))
        for old, new, expected in [('1.2.3', 'v1.2.4', 'patch'), ('v0.1.2', 'v0.2.0', 'minor'),
                                   ('1.2.3', '2.0.0', 'major'), ('1.2.3', '1.2.3', 'none'),
                                   ('1.2.3', 'v1.2.3', 'none'), ('2.0.0', '1.9.9', 'downgrade'),
                                   ('3.7a', '3.8', 'manual')]:
            with self.subTest(new=new):
                self.assertEqual(updater.classify_update(old, new), expected)

    def test_stable_highest_is_numeric_and_order_independent(self):
        client = FixtureClient('lazygit', 'v1.10.0')
        low = dict(client.release, tag_name='v1.9.9')
        prerelease = dict(client.release, tag_name='v9.0.0', prerelease=True)
        draft = dict(client.release, tag_name='v8.0.0', draft=True)
        alias = dict(client.release, tag_name='7.0.0')
        odd = dict(client.release, tag_name='v5.0.0-beta')
        client.data[client.list_url] = [low, prerelease, alias, client.release, draft, odd]
        result = updater.check_updates(fixture_manifest('lazygit'), client=client)
        row = result['updates'][0]
        self.assertEqual((row['latest'], row['classification'], row['available']), ('v1.10.0', 'minor', True))
        self.assertFalse(any('/download/' in url for url in client.calls))

    def test_bounded_pagination(self):
        client = FixtureClient('lazygit')
        batch = [dict(client.release, draft=True)] * updater.PAGE_SIZE
        for page in range(1, updater.MAX_PAGES + 1):
            client.data[client.list_url.rsplit('=', 1)[0] + f'={page}'] = batch
        self.assertEqual(updater.releases('lazygit', client), [])
        self.assertEqual(len(client.calls), updater.MAX_PAGES)

    def test_no_update_never_downgrades(self):
        client = FixtureClient('lazygit', 'v1.2.2')
        row = updater.check_updates(fixture_manifest('lazygit'), client=client)['updates'][0]
        self.assertEqual((row['latest'], row['classification']), ('v1.2.3', 'none'))

    def test_companions_and_pokemon_are_not_binary_candidates(self):
        client = FixtureClient()
        self.assertEqual(len(updater.check_updates(fixture_manifest(), client=client)['updates']), 1)
        for tool in ('pokemon', 'fzf-completion'):
            with self.assertRaises(ValueError):
                updater.check_updates(fixture_manifest(), tools=[tool], client=client)


class Updates(unittest.TestCase):
    def test_verified_group_update(self):
        manifest, client = fixture_manifest(), FixtureClient()
        updated = updater.prepare_update(manifest, 'fzf', 'v1.2.4', client)
        self.assertEqual(manifest['fzf']['version'], 'v1.2.3')
        self.assertEqual(updater.verify_manifest_change(manifest, updated, 'fzf'), 'patch')
        for key in ('fzf', *updater.FZF_FILES):
            self.assertEqual(updated[key]['version'], 'v1.2.4')
        self.assertEqual(updated['pokemon'], manifest['pokemon'])
        for arch in updater.ARCHES:
            self.assertIn(updated['fzf']['assets'][arch]['url'], client.calls)
        for companion, filename in updater.FZF_FILES.items():
            content = client.data[updater.script_url('v1.2.4', filename)]
            self.assertEqual(updated[companion]['assets']['all']['sha256'], hashlib.sha256(content).hexdigest())

    def test_missing_architecture_and_digest_never_write(self):
        for failure in ('architecture', 'digest', 'mismatch', 'prerelease', 'url'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'tools.json'
                original = json.dumps(fixture_manifest()).encode()
                path.write_bytes(original)
                client = FixtureClient()
                if failure == 'architecture':
                    client.release['assets'].pop()
                elif failure == 'digest':
                    client.release['assets'][1]['digest'] = None
                elif failure == 'mismatch':
                    client.data[client.release['assets'][1]['browser_download_url']] = b'corrupt'
                elif failure == 'prerelease':
                    client.release['prerelease'] = True
                else:
                    client.release['assets'][1]['browser_download_url'] += '?spoof=1'
                with self.assertRaises(ValueError):
                    updater.apply_update(path, 'fzf', 'v1.2.4', client)
                self.assertEqual(path.read_bytes(), original)
                self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_missing_asset_reported_unavailable(self):
        client = FixtureClient()
        client.release['assets'].pop()
        row = updater.check_updates(fixture_manifest(), client=client)['updates'][0]
        self.assertEqual(row['latest'], 'v1.2.4')
        self.assertFalse(row['available'])

    def test_official_checksum_fallback(self):
        client = FixtureClient('lazygit')
        lines = []
        for asset in client.release['assets']:
            lines.append(asset.pop('digest')[7:] + '  ' + asset['name'])
        url = updater.release_url('lazygit', client.tag, 'checksums.txt')
        client.data[url] = ('\n'.join(lines) + '\n').encode()
        client.release['assets'].append({'name': 'checksums.txt', 'browser_download_url': url})
        updater.prepare_update(fixture_manifest('lazygit'), 'lazygit', client.tag, client)
        self.assertIn(url, client.calls)

    def test_checksum_fallback_cannot_name_other_asset(self):
        client = FixtureClient('lazygit')
        client.release['assets'][0]['digest'] = None
        url = updater.release_url('lazygit', client.tag, 'checksums.txt')
        client.data[url] = ('a' * 64 + '  other.tar.gz\n').encode()
        client.release['assets'].append({'name': 'checksums.txt', 'browser_download_url': url})
        with self.assertRaisesRegex(ValueError, 'No official SHA-256'):
            updater.prepare_update(fixture_manifest('lazygit'), 'lazygit', client.tag, client)

    def test_downgrade_alias_and_same_tag_rejected_before_network(self):
        client = FixtureClient()
        for tag in ('v1.2.2', '1.2.4', 'v1.2.3', 'v1.2.4-rc1', 'v01.2.4'):
            with self.assertRaises(ValueError):
                updater.prepare_update(fixture_manifest(), 'fzf', tag, client)
        self.assertEqual(client.calls, [])

    def test_atomic_failure_cleans_temp_and_preserves_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'tools.json'
            original = json.dumps(fixture_manifest()).encode()
            path.write_bytes(original)
            with patch.object(updater.os, 'replace', side_effect=OSError('fixture failure')):
                with self.assertRaises(OSError):
                    updater.apply_update(path, 'fzf', 'v1.2.4', FixtureClient())
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_atomic_success_preserves_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'tools.json'
            path.write_text(json.dumps(fixture_manifest()))
            path.chmod(0o640)
            updater.apply_update(path, 'fzf', 'v1.2.4', FixtureClient())
            self.assertEqual(json.loads(path.read_text())['fzf']['version'], 'v1.2.4')
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)

    def test_tmux_is_manual_and_source_only(self):
        client = FixtureClient('tmux', '3.8')
        # Both architectures share a single upstream source archive.
        client.release['assets'] = client.release['assets'][:1]
        url = client.release['assets'][0]['browser_download_url']
        client.release['assets'][0]['digest'] = 'sha256:' + hashlib.sha256(client.data[url]).hexdigest()
        updated = updater.prepare_update(fixture_manifest('tmux', '3.7a'), 'tmux', '3.8', client)
        self.assertEqual(updater.verify_manifest_change(fixture_manifest('tmux', '3.7a'), updated, 'tmux'), 'manual')
        self.assertIn('source', updated['tmux'])
        self.assertNotIn('assets', updated['tmux'])


class ManifestSecurity(unittest.TestCase):
    def test_spoofed_changes_rejected(self):
        base = fixture_manifest()
        good = updater.prepare_update(base, 'fzf', 'v1.2.4', FixtureClient())
        mutations = [
            lambda m: m['pokemon'].update(commit='spoof'),
            lambda m: m['fzf'].update(upstream='attacker/repo'),
            lambda m: m['fzf'].update(version='v1.2.2'),
            lambda m: m['fzf']['assets']['x86_64'].update(url='https://evil.invalid/fzf.tar.gz'),
            lambda m: m['fzf']['assets']['x86_64'].update(sha256='f' * 63),
            lambda m: m['fzf']['assets'].update(all=m['fzf']['assets']['x86_64']),
            lambda m: m['fzf-completion'].update(version='v1.2.3'),
            lambda m: m['fzf-completion'].update(file='evil.bash'),
            lambda m: m['fzf-key-bindings']['assets']['all'].update(url=updater.script_url('v1.2.3', 'key-bindings.bash')),
            lambda m: m['fzf']['assets']['x86_64'].update(command='curl evil'),
        ]
        for mutate in mutations:
            changed = copy.deepcopy(good)
            mutate(changed)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                updater.verify_manifest_change(base, changed, 'fzf')

    def test_cli_check_prints_json_and_never_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'tools.json'
            original = json.dumps(fixture_manifest())
            path.write_text(original)
            with patch.object(updater, 'GitHubClient', return_value=FixtureClient()), patch('sys.stdout', new_callable=io.StringIO) as output:
                updater.main(['--check', '--tool', 'fzf', '--manifest', str(path)])
            self.assertEqual(json.loads(output.getvalue())['updates'][0]['latest'], 'v1.2.4')
            self.assertEqual(path.read_text(), original)


if __name__ == '__main__':
    unittest.main()
