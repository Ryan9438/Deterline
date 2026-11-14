"""06 §4 执行入口（值守场次实现，2026-11-14）：recovery-apply / recovery-clean /
backup-prune --commit 的离线矩阵。

全部 tmp 隔离零 UTMT；合成 journal 记录（test_transactions_unittest.TestRecoveryScan
夹具风格）。apply = 逐目标 os.replace + journal 复用方案 A（不删记录，完成后
scan 重分类）；clean = 现场重分类（绝不信任存量 state）；prune --commit =
现场重算 + 硬前置 + 可逆移入 pruned/<ts>/。
"""

import contextlib
import hashlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "tests"))

import modify_save as ms  # noqa: E402
import fixtures_save  # noqa: E402
import deterline.paths  # noqa: E402
import deterline.transactions  # noqa: E402
from deterline.cmds import recovery  # noqa: E402


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class RecoveryExecBase(unittest.TestCase):
    """tmp 布景：双目标 run（t0.bin/t1.bin）+ staged/rollback 副本。"""

    OLD = {0: b"OLD0", 1: b"OLD1"}
    NEW = {0: b"NEW0", 1: b"NEW1"}

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="deterline_rec_exec_"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.game = self.root / "game.ios"
        self.game.write_bytes(b"GAME")

    def _make_targets(self, replaced=()):
        """建 t0/t1 目标文件；replaced 中的目标写 NEW 内容，其余 OLD。"""
        paths = {}
        for i in (0, 1):
            p = self.root / f"t{i}.bin"
            p.write_bytes(self.NEW[i] if i in replaced else self.OLD[i])
            paths[i] = p
        return paths

    def _make_copies(self, with_staged=True, with_rollback=True):
        copies = {}
        for i in (0, 1):
            if with_staged:
                s = self.root / f".t{i}.bin.stage{i}.new"
                s.write_bytes(self.NEW[i])
                copies.setdefault("staged", {})[i] = s
            if with_rollback:
                r = self.root / f".t{i}.bin.back{i}.new"
                r.write_bytes(self.OLD[i])
                copies.setdefault("rollback", {})[i] = r
        return copies

    def _entries(self, copies):
        entries = []
        for i in (0, 1):
            entry = {
                "path": str(self.root / f"t{i}.bin"),
                "before": _sha(self.OLD[i]),
                "after": _sha(self.NEW[i]),
                "staged": str(copies["staged"][i]) if "staged" in copies else None,
                "rollback": str(copies["rollback"][i]) if "rollback" in copies else None,
            }
            entries.append(entry)
        return entries

    def _write_journal(self, jid, state, entries):
        journal_dir = self.root / ".deterline" / "journal"
        journal_dir.mkdir(parents=True, exist_ok=True)
        path = journal_dir / f"{jid}.json"
        path.write_text(json.dumps({
            "schema": deterline.transactions.JOURNAL_SCHEMA,
            "id": jid, "state": state, "targets": entries,
        }), encoding="utf-8")
        return path

    def _apply(self, direction=None, commit=False, json_out=False):
        buf = io.StringIO()
        with mock.patch.object(deterline.paths, "find_game_data_file",
                               return_value=self.game):
            with contextlib.redirect_stdout(buf):
                code = recovery.cmd_recovery_apply(
                    self.root, str(self.root), direction=direction,
                    commit=commit, json_out=json_out)
        return buf.getvalue(), code

    def _clean(self, commit=False, json_out=False):
        buf = io.StringIO()
        with mock.patch.object(deterline.paths, "find_game_data_file",
                               return_value=self.game):
            with contextlib.redirect_stdout(buf):
                code = recovery.cmd_recovery_clean(
                    self.root, str(self.root), commit=commit,
                    json_out=json_out)
        return buf.getvalue(), code

    def _scan_levels(self):
        buf = io.StringIO()
        with mock.patch.object(deterline.paths, "find_game_data_file",
                               return_value=self.game):
            with contextlib.redirect_stdout(buf):
                code = recovery.cmd_recovery_scan(
                    self.root, str(self.root), json_out=True)
        payload = json.loads(buf.getvalue())
        return {f["path"]: f["level"] for f in payload["findings"]
                if f["kind"] == "run-journal"}


