"""拆包后冷路径覆盖棘轮（风险席提案裁决落地，2026-11-11）。

room-list P0 的土壤：接线层 bug 不被 CSX golden 钉住，而冷路径零测试覆盖
让它潜伏到运行时。本文件三层防线：

1. 覆盖地图（动态计算）：commands.json 的每个 action，其 action 名或实现
   cmd_* 函数名必须在 tests/ 出现过——零覆盖集合必须 ⊆ ALLOWLIST（当前
   为空：10 条 save 域命令已全数冒烟，84/84）。新增命令不带测试即爆红。
2. 三方 SSOT 扩展：commands.json actions == cli.ACTION_CHOICES == dispatch
   分支集合（docs lint 已有两腿，此处补齐 dispatch 腿的 In-tuple 形态）。
3. 十条 save 域命令冒烟：全部 tmp 目录（experiment 系经 DETERLINE_GAME_FILE
   env 隔离——cmd_experiment_* 无 dir 参数，find_game_data_file() 直连真实
   Steam 路径，env 不重定向会碰真盘！），零 UTMT 子进程，纯 shutil/json。

ALLOWLIST 语义：带理由的显式豁免清单。条目被覆盖后成为陈余（爆红提示清理）。
"""

import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import modify_save as ms  # noqa: E402
import deterline.paths  # noqa: E402

# 覆盖豁免清单：{action: 理由}。当前为空——84/84 全覆盖。
# 新命令若暂缺测试，须连同理由登记于此（下一 commit 补测试即移除）。
ALLOWLIST: dict[str, str] = {}


def _actions() -> list[str]:
    cj = json.loads((REPO / "scripts" / "commands.json").read_text(encoding="utf-8"))

    def find(obj):
        if isinstance(obj, list) and obj and isinstance(obj[0], dict) and "action" in obj[0]:
            return [c["action"] for c in obj]
        if isinstance(obj, dict):
            for v in obj.values():
                r = find(v)
                if r:
                    return r
        return None
    return find(cj)


def _coverage_map() -> dict[str, list[str]]:
    """action -> [零覆盖判定所需的实现函数名集合]（dispatch 分支体粗扫描）。"""
    cli_src = (REPO / "scripts" / "deterline" / "cli.py").read_text(encoding="utf-8")
    lines = cli_src.split("\n")
    out = {}
    for act in _actions():
        start = None
        for i, l in enumerate(lines):
            if (re.search(rf'==\s*"{re.escape(act)}"', l)
                    or re.search(rf'in \([^)]*"{re.escape(act)}"', l)):
                start = i
                break
        if start is None:
            continue
        body = "\n".join(lines[start:min(start + 80, len(lines))])
        out[act] = sorted(set(re.findall(r"\b(cmd_[a-z_]+)\b", body)))
    return out


class TestDispatchCoverageRatchet(unittest.TestCase):
    """棘轮：只许收紧，不许松开。"""

    def test_actions_match_action_choices(self):
        sys.path.insert(0, str(REPO / "tests"))
        from deterline.cli import ACTION_CHOICES  # noqa: E402
        self.assertEqual(sorted(_actions()), sorted(ACTION_CHOICES),
                         "commands.json 与 cli.ACTION_CHOICES 集合漂移")

    def test_every_action_has_dispatch_branch(self):
        covered_by_branch = set(_coverage_map())
        missing = [a for a in _actions() if a not in covered_by_branch]
        self.assertEqual(missing, [],
                         f"commands.json 有 action 无 dispatch 分支（冷路径）: {missing}")

    def test_zero_coverage_within_allowlist(self):
        test_src = "\n".join(
            f.read_text(encoding="utf-8") for f in (REPO / "tests").glob("test_*.py"))
        zero = []
        for act, fns in _coverage_map().items():
            mentioned = act in test_src or any(f in test_src for f in fns)
            if not mentioned:
                zero.append(act)
        stale = [a for a in ALLOWLIST if a not in zero]
        self.assertEqual(stale, [],
                         f"ALLOWLIST 陈余（已覆盖，请移除条目）: {stale}")
        unlisted = [a for a in zero if a not in ALLOWLIST]
        self.assertEqual(unlisted, [],
                         f"零覆盖且未豁免的 action（补测试或带理由登记 ALLOWLIST）: {unlisted}")


class _SaveDirBase(unittest.TestCase):
    """tmp 存档目录夹具：全冒烟零真实路径接触。"""

    def setUp(self):
        d = tempfile.mkdtemp(prefix="dispatch_cov_test_")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        self.save_dir = Path(d)
        self._write_file0([0] * 80 + [1] * 10)  # name=Freddy; flag 域占位

    def _write_file0(self, numbers: list[int], name: str = "Freddy"):
        with open(self.save_dir / "file0", "w", encoding="utf-8", newline="\r\n") as f:
            f.write(name + "\r\n")
            for n in numbers:
                f.write(f"{n} \r\n")

    def _read_file0(self) -> list[int]:
        _, nums = ms._parse_file0(self.save_dir / "file0")
        return nums


