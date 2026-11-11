#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
for tool in sesh fzf zoxide; do
    command -v "$tool" >/dev/null || { echo "Missing tool: $tool" >&2; exit 1; }
done
# Keep existing sessions usable while the complete workspace list loads.
selection=$(fzf --height=100% --no-sort --no-sync --prompt='Project > ' \
    --header='Loading workspaces…' \
    --bind='start:reload-sync(sesh list),load:transform-header:if [ "$FZF_TOTAL_COUNT" = 0 ]; then echo "No workspaces yet. Start one with: sesh connect /path/to/project"; fi' \
    < <(tmux list-sessions -F '#S' 2>/dev/null || true)) || exit 0
if [[ -n "$selection" ]]; then exec sesh connect "$selection"; fi
