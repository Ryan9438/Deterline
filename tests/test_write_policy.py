"""沙箱路径不变量测试（D0 清偿日 A5，O2 拆包第 3 步前置）。

_modify_save 的 V2 写入策略核心：_resolve_write_target（写操作统一入口）与
_effective_game_file（读写统一重定向）。此前零函数级覆盖（复核R2:172 遗留、
风险审计派 P0 回归事故点）。

本文件**不跑 UTMT 子进程**，纯单测两个路径函数与全局旗标的组合矩阵：

  - 默认（无旗标）→ 写目标 = *.sandbox 副本（且自动激活沙箱）
  - COMMIT_ACTIVE  → 写目标 = 真实路径（不激活沙箱）
  - SANDBOX_ACTIVE → _effective_game_file 对所有命令重定向（含只读）；
                      已存在的 .sandbox 复用不覆盖
  - NO_STEAM_SYNC  → 不影响目标选择，只影响 Steam 同步（同步逻辑在
                      _run_utmt 内，涉及子进程，不在本文件范围）

全局旗标经 mock.patch.object 修改并在退出时自动复原，不污染其他测试。
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import modify_save as ms

# O2 步 1（研讨会2/01 修订 1）：旗标单点迁 deterline/state.py，patch/断言
# 必须指向 canonical 位置——patch ms.* 的快照 re-export 不再影响行为读写。
from deterline import state


class WritePolicyTestBase(unittest.TestCase):
    """公用夹具：真实临时 game.ios（_effective_game_file 会复制它到 .sandbox）。"""

    def setUp(self):
        d = tempfile.mkdtemp(prefix="write_policy_test_")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        self.game_file = Path(d) / "game.ios"
        self.game_file.write_bytes(b"FAKE-GAME-DATA-BASELINE")
        self.sandbox_path = self.game_file.resolve().parent / ".deterline" / "game.ios" / "default" / "game.ios"

    def _patched_flags(self, sandbox=False, commit=False, no_steam_sync=False,
                       sandbox_original=None):
        """同时 patch 四个全局旗标（canonical 位置 deterline.state），
        退出时自动复原（防污染其他测试）。"""
        return [
            mock.patch.object(state, "SANDBOX_ACTIVE", sandbox),
            mock.patch.object(state, "COMMIT_ACTIVE", commit),
            mock.patch.object(state, "NO_STEAM_SYNC", no_steam_sync),
            mock.patch.object(state, "SANDBOX_ORIGINAL", sandbox_original),
        ]


class TestResolveWriteTarget(WritePolicyTestBase):
    """_resolve_write_target：写入策略统一入口的目标选择。"""

    def test_default_goes_to_sandbox_and_activates_it(self):
        """V2 核心不变量：无任何旗标时写目标 = *.sandbox，且自动进入沙箱态。"""
        for p in self._patched_flags(sandbox=False, commit=False):
            p.start()
            self.addCleanup(p.stop)
        target = ms._resolve_write_target(self.game_file)
        self.assertEqual(target, self.sandbox_path,
                         "默认写目标必须是 *.sandbox 副本（v2 写入安全）")
        self.assertTrue(state.SANDBOX_ACTIVE,
                        "首次写操作应自动激活沙箱（默认沙箱策略）")
        self.assertTrue(self.sandbox_path.exists(),
                        "激活沙箱时应创建 *.sandbox 副本")
        self.assertEqual(self.sandbox_path.read_bytes(),
                         self.game_file.read_bytes(),
                         "*.sandbox 应是真实文件的完整副本")

    def test_commit_writes_real_file_without_activating_sandbox(self):
        """--commit：写目标 = 真实路径，且不得暗中激活沙箱。"""
        for p in self._patched_flags(sandbox=False, commit=True):
            p.start()
            self.addCleanup(p.stop)
        target = ms._resolve_write_target(self.game_file)
        self.assertEqual(target, self.game_file,
                         "COMMIT_ACTIVE 时写目标必须是真实文件")
        self.assertFalse(state.SANDBOX_ACTIVE,
                         "--commit 不得激活沙箱（否则会静默改写目标）")
        self.assertFalse(self.sandbox_path.exists(),
                         "--commit 不得创建 *.sandbox 副本")

    def test_no_steam_sync_does_not_change_target_selection(self):
        """--no-steam-sync 只影响同步（_run_utmt 内），不得改变写目标选择。"""
        for p in self._patched_flags(sandbox=False, commit=True,
                                     no_steam_sync=True):
            p.start()
            self.addCleanup(p.stop)
        target = ms._resolve_write_target(self.game_file)
        self.assertEqual(target, self.game_file,
                         "NO_STEAM_SYNC + COMMIT 时写目标仍是真实文件")
        self.assertFalse(state.SANDBOX_ACTIVE)

    def test_sandbox_active_wins_over_commit(self):
        """沙箱已激活时，即使 --commit 在场，写目标仍是沙箱副本（防泄漏）。"""
        for p in self._patched_flags(sandbox=True, commit=True):
            p.start()
            self.addCleanup(p.stop)
        target = ms._resolve_write_target(self.game_file)
        self.assertEqual(target, self.sandbox_path,
                         "SANDBOX_ACTIVE 优先于 COMMIT_ACTIVE（沙箱内容不得泄漏进真实文件）")


class TestEffectiveGameFile(WritePolicyTestBase):
    """_effective_game_file：所有命令（含只读）的重定向。"""

    def test_inactive_returns_original_path(self):
        for p in self._patched_flags(sandbox=False):
            p.start()
            self.addCleanup(p.stop)
        self.assertEqual(ms._effective_game_file(self.game_file), self.game_file)
        self.assertFalse(self.sandbox_path.exists())

    def test_active_redirects_and_copies_once(self):
        """沙箱激活 → 重定向到 *.sandbox；副本懒创建一次。"""
        for p in self._patched_flags(sandbox=True, sandbox_original=None):
            p.start()
            self.addCleanup(p.stop)
        first = ms._effective_game_file(self.game_file)
        self.assertEqual(first, self.sandbox_path,
                         "SANDBOX_ACTIVE 时必须重定向到 *.sandbox（只读命令也要看到沙箱内容）")
        self.assertTrue(self.sandbox_path.exists())
        self.assertEqual(self.sandbox_path.read_bytes(),
                         self.game_file.read_bytes())

        # 第二次调用：复用已存在的副本，不重新复制（已写入的沙箱内容不得被覆盖）
        self.sandbox_path.write_bytes(b"MODIFIED-IN-SANDBOX")
        second = ms._effective_game_file(self.game_file)
        self.assertEqual(second, self.sandbox_path)
        self.assertEqual(self.sandbox_path.read_bytes(), b"MODIFIED-IN-SANDBOX",
                         "已存在的 *.sandbox 必须复用，不得被源文件覆盖")

    def test_active_records_sandbox_original(self):
        """首次重定向时记录 SANDBOX_ORIGINAL（sandbox-restore 的退路依据）。"""
        for p in self._patched_flags(sandbox=True, sandbox_original=None):
            p.start()
            self.addCleanup(p.stop)
        ms._effective_game_file(self.game_file)
        self.assertEqual(state.SANDBOX_ORIGINAL, self.game_file,
                         "SANDBOX_ORIGINAL 应记录沙箱源文件")

    def test_active_redirect_is_independent_of_save_flag(self):
        """重定向只看 SANDBOX_ACTIVE（save/commit 与否均重定向）——
        colorize-sprite --sandbox 曾因只读不重定向而必然失败（P0 回归）。"""
        for p in self._patched_flags(sandbox=True, commit=False):
            p.start()
            self.addCleanup(p.stop)
        self.assertEqual(ms._effective_game_file(self.game_file),
                         self.sandbox_path)


if __name__ == "__main__":
    unittest.main()
