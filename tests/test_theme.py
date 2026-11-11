import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import unittest.mock

ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / 'scripts/.scripts/dotfiles-theme'


class Theme(unittest.TestCase):
    def test_cycle_persistence_and_invalid_input(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / 'dotfiles/theme'
            env = dict(os.environ, XDG_STATE_HOME=directory, XDG_CONFIG_HOME=directory)
            env.pop('WSL_DISTRO_NAME', None)
            env['DOTFILES_THEME_NO_WINDOWS'] = '1'
            env['DOTFILES_THEME_NO_APPS'] = '1'
            env.pop('TMUX', None)
            tools = Path(directory) / 'bin'
            tools.mkdir()
            stub = tools / 'tmux'
            stub.write_text('#!/bin/sh\nexit 1\n')
            stub.chmod(0o755)
            env['PATH'] = str(tools) + os.pathsep + env['PATH']
            for action, expected in [('status', 'dark'), ('light', 'light'), ('apply', 'light'), ('toggle', 'dark'), ('dark', 'dark')]:
                result = subprocess.run([str(COMMAND), action], env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), expected)
                if action != 'status':
                    color = '#076B3A' if expected == 'light' else '#8EC07C'
                    self.assertIn(color, (state / 'tmux.conf').read_text())
            self.assertEqual((state / 'mode').read_text(), 'dark\n')
            self.assertIn('#8EC07C', (state / 'tmux.conf').read_text())
            before = {p.name: p.read_bytes() for p in state.iterdir()}
            result = subprocess.run([str(COMMAND), 'invalid'], env=env, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(before, {p.name: p.read_bytes() for p in state.iterdir()})

    def test_kimbie_light_and_generated_schemes(self):
        loader = importlib.machinery.SourceFileLoader('dotfiles_theme', str(COMMAND))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        command = importlib.util.module_from_spec(spec)
        loader.exec_module(command)
        palette = json.loads((ROOT / 'themes/chocolatier.json').read_text())
        light = palette['light']
        self.assertEqual(light['bg'], '#FBEBD4')
        self.assertEqual(light['fg'], '#221A0F')
        self.assertEqual(light['picker']['muted'], '#5E452B')
        dark_scheme, light_scheme = command.schemes(palette)
        self.assertEqual(dark_scheme['name'], 'Chocolatier')
        self.assertEqual(light_scheme['name'], 'Kimbie Light')
        self.assertEqual(light_scheme['background'], light['bg'])
        self.assertEqual(light_scheme['foreground'], light['fg'])
        self.assertEqual(light_scheme['selectionBackground'], light['selection'])
        self.assertEqual(light_scheme['cursorColor'], light['bright'])
        names = ['black', 'red', 'green', 'yellow', 'blue', 'purple', 'cyan', 'white',
                 'brightBlack', 'brightRed', 'brightGreen', 'brightYellow', 'brightBlue',
                 'brightPurple', 'brightCyan', 'brightWhite']
        self.assertEqual([light_scheme[name] for name in names], light['ansi'])

    def load(self):
        loader = importlib.machinery.SourceFileLoader('dotfiles_theme', str(COMMAND))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        command = importlib.util.module_from_spec(spec)
        loader.exec_module(command)
        return command

    def test_tmux_theme_preserves_plugin_status_hooks(self):
        command = self.load()
        palette = json.loads((ROOT / 'themes/chocolatier.json').read_text())
        for colors in palette.values():
            lines = command.tmux_style(colors).splitlines()
            base = next(line for line in lines if line.startswith('set -g @dotfiles-status-right '))
            self.assertIn(colors['purple'], base)
            self.assertIn('#h', base)
            self.assertFalse(any(line.startswith('set -g status-right ') for line in lines))

    def test_claude_and_codex_follow_mode(self):
        command = self.load()
        palette = json.loads((ROOT / 'themes/chocolatier.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            claude, codex = Path(directory) / 'claude', Path(directory) / 'codex'
            claude.mkdir()
            codex.mkdir()
            original = 'model = "x"\n[tui]\nscreen_reader_detection_done = true\n\n[notice]\nhide = true\n'
            (codex / 'config.toml').write_text(original)
            env = {'CLAUDE_CONFIG_DIR': str(claude), 'CODEX_HOME': str(codex)}
            with unittest.mock.patch.dict(os.environ, env):
                os.environ.pop('DOTFILES_THEME_NO_APPS', None)
                for mode in ('light', 'dark', 'light'):
                    command.apps(mode, palette[mode])
                    theme = json.loads((claude / 'themes/dotfiles.json').read_text())
                    self.assertEqual(theme['base'], mode)
                    self.assertEqual('theme =' in (codex / 'config.toml').read_text(), mode == 'light')
                    self.assertEqual(theme['overrides']['text'], palette[mode]['fg'])
                    self.assertEqual(theme['overrides']['userMessageBackground'], palette[mode]['surface'])
                    for value in theme['overrides'].values():
                        self.assertRegex(value, '^#[0-9A-F]{6}$')
            config = (codex / 'config.toml').read_text()
            self.assertEqual(config, original.replace('[tui]\n', '[tui]\ntheme = "dotfiles-kimbie-light"\n'))
        self.assertEqual(command.set_toml_key('', 'tui', 'theme', 'a'), '[tui]\ntheme = "a"\n')
        self.assertEqual(command.mix('#FFFFFF', '#000000', 0.5), '#808080')

    def test_toggle_binding_is_silent(self):
        tmux = (ROOT / 'tmux/.config/tmux/tmux.conf').read_text()
        binding = next(line for line in tmux.splitlines() if 'dotfiles-theme toggle' in line)
        self.assertIn('run-shell -b', binding)
        self.assertIn('>/dev/null', binding)
        self.assertIn('display-message', binding)

    def isolated(self, directory):
        root = Path(directory)
        tools = root / 'bin'
        tools.mkdir()
        tmux = tools / 'tmux'
        tmux.write_text('#!/bin/sh\nexit 1\n')
        tmux.chmod(0o755)
        claude, codex = root / 'claude', root / 'codex'
        claude.mkdir()
        codex.mkdir()
        return dict(os.environ, XDG_STATE_HOME=str(root / 'state'), XDG_CONFIG_HOME=str(root / 'config'),
                    CLAUDE_CONFIG_DIR=str(claude), CODEX_HOME=str(codex), DOTFILES_THEME_NO_WINDOWS='1',
                    DOTFILES_THEME_NO_APPS='0', TMUX='', PATH=str(tools) + os.pathsep + os.environ['PATH'])

    def test_preflight_rejects_bad_config_before_app_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            env = self.isolated(directory)
            root = Path(directory)
            (root / 'codex/config.toml').write_text('broken = [')
            result = subprocess.run([str(COMMAND), 'light'], env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / 'claude/settings.json').exists())
            self.assertFalse((root / 'state/dotfiles/theme/mode').exists())
            self.assertFalse((root / 'state/dotfiles/theme/tmux.conf').exists())

    def test_concurrent_toggles_are_serialized(self):
        with tempfile.TemporaryDirectory() as directory:
            env = self.isolated(directory)
            processes = [subprocess.Popen([str(COMMAND), 'toggle'], env=env, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE, text=True) for _ in range(8)]
            for process in processes:
                out, err = process.communicate(timeout=15)
                self.assertEqual(process.returncode, 0, err)
            self.assertEqual((Path(directory) / 'state/dotfiles/theme/mode').read_text(), 'dark\n')

    def test_verbose_status_does_not_apply_or_create_state(self):
        with tempfile.TemporaryDirectory() as directory:
            env = self.isolated(directory)
            result = subprocess.run([str(COMMAND), 'status', '--verbose'], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('configuration checks only', result.stdout)
            self.assertIn('unverified', result.stdout)
            self.assertFalse((Path(directory) / 'state').exists())
            self.assertFalse((Path(directory) / 'claude/settings.json').exists())

    def test_late_tmux_reload_failure_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            env = self.isolated(directory)
            (Path(directory) / 'bin/tmux').write_text('#!/bin/sh\ncase "$1" in has-session) exit 0;; *) echo reload-failed >&2; exit 1;; esac\n')
            result = subprocess.run([str(COMMAND), 'light'], env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('reload failed after apply', result.stderr)
            self.assertEqual((Path(directory) / 'state/dotfiles/theme/mode').read_text(), 'light\n')

    def test_generated_codex_theme_and_claude_selection(self):
        import plistlib
        with tempfile.TemporaryDirectory() as directory:
            env = self.isolated(directory)
            result = subprocess.run([str(COMMAND), 'light'], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            root = Path(directory)
            self.assertEqual(json.loads((root / 'claude/settings.json').read_text())['theme'], 'custom:dotfiles')
            theme = plistlib.loads((root / 'codex/themes/dotfiles-kimbie-light.tmTheme').read_bytes())
            self.assertEqual(theme['settings'][0]['settings']['foreground'], '#221A0F')
            self.assertIn('may need reopening', result.stderr)

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
