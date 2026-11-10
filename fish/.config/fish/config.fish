# ~/.config/fish/config.fish - CachyOS-style Fish configuration

# Clean Windows /mnt/c paths from PATH to keep tab completion instant in WSL
if set -q WSL_DISTRO_NAME
    set -l clean_path
    for entry in $PATH
        if string match -q '/mnt/*' -- "$entry"; and not string match -q '*/Microsoft VS Code/bin' -- "$entry"
            continue
        end
        contains -- "$entry" $clean_path; or set -a clean_path "$entry"
    end
    set -gx PATH $clean_path
end

# User bin & Go PATH
fish_add_path --path ~/.local/bin
fish_add_path --path ~/.config/emacs/bin
fish_add_path --path (test -n "$GOPATH"; and echo "$GOPATH/bin"; or echo "$HOME/go/bin")

# Pyenv
if test -d "$HOME/.pyenv/bin"
    fish_add_path --path "$HOME/.pyenv/shims" "$HOME/.pyenv/bin"
end

if test -r "$HOME/.config/fish/local.fish"
    source "$HOME/.config/fish/local.fish"
end
status is-interactive; or return

# Enter the existing tmux server, or start one and restore its saved layout.
if test "$DOTFILES_NO_TMUX" != 1; and test -z "$TMUX"; and isatty stdin; and isatty stdout; and type -q tmux
    if tmux has-session 2>/dev/null
        tmux attach-session
    else
        tmux new-session
    end
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

# Zoxide smart directory jumping (z, zi)
if type -q zoxide
    zoxide init fish | source
end

# Greeting message (pokemon-terminal-greeting)
if status is-interactive
    if type -q pokemon-greeting
        pokemon-greeting --speed 0
    else if type -q fastfetch
        fastfetch
    end
end

if type -q atuin; and not set -q _dotfiles_atuin_initialized
    atuin init fish --disable-up-arrow | source
    set -g _dotfiles_atuin_initialized 1
end
