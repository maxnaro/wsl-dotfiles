# Auto-activate Python venvs on directory change in Fish
function _auto_venv --on-variable PWD --description "Automatically activate/deactivate Python venvs on cd"
    # Check for common venv folders in current directory
    for venv in .venv venv env
        if test -f "$venv/bin/activate.fish"
            if test "$VIRTUAL_ENV" != (pwd)/$venv
                source "$venv/bin/activate.fish"
            end
            return
        end
    end

    # Deactivate if leaving the project tree
    if test -n "$VIRTUAL_ENV"
        set -l venv_parent (dirname "$VIRTUAL_ENV")
        if test "$PWD" != "$venv_parent"; and not string match -qr -- '^'(string escape --style=regex -- "$venv_parent")/ "$PWD"
            # VIRTUAL_ENV can be inherited without Fish's deactivate function.
            if not functions -q deactivate
                return
            end
            deactivate
        end
    end
end
