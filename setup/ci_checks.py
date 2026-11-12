"""Candidate validation in an isolated CI home; never run the full setup script."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(*args, **kwargs):
    subprocess.run([str(arg) for arg in args], check=True, **kwargs)


def prepare(home):
    home = home.resolve()
    if home == Path.home().resolve():
        raise ValueError('CI home must differ from the runner home')
    home.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / 'setup/tools.json').read_text())
    tools = [name for name, spec in manifest.items() if 'version' in spec and 'file' not in spec]
    # Hide runner copies of manifest binaries so --upgrade cannot keep a system pin.
    bootstrap = home.parent / 'candidate-bootstrap-bin'
    bootstrap.mkdir(exist_ok=True)
    for directory in os.get_exec_path():
        source = Path(directory)
        if not source.is_dir():
            continue
        for executable in source.iterdir():
            target = bootstrap / executable.name
            if executable.name not in tools and executable.is_file() and os.access(executable, os.X_OK) and not target.exists():
                target.symlink_to(executable.resolve())
    env = dict(os.environ, HOME=str(home), PATH=f'{home}/.local/bin:{bootstrap}')
    run(sys.executable, ROOT / 'setup/install_tools.py', '--upgrade', *tools, env=env)
    for tool in tools:
        command = [str(home / '.local/bin' / tool), '-V' if tool == 'tmux' else '--version']
        output = subprocess.check_output(command, env=env, text=True, stderr=subprocess.STDOUT)
        version = manifest[tool]['version'].removeprefix('v')
        if not re.search(r'(?<![\d.])' + re.escape(version) + r'(?![\d.])', output):
            raise AssertionError(f'{tool}: expected {version}, got {output!r}')
        if Path(shutil.which(tool, path=env['PATH'])).resolve() != (home / '.local/bin' / tool).resolve():
            raise AssertionError(f'{tool}: PATH does not select the candidate binary')
    for package in ('fish', 'tmux', 'atuin', 'lazygit'):
        source = ROOT / package / '.config' / package
        destination = home / '.config' / package
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(source, target_is_directory=True)
    for name in ('.bashrc', '.bash_aliases', '.inputrc'):
        (home / name).symlink_to(ROOT / 'bash' / name)
    (home / '.config/nvim').mkdir()
    shutil.copytree(ROOT / 'nvim/.config/nvim', home / '.config/nvim', dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('.git'))
    lazy_config = home / '.config/nvim/lua/config/lazy.lua'
    text = lazy_config.read_text().replace('enabled = true, -- check for plugin updates periodically',
                                           'enabled = false, -- disabled in isolated CI')
    lazy_config.write_text(text)
    if output_path := os.environ.get('GITHUB_ENV'):
        with open(output_path, 'a') as output:
            for name, value in {'HOME': home, 'XDG_CONFIG_HOME': home / '.config',
                                'XDG_DATA_HOME': home / '.local/share',
                                'XDG_STATE_HOME': home / '.local/state',
                                'XDG_CACHE_HOME': home / '.cache',
                                'DOTFILES_NO_TMUX': '1', 'DOTFILES_NO_FISH': '1'}.items():
                output.write(f'{name}={value}\n')
        with open(os.environ['GITHUB_PATH'], 'a') as output:
            output.write(f'{home}/.local/bin\n')


def plugins():
    """Bootstrap lazy at its lock, restore plugins, then assert every locked checkout."""
    config = Path(os.environ['XDG_CONFIG_HOME']) / 'nvim'
    lock_path = config / 'lazy-lock.json'
    lock = json.loads(lock_path.read_text())
    directory = Path(os.environ['XDG_DATA_HOME']) / 'nvim/lazy'
    lazy = directory / 'lazy.nvim'
    if not lazy.exists():
        run('git', 'clone', '--filter=blob:none', '--no-checkout', 'https://github.com/folke/lazy.nvim.git', lazy)
    run('git', '-C', lazy, 'fetch', '--depth=1', 'origin', lock['lazy.nvim']['commit'])
    run('git', '-C', lazy, 'checkout', '--detach', lock['lazy.nvim']['commit'])
    # lazy's install task reads the lockfile; restore also repairs cached checkouts.
    active_path = config / 'ci-active-plugins.json'
    export = ('lua local p = {}; for name, plugin in pairs(require("lazy.core.config").plugins) do '
              'p[name] = plugin.dir end; vim.fn.writefile({vim.json.encode(p)}, '
              'vim.fn.stdpath("config") .. "/ci-active-plugins.json")')
    run('nvim', '--headless', '+Lazy! restore', '-c', export, '+qa!', timeout=600)
    if json.loads(lock_path.read_text()) != lock:
        raise AssertionError('Plugin bootstrap changed lazy-lock.json')
    for name, path in json.loads(active_path.read_text()).items():
        if name not in lock:
            raise AssertionError(f'{name}: active plugin has no lock entry')
        spec = lock[name]
        checkout = Path(path)
        actual = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], text=True).strip()
        if actual != spec['commit']:
            raise AssertionError(f'{name}: expected lock {spec["commit"]}, got {actual}')
    # Disable missing-plugin installation for all subsequent candidate tests.
    lazy_config = config / 'lua/config/lazy.lua'
    lazy_config.write_text(lazy_config.read_text().replace('install = { colorscheme =',
                                                          'install = { missing = false, colorscheme ='))


def syntax():
    tracked = subprocess.check_output(
        ['git', '-C', str(ROOT), 'ls-files', '--cached', '--recurse-submodules', '-z'])
    for name in tracked.decode().split('\0'):
        if not name:
            continue
        path = ROOT / name
        if not path.is_file():
            continue
        with path.open('rb') as source:
            first = source.read(256).splitlines()
        shebang = first[0] if first else b''
        if path.suffix == '.fish':
            run('fish', '--no-config', '-n', path)
        elif (path.name.startswith('.bash') or path.suffix == '.sh'
              or shebang in (b'#!/bin/bash', b'#!/usr/bin/env bash', b'#!/bin/sh', b'#!/usr/bin/env sh')):
            run('bash', '-n', path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'plugins', 'syntax'))
    parser.add_argument('--home', type=Path)
    args = parser.parse_args()
    if args.command == 'prepare':
        if args.home is None:
            parser.error('prepare requires --home')
        prepare(args.home)
    else:
        globals()[args.command]()


if __name__ == '__main__':
    main()
