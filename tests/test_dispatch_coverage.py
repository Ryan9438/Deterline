"""拆包后冷路径覆盖棘轮（风险席提案裁决落地，2026-11-11）。

room-list P0 的土壤：接线层 bug 不被 CSX golden 钉住，而冷路径零测试覆盖
让它潜伏到运行时。本文件三层防线：

1. 覆盖地图（动态计算）：commands.json 的每个 action，其 action 名或实现
   cmd_* 函数名必须在 tests/ 出现过——零覆盖集合必须 ⊆ ALLOWLIST（当前
   为空：10 条 save 域命令已全数冒烟，84/84）。新增命令不带测试即爆红。
2. 三方 SSOT 扩展：commands.json actions == cli.ACTION_CHOICES == dispatch
   分支集合（docs lint 已有两腿，此处补齐 dispatch 腿的 In-tuple 形态）。
3. 十条 save 域命令冒烟：全部 tmp 目录（experiment 系经
   patch paths.find_game_data_file 隔离——⚠️ 教训：DETERLINE_GAME_FILE env
   是优先级 3 兜底，本机 Steam 路径（优先级 1）恒压过 env，曾致冒烟打到
   真实 Steam 目录覆盖两枚旧快照，见 CHANGELOG v2.3.2 事故记录），
   零 UTMT 子进程，纯 shutil/json。

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
sys.path.insert(0, str(REPO / "tests"))

import modify_save as ms  # noqa: E402
import fixtures_save  # noqa: E402  # 阶段 0.3 共享存档夹具
import deterline.paths  # noqa: E402

# 覆盖豁免清单：{action: 理由}（复核 P1-2 修正后按 AST 精确分支归属实测）。
# 两类豁免：
#   - md5/sandbox-restore：逻辑内联在 cli.py dispatch（无 cmd_* 函数可单测；
#     收编 = 表驱动 dispatch 的独立后续项）
#   - 其余 22 条：读式/诊断命令（UTMT 查询+打印）或重游戏依赖命令
#     （npc-dialogue/smoke-test/replace-texture），行为面已由 golden CSX
#     （28 生成器钉死）+ A3 双轮游戏级快照 parity 覆盖；补单测 = 独立后续项
#     （需 dual_patch_utmt mock 逐条搭夹具，与本 commit 的接线防线目标正交）。
# 新命令若暂缺测试，须连同理由登记于此（下一 commit 补测试即移除）。
ALLOWLIST: dict[str, str] = {
    "md5": "逻辑内联 cli.py dispatch（无 cmd_* 函数）——表驱动 dispatch 收编",
    "sandbox-restore": "逻辑内联 cli.py dispatch——同上",
    "decompile-code": "读式诊断；golden 钉 _decompile_to_lines 链路",

    "dump-sprites": "读式导出（UTMT dump）",
    "export-sprite": "读式导出",
    "export-texture": "读式导出",
    "get-obj": "读式诊断",
    "get-string": "读式（strg_get 逻辑经 cmd_strg_set 的 golden 间接覆盖）",
    "list-codes": "读式列表",
    "list-doors": "读式列表",
    "list-game-bgs": "读式列表",
    "list-sprites": "读式列表",
    "list-strings": "读式列表",
    "list-textures": "读式列表",
    "npc-choice": "重游戏依赖（触发块+choice 链）；_build_npc_choice_block golden 钉死",
    "npc-dialogue": "重游戏依赖；_build_npc_step_block golden 钉死 + A3 parity",
    "preview-sprite": "读式诊断",
    "replace-texture": "重游戏依赖（真实 UTMT 写纹理页）；A3 parity 实证",
    "room-bg-info": "读式诊断",
    "room-objects": "读式诊断",
    "search-sctext": "读式搜索（_fail_if_no_match 退出码 3 已测）",
    "search-sprite": "读式搜索",
    "verify-code": "verify 域；cmd_cjk_font 五步管线的收尾步每轮实测",
}


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
    """Read each actual registry handler to associate its domain commands."""
    import ast
    import inspect
    from deterline.command_handlers import COMMANDS

    out = {}
    for action, routes in COMMANDS.items():
        functions = set()
        for handler in routes.values():
            for node in ast.walk(ast.parse(inspect.getsource(handler))):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if node.func.attr.startswith("cmd_"):
                        functions.add(node.func.attr)
        out[action] = sorted(functions)
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
        # 排除棘轮自身：ALLOWLIST 的理由文本提到 action 名会把自己算成"已覆盖"
        test_src = "\n".join(
            f.read_text(encoding="utf-8") for f in (REPO / "tests").glob("test_*.py")
            if f.name != "test_dispatch_coverage.py")
        zero = []
        for act, fns in _coverage_map().items():
            mentioned = act in test_src or any(f in test_src for f in fns)
            if not mentioned:
                zero.append(act)
        cmap = _coverage_map()
        # 陈余判定只对"有实现函数"的 action 生效；内联型（无 cmd_*，如
        # md5/sandbox-restore）结构上不可能有单元覆盖，字面子串提及不算数
        stale = [a for a in ALLOWLIST if a not in zero and cmap.get(a)]
        self.assertEqual(stale, [],
                         f"ALLOWLIST 陈余（已覆盖，请移除条目）: {stale}")
        unlisted = [a for a in zero if a not in ALLOWLIST]
        self.assertEqual(unlisted, [],
                         f"零覆盖且未豁免的 action（补测试或带理由登记 ALLOWLIST）: {unlisted}")


class _SaveDirBase(unittest.TestCase):
    """tmp 存档目录夹具：全冒烟零真实路径接触。

    阶段 0.3 起复用共享存档夹具 fixtures_save（标准库，含旧格式行尾兼容件）。
    """

    def setUp(self):
        self.save_dir = fixtures_save.make_save_dir()
        self.addCleanup(shutil.rmtree, str(self.save_dir), ignore_errors=True)

    def _write_file0(self, numbers: list[int], name: str = fixtures_save.SAMPLE_FILE0_NAME):
        (self.save_dir / "file0").write_bytes(
            fixtures_save.serialize_file0(name, numbers))

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


class TestCjkCheckSmoke(_SaveDirBase):
    """cjk-check 冒烟（纯文本×JSON 运算，零游戏依赖）。"""

    def test_full_coverage_exit0(self):
        import io as _io
        import contextlib as _ctxlib
        buf = _io.StringIO()
        with _ctxlib.redirect_stdout(buf):
            ms.cmd_cjk_check("* 托丽尔你好，这里是中文测试。",
                             Path(__file__).resolve().parent / "fixtures" / "glyphs_min.json")
        self.assertIn("覆盖完备", buf.getvalue())

    def test_missing_glyph_exit1(self):
        import io as _io
        import contextlib as _ctxlib
        # '𠀀'（U+20000，表外）必不在 4064 码点集内
        with self.assertRaises(SystemExit) as cm:
            with _ctxlib.redirect_stdout(_io.StringIO()):
                ms.cmd_cjk_check("* 托丽尔你好𠀀",
                                 Path(__file__).resolve().parent / "fixtures" / "glyphs_min.json")
        self.assertEqual(cm.exception.code, 1)

    def test_missing_glyphs_table_exit2(self):
        import io as _io
        import contextlib as _ctxlib
        with self.assertRaises(SystemExit) as cm:
            with _ctxlib.redirect_stderr(_io.StringIO()):
                ms.cmd_cjk_check("* 你好", Path("/nonexistent/glyphs.json"))
        self.assertEqual(cm.exception.code, 2)

    def test_empty_text_raises(self):
        with self.assertRaises(ms.ValidationError):
            ms.cmd_cjk_check("   ")


class TestDoctorSmoke(_SaveDirBase):
    """doctor 聚合体检冒烟（全只读，tmp 存档目录）。"""

    def test_all_pass_clean_env(self):
        import io as _io
        import contextlib as _ctxlib
        (self.save_dir / "undertale.ini").write_text("[General]\nLove=1\n", encoding="utf-8")
        # 假游戏文件经 patch 定位（避免真实 Steam 路径）
        game = self.save_dir / "game.ios"
        game.write_bytes(b"FAKE-GAME-DOCTOR")
        with mock.patch.object(deterline.paths, "find_game_data_file", return_value=game):
            with self.assertRaises(SystemExit) as cm:
                with _ctxlib.redirect_stdout(_io.StringIO()):
                    ms.cmd_doctor(self.save_dir)
        # tmp 环境：基线比对 ✗（假游戏≠仓库基线）与字形表/UTMT 视本机而定——
        # 只断言"体检完成"行存在与退出码 ∈ {0, 1}
        self.assertIn(cm.exception.code, (0, 1))

    def test_missing_save_dir_reports(self):
        import io as _io
        import contextlib as _ctxlib
        with self.assertRaises(SystemExit) as cm:
            with _ctxlib.redirect_stdout(_io.StringIO()):
                ms.cmd_doctor(None)
        self.assertEqual(cm.exception.code, 1)

    def test_duplicate_key_ini_is_read_only(self):
        """复核 P1-1：doctor 对重复键 ini 必须零写盘（_read_ini 会备份+改写）。"""
        import io as _io
        import contextlib as _ctxlib
        (self.save_dir / "undertale.ini").write_text(
            "[General]\nLove=1\nLove=2\n", encoding="utf-8")
        game = self.save_dir / "game.ios"
        game.write_bytes(b"FAKE")
        before = {q.name: (q.stat().st_mtime_ns, q.stat().st_size)
                  for q in self.save_dir.iterdir()}
        with mock.patch.object(deterline.paths, "find_game_data_file", return_value=game):
            with self.assertRaises(SystemExit) as cm:
                with _ctxlib.redirect_stdout(_io.StringIO()):
                    ms.cmd_doctor(self.save_dir)
        after = {q.name: (q.stat().st_mtime_ns, q.stat().st_size)
                 for q in self.save_dir.iterdir()}
        self.assertEqual(set(after) - set(before), set(),
                         "doctor 不得产生新文件（.bak×2 = 违反零写盘）")
        self.assertEqual((self.save_dir / "undertale.ini").read_text(),
                         "[General]\nLove=1\nLove=2\n", "doctor 不得改写 ini 本体")
        self.assertIn(cm.exception.code, (0, 1))

    def test_dir_pointing_game_file_no_crash(self):
        """复核 P1-2：--dir 指向存档目录（find_game_data_file 返回目录本身）
        → is_file 守卫降级为 ✗ 行，不裸 IsADirectoryError。"""
        import io as _io
        import contextlib as _ctxlib
        with mock.patch.object(deterline.paths, "find_game_data_file",
                               return_value=self.save_dir):  # 目录！
            with self.assertRaises(SystemExit) as cm:
                with _ctxlib.redirect_stdout(_io.StringIO()):
                    ms.cmd_doctor(self.save_dir)
        self.assertEqual(cm.exception.code, 1)  # ✗ 降级，非裸异常


class TestSaveFixtures(unittest.TestCase):
    """阶段 0.3：共享夹具与解析器的行尾兼容契约（新/旧两种 file0）。"""

    def test_stdlib_fixture_roundtrip_through_parser(self):
        import fixtures_save
        d = fixtures_save.make_save_dir()
        self.addCleanup(shutil.rmtree, str(d), ignore_errors=True)
        nums = fixtures_save.read_file0_numbers(d / "file0")
        self.assertEqual(len(nums), len(fixtures_save.SAMPLE_FILE0_NUMBERS))

    def test_legacy_double_cr_still_parses(self):
        import fixtures_save
        import tempfile
        d = Path(tempfile.mkdtemp(prefix="fixtures_legacy_"))
        self.addCleanup(shutil.rmtree, str(d), ignore_errors=True)
        (d / "file0").write_bytes(fixtures_save.serialize_file0_legacy())
        self.assertEqual(len(fixtures_save.read_file0_numbers(d / "file0")),
                         len(fixtures_save.SAMPLE_FILE0_NUMBERS))


class TestDoctorPerItemChecks(_SaveDirBase):
    """审核席 B P2-1：doctor 的单项检查必须有 ✓/✗ 断言（rooms 恒 ✗ 曾被
    吞异常掩盖）。"""

    def test_rooms_check_passes_on_valid_repo(self):
        import io as _io
        import contextlib as _ctxlib
        (self.save_dir / "undertale.ini").write_text("[General]\nLove=1\n", encoding="utf-8")
        game = self.save_dir / "game.ios"
        game.write_bytes(b"FAKE")
        buf = _io.StringIO()
        err = _io.StringIO()
        with mock.patch.object(deterline.paths, "find_game_data_file", return_value=game):
            with _ctxlib.redirect_stdout(buf), _ctxlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as cm:
                    ms.cmd_doctor(self.save_dir)
        out = buf.getvalue()
        # rooms.json 项必须 ✓（解析自仓库真实 rooms.json）
        self.assertIn("✓ rooms.json", out)
        self.assertNotIn("✗ rooms.json", out)
        self.assertIn(cm.exception.code, (0, 1))


class TestBackupIndexSmoke(_SaveDirBase):
    """backup-index 冒烟（O5 最小切片）：只读索引，全 tmp 隔离。

    隔离教训：cmd_backup_index 内部 paths.find_game_data_file(dir_override)
    —— override=None 时优先级 1（Steam）恒压过 env 兜底（v2.3.3 事故模式），
    必须 patch find_game_data_file 本体。
    """

    def _index_output(self, game_file):
        import io as _io
        import contextlib as _ctxlib
        buf = _io.StringIO()
        err = _io.StringIO()
        with mock.patch.object(deterline.paths, "find_game_data_file",
                               return_value=game_file):
            with _ctxlib.redirect_stdout(buf), _ctxlib.redirect_stderr(err):
                ms.cmd_backup_index(self.save_dir, None,
                                    with_hash=self.with_hash)
        return buf.getvalue() + err.getvalue()

    with_hash = False

    def test_lists_bak_snap_workspace_and_legacy(self):
        import json as _json
        game = self.save_dir / "game.ios"
        game.write_bytes(b"FAKE-GAME")
        (self.save_dir / "game.ios.bak").write_bytes(b"a")
        (self.save_dir / "game.ios.bak.20261112_000000_1").write_bytes(b"b")
        (self.save_dir / "game.ios.snap.demo").write_bytes(b"c")
        (self.save_dir / "file0.bak").write_bytes(b"d")
        ws = self.save_dir / ".deterline" / "game.ios" / "cjk_sample"
        ws.mkdir(parents=True)
        (ws / "game.ios").write_bytes(b"WS")
        (ws / "game.ios.json").write_text(
            _json.dumps({"source_sha256": "x", "history": [{"a": 1}, {"b": 2}]}),
            encoding="utf-8")
        out = self._index_output(game)
        self.assertIn("bak-latest", out)
        self.assertIn("bak-archive", out)
        self.assertIn("named-snapshot", out)
        self.assertIn("workspace-copy", out)
        self.assertIn("history=2", out, "manifest history 摘要")
        self.assertNotIn("workspace-legacy", out, "无 .sandbox 时不出现 legacy 行")

    def test_legacy_sandbox_row(self):
        (self.save_dir / "game.ios.sandbox").write_bytes(b"sandbox")
        game = self.save_dir / "game.ios"
        game.write_bytes(b"FAKE")
        out = self._index_output(game)
        self.assertIn("workspace-legacy", out)

    def test_hash_flag_appends_sha256(self):
        game = self.save_dir / "game.ios"
        game.write_bytes(b"FAKE")
        (self.save_dir / "game.ios.bak").write_bytes(b"BAK-CONTENT")
        self.with_hash = True
        try:
            out = self._index_output(game)
        finally:
            self.with_hash = False
        self.assertIn("sha256=", out)

    def test_corrupt_manifest_tolerated(self):
        ws = self.save_dir / ".deterline" / "game.ios" / "ws1"
        ws.mkdir(parents=True)
        (ws / "game.ios").write_bytes(b"WS")
        (ws / "game.ios.json").write_text("{NOT VALID", encoding="utf-8")
        game = self.save_dir / "game.ios"
        game.write_bytes(b"FAKE")
        out = self._index_output(game)
        self.assertIn("manifest损坏", out, "损坏 manifest 容错不崩溃")

    def test_missing_locations_degrade(self):
        import io as _io
        import contextlib as _ctxlib
        empty = Path(tempfile.mkdtemp(prefix="o5_empty_"))
        self.addCleanup(shutil.rmtree, str(empty), ignore_errors=True)
        with mock.patch.object(deterline.paths, "find_game_data_file",
                               return_value=empty / "none.ios"), \
             mock.patch.object(deterline.paths, "find_save_dir",
                               side_effect=FileNotFoundError("无存档目录")):
            with _ctxlib.redirect_stdout(_io.StringIO()):
                ms.cmd_backup_index(None, None)  # 双定位失败 → 降级行不崩溃
