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
                    color = '#427B58' if expected == 'light' else '#8EC07C'
                    self.assertIn(color, (state / 'tmux.conf').read_text())
            self.assertEqual((state / 'mode').read_text(), 'dark\n')
            self.assertIn('#8EC07C', (state / 'tmux.conf').read_text())
            before = {p.name: p.read_bytes() for p in state.iterdir()}
            result = subprocess.run([str(COMMAND), 'invalid'], env=env, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(before, {p.name: p.read_bytes() for p in state.iterdir()})

    def test_gruvbox_medium_light_and_generated_schemes(self):
        loader = importlib.machinery.SourceFileLoader('dotfiles_theme', str(COMMAND))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        command = importlib.util.module_from_spec(spec)
        loader.exec_module(command)
        palette = json.loads((ROOT / 'themes/chocolatier.json').read_text())
        light = palette['light']
        self.assertEqual({k: light[k] for k in ('bg', 'surface', 'selection', 'fg', 'bright', 'muted')}, {
            'bg': '#FBF1C7', 'surface': '#EBDBB2', 'selection': '#D5C4A1',
            'fg': '#3C3836', 'bright': '#282828', 'muted': '#928374',
        })
        self.assertEqual(light['ansi'], [
            '#FBF1C7', '#CC241D', '#98971A', '#D79921', '#458588', '#B16286', '#689D6A', '#7C6F64',
            '#928374', '#9D0006', '#79740E', '#B57614', '#076678', '#8F3F71', '#427B58', '#3C3836',
        ])
        for index, name in enumerate(('red', 'green', 'yellow', 'blue', 'purple', 'cyan'), 9):
            self.assertEqual(light[name], light['ansi'][index])
            self.assertEqual(light['picker'][name], light[name])
        self.assertEqual(light['picker']['hidden'], '#665C54')
        self.assertEqual(light['picker']['muted'], '#665C54')
        dark_scheme, light_scheme = command.schemes(palette)
        self.assertEqual(dark_scheme['name'], 'Chocolatier')
        self.assertEqual(light_scheme['name'], 'Gruvbox Light')
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
            self.assertEqual(config, original.replace('[tui]\n', '[tui]\ntheme = "gruvbox-light"\n'))
        self.assertEqual(command.set_toml_key('', 'tui', 'theme', 'a'), '[tui]\ntheme = "a"\n')
        self.assertEqual(command.mix('#FFFFFF', '#000000', 0.5), '#808080')

    def test_toggle_binding_is_silent(self):
        tmux = (ROOT / 'tmux/.config/tmux/tmux.conf').read_text()
        binding = next(line for line in tmux.splitlines() if 'dotfiles-theme toggle' in line)
        self.assertIn('run-shell -b', binding)
        self.assertIn('>/dev/null', binding)
        self.assertIn('display-message', binding)

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
