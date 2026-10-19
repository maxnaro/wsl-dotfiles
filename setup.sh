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

DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
SHARE_DIR="$HOME/.local/share"

# RunCat's pinned build tool needs Python 3.11+, but does not need pip or venv.
if ! command -v python3 >/dev/null 2>&1 || ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then
    error "Setup requires Python 3.11 or newer on PATH (for the tmux RunCat font build)."
    exit 1
fi

info "Initializing dotfiles submodules..."
git -C "$DOTFILES_DIR" submodule update --init --recursive

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
        ARCH_FISH="linux-x86_64"
        ARCH_LAZYGIT="Linux_x86_64"
        ARCH_RG="x86_64-unknown-linux-musl"
        ARCH_ZOXIDE="x86_64-unknown-linux-musl"
        ;;
    aarch64|arm64)
        ARCH_FZF="linux_arm64"
        ARCH_BAT="aarch64-unknown-linux-musl"
        ARCH_EZA="aarch64-unknown-linux-musl"
        ARCH_FASTFETCH="linux-aarch64"
        ARCH_NVIM="linux-arm64"
        ARCH_FISH="linux-aarch64"
        ARCH_LAZYGIT="Linux_arm64"
        ARCH_RG="aarch64-unknown-linux-musl"
        ARCH_ZOXIDE="aarch64-unknown-linux-musl"
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

# 1.0 Rust toolchain and tmux prefix help
# rustup may already be installed without being on this shell's PATH.
export PATH="${CARGO_HOME:-$HOME/.cargo}/bin:$PATH"
if ! command -v cc >/dev/null 2>&1; then
    error "Building tmux-prefix-help requires a C linker (cc). Install your system's C build tools first (e.g. build-essential on Debian/Ubuntu)."
    exit 1
fi

if ! command -v rustup >/dev/null 2>&1; then
    info "Installing Rust with rustup..."
    curl https://sh.rustup.rs -sSf | sh -s -- -y --profile minimal --no-modify-path
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

# 1.7 FISH SHELL
if ! command -v "$BIN_DIR/fish" >/dev/null 2>&1 && ! command -v fish >/dev/null 2>&1; then
    info "Installing Fish Shell..."
    FISH_VERSION=$(curl -sI https://github.com/fish-shell/fish-shell/releases/latest | grep -i location | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1 || echo "4.9.3")
    curl -sL "https://github.com/fish-shell/fish-shell/releases/download/${FISH_VERSION}/fish-${FISH_VERSION}-${ARCH_FISH}.tar.xz" | tar -xJ -C "$BIN_DIR"
    chmod +x "$BIN_DIR/fish"
    success "Fish Shell v${FISH_VERSION} installed"
else
    success "Fish Shell is already available"
fi

# 1.8 POKEMON TERMINAL GREETING
if ! command -v "$BIN_DIR/pokemon-greeting" >/dev/null 2>&1; then
    info "Installing pokemon-terminal-greeting..."
    TMP_PKG=$(mktemp -d)
    git clone --depth 1 https://github.com/Youpen-y/pokemon-terminal-greeting.git "$TMP_PKG"
    "$TMP_PKG/install.sh" --no-hook
    rm -rf "$TMP_PKG"
    success "pokemon-terminal-greeting installed"
else
    success "pokemon-terminal-greeting is already installed"
fi

# 1.9 LAZYGIT
if ! command -v "$BIN_DIR/lazygit" >/dev/null 2>&1; then
    info "Installing lazygit..."
    LAZYGIT_VERSION=$(curl -sI https://github.com/jesseduffield/lazygit/releases/latest | grep -i location | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1 || echo "0.66.1")
    curl -sL "https://github.com/jesseduffield/lazygit/releases/download/v${LAZYGIT_VERSION}/lazygit_${LAZYGIT_VERSION}_${ARCH_LAZYGIT}.tar.gz" | tar -xz -C "$BIN_DIR" lazygit
    chmod +x "$BIN_DIR/lazygit"
    success "lazygit v${LAZYGIT_VERSION} installed"
else
    success "lazygit is already installed"
fi

# 1.10 RIPGREP
if ! command -v "$BIN_DIR/rg" >/dev/null 2>&1; then
    info "Installing ripgrep..."
    RG_VERSION=$(curl -sI https://github.com/BurntSushi/ripgrep/releases/latest | grep -i location | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1 || echo "15.2.0")
    curl -sL "https://github.com/BurntSushi/ripgrep/releases/download/${RG_VERSION}/ripgrep-${RG_VERSION}-${ARCH_RG}.tar.gz" | tar -xz --strip-components=1 -C "$BIN_DIR" "ripgrep-${RG_VERSION}-${ARCH_RG}/rg"
    chmod +x "$BIN_DIR/rg"
    success "ripgrep v${RG_VERSION} installed"
else
    success "ripgrep is already installed"
fi

# 1.11 ZOXIDE
if ! command -v "$BIN_DIR/zoxide" >/dev/null 2>&1; then
    info "Installing zoxide..."
    ZOXIDE_VERSION=$(curl -sI https://github.com/ajeetdsouza/zoxide/releases/latest | grep -i location | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1 || echo "0.10.0")
    curl -sL "https://github.com/ajeetdsouza/zoxide/releases/download/v${ZOXIDE_VERSION}/zoxide-${ZOXIDE_VERSION}-${ARCH_ZOXIDE}.tar.gz" | tar -xz -C "$BIN_DIR" zoxide
    chmod +x "$BIN_DIR/zoxide"
    success "zoxide v${ZOXIDE_VERSION} installed"
else
    success "zoxide is already installed"
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
    info "Building and installing pinned JetBrainsMono / RunCat fonts..."
    bash "$DOTFILES_DIR/tmux/.config/tmux/plugins/tmux-runcat/fonts/setup.sh"
    link_file "$DOTFILES_DIR/tmux/.config/tmux" "$HOME/.config/tmux"
fi

# -----------------------------------------------------------------------------
# 3. Optional: GNU Stow support
# -----------------------------------------------------------------------------
if command -v stow >/dev/null 2>&1; then
    info "GNU Stow detected. You can also run 'stow bash', 'stow git', 'stow scripts', 'stow nvim', 'stow fish', or 'stow tmux' inside $DOTFILES_DIR"
fi

echo ""
success "Setup complete! Run 'source ~/.bashrc' or restart your terminal."
