#!/bin/bash
# Description: Automatically activate/deactivate Python venvs on 'cd'

auto_venv_cd() {
  builtin cd "$@" || return

  # Check for common venv names
  for venv_dir in .venv venv env; do
    if [[ -f "$venv_dir/bin/activate" ]]; then
      if [[ "$VIRTUAL_ENV" != "$(pwd)/$venv_dir" ]]; then
        source "$venv_dir/bin/activate"
      fi
      return
    fi
  done

  # Auto-deactivate if you leave the project tree
  if [[ -n "$VIRTUAL_ENV" ]]; then
    if [[ "$PWD"/ != "$(dirname "$VIRTUAL_ENV")"/* ]]; then
      deactivate
    fi
  fi
}

# Override the standard cd command with our wrapper function
alias cd='auto_venv_cd'
