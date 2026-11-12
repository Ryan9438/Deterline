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


class RecoveryMatrixTests(unittest.TestCase):
    """03 §2.2 故障矩阵（2026-11-12 2.2a 补齐）：竞争 / 回滚不完整 /
    工作区清单三类此前零覆盖。全部 tmp 隔离，零真实路径。"""

    def test_duplicate_targets_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "file0"
            path.write_bytes(b"old")
            edits = (transactions.FileEdit.prepare(path, b"a"),
                     transactions.FileEdit.prepare(path, b"b"))
            with self.assertRaises(ValueError):
                transactions.EditPlan(edits)

    def test_backup_archive_and_latest_created_on_success(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "file0"
            path.write_bytes(b"old")
            transactions.write_one(path, b"new")
            self.assertEqual(path.read_bytes(), b"new")
            self.assertEqual(path.with_suffix(path.suffix + ".bak").read_bytes(),
                             b"old", "latest .bak 必须是写入前内容")
            self.assertTrue(list(path.parent.glob("file0.bak.*")),
                             "时间戳归档必须生成")

    def test_second_plan_loses_baseline_race(self):
        """竞争（同进程模拟）：两个 plan 先后 prepare 同一目标，先提交者赢，
        后提交者必须被基线校验拒绝（flock 串行 + 基线漂移双重防线）。"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "file0"
            path.write_bytes(b"old")
            winner = transactions.EditPlan(
                (transactions.FileEdit.prepare(path, b"winner"),))
            loser = transactions.EditPlan(
                (transactions.FileEdit.prepare(path, b"loser"),))
            winner.commit()
            with self.assertRaisesRegex(RuntimeError, "已变化"):
                loser.commit()
            self.assertEqual(path.read_bytes(), b"winner")

    def test_concurrent_commits_single_winner(self):
        """竞争（真并发）：两线程提交同一目标，文件锁串行化后恰有一个成功、
        一个基线拒绝，最终内容与胜者一致。
        （审核席 B P2-1：在 os.replace 前注入受控延迟拉大 TOCTOU 窗口——
        锁被移除时两线程都能通过基线检查形成双胜者，测试必红；有锁时
        后者只能在胜者提交后进入、基线拒绝。）"""
        import threading
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "file0"
            path.write_bytes(b"old")
            plans = {name: transactions.EditPlan(
                         (transactions.FileEdit.prepare(path, name.encode()),))
                     for name in ("winner", "loser")}
            real_replace = transactions.os.replace
            target = path.resolve()

            def slow_replace(src, dst):
                if Path(dst) == target:
                    import time as _time
                    _time.sleep(0.2)  # 拉大窗口：无锁时后者可在此期间过基线检查
                return real_replace(src, dst)

            results = {}

            def commit(name):
                try:
                    with patch("deterline.transactions.os.replace",
                               side_effect=slow_replace):
                        plans[name].commit()
                    results[name] = "ok"
                except RuntimeError:
                    results[name] = "rejected"

            threads = [threading.Thread(target=commit, args=(n,))
                       for n in ("winner", "loser")]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            self.assertEqual(sorted(results.values()), ["ok", "rejected"],
                             f"文件锁必须保证恰有一个胜者: {results}")
            winner_name = next(n for n, r in results.items() if r == "ok")
            self.assertEqual(path.read_bytes(), winner_name.encode())

    def test_incomplete_rollback_preserves_copies(self):
        """回滚不完整：恢复副本必须保留在目标旁（最后防线），错误聚合报告。"""
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "undertale.ini"
            second = Path(directory) / "file0"
            first.write_bytes(b"ini-old")
            second.write_bytes(b"f0-old")
            real_replace = transactions.os.replace
            state = {"first_replaced": False}

            def fail_replace(src, dst):
                dst_path = Path(dst)
                if dst_path == second.resolve():
                    raise OSError("injected failure")
                if dst_path == first.resolve():
                    # 初次替换放行；回滚阶段的第二次替换注入失败
                    # （backup_file 写 .bak 归档的 os.replace dst ≠ 目标本体，不受影响）
                    if state["first_replaced"]:
                        raise OSError("rollback failure")
                    result = real_replace(src, dst)
                    state["first_replaced"] = True
                    return result
                return real_replace(src, dst)

            with patch("deterline.transactions.os.replace",
                       side_effect=fail_replace):
                with self.assertRaisesRegex(RuntimeError, "回滚不完整"):
                    transactions.write_many({first: b"ini-new",
                                             second: b"f0-new"})
            self.assertEqual(second.read_bytes(), b"f0-old")
            self.assertEqual(first.read_bytes(), b"ini-new",
                             "回滚失败时第一目标保持已替换内容")
            leftovers = list(first.parent.glob(".undertale.ini.*.new"))
            self.assertTrue(leftovers,
                            "回滚副本必须保留供人工恢复（SIGKILL 同型残留）")

    def test_sandbox_rejects_corrupted_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Path(directory) / "game.ios"
            game.write_bytes(b"original")
            copy = sandbox.ensure_workspace(game)
            copy.with_name(copy.name + ".json").write_text("{bad",
                                                           encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "损坏"):
                sandbox.check_baseline(game, copy)

    def _commit_edit_like_game_edit(self, game, copy, new_content: bytes):
        """按生产形态构造一次工作区编辑：artifact 暂存文件 + 副本内容
        FileEdit + record_edit manifest 追加，同一 EditPlan 原子提交
        （审核席 B P3-4：正控不得用 record_edit(copy, copy) 恒真式）。"""
        artifact = copy.parent / f"{copy.name}.artifact-tmp"
        artifact.write_bytes(new_content)
        edits = [
            transactions.FileEdit(copy.resolve(), artifact,
                                  transactions.fingerprint(copy),
                                  backup=False),
        ]
        record = sandbox.record_edit(copy, artifact, "test-edit")
        if record is not None:
            edits.append(record)
        transactions.EditPlan(tuple(edits)).apply()
        artifact.unlink(missing_ok=True)

    def test_sandbox_rejects_copy_history_mismatch(self):
        """工作区产物与清单不匹配：副本内容 ≠ 清单末条 sha → 拒绝应用。"""
        with tempfile.TemporaryDirectory() as directory:
            game = Path(directory) / "game.ios"
            game.write_bytes(b"original")
            copy = sandbox.ensure_workspace(game)
            self._commit_edit_like_game_edit(game, copy, b"EDITED")
            copy.write_bytes(b"TAMPERED")
            with self.assertRaisesRegex(RuntimeError, "清单末条记录不符"):
                sandbox.check_baseline(game, copy)

    def test_sandbox_history_consistent_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Path(directory) / "game.ios"
            game.write_bytes(b"original")
            copy = sandbox.ensure_workspace(game)
            self._commit_edit_like_game_edit(game, copy, b"EDITED")
            self.assertEqual(copy.read_bytes(), b"EDITED")
            self.assertEqual(sandbox.check_baseline(game, copy),
                             transactions.fingerprint(game))

    def test_sandbox_tolerates_malformed_history_shapes(self):
        """审核席 A P2-1 / B P3-1：history 畸形（dict/int/None/元素非 dict/
        sha 空串）一律按无记录跳过校验，不得 KeyError/TypeError 逃逸。"""
        import json as _json
        with tempfile.TemporaryDirectory() as directory:
            game = Path(directory) / "game.ios"
            game.write_bytes(b"original")
            copy = sandbox.ensure_workspace(game)
            manifest = copy.with_name(copy.name + ".json")
            base = {"source_sha256": transactions.fingerprint(game),
                    "source": str(game.resolve())}
            for history in ({"k": "v"}, 7, None, ["str-entry"],
                            [{"no_sha": 1}], [{"sha256": ""}]):
                record = dict(base)
                record["history"] = history
                manifest.write_text(_json.dumps(record), encoding="utf-8")
                self.assertEqual(sandbox.check_baseline(game, copy),
                                 transactions.fingerprint(game),
                                 f"history={history!r} 应跳过校验不崩溃")

    def test_sandbox_missing_copy_reported(self):
        """副本文件丢失（竞争窗口/外部删除）：明确报错，不得 TypeError 逃逸。"""
        with tempfile.TemporaryDirectory() as directory:
            game = Path(directory) / "game.ios"
            game.write_bytes(b"original")
            copy = sandbox.ensure_workspace(game)
            self._commit_edit_like_game_edit(game, copy, b"EDITED")
            copy.unlink()
            with self.assertRaisesRegex(RuntimeError, "副本已丢失"):
                sandbox.check_baseline(game, copy)


if __name__ == "__main__":
    unittest.main()
