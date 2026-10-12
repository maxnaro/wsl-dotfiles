# ~/.config/fish/config.fish - CachyOS-style Fish configuration

# Clean Windows /mnt/c paths from PATH to keep tab completion instant in WSL
set -l clean_path (string split : $PATH | string match -v -r '^/mnt/c')
set -gx PATH $clean_path /mnt/c/Users/MaxNarongchai/AppData/Local/Programs/Microsoft\ VS\ Code/bin

# User bin & Go PATH
fish_add_path ~/.local/bin
fish_add_path (test -n "$GOPATH"; and echo "$GOPATH/bin"; or echo "$HOME/go/bin")

# Pyenv
if test -d "$HOME/.pyenv/bin"
    fish_add_path "$HOME/.pyenv/shims" "$HOME/.pyenv/bin"
end

# Format man pages with bat (CachyOS style)
if type -q bat
    set -gx MANROFFOPT "-c"
    set -gx MANPAGER "sh -c 'col -bx | bat -l man -p'"
end

# Modern CachyOS aliases (eza)
if type -q eza
    alias ls='eza -al --color=always --group-directories-first --icons=always'
    alias la='eza -a --color=always --group-directories-first --icons=always'
    alias ll='eza -l --color=always --group-directories-first --icons=always'
    alias lt='eza -aT --color=always --group-directories-first --icons=always'
    alias l.="eza -a | grep -e '^\.'"
end

# Navigation shortcuts
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'

# FZF configuration for Fish
if type -q fzf
    if type -q fd
        set -gx FZF_DEFAULT_COMMAND 'fd --type f --strip-cwd-prefix --hidden --follow --exclude .git'
        set -gx FZF_CTRL_T_COMMAND "$FZF_DEFAULT_COMMAND"
        set -gx FZF_ALT_C_COMMAND 'fd --type d --strip-cwd-prefix --hidden --follow --exclude .git'
    end

    set -gx FZF_DEFAULT_OPTS "
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
    set -gx FZF_CTRL_T_OPTS "--preview 'bat --style=numbers --color=always --line-range :300 {} 2>/dev/null || cat {}'"
    set -gx FZF_ALT_C_OPTS "--preview 'eza --tree --level=2 --color=always --icons=always {} 2>/dev/null || ls -la {}'"
end

# Greeting message (fastfetch)
if status is-interactive
    if type -q fastfetch
        fastfetch
    end
end