class TestRecoveryApply(RecoveryExecBase):
    def test_preview_complete_shows_plan_no_action(self):
        self._make_targets()
        copies = self._make_copies()
        self._write_journal("j", "pending", self._entries(copies))
        out, code = self._apply(direction="complete")
        self.assertEqual(code, 0)
        self.assertIn("预览完成", out)
        self.assertIn("os.replace", out)
        # 零动作：目标仍 OLD、staged 副本仍在
        self.assertEqual((self.root / "t0.bin").read_bytes(), self.OLD[0])
        self.assertTrue(copies["staged"][0].is_file())

    def test_commit_complete_targets_become_after(self):
        self._make_targets()
        copies = self._make_copies()
        journal = self._write_journal("j", "pending", self._entries(copies))
        out, code = self._apply(direction="complete", commit=True)
        self.assertEqual(code, 0, out)
        self.assertEqual((self.root / "t0.bin").read_bytes(), self.NEW[0])
        self.assertEqual((self.root / "t1.bin").read_bytes(), self.NEW[1])
        # 副本即被消费（os.replace 移动）
        self.assertFalse(copies["staged"][0].is_file())
        self.assertFalse(copies["staged"][1].is_file())
        # journal 复用方案 A：记录保留（提交拒绝闸门持续生效）
        self.assertTrue(journal.is_file())
        # scan 现场重分类 → done-confirm（clean 可清）
        levels = self._scan_levels()
        self.assertEqual(list(levels.values()), ["done-confirm"])

    def test_commit_rollback_targets_become_before(self):
        self._make_targets(replaced=(0, 1))
        copies = self._make_copies(with_staged=False)
        self._write_journal("j", "committing", self._entries(copies))
        out, code = self._apply(direction="rollback", commit=True)
        self.assertEqual(code, 0, out)
        self.assertEqual((self.root / "t0.bin").read_bytes(), self.OLD[0])
        self.assertEqual((self.root / "t1.bin").read_bytes(), self.OLD[1])
        self.assertFalse(copies["rollback"][0].is_file())
        levels = self._scan_levels()
        self.assertEqual(list(levels.values()), ["not-started"])

    def test_refuses_mixed_classification(self):
        # interrupted：t0 已替换、t1 未替换 → 两方向都整批拒绝
        self._make_targets(replaced=(0,))
        copies = self._make_copies()
        self._write_journal("j", "committing", self._entries(copies))
        for direction in ("rollback", "complete"):
            out, code = self._apply(direction=direction)
            self.assertEqual(code, 1, direction)
            self.assertIn("整批拒绝", out)
        # 零动作
        self.assertEqual((self.root / "t1.bin").read_bytes(), self.OLD[1])
        self.assertTrue(copies["staged"][1].is_file())

    def test_refuses_external_modification(self):
        self._make_targets()
        (self.root / "t0.bin").write_bytes(b"TAMPERED")
        copies = self._make_copies()
        self._write_journal("j", "pending", self._entries(copies))
        out, code = self._apply(direction="complete")
        self.assertEqual(code, 1)
        self.assertIn("外部修改", out)

    def test_refuses_missing_copy(self):
        self._make_targets()
        copies = self._make_copies(with_rollback=False)
        copies["staged"][1].unlink()          # complete 的副本缺一份
        self._write_journal("j", "pending", self._entries(copies))
        out, code = self._apply(direction="complete")
        self.assertEqual(code, 1)
        self.assertIn("副本校验失败", out)
        # 未被拒绝者也不执行（整批拒绝）
        self.assertEqual((self.root / "t0.bin").read_bytes(), self.OLD[0])

    def test_refuses_multiple_records(self):
        self._make_targets()
        copies = self._make_copies()
        self._write_journal("a", "pending", self._entries(copies))
        self._write_journal("b", "pending", self._entries(copies))
        out, code = self._apply(direction="complete")
        self.assertEqual(code, 1)
        self.assertIn("一次只处理一条", out)

    def test_refuses_complete_on_done_confirm(self):
        # done-confirm（全部 after）+ complete：同质校验拒绝（rollback 才合法）
        self._make_targets(replaced=(0, 1))
        copies = self._make_copies()
        self._write_journal("j", "committing", self._entries(copies))
        out, code = self._apply(direction="complete")
        self.assertEqual(code, 1)
        self.assertIn("整批拒绝", out)

    def test_done_confirm_rollback_abandons_run(self):
        # done-confirm + rollback = 放弃本次（合法出口：目标←回滚副本）
        self._make_targets(replaced=(0, 1))
        copies = self._make_copies(with_staged=False)
        self._write_journal("j", "committing", self._entries(copies))
        out, code = self._apply(direction="rollback", commit=True)
        self.assertEqual(code, 0, out)
        self.assertEqual((self.root / "t0.bin").read_bytes(), self.OLD[0])

    def test_commit_requires_direction(self):
        self._make_targets()
        copies = self._make_copies()
        self._write_journal("j", "pending", self._entries(copies))
        out, code = self._apply(direction=None, commit=True)
        self.assertEqual(code, 1)
        self.assertIn("--direction", out)
        self.assertEqual((self.root / "t0.bin").read_bytes(), self.OLD[0])

    def test_commit_refuses_tampered_copy_zero_action(self):
        # R6 M2b 回归钉：副本"存在但指纹不符"（非缺失）——commit 模式整批
        # 拒绝且零动作（此前只钉缺失分支，指纹比对分支无钉）
        self._make_targets()
        copies = self._make_copies()
        copies["staged"][0].write_bytes(b"TAMPERED-STAGED")  # ≠ NEW0
        self._write_journal("j", "pending", self._entries(copies))
        out, code = self._apply(direction="complete", commit=True)
        self.assertEqual(code, 1)
        self.assertIn("副本校验失败", out)
        self.assertEqual((self.root / "t1.bin").read_bytes(), self.OLD[1],
                         "整批拒绝——未拒绝目标也不得执行")
        self.assertTrue(copies["staged"][1].is_file())

    def test_apply_json_schema(self):
        self._make_targets()
        copies = self._make_copies()
        self._write_journal("j", "pending", self._entries(copies))
        out, code = self._apply(direction="complete", json_out=True)
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["schema"], "deterline.recovery-apply/v1")
        self.assertEqual(payload["direction"], "complete")
        self.assertEqual(len(payload["plan"]), 2)
        self.assertTrue(all(t["copy_sha_ok"] for t in payload["plan"]))


