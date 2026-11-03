#!/usr/bin/env bash
# Keep Doom's framework and generated state outside the dotfiles repository.
set -euo pipefail
emacs --batch -Q --eval '(kill-emacs (if (version< emacs-version "29.1") 1 0))'
doom_dir="$HOME/.config/emacs"
doom_revision=59cdaa32ae933469bb6a1fb3cadee8a988c15968
if [[ -e "$doom_dir" || -L "$doom_dir" ]]; then
    if [[ ! -f "$doom_dir/lisp/doom.el" || ! -x "$doom_dir/bin/doom" ]]; then
        echo "Cannot bootstrap Doom: $doom_dir contains an unrelated configuration. Move it aside first." >&2
        exit 1
    fi
    "$doom_dir/bin/doom" --doomdir "$HOME/.config/doom" --force sync
else
    mkdir -p "$(dirname "$doom_dir")"
    stage=$(mktemp -d "$(dirname "$doom_dir")/.doom-install.XXXXXXXX")
    trap 'rm -rf -- "$stage"' EXIT
    git clone --no-checkout https://github.com/doomemacs/core "$stage/emacs"
    git -C "$stage/emacs" checkout --detach "$doom_revision"
    git -C "$stage/emacs" submodule update --init --recursive
    mv -- "$stage/emacs" "$doom_dir"
    "$doom_dir/bin/doom" --doomdir "$HOME/.config/doom" --force install --no-config --no-env
fi
