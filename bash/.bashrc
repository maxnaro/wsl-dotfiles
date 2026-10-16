# ~/.bashrc: executed by bash(1) for non-login shells.
# see /usr/share/doc/bash/examples/startup-files (in the package bash-doc)
# for examples

# If not running interactively, don't do anything
case $- in
*i*) ;;
*) return ;;
esac

# don't put duplicate lines or lines starting with space in the history.
# See bash(1) for more options
HISTCONTROL=ignoreboth

# append to the history file, don't overwrite it
shopt -s histappend

# for setting history length see HISTSIZE and HISTFILESIZE in bash(1)
HISTSIZE=1000
HISTFILESIZE=2000

# check the window size after each command and, if necessary,
# update the values of LINES and COLUMNS.
shopt -s checkwinsize

# If set, the pattern "**" used in a pathname expansion context will
# match all files and zero or more directories and subdirectories.
#shopt -s globstar

# make less more friendly for non-text input files, see lesspipe(1)
[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# set variable identifying the chroot you work in (used in the prompt below)
if [ -z "${debian_chroot:-}" ] && [ -r /etc/debian_chroot ]; then
  debian_chroot=$(cat /etc/debian_chroot)
fi

# set a fancy prompt (non-color, unless we know we "want" color)
case "$TERM" in
xterm-color | *-256color) color_prompt=yes ;;
esac

# uncomment for a colored prompt, if the terminal has the capability; turned
# off by default to not distract the user: the focus in a terminal window
# should be on the output of commands, not on the prompt
#force_color_prompt=yes

if [ -n "$force_color_prompt" ]; then
  if [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then
    # We have color support; assume it's compliant with Ecma-48
    # (ISO/IEC-6429). (Lack of such support is extremely rare, and such
    # a case would tend to support setf rather than setaf.)
    color_prompt=yes
  else
    color_prompt=
  fi
fi

if [ "$color_prompt" = yes ]; then
  PS1='${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
else
  PS1='${debian_chroot:+($debian_chroot)}\u@\h:\w\$ '
fi
unset color_prompt force_color_prompt

# If this is an xterm set the title to user@host:dir
case "$TERM" in
xterm* | rxvt*)
  PS1="\[\e]0;${debian_chroot:+($debian_chroot)}\u@\h: \w\a\]$PS1"
  ;;
*)
  ;;
esac

# enable color support of ls and also add handy aliases
if [ -x /usr/bin/dircolors ]; then
  test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
  alias ls='ls --color=auto'
  #alias dir='dir --color=auto'
  #alias vdir='vdir --color=auto'

  alias grep='grep --color=auto'
  alias fgrep='fgrep --color=auto'
  alias egrep='egrep --color=auto'
fi

# colored GCC warnings and errors
#export GCC_COLORS='error=01;31:warning=01;35:note=01;36:caret=01;32:locus=01:quote=01'

# some more ls aliases
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'

# Add an "alert" alias for long running commands.  Use like so:
#   sleep 10; alert
alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'

# Alias definitions.
# You may want to put all your additions into a separate file like
# ~/.bash_aliases, instead of adding them here directly.
# See /usr/share/doc/bash-doc/examples in the bash-doc package.

if [ -f ~/.bash_aliases ]; then
  . ~/.bash_aliases
fi

# enable programmable completion features (you don't need to enable
# this, if it's already enabled in /etc/bash.bashrc and /etc/profile
# sources /etc/bash.bashrc).
if ! shopt -oq posix; then
  if [ -f /usr/share/bash-completion/bash_completion ]; then
    . /usr/share/bash-completion/bash_completion
  elif [ -f /etc/bash_completion ]; then
    . /etc/bash_completion
  fi
fi