class TestRecoveryClean(RecoveryExecBase):
    def test_commit_cleans_cleanable_and_orphans_keeps_refused(self):
        # 可清记录用独立目标 a0/a1；拒绝记录（interrupted）用 t0/t1
        a0 = self.root / "a0.bin"
        a1 = self.root / "a1.bin"
        a0.write_bytes(self.OLD[0])
        a1.write_bytes(self.OLD[1])
        s = self.root / ".a0.bin.s0.new"
        s.write_bytes(self.NEW[0])
        r = self.root / ".a1.bin.r1.new"
        r.write_bytes(self.OLD[1])
        entries_a = [
            {"path": str(a0), "before": _sha(self.OLD[0]),
             "after": _sha(self.NEW[0]), "staged": str(s), "rollback": None},
            {"path": str(a1), "before": _sha(self.OLD[1]),
             "after": _sha(self.NEW[1]), "staged": None, "rollback": str(r)},
        ]
        cleanable = self._write_journal("clean_me", "pending", entries_a)
        # 拒绝记录：t0 已替换、t1 未改 → interrupted
        self._make_targets(replaced=(0,))
        mixed_copies = self._make_copies()
        refused = self._write_journal("stuck", "committing",
                                      self._entries(mixed_copies))
        orphan = self.root / ".t0.bin.lost.new"
        orphan.write_bytes(b"LOST")
        out, code = self._clean(commit=True)
        self.assertEqual(code, 1, "存在拒绝项 → 1")
        self.assertFalse(cleanable.is_file(), "可清 journal 已删")
        self.assertFalse(s.is_file(), "可清 staged 副本已删")
        self.assertFalse(r.is_file(), "可清 rollback 副本已删")
        self.assertFalse(orphan.is_file(), "孤儿已删")
        self.assertTrue(refused.is_file(), "拒绝项原样保留")
        self.assertTrue(mixed_copies["staged"][0].is_file(), "拒绝项副本保留")
        self.assertIn("拒绝", out)
        self.assertIn("逐条 cp 指引", out, "指引指向 scan 的 cp 出口（apply 恒拒混合）")

    def test_commit_all_cleanable_exit_zero(self):
        self._make_targets()
        copies = self._make_copies()
        journal = self._write_journal("j", "pending", self._entries(copies))
        orphan = self.root / ".t1.bin.x.new"
        orphan.write_bytes(b"X")
        out, code = self._clean(commit=True)
        self.assertEqual(code, 0, out)
        self.assertFalse(journal.is_file())
        self.assertFalse(orphan.is_file())
        self.assertIn("已删除", out)

    def test_never_trusts_stored_state(self):
        # state 声称 done-confirm，现场重分类发现混合（t1 被外部改动）
        self._make_targets(replaced=(0,))
        (self.root / "t1.bin").write_bytes(b"EXTERNAL")
        copies = self._make_copies()
        journal = self._write_journal("j", "committing", self._entries(copies))
        out, code = self._clean(commit=True)
        self.assertEqual(code, 1, "suspicious 重分类 → 拒绝")
        self.assertTrue(journal.is_file(), "存 state 不可信——拒绝清理")

    def test_aborted_clean_reclassified_cleanable(self):
        # aborted-clean + 全 before → 纯重分类 not-started → 可清（06 §4 拒绝
        # 清单不含 aborted-clean）
        self._make_targets()
        copies = self._make_copies(with_staged=False)
        journal = self._write_journal("j", "aborted-clean", self._entries(copies))
        out, code = self._clean(commit=True)
        self.assertEqual(code, 0, out)
        self.assertFalse(journal.is_file())

    def test_clean_json_manifest_stdout_only(self):
        self._make_targets()
        copies = self._make_copies()
        self._write_journal("j", "pending", self._entries(copies))
        out, code = self._clean(commit=True, json_out=True)
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["schema"], "deterline.recovery-clean/v1")
        self.assertEqual(len(payload["deleted"]), 5, "journal+2×(staged+rollback)")
        # manifest 不落盘（journal 目录已空/被摘除）
        journal_dir = self.root / ".deterline" / "journal"
        self.assertFalse(journal_dir.exists() and any(journal_dir.glob("*")))

    def test_corrupt_journal_skips_orphan_sweep(self):
        # R5 P2-2 回归钉：存在 corrupt-journal 时孤儿清扫跳过（corrupt 记录
        # 资产"宁缺毋滥"），处置后二次 clean 才清孤儿
        self._make_targets()
        copies = self._make_copies()
        self._write_journal("j", "pending", self._entries(copies))
        journal_dir = self.root / ".deterline" / "journal"
        (journal_dir / "broken.json").write_text("{broken", encoding="utf-8")
        orphan = self.root / ".t0.bin.ghost.new"
        orphan.write_bytes(b"GHOST")
        buf, err = io.StringIO(), io.StringIO()
        with mock.patch.object(deterline.paths, "find_game_data_file",
                               return_value=self.game):
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
                code = recovery.cmd_recovery_clean(
                    self.root, str(self.root), commit=True, json_out=False)
        out = buf.getvalue()
        self.assertEqual(code, 1)
        self.assertTrue(orphan.is_file(), "corrupt 存在 → 孤儿清扫跳过")
        self.assertIn("孤儿暂存清扫跳过", err.getvalue())
        (journal_dir / "broken.json").unlink()   # 人工处置 corrupt
        out2, code2 = self._clean(commit=True)
        self.assertEqual(code2, 0, out2)
        self.assertFalse(orphan.is_file(), "二次 clean 清孤儿")

    def test_preview_zero_action(self):
        self._make_targets()
        copies = self._make_copies()
        journal = self._write_journal("j", "pending", self._entries(copies))
        out, code = self._clean(commit=False)
        self.assertEqual(code, 0)
        self.assertTrue(journal.is_file())
        self.assertIn("预览完成", out)


