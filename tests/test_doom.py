import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DoomBootstrap(unittest.TestCase):
    def test_bootstrap_scenarios(self):
        for scenario in ('fresh', 'existing', 'conflict', 'old', 'clone_failure', 'install_failure'):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as tmp:
                home = Path(tmp)
                binaries = home / 'bin'
                binaries.mkdir()
                log = home / 'commands'
                scripts = {
                    'emacs': '#!/bin/bash\n[[ $SCENARIO != old ]]\n',
                    'git': '''#!/bin/bash
echo "git $*" >> "$LOG"
[[ $SCENARIO != clone_failure ]] || exit 23
if [[ $1 == clone ]]; then
    mkdir -p "$4/bin" "$4/lisp"
    touch "$4/lisp/doom.el"
    cp "$HOME/bin/fake-doom" "$4/bin/doom"
fi
''',
                    'fake-doom': '''#!/bin/bash
echo "doom $*" >> "$LOG"
[[ $SCENARIO != install_failure ]]
''',
                }
                for name, content in scripts.items():
                    path = binaries / name
                    path.write_text(content)
                    path.chmod(0o755)
                destination = home / '.config/emacs'
                if scenario in ('existing', 'conflict'):
                    destination.mkdir(parents=True)
                    (destination / 'sentinel').write_text('preserve')
                    if scenario == 'existing':
                        (destination / 'bin').mkdir()
                        (destination / 'lisp').mkdir()
                        (destination / 'lisp/doom.el').touch()
                        doom = destination / 'bin/doom'
                        doom.write_text(scripts['fake-doom'])
                        doom.chmod(0o755)
                env = dict(os.environ, HOME=tmp, PATH=f'{binaries}:/usr/bin:/bin',
                           SCENARIO=scenario, LOG=str(log))
                result = subprocess.run(['bash', str(ROOT / 'setup/install_doom.sh')],
                                        env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode == 0, scenario in ('fresh', 'existing'), result.stderr)
                commands = log.read_text() if log.exists() else ''
                if scenario == 'fresh':
                    self.assertIn('checkout --detach 59cdaa32', commands)
                    self.assertIn('submodule update --init --recursive', commands)
                    self.assertIn('install --no-config --no-env', commands)
                if scenario == 'existing':
                    self.assertIn('--force sync', commands)
                    self.assertNotIn('git ', commands)
                if scenario in ('existing', 'conflict'):
                    self.assertEqual((destination / 'sentinel').read_text(), 'preserve')
                if scenario in ('old', 'conflict'):
                    self.assertEqual(commands, '')
                if scenario == 'clone_failure':
                    self.assertFalse(destination.exists())
                    self.assertEqual(list((home / '.config').glob('.doom-install.*')), [])
