#!/usr/bin/env bash
# Claude Code status line: cwd, git branch, and a badge while caveman is active.
input=$(cat)
cwd=$(jq -r '.workspace.current_dir // .cwd // empty' <<<"$input")
session=$(jq -r '.session_id // empty' <<<"$input")
[ -z "$cwd" ] && cwd=$(pwd)
disp="${cwd/#$HOME/\~}"
branch=$(git -C "$cwd" --no-optional-locks branch --show-current 2>/dev/null)
out="$disp"
[ -n "$branch" ] && out="$out ($branch)"
flags="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/caveman"
if [ -n "$session" ] && [ -e "$flags/$session" ]; then
    out="$out \033[38;5;208m[CAVEMAN ULTRA]\033[0m"
fi
printf '%b' "$out"
