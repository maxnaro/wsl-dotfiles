import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('fish'), 'Fish unavailable')
class FishVi(unittest.TestCase):
    def test_modes_and_error_indicator(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, HOME=tmp, XDG_CONFIG_HOME=tmp,
                       TERM='xterm-256color')
            script = '''
source $argv[1]
source $argv[2]
for mode in default insert visual replace replace_one operator
    set -g fish_bind_mode $mode
    false
    fish_prompt
end
'''
            result = subprocess.run(['fish', '--no-config', '-c', script,
                                     str(ROOT/'fish/.config/fish/functions/fish_prompt.fish'),
                                     str(ROOT/'fish/.config/fish/functions/fish_mode_prompt.fish')],
                                    env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            # Each mode remains visible alongside the failed-command marker.
            for label in ('N ', 'I ', 'V ', 'R '):
                self.assertIn(label, result.stdout)
            self.assertEqual(result.stdout.count('❯'), 6)

    def test_interactive_bindings_survive_reload(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, HOME=tmp, XDG_CONFIG_HOME=tmp,
                       DOTFILES_NO_TMUX='1', TERM='xterm-256color')
            script = '''
source $argv[1]
source $argv[1]
bind -M default ctrl-r
bind --preset -M default u
printf 'CURSORS:%s,%s,%s\\n' $fish_cursor_default $fish_cursor_insert $fish_cursor_replace
'''
            result = subprocess.run(['fish', '--no-config', '-ic', script,
                                     str(ROOT/'fish/.config/fish/config.fish')],
                                    env=env, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('ctrl-r redo', result.stdout)
            self.assertIn('u undo', result.stdout)
            self.assertIn('CURSORS:block,line,underscore', result.stdout)
