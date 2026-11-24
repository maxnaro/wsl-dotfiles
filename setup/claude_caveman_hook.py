"""Claude Code hook that enforces caveman ultra.

SessionStart injects the full rule set and marks the session active.
UserPromptSubmit re-injects a short reminder on every turn while the session
is active. Asking for normal mode writes a `<session>.off` marker, which stops
the reminders and hides the status line badge.
"""
import json
import os
from pathlib import Path
import re
import sys
import time

RULES = (
    'CAVEMAN ULTRA MODE IS ACTIVE. It applies to every reply in this session, '
    'including the first one and all progress updates, and it overrides any '
    'default verbosity or tone guidance.\n'
    'Rules:\n'
    '- Fragments, not sentences. Drop articles, filler, hedging, pleasantries '
    'and transitions ("so", "however", "let me").\n'
    '- Abbreviate common terms: config, repo, fn, impl, req, res, DB, auth, '
    'env, dir, deps, msg.\n'
    '- Arrows for cause and flow: "hook fires -> flag set -> badge shows".\n'
    '- One word when one word is enough. State each fact once. No recap.\n'
    '- Max ~3 short bullets per list unless the content needs more.\n'
    '- Keep exact: code, commands, paths, errors, numbers, units, names and '
    'qualifiers.\n'
    '- Exceptions (use clear full sentences): genuine ambiguity, questions to '
    'the user, warnings before destructive or consequential actions.\n'
    '- Code, code comments, commit messages and written artifacts use normal '
    'prose.\n'
    '- Stays on until the user says "stop caveman" or "normal mode".\n'
    'Example: "Test hit real network -> slow. Mock `fetchUser`. 4.2s -> 0.3s."'
)
REMINDER = (
    'Reminder: caveman ultra active. Fragments, abbreviations, arrows, no '
    'filler. Keep code, paths, errors and numbers exact.'
)
STOP = re.compile(r'\b(stop caveman|normal mode|talk normal|drop caveman)\b', re.I)


def flag_path(session):
    session = ''.join(c for c in session if c.isalnum() or c in '-_')
    if not session:
        return None
    root = Path(os.environ.get('CLAUDE_CONFIG_DIR') or Path.home() / '.claude')
    return root / 'caveman' / session


def prune(directory):
    cutoff = time.time() - 7 * 86400
    for old in directory.iterdir():
        try:
            if old.stat().st_mtime < cutoff:
                old.unlink()
        except OSError:
            pass


def emit(event, context):
    print(json.dumps({'hookSpecificOutput': {
        'hookEventName': event,
        'additionalContext': context,
    }}))


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        data = {}
    event = data.get('hook_event_name') or 'SessionStart'
    flag = flag_path(data.get('session_id') or '')
    off = flag and flag.with_name(flag.name + '.off')

    if event == 'UserPromptSubmit':
        if STOP.search(data.get('prompt') or ''):
            if flag:
                flag.parent.mkdir(parents=True, exist_ok=True)
                off.touch()
            return
        if not (off and off.exists()):
            emit(event, REMINDER)
        return

    # SessionStart: a fresh session or /clear always turns the mode on; a
    # resume or compaction keeps an explicit "normal mode" choice.
    if flag:
        flag.parent.mkdir(parents=True, exist_ok=True)
        if (data.get('source') or 'startup') in ('startup', 'clear'):
            off.unlink(missing_ok=True)
        flag.touch()
        prune(flag.parent)
    if not (off and off.exists()):
        emit(event, RULES)


if __name__ == '__main__':
    main()