class TestBackupPruneCommit(RecoveryExecBase):
    def _prune(self, commit=False, json_out=False):
        buf = io.StringIO()
        with mock.patch.object(deterline.paths, "find_game_data_file",
                               return_value=self.game):
            with contextlib.redirect_stdout(buf):
                code = ms.cmd_backup_prune(self.root, None, keep_archives=3,
                                           json_out=json_out, commit=commit)
        return buf.getvalue(), code

    def _make_archives(self, count):
        import time as _time
        import os as _os
        self.game.write_bytes(b"GAME")
        stamps = []
        for i in range(count):
            archive = self.root / f"game.ios.bak.2026112{i}_000000_{i}"
            archive.write_bytes(f"ARCH-{i}".encode())
            stamp = _time.time() - (count - i) * 100
            _os.utime(archive, (stamp, stamp))
            stamps.append(archive)
        return stamps

    def test_commit_moves_into_pruned_with_manifest(self):
        archives = self._make_archives(5)
        out, code = self._prune(commit=True)
        self.assertEqual(code, 0, out)
        # 2 份超窗（最旧）被移入 pruned/<ts>/
        self.assertFalse(archives[0].is_file())
        self.assertFalse(archives[1].is_file())
        self.assertTrue(archives[2].is_file(), "窗口内保留")
        pruned_root = self.root / ".deterline" / "pruned"
        ts_dirs = [d for d in pruned_root.iterdir() if d.is_dir()]
        self.assertEqual(len(ts_dirs), 1)
        manifest_path = ts_dirs[0] / "manifest.json"
        self.assertTrue(manifest_path.is_file())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema"], "deterline.pruned-manifest/v1")
        self.assertEqual(len(manifest["entries"]), 2)
        self.assertEqual(sorted(e["original_path"] for e in manifest["entries"]),
                         sorted([str(archives[0]), str(archives[1])]))
        # R6 M8 回归钉：可逆移动本体——moved_to 处文件真实存在且指纹一致
        # （move→unlink 变异曾全绿：manifest 断言只查记录不查文件）
        for entry in manifest["entries"]:
            moved = Path(entry["moved_to"])
            self.assertTrue(moved.is_file(), "可逆设计本体：文件必须在 pruned/ 中")
            self.assertEqual(hashlib.sha256(moved.read_bytes()).hexdigest(),
                             entry["sha256"])
        self.assertTrue(manifest["entries"][0]["sha256"])
        self.assertIn("undo --value", out, "undo 失效提示随行打印")

    def test_commit_refuses_corrupt_journal(self):
        archives = self._make_archives(5)
        journal_dir = self.root / ".deterline" / "journal"
        journal_dir.mkdir(parents=True)
        (journal_dir / "broken.json").write_text("{broken", encoding="utf-8")
        out, code = self._prune(commit=True)
        self.assertEqual(code, 1, "硬前置：损坏运行记录 → 拒绝")
        self.assertTrue(archives[0].is_file(), "拒绝时零移动")
        self.assertIn("拒绝", out)

    def test_commit_journal_protected_archive_not_moved(self):
        archives = self._make_archives(5)
        journal_dir = self.root / ".deterline" / "journal"
        journal_dir.mkdir(parents=True)
        (journal_dir / "active.json").write_text(json.dumps({
            "schema": deterline.transactions.JOURNAL_SCHEMA,
            "id": "j", "state": "committing",
            "targets": [{"path": str(archives[0]), "before": None,
                         "after": None, "rollback": None, "staged": None}],
        }), encoding="utf-8")
        out, code = self._prune(commit=True)
        self.assertEqual(code, 0, out)
        self.assertTrue(archives[0].is_file(), "journal 引用文件保护跳过")
        self.assertFalse(archives[1].is_file(), "其余超窗照常移入")

    def test_commit_noop_when_deletion_set_empty(self):
        archives = self._make_archives(2)
        out, code = self._prune(commit=True)
        self.assertEqual(code, 0, out)
        self.assertTrue(all(a.is_file() for a in archives))
        self.assertIn("no-op", out)

    def test_commit_json_schema(self):
        self._make_archives(5)
        out, code = self._prune(commit=True, json_out=True)
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["schema"], "deterline.backup-prune/v1")
        self.assertTrue(payload["commit"]["executed"])
        self.assertEqual(len(payload["commit"]["moved"]), 2)
        self.assertTrue(payload["commit"]["manifest"])


