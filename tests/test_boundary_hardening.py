"""A3 写入边界收紧（12 计划）：符号链接拒绝、journal 原子写残留单列、
kept_counts bak-archive 语义、跨目录 journal 可见性钉、相对路径解析钉。

全部 tmp 隔离零 UTMT；合成 journal 夹具（test_recovery_exec 风格）。
"""

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "tests"))

import deterline.transactions as transactions  # noqa: E402
from deterline.cmds import recovery  # noqa: E402
from deterline.cmds import save_cmds  # noqa: E402


def _sha(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()


class BoundaryBase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="deterline_a3_"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        (self.root / "game.ios").write_bytes(b"GAME")  # resolve 定位锚

    def _capture(self, fn, *a, **k):
        """静默执行（命令函数直接 print；测试只取返回码）。"""
        buf_out, buf_err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            rc = fn(*a, **k)
        return rc, buf_out.getvalue(), buf_err.getvalue()

    def _capture_raise(self, fn, exc=RuntimeError) -> str:
        """静默执行并捕获预期异常，返回异常文本。"""
        buf_out, buf_err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            with self.assertRaises(exc) as ctx:
                fn()
        return str(ctx.exception)


class TestSymlinkRefusal(BoundaryBase):
    """A3：符号链接目标拒绝——os.replace 会替换链接本身而非写穿。

    G6（07 §3 条1 Windows symlink 回归）：skip 判定从平台静态改为
    **尝试建链**——有特权/开发者模式的 Windows CI 实跑，无权限环境
    skipTest 留痕（诚实口径：能跑才跑，跑不了如实记 skip）。
    """

    def _make_symlink(self, link: Path, real: Path) -> None:
        real.write_bytes(b"REAL")
        try:
            link.symlink_to(real)
        except (OSError, NotImplementedError):
            self.skipTest("当前环境建符号链接需特权/开发者模式")

    def test_prepare_refuses_symlink(self):
        real = self.root / "real.bin"
        link = self.root / "link.bin"
        self._make_symlink(link, real)
        with self.assertRaises(RuntimeError) as ctx:
            transactions.FileEdit.prepare(link, b"NEW", backup=True)
        self.assertIn("符号链接", str(ctx.exception))
        # 零副作用：链接仍在、指向不变、真实文件未被改
        self.assertTrue(link.is_symlink())
        self.assertEqual(real.read_bytes(), b"REAL")

    def test_commit_refuses_symlink_target(self):
        """防线 2：绕过 prepare 直接构造的方案（数据类不解析路径）在
        commit 期仍拦截——staging 失败路径，零替换、链接保持。"""
        real = self.root / "real.bin"
        link = self.root / "link.bin"
        self._make_symlink(link, real)
        edit = transactions.FileEdit(link, b"NEW",
                                     transactions.fingerprint(link),
                                     backup=True)  # 基线=链接当前指向的内容
        plan = transactions.EditPlan((edit,))
        message = self._capture_raise(plan.commit)
        self.assertIn("符号链接", message)
        self.assertTrue(link.is_symlink())
        self.assertEqual(real.read_bytes(), b"REAL")


class TestHardlinkWarning(BoundaryBase):
    """G4（v2.5.11 前瞻）：硬链接目标提交 → 警告而非拒绝——os.replace
    断链语义（其他链接名保留旧内容）如实告知；备份为独立副本不受影响。"""

    def test_commit_warns_on_hardlink_and_breaks_link(self):
        target = self.root / "game.ios"   # BoundaryBase 锚文件（b"GAME"）
        alias = self.root / "alias.bin"
        try:
            os.link(target, alias)
        except (OSError, NotImplementedError):
            self.skipTest("当前环境不支持 os.link")
        self.assertEqual(alias.read_bytes(), b"GAME")
        edit = transactions.FileEdit(target, b"NEW!",
                                     transactions.fingerprint(target),
                                     backup=True)
        plan = transactions.EditPlan((edit,))
        buf_out, buf_err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            plan.commit()
        self.assertIn("硬链接", buf_err.getvalue())
        self.assertIn("st_nlink=2", buf_err.getvalue())
        self.assertEqual(target.read_bytes(), b"NEW!")
        # 断链语义实证：别名（旧 inode）保留旧内容——警告所述行为
        self.assertEqual(alias.read_bytes(), b"GAME")
        # 正常路径回归：无硬链接时零警告
        plain = self.root / "plain.bin"
        plain.write_bytes(b"PLAIN")
        edit2 = transactions.FileEdit(plain, b"NEW2",
                                      transactions.fingerprint(plain),
                                      backup=True)
        plan2 = transactions.EditPlan((edit2,))
        buf_out2, buf_err2 = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(buf_out2), contextlib.redirect_stderr(buf_err2):
            plan2.commit()
        self.assertNotIn("硬链接", buf_err2.getvalue())


class TestJournalTmpListing(BoundaryBase):
    """A3：`.journal.*.new` 原子写残留单列——只列出，不自动清理。"""

    def test_scan_lists_journal_tmp_and_clean_preserves(self):
        target = self.root / "t0.bin"
        target.write_bytes(b"OLD")
        journal_dir = self.root / ".deterline" / "journal"
        journal_dir.mkdir(parents=True)
        tmp = journal_dir / ".journal.abc.new"
        tmp.write_text('{"schema": "deterline.run-journal/v1", "half": ',)
        rc, out, _ = self._capture(
            recovery.cmd_recovery_scan, None, str(self.root), json_out=True)
        self.assertEqual(rc, 1)
        findings = json.loads(out)["findings"]
        kinds = {f["kind"] for f in findings}
        self.assertIn("journal-tmp", kinds)
        # journal-tmp 的路径指向残留文件本体
        jt = [f for f in findings if f["kind"] == "journal-tmp"][0]
        self.assertEqual(Path(jt["path"]).name, ".journal.abc.new")
        # clean --commit 不触碰 journal-tmp（宁缺毋滥——内容可能是未落盘快照）
        rc_c, _o, _e = self._capture(
            recovery.cmd_recovery_clean, None, str(self.root), commit=True)
        self.assertTrue(tmp.exists(), "journal-tmp 不得被 clean 自动删除")
        # 人工删除后复查干净
        tmp.unlink()
        rc2, out2, _ = self._capture(
            recovery.cmd_recovery_scan, None, str(self.root), json_out=True)
        self.assertEqual(rc2, 0)

    def test_scan_clean_without_journal_tmp(self):
        target = self.root / "t0.bin"
        target.write_bytes(b"OLD")
        rc, out, _ = self._capture(
            recovery.cmd_recovery_scan, None, str(self.root), json_out=True)
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out)["findings"], [])


