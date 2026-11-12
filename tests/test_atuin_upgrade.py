from contextlib import closing
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('atuin_upgrade', ROOT / 'setup/atuin_upgrade.py')
atuin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(atuin)


class AtuinCompatibility(unittest.TestCase):
    def database(self, directory):
        directory.mkdir(parents=True)
        path = directory / 'history.db'
        with closing(sqlite3.connect(path)) as db, db:
            db.execute('CREATE TABLE history (id TEXT PRIMARY KEY, command TEXT)')
            db.execute('INSERT INTO history VALUES (?, ?)', ('test-uuid', 'secret command'))
        return path

    def reader(self, source, destructive=False):
        def run(executable, arguments, environment=None):
            if arguments == ['info']:
                path = Path(environment['ATUIN_HOME']) / 'history.db' if environment else source
                return f'client db path: {path}\nmeta db path: {path.parent}/meta.db\n'.encode()
            self.assertIsNotNone(environment)
            self.assertNotEqual(Path(environment['ATUIN_HOME']) / 'history.db', source)
            with closing(sqlite3.connect(Path(environment['ATUIN_HOME']) / 'history.db')) as db, db:
                if executable == 'candidate':
                    db.execute('CREATE TABLE IF NOT EXISTS new_metadata (id TEXT)')
                    if destructive:
                        db.execute('DELETE FROM history')
                return b'\0'.join(row[0].encode() for row in db.execute('SELECT id FROM history'))
        return run

    def test_snapshot_and_forward_backward_checks_preserve_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.database(root / 'data')
            before = source.read_bytes()
            transaction = root / 'transaction'
            transaction.mkdir()
            with patch.object(atuin, '_run', side_effect=self.reader(source)):
                atuin.prepare('old', 'candidate', root, transaction)
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual((transaction / 'atuin').stat().st_mode & 0o777, 0o700)
            records = json.loads((transaction / 'atuin/databases.json').read_text())
            self.assertEqual(len(records), 1)
            backup = transaction / 'atuin' / records[0]['backup']
            self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
            with closing(sqlite3.connect(backup)) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM history').fetchone()[0], 1)

    def test_destructive_candidate_is_rejected_without_touching_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.database(root / 'data')
            transaction = root / 'transaction'
            transaction.mkdir()
            with patch.object(atuin, '_run', side_effect=self.reader(source, destructive=True)):
                with self.assertRaisesRegex(RuntimeError, 'history UUID set'):
                    atuin.prepare('old', 'candidate', root, transaction)
            with closing(sqlite3.connect(source)) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM history').fetchone()[0], 1)

    def test_sqlite_backup_includes_committed_wal_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.database(root / 'data')
            with closing(sqlite3.connect(source)) as writer, writer:
                writer.execute('PRAGMA journal_mode=WAL')
                writer.execute('INSERT INTO history VALUES (?, ?)', ('wal-uuid', 'another secret'))
                writer.commit()
                atuin._backup(source, root / 'backup/history.db')
                with closing(sqlite3.connect(root / 'backup/history.db')) as backup:
                    self.assertEqual(backup.execute('SELECT count(*) FROM history').fetchone()[0], 2)

    def test_sandbox_removes_inherited_data_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.dict(os.environ, {'ATUIN_DB_PATH': '/live/history.db', 'XDG_DATA_HOME': '/live'}):
                environment = atuin._sandbox(root / 'sandbox', root, [])
            self.assertNotIn('ATUIN_DB_PATH', environment)
            self.assertTrue(Path(environment['XDG_DATA_HOME']).is_relative_to(root))
            self.assertEqual(environment['ATUIN_SESSION'], '0' * 32)

    def test_no_previous_executable_refuses_existing_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.database(root / '.atuin/data')
            with self.assertRaisesRegex(RuntimeError, 'previous executable'):
                atuin.prepare(None, 'candidate', root, root)

    def test_rollback_checks_current_database_copy_without_restoring_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.database(root / 'data')
            active = root / '.local/bin/atuin'
            active.parent.mkdir(parents=True)
            active.touch()
            before = source.read_bytes()
            with patch.object(atuin, '_run', side_effect=self.reader(source)):
                atuin.verify_rollback('old', root, root)
            self.assertEqual(source.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
