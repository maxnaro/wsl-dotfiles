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
# Claude Code: follow the generated custom theme unless another theme was chosen.
claude=${CLAUDE_CONFIG_DIR:-$HOME/.claude}
if [[ -d $claude ]]; then
    python3 - "$claude/settings.json" <<'EOF'
import json, os, sys, tempfile
path = sys.argv[1]
settings = json.load(open(path)) if os.path.exists(path) else {}
if settings.get('theme', 'auto') == 'auto':
    settings['theme'] = 'custom:dotfiles'
    fd, temporary = tempfile.mkstemp(dir=os.path.dirname(path))
    with os.fdopen(fd, 'w') as stream:
        json.dump(settings, stream, indent=2)
        stream.write('\n')
    os.replace(temporary, os.path.realpath(path) if os.path.islink(path) else path)
EOF
fi