class TestKeptCountsBakArchive(BoundaryBase):
    """B P3-4/A3：kept_counts 必须含 bak-archive（kept = 未进删除集）。"""

    def test_kept_counts_includes_bak_archive(self):
        game = self.root / "game.ios"
        game.write_bytes(b"GAME")
        for k in range(4):
            (self.root / f"game.ios.bak.2026110{k}_000000_{k}").write_bytes(
                f"arch{k}".encode() * 10)
        rc, out, _ = self._capture(
            save_cmds.cmd_backup_prune, None, str(self.root),
            keep_archives=2, json_out=True)
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        # 4 份归档、窗口 2 → 删除 2、保留 2
        self.assertEqual(len(payload["deletions"]), 2)
        self.assertEqual(payload["kept_counts"].get("bak-archive"), 2)


class TestCrossDirJournalPins(BoundaryBase):
    """跨目录 journal 语义钉（已知局限 = CHANGELOG v2.5.7 A P2-3 + SKILL
    "写入安全与恢复链"节；登记锚点以 CHANGELOG 为准）。"""

    def setUp(self):
        super().setUp()
        self.dir1 = self.root / "game_side"
        self.dir2 = self.root / "save_side"
        self.dir1.mkdir()
        self.dir2.mkdir()
        # 两侧各放 resolve 定位锚（scan --dir 单侧传入时须能定位）
        (self.dir1 / "game.ios").write_bytes(b"GAME1")
        (self.dir2 / "game.ios").write_bytes(b"GAME2")

    def _make_record(self, dir1_target: Path, dir2_target: Path) -> Path:
        """合成跨目录 journal（落在首目标旁 = dir1）+ 副本。"""
        journal_dir = self.dir1 / ".deterline" / "journal"
        journal_dir.mkdir(parents=True)
        staged1 = self.dir1 / ".t1.bin.s1.new"
        staged1.write_bytes(b"NEW1")
        rollback1 = self.dir1 / ".t1.bin.r1.new"
        rollback1.write_bytes(b"OLD1")
        record = {
            "schema": "deterline.run-journal/v1", "id": "xd_probe",
            "state": "committing", "pid": 0,
            "created": "2026-01-01T00:00:00", "updated": "2026-01-01T00:00:00",
            "targets": [
                {"path": str(dir1_target), "before": _sha(b"OLD1"),
                 "after": _sha(b"NEW1"), "staged": str(staged1),
                 "rollback": str(rollback1), "backup": True},
                {"path": str(dir2_target), "before": _sha(b"OLD2"),
                 "after": _sha(b"NEW2"), "staged": None,
                 "rollback": None, "backup": True},
            ],
        }
        path = journal_dir / "xd_probe.json"
        path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        return path

    def test_scan_with_first_dir_finds_cross_dir_record(self):
        t1 = self.dir1 / "t1.bin"
        t1.write_bytes(b"OLD1")
        t2 = self.dir2 / "t2.bin"
        t2.write_bytes(b"OLD2")
        self._make_record(t1, t2)
        # --dir dir1（游戏侧）：journal 在 dir1 → 可见
        rc, out, _ = self._capture(
            recovery.cmd_recovery_scan, None, str(self.dir1), json_out=True)
        self.assertEqual(rc, 1)
        findings = json.loads(out)["findings"]
        run_journals = [f for f in findings if f["kind"] == "run-journal"]
        self.assertEqual(len(run_journals), 1)
        # classes: t1=before, t2 在 dir2（存在且 == before）→ not-started
        self.assertEqual(run_journals[0]["level"], "not-started")

    def test_scan_other_dir_alone_is_documented_gap(self):
        """已知局限钉面（CHANGELOG v2.5.7 A P2-3）：scan 只给 dir2 看不到
        dir1 的记录——这是**有意登记的局限**，此测试让行为变化显式化。"""
        t1 = self.dir1 / "t1.bin"
        t1.write_bytes(b"OLD1")
        t2 = self.dir2 / "t2.bin"
        t2.write_bytes(b"OLD2")
        self._make_record(t1, t2)
        rc, out, _ = self._capture(
            recovery.cmd_recovery_scan, None, str(self.dir2), json_out=True)
        self.assertEqual(rc, 0)  # 局限：另一侧单独扫 → 干净
        self.assertEqual(json.loads(out)["findings"], [])

    def test_new_commit_touching_other_side_not_refused(self):
        """局限推论钉面（CHANGELOG v2.5.7 A P2-3）：仅动 dir2 的新提交不被
        dir1 记录拒绝——SKILL 补偿控制（recovery-scan 双 roots 兜底）的
        边界证据。"""
        t1 = self.dir1 / "t1.bin"
        t1.write_bytes(b"OLD1")
        t2 = self.dir2 / "t2.bin"
        t2.write_bytes(b"OLD2")
        self._make_record(t1, t2)
        edit = transactions.FileEdit.prepare(t2, b"NEW2B", backup=True)
        plan = transactions.EditPlan((edit,))
        self._capture(plan.commit)  # 成功（不被拒）——局限如文档所述
        self.assertEqual(t2.read_bytes(), b"NEW2B")
        # dir1 记录不受影响
        rc, out, _ = self._capture(
            recovery.cmd_recovery_scan, None, str(self.dir1), json_out=True)
        self.assertEqual(rc, 1)

    def test_overlapping_target_still_refused(self):
        """闸门工作面：同侧（dir1 内）目标的未完结记录照常拒绝再提交。"""
        t1 = self.dir1 / "t1.bin"
        t1.write_bytes(b"OLD1")
        t2 = self.dir2 / "t2.bin"
        t2.write_bytes(b"OLD2")
        self._make_record(t1, t2)
        edit = transactions.FileEdit.prepare(t1, b"NEW1B", backup=True)
        plan = transactions.EditPlan((edit,))
        message = self._capture_raise(plan.commit)
        self.assertIn("未完结的运行记录", message)


