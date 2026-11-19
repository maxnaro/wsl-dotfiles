import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Features(unittest.TestCase):
    def workspace(self, selection='', exit_code=0, entries="project with spaces"):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            bindir = home/'.local/bin'
            bindir.mkdir(parents=True)
            scripts = {
                'sesh': '#!/bin/sh\nif [ "$1" = list ]; then printf "%s\\n" "$ENTRIES"; else printf "%s\\n" "$@" > "$HOME/connected"; fi\n',
                'fzf': f'#!/bin/sh\ncat >/dev/null\nprintf "%s" "$SELECTED"\nexit {exit_code}\n',
                'zoxide': '#!/bin/sh\nexit 0\n',
            }
            for tool, body in scripts.items():
                p = bindir/tool
                p.write_text(body)
                p.chmod(0o755)
            env = dict(os.environ, HOME=tmp, SELECTED=selection, ENTRIES=entries, PATH='/usr/bin:/bin')
            result = subprocess.run(['bash', str(ROOT/'tmux/.config/tmux/scripts/workspace.sh')], env=env, capture_output=True, input=b"\n")
            connection = home/'connected'
            return result.returncode, connection.read_text() if connection.exists() else None

    def test_project_paths_are_single_arguments(self):
        status, connection = self.workspace('project with spaces')
        self.assertEqual(status, 0)
        self.assertEqual(connection, 'connect\nproject with spaces\n')

    def test_cancellation_does_not_connect(self):
        self.assertEqual(self.workspace(exit_code=130), (0, None))

    def test_empty_selection_does_not_connect(self):
        self.assertEqual(self.workspace(), (0, None))

    def test_empty_project_list_does_not_connect(self):
        self.assertEqual(self.workspace(entries=''), (0, None))

    def test_workspace_style_is_independent_of_tmux_startup_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            bindir = home / '.local/bin'
            bindir.mkdir(parents=True)
            for tool in ('sesh', 'zoxide', 'tmux'):
                stub = bindir / tool
                stub.write_text('#!/bin/sh\nexit 0\n')
                stub.chmod(0o755)
            stub = bindir / 'fzf'
            stub.write_text(
                '#!/bin/sh\ncat >/dev/null\n'
                'printf "%s\\n" "$FZF_DEFAULT_OPTS" "$FZF_DEFAULT_OPTS_FILE" "$@" > "$HOME/options"\n'
            )
            stub.chmod(0o755)
            snapshots = []
            for inherited in ('', '--height=20% --layout=default --border=none'):
                env = dict(os.environ, HOME=tmp, PATH='/usr/bin:/bin',
                           FZF_DEFAULT_OPTS=inherited, FZF_DEFAULT_OPTS_FILE='/stale/options')
                subprocess.run(['bash', str(ROOT / 'tmux/.config/tmux/scripts/workspace.sh')],
                               env=env, check=True, capture_output=True)
                snapshots.append((home / 'options').read_text().splitlines())
            self.assertEqual(snapshots[0], snapshots[1])
            self.assertEqual(snapshots[0][:2], ['', ''])
            for option in ('--style=full', '--layout=reverse', '--border=rounded', '--height=100%'):
                self.assertIn(option, snapshots[0])
