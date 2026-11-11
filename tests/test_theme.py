import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / 'scripts/.scripts/dotfiles-theme'


class Theme(unittest.TestCase):
    def test_cycle_persistence_and_invalid_input(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / 'dotfiles/theme'
            env = dict(os.environ, XDG_STATE_HOME=directory, XDG_CONFIG_HOME=directory)
            env.pop('WSL_DISTRO_NAME', None)
            env['DOTFILES_THEME_NO_WINDOWS'] = '1'
            env.pop('TMUX', None)
            for action, expected in [('status', 'dark'), ('light', 'light'), ('apply', 'light'), ('toggle', 'dark'), ('dark', 'dark')]:
                result = subprocess.run([str(COMMAND), action], env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), expected)
            self.assertEqual((state / 'mode').read_text(), 'dark\n')
            self.assertIn('#7EA69F', (state / 'tmux.conf').read_text())
            before = {p.name: p.read_bytes() for p in state.iterdir()}
            result = subprocess.run([str(COMMAND), 'invalid'], env=env, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(before, {p.name: p.read_bytes() for p in state.iterdir()})

    def test_palette_matches_original_terminal(self):
        palette = json.loads((ROOT / 'themes/chocolatier.json').read_text())
        terminal = json.loads((ROOT / 'windows-terminal/settings.json').read_text())['schemes'][0]
        self.assertEqual(palette['dark']['bg'], terminal['background'])
        self.assertEqual(palette['dark']['fg'], terminal['foreground'])
        for mode in palette.values():
            self.assertEqual(len(mode['ansi']), 16)
            for color in mode['ansi']:
                self.assertRegex(color, '^#[0-9A-Fa-f]{6}$')


if __name__ == '__main__':
    unittest.main()
