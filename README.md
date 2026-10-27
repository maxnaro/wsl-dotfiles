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
without a speed cap and sleeps after three idle seconds. The parent config
places it before the device icon, device name, and clock. It selects the
Pet Cats skin: stretching on wake, walking/running with typing, varied pause
gestures, and lying down before sleeping with subtle breathing. The cat uses
the status foreground (cyan) and the four-cell `xlarge` preset. The three-second
idle delay gives pause gestures about 1.3 seconds to play before lying down.

Animation frames and key counts use hidden tmux session variables to avoid
full client redraws. The status format uses `#{RUNCAT_FRAME}`. Synchronized
rendering is enabled for `xterm-256color` clients to reduce flicker; this requires
a terminal with DECSET 2026 support, such as Windows Terminal 1.23.20211.0 or
newer. Detach and reattach existing clients after reloading the config to apply
that terminal feature.

Use `set -g @runcat-size small`, `medium`, `large`, or `xlarge` in `tmux.conf`
to select one-, two-, three-, or four-cell cats. The plugin defaults to `medium`;
this configuration selects `xlarge`. Changes apply live.
Use `set -g @runcat-skin classic` to switch to the original silhouette.

`./setup.sh` builds the executable and fonts, installs fonts in the terminal's
host OS, and configures Windows Terminal automatically on WSL. All font build
inputs are pinned and bundled; the Rust plugin has no third-party dependencies.
On Linux, select `JetBrainsMono RunCat v5` after setup. See the
[plugin README](tmux/.config/tmux/plugins/tmux-runcat/README.md) for options,
font setup, tests, and TPM installation.

To use a different base font during setup:

```bash
RUNCAT_BASE_FONT="$HOME/fonts/MyMono-Regular.ttf" ./setup.sh
```

Optional `RUNCAT_BOLD_FONT`, `RUNCAT_ITALIC_FONT`, and
`RUNCAT_BOLD_ITALIC_FONT` select matching faces; `RUNCAT_FONT_FAMILY` names the
patched family. Use static monospaced TrueType files, with a Nerd Font base
to retain device icons. Keep the same font files and options for reproducible
custom setup. The bundled JetBrainsMono font remains the default.

After updating the plugin submodule:

```bash
git submodule update --init --recursive
cargo build --release --locked --offline --manifest-path tmux/.config/tmux/plugins/tmux-runcat/Cargo.toml
bash tmux/.config/tmux/plugins/tmux-runcat/fonts/setup.sh
tmux source-file ~/.config/tmux/tmux.conf
```

Commit plugin changes in its repository, then commit its updated submodule
pointer in this repository.