# NVM CONFIGURATION (Lazy-loaded on first call to nvm/node/npm/npx/pnpm/yarn)
export NVM_DIR="$HOME/.nvm"
_load_nvm() {
  unset -f nvm node npm npx pnpm yarn _load_nvm
  [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
  [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
}
for _nvm_cmd in nvm node npm npx pnpm yarn; do
  eval "$_nvm_cmd() { _load_nvm; \"$_nvm_cmd\" \"\$@\"; }"
done
unset _nvm_cmd

# PYENV CONFIGURATION (Fast PATH shims, lazy-load completions/rehash on pyenv invocation)
export PYENV_ROOT="$HOME/.pyenv"
if [ -d "$PYENV_ROOT/bin" ]; then
  export PATH="$PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH"
fi
pyenv() {
  unset -f pyenv
  eval "$(command pyenv init -)"
  pyenv "$@"
}

# Added by Antigravity CLI installer
export PATH="/home/max/.local/bin:$PATH"
# Filter slow /mnt/c Windows paths from PATH to prevent tab-completion freezes in WSL,
# while retaining access to VS Code CLI
_clean_path=$(echo "$PATH" | tr ':' '\n' | grep -v '^/mnt/c' | paste -sd: -)
export PATH="${_clean_path}:/mnt/c/Users/MaxNarongchai/AppData/Local/Programs/Microsoft VS Code/bin"
unset _clean_path

# Go bin PATH (Static path avoids slow 'go env GOPATH' subshell execution)
export PATH="${GOPATH:-$HOME/go}/bin:$PATH"
[[ -f ~/.scripts/auto_venv.sh ]] && source ~/.scripts/auto_venv.sh

# -----------------------------------------------------------------------------
# CachyOS Terminal Enhancements (FZF, Manpager, Prompt, Fastfetch)
# -----------------------------------------------------------------------------

# Man pages formatted with bat
if command -v bat >/dev/null 2>&1; then
  export MANROFFOPT="-c"
  export MANPAGER="sh -c 'col -bx | bat -l man -p'"
fi

# FZF: CachyOS-style layout, floating rounded border, and previews
# (Using terminal default colors to respect user color scheme)
if command -v fzf >/dev/null 2>&1; then
  if command -v fd >/dev/null 2>&1; then
    export FZF_DEFAULT_COMMAND='fd --type f --strip-cwd-prefix --hidden --follow --exclude .git'
    export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"
    export FZF_ALT_C_COMMAND='fd --type d --strip-cwd-prefix --hidden --follow --exclude .git'
  fi

  export FZF_DEFAULT_OPTS="
      --style=full
      --layout=reverse
      --height=60%
      --border=rounded
      --border-label=' 󰍉 Search '
      --border-label-pos=2
      --info=inline-right
      --prompt='❯ '
      --pointer='◆'
      --marker='✓'
    "

  # Previews: syntax-highlighted files (bat), tree directory view (eza)
  export FZF_CTRL_T_OPTS="--preview 'bat --style=numbers --color=always --line-range :300 {} 2>/dev/null || cat {}'"
  export FZF_ALT_C_OPTS="--preview 'eza --tree --level=2 --color=always --icons=always {} 2>/dev/null || ls -la {}'"

  # Load FZF bash autocompletion & keybindings
  [ -f "$HOME/.local/share/fzf/completion.bash" ] && source "$HOME/.local/share/fzf/completion.bash"
  [ -f "$HOME/.local/share/fzf/key-bindings.bash" ] && source "$HOME/.local/share/fzf/key-bindings.bash"
fi

# Zoxide smart directory jumping (z, zi)
if command -v zoxide >/dev/null 2>&1; then
  eval "$(zoxide init bash)"
fi

# Minimalist CachyOS Pure-style prompt (two-line layout with git branch and ❯ symbol)
_cachyos_git_branch() {
  local branch
  branch=$(git branch --show-current 2>/dev/null)
  if [ -n "$branch" ]; then
    printf " (%s)" "$branch"
  fi
}
PS1='\w$(_cachyos_git_branch)\n❯ '

# Automatically launch fish for interactive sessions (retains bash for system scripts)
if [[ $- == *i* ]] && [ -z "$FISH_VERSION" ] && command -v fish >/dev/null 2>&1; then
  exec fish
fi
. "$HOME/.cargo/env"
