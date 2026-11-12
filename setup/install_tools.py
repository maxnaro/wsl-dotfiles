"""Install missing pinned tools; never overwrite working executables."""
import hashlib
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import tempfile


def download(asset, destination):
    subprocess.run(['curl', '--fail', '--show-error', '--location', '--retry', '3',
                    '--connect-timeout', '15', asset['url'], '-o', str(destination)], check=True)
    if hashlib.sha256(destination.read_bytes()).hexdigest() != asset['sha256']:
        raise ValueError(f"Checksum mismatch: {asset['url']}")


def executable_candidates(directory, tool):
    """Ignore documentation and completion files sharing an executable's name."""
    matches = []
    for path in directory.rglob(tool):
        if not path.is_file():
            continue
        with path.open('rb') as stream:
            header = stream.read(4)
        if path.stat().st_mode & 0o111 or header.startswith(b'\x7fELF'):
            matches.append(path)
    return matches


def install(tool, spec, arch, home):
    if tool in ('fzf-completion', 'fzf-key-bindings'):
        fzf = shutil.which('fzf')
        local_fzf = home / '.local/bin/fzf'
        if not fzf and os.access(local_fzf, os.X_OK):
            fzf = str(local_fzf)
        result = subprocess.run([fzf, '--version'], capture_output=True, text=True) if fzf else None
        actual = result.stdout.split()[0].removeprefix('v') if result and result.returncode == 0 and result.stdout.split() else None
        if actual != spec['version'].removeprefix('v'):
            print(f'Keeping existing {tool}: fzf version {actual or "unavailable"} differs from pin {spec["version"]}')
            return
    existing = shutil.which(tool)
    target = home / '.local/bin' / tool
    if existing or os.access(target, os.X_OK):
        executable = existing or str(target)
        result = subprocess.run([executable, '--version'], capture_output=True, text=True)
        version = (result.stdout or result.stderr).splitlines()
        print(f"Keeping {executable}: {version[0] if version else 'version unavailable'} (pin {spec['version']})")
        return
    asset = spec['assets'].get(arch, spec['assets'].get('all'))
    if asset is None:
        raise ValueError(f'No {arch} asset for {tool}')
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.dotfiles-', dir=target.parent) as stage:
        stage = Path(stage)
        archive = stage / 'archive'
        download(asset, archive)
        if 'file' in spec:
            target = home / '.local/share/fzf' / spec['file']
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(archive, target)
            return
        extracted = stage / 'extracted'
        with tarfile.open(archive) as package:
            package.extractall(extracted, filter='data')
        matches = executable_candidates(extracted, tool)
        if len(matches) != 1:
            raise ValueError(f'Expected one {tool} executable, found {len(matches)}')
        binary = matches[0]
        binary.chmod(0o755)
        subprocess.run([str(binary), '--version'], check=True, stdout=subprocess.DEVNULL)
        if tool == 'nvim':
            # Keep the runtime beside bin/nvim; avoid extracting over ~/.local.
            runtime = home / '.local/share/dotfiles' / ('nvim-' + spec['version'])
            runtime.parent.mkdir(parents=True, exist_ok=True)
            if runtime.exists():
                raise FileExistsError(f'Refusing to overwrite {runtime}')
            shutil.move(str(binary.parent.parent), runtime)
            binary = runtime / 'bin/nvim'
            target.symlink_to(binary)
        else:
            os.replace(binary, target)
        print(f'Installed {tool} {spec["version"]}')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--upgrade', nargs='+', metavar='TOOL')
    mode.add_argument('--rollback', metavar='ID')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)
    if args.dry_run and not args.upgrade:
        parser.error('--dry-run requires --upgrade TOOL...')
    arch = {'amd64': 'x86_64', 'arm64': 'aarch64'}.get(platform.machine(), platform.machine())
    if platform.system() != 'Linux' or arch not in ('x86_64', 'aarch64'):
        raise ValueError('Only Linux x86_64 and aarch64 are supported')
    manifest = json.loads(Path(__file__).with_name('tools.json').read_text())
    if args.upgrade or args.rollback:
        from upgrades import upgrade, rollback
        if args.rollback:
            rollback(args.rollback, Path.home())
        else:
            upgrade(args.upgrade, manifest, arch, Path.home(), download, args.dry_run)
        return
    for tool, spec in manifest.items():
        if tool == 'pokemon' or 'source' in spec:
            continue
        try:
            install(tool, spec, arch, Path.home())
        except Exception as error:
            raise RuntimeError(f'{tool}: {error}') from error

    for tool in ('sesh', 'atuin'):
        executable = shutil.which(tool) or str(Path.home()/'.local/bin'/tool)
        for shell in ('fish', 'bash'):
            command = ([executable, 'completion', shell] if tool == 'sesh'
                       else [executable, 'gen-completions', '--shell', shell])
            output = subprocess.run(command, check=True, capture_output=True).stdout
            directory = Path.home()/'.local/share'/('fish/vendor_completions.d' if shell == 'fish' else 'bash-completion/completions')
            directory.mkdir(parents=True, exist_ok=True)
            target = directory/(tool + ('.fish' if shell == 'fish' else ''))
            with tempfile.NamedTemporaryFile(dir=directory, delete=False) as staged:
                staged.write(output)
            os.replace(staged.name, target)


if __name__ == '__main__':
    main()
