import tomllib
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class History(unittest.TestCase):
    def test_local_history_configuration(self):
        config = tomllib.loads((ROOT/'atuin/.config/atuin/config.toml').read_text())
        for option in ('auto_sync', 'update_check', 'enter_accept'):
            self.assertIs(config[option], False)
