"""Register a Claude Code SessionStart hook that enforces `/caveman ultra`."""
import json
import os
from pathlib import Path
import tempfile

MESSAGE = (
    'Ultracave mode is mandatory for this session. Apply `/caveman ultra` from '
    'the first reply, including progress updates, and keep it active until the '
    'user says "stop caveman" or "normal mode".'
)
COMMAND = f"echo '{MESSAGE}'"
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
    for entry in entries:
        if isinstance(entry, dict) and any(
            isinstance(h, dict) and h.get('command') == COMMAND for h in entry.get('hooks', [])
        ):
            return
    entries.append({'matcher': MATCHER, 'hooks': [{'type': 'command', 'command': COMMAND}]})

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
