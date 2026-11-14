#!/usr/bin/env python3
"""Install the shared shell manifest without replacing Fish's state directory."""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile


def link_shell(module: Path, home: Path) -> None:
    module = module.resolve()
    home = home.resolve()
    manifest = json.loads((module / 'manifest.json').read_text())
    if manifest.get('version') != 1:
        raise ValueError('Unsupported shell manifest version')
    profiles = {'bash', 'fish', 'shared', 'atuin', 'lazygit'}
    files = [entry for entry in manifest['files'] if profiles.intersection(entry['profiles'])]
    fish = home / '.config/fish'
    for entry in files:
        source, target = Path(entry['source']), Path(entry['target'])
        if source.is_absolute() or target.is_absolute() or '..' in source.parts or '..' in target.parts:
            raise ValueError('Invalid shell manifest path')
        source_file = module / source
        if not source_file.resolve().is_relative_to(module):
            raise ValueError('Shell manifest source escapes module')
        if not source_file.is_file():
            raise FileNotFoundError(source_file)
        parent = home / target.parent
        # A linked Fish directory is deliberately replaced before installing;
        # validate its parent, while other linked ancestors must remain in HOME.
        if fish.is_symlink() and (parent == fish or fish in parent.parents):
            parent = fish.parent
        if not parent.resolve().is_relative_to(home):
            raise ValueError(f'Shell target escapes home: {target}')

    # Older setups linked this entire directory. Copy its contents before
    # replacing the link so local.fish, fish_variables and other state survive.
    if fish.is_symlink() and fish.is_dir():
        original_link = os.readlink(fish)
        with tempfile.TemporaryDirectory(prefix='.fish-migrate-', dir=fish.parent) as stage:
            copy = Path(stage) / 'fish'
            shutil.copytree(fish, copy, symlinks=False)
            fish.unlink()
            try:
                copy.rename(fish)
            except BaseException:
                fish.symlink_to(original_link)
                raise

    elif fish.is_symlink():
        backup = Path(tempfile.mkdtemp(prefix='fish.bak.', dir=fish.parent))
        fish.rename(backup / 'original')

    for entry in files:
        source = module / entry['source']
        target = home / entry['target']
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_symlink() and target.resolve() == source.resolve():
            continue
        backup = None
        if target.exists() or target.is_symlink():
            backup = Path(tempfile.mkdtemp(prefix=target.name + '.bak.', dir=target.parent))
            target.rename(backup / 'original')
        try:
            target.symlink_to(source)
        except OSError:
            if backup is not None:
                (backup / 'original').rename(target)
                backup.rmdir()
            raise
        print(f'Linked {target} -> {source}')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit('Usage: link_shell.py MODULE HOME')
    link_shell(Path(sys.argv[1]), Path(sys.argv[2]))