class TestRelativePathResolution(BoundaryBase):
    """A3：相对路径目标 resolve 到绝对路径；journal 落在解析后目标旁。"""

    def test_relative_target_resolves_and_journal_beside(self):
        cwd = os.getcwd()
        try:
            os.chdir(self.root)
            target = Path("rel_t.bin")
            target.write_bytes(b"OLD")
            edit = transactions.FileEdit.prepare(target, b"NEW", backup=True)
            self.assertTrue(edit.target.is_absolute())
            # macOS /tmp → /private/tmp 拼写差：以 resolve 归一比较
            self.assertEqual(edit.target,
                             (self.root / "rel_t.bin").resolve())
            plan = transactions.EditPlan((edit,))
            self._capture(plan.commit)
            self.assertEqual((self.root / "rel_t.bin").read_bytes(), b"NEW")
            # journal 成功摘除（落在解析后目标旁，非 cwd 残留）
            journal_dir = self.root / ".deterline" / "journal"
            self.assertFalse(journal_dir.exists())
        finally:
            os.chdir(cwd)


    @unittest.skipIf(sys.platform == "win32",
                     "Windows 建符号链接需特权/开发者模式")
    def test_write_many_baselines_refuses_symlink(self):
        """R11 P1-2 回归钉：write_many 的 baseline 直传分支同样拒绝
        符号链接（此前 resolve 在前、防线被绕过，alias 写入静默放行）。"""
        real = self.root / "real.ini"
        real.write_bytes(b"[General]\nLove=1\n")
        link = self.root / "alias.ini"
        link.symlink_to(real)
        baseline = transactions.fingerprint(link)   # 跟链接读内容
        with self.assertRaises(RuntimeError) as ctx:
            transactions.write_many({link: b"[General]\nLove=2\n"},
                                    baselines={link: baseline})
        self.assertIn("符号链接", str(ctx.exception))
        # 零副作用：链接仍在、真实文件未被写穿
        self.assertTrue(link.is_symlink())
        self.assertIn(b"Love=1", real.read_bytes())


