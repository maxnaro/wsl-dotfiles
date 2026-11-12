"""Measure terminal echo latency and redraw traffic through isolated PTYs.

Run with ``python3 tests/live_terminal_latency.py``. Add ``--socket PATH`` to
also test an existing tmux server using a temporary session and separate client.
Existing sessions and clients are never selected or sent input. This measures
the Linux PTY path, not Windows Terminal's display or physical keyboard latency.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import shlex
import statistics
import struct
import subprocess
import tempfile
import termios
import time

ROOT = Path(__file__).resolve().parents[1]
ECHO = """
import os, tty
tty.setraw(0)
os.write(1, (b'abcdefghijklmnopqrstuvwxyz0123456789' * 5 + b'\\r\\n') * 45)
count = 0
os.write(1, b'PERF-00000000')
while True:
    data = os.read(0, 65536)
    if not data:
        break
    count += len(data)
    os.write(1, ('\\rPERF-%08d' % count).encode())
"""


def measure(label, samples, socket=None, configured=False, private=False):
    with tempfile.TemporaryDirectory(prefix='dotfiles-latency-') as temporary:
        home = Path(temporary)
        env = dict(os.environ, TERM='xterm-256color', DOTFILES_NO_TMUX='1')
        env.pop('TMUX', None)
        env.pop('TMUX_PANE', None)
        if private:
            socket = str(home / 'tmux.sock')
            env.update(HOME=temporary, XDG_CONFIG_HOME=str(home / '.config'),
                       XDG_STATE_HOME=str(home / '.local/state'),
                       XDG_CACHE_HOME=str(home / '.cache'),
                       XDG_DATA_HOME=str(home / '.local/share'))
            (home / '.config').mkdir()
            (home / '.config/tmux').symlink_to(ROOT / 'tmux/.config/tmux')
        session = f'latency-probe-{os.getpid()}'
        base = ['tmux', '-S', socket] if socket else None
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 55, 208, 0, 0))
        client = None
        created = False

        def tmux(*args):
            return subprocess.run(base + list(args), env=env, check=True,
                                  capture_output=True, timeout=10)

        def read_until(marker, timeout=5):
            output = b''
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if select.select([master], [], [], max(0, deadline - time.monotonic()))[0]:
                    output += os.read(master, 65536)
                    if marker in output:
                        return len(output)
            raise TimeoutError(f'{label}: missing {marker!r}')

        def drain(duration):
            deadline = time.monotonic() + duration
            while time.monotonic() < deadline:
                if select.select([master], [], [], max(0, deadline - time.monotonic()))[0]:
                    os.read(master, 65536)

        def attach_terminal():
            os.setsid()
            fcntl.ioctl(slave, termios.TIOCSCTTY, 0)

        try:
            command = ['/usr/bin/python3', '-u', '-c', ECHO]
            if base:
                tmux(*(['-f', '/dev/null'] if private else []),
                     'new-session', '-d', '-s', session, '-x', '208', '-y', '55',
                     shlex.join(command))
                created = True
                if configured:
                    tmux('source-file', str(ROOT / 'tmux/.config/tmux/tmux.conf'))
                command = base + ['attach-session', '-t', session]
            client = subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave,
                                      env=env, preexec_fn=attach_terminal)
            read_until(b'PERF-00000000')
            drain(0.3)
            timings = []
            output_bytes = 0
            for count in range(1, samples + 1):
                start = time.perf_counter()
                os.write(master, b'x')
                output_bytes += read_until(f'PERF-{count:08d}'.encode())
                timings.append((time.perf_counter() - start) * 1000)
                time.sleep(0.01)
            bursts = []
            for count in range(1, 6):
                drain(0.05)
                start = time.perf_counter()
                os.write(master, b'x' * 500)
                read_until(f'PERF-{samples + count * 500:08d}'.encode())
                bursts.append((time.perf_counter() - start) * 1000)
            timings.sort()
            return dict(case=label, samples=samples,
                        median_ms=round(statistics.median(timings), 3),
                        p95_ms=round(timings[min(samples - 1, int(samples * .95))], 3),
                        max_ms=round(max(timings), 3),
                        bytes_per_key=round(output_bytes / samples),
                        burst_500_ms=round(statistics.median(bursts), 3))
        finally:
            if client is not None:
                client.terminate()
                try:
                    client.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    client.kill()
                    client.wait(timeout=5)
            os.close(master)
            os.close(slave)
            if created:
                subprocess.run(base + ['kill-session', '-t', session], env=env,
                               capture_output=True, timeout=10)
            if private:
                subprocess.run(base + ['kill-server'], env=env,
                               capture_output=True, timeout=10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--socket', help='also measure an existing tmux server')
    parser.add_argument('--samples', type=int, default=160)
    args = parser.parse_args()
    if args.samples < 1:
        parser.error('--samples must be positive')
    cases = [('direct PTY', {}), ('tmux without config', dict(private=True)),
             ('tmux with dotfiles', dict(private=True, configured=True))]
    if args.socket:
        cases.append(('existing tmux', dict(socket=args.socket)))
    for label, options in cases:
        print(json.dumps(measure(label, args.samples, **options)), flush=True)


if __name__ == '__main__':
    main()
