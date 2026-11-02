#!/usr/bin/env bash
#
# setup.sh - Cross-platform / WSL setup script for dotfiles and modern CLI tooling.
# Installs tools without sudo; building Rust code requires a system C linker.

set -euo pipefail

# ANSI color output
CYAN='\033[1;36m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
NC='\033[0m' # No Color

info() {
    printf "${CYAN}==>${NC} %s\n" "$1"
}

success() {
    printf "${GREEN}✔${NC} %s\n" "$1"
}

warn() {
    printf "${YELLOW}⚠${NC} %s\n" "$1"
}

error() {
    printf "${RED}✖${NC} %s\n" "$1"
}

# Validate prerequisites before creating installation directories.
for prerequisite in git curl python3 tar sha256sum cc tmux; do
    command -v "$prerequisite" >/dev/null 2>&1 || { error "Missing prerequisite: $prerequisite"; exit 1; }
done
[[ $(uname -s) == Linux ]] || { error "Setup supports Linux and WSL only"; exit 1; }
SETUP_STAGE=$(mktemp -d)
trap 'rm -rf -- "$SETUP_STAGE"' EXIT
trap 'error "Setup failed at line $LINENO; rerun after resolving the error"' ERR

DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
SHARE_DIR="$HOME/.local/share"

# RunCat's pinned build tool needs Python 3.11+, but does not need pip or venv.
if ! command -v python3 >/dev/null 2>&1 || ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then
    error "Setup requires Python 3.11 or newer on PATH (for the tmux RunCat font build)."
    exit 1
fi

case "$(uname -m)" in
    x86_64|amd64|aarch64|arm64) ;;
    *) error "Unsupported architecture: $(uname -m)"; exit 1 ;;
esac

info "Initializing dotfiles submodules..."
git -C "$DOTFILES_DIR" submodule update --init --recursive

mkdir -p "$BIN_DIR" "$SHARE_DIR/fzf"

# -----------------------------------------------------------------------------
# 1. Download & Install Tools (Zero-sudo required)
# -----------------------------------------------------------------------------
info "Installing CLI tools into $BIN_DIR..."

# 1.0 Rust toolchain and tmux prefix help
# rustup may already be installed without being on this shell's PATH.
export PATH="${CARGO_HOME:-$HOME/.cargo}/bin:$PATH"
if ! command -v cc >/dev/null 2>&1; then
    error "Building tmux-prefix-help requires a C linker (cc). Install your system's C build tools first (e.g. build-essential on Debian/Ubuntu)."
    exit 1
fi

if ! command -v rustup >/dev/null 2>&1; then
    info "Installing Rust with rustup..."
    curl --fail --show-error --location --retry 3 --connect-timeout 15 https://sh.rustup.rs -o "$SETUP_STAGE/rustup-init.sh"
    sh "$SETUP_STAGE/rustup-init.sh" -y --profile minimal --no-modify-path
else
    success "rustup is already installed"
fi

# Ensure stable meets the plugin's minimum Rust version, including on machines
# with an older installation. Use it explicitly without changing user defaults.
info "Ensuring the stable Rust toolchain is up to date..."
rustup toolchain install stable --profile minimal

TMUX_PREFIX_HELP_DIR="$DOTFILES_DIR/tmux/.config/tmux/plugins/tmux-prefix-help"
info "Building tmux-prefix-help..."
rustup run stable cargo build --release --locked \
    --manifest-path "$TMUX_PREFIX_HELP_DIR/Cargo.toml" \
    --target-dir "$TMUX_PREFIX_HELP_DIR/target"
success "tmux-prefix-help release binary built"

TMUX_RUNCAT_DIR="$DOTFILES_DIR/tmux/.config/tmux/plugins/tmux-runcat"
info "Building tmux-runcat..."
rustup run stable cargo build --release --locked --offline \
    --manifest-path "$TMUX_RUNCAT_DIR/Cargo.toml" \
    --target-dir "$TMUX_RUNCAT_DIR/target"
success "tmux-runcat release binary built"

python3 "$DOTFILES_DIR/setup/install_tools.py"

