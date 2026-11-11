"""Exercise tmux's cached terminal colours through a private attached client.

Run explicitly with ``python3 tests/live_tmux_theme.py``. The fake outer
terminal answers OSC 10/11 queries; no real tmux server or terminal is touched.
"""
import fcntl
import json
import os
from pathlib import Path
import pty
import re
import runpy
import select
import shlex
import struct
import subprocess
import tempfile
import termios
import threading
import time

ROOT = Path(__file__).resolve().parents[1]


class FakeTerminal:
    """Answer tmux's outer-terminal colour queries on the PTY master."""

    def __init__(self, master, dark, light):
        self.master = master
        self.colours = {'dark': dark, 'light': light}
        self.active = 'dark'
        self.delayed_mode = None
        self.delayed_at = None
        self.query_count = {10: 0, 11: 0}
        self._buffer = bytearray()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._pump, daemon=True)
        self._thread.start()

    def switch(self, mode, delay_after_next_query=False):
        with self._lock:
            if delay_after_next_query:
                # Keep returning the previous response for a short interval
                # after the first refresh request. A later retry sees new data.
                self.delayed_mode = mode
                self.delayed_at = None
            else:
                self.active = mode
                self.delayed_mode = None
                self.delayed_at = None

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=2)

    @staticmethod
    def _osc_colour(code, colour):
        channels = [colour[index:index + 2].lower() * 2 for index in (1, 3, 5)]
        return f'\x1b]{code};rgb:{channels[0]}/{channels[1]}/{channels[2]}\x1b\\'.encode()

    def _answer(self, code):
        with self._lock:
            self.query_count[code] += 1
            if self.delayed_mode and self.delayed_at is None:
                self.delayed_at = time.monotonic() + 0.55
            if self.delayed_mode and self.delayed_at is not None and time.monotonic() >= self.delayed_at:
                self.active = self.delayed_mode
                self.delayed_mode = None
                self.delayed_at = None
            colour_key = 'fg' if code == 10 else 'bg'
            colour = self.colours[self.active][colour_key]
        os.write(self.master, self._osc_colour(code, colour))

    def _pump(self):
        # Tmux may wrap terminal queries in its DCS passthrough framing. The
        # OSC sequence remains visible after collapsing doubled ESC bytes.
        query = re.compile(rb'\x1b\]([0-9]{1,2});\?\x07|\x1b\]([0-9]{1,2});\?\x1b\\')
        while not self._stop.is_set():
            try:
                ready, _, _ = select.select([self.master], [], [], 0.05)
                if not ready:
                    continue
                data = os.read(self.master, 65536)
            except (OSError, ValueError):
                return
            self._buffer.extend(data.replace(b'\x1b\x1b', b'\x1b'))
            # Keep unrelated screen output bounded while preserving partial OSCs.
            if len(self._buffer) > 131072:
                del self._buffer[:-4096]
            while True:
                match = query.search(self._buffer)
                if not match:
                    break
                code = int(match.group(1) or match.group(2))
                del self._buffer[:match.end()]
                if code in self.query_count:
                    self._answer(code)


