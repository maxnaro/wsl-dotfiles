import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from contextlib import redirect_stderr
from io import StringIO

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
                    self.assertTrue(command.apps(mode, palette[mode]))
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

    def test_apps_reports_codex_configuration_without_session_warning(self):
        command = self.load()
        palette = json.loads((ROOT / 'themes/chocolatier.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            codex = Path(directory) / 'codex'
            claude = Path(directory) / 'claude-absent'
            codex.mkdir()
            isolated_env = {'CODEX_HOME': str(codex), 'CLAUDE_CONFIG_DIR': str(claude), 'DOTFILES_THEME_NO_APPS': '0'}
            with unittest.mock.patch.dict(os.environ, isolated_env):
                stderr = StringIO()
                with redirect_stderr(stderr):
                    result = command.apps('light', palette['light'])
            self.assertTrue(result)
            self.assertEqual(stderr.getvalue(), '')
            with unittest.mock.patch.dict(os.environ, dict(isolated_env, CODEX_HOME=str(Path(directory) / 'absent'))):
                self.assertFalse(command.apps('dark', palette['dark']))

    def test_refresh_tmux_colours_writes_query_at_scheduled_offsets(self):
        command = self.load()
        wire = b'\x1b]11;?\x1b\\\x1b]10;?\x1b\\'
        writes = []
        opened = []
        with unittest.mock.patch.object(command.os, 'open', side_effect=lambda path, flags: opened.append((path, flags)) or len(opened)), \
             unittest.mock.patch.object(command.os, 'isatty', return_value=True), \
             unittest.mock.patch.object(command.subprocess, 'run', return_value=subprocess.CompletedProcess(['ps'], 0, stdout='42 42\n')) as process_check, \
             unittest.mock.patch.object(command.os, 'write', side_effect=lambda fd, data: writes.append((fd, data)) or len(data)), \
             unittest.mock.patch.object(command.os, 'close') as close, \
             unittest.mock.patch.object(command.time, 'monotonic', return_value=0), \
             unittest.mock.patch.object(command.time, 'sleep') as sleep:
            command.refresh_tmux_colours({'/dev/pts/1': 42, '/dev/pts/2': 43})
        self.assertEqual([path for path, _ in opened], ['/dev/pts/1', '/dev/pts/2'] * 4)
        self.assertTrue(all(data == wire for _, data in writes))
        self.assertEqual(len(writes), 8)
        self.assertEqual(close.call_count, 8)
        self.assertTrue(all(flags & os.O_WRONLY and flags & os.O_NOCTTY and flags & os.O_NONBLOCK for _, flags in opened))
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [0.25, 1, 2])
        self.assertEqual(process_check.call_count, 8)
        self.assertTrue(all(call.kwargs['timeout'] == 1 for call in process_check.call_args_list))
        self.assertTrue(all(call.args[0][0] == 'ps' and call.args[0][1] == '-p' for call in process_check.call_args_list))

    def test_refresh_tmux_colours_skips_empty_and_failed_terminals(self):
        command = self.load()
        with unittest.mock.patch.object(command.time, 'sleep') as sleep:
            command.refresh_tmux_colours([])
        sleep.assert_not_called()

        def open_terminal(path, flags):
            if path == '/dev/pts/open-fails':
                raise OSError('gone')
            return {'/dev/pts/not-a-tty': 1, '/dev/pts/short-write': 2, '/dev/pts/write-fails': 3}[path]

        with unittest.mock.patch.object(command.os, 'open', side_effect=open_terminal) as open_file, \
             unittest.mock.patch.object(command.os, 'isatty', side_effect=lambda fd: fd in (2, 3)), \
             unittest.mock.patch.object(command.subprocess, 'run', return_value=subprocess.CompletedProcess(['ps'], 0, stdout='42 42\n')), \
             unittest.mock.patch.object(command.os, 'write', side_effect=lambda fd, data: 1 if fd == 2 else (_ for _ in ()).throw(OSError('write failed'))) as write, \
             unittest.mock.patch.object(command.os, 'close') as close, \
             unittest.mock.patch.object(command.time, 'monotonic', return_value=0), \
             unittest.mock.patch.object(command.time, 'sleep'), \
             redirect_stderr(StringIO()) as stderr:
            command.refresh_tmux_colours({'/dev/pts/open-fails': 42, '/dev/pts/not-a-tty': 42,
                                          '/dev/pts/short-write': 42, '/dev/pts/write-fails': 42})
        self.assertIn('open-fails', stderr.getvalue())
        self.assertIn('short-write', stderr.getvalue())
        self.assertIn('write-fails', stderr.getvalue())
        self.assertEqual(open_file.call_count, 4)
        self.assertEqual(write.call_count, 2)
        self.assertEqual(close.call_count, 3)

    def test_refresh_tmux_colours_skips_detached_terminal_owners(self):
        command = self.load()

        def process_state(argv, **kwargs):
            pid = argv[2]
            if pid == '123':
                return subprocess.CompletedProcess(argv, 0, stdout='42 88\n')
            if pid == '456':
                return subprocess.CompletedProcess(argv, 1, stdout='')
            raise subprocess.TimeoutExpired(argv, 1)

        with unittest.mock.patch.object(command.os, 'open', return_value=9), \
             unittest.mock.patch.object(command.os, 'isatty', return_value=True), \
             unittest.mock.patch.object(command.subprocess, 'run', side_effect=process_state) as process_check, \
             unittest.mock.patch.object(command.os, 'write') as write, \
             unittest.mock.patch.object(command.os, 'close') as close, \
             unittest.mock.patch.object(command.time, 'sleep'), \
             redirect_stderr(StringIO()) as stderr:
            command.refresh_tmux_colours({'/dev/pts/detached': 123, '/dev/pts/exited': 456,
                                          '/dev/pts/check-times-out': 789})
        self.assertIn('detached', stderr.getvalue())
        self.assertIn('exited', stderr.getvalue())
        self.assertIn('check-times-out', stderr.getvalue())
        write.assert_not_called()
        self.assertEqual(close.call_count, 3)
        self.assertEqual(process_check.call_count, 3)

    def test_toggle_binding_is_silent(self):
        tmux = (ROOT / 'tmux/.config/tmux/tmux.conf').read_text()
        binding = next(line for line in tmux.splitlines() if 'dotfiles-theme toggle' in line)
        self.assertIn('run-shell -b', binding)
        self.assertIn('>/dev/null', binding)
        self.assertIn('display-message', binding)

    def test_toggle_binding_forwards_warnings_and_failure_fallback(self):
        tmux_config = (ROOT / 'tmux/.config/tmux/tmux.conf').read_text()
        binding = next(line for line in tmux_config.splitlines() if 'dotfiles-theme toggle' in line)
        shell = next(arg for arg in shlex.split(binding) if 'dotfiles-theme toggle' in arg)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            local_bin = root / '.local/bin'
            tools = root / 'bin'
            local_bin.mkdir(parents=True)
            tools.mkdir()
            theme = local_bin / 'dotfiles-theme'
            theme.write_text('#!/bin/sh\necho "$THEME_BEHAVIOR-mode"\ncase "$THEME_BEHAVIOR" in warning) echo "Codex restart warning" >&2;; failure) echo "underlying failure" >&2; exit 1;; silent-failure) exit 1;; esac\nexit 0\n')
            theme.chmod(0o755)
            calls = root / 'tmux-calls'
            tmux = tools / 'tmux'
            tmux.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$TMUX_CALLS"\n')
            tmux.chmod(0o755)
            base = dict(os.environ, HOME=str(root), PATH=str(tools) + os.pathsep + os.environ['PATH'], TMUX_CALLS=str(calls))
            for behavior, expected in [('warning', 'display-message -d 4000 dotfiles-theme: Codex restart warning'),
                                       ('success', None), ('failure', 'display-message -d 4000 dotfiles-theme: underlying failure'),
                                       ('silent-failure', 'display-message -d 4000 dotfiles-theme: toggle failed')]:
                calls.unlink(missing_ok=True)
                env = dict(base, THEME_BEHAVIOR=behavior)
                result = subprocess.run(['/bin/sh', '-c', shell], env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, '')
                lines = calls.read_text().splitlines() if calls.exists() else []
                if expected:
                    self.assertEqual(lines, [expected])
                else:
                    self.assertEqual(lines, [])

    def test_main_orders_preflight_apply_and_codex_notice_after_reload(self):
        command = self.load()
        palette = json.loads((ROOT / 'themes/chocolatier.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            events = []
            stderr = StringIO()
            real_print = print

            def record_print(*args, **kwargs):
                destination = kwargs.get('file')
                if destination is sys.stderr:
                    events.append('notice')
                    real_print(*args, **kwargs)
                else:
                    real_print(*args, **kwargs)

            with unittest.mock.patch.object(command, 'STATE', Path(directory) / 'state'), \
                 unittest.mock.patch.object(command, 'palettes', return_value=palette), \
                 unittest.mock.patch.object(command, 'preflight', side_effect=lambda *args: events.append('preflight')), \
                 unittest.mock.patch.object(command, 'windows', side_effect=lambda *args: events.append('windows')), \
                 unittest.mock.patch.object(command, 'apps', side_effect=lambda *args: events.append('apps') or True), \
                 unittest.mock.patch.object(command, 'desktop_apply'), \
                 unittest.mock.patch.object(command, 'reload_tmux', side_effect=lambda: events.append('reload')), \
                 unittest.mock.patch.object(command.sys, 'argv', ['dotfiles-theme', 'light']), \
                 unittest.mock.patch('builtins.print', side_effect=record_print):
                with redirect_stderr(stderr):
                    command.main()
            self.assertEqual(events, ['preflight', 'windows', 'apps', 'reload', 'notice'])
            self.assertEqual(stderr.getvalue(), 'Warning: Codex: exit and run codex resume to refresh interface and syntax colours; if still stale, detach/reattach tmux first.\n')
            self.assertEqual((Path(directory) / 'state/mode').read_text(), 'light\n')

    def test_status_and_failed_preflight_do_not_query_tmux_or_change_state(self):
        command = self.load()
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / 'state'
            with unittest.mock.patch.object(command, 'STATE', state), \
                 unittest.mock.patch.object(command.sys, 'argv', ['dotfiles-theme', 'status']), \
                 unittest.mock.patch.object(command, 'reload_tmux') as reload_tmux, \
                 unittest.mock.patch.object(command, 'apps') as apps, \
                 redirect_stderr(StringIO()):
                command.main()
            reload_tmux.assert_not_called()
            apps.assert_not_called()
            self.assertFalse(state.exists())

            palette = json.loads((ROOT / 'themes/chocolatier.json').read_text())
            with unittest.mock.patch.object(command, 'palettes', return_value=palette), \
                 unittest.mock.patch.object(command, 'STATE', state), \
                 unittest.mock.patch.object(command, 'preflight', side_effect=ValueError('bad config')), \
                 unittest.mock.patch.object(command, 'windows') as windows, \
                 unittest.mock.patch.object(command, 'apps') as apps, \
                 unittest.mock.patch.object(command, 'reload_tmux') as reload_tmux, \
                 unittest.mock.patch.object(command.sys, 'argv', ['dotfiles-theme', 'light']):
                with self.assertRaisesRegex(ValueError, 'bad config'):
                    command.main()
            windows.assert_not_called()
            apps.assert_not_called()
            reload_tmux.assert_not_called()
            self.assertFalse((state / 'mode').exists())

    def test_reload_tmux_lists_only_live_interactive_client_ttys(self):
        command = self.load()
        calls = []
        current = '/tmp/tmux-current'
        outputs = {
            current: '0\t42\t/dev/pts/1\n1\t99\t/dev/pts/control\n0\t17\t\n0\t0\t/dev/pts/zero-pid\n0\tbad\t/dev/pts/invalid-pid\n0\t42\t/dev/pts/1\n',
            None: '0\t43\t/dev/pts/2\n0\t42\t/dev/pts/1\n',
        }

        def run(argv, **kwargs):
            calls.append((argv, kwargs))
            if argv[-1] == 'has-session':
                return subprocess.CompletedProcess(argv, 0)
            if argv[-1] == 'source-file':
                return subprocess.CompletedProcess(argv, 0)
            return subprocess.CompletedProcess(argv, 0, stdout=outputs[current if '-S' in argv else None])

        with unittest.mock.patch.object(command, 'STATE', Path('/tmp/theme-state')), \
             unittest.mock.patch.dict(os.environ, {'TMUX': current + ',234,0'}), \
             unittest.mock.patch.object(command.subprocess, 'run', side_effect=run), \
             unittest.mock.patch.object(command, 'refresh_tmux_colours') as refresh:
            command.reload_tmux()
        self.assertEqual(refresh.call_args.args[0], {'/dev/pts/1': 42, '/dev/pts/2': 43})
        listings = [(argv, kwargs) for argv, kwargs in calls if 'list-clients' in argv]
        self.assertEqual(len(listings), 2)
        for argv, kwargs in listings:
            self.assertIn('-F', argv)
            self.assertEqual(argv[-1], '#{client_control_mode}\t#{client_pid}\t#{client_tty}')
            self.assertEqual(kwargs['timeout'], 2)
        self.assertEqual(listings[0][0][:3], ['tmux', '-S', current])
        self.assertEqual(listings[1][0][0], 'tmux')
        self.assertNotIn('-S', listings[1][0])

    def test_reload_tmux_skips_absent_clients_and_warns_on_list_failure(self):
        command = self.load()

        def run_empty(argv, **kwargs):
            if argv[-1] == 'has-session':
                return subprocess.CompletedProcess(argv, 0)
            if 'list-clients' in argv:
                return subprocess.CompletedProcess(argv, 0, stdout='1\t99\t/dev/pts/control\n0\t42\t\n')
            return subprocess.CompletedProcess(argv, 0, stdout='')

        with unittest.mock.patch.object(command.subprocess, 'run', side_effect=run_empty), \
             unittest.mock.patch.dict(os.environ, {}, clear=False), \
             unittest.mock.patch.dict(os.environ, {'TMUX': ''}), \
             unittest.mock.patch.object(command, 'refresh_tmux_colours') as refresh:
            command.reload_tmux()
        refresh.assert_called_once_with({})

        def run_failed(argv, **kwargs):
            if argv[-1] == 'has-session':
                return subprocess.CompletedProcess(argv, 0)
            if 'list-clients' in argv:
                return subprocess.CompletedProcess(argv, 1, stdout='', stderr='list failed')
            return subprocess.CompletedProcess(argv, 0)

        stderr = StringIO()
        with unittest.mock.patch.object(command.subprocess, 'run', side_effect=run_failed), \
             unittest.mock.patch.dict(os.environ, {'TMUX': ''}), \
             unittest.mock.patch.object(command, 'refresh_tmux_colours') as refresh, \
             redirect_stderr(stderr):
            command.reload_tmux()
        self.assertIn('list failed', stderr.getvalue())
        refresh.assert_called_once_with({})

        with unittest.mock.patch.object(command.subprocess, 'run', side_effect=FileNotFoundError), \
             unittest.mock.patch.dict(os.environ, {'TMUX': ''}), \
             unittest.mock.patch.object(command, 'refresh_tmux_colours') as refresh:
            command.reload_tmux()
        refresh.assert_called_once_with({})

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
            self.assertIn('exit and run codex resume', result.stderr)

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
