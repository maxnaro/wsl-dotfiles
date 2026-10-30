"""Install missing pinned tools; never overwrite working executables."""
import hashlib
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


def install(tool, spec, arch, home):
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
        matches = [p for p in extracted.rglob(tool) if p.is_file()]
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


def main():
    arch = {'amd64': 'x86_64', 'arm64': 'aarch64'}.get(platform.machine(), platform.machine())
    if platform.system() != 'Linux' or arch not in ('x86_64', 'aarch64'):
        raise ValueError('Only Linux x86_64 and aarch64 are supported')
    manifest = json.loads(Path(__file__).with_name('tools.json').read_text())
    for tool, spec in manifest.items():
        if tool == 'pokemon':
            continue
        try:
            install(tool, spec, arch, Path.home())
        except Exception as error:
            raise RuntimeError(f'{tool}: {error}') from error


if __name__ == '__main__':
    main()