def main():
    with tempfile.TemporaryDirectory(prefix='dotfiles-tmux-theme-') as temporary:
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
        palettes = json.loads((ROOT / 'themes/chocolatier.json').read_text())
        refresh = runpy.run_path(str(ROOT / 'scripts/.scripts/dotfiles-theme'))['refresh_tmux_colours']
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 120, 0, 0))
        terminal = FakeTerminal(master, palettes['dark'], palettes['light'])
        client = None
        windows = []
        probe = home / 'probe.py'
        probe.write_text(
            'import json, os, select, sys, time\n'
            'import tty\n'
            'fd = sys.stdin.fileno()\n'
            'tty.setraw(fd)\n'
            'os.write(sys.stdout.fileno(), b"\\x1b]10;?\\x1b\\\\")\n'
            'os.write(sys.stdout.fileno(), b"\\x1b]11;?\\x1b\\\\")\n'
            'data = bytearray()\n'
            'deadline = time.monotonic() + 4\n'
            'while time.monotonic() < deadline and data.count(b"\\x1b\\\\") < 2:\n'
            '    ready, _, _ = select.select([fd], [], [], 0.05)\n'
            '    if ready: data.extend(os.read(fd, 4096))\n'
            'open(sys.argv[1], "w").write(data.decode("latin1"))\n'
        )

        def tmux(*args):
            return subprocess.run(['tmux', '-S', socket, *args], env=env, check=True,
                                  capture_output=True, text=True, timeout=10).stdout.strip()

        def attach_terminal():
            os.setsid()
            fcntl.ioctl(slave, termios.TIOCSCTTY, 0)

        def probe_colours():
            result = home / f'probe-{len(windows)}.txt'
            command = 'python3 {} {}'.format(shlex.quote(str(probe)), shlex.quote(str(result)))
            pane = tmux('new-window', '-d', '-P', '-F', '#{pane_id}', command)
            windows.append(pane)
            deadline = time.monotonic() + 6
            while time.monotonic() < deadline and not result.exists():
                time.sleep(0.05)
            assert result.exists(), 'probe pane did not receive terminal colours'
            raw = result.read_text()
            return raw

        def expected(colour):
            return 'rgb:{}/{}/{}'.format(*(colour[index:index + 2].lower() * 2 for index in (1, 3, 5)))

        def assert_probe(mode):
            raw = probe_colours()
            assert expected(palettes[mode]['fg']) in raw, f'{mode} foreground missing: {raw!r}'
            assert expected(palettes[mode]['bg']) in raw, f'{mode} background missing: {raw!r}'

        try:
            tmux('-f', '/dev/null', 'new-session', '-d', '-s', 'test', '/bin/sleep 120')
            client = subprocess.Popen(['tmux', '-S', socket, 'attach-session', '-t', 'test'],
                                      env=env, stdin=slave, stdout=slave, stderr=slave,
                                      preexec_fn=attach_terminal)
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                if tmux('display-message', '-p', '#{session_attached}') == '1':
                    break
                time.sleep(0.05)
            else:
                raise AssertionError('private tmux client did not attach')
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and (terminal.query_count[10] == 0 or terminal.query_count[11] == 0):
                time.sleep(0.05)
            assert terminal.query_count[10] and terminal.query_count[11], 'tmux startup colour queries were not answered'
            assert_probe('dark')

            # Changing the fake terminal alone does not invalidate tmux's cache.
            terminal.switch('light')
            assert_probe('dark')

            client_tty = tmux('display-message', '-p', '#{client_tty}')
            before = dict(terminal.query_count)
            terminal.switch('dark')
            terminal.switch('light', delay_after_next_query=True)
            refresh({client_tty: client.pid})
            assert terminal.query_count[10] >= before[10] + 3, 'foreground refresh retries were not sent'
            assert terminal.query_count[11] >= before[11] + 3, 'background refresh retries were not sent'
            assert_probe('light')

            before = dict(terminal.query_count)
            terminal.switch('dark')
            refresh({client_tty: client.pid})
            assert terminal.query_count[10] >= before[10] + 3, 'reverse foreground refresh retries were not sent'
            assert terminal.query_count[11] >= before[11] + 3, 'reverse background refresh retries were not sent'
            assert_probe('dark')
            print('tmux terminal colours passed: stale cache, delayed refresh retries, dark -> light -> dark')
        finally:
            for pane in windows:
                subprocess.run(['tmux', '-S', socket, 'kill-pane', '-t', pane], env=env,
                               capture_output=True, timeout=5)
            subprocess.run(['tmux', '-S', socket, 'kill-server'], env=env,
                           capture_output=True, timeout=5)
            terminal.stop()
            if client is not None:
                try:
                    client.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    client.terminate()
                    client.wait(timeout=3)
            os.close(master)
            os.close(slave)


if __name__ == '__main__':
    main()