if __name__ == "__main__":
    unittest.main()


class TestPreviewCommitMutex(unittest.TestCase):
    """R5 P2-3 回归钉：--preview × --commit 三 handler 互斥（parser.error）。
    --preview 设 state.PREVIEW——执行动词（--commit）不得与预览门并存。"""

    def _expect_parser_error(self, handler_name, extra):
        import types as _types
        import contextlib as _ctxlib
        import io as _io
        import deterline.command_handlers as _ch
        args = _types.SimpleNamespace(dir=None, json=False, commit=True,
                                      preview=True, keep_archives=3,
                                      direction=None)
        for k, v in extra.items():
            setattr(args, k, v)

        class _Parser:
            def error(self, msg):
                raise SystemExit(2)

        buf = _io.StringIO()
        with mock.patch.object(deterline.paths, "find_save_dir",
                               return_value=None), \
             mock.patch.object(deterline.state, "PREVIEW", True):
            with _ctxlib.redirect_stdout(buf):
                with self.assertRaises(SystemExit) as cm:
                    getattr(_ch, handler_name)(args, _Parser(), None)
        self.assertEqual(cm.exception.code, 2)

    def test_backup_prune_mutex(self):
        self._expect_parser_error("_backup_prune", {})

    def test_recovery_apply_mutex(self):
        self._expect_parser_error("_recovery_apply", {"direction": "complete"})

    def test_recovery_clean_mutex(self):
        self._expect_parser_error("_recovery_clean", {})
