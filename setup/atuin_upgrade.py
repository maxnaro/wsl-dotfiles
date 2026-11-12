"""Validate Atuin history compatibility using SQLite backups, never live writes."""
from contextlib import closing
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import tempfile
from urllib.parse import quote


def _run(executable, arguments, environment=None):
    result = subprocess.run([str(executable), *arguments], env=environment,
                            capture_output=True, timeout=60)
    if result.returncode:
        # History commands can contain credentials. Never include their output.
        raise RuntimeError(f'Atuin compatibility check failed: {arguments[0]} '
                           f'(exit {result.returncode})')
    return result.stdout


def _locations(executable, environment=None):
    info = _run(executable, ['info'], environment).decode()
    paths = {}
    for label in ('client db path', 'meta db path', 'key path'):
        match = re.search(r'^' + re.escape(label) + r':\s*(.+)$', info, re.MULTILINE)
        if match:
            paths[label] = Path(match[1].strip().strip('"')).expanduser()
    if 'client db path' not in paths:
        raise RuntimeError('Cannot determine Atuin history database location safely')
    return paths


def _backup(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    uri = 'file:' + quote(str(source.resolve()), safe='/') + '?mode=ro'
    with closing(sqlite3.connect(uri, uri=True, timeout=10)) as original:
        with closing(sqlite3.connect(destination)) as backup:
            original.backup(backup)
    destination.chmod(0o600)


def _snapshot(executable, destination):
    locations = _locations(executable)
    databases = {locations['client db path']}
    for path in locations.values():
        if path.suffix == '.db':
            databases.add(path)
        if path.parent.is_dir():
            databases.update(path.parent.glob('*.db'))
    records = []
    for index, source in enumerate(sorted(databases)):
        if not source.is_file():
            continue
        target = destination / f'{index}-{source.name}'
        _backup(source, target)
        records.append({'source': str(source), 'backup': target.name,
                        'history': source == locations['client db path']})
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination.chmod(0o700)
    metadata = destination / 'databases.json'
    metadata.write_text(json.dumps(records, indent=2) + '\n')
    metadata.chmod(0o600)
    return records


def _sandbox(directory, snapshot, records):
    directory.mkdir(mode=0o700)
    data = directory / 'data'
    data.mkdir(mode=0o700)
    config = directory / 'config'
    config.mkdir(mode=0o700)
    for record in records:
        name = 'history.db' if record['history'] else Path(record['source']).name
        _backup(snapshot / record['backup'], data / name)
    # Explicit database paths and a private home prevent config/env overrides
    # from sending candidate commands to the user's actual databases.
    settings = {
        'auto_sync': False, 'update_check': False,
        'db_path': str(data / 'history.db'),
        'record_store_path': str(data / 'records.db'),
        'key_path': str(data / 'key'), 'session_path': str(data / 'session'),
    }
    (config / 'config.toml').write_text('\n'.join(
        f'{key} = {json.dumps(value)}' for key, value in settings.items()
    ) + '\n[daemon]\nenabled = false\n')
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(('ATUIN_', 'XDG_'))}
    env.update(HOME=str(directory), ATUIN_HOME=str(data), ATUIN_CONFIG_DIR=str(config),
               ATUIN_SESSION='00000000000000000000000000000000',
               XDG_CONFIG_HOME=str(directory / '.config'),
               XDG_DATA_HOME=str(directory / '.local/share'),
               XDG_STATE_HOME=str(directory / '.local/state'),
               XDG_CACHE_HOME=str(directory / '.cache'))
    return env


def _history(executable, env, root):
    for path in _locations(executable, env).values():
        if not path.resolve().is_relative_to(root.resolve()):
            raise RuntimeError('Atuin sandbox path escaped the compatibility directory')
    # Compare UUIDs rather than logging any command text.
    output = _run(executable, ['history', 'list', '--format', '{uuid}', '--print0'], env)
    return sorted(output.split(b'\0'))


def prepare(old_executable, candidate, home, transaction_dir):
    """Back up existing databases; prove old/new/old history access on a copy."""
    if not old_executable:
        # A fresh installation has no old reader with which to prove downgrade
        # compatibility. Refuse an unrecognized pre-existing data installation.
        roots = [Path(home) / '.atuin', Path(home) / '.local/share/atuin']
        if any(root.is_dir() and any(root.rglob('*.db')) for root in roots):
            raise RuntimeError('Existing Atuin data requires the previous executable for validation')
        return
    snapshot = Path(transaction_dir) / 'atuin'
    records = _snapshot(old_executable, snapshot)
    with tempfile.TemporaryDirectory(prefix='atuin-compat-', dir=transaction_dir) as tmp:
        root = Path(tmp) / 'sandbox'
        env = _sandbox(root, snapshot, records)
        before = _history(old_executable, env, root)
        upgraded = _history(candidate, env, root)
        restored = _history(old_executable, env, root)
        if before != upgraded or before != restored:
            raise RuntimeError('Atuin upgrade/downgrade changed the history UUID set')


def verify_rollback(executable, home, transaction_dir):
    """Prove the previous reader can open a copy of current history before rollback."""
    active = Path(home) / '.local/bin/atuin'
    if not active.exists():
        active = shutil.which('atuin')
    if not active:
        raise RuntimeError('Cannot find the active Atuin executable for rollback validation')
    with tempfile.TemporaryDirectory(prefix='atuin-rollback-', dir=transaction_dir) as tmp:
        snapshot = Path(tmp) / 'snapshot'
        records = _snapshot(active, snapshot)
        root = Path(tmp) / 'sandbox'
        env = _sandbox(root, snapshot, records)
        before = _history(active, env, root)
        after = _history(executable, env, root)
        if before != after:
            raise RuntimeError('Previous Atuin version cannot preserve current history; rollback refused')
