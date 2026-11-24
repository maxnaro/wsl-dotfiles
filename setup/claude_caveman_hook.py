"""SessionStart hook: inject caveman ultra rules and mark the session active."""
import json
import os
from pathlib import Path
import sys
import time

CONTEXT = (
    'Ultracave mode is mandatory for this session. Apply `/caveman ultra` from '
    'the first reply, including progress updates. Use short fragments where '
    'clear, state each fact once, drop filler, articles and pleasantries. '
    'Preserve technical details, commands, paths, errors, numbers, units and '
    'qualifiers. Use full sentences for ambiguity, questions and consequential '
    'actions. Use normal prose for code comments and written artifacts. Keep '
    'it active until the user says "stop caveman" or "normal mode".'
)


def main():
    try:
        session = json.load(sys.stdin).get('session_id') or ''
    except ValueError:
        session = ''
    session = ''.join(c for c in session if c.isalnum() or c in '-_')
    if session:
        flags = Path(os.environ.get('CLAUDE_CONFIG_DIR') or Path.home() / '.claude') / 'caveman'
        flags.mkdir(parents=True, exist_ok=True)
        (flags / session).touch()
        cutoff = time.time() - 7 * 86400
        for old in flags.iterdir():
            try:
                if old.stat().st_mtime < cutoff:
                    old.unlink()
            except OSError:
                pass
    print(json.dumps({'hookSpecificOutput': {
        'hookEventName': 'SessionStart',
        'additionalContext': CONTEXT,
    }}))


if __name__ == '__main__':
    main()
