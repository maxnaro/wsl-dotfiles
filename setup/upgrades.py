"""Explicit, journalled user-local upgrades. No system executables are replaced."""
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import uuid
from datetime import datetime, timezone

from install_tools import executable_candidates


def version(executable, tool):
    result = subprocess.run([str(executable), '-V' if tool == 'tmux' else '--version'],
                            check=True, capture_output=True, text=True)
    output = result.stdout + result.stderr
    match = re.search(r'''(?<![\d.])v?(\d+(?:\.\d+)+[^\s,()\'"`;:\x1b\[\]{}]*)''', output)
    if not match:
        raise ValueError(f'Cannot read {tool} version: {output.strip()}')
    return match.group(1)


def normalized(value):
    return value.removeprefix('v')


def newer(current, pinned):
    def key(value):
        match = re.fullmatch(r'(\d+(?:\.\d+)*)([a-z]?)(?:-([0-9A-Za-z.-]+))?(?:\+([0-9A-Za-z.-]+))?', normalized(value))
        if not match:
            raise ValueError(f'Cannot safely compare installed version {current} with pin {pinned}')
        numbers = tuple(map(int, match[1].split('.')))
        return numbers, match[2], match[3], match[4]
    current_key, pinned_key = key(current), key(pinned)
    current_numbers, current_letter, current_pre, current_build = current_key
    pinned_numbers, pinned_letter, pinned_pre, pinned_build = pinned_key
    width = max(len(current_numbers), len(pinned_numbers))
    current_numbers += (0,) * (width - len(current_numbers))
    pinned_numbers += (0,) * (width - len(pinned_numbers))
    if current_numbers != pinned_numbers:
        return current_numbers > pinned_numbers
    if current_letter != pinned_letter:
        return current_letter > pinned_letter
    if current_pre != pinned_pre:
        if current_pre is None or pinned_pre is None:
            return current_pre is None
        def prerelease(value):
            return tuple((0, int(part)) if part.isdigit() else (1, part) for part in value.split('.'))
        return prerelease(current_pre) > prerelease(pinned_pre)
    if current_build != pinned_build:
        raise ValueError(f'Cannot safely compare installed build {current} with pin {pinned}')
    return False


