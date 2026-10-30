"""Isolated real-tmux save/restore smoke test; run explicitly."""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='dotfiles-recovery-') as temporary:
    home = Path(temporary)
    socket = str(home/'tmux.sock')
    env = dict(os.environ, HOME=temporary, XDG_CONFIG_HOME=str(home/'.config'), XDG_DATA_HOME=str(home/'.local/share'), XDG_STATE_HOME=str(home/'.local/state'))
    env.pop('TMUX', None)
    (home/'.config').mkdir()
    (home/'.config/tmux').symlink_to(ROOT/'tmux/.config/tmux')
    def tmux(*args):
        return subprocess.run(['tmux', '-S', socket, *args], env=env, check=True, capture_output=True, text=True).stdout.strip()
    try:
        tmux('-f', '/dev/null', 'new-session', '-d', '-s', 'project', '-c', temporary, '/bin/sleep 120')
        tmux('source-file', str(ROOT/'tmux/.config/tmux/tmux.conf'))
        # This test uses a private socket and home; no live user server is reconfigured.
        tmux('split-window', '-h', '-c', temporary, '/bin/sleep 120')
        assert tmux('show-option', '-gqv', '@continuum-restore') == 'off'
        assert tmux('show-option', '-gqv', '@resurrect-processes') == 'false'
        assert tmux('show-option', '-gqv', '@continuum-save-interval') == '15'
        assert tmux('show-option', '-gqv', '@prefix-help-save-key') == 'C-s'
        for key in ('g', 'C-s', 'C-r'):
            assert tmux('list-keys', '-T', 'prefix', key)
        tmux('run-shell', str(ROOT/'tmux/.config/tmux/plugins/tmux-resurrect/scripts/save.sh'))
        assert (home/'.local/state/tmux/resurrect/last').exists()
        tmux('kill-pane', '-t', 'project:.2')
        tmux('run-shell', str(ROOT/'tmux/.config/tmux/plugins/tmux-resurrect/scripts/restore.sh'))
        assert len(tmux('list-panes', '-t', 'project', '-F', '#{pane_current_path}').splitlines()) == 2
        tmux('source-file', str(ROOT/'tmux/.config/tmux/tmux.conf'))
        status = tmux('show-option', '-gqv', 'status-right')
        assert '#{RUNCAT_FRAME}' in status
        assert status.count('continuum_save.sh') <= 1
        assert status.count(' watch ') == 1
        print('Recovery passed: shortcuts, save, restore, layout-only policy, reload, status triggers')
    finally:
        subprocess.run(['tmux', '-S', socket, 'kill-server'], env=env, capture_output=True)
