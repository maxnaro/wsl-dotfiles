#!/usr/bin/env bash
# Claude Code status line: cwd and git branch.
input=$(cat)
cwd=$(jq -r '.workspace.current_dir // .cwd // empty' <<<"$input")
[ -z "$cwd" ] && cwd=$(pwd)
disp="${cwd/#$HOME/\~}"
branch=$(git -C "$cwd" --no-optional-locks branch --show-current 2>/dev/null)
out="$disp"
[ -n "$branch" ] && out="$out ($branch)"
printf '%b' "$out"