def fingerprint(path):
    if path.is_symlink():
        # A changed symlink referent is also a changed executable.
        result = {'kind': 'symlink', 'link': os.readlink(path)}
        if path.is_file():
            result['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        return result
    if path.is_file():
        return {'kind': 'file', 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'mode': path.stat().st_mode & 0o777}
    if path.exists():
        raise ValueError(f'Refusing non-file destination: {path}')
    return {'kind': 'absent'}


def save_journal(directory, journal):
    temporary = directory / 'journal.tmp'
    with temporary.open('w') as stream:
        json.dump(journal, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, directory / 'journal.json')
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def require_local(path, home):
    if not path.parent.resolve().is_relative_to(home.resolve()):
        raise ValueError(f'Refusing destination outside home: {path}')


@contextlib.contextmanager
def locked(home):
    root = home / '.local/state/dotfiles/upgrades'
    require_local(root / 'lock', home)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (root / 'lock').open('a') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError('Another dotfiles upgrade or rollback is running') from error
        yield root


def replace(source, target):
    """Publish through a sibling rename, preserving symlinks without dereferencing."""
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name('.' + target.name + '.upgrade-' + uuid.uuid4().hex)
    try:
        if source.is_symlink():
            temporary.symlink_to(os.readlink(source))
        else:
            shutil.copy2(source, temporary)
        os.replace(temporary, target)
        descriptor = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def restore(directory, journal):
    """Preflight every destination before restoring any, including crash recovery."""
    for entry in journal['entries']:
        require_local(Path(entry['target']), Path(journal['home']))
        current = fingerprint(Path(entry['target']))
        if current not in (entry['before'], entry['after']):
            raise RuntimeError(f"Rollback refused: modified destination {entry['target']}")
    for entry in journal['entries']:
        if entry['before']['kind'] == 'absent':
            continue
        backup = directory / entry['backup']
        saved = fingerprint(backup)
        expected = entry['before']
        if expected['kind'] == 'symlink':
            saved = {key: saved.get(key) for key in ('kind', 'link')}
            expected = {key: expected[key] for key in ('kind', 'link')}
        if saved != expected:
            raise RuntimeError(f'Rollback backup changed: {backup}')
    if 'atuin' in journal['tools']:
        entry = next(e for e in journal['entries'] if Path(e['target']).name == 'atuin')
        if (directory / 'atuin-old-executable').exists() and fingerprint(Path(entry['target'])) != entry['before']:
            from atuin_upgrade import verify_rollback
            verify_rollback(directory / 'atuin-old-executable', Path(entry['target']).parents[2], directory)
    journal['status'] = 'rolling_back'
    save_journal(directory, journal)
    for entry in reversed(journal['entries']):
        target = Path(entry['target'])
        if fingerprint(target) == entry['before']:
            continue
        if entry['before']['kind'] == 'absent':
            target.unlink()
        else:
            backup = directory / entry['backup']
            replace(backup, target)
    journal['status'] = 'rolled_back'
    save_journal(directory, journal)


def recover(root):
    for directory in sorted(root.iterdir()):
        journal_path = directory / 'journal.json'
        if not directory.is_dir() or not journal_path.is_file():
            continue
        journal = json.loads(journal_path.read_text())
        if journal['status'] in ('activating', 'rolling_back'):
            restore(directory, journal)
            print(f'Recovered interrupted transaction {directory.name}')


def rollback(transaction_id, home):
    if not re.fullmatch(r'[A-Za-z0-9-]+', transaction_id):
        raise ValueError('Invalid transaction ID')
    with locked(home) as root:
        directory = root / transaction_id
        journal = json.loads((directory / 'journal.json').read_text())
        if journal['status'] == 'rolled_back':
            print(f'Already rolled back {transaction_id}')
            return
        if journal['status'] not in ('complete', 'activating', 'rolling_back'):
            raise ValueError(f"Cannot roll back transaction with status {journal['status']}")
        restore(directory, journal)
        print(f'Rolled back {transaction_id}')


def select(names, manifest):
    supported = {name for name, spec in manifest.items() if 'assets' in spec and 'file' not in spec}
    supported |= {name for name, spec in manifest.items() if 'source' in spec}
    unknown = set(names) - supported
    if unknown:
        raise ValueError('Unsupported upgrade tool(s): ' + ', '.join(sorted(unknown)))
    return list(dict.fromkeys(names))


def installed(tool, home):
    target = home / '.local/bin' / tool
    # The local target takes precedence even when the caller has not refreshed PATH.
    return str(target) if os.access(target, os.X_OK) else shutil.which(tool)


def preflight_tmux():
    for command in ('cc', 'make', 'pkg-config'):
        if not shutil.which(command):
            raise RuntimeError(f'tmux build needs {command}; install system build prerequisites first')
    for library in ('libevent', 'ncurses'):
        result = subprocess.run(['pkg-config', '--exists', library], check=False)
        if result.returncode:
            raise RuntimeError(f'tmux build needs {library} development files (pkg-config {library})')


def extract(archive, directory):
    with tarfile.open(archive) as package:
        package.extractall(directory, filter='data')


def candidate(tool, spec, arch, directory, home, transaction_id, download):
    work = directory / 'stage' / tool
    work.mkdir(parents=True)
    archive = work / 'archive'
    asset = spec['source'] if 'source' in spec else spec['assets'].get(arch, spec['assets'].get('all'))
    if asset is None:
        raise ValueError(f'No {arch} asset for {tool}')
    download(asset, archive)
    extracted = work / 'extracted'
    extract(archive, extracted)
    runtime = None
    if tool == 'tmux':
        configure = list(extracted.glob('*/configure'))
        if len(configure) != 1:
            raise ValueError('Expected one tmux source configure script')
        source = configure[0].parent
        runtime = home / '.local/share/dotfiles' / f'tmux-{normalized(spec["version"])}-{transaction_id}'
        subprocess.run(['./configure', '--prefix=' + str(runtime)], cwd=source, check=True)
        subprocess.run(['make', '-j2'], cwd=source, check=True)
        destdir = work / 'destdir'
        subprocess.run(['make', 'install', 'DESTDIR=' + str(destdir)], cwd=source, check=True)
        runtime_source = destdir / runtime.relative_to('/')
        binary = runtime_source / 'bin/tmux'
    else:
        matches = executable_candidates(extracted, tool)
        if len(matches) != 1:
            raise ValueError(f'Expected one {tool} executable, found {len(matches)}')
        binary = matches[0]
        binary.chmod(0o755)
        if tool == 'nvim':
            if binary.parent.name != 'bin' or not (binary.parent.parent / 'share/nvim/runtime').is_dir():
                raise ValueError('Neovim archive is missing its runtime')
            runtime_source = binary.parent.parent
            runtime = home / '.local/share/dotfiles' / f'nvim-{normalized(spec["version"])}-{transaction_id}'
    actual = version(binary, tool)
    if actual != normalized(spec['version']):
        raise ValueError(f'{tool}: expected {spec["version"]}, candidate reports {actual}')
    return binary, (runtime_source, runtime) if runtime is not None else None


def add_entry(directory, journal, target, source):
    require_local(target, Path(journal['home']))
    before = fingerprint(target)
    number = str(len(journal['entries']))
    backup = 'backups/' + number
    if before['kind'] != 'absent':
        destination = directory / backup
        destination.parent.mkdir(parents=True, exist_ok=True)
        if target.is_symlink():
            destination.symlink_to(os.readlink(target))
        else:
            shutil.copy2(target, destination)
    # Staging symlinks may point at a runtime not published yet. Its content hash
    # is recorded after publication, before activation begins.
    journal['entries'].append({'target': str(target), 'source': str(source),
                               'backup': backup, 'before': before, 'after': fingerprint(source)})


def upgrade(names, manifest, arch, home, download, dry_run=False):
    names = select(names, manifest)
    if dry_run:
        return perform_upgrade(names, manifest, arch, home, download, True, None)
    with locked(home) as root:
        recover(root)
        return perform_upgrade(names, manifest, arch, home, download, False, root)


def perform_upgrade(names, manifest, arch, home, download, dry_run, root):
    selected = []
    existing = {}
    for tool in names:
        executable = installed(tool, home)
        current = version(executable, tool) if executable else None
        pinned = normalized(manifest[tool]['version'])
        existing[tool] = executable
        if current == pinned or (current and newer(current, pinned)):
            print(f'Keeping {tool} {current} (pin {pinned})')
        else:
            selected.append(tool)
            print(f'{"Would upgrade" if dry_run else "Upgrade"} {tool}: {current or "missing"} -> {pinned}')
    if 'tmux' in selected:
        preflight_tmux()
    if dry_run or not selected:
        return None
    transaction_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]
    directory = root / transaction_id
    directory.mkdir(mode=0o700)
    journal = {'status': 'staging', 'tools': selected, 'home': str(home), 'entries': []}
    save_journal(directory, journal)
    runtimes = []
    activation_started = False
    try:
        for tool in selected:
            spec = manifest[tool]
            binary, runtime = candidate(tool, spec, arch, directory, home, transaction_id, download)
            if tool == 'atuin':
                from atuin_upgrade import prepare
                prepare(existing[tool], binary, home, directory)
                if existing[tool]:
                    shutil.copy2(existing[tool], directory / 'atuin-old-executable')
            if runtime:
                runtimes.append(runtime)
                link = directory / 'stage' / tool / 'link'
                link.symlink_to(runtime[1] / binary.relative_to(runtime[0]))
                source = link
            else:
                source = binary
            add_entry(directory, journal, home / '.local/bin' / tool, source)
            if tool in ('atuin', 'sesh'):
                for shell in ('fish', 'bash'):
                    command = ([str(binary), 'completion', shell] if tool == 'sesh'
                               else [str(binary), 'gen-completions', '--shell', shell])
                    output = subprocess.run(command, check=True, capture_output=True).stdout
                    if not output.strip():
                        raise ValueError(f'{tool}: empty {shell} completions')
                    completion = directory / 'stage' / tool / ('completion.' + shell)
                    completion.write_bytes(output)
                    relative = 'fish/vendor_completions.d' if shell == 'fish' else 'bash-completion/completions'
                    target = home / '.local/share' / relative / (tool + ('.fish' if shell == 'fish' else ''))
                    add_entry(directory, journal, target, completion)
            if tool == 'fzf':
                for companion in ('fzf-completion', 'fzf-key-bindings'):
                    companion_spec = manifest[companion]
                    if normalized(companion_spec['version']) != normalized(spec['version']):
                        raise ValueError('fzf binary and shell integration pins differ')
                    source = directory / 'stage/fzf' / companion_spec['file']
                    download(companion_spec['assets']['all'], source)
                    subprocess.run(['bash', '-n', str(source)], check=True)
                    add_entry(directory, journal, home / '.local/share/fzf' / companion_spec['file'], source)
        # All downloads, builds, version checks, and data checks succeeded.
        for source, destination in runtimes:
            require_local(destination, home)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                raise FileExistsError(destination)
            shutil.move(str(source), destination)
        for entry in journal['entries']:
            entry['after'] = fingerprint(Path(entry['source']))
            if fingerprint(Path(entry['target'])) != entry['before']:
                raise RuntimeError(f"Destination changed during staging: {entry['target']}")
        journal['status'] = 'activating'
        save_journal(directory, journal)
        activation_started = True
        for entry in journal['entries']:
            if fingerprint(Path(entry['target'])) != entry['before']:
                raise RuntimeError(f"Destination changed during activation: {entry['target']}")
            replace(Path(entry['source']), Path(entry['target']))
        journal['status'] = 'complete'
        save_journal(directory, journal)
    except BaseException:
        if activation_started:
            restore(directory, journal)
        else:
            journal['status'] = 'failed'
            save_journal(directory, journal)
        raise
    print(f'Upgrade complete. Rollback: ./setup.sh --rollback {transaction_id}')
    return transaction_id
