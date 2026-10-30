#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
for tool in sesh fzf zoxide; do
    command -v "$tool" >/dev/null || { echo "Missing tool: $tool" >&2; exit 1; }
done
entries=$(sesh list)
[[ -n "$entries" ]] || { echo 'No workspaces yet. Start one with: sesh connect /path/to/project'; read -r || true; exit 0; }
selection=$(printf '%s\n' "$entries" | fzf --height=100% --no-sort --prompt='Project > ') || exit 0
if [[ -n "$selection" ]]; then exec sesh connect "$selection"; fi