class TestSaveDomainSmokes(_SaveDirBase):
    """十条零覆盖 save 域命令冒烟（纯 Python、tmp 目录、零 UTMT）。"""

    def test_undo_restores_from_bak(self):
        (self.save_dir / "file0.bak").write_text("OldName\r\n7 \r\n", encoding="utf-8")
        ms.cmd_undo(self.save_dir, "file0")
        self.assertEqual(self._read_file0(), [7], "undo 应把 file0 恢复为 .bak 内容")

    def test_undo_missing_bak_lists_available(self):
        import io as _io
        import contextlib as _ctxlib
        buf = _io.StringIO()
        with _ctxlib.redirect_stderr(buf):
            ms.cmd_undo(self.save_dir, "file0")  # 无 .bak → 打印可用备份并 return
        self.assertIn("没有找到备份文件", buf.getvalue())

    def test_list_backups_lists_and_sorts(self):
        (self.save_dir / "file0.bak.20260101_000000").write_bytes(b"a")
        (self.save_dir / "file0.bak").write_bytes(b"b")
        import io as _io
        import contextlib as _ctxlib
        buf = _io.StringIO()
        with _ctxlib.redirect_stdout(buf):
            ms.cmd_list_backups(self.save_dir, "file0")
        self.assertIn("bak.20260101_000000", buf.getvalue())

    def test_reset_flags_zeros_flowey_and_kills(self):
        (self.save_dir / "undertale.ini").write_text(
            "[Flowey]\nTalking=false\n[General]\nKills=5\nfun=42\n", encoding="utf-8")
        nums = self._read_file0()
        nums[10] = 6
        self._write_file0(nums)
        ms.cmd_reset_flags(self.save_dir)
        cp = ms._read_ini(self.save_dir / "undertale.ini")
        self.assertEqual(ms.parse_ini_value(cp.get("General", "Kills")), "0")
        self.assertEqual(self._read_file0()[10], 0, "file0 Kills 应同步清零")

    def test_reset_all_preserves_pacifist_memory(self):
        nums = self._read_file0()
        nums[0] = 9            # LOVE
        nums[10] = 100         # KILLS
        while len(nums) <= 65:
            nums.append(0)
        nums[29 + 36] = 1      # flag[36] 和平记忆
        self._write_file0(nums)
        ms.cmd_reset_all(self.save_dir)
        out = self._read_file0()
        self.assertEqual(out[0], 1, "LOVE 重置为 1")
        self.assertEqual(out[10], 0, "KILLS 清零")
        self.assertEqual(out[65], 1, "flag[36] 必须保留（和平记忆）")

    def test_create_system_info_and_validation(self):
        ms.cmd_create_system_info(self.save_dir, "962")
        self.assertTrue((self.save_dir / "system_information_962").exists())
        with self.assertRaises(ms.ValidationError):
            ms.cmd_create_system_info(self.save_dir, "964")

    def test_quest_init_resets_custom_flag(self):
        nums = self._read_file0()
        while len(nums) <= 29 + ms.FLAG_CUSTOM_START:
            nums.append(0)
        nums[29 + ms.FLAG_CUSTOM_START] = 3
        self._write_file0(nums)
        ms.cmd_quest_init(self.save_dir, ms.FLAG_CUSTOM_START)
        self.assertEqual(self._read_file0()[29 + ms.FLAG_CUSTOM_START], 0)

    def test_quest_status_prints_flags(self):
        import io as _io
        import contextlib as _ctxlib
        buf = _io.StringIO()
        with _ctxlib.redirect_stdout(buf):
            ms.cmd_quest_status(self.save_dir)
        self.assertIn("flag[", buf.getvalue())

    def _fake_game_env(self, d: Path):
        """隔离 experiment 系的真实路径触达。

        ⚠️ 教训（本测试初版）：DETERLINE_GAME_FILE 是 find_game_data_file 的
        优先级 3 兜底——优先级 1 的 Steam 路径在本机存在时会**赢过 env**，
        初版冒烟实际打到真实 Steam 目录（快照覆盖了两枚同名旧档）。正解 =
        patch paths.find_game_data_file（模块属性纪律保证可拦截）。
        """
        game = d / "game.ios"
        game.write_bytes(b"FAKE-GAME")
        return mock.patch.object(deterline.paths, "find_game_data_file",
                                 return_value=game)

    def test_experiment_snapshot_list_restore_roundtrip(self):
        with self._fake_game_env(self.save_dir):
            ms.cmd_experiment_snapshot(self.save_dir, "a3smoke")
            self.assertTrue((self.save_dir / "file0.snap.a3smoke").exists())
            # 篡改 file0 后恢复
            self._write_file0([7] * 90, name="Changed")
            import io as _io
            import contextlib as _ctxlib
            buf = _io.StringIO()
            with _ctxlib.redirect_stdout(buf):
                ms.cmd_experiment_list(self.save_dir)
            self.assertIn("a3smoke", buf.getvalue())
            ms.cmd_experiment_restore(self.save_dir, "a3smoke")
            self.assertEqual(self._read_file0()[0], 0, "experiment-restore 应还原 file0")


if __name__ == "__main__":
    unittest.main()
