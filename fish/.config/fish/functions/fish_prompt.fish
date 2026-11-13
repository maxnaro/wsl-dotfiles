# ~/.config/fish/functions/fish_prompt.fish - Minimal CachyOS Pure-style prompt
function fish_prompt
    set -l command_status $status
    # First line: Current directory (in cyan) and git branch (in magenta)
    set -l cyan (set_color cyan)
    set -l magenta (set_color magenta)
    set -l normal (set_color normal)

    # Git branch
    set -l git_info ""
    if command -sq git
        set -l branch (git branch --show-current 2>/dev/null)
        if test -n "$branch"
            set git_info " $magenta($branch)$normal"
        end
    end

    # Print path and git branch on top line
    echo ""
    echo -s "$cyan" (prompt_pwd -d 0) "$normal" "$git_info"

    # Match Neovim's compact, transparent mode indicator.
    set -l mode_label N
    set -l mode_color cyan
    switch $fish_bind_mode
        case insert
            set mode_label I
            set mode_color green
        case visual
            set mode_label V
            set mode_color magenta
        case replace replace_one
            set mode_label R
            set mode_color red
    end
    echo -n -s (set_color $mode_color) "$mode_label " (set_color normal)

    # Second line: Symbol ❯ (cyan or red on error)
    if test $command_status -eq 0
        echo -n -s (set_color cyan) "❯ " (set_color normal)
    else
        echo -n -s (set_color red) "❯ " (set_color normal)
    end
end
