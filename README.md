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
Emacs 29.1+, and a system C linker (`cc`) must already be installed;
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
stow -R lazygit
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
without a speed cap and sleeps within eight idle seconds. The parent config
lets it roam through the free space between the window list and right status,
turning around at the edges and resting where it stops. It selects the
Pet Cats skin with an 18% chance per running second to start an OIIA-style
spin. Set `@runcat-spin-chance 0` to disable spinning, or `@runcat-roam off`
and add `#{@runcat-frame}` to a status segment for a stationary cat.
The cat uses the four-cell `xlarge` preset and stays cyan in all actions and
both directions. Change `@runcat-color` to a literal tmux colour, or `inherit`
to use the status foreground. Roaming and gait share a smoothed cadence;
changing between walk and run preserves the stride, and wide terminals do
not increase travel speed.

After typing pauses, the cat eases into a slow walk for up to two seconds.
Idle/sitting lasts 0.5 seconds, meowing one second, and grooming/scratching
three seconds, followed by 0.6 seconds of lying down. It then sleeps rather
than holding a short gesture until the eight-second maximum.

The plugin measures available space for each client and adapts to terminal
resizes and window names. Keep the stationary cat placeholder out of the status
format while roaming to avoid drawing it twice. Synchronized rendering is
enabled for `xterm-256color` clients to reduce flicker. Detach and reattach
existing clients after reloading the config to apply that terminal feature.

Use `set -g @runcat-size small`, `medium`, `large`, or `xlarge` in `tmux.conf`
to select one-, two-, three-, or four-cell cats. The plugin defaults to `medium`;
this configuration selects `xlarge`. Changes apply live.
Use `set -g @runcat-skin classic` to switch to the original silhouette.

`./setup.sh` builds the executable and fonts, installs fonts in the terminal's
host OS, and configures Windows Terminal automatically on WSL. All font build
inputs are pinned and bundled; the Rust plugin has no third-party dependencies.
On Linux, select `JetBrainsMono RunCat v7` after setup. See the
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

### Editor and LazyGit styling

LazyVim uses a transparent, compact status line with file changes, Git details,
diagnostics, and cursor position. Its text, syntax accents, selection surfaces, and LazyGit borders match the
terminal's Chocolatier palette. Buffer tabs are disabled; native tab pages remain available. In LazyGit, Escape dismisses dialogs and subviews,
then quits from the top level; `q` also quits. Existing leader shortcuts remain.

Setup links `lazygit/.config/lazygit/config.yml` to `~/.config/lazygit/config.yml`,
backing up an existing file. For an existing installation, use `stow -R lazygit`
after moving any existing LazyGit config aside. Restart Neovim and LazyGit to
load their changes; reload tmux with `tmux source-file ~/.config/tmux/tmux.conf`.

### Neovim AI autocomplete

AI autocomplete starts off in every Neovim session. Press Space `au` to toggle
Copilot across buffers. Enable it first, then run `:Copilot auth` to sign in.
Explicit `:Copilot` commands also load the plugin. Lazy installs the plugin;
its native language server downloads on first use and requires Copilot access.

Tab accepts the visible regular completion first, advances snippet placeholders,
then accepts visible AI ghost text, otherwise inserting normal Tab. Shift-Tab
selects the previous completion or snippet placeholder. AI text hides while the
regular completion menu is open. Alt-`]` / Alt-`[` cycle AI suggestions and
Ctrl-`]` dismisses them; Escape retains its normal Insert-mode behavior.

The toggle stops Copilot across buffers without persisting its state. Chat,
assistant terminals, and next-edit suggestions are not enabled.

Pet Cats pause gestures last up to three seconds for grooming and scratching,
one second for meowing, and half a second for standing idle or sitting.
The idle setting is an upper limit: the cat lies down and sleeps sooner when
its gesture finishes. With an eight-second limit, sleep begins after about
5.6, 3.6, or 3.1 seconds respectively.

### Neovim navigation and tools

Space is the leader key. Search keeps its existing layout and diagnostics and
inlay hints retain their detail. The compact status line colors the mode letter
and shows `REC @register` while recording a macro.

| Shortcut | Action |
| --- | --- |
| `H` / `L`, `[b` / `]b` | Previous / next buffer |
| `Space ,` | Buffer picker |
| `Space bb` | Alternate buffer |
| `Space gg`, `Space lg` | LazyGit at the project Git root |
| `Space gG` | LazyGit at Neovim's working directory |
| `Space gf` | Current-file Git history |
| `Space lz` | Plugin manager |
| `Space cl` | LSP info |
| `Space cLh/j/s/w` | Live Share host / join / stop / workspace |
| `Space qs`, `Space qS` | Restore project session / select session |
| `Space sr` | Search and replace |
| `Space gh` | Git hunk actions (Which-Key menu) |
| `Space wm`, `Space uz` | Zoom window / zen mode |

Alt-h/j/k/l navigate editor splits and tmux panes from Normal, Insert, Visual,
and terminal modes. Navigation leaves input/selection mode; picker-local keys
remain available, including Alt-h to toggle hidden files. Alt-j/k no longer move
lines. The old Live Share aliases and `Space l` plugin-manager binding are removed.
LazyGit uses Snacks; the former plugin's `:LazyGit*` commands are retired.

### Emacs and Doom

Doom uses a local Chocolatier theme matching Neovim and the terminal, with a
ViMax-style EMax block-letter banner. Terminal backgrounds inherit the terminal's
background; graphical frames use warm brown. The existing modeline layout and
dashboard actions are preserved. Restart Emacs after updating the configuration;
`M-x doom/reload-theme` reloads theme edits. No additional packages are needed.

Install Emacs through your system package manager first (for example,
`sudo apt install emacs-nox` on Ubuntu for terminal use). Setup requires
Emacs 29.1 or newer and does not install system packages.

Personal Doom configuration lives in `doom/.config/doom/`. Setup links it to
`~/.config/doom`, backing up existing configuration, then bootstraps Doom in
`~/.config/emacs`. Fresh installations use core revision
`59cdaa32ae933469bb6a1fb3cadee8a988c15968` and its pinned submodules.
Existing Doom installations retain their revision and run `doom sync`.
Unrelated Emacs configurations must be moved aside before bootstrap.
Framework code, installed packages, and caches remain outside this repository.

For manual linking, move any existing personal configuration aside and run
`stow -R doom`. With Emacs installed, run `bash setup/install_doom.sh` to
bootstrap Doom without running the full setup. Bash and Fish expose `doom`
on PATH after restarting the shell.

Run `doom sync` after changing `init.el` or `packages.el`; restart Emacs after
configuration changes. Use `doom doctor` to inspect missing optional tools
and `doom upgrade` when you deliberately want to update Doom.
