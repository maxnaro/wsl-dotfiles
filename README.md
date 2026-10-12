# Dotfiles

My personal WSL / Linux configuration files, styled with CachyOS terminal utilities and fuzzy finder.

## Directory Structure

```text
dotfiles/
├── bash/
│   ├── .bashrc
│   └── .bash_aliases
├── git/
│   └── .gitconfig
├── scripts/
│   └── .scripts/
│       └── auto_venv.sh
├── setup.sh
└── README.md
```

## Quick Start (New Machine / WSL Installation)

Clone this repository and run the setup script. It requires **no sudo privileges** and installs all dependencies directly to `~/.local/bin`:

```bash
git clone <your-repo-url> ~/dotfiles
cd ~/dotfiles
./setup.sh
source ~/.bashrc
```

### What `setup.sh` does:
1. **Downloads modern CLI tools** (`fzf`, `bat`, `eza`, `fastfetch`) directly to `~/.local/bin`.
2. **Downloads official FZF bash keybindings and completions** to `~/.local/share/fzf/`.
3. **Symlinks dotfiles** cleanly to `$HOME`:
   - `bash/.bashrc` -> `~/.bashrc`
   - `bash/.bash_aliases` -> `~/.bash_aliases`
   - `git/.gitconfig` -> `~/.gitconfig`
   - `scripts/.scripts/auto_venv.sh` -> `~/.scripts/auto_venv.sh`
4. Creates automatic `.bak` backups if any files already exist in your home directory before linking.

### (Optional) GNU Stow

If you prefer using `stow`:
```bash
cd ~/dotfiles
stow -R bash
stow -R git
stow -R scripts
```
