# Dotfiles

My personal WSL / Linux configuration files, styled with CachyOS terminal utilities and fuzzy finder.

## Directory Structure

```text
dotfiles/
├── bash/
│   ├── .bashrc
│   ├── .bash_aliases
│   ├── .inputrc
│   └── .blerc
├── fish/
│   └── .config/
│       └── fish/
│           ├── config.fish
│           ├── functions/
│           └── conf.d/
├── git/
│   └── .gitconfig
├── nvim/
│   └── .config/
│       └── nvim/
├── tmux/
│   └── .config/
│       └── tmux/
│           ├── tmux.conf
│           ├── plugins/tmux-prefix-help/  # Git submodule
│           └── plugins/tmux-runcat/       # Git submodule
├── scripts/
│   └── .scripts/
│       └── auto_venv.sh
├── setup.sh
└── README.md
```

## Quick Start (New Machine / WSL Installation)

Clone this repository and run the setup script. It installs CLI tools into
`~/.local/bin` and Rust through rustup (normally `~/.cargo` and `~/.rustup`),
without sudo. Git, curl, Python 3.11+, tmux, tar with xz support, sha256sum,
and a system C linker (`cc`) must already be installed;
on Debian/Ubuntu, `build-essential` provides the C build tools.

```bash
git clone --recurse-submodules <your-repo-url> ~/dotfiles
cd ~/dotfiles
./setup.sh
source ~/.bashrc
```

### What `setup.sh` does:

Initializes Git submodules before installing tools or linking configuration.
Installs rustup noninteractively when missing, installs or updates the minimal
stable Rust toolchain, and builds the tmux prefix-help release executable
before linking the tmux configuration. Existing Rust toolchain defaults and
shell startup files are preserved by the Rust installation step.
It also builds the Rust `tmux-runcat` plugin and installs its bundled fonts.

1. **Downloads modern CLI tools, Neovim, Fish, Lazygit, Ripgrep, Zoxide & Pokémon Greeting** (`fzf`, `bat`, `eza`, `fastfetch`, `nvim`, `fish`, `lazygit`, `rg`, `zoxide`, `pokemon-greeting`) directly to `~/.local/bin`.
2. **Downloads official FZF bash keybindings and completions** to `~/.local/share/fzf/`.
3. **Symlinks dotfiles** cleanly to `$HOME`:
   - `bash/.bashrc` -> `~/.bashrc`
   - `bash/.bash_aliases` -> `~/.bash_aliases`
   - `bash/.inputrc` -> `~/.inputrc`
   - `fish/.config/fish` -> `~/.config/fish`
   - `git/.gitconfig` -> `~/.gitconfig`
   - `scripts/.scripts/auto_venv.sh` -> `~/.scripts/auto_venv.sh`
   - `nvim/.config/nvim` -> `~/.config/nvim`
   - `tmux/.config/tmux` -> `~/.config/tmux`
4. Creates automatic `.bak` backups if any files already exist in your home directory before linking.

### (Optional) GNU Stow

If you prefer using `stow`:
```bash
cd ~/dotfiles
stow -R bash
stow -R fish
stow -R git
stow -R scripts
stow -R nvim
stow -R tmux
```

### Tmux prefix help

The floating shortcut popup lives in the standalone `tmux-prefix-help`
repository, included as a submodule at
`tmux/.config/tmux/plugins/tmux-prefix-help`. See its
[README](tmux/.config/tmux/plugins/tmux-prefix-help/README.md) for installation,
behavior, and tests.

`./setup.sh` installs the toolchain and builds the plugin. After updating the
submodule in an existing installation, rebuild it before reloading tmux:

```bash
git submodule update --init --recursive
export PATH="${CARGO_HOME:-$HOME/.cargo}/bin:$PATH"
rustup toolchain install stable --profile minimal
rustup run stable cargo build --release --locked \
  --manifest-path tmux/.config/tmux/plugins/tmux-prefix-help/Cargo.toml \
  --target-dir tmux/.config/tmux/plugins/tmux-prefix-help/target
tmux source-file ~/.config/tmux/tmux.conf
```

Set `@prefix-help-delay` in `tmux.conf` to adjust the default 500 ms delay.
Commit plugin changes inside the submodule, then commit its updated pointer
in this repository.

### Tmux running cat

The cat lives in the standalone Rust `tmux-runcat` plugin, included as a
submodule at `tmux/.config/tmux/plugins/tmux-runcat`. It runs faster with typing
and sleeps after two idle seconds. The parent config places it before the
device icon, device name, and clock.

Use `set -g @runcat-size small`, `medium`, or `large` in `tmux.conf` to select
one-, two-, or three-cell cats. The default is `medium`; changes apply live.

`./setup.sh` builds the executable and fonts, installs fonts in the terminal's
host OS, and configures Windows Terminal automatically on WSL. All font build
inputs are pinned and bundled; the Rust plugin has no third-party dependencies.
On Linux, select `JetBrainsMono RunCat v3` after setup. See the
[plugin README](tmux/.config/tmux/plugins/tmux-runcat/README.md) for options,
font setup, tests, and TPM installation.

After updating the plugin submodule:

```bash
git submodule update --init --recursive
cargo build --release --locked --offline --manifest-path tmux/.config/tmux/plugins/tmux-runcat/Cargo.toml
bash tmux/.config/tmux/plugins/tmux-runcat/fonts/setup.sh
tmux source-file ~/.config/tmux/tmux.conf
```

Commit plugin changes in its repository, then commit its updated submodule
pointer in this repository.
