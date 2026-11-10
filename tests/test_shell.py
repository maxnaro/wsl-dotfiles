import importlib.util
import io
import json
import os
import pty
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




class ShellStartup(unittest.TestCase):
    def test_bash_fish_handoff_and_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home/'bin').mkdir()
            fish = home/'bin/fish'
            fish.write_text('#!/bin/sh\necho FISH_HANDOFF\n')
            fish.chmod(0o755)
            env = dict(os.environ, HOME=tmp, PATH=str(home/'bin')+':/usr/bin:/bin', TERM='xterm', DOTFILES_NO_FISH='0')
            result = subprocess.run(['bash', '--noprofile', '--rcfile', str(ROOT/'bash/.bashrc'), '-ic', 'echo BASH_FALLBACK'], env=env, capture_output=True, text=True)
            self.assertIn('FISH_HANDOFF', result.stdout)
            self.assertNotIn('BASH_FALLBACK', result.stdout)
            env['DOTFILES_NO_FISH'] = '1'
            result = subprocess.run(['bash', '--noprofile', '--rcfile', str(ROOT/'bash/.bashrc'), '-ic', 'echo BASH_FALLBACK'], env=env, capture_output=True, text=True)
            self.assertIn('BASH_FALLBACK', result.stdout)
            self.assertNotIn('FISH_HANDOFF', result.stdout)
            self.assertNotIn('No such file', result.stderr)

    def test_tmux_autostart_guards_and_attach(self):
        shells = [('bash', ['bash', '--noprofile', '--rcfile', str(ROOT/'bash/.bashrc'), '-ic', 'exit'])]
        if installer.shutil.which('fish'):
            shells.append(('fish', [installer.shutil.which('fish'), '-ic', 'exit']))
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home/'bin').mkdir()
            (home/'.config').mkdir()
            (home/'.config/fish').symlink_to(ROOT/'fish/.config/fish')
            tmux = home/'bin/tmux'
            tmux.write_text('#!/bin/sh\necho "$1" >> "$HOME/tmux-log"\n[ "$1" != has-session ] || [ "$MOCK_SERVER" = 1 ]\n')
            tmux.chmod(0o755)
            for shell, command in shells:
                for server, extra, expected in [('0', {}, ['has-session', 'new-session']),
                                                ('1', {}, ['has-session', 'attach-session']),
                                                ('0', {'TMUX': 'inside'}, []),
                                                ('0', {'DOTFILES_NO_TMUX': '1'}, [])]:
                    log = home/'tmux-log'
                    log.unlink(missing_ok=True)
                    env = dict(os.environ, HOME=tmp, XDG_CONFIG_HOME=str(home/'.config'),
                               PATH=str(home/'bin')+':/usr/bin:/bin', TERM='xterm',
                               DOTFILES_NO_FISH='1', DOTFILES_NO_TMUX='0', MOCK_SERVER=server)
                    env.pop('TMUX', None)
                    env.update(extra)
                    master, slave = pty.openpty()
                    try:
                        result = subprocess.run(command, env=env, stdin=slave, stdout=slave, stderr=slave, timeout=15)
                    finally:
                        os.close(master)
                        os.close(slave)
                    self.assertEqual(result.returncode, 0, shell)
                    self.assertEqual(log.read_text().splitlines() if log.exists() else [], expected, shell)

    @unittest.skipUnless(installer.shutil.which('fish'), 'Fish unavailable')
    def test_fish_noninteractive_is_quiet_without_rust(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, HOME=tmp, XDG_CONFIG_HOME=tmp, XDG_DATA_HOME=tmp)
            result = subprocess.run(['fish', '--no-config', '-c', 'source $argv[1]; source $argv[2]', str(ROOT/'fish/.config/fish/config.fish'), str(ROOT/'fish/.config/fish/conf.d/rustup.fish')], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, '')
            self.assertEqual(result.stderr, '')


if __name__ == '__main__':
    unittest.main()
