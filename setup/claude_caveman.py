"""Register a Claude Code SessionStart hook that enforces `/caveman ultra`
and a status line that shows when it is active."""
import json
import os
from pathlib import Path
import tempfile

HERE = Path(__file__).resolve().parent
COMMAND = f"python3 '{HERE / 'claude_caveman_hook.py'}'"
STATUSLINE = f"'{HERE / 'claude_statusline.sh'}'"
LEGACY_STATUSLINE = 'input=$(cat); cwd=$(echo "$input" | jq -r'
LEGACY_HOOK = "echo 'Ultracave mode is mandatory"
MATCHER = 'startup|resume|clear|compact'


def configure(path):
    path = path.resolve()
    try:
        settings = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        settings = {}
    if not isinstance(settings, dict):
        raise ValueError('expected a JSON object')

    hooks = settings.setdefault('hooks', {})
    if not isinstance(hooks, dict):
        raise ValueError('expected hooks to be an object')
    entries = hooks.setdefault('SessionStart', [])
    if not isinstance(entries, list):
        raise ValueError('expected hooks.SessionStart to be a list')
    entries[:] = [
        e for e in entries
        if not (isinstance(e, dict) and any(
            isinstance(h, dict) and str(h.get('command', '')).startswith(LEGACY_HOOK)
            for h in e.get('hooks', [])
        ))
    ]
    if not any(
        isinstance(e, dict) and any(
            isinstance(h, dict) and h.get('command') == COMMAND for h in e.get('hooks', [])
        ) for e in entries
    ):
        entries.append({'matcher': MATCHER, 'hooks': [{'type': 'command', 'command': COMMAND}]})

    status = settings.get('statusLine')
    if not isinstance(status, dict) or str(status.get('command', '')).startswith(
        (LEGACY_STATUSLINE, STATUSLINE)
    ) or not status:
        settings['statusLine'] = {
            'type': 'command', 'command': STATUSLINE, 'padding': 0, 'refreshInterval': 10,
        }

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(settings, stream, indent=2, ensure_ascii=False)
            stream.write('\n')
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


if __name__ == '__main__':
    directory = Path(os.environ.get('CLAUDE_CONFIG_DIR') or Path.home() / '.claude')
    path = directory / 'settings.json'
    try:
        configure(path)
    except (OSError, ValueError) as error:
        raise SystemExit(f'{path}: {error}') from error
