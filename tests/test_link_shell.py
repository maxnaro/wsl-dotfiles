import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('link_shell', ROOT/'setup/link_shell.py')
link_shell = importlib.util.module_from_spec(spec)
spec.loader.exec_module(link_shell)


class ShellLinks(unittest.TestCase):
    def test_migrates_linked_fish_directory_and_preserves_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            module, home, old = root/'module', root/'home', root/'old-fish'
            (module/'fish').mkdir(parents=True)
            (module/'fish/config.fish').write_text('new config')
            (module/'manifest.json').write_text(json.dumps({'version': 1, 'files': [
                {'source': 'fish/config.fish', 'target': '.config/fish/config.fish', 'profiles': ['fish']}]}))
            old.mkdir()
            (old/'config.fish').write_text('custom config')
            (old/'local.fish').write_text('local')
            (old/'fish_variables').write_text('state')
            (home/'.config').mkdir(parents=True)
            (home/'.config/fish').symlink_to(old)
            link_shell.link_shell(module, home)
            fish = home/'.config/fish'
            self.assertFalse(fish.is_symlink())
            self.assertEqual((fish/'local.fish').read_text(), 'local')
            self.assertEqual((fish/'fish_variables').read_text(), 'state')
            self.assertEqual((fish/'config.fish').resolve(), (module/'fish/config.fish').resolve())
            self.assertEqual(next(fish.glob('config.fish.bak.*/original')).read_text(), 'custom config')
            link_shell.link_shell(module, home)
            self.assertEqual(len(list(fish.glob('config.fish.bak.*'))), 1)

    def test_rejects_manifest_paths_outside_module_or_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'manifest.json').write_text(json.dumps({'version': 1, 'files': [
                {'source': '../escape', 'target': '.bashrc', 'profiles': ['bash']}]}))
            with self.assertRaises(ValueError):
                link_shell.link_shell(root, root/'home')

    def test_symlinked_config_outside_home_fails_before_any_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            module, home, outside = root/'module', root/'home', root/'outside'
            module.mkdir(); home.mkdir(); outside.mkdir()
            (module/'bashrc').write_text('bash')
            (module/'fish').write_text('fish')
            (module/'manifest.json').write_text(json.dumps({'version': 1, 'files': [
                {'source': 'bashrc', 'target': '.bashrc', 'profiles': ['bash']},
                {'source': 'fish', 'target': '.config/fish/config.fish', 'profiles': ['fish']}]}))
            (home/'.config').symlink_to(outside)
            with self.assertRaisesRegex(ValueError, 'escapes home'):
                link_shell.link_shell(module, home)
            self.assertFalse((home/'.bashrc').exists())
            self.assertEqual(list(outside.iterdir()), [])
