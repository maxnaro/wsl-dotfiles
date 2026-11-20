"""Disable Claude Code commit attribution in the user's settings."""
import json
import os
from pathlib import Path
import tempfile


def configure(path):
    path = path.resolve()
    try:
        settings = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        settings = {}
    if not isinstance(settings, dict):
        raise ValueError('expected a JSON object')

    attribution = settings.get('attribution', {})
    if attribution is False:
        return
    if not isinstance(attribution, dict):
        raise ValueError('expected attribution to be an object or false')
    if attribution.get('commit') == '':
        return
    if settings.get('includeCoAuthoredBy') is False and not {'commit', 'pr'} & attribution.keys():
        attribution['pr'] = ''
    attribution['commit'] = ''
    settings['attribution'] = attribution

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