if ! command -v pokemon-greeting >/dev/null 2>&1 && [[ ! -x "$BIN_DIR/pokemon-greeting" ]]; then
    info "Installing pinned pokemon-terminal-greeting source..."
    POKEMON_COMMIT=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["pokemon"]["commit"])' "$DOTFILES_DIR/setup/tools.json")
    git clone --no-checkout https://github.com/Youpen-y/pokemon-terminal-greeting.git "$SETUP_STAGE/pokemon"
    git -C "$SETUP_STAGE/pokemon" checkout --detach "$POKEMON_COMMIT"
    "$SETUP_STAGE/pokemon/install.sh" --no-hook
fi
if ! command -v fd >/dev/null 2>&1 && command -v fdfind >/dev/null 2>&1; then
    ln -s "$(command -v fdfind)" "$BIN_DIR/fd"
fi

# -----------------------------------------------------------------------------
# 2. Symlink Dotfiles
# -----------------------------------------------------------------------------
    info "Building and installing RunCat fonts (customizable with RUNCAT_BASE_FONT)..."
    bash "$DOTFILES_DIR/tmux/.config/tmux/plugins/tmux-runcat/fonts/setup.sh"
info "Linking dotfiles to $HOME..."

link_file() {
    local src="$1"
    local dst="$2"

    mkdir -p "$(dirname "$dst")"

    if [ -e "$dst" ] || [ -L "$dst" ]; then
        if [ "$(readlink -f "$dst" 2>/dev/null || true)" = "$(readlink -f "$src")" ]; then
            success "Already linked: $dst"
            return
        fi
        local backup_dir
        backup_dir=$(mktemp -d "${dst}.bak.XXXXXXXX")
        warn "Backing up existing $dst to $backup_dir/original"
        mv -- "$dst" "$backup_dir/original"
    fi

    if ! ln -s -- "$src" "$dst"; then
        if [[ -n ${backup_dir:-} ]]; then
            mv -- "$backup_dir/original" "$dst"
            rmdir -- "$backup_dir"
        fi
        return 1
    fi
    success "Linked $dst -> $src"
}

# Link bash configuration
link_file "$DOTFILES_DIR/atuin/.config/atuin/config.toml" "$HOME/.config/atuin/config.toml"

link_file "$DOTFILES_DIR/bash/.bashrc" "$HOME/.bashrc"
link_file "$DOTFILES_DIR/bash/.bash_aliases" "$HOME/.bash_aliases"
if [ -f "$DOTFILES_DIR/bash/.inputrc" ]; then
    link_file "$DOTFILES_DIR/bash/.inputrc" "$HOME/.inputrc"
fi
if [ -f "$DOTFILES_DIR/bash/.blerc" ]; then
    link_file "$DOTFILES_DIR/bash/.blerc" "$HOME/.blerc"
fi

# Link git configuration if present
if [ -f "$DOTFILES_DIR/git/.gitconfig" ]; then
    link_file "$DOTFILES_DIR/git/.gitconfig" "$HOME/.gitconfig"
fi

# Link helper scripts (.scripts/)
if [ -f "$DOTFILES_DIR/scripts/.scripts/auto_venv.sh" ]; then
    link_file "$DOTFILES_DIR/scripts/.scripts/auto_venv.sh" "$HOME/.scripts/auto_venv.sh"
fi

# Link LazyGit configuration
link_file "$DOTFILES_DIR/lazygit/.config/lazygit/config.yml" "$HOME/.config/lazygit/config.yml"

# Link Neovim configuration (~/.config/nvim)
if [ -d "$DOTFILES_DIR/nvim/.config/nvim" ]; then
    link_file "$DOTFILES_DIR/nvim/.config/nvim" "$HOME/.config/nvim"
fi

# Link Fish configuration (~/.config/fish)
if [ -d "$DOTFILES_DIR/fish/.config/fish" ]; then
    link_file "$DOTFILES_DIR/fish/.config/fish" "$HOME/.config/fish"
fi

# Link Tmux configuration (~/.config/tmux)
if [ -d "$DOTFILES_DIR/tmux/.config/tmux" ]; then
    link_file "$DOTFILES_DIR/tmux/.config/tmux" "$HOME/.config/tmux"
fi

# -----------------------------------------------------------------------------
# 3. Optional: GNU Stow support
# -----------------------------------------------------------------------------
if command -v stow >/dev/null 2>&1; then
    info "GNU Stow detected. You can also run 'stow bash', 'stow git', 'stow scripts', 'stow nvim', 'stow fish', 'stow lazygit', or 'stow tmux' inside $DOTFILES_DIR"
fi

echo ""
success "Setup complete! Run 'source ~/.bashrc' or restart your terminal."
