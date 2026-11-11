"""Failure-path tests runnable with the standard library."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from deterline import file0, sandbox, transactions


class TransactionTests(unittest.TestCase):
    def test_file0_has_exact_crlf(self):
        self.assertEqual(file0._serialize_file0("Frisk", [1, 20]),
                         b"Frisk\r\n1 \r\n20 \r\n")

    def test_backup_failure_does_not_touch_original(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "file0"
            path.write_bytes(b"old")
            with patch("deterline.paths.backup_file", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    transactions.write_one(path, b"new")
            self.assertEqual(path.read_bytes(), b"old")

    def test_second_replace_failure_rolls_back_first(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "undertale.ini"
            second = Path(directory) / "file0"
            first.write_bytes(b"ini-old")
            second.write_bytes(b"file0-old")
            real_replace = transactions.os.replace

            def fail_second(src, dst):
                if Path(dst) == second.resolve():
                    raise OSError("injected failure")
                return real_replace(src, dst)

            with patch("deterline.transactions.os.replace", side_effect=fail_second):
                with self.assertRaises(OSError):
                    transactions.write_many({first: b"ini-new", second: b"file0-new"})
            self.assertEqual(first.read_bytes(), b"ini-old")
            self.assertEqual(second.read_bytes(), b"file0-old")

    def test_sandbox_rejects_changed_source(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Path(directory) / "game.ios"
            game.write_bytes(b"original")
            copy = sandbox.ensure_workspace(game)
            sandbox.check_baseline(game, copy)
            game.write_bytes(b"changed")
            with self.assertRaisesRegex(RuntimeError, "已变化"):
                sandbox.check_baseline(game, sandbox.sandbox_path(game))

    def test_sandbox_rejects_unknown_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Path(directory) / "game.ios"
            game.write_bytes(b"original")
            with self.assertRaisesRegex(RuntimeError, "缺少基线"):
                sandbox.check_baseline(game, sandbox.sandbox_path(game))

    def test_plan_rejects_target_changed_after_preparation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "file0"
            path.write_bytes(b"initial save")
            plan = transactions.EditPlan((transactions.FileEdit.prepare(path, b"edited"),))
            path.write_bytes(b"newer save")
            with self.assertRaisesRegex(RuntimeError, "已变化"):
                plan.commit()
            self.assertEqual(path.read_bytes(), b"newer save")


if __name__ == "__main__":
    unittest.main()
