"""recovery_stress 工具的 CI 级验证（12 计划 A2）。

确定性窗口子集进 CI（s1+s2+s5a+p1_prune；Windows 仅 s1+p1_prune——
多窗口 TerminateProcess 语义按 07 §3 条3 保守逐级验证）。测试进程内
直接调用工具（rs.main），子进程强杀在工具内部独立进程完成——测试文件
本身零 subprocess。全量场景与随机批次 = 本地 opt-in（--confirm-synthetic）。
全部 tmp 隔离、零 UTMT、零真实数据。
"""

import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import recovery_stress as rs  # noqa: E402


def _invoke(argv, expect_rc=None):
    """进程内调用工具 main（捕获打印；返回 (rc, out_dir, jsonl, stdout, stderr)）。
    expect_rc 不符时抛 AssertionError（信息带 stdout/stderr 便于诊断）。"""
    out = Path(tempfile.mkdtemp(prefix="deterline_stress_test_"))
    buf_out, buf_err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
        rc = rs.main(argv + ["--out", str(out)])
    jsonl = sorted(out.glob("stress_*.jsonl"))
    if expect_rc is not None and rc != expect_rc:
        raise AssertionError(
            f"rc={rc} != {expect_rc}\nstdout={buf_out.getvalue()}\nstderr={buf_err.getvalue()}")
    return rc, out, jsonl, buf_out.getvalue(), buf_err.getvalue()


def _load_records(jsonl_paths):
    records = []
    for path in jsonl_paths:
        records.extend(
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines())
    return records


class TestOracleTables(unittest.TestCase):
    """oracle 表静态完整性：任何场景缺迁移定义 = 工具自身缺陷。"""

    def test_every_scenario_has_full_oracle(self):
        for sid in rs.ALL_SCENARIOS:
            self.assertIn(sid, rs.KILL_PHASES, sid)
            self.assertIn(sid, rs.CLOSURE, sid)
            self.assertIn(sid, rs.EXPECT_LEVELS, sid)
            self.assertTrue(rs.KILL_PHASES[sid], sid)
            self.assertGreaterEqual(rs.TARGET_COUNTS[sid], 1, sid)

    def test_not_created_indexes_valid(self):
        for sid, indexes in rs.NOT_CREATED.items():
            self.assertIn(sid, rs.ALL_SCENARIOS, sid)
            for i in indexes:
                self.assertLess(i, rs.TARGET_COUNTS[sid], sid)

    def test_p1_not_in_kill_matrix(self):
        self.assertNotIn("p1_prune", rs.KILL_PHASES)


class TestGate(unittest.TestCase):
    def test_gate_refuses_without_confirm(self):
        rc, out, _j, _o, stderr = _invoke(["--scenarios", "s1"], expect_rc=2)
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)  # R12 P3-4
        self.assertIn("--confirm-synthetic", stderr)

    def test_unknown_scenario_refused(self):
        rc, out, _j, _o, stderr = _invoke(["--confirm-synthetic",
                                           "--scenarios", "sX"], expect_rc=2)
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        self.assertIn("未知场景", stderr)


class TestDeterministicWindows(unittest.TestCase):
    """CI 子集：pending / committing 副本入记录 / 中断双拒 / prune manifest。"""

    def _run_subset(self, scenarios: str) -> list:
        rc, out, jsonl, stdout, stderr = _invoke(
            ["--confirm-synthetic", "--scenarios", scenarios])
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)  # 断言前注册
        records = _load_records(jsonl)
        self.assertEqual(records[0]["kind"], "run-header")
        self.assertTrue(records[0]["transactions_sha"])
        self.assertEqual(records[0]["scenarios"], scenarios.split(","))
        verdicts = {r["scenario"]: r["verdict"] for r in records[1:]}
        self.assertEqual(set(verdicts), set(scenarios.split(",")))
        for sid, verdict in verdicts.items():
            detail = [r for r in records if r.get("scenario") == sid]
            self.assertEqual(verdict, "pass", msg=sid + ": " + repr(detail))
        return records[1:]

    def _assert_copy_evidence_complete(self, records: list) -> None:
        """G5（v2.5.11 前瞻）：journal 引用的每个副本要么有哈希、要么显式
        标记 <consumed-before-recording>——证据链无静默空洞；且子集至少
        一条记录携带副本证据（kill 窗口命中 journal 的场景）。"""
        with_evidence = 0
        for rec in records:
            refs = rec.get("journal_referenced_copies")
            if not refs:
                continue
            with_evidence += 1
            hashes = rec.get("copy_hashes", {})
            for path in refs:
                self.assertIn(path, hashes,
                              msg=f"{rec.get('scenario')}: 静默空洞 {path}")
        self.assertGreaterEqual(with_evidence, 1,
                                "子集无任何副本证据记录——kill 窗口表漂移？")

    @unittest.skipIf(sys.platform == "win32",
                     "多窗口 TerminateProcess 语义保守逐级验证（07 §3 条3）"
                     "——Windows 仅跑 s1+p1_prune")
    def test_posix_subset(self):
        records = self._run_subset("s1,s2,s5a,p1_prune")
        self._assert_copy_evidence_complete(records)

    @unittest.skipIf(sys.platform != "win32", "Windows CI 子集")
    def test_windows_subset(self):
        # R18 P1：Windows 子集补 s2——s1（pending 杀，journal 无 staged/
        # rollback 记录）与 p1_prune（走 prune 分支）都不产副本证据记录，
        # 证据下限断言会确定性红灯；s2（committing 杀）与 s1 同型且稳定
        # 携带 staged+rollback 证据
        records = self._run_subset("s1,s2,p1_prune")
        self._assert_copy_evidence_complete(records)


if __name__ == "__main__":
    unittest.main()
