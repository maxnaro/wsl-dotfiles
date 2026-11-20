"""Activate My Time Has Come once, preserving local Claude and mthc settings."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


def executable(name, home):
    local = home / '.local/bin' / name
    return shutil.which(name) or (str(local) if os.access(local, os.X_OK) else None)


def configure(home):
    if not executable('claude', home):
        return

    directory = home / '.claude'
    if Path(os.environ.get('CLAUDE_CONFIG_DIR') or directory).resolve() != directory.resolve():
        print('Skipping mthc activation: upstream requires the default Claude config directory.', file=sys.stderr)
        return

    settings = directory / 'settings.json'
    config = home / '.config/mthc/config.toml'
    if config.exists() or config.is_symlink():
        return
    if settings.is_symlink():
        print('Skipping mthc activation: Claude settings.json is a symlink.', file=sys.stderr)
        return

    original = settings.read_bytes()
    parsed = json.loads(original)
    commands = [(parsed.get('statusLine') or {}).get('command', '')]
    for event in ('PreToolUse', 'PostToolBatch'):
        commands.extend(hook.get('command', '') for group in parsed.get('hooks', {}).get(event, [])
                        for hook in group.get('hooks', []))
        commands.extend(hook.get('command', '') for hook in parsed.get(event, []))
    if any(re.search(r'(?:^|/)mthc(?:\.js)?\s+(?:statusline|hook)-shim\s*$', command)
           for command in commands if isinstance(command, str)):
        print('Skipping mthc activation: existing shims have no mthc config. Run mthc doctor.', file=sys.stderr)
        return

    mthc = executable('mthc', home)
    if not mthc:
        raise ValueError('mthc executable missing after tool installation')
    command = mthc if re.fullmatch(r'[\w./+-]+', mthc, flags=re.ASCII) else 'mthc'
    with tempfile.TemporaryDirectory(prefix='.mthc-activation-', dir=directory) as stage:
        backup = Path(stage) / 'settings.json'
        shutil.copy2(settings, backup)
        try:
            subprocess.run([mthc, 'install'], check=True, env=dict(os.environ, MTHC_INSTALL_COMMAND=command))
        except (OSError, subprocess.CalledProcessError):
            os.replace(backup, settings)
            config.unlink(missing_ok=True)
            raise


if __name__ == '__main__':
    try:
        configure(Path.home())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(f'mthc activation: {error}') from error
