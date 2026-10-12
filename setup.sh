#!/usr/bin/env bash
#
# setup.sh - Cross-platform / WSL setup script for dotfiles and modern CLI tooling.
# Works completely without sudo (installs user-local binaries to ~/.local/bin),
# but can optionally use sudo / apt if available.

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

DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
SHARE_DIR="$HOME/.local/share"

mkdir -p "$BIN_DIR" "$SHARE_DIR/fzf"

# Detect machine architecture
ARCH="$(uname -m)"
case "$ARCH" in
    x86_64|amd64)
        ARCH_FZF="linux_amd64"
        ARCH_BAT="x86_64-unknown-linux-musl"
        ARCH_EZA="x86_64-unknown-linux-musl"
        ARCH_FASTFETCH="linux-amd64"
        ARCH_NVIM="linux-x86_64"
        ;;
    aarch64|arm64)
        ARCH_FZF="linux_arm64"
        ARCH_BAT="aarch64-unknown-linux-musl"
        ARCH_EZA="aarch64-unknown-linux-musl"
        ARCH_FASTFETCH="linux-aarch64"
        ARCH_NVIM="linux-arm64"
        ;;
    *)
        error "Unsupported architecture: $ARCH"
        exit 1
        ;;
esac

# -----------------------------------------------------------------------------
# 1. Download & Install Tools (Zero-sudo required)
# -----------------------------------------------------------------------------
info "Installing CLI tools into $BIN_DIR..."

