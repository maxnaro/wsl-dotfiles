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
│           └── plugins/tmux-prefix-help/  # Git submodule
├── scripts/
│   └── .scripts/
│       └── auto_venv.sh
├── setup.sh
└── README.md
```

## Quick Start (New Machine / WSL Installation)

Clone this repository and run the setup script. It requires **no sudo privileges** and installs all dependencies directly to `~/.local/bin`:

```bash
git clone --recurse-submodules <your-repo-url> ~/dotfiles
cd ~/dotfiles
./setup.sh
source ~/.bashrc
```

### What `setup.sh` does:

Initializes Git submodules before installing tools or linking configuration.

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

For an existing checkout, initialize the submodule before reloading tmux:

```bash
git submodule update --init --recursive
tmux source-file ~/.config/tmux/tmux.conf
```

Set `@prefix-help-delay` in `tmux.conf` to adjust the default 500 ms delay.
Commit plugin changes inside the submodule, then commit its updated pointer
in this repository.
