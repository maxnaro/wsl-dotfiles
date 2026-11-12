"""Candidate validation in an isolated CI home; never run the full setup script."""
import argparse
import json
import os
from pathlib import Path
import pwd
import re
import runpy
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
    """Resolve specs without startup, pre-clone locked commits, then test real startup."""
    config = Path(os.environ['XDG_CONFIG_HOME']) / 'nvim'
    lock_path = config / 'lazy-lock.json'
    original_lock = lock_path.read_bytes()
    lock = json.loads(original_lock)
    directory = Path(os.environ['XDG_DATA_HOME']) / 'nvim/lazy'

    def clone(name, url):
        if name not in lock or not re.fullmatch(r'[0-9a-f]{40}', lock[name]['commit']):
            raise AssertionError(f'{name}: active plugin needs an immutable lock commit')
        checkout = directory / name
        if not checkout.exists():
            run('git', 'clone', '--quiet', '--filter=blob:none', '--no-checkout', url, checkout)
        present = subprocess.run(['git', '-C', str(checkout), 'cat-file', '-e', lock[name]['commit'] + '^{commit}'],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if present.returncode:
            run('git', '-C', checkout, 'fetch', '--quiet', '--depth=1', 'origin', lock[name]['commit'])
        run('git', '-C', checkout, 'checkout', '--quiet', '--detach', lock[name]['commit'])
        actual = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], text=True).strip()
        if actual != lock[name]['commit']:
            raise AssertionError(f'{name}: expected {lock[name]["commit"]}, got {actual}')

    clone('lazy.nvim', 'https://github.com/folke/lazy.nvim.git')
    clone('LazyVim', 'https://github.com/LazyVim/LazyVim.git')
    lazy_config = config / 'lua/config/lazy.lua'
    lazy_config.write_text(lazy_config.read_text().replace('install = { colorscheme =',
                                                          'install = { missing = false, colorscheme ='))
    # External language servers, formatters, and grammars are outside the theme/notebook
    # checks. Keep plugin configuration active while suppressing their live installers.
    (config / 'lua/plugins/zz_ci.lua').write_text('''return {
  { "mason-org/mason.nvim", opts = function(_, opts) opts.ensure_installed = {} end },
  { "mason-org/mason-lspconfig.nvim", opts = function(_, opts) opts.ensure_installed = {} end },
  { "neovim/nvim-lspconfig", opts = function(_, opts) opts.servers = {} end },
}
''')
    active_path = config / 'ci-active-plugins.json'
    resolver = config / 'ci-resolve.lua'
    resolver.write_text('''vim.o.loadplugins = true
vim.opt.rtp:prepend(vim.fn.stdpath("data") .. "/lazy/lazy.nvim")
vim.opt.rtp:prepend(vim.fn.stdpath("data") .. "/lazy/LazyVim")
local loader = require("lazy.core.loader")
loader.setup = function() require("lazy.core.plugin").load() end
loader.startup = function() end
require("config.lazy")
local plugins = {}
for name, plugin in pairs(require("lazy.core.config").plugins) do
  plugins[name] = { url = plugin.url, dir = plugin.dir }
end
vim.fn.writefile({vim.json.encode(plugins)}, vim.fn.stdpath("config") .. "/ci-active-plugins.json")
vim.cmd("qa!")
''')
    run('nvim', '--headless', '-u', 'NONE', '-l', resolver, timeout=60)
    active = json.loads(active_path.read_text())
    if not isinstance(active, dict) or 'LazyVim' not in active:
        raise AssertionError('Resolver did not load the active LazyVim specification')
    for name, spec in active.items():
        clone(name, spec['url'])
    if lock_path.read_bytes() != original_lock:
        raise AssertionError('Spec resolution changed lazy-lock.json')
    instrumentation = config / 'ci-errors.lua'
    instrumentation.write_text('''vim.g.ci_errors = {}
local function record(message)
  local errors = vim.g.ci_errors
  errors[#errors + 1] = type(message) == "string" and message or vim.inspect(message)
  vim.g.ci_errors = errors
end
local lazy = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
vim.opt.rtp:prepend(lazy)
local util = require("lazy.core.util")
local original = util.error
util.error = function(message, ...) record(message); return original(message, ...) end
local notify = vim.notify
vim.notify = function(message, level, ...)
  if level == vim.log.levels.ERROR then record(message) end
  return notify(message, level, ...)
end
''')
    probe = ('lua local ok, failure = xpcall(function() '
             'local ready = vim.wait(180000, function() '
             'local present, ts = pcall(require, "nvim-treesitter"); if not present then return false end; '
             'local installed = ts.get_installed(); '
             'for _, name in ipairs(LazyVim.opts("nvim-treesitter").ensure_installed or {}) do '
             'if not vim.tbl_contains(installed, name) then return false end end; return true end, 100); '
             'assert(ready, "Treesitter setup did not complete"); '
             'assert(#vim.g.ci_errors == 0, vim.inspect(vim.g.ci_errors)); '
             'assert(vim.v.errmsg == "", vim.v.errmsg) end, debug.traceback); '
             'if not ok then vim.api.nvim_err_writeln(failure); vim.cmd("cquit 1") end')
    run('nvim', '--headless', '--cmd', 'luafile ' + str(instrumentation),
        '-u', config / 'init.lua', '-c', probe, '+qa!', timeout=210)
    for name, spec in active.items():
        actual = subprocess.check_output(['git', '-C', spec['dir'], 'rev-parse', 'HEAD'], text=True).strip()
        if actual != lock[name]['commit']:
            raise AssertionError(f'{name}: startup changed its locked checkout')
    if lock_path.read_bytes() != original_lock:
        raise AssertionError('Full startup changed lazy-lock.json')


def notebook():
    # Molten writes its kernel connection file directly. A fresh CI home has not
    # run Jupyter yet, so its private runtime directory must exist first.
    from jupyter_core.paths import jupyter_runtime_dir
    home = Path.home().resolve()
    config = Path(os.environ['XDG_CONFIG_HOME']).resolve()
    runtime = Path(jupyter_runtime_dir()).resolve()
    if (home == Path(pwd.getpwuid(os.getuid()).pw_dir).resolve()
            or not runtime.is_relative_to(home) or not config.is_relative_to(home)):
        raise ValueError('CI notebook check requires HOME, config, and runtime in an isolated home')
    runtime.mkdir(parents=True, exist_ok=True, mode=0o700)
    runtime.chmod(0o700)
    script = config / 'nvim/tests/jupyter.py'
    try:
        runpy.run_path(str(script), run_name='__main__')
    except subprocess.TimeoutExpired as error:
        for label, output in (('stdout', error.stdout), ('stderr', error.stderr)):
            if output:
                text = output.decode(errors='replace') if isinstance(output, bytes) else output
                print(f'Notebook timeout {label}:\n{text}', file=sys.stderr)
        raise


def smoke():
    for shell in ('bash', 'fish'):
        initialization = subprocess.check_output(['atuin', 'init', shell], text=True)
        subprocess.run([shell, '-n'], input=initialization, text=True, check=True)
    result = subprocess.check_output(['fzf', '--filter', 'candidate-smoke'],
                                     input='other\ncandidate-smoke\n', text=True)
    if result.strip() != 'candidate-smoke':
        raise AssertionError('fzf filter did not select the candidate input')
    run('fastfetch', '--config', 'none', '--logo', 'none', '--structure', 'OS:Kernel:Shell')


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
    parser.add_argument('command', choices=('prepare', 'plugins', 'syntax', 'smoke', 'notebook'))
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
