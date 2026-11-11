# Dotfiles

My personal WSL / Linux configuration files, styled with CachyOS terminal utilities and fuzzy finder.

## Directory Structure

```text
dotfiles/
├── bash/
│   ├── .bashrc
│   ├── .bash_aliases
│   └── .inputrc
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
│       └── nvim/                         # Git submodule (maxnaro/nvim-config)
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
stow -R lazygit
stow -R scripts
stow -R nvim
stow -R tmux
stow -R --no-folding codex
```

### Codex and Claude Code delegation preference

`codex/.codex/AGENTS.md` contains a standing request to use judgment when
delegating work to subagents. Small or dependent tasks stay with the main agent;
independent work can be delegated without a fresh request. Higher-priority
instructions and explicit task restrictions still apply.

`./setup.sh` links this policy to `${CODEX_HOME:-$HOME/.codex}/AGENTS.md`,
backing up existing files through the normal installer behavior. GNU Stow uses
the default `~/.codex` location; custom `CODEX_HOME` installations use setup.
Only the instruction file is managed; Codex runtime state stays local.

Setup also links the same policy to
`${CLAUDE_CONFIG_DIR:-$HOME/.claude}/CLAUDE.md` for Claude Code, with the same
backup and rerun behavior. Existing Claude settings and permissions stay local.
Both tools share one policy source. `stow codex` installs only the Codex link;
use setup to install both integrations.

In fresh Claude Code sessions inside and outside this repository, run
`/context all` and confirm the global `CLAUDE.md` appears under Memory files.

Start a fresh Codex session inside and outside this repository and ask it to
summarize its loaded delegation instructions. Both should report the standing
request. Other devices inherit the preference after installing these dotfiles.

### Tmux startup and recovery

Interactive Bash and Fish terminals automatically attach to an existing tmux
server or start a new one. On a new server, tmux-continuum restores the last
saved layout when available; it saves every 15 minutes. Continuum skips automatic
restore when another tmux server is running, and restoration takes place shortly
after startup. Pane processes are not restarted. Detaching returns to the shell. Set `DOTFILES_NO_TMUX=1` in the
environment (or in `~/.bashrc.local` / `~/.config/fish/local.fish`) to skip
automatic entry. Existing tmux panes and noninteractive shells do not launch
another server. Save and restore manually with prefix `Ctrl-s` and `Ctrl-r`.

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

### Neovim configuration repository

The Neovim configuration lives in the public
[maxnaro/nvim-config](https://github.com/maxnaro/nvim-config) repository,
included as a Git submodule at `nvim/.config/nvim`. Its Neovim-specific history
is preserved there. See its [README](nvim/.config/nvim/README.md) for standalone
installation and configuration details.

The setup script and `stow -R nvim` use the same paths as before. After pulling
updates to this repository, initialize or update the pinned configuration:

```bash
git submodule update --init --recursive
```

To change the configuration, commit and push inside `nvim/.config/nvim` first,
then commit the updated submodule pointer in this repository. Submodule updates
normally check out a detached HEAD; switch to `main` before making changes.

### Editor and LazyGit styling

LazyVim uses a transparent, compact status line with file changes, Git details,
diagnostics, and cursor position. Its text, syntax accents, selection surfaces, and LazyGit borders match the
shared terminal palette. Buffer tabs are disabled; native tab pages remain available. In LazyGit, Escape dismisses dialogs and subviews,
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
then accepts visible AI ghost text, or opens completions after a typed word.
Otherwise it inserts normal Tab. Shift-Tab
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

### Shared light and dark themes

Chocolatier dark and [Kimbie Light](https://github.com/idleberg/atom-kimbie-light)
share one palette in `themes/chocolatier.json`. Kimbie retains its cream background
(`#FBEBD4`) and brown text (`#221A0F`), with stronger accents and labels for readable
terminal use. [Source attribution and license](themes/KIMBIE-LIGHT.md) cover the
adapted light theme. Chocolatier colors remain unchanged. Both modes use 75%
Windows Terminal opacity with acrylic enabled; Neovim retains transparent editor
backgrounds, floats, gutters, and status lines.

```bash
bash themes/install.sh
dotfiles-theme light
dotfiles-theme dark
dotfiles-theme toggle
dotfiles-theme status
dotfiles-theme status --verbose
```

Tmux prefix + `T` toggles in the background. Captured warnings appear briefly in
the status line even when the switch succeeds; a warning-free success stays silent,
and failures without stderr show a generic error. Both Ctrl-b and Ctrl-a prefixes
work. The saved choice persists under `${XDG_STATE_HOME:-~/.local/state}/dotfiles/theme`;
`dotfiles-theme apply` reapplies it. Switching does not edit tracked configuration.

The command validates app configuration and destinations before applying changes.
A failed preflight leaves the current theme intact. A later write or live-reload
failure is reported, but cannot make updates across independent apps atomic.
Concurrent toggles are serialized. `status --verbose` checks integration readiness
and explains refresh limits; it does not claim to verify live pixels.

After applying a theme, the command asks attached tmux clients' terminals for fresh
foreground and background colors so tmux can update its cache. It retries over two
seconds because Windows Terminal may reload settings asynchronously. This is best
effort; it does not verify rendered pixels or cached colors. The generated tmux
styles keep default pane backgrounds, preserving acrylic at 75% opacity and both palettes.

Terminal, tmux, and open Neovim instances follow the saved mode. Claude Code is
pointed at generated `~/.claude/themes/dotfiles.json` with `theme: custom:dotfiles`;
this replaces any independently selected Claude theme. Native reload handles
running sessions where supported; sessions started before the themes directory
existed may need reopening. Codex receives a generated Kimbie syntax theme in light
mode; dark retains its default. Running Codex sessions may retain startup prompt
or syntax colors, so each apply reports a restart warning when Codex is
configured. To refresh an existing Codex session, exit the process and run
`codex resume` from its shell; `/resume` inside the same TUI does not reload its
startup colors. If the terminal still shows stale colors, detach and reattach tmux,
then reopen Codex. Theme switching does not restart sessions, clear drafts, or
change agent session state. A standalone private-PTY regression check is available
with `python3 tests/live_tmux_theme.py`.

LazyGit inside Neovim receives an updated RGB theme on each switch; hide/show its
popup or re-enter terminal input mode to reload. Reopen standalone LazyGit,
history searches, pickers, and other embedded terminals if colors persist. Shell
prompts, Fish syntax, fzf, bat previews/man pages, eza, and Atuin use terminal ANSI
colors. Windows desktop appearance remains independent.

`windows-terminal/settings.json` tracks the imported Windows Terminal configuration,
including profiles, defaults, fonts, shortcuts, and the original Chocolatier scheme.
The live file stays at its native Windows location; this is managed apply rather
than a symlink into WSL. On WSL, the theme command discovers stable, preview, or
unpackaged Terminal settings, in that order, and applies both shared schemes through
Windows PowerShell. It preserves unrelated settings and updates profile color
scheme overrides. Each change creates a timestamped `.dotfiles-*.bak` beside the
live JSON. Restore by copying the desired backup over `settings.json`, then run
`dotfiles-theme apply` to coordinate the remaining apps. The tracked snapshot is
also available for a complete manual restore on this machine. JSONC is accepted;
comments and formatting are normalized on write. Invalid JSON leaves the file intact.
Linux installations without Windows Terminal apply the WSL themes normally.