# 1.1 FZF
if ! command -v "$BIN_DIR/fzf" >/dev/null 2>&1; then
    info "Installing fzf..."
    FZF_VERSION=$(curl -sI https://github.com/junegunn/fzf/releases/latest | grep -i location | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1 || echo "0.74.5")
    curl -sL "https://github.com/junegunn/fzf/releases/download/v${FZF_VERSION}/fzf-${FZF_VERSION}-${ARCH_FZF}.tar.gz" | tar -xz -C "$BIN_DIR"
    chmod +x "$BIN_DIR/fzf"
    success "fzf v${FZF_VERSION} installed"
else
    success "fzf is already installed"
fi

# Download fzf shell scripts
curl -sL https://raw.githubusercontent.com/junegunn/fzf/master/shell/key-bindings.bash -o "$SHARE_DIR/fzf/key-bindings.bash"
curl -sL https://raw.githubusercontent.com/junegunn/fzf/master/shell/completion.bash -o "$SHARE_DIR/fzf/completion.bash"

# 1.2 BAT
if ! command -v "$BIN_DIR/bat" >/dev/null 2>&1; then
    info "Installing bat..."
    BAT_VERSION=$(curl -sI https://github.com/sharkdp/bat/releases/latest | grep -i location | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1 || echo "0.26.1")
    curl -sL "https://github.com/sharkdp/bat/releases/download/v${BAT_VERSION}/bat-v${BAT_VERSION}-${ARCH_BAT}.tar.gz" | tar -xz --strip-components=1 -C "$BIN_DIR" "bat-v${BAT_VERSION}-${ARCH_BAT}/bat"
    chmod +x "$BIN_DIR/bat"
    success "bat v${BAT_VERSION} installed"
else
    success "bat is already installed"
fi

# 1.3 EZA
if ! command -v "$BIN_DIR/eza" >/dev/null 2>&1; then
    info "Installing eza..."
    EZA_VERSION=$(curl -sI https://github.com/eza-community/eza/releases/latest | grep -i location | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1 || echo "0.23.5")
    curl -sL "https://github.com/eza-community/eza/releases/download/v${EZA_VERSION}/eza_${ARCH_EZA}.tar.gz" | tar -xz -C "$BIN_DIR"
    chmod +x "$BIN_DIR/eza"
    success "eza v${EZA_VERSION} installed"
else
    success "eza is already installed"
fi

# 1.4 FASTFETCH
if ! command -v "$BIN_DIR/fastfetch" >/dev/null 2>&1; then
    info "Installing fastfetch..."
    FF_VERSION=$(curl -sI https://github.com/fastfetch-cli/fastfetch/releases/latest | grep -i location | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1 || echo "2.69.0")
    curl -sL "https://github.com/fastfetch-cli/fastfetch/releases/download/${FF_VERSION}/fastfetch-${ARCH_FASTFETCH}.tar.gz" | tar -xz --strip-components=3 -C "$BIN_DIR" "fastfetch-${ARCH_FASTFETCH}/usr/bin/fastfetch"
    chmod +x "$BIN_DIR/fastfetch"
    success "fastfetch v${FF_VERSION} installed"
else
    success "fastfetch is already installed"
fi

# 1.5 FD (symlink to fdfind if available)
if ! command -v "$BIN_DIR/fd" >/dev/null 2>&1; then
    if command -v fdfind >/dev/null 2>&1; then
        ln -sf "$(command -v fdfind)" "$BIN_DIR/fd"
        success "fd symlinked to fdfind"
    elif command -v fd >/dev/null 2>&1; then
        success "fd is already available"
    else
        warn "fdfind/fd not found on PATH. Install 'fd-find' via apt or your package manager if available."
    fi
else
    success "fd is available"
fi

# 1.6 NEOVIM
if ! command -v "$BIN_DIR/nvim" >/dev/null 2>&1 && ! command -v nvim >/dev/null 2>&1; then
    info "Installing Neovim..."
    NVIM_VERSION=$(curl -sI https://github.com/neovim/neovim/releases/latest | grep -i location | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1 || echo "0.12.6")
    curl -sL "https://github.com/neovim/neovim/releases/download/v${NVIM_VERSION}/nvim-${ARCH_NVIM}.tar.gz" | tar -xz --strip-components=1 -C "$HOME/.local"
    chmod +x "$BIN_DIR/nvim"
    success "Neovim v${NVIM_VERSION} installed"
else
    success "Neovim is already available"
fi

# -----------------------------------------------------------------------------
# 2. Symlink Dotfiles
# -----------------------------------------------------------------------------
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
        warn "Backing up existing $dst to ${dst}.bak"
        mv "$dst" "${dst}.bak"
    fi

    ln -s "$src" "$dst"
    success "Linked $dst -> $src"
}

# Link bash configuration
link_file "$DOTFILES_DIR/bash/.bashrc" "$HOME/.bashrc"
link_file "$DOTFILES_DIR/bash/.bash_aliases" "$HOME/.bash_aliases"
if [ -f "$DOTFILES_DIR/bash/.inputrc" ]; then
    link_file "$DOTFILES_DIR/bash/.inputrc" "$HOME/.inputrc"
fi

# Link git configuration if present
if [ -f "$DOTFILES_DIR/git/.gitconfig" ]; then
    link_file "$DOTFILES_DIR/git/.gitconfig" "$HOME/.gitconfig"
fi

# Link helper scripts (.scripts/)
if [ -f "$DOTFILES_DIR/scripts/.scripts/auto_venv.sh" ]; then
    link_file "$DOTFILES_DIR/scripts/.scripts/auto_venv.sh" "$HOME/.scripts/auto_venv.sh"
fi

# Link Neovim configuration (~/.config/nvim)
if [ -d "$DOTFILES_DIR/nvim/.config/nvim" ]; then
    link_file "$DOTFILES_DIR/nvim/.config/nvim" "$HOME/.config/nvim"
fi

# -----------------------------------------------------------------------------
# 3. Optional: GNU Stow support
# -----------------------------------------------------------------------------
if command -v stow >/dev/null 2>&1; then
    info "GNU Stow detected. You can also run 'stow bash', 'stow git', 'stow scripts', or 'stow nvim' inside $DOTFILES_DIR"
fi

echo ""
success "Setup complete! Run 'source ~/.bashrc' or restart your terminal."