class TestRelativeEscapePins(BoundaryBase):
    """R12 P3-6：`..` 逃逸负形钉——事务层语义 = 相对路径按 cwd 解析，
    journal 落在**解析后**目标旁；允许根约束在 CLI 层（--dir 定位锚，
    无回退）。此钉让分层契约显式化，防两层职责漂移。"""

    def test_dotdot_escape_resolves_outside_and_journal_follows(self):
        outside = self.root.parent
        cwd = os.getcwd()
        try:
            os.chdir(self.root)
            target = Path("../escape_t.bin")
            resolved_target = (self.root.parent / "escape_t.bin").resolve()
            edit = transactions.FileEdit.prepare(target, b"ESC", backup=True)
            self.assertEqual(edit.target, resolved_target,
                             "事务层按 cwd 解析 .. —— 逃逸目标落在 root 外")
            plan = transactions.EditPlan((edit,))
            self._capture(plan.commit)
            self.assertEqual(resolved_target.read_bytes(), b"ESC")
            journal_dir = (self.root.parent / ".deterline" / "journal")
            self.assertFalse(journal_dir.exists(),
                             "journal 落在解析后目标旁（root 外）并成功摘除")
        finally:
            os.chdir(cwd)
            (self.root.parent / "escape_t.bin").unlink(missing_ok=True)
            shutil.rmtree(self.root.parent / ".deterline", ignore_errors=True)

    def test_cli_override_no_fallback_to_steam(self):
        """CLI 层允许根锚：--dir 无效必须报错，不得回退默认定位（否则
        会把真实 Steam 安装当成操作对象）。"""
        from deterline import paths
        with self.assertRaises(FileNotFoundError):
            paths.resolve_game_data_file("/tmp/dl_no_such_dir_a3x/game.ios")


class TestSymlinkJournalSideEffects(BoundaryBase):
    """A3 伴随钉：journal 目录路径不受符号链接歧义影响（resolve 归一）。"""

    def test_journal_dir_for_resolved_target(self):
        real_dir = self.root / "actual"
        real_dir.mkdir()
        target = real_dir / "t.bin"
        target.write_bytes(b"OLD")
        edit = transactions.FileEdit.prepare(target, b"NEW", backup=True)
        # macOS /tmp → /private/tmp 拼写差：resolve 归一比较
        self.assertEqual(transactions.journal_dir_for(edit.target),
                         (real_dir / ".deterline" / "journal").resolve())


if __name__ == "__main__":
    unittest.main()
