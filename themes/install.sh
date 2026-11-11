#!/usr/bin/env bash
# Install theme controls without downloading tools or rebuilding plugins.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
link() {
    local source=$1 destination=$2 backup
    mkdir -p -- "$(dirname -- "$destination")"
    if [[ -e $destination || -L $destination ]]; then
        [[ $(readlink -f -- "$destination" 2>/dev/null || true) != $(readlink -f -- "$source") ]] || return 0
        backup=$(mktemp -d "${destination}.bak.XXXXXXXX")
        mv -- "$destination" "$backup/original"
    fi
    if ! ln -s -- "$source" "$destination"; then
        if [[ -n ${backup:-} ]]; then mv -- "$backup/original" "$destination"; rmdir -- "$backup"; fi
        return 1
    fi
}
link "$root/themes/chocolatier.json" "${XDG_CONFIG_HOME:-$HOME/.config}/dotfiles/theme/palette.json"
link "$root/scripts/.scripts/dotfiles-theme" "$HOME/.local/bin/dotfiles-theme"
link "$root/atuin/.config/atuin/themes" "${XDG_CONFIG_HOME:-$HOME/.config}/atuin/themes"
"$HOME/.local/bin/dotfiles-theme" apply
