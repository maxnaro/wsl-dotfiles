"""Exercise prefix help through an attached PTY on a private tmux server.

Run explicitly with python3 tests/live_prefix_help.py; requires built tmux plugins.
Theme rendering calls tmux_style directly, never the command's live reload path.
"""
import fcntl
import json
import os
from pathlib import Path
import pty
import runpy
import select
import struct
import subprocess
import tempfile
import termios
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix='dotfiles-prefix-help-') as temporary:
        home = Path(temporary)
        socket = str(home / 'tmux.sock')
        env = dict(os.environ, HOME=temporary, TERM='xterm-256color',
                   XDG_CONFIG_HOME=str(home / '.config'),
                   XDG_STATE_HOME=str(home / '.local/state'),
                   XDG_CACHE_HOME=str(home / '.cache'),
                   XDG_DATA_HOME=str(home / '.local/share'))
        env.pop('TMUX', None)
        (home / '.config').mkdir()
        (home / '.config/tmux').symlink_to(ROOT / 'tmux/.config/tmux')
        theme = home / '.local/state/dotfiles/theme/tmux.conf'
        theme.parent.mkdir(parents=True)
        render = runpy.run_path(str(ROOT / 'scripts/.scripts/dotfiles-theme'))['tmux_style']
        palette = json.loads((ROOT / 'themes/chocolatier.json').read_text())
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 120, 0, 0))
        client = None

        def tmux(*args):
            return subprocess.run(['tmux', '-S', socket, *args], env=env, check=True,
                                  capture_output=True, text=True, timeout=10).stdout.strip()

        def read_until(needle, timeout=5):
            output = b''
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if select.select([master], [], [], 0.05)[0]:
                    output += os.read(master, 65536)
                    if needle in output:
                        return
            raise AssertionError(f'PTY did not display {needle!r}: {output[-2000:]!r}')

        def drain():
            while select.select([master], [], [], 0.05)[0]:
                os.read(master, 65536)

        def wait_for(format_, expected):
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if tmux('display-message', '-p', format_) == expected:
                    return
                time.sleep(0.05)
            raise AssertionError(f'{format_} did not become {expected!r}')

        def attach_terminal():
            os.setsid()
            fcntl.ioctl(slave, termios.TIOCSCTTY, 0)

        try:
            tmux('-f', '/dev/null', 'new-session', '-d', '-s', 'test', '/bin/sleep 120')
            tmux('source-file', str(ROOT / 'tmux/.config/tmux/tmux.conf'))
            # A harmless hook proves theme generation preserves other plugins too,
            # even when continuum suppresses its hook because a live server exists.
            tmux('set-option', '-ag', 'status-right', '#(true continuum_save.sh)')
            tmux('bind-key', '-N', 'Regression replay', 'x', 'set-option', '-g', '@replayed', 'yes')
            tmux('bind-key', '-n', 'y', 'set-option', '-g', '@root-forwarded', 'yes')
            client = subprocess.Popen(['tmux', '-S', socket, 'attach-session', '-t', 'test'],
                                      env=env, stdin=slave, stdout=slave, stderr=slave,
                                      preexec_fn=attach_terminal)
            wait_for('#{session_attached}', '1')
            for index, mode in enumerate(('dark', 'light', 'dark', 'light')):
                theme.write_text(render(palette[mode]))
                tmux('source-file', str(theme))
                if index:
                    # Full reload resets then reinstalls hooks; apply the theme again
                    # to reproduce the original ordering failure.
                    tmux('source-file', str(ROOT / 'tmux/.config/tmux/tmux.conf'))
                    tmux('source-file', str(theme))
                status = tmux('show-option', '-gqv', 'status-right')
                assert status.count(' watch ') == 1, status
                assert status.count('#{E:@dotfiles-status-right}') == 1, status
                if index == 0:
                    assert status.count('continuum_save.sh') >= 1, status
                assert palette[mode]['purple'] in tmux('show-option', '-gqv', '@dotfiles-status-right')
                assert palette[mode]['purple'] in tmux('display-message', '-p', '#{E:@dotfiles-status-right}')
                drain()
                os.write(master, b'\x02')
                read_until(b'Prefix help')
                # Escape dismisses help, then root-table input still reaches tmux.
                os.write(master, b'\x1b')
                wait_for('#{client_prefix}', '0')
                os.write(master, b'y')
                wait_for('#{@root-forwarded}', 'yes')
                tmux('set-option', '-gu', '@root-forwarded')
                drain()
                os.write(master, b'\x01')
                read_until(b'Prefix help')
                # A non-Escape key closes help and executes the prefix binding.
                os.write(master, b'x')
                wait_for('#{@replayed}', 'yes')
                wait_for('#{client_prefix}', '0')
                tmux('set-option', '-gu', '@replayed')
            print('Prefix help passed: dark/light switches, repeated reloads, single trigger, Escape, prefix replay')
        finally:
            subprocess.run(['tmux', '-S', socket, 'kill-server'], env=env, capture_output=True)
            if client is not None:
                client.wait(timeout=5)
            os.close(master)
            os.close(slave)


if __name__ == '__main__':
    main()
