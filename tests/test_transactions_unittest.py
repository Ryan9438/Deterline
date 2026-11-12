"""Failure-path tests runnable with the standard library."""

import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from deterline import file0, sandbox, transactions
from deterline.cmds import recovery


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


def _redirect(buffer):
    import contextlib
    return contextlib.redirect_stdout(buffer)


class TestRunJournal(unittest.TestCase):
    """03 §2.2b：可恢复运行记录（journal）生命周期。"""

    def _targets(self, directory):
        targets = [Path(directory) / f"t{i}.bin" for i in range(3)]
        for t in targets:
            t.write_bytes(b"OLD-" + t.name.encode())
        return targets

    def test_success_removes_journal_and_dirs(self):
        with tempfile.TemporaryDirectory() as directory:
            targets = self._targets(directory)
            transactions.write_many({t: b"NEW" for t in targets})
            self.assertFalse(transactions.journal_dir_for(targets[0]).exists(),
                             "成功提交后 journal 目录必须整体摘除")

    def test_baseline_reject_marks_aborted_clean(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "t0.bin"
            target.write_bytes(b"OLD")
            plan = transactions.EditPlan(
                (transactions.FileEdit.prepare(target, b"NEW"),))
            target.write_bytes(b"EXTERNAL")
            with self.assertRaisesRegex(RuntimeError, "已变化"):
                plan.commit()
            journals = list(transactions.journal_dir_for(target).glob("*.json"))
            self.assertEqual(len(journals), 1, "失败路径必须保留运行记录")
            record = json.loads(journals[0].read_text(encoding="utf-8"))
            self.assertEqual(record["state"], "aborted-clean")
            self.assertIn("已变化", record["error"])

    def test_rollback_failure_marks_aborted_partial(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "a.txt"
            second = Path(directory) / "b.txt"
            first.write_bytes(b"ini-old")
            second.write_bytes(b"f0-old")
            real_replace = transactions.os.replace
            state = {"replaced": False}

            def fail_replace(src, dst):
                if Path(dst) == second.resolve():
                    raise OSError("injected failure")
                if Path(dst) == first.resolve():
                    if state["replaced"]:
                        raise OSError("rollback failure")
                    result = real_replace(src, dst)
                    state["replaced"] = True
                    return result
                return real_replace(src, dst)

            with patch("deterline.transactions.os.replace",
                       side_effect=fail_replace):
                with self.assertRaisesRegex(RuntimeError, "回滚不完整"):
                    transactions.write_many({first: b"a-new",
                                             second: b"b-new"})
            journals = list(transactions.journal_dir_for(first).glob("*.json"))
            record = json.loads(journals[0].read_text(encoding="utf-8"))
            self.assertEqual(record["state"], "aborted-partial")
            self.assertIn("rollback failure", record["error"],
                          "error 字段必须记录恢复失败原因（回滚不完整聚合前）")
            rollback_path = record["targets"][0]["rollback"]
            self.assertTrue(rollback_path and Path(rollback_path).exists(),
                            "aborted-partial 记录的恢复副本必须真实存在")

    def test_preview_writes_no_journal(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "t0.bin"
            target.write_bytes(b"OLD")
            plan = transactions.EditPlan(
                (transactions.FileEdit.prepare(target, b"NEW"),))
            plan.preview()
            self.assertFalse(transactions.journal_dir_for(target).exists(),
                             "预览零写盘——不得创建运行记录")

    def test_pending_journal_written_before_first_stage(self):
        """核心不变量（审核席 A P2-3）：首个暂存文件产生前，pending 记录
        必须已在盘上——否则 staging 窗口的 SIGKILL 完全不可识别。"""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "t0.bin"
            target.write_bytes(b"OLD")
            real_stage = transactions._stage
            observed = {}

            def spy_stage(stage_target, content, mode):
                if not observed:
                    journals = list(transactions.journal_dir_for(
                        target).glob("*.json"))
                    self.assertEqual(len(journals), 1,
                                     "首个 staged 产生前 journal 必须已落盘")
                    record = json.loads(journals[0].read_text(encoding="utf-8"))
                    self.assertEqual(record["state"], "pending")
                    observed["ok"] = True
                return real_stage(stage_target, content, mode)

            with patch("deterline.transactions._stage",
                       side_effect=spy_stage):
                transactions.write_one(target, b"NEW")
            self.assertTrue(observed, "spy 未被触发（patch 目标错误？）")

    def test_refuses_when_unfinished_journal_exists(self):
        """再次运行识别（03 §2.2c）：同名目标存在未完结记录 → 拒绝并指引。"""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "t0.bin"
            target.write_bytes(b"OLD")
            journal_root = transactions.journal_dir_for(target)
            journal_root.mkdir(parents=True)
            (journal_root / "stale.json").write_text(json.dumps({
                "schema": transactions.JOURNAL_SCHEMA, "id": "stale",
                "state": "pending",
                "targets": [{"path": str(target)}],
            }), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "运行记录"):
                transactions.write_one(target, b"NEW")
            self.assertEqual(target.read_bytes(), b"OLD", "拒绝时零写入")
            (journal_root / "stale.json").unlink()
            transactions.write_one(target, b"NEW")
            self.assertEqual(target.read_bytes(), b"NEW")


class TestRecoveryScan(unittest.TestCase):
    """03 §2.2c：recovery-scan 窗口分类（合成 journal，零 UTMT）。"""

    def _scan(self, root, json_out=False):
        import io as _io
        import contextlib as _ctxlib
        buf = _io.StringIO()
        with _ctxlib.redirect_stdout(buf):
            code = recovery.cmd_recovery_scan(root, str(root),
                                              json_out=json_out)
        return buf.getvalue(), code

    def _write_journal(self, root, jid, state, entries, extra=None):
        journal_dir = root / ".deterline" / "journal"  # 扫描语义：root 即扫描根
        journal_dir.mkdir(parents=True, exist_ok=True)
        record = {"schema": transactions.JOURNAL_SCHEMA, "id": jid,
                  "state": state, "targets": entries}
        if extra:
            record.update(extra)
        path = journal_dir / f"{jid}.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        return path

    def test_no_findings_exit0_and_json_pure(self):
        with tempfile.TemporaryDirectory() as directory:
            out, code = self._scan(Path(directory))
            self.assertEqual(code, 0)
            self.assertIn("无未完结", out)
            payload_buf, code2 = self._scan(Path(directory), json_out=True)
            self.assertEqual(code2, 0)
            payload = json.loads(payload_buf)
            self.assertEqual(payload["schema"], "deterline.recovery-scan/v1")

    def test_not_started_window(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "t0.bin"
            target.write_bytes(b"OLD")
            staged = root / ".t0.bin.x.new"
            staged.write_bytes(b"NEW")
            self._write_journal(root, "j1", "committing", [{
                "path": str(target),
                "before": transactions.fingerprint(target),
                "after": transactions.fingerprint(staged),
                "rollback": None, "staged": str(staged)}])
            out, code = self._scan(root)
            self.assertEqual(code, 1)
            self.assertIn("目标未被触及", out)

    def test_done_confirm_window(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "t0.bin"
            target.write_bytes(b"NEW")
            self._write_journal(root, "j1", "committing", [{
                "path": str(target), "before": None,
                "after": transactions.fingerprint(target),
                "rollback": None, "staged": None}])
            out, code = self._scan(root)
            self.assertEqual(code, 1)
            self.assertIn("全部目标已写入", out)

    def test_interrupted_window_offers_both_directions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            done = root / "t0.bin"       # 已替换 → 可回滚
            pending = root / "t1.bin"    # 未替换 → 可完成
            done.write_bytes(b"NEW0")
            pending.write_bytes(b"OLD1")
            rollback_copy = root / ".t0.bin.r.new"
            rollback_copy.write_bytes(b"OLD0")
            staged_copy = root / ".t1.bin.s.new"
            staged_copy.write_bytes(b"NEW1")
            self._write_journal(root, "j1", "committing", [
                {"path": str(done), "before": "00",
                 "after": transactions.fingerprint(done),
                 "rollback": str(rollback_copy), "staged": None},
                {"path": str(pending), "before": transactions.fingerprint(pending),
                 "after": transactions.fingerprint(staged_copy),
                 "rollback": None, "staged": str(staged_copy)}])
            out, code = self._scan(root)
            self.assertEqual(code, 1)
            self.assertIn("替换中断", out)
            self.assertIn("回滚该目标", out)
            self.assertIn("完成该目标", out)

    def test_suspicious_external_modification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "t0.bin"
            target.write_bytes(b"NEITHER")
            self._write_journal(root, "j1", "committing", [{
                "path": str(target), "before": "aa", "after": "bb",
                "rollback": None, "staged": None}])
            out, code = self._scan(root)
            self.assertEqual(code, 1)
            self.assertIn("外部修改", out)

    def test_corrupt_and_alien_journals_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            journal_dir = root / ".deterline" / "journal"
            journal_dir.mkdir(parents=True, exist_ok=True)
            (journal_dir / "bad.json").write_text("{not json", encoding="utf-8")
            (journal_dir / "alien.json").write_text(
                json.dumps({"schema": "other/v9"}), encoding="utf-8")
            out, code = self._scan(root)
            self.assertEqual(code, 1)
            self.assertIn("corrupt-journal", out)

    def test_orphan_staged_listed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            orphan = root / ".mystery.bin.xyz.new"
            orphan.write_bytes(b"junk")
            journal_tmp = root / ".journal.tmp.new"   # journal 自身暂存，忽略
            journal_tmp.write_bytes(b"x")
            out, code = self._scan(root)
            self.assertEqual(code, 1)
            self.assertIn("orphan-staged", out)
            self.assertIn("mystery", out)
            self.assertNotIn("journal.tmp", out)

    def test_both_locations_failed_exit2(self):
        """审核席 B P3-2：双侧定位失败不得报"干净"（对齐 backup-index=2）。"""
        import io as _io
        import contextlib as _ctxlib
        buf = _io.StringIO()
        err = _io.StringIO()
        with _ctxlib.redirect_stdout(buf), _ctxlib.redirect_stderr(err):
            code = recovery.cmd_recovery_scan(
                None, "/tmp/dl_missing_dir_9f3c1")
        self.assertEqual(code, 2)
        self.assertIn("未扫描任何目录", buf.getvalue())

    def test_aborted_partial_offers_rollback_cp(self):
        """审核席 A P3-1/B P3-4：aborted-partial 且回滚副本在盘 → 给 cp 出口。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "t0.bin"
            target.write_bytes(b"NEW0")   # 已替换
            rollback_copy = root / ".t0.bin.r.new"
            rollback_copy.write_bytes(b"OLD0")
            self._write_journal(root, "j1", "aborted-partial", [{
                "path": str(target), "before": "aa",
                "after": transactions.fingerprint(target),
                "rollback": str(rollback_copy), "staged": None}],
                extra={"error": "a.txt: 恢复副本 … (rollback failure)"})
            out, code = self._scan(root)
            self.assertEqual(code, 1)
            self.assertIn("回滚该目标: cp", out)

    def test_empty_targets_treated_as_corrupt(self):
        """审核席 A P3-3：targets 缺失/空的畸形记录不得误判 done-confirm。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_journal(root, "j1", "committing", [])
            out, code = self._scan(root)
            self.assertEqual(code, 1)
            self.assertIn("corrupt-journal", out)

    def test_unknown_state_flagged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "t0.bin"
            target.write_bytes(b"OLD")
            self._write_journal(root, "j1", "weird-state", [{
                "path": str(target),
                "before": transactions.fingerprint(target),
                "after": None, "rollback": None, "staged": None}])
            out, code = self._scan(root)
            self.assertEqual(code, 1)
            self.assertIn("state 字段不在已知状态机内", out)


class TestSigkillRecovery(unittest.TestCase):
    """03 §2.2c：子进程强制中止中断点 → 再次运行识别未完成操作。

    确定性设计：子进程在替换第二个目标前悬挂（patch os.replace），
    父进程轮询到「journal=committing 且第 1 目标已替换」后 kill -9 ——
    精确制造"部分替换"窗口，不靠时运。"""

    CHILD_SCRIPT = """
import sys, time
from pathlib import Path
sys.path.insert(0, r"{scripts}")
from deterline import transactions
root = Path(sys.argv[1])
targets = [root / f"t{{i}}.bin" for i in range(3)]
for t in targets:
    t.write_bytes(b"OLD-" + t.name.encode())
real_replace = transactions.os.replace

def slow_replace(src, dst):
    if Path(dst).name == "t1.bin":
        time.sleep(30)  # 悬挂点：父进程必须在此窗口内 kill
    return real_replace(src, dst)

transactions.os.replace = slow_replace
transactions.write_many({{t: (b"NEW-" + t.name.encode()) for t in targets}})
"""

    def test_kill_during_replace_is_identified(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = str((Path(__file__).resolve().parent.parent / "scripts"))
            script = root / "child.py"
            script.write_text(self.CHILD_SCRIPT.format(scripts=scripts),
                              encoding="utf-8")
            proc = subprocess.Popen([sys.executable, str(script), str(root)],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
            try:
                journal = None
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    journals = list(transactions.journal_dir_for(
                        root / "t0.bin").glob("*.json"))
                    if journals:
                        record = json.loads(
                            journals[0].read_text(encoding="utf-8"))
                        if (record.get("state") == "committing"
                                and (root / "t0.bin").read_bytes() == b"NEW-t0.bin"):
                            journal = journals[0]
                            break
                    time.sleep(0.05)
                self.assertIsNotNone(journal,
                                     "20s 内未到达部分替换窗口（子进程卡死？）")
                proc.kill()
                proc.wait(timeout=10)
            finally:
                if proc.poll() is None:
                    proc.kill()

            self.assertTrue(journal.exists(),
                            "SIGKILL 后运行记录必须幸存（原子写 + fsync）")
            payload, code = self._scan_json(root)
            self.assertEqual(code, 1)
            self.assertFalse(any(f["kind"] == "orphan-staged"
                                 for f in payload["findings"]),
                             "journal 引用的副本不得被误报为孤儿"
                             "（/var 与 /private/var 拼写差，A/B P2-1）")
            finding = next(f for f in payload["findings"]
                           if f["kind"] == "run-journal")
            self.assertEqual(finding["level"], "interrupted")
            classes = {Path(t["path"]).name: t["class"]
                       for t in finding["targets"]}
            self.assertEqual(classes["t0.bin"], "after")
            self.assertEqual(classes["t1.bin"], "before")
            self.assertEqual(classes["t2.bin"], "before")
            self.assertTrue(any("回滚该目标" in a for a in finding["actions"]),
                            "已替换目标必须给出回滚指引（回滚副本幸存）")

    def _scan_json(self, root):
        import io as _io
        import contextlib as _ctxlib
        buf = _io.StringIO()
        with _ctxlib.redirect_stdout(buf):
            code = recovery.cmd_recovery_scan(root, str(root), json_out=True)
        return json.loads(buf.getvalue()), code


if __name__ == "__main__":
    unittest.main()
