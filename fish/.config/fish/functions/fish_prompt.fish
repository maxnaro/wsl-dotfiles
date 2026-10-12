# ~/.config/fish/functions/fish_prompt.fish - Minimal CachyOS Pure-style prompt
function fish_prompt
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

    # Second line: Symbol ❯ (cyan or red on error)
    if test $status -eq 0
        echo -n -s (set_color cyan) "❯ " (set_color normal)
    else
        echo -n -s (set_color red) "❯ " (set_color normal)
    end
end
