#!/usr/bin/env bash
# Serialize detached directory-history updates without blocking navigation.
set -euo pipefail
data_dir=${_ZO_DATA_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/zoxide}
mkdir -p -- "$data_dir"
exec flock "$data_dir/.dotfiles-add.lock" zoxide add -- "$1"
