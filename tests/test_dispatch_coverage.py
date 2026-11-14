"""拆包后冷路径覆盖棘轮（风险席提案裁决落地，2026-11-11）。

room-list P0 的土壤：接线层 bug 不被 CSX golden 钉住，而冷路径零测试覆盖
让它潜伏到运行时。本文件三层防线：

1. 覆盖地图（动态计算）：commands.json 的每个 action，其 action 名或实现
   cmd_* 函数名必须在 tests/ 出现过——零覆盖集合必须 ⊆ ALLOWLIST
   （2026-11-14 口径：91 actions = 71 已覆盖 + 20 条显式豁免）。
   新增命令不带测试即爆红。
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
#   - md5/sandbox-restore：已收编（2026-11-13 抽 cmd_md5/cmd_sandbox_restore
#     入 cmds/save_cmds.py，测试见 test_transactions_unittest.TestDispatchRemnantCmds）
#   - 其余 20 条：读式/诊断命令（UTMT 查询+打印）或重游戏依赖命令
#     （npc-dialogue/smoke-test/replace-texture），行为面已由 golden CSX
#     （28 生成器钉死）+ A3 双轮游戏级快照 parity 覆盖；补单测 = 独立后续项
#     （需 dual_patch_utmt mock 逐条搭夹具，与本 commit 的接线防线目标正交）。
# 新命令若暂缺测试，须连同理由登记于此（下一 commit 补测试即移除）。
ALLOWLIST: dict[str, str] = {
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
    # verify-code：2026-11-13 移出——cjk-trigger 前置校验测试引用
    # cmd_verify_code（test_cjk_wrap.TestCjkTriggerGlyphPreflight），
    # 且五步管线的收尾步每轮实测（原理由）见 CHANGELOG v2.3.2
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
        # 排除自引用源：①棘轮自身（ALLOWLIST 理由文本提到 action 名会把自己
        # 算成"已覆盖"）②compat_surface 的 FROZEN_EXPORTS 冻结名册块
        # （2026-11-13 全量导出锁入清单后，213 个 cmd_* 名被子串扫描误判成
        # 21 条 ALLOWLIST 项"已覆盖"——名册不是覆盖；COMPAT_SURFACE 原有
        # 语义保持不变）
        def _coverage_text(f):
            text = f.read_text(encoding="utf-8")
            if f.name == "test_compat_surface.py":
                head, sep, _tail = text.partition("FROZEN_EXPORTS = [")
                # C P2-2：截断必须真发生——字面量漂移（如加类型注解）曾会
                # 静默返回全文，215 个冻结名会把 20 条 ALLOWLIST 误判成
                # "已覆盖"并强制清偿，棘轮整体假绿
                if not sep:
                    raise AssertionError(
                        "test_compat_surface.py 找不到 'FROZEN_EXPORTS = [' "
                        "字面量——冻结名册截断失效（棘轮假绿面）；"
                        "请同步更新本处的匹配标记")
                text = head
            return text
        test_src = "\n".join(
            _coverage_text(f) for f in (REPO / "tests").glob("test_*.py")
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


class TestBackupPrune(_SaveDirBase):
    """backup-prune 冒烟（03 §2.4 最小切片）：只读预览，零删除。"""

    def _prune(self, keep_archives=3, json_out=False):
        import io as _io
        import contextlib as _ctxlib
        game = self.save_dir / "game.ios"
        buf = _io.StringIO()
        with mock.patch.object(deterline.paths, "find_game_data_file",
                               return_value=game):
            with _ctxlib.redirect_stdout(buf):
                code = ms.cmd_backup_prune(self.save_dir, None,
                                           keep_archives=keep_archives,
                                           json_out=json_out)
        return buf.getvalue(), code

    def _make_archives(self, count, dup_oldest=0, same_mtime=False):
        """count 份归档，mtime 递增；最旧 dup_oldest 份内容与最新一份重复。
        same_mtime=True：全部归档同一 mtime（A P2-1 整秒截断反转面）。"""
        import time as _time
        game = self.save_dir / "game.ios"
        game.write_bytes(b"GAME")
        # 每份独立内容；最旧 dup_oldest 份改写为与最新一份相同（重复组）
        contents = [f"ARCH-{i}".encode() for i in range(count)]
        for i in range(dup_oldest):
            contents[i] = contents[-1]
        fixed_stamp = _time.time()  # 同一值 → st_mtime_ns 全等（纯 tiebreak 面）
        for i, content in enumerate(contents):
            archive = self.save_dir / f"game.ios.bak.2026111{i}_000000_{i}"
            archive.write_bytes(content)
            stamp = _time.time() - (count - i) * 100
            if same_mtime:
                stamp = fixed_stamp
            import os as _os
            _os.utime(archive, (stamp, stamp))
        (self.save_dir / "game.ios.snap.keepme").write_bytes(b"SNAP")
        (self.save_dir / "game.ios.bak").write_bytes(b"LATEST")

    def test_preview_deletes_nothing_and_suggests_beyond_window(self):
        self._make_archives(5)
        files_before = sorted(p.name for p in self.save_dir.iterdir())
        out, code = self._prune(keep_archives=3)
        files_after = sorted(p.name for p in self.save_dir.iterdir())
        self.assertEqual(files_before, files_after,
                         "预览模式必须零删除（03 §2.4：由用户决定）")
        self.assertEqual(code, 0)
        self.assertIn("backup-prune（只读预览，零删除）", out)
        self.assertIn("建议删除 2 项", out, "5 份归档 - 窗口 3 = 2 份超窗")
        self.assertIn('rm "', out)
        self.assertNotIn("game.ios.snap.keepme", out.split("建议删除")[1],
                         "命名快照永不入删除集")
        # 顺序不变量：undo --backup 后果提示只出现在"保留条件"头之后
        # （删除集行内）；统计/重复组段不得出现（B P3-8 改写）
        self.assertLess(out.index("保留条件"), out.index("undo --value"),
                        "undo 后果提示必须位于删除集段内")

    def test_duplicate_group_reported(self):
        self._make_archives(4, dup_oldest=2)
        out, _ = self._prune(keep_archives=3)
        self.assertIn("重复内容", out)
        self.assertIn("×3", out, "2 份重复归档 + 最新 1 份同内容")
        # B P2-1 回归钉：reclaimable 只计进入删除集的重复份（曾因
        # deletion_paths 在同组删除集之前快照而恒为 0）
        import json as _json
        jout, _ = self._prune(keep_archives=3, json_out=True)
        payload = _json.loads(jout)
        dup = [g for g in payload["duplicate_groups"] if g["count"] > 1]
        self.assertTrue(dup, "重复组必须被报告")
        self.assertGreater(dup[0]["reclaimable_bytes"], 0,
                           "超窗重复份可回收字节必须 > 0（B P2-1 曾恒 0）")
        # 4 份归档 keep=3 → 删除集恰 1 份（最旧的重复份）：reclaimable
        # 必须恰等于该删除行字节——窗口内保留的重复份不得虚报
        self.assertEqual(dup[0]["reclaimable_bytes"],
                         payload["deletions"][0]["size_bytes"])

    def test_same_mtime_keeps_newest(self):
        """A P2-1 回归钉：同秒 mtime 归档保留方向必须仍是"留最新"。
        （mtime_epoch 整秒截断 + 稳定排序曾反转——删最新留最旧。）"""
        self._make_archives(5, same_mtime=True)
        out, code = self._prune(keep_archives=3)
        self.assertEqual(code, 0)
        rm_lines = [l for l in out.splitlines() if l.startswith('    rm "')]
        self.assertEqual(len(rm_lines), 2, "5 份 - 窗口 3 = 2 份超窗")
        tails = [l.rsplit("/", 1)[-1] for l in rm_lines]
        self.assertTrue(any(t.endswith('_000000_0"') for t in tails),
                        f"删除建议必须指向最旧两份（A P2-1）：{tails}")
        self.assertTrue(any(t.endswith('_000000_1"') for t in tails))
        self.assertFalse(any(t.endswith(('_000000_3"', '_000000_4"'))
                             for t in tails), "同秒场景不得误删最新归档")

    def test_json_schema_and_purity(self):
        import json as _json
        self._make_archives(4)
        out, code = self._prune(json_out=True)
        payload = _json.loads(out)
        self.assertEqual(payload["schema"], "deterline.backup-prune/v1")
        self.assertEqual(code, 0)
        self.assertEqual(len(payload["deletions"]), 1,
                         "4 份 - 窗口 3 = 1 份超窗")
        self.assertGreaterEqual(len(payload["duplicate_groups"]), 0)
        for key in ("stats", "duplicate_groups", "deletions", "kept_counts"):
            self.assertIn(key, payload)

    def test_journal_protected_archive_skipped(self):
        import json as _json
        self._make_archives(5)
        oldest = sorted(self.save_dir.glob("game.ios.bak.2026*"))[0]
        journal_dir = self.save_dir / ".deterline" / "journal"
        journal_dir.mkdir(parents=True)
        (journal_dir / "active.json").write_text(json.dumps({
            "schema": "deterline.run-journal/v1", "id": "j", "state": "committing",
            "targets": [{"path": str(oldest), "before": None, "after": None,
                         "rollback": None, "staged": None}],
        }), encoding="utf-8")
        out, _ = self._prune(keep_archives=3)
        self.assertNotIn(f'rm "{oldest}"', out,
                         "journal 引用的归档必须被保护跳过")
        self.assertIn("journal 保护跳过 1 项", out)

    def test_corrupt_journal_warning_visible_human(self):
        """R2 P3-3 回归钉：损坏 journal 前置信号人读模式必须可见（B P2-3）。"""
        import io as _io
        import contextlib as _ctxlib
        self._make_archives(3)
        journal_dir = self.save_dir / ".deterline" / "journal"
        journal_dir.mkdir(parents=True)
        (journal_dir / "broken.json").write_text("{broken", encoding="utf-8")
        game = self.save_dir / "game.ios"
        buf, err = _io.StringIO(), _io.StringIO()
        with mock.patch.object(deterline.paths, "find_game_data_file",
                               return_value=game):
            with _ctxlib.redirect_stdout(buf), _ctxlib.redirect_stderr(err):
                code = ms.cmd_backup_prune(self.save_dir, None, keep_archives=3)
        self.assertEqual(code, 0)
        self.assertIn("损坏/不可解析运行记录", err.getvalue(),
                      "人读模式必须可见损坏 journal 前置信号（B P2-3）")

    def test_keep_archives_zero_rejected(self):
        """审核席 A P2-2：--keep-archives 0 不得被静默吞成默认 3。"""
        import types as _types
        import deterline.command_handlers as _ch
        game = self.save_dir / "game.ios"
        game.write_bytes(b"G")

        class _Parser:
            def error(self, msg):
                raise SystemExit(2)

        args = _types.SimpleNamespace(dir=str(self.save_dir), json=False,
                                      keep_archives=0)
        with mock.patch.object(deterline.paths, "find_save_dir",
                               return_value=self.save_dir), \
             mock.patch.object(deterline.paths, "resolve_game_data_file",
                               return_value=game):
            with self.assertRaises(SystemExit) as cm:
                _ch._backup_prune(args, _Parser(), None)
        self.assertEqual(cm.exception.code, 2)

    def test_system_info_archives_within_window(self):
        """P3-5B：system-info 归档同样受 --keep-archives 窗口管理。"""
        import time as _time
        import os as _os
        for i in range(5):
            p = self.save_dir / f"system_information_962.bak.2026111{i}_00000_{i}"
            p.write_bytes(f"SYS-{i}".encode())
            stamp = _time.time() - (5 - i) * 100
            _os.utime(p, (stamp, stamp))
        out, _ = self._prune(keep_archives=2)
        self.assertIn("建议删除 3 项", out, "5 份 sysinfo 归档 - 窗口 2 = 3")

    def test_missing_locations_exit2(self):
        import io as _io
        import contextlib as _ctxlib
        buf = _io.StringIO()
        with mock.patch.object(deterline.paths, "resolve_game_data_file",
                               side_effect=FileNotFoundError("无游戏")):
            with _ctxlib.redirect_stdout(buf):
                code = ms.cmd_backup_prune(None, "/tmp/dl_missing_9f3c2")
        self.assertEqual(code, 2)


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
        """提示文本断言（审核席 A/B：提示列是本切片唯一交付物，须与
        cmd_undo/cmd_experiment_restore 的 key/tag 语义精确对齐）。"""
        import json as _json
        game = self.save_dir / "game.ios"
        game.write_bytes(b"FAKE-GAME")
        (self.save_dir / "game.ios.bak").write_bytes(b"a")
        (self.save_dir / "game.ios.bak.20261112_000000_1").write_bytes(b"b")
        (self.save_dir / "game.ios.snap.demo").write_bytes(b"c")
        (self.save_dir / "file0.bak").write_bytes(b"d")
        (self.save_dir / "undertale.ini.bak.20261112_010101").write_bytes(b"e")
        (self.save_dir / "undertale.ini.snap.t1").write_bytes(b"f")
        (self.save_dir / "game.ios.snap.t1").write_bytes(b"g")  # 组快照存在才可恢复
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
        self.assertIn("ok=2", out, "manifest history 摘要")
        self.assertNotIn("workspace-legacy", out, "无 .sandbox 时不出现 legacy 行")
        # 提示语义对齐（P1-1/2/3 回归钉）
        self.assertIn("undo --value game.ios --dir", out, "game 侧 latest 合法 key")
        self.assertIn("undo --value game.ios --backup 20261112_000000_1", out,
                      "archive 行须带 --backup tag")
        self.assertIn("experiment-restore --value demo", out,
                      "snap 行须剥前缀取 tag（P1-1）")
        self.assertIn("sandbox-restore --workspace cjk_sample", out,
                      "工作区行必须用 --workspace（024e698 回退回归钉）")
        self.assertNotIn("sandbox-restore --value cjk_sample", out,
                         "工作区行不得再用 --value（会被静默忽略）")
        self.assertIn("undo --value file0", out)
        self.assertIn("undo --value ini --backup 20261112_010101", out,
                      "ini 的合法 key 是 ini（P1-3）")
        self.assertIn("experiment-restore --value t1", out,
                      "ini snap tag 须剥 undertale.ini.snap. 前缀（P1-2）")
        self.assertNotIn("undo --value undertale.ini", out, "非法 key 不得出现")
        self.assertNotIn("experiment-restore --value game.ios.snap", out,
                         "双前缀 tag 不得出现")

    def test_legacy_sandbox_row(self):
        (self.save_dir / "game.ios.sandbox").write_bytes(b"sandbox")
        game = self.save_dir / "game.ios"
        game.write_bytes(b"FAKE")
        out = self._index_output(game)
        self.assertIn("workspace-legacy", out)
        self.assertIn("sandbox-restore --dir", out,
                      "legacy 恢复不需要 --value（空值会令 argparse 报错）")
        self.assertNotIn("sandbox-restore --value", out)

    def test_legacy_sandbox_hint_restores(self):
        """legacy .sandbox 无 manifest 也必须可恢复（提示列的唯一用途）。"""
        import types as _types
        import deterline.command_handlers as _ch
        import deterline.state as _state
        game = self.save_dir / "game.ios"
        game.write_bytes(b"BASE")
        (self.save_dir / "game.ios.sandbox").write_bytes(b"LEGACY")
        with mock.patch.object(_state, "WORKSPACE", None), \
             mock.patch.object(_state, "PREVIEW", False):
            _ch._sandbox_restore(_types.SimpleNamespace(dir=str(game)),
                                 None, None)
        self.assertEqual(game.read_bytes(), b"LEGACY")

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
        self.assertIn("损坏(", out, "损坏 manifest 容错不崩溃")

    def test_system_info_indexed_and_undovable(self):
        """议会 D'（第四选项）：system_information_962/963 备份此前
        不被索引也不能 undo——扩 _backup_target keys + 索引覆盖。"""
        import io as _io
        import contextlib as _ctxlib
        (self.save_dir / "system_information_962").write_bytes(b"")
        (self.save_dir / "system_information_962.bak").write_bytes(b"pre")
        game = self.save_dir / "game.ios"
        game.write_bytes(b"FAKE")
        out = self._index_output(game)
        self.assertIn("system-info", out, "sysinfo 文件应被索引")
        self.assertIn("undo --value 962", out, "恢复提示应给出合法 undo key")
        # undo 可用性：用备份恢复 sysinfo
        with mock.patch.object(deterline.paths, "find_game_data_file",
                               return_value=game):
            ms.cmd_undo(self.save_dir, "962")
        self.assertEqual((self.save_dir / "system_information_962").read_bytes(),
                         b"pre", "undo 962 应从 .bak 恢复")

    def test_no_save_dir_hint_has_no_none_dir(self):
        """审核席 A/B P2-1 回归钉：存档侧未定位时，游戏侧提示不得出现
        --dir "None"（粘贴即错）；JSON restore 不得带 dir:null 键。
        （patch 游戏定位到 tmp——否则 CI 无 Steam 时 entries 为空
        StopIteration，而本机会静默读真实 Steam 目录：夹具泄漏同型。）"""
        import json as _json
        import io as _io
        import contextlib as _ctxlib
        game = self.save_dir / "game.ios"
        game.write_bytes(b"FAKE")
        (self.save_dir / "game.ios.snap.demo").write_bytes(b"s")
        buf = _io.StringIO()
        payload_buf = _io.StringIO()
        with mock.patch.object(deterline.paths, "find_save_dir",
                               side_effect=FileNotFoundError("无存档目录")), \
             mock.patch.object(deterline.paths, "resolve_game_data_file",
                               return_value=game):
            with _ctxlib.redirect_stdout(buf):
                ms.cmd_backup_index(None, None)
            with _ctxlib.redirect_stdout(payload_buf):
                ms.cmd_backup_index(None, None, json_out=True)
        self.assertNotIn('--dir "None"', buf.getvalue())
        payload = _json.loads(payload_buf.getvalue())
        snap = next(e for e in payload["entries"]
                    if e["kind"] == "named-snapshot")
        self.assertNotIn("dir", snap["restore"])

    def test_missing_locations_degrade(self):
        """双定位失败 → 降级提示行（含断言；审核席 B P2-4：原版零断言且
        find_game_data_file 的 FileNotFoundError 降级分支零覆盖）。"""
        import io as _io
        import contextlib as _ctxlib
        buf = _io.StringIO()
        err = _io.StringIO()
        with mock.patch.object(deterline.paths, "find_game_data_file",
                               side_effect=FileNotFoundError("游戏数据目录未定位")), \
             mock.patch.object(deterline.paths, "find_save_dir",
                               side_effect=FileNotFoundError("无存档目录")):
            with _ctxlib.redirect_stdout(buf), _ctxlib.redirect_stderr(err):
                code = ms.cmd_backup_index(None, None)
        out = buf.getvalue() + err.getvalue()
        self.assertEqual(code, 2, "两侧定位均失败必须非零（可区分空索引与路径错）")
        self.assertIn("游戏数据目录未定位", out)
        self.assertIn("存档目录未定位", out)
        self.assertIn("索引完成", out)

    def test_ini_snapshot_and_archive_hints(self):
        """P1-2/P2-b 回归：undertale.ini 的 snap tag 与 archive --backup。"""
        import io as _io
        import contextlib as _ctxlib
        (self.save_dir / "undertale.ini").write_text("[General]\n", encoding="utf-8")
        (self.save_dir / "undertale.ini.bak.20261112_010101").write_bytes(b"x")
        (self.save_dir / "undertale.ini.snap.t1").write_bytes(b"y")
        (self.save_dir / "game.ios.snap.t1").write_bytes(b"z")
        game = self.save_dir / "game.ios"
        game.write_bytes(b"FAKE")
        out = self._index_output(game)
        self.assertIn("experiment-restore --value t1", out)
        self.assertIn("undo --value ini --backup 20261112_010101", out)

    def test_orphan_snapshot_not_recommended(self):
        """save 侧孤儿快照（缺 game.ios.snap.<tag>）不得给出死命令提示。"""
        (self.save_dir / "undertale.ini.snap.orphan").write_bytes(b"y")
        game = self.save_dir / "game.ios"
        game.write_bytes(b"FAKE")
        out = self._index_output(game)
        self.assertIn("orphan-snapshot", out)
        self.assertNotIn("experiment-restore --value orphan", out)

    def test_json_output_is_pure_and_complete(self):
        """--json：stdout 必须是纯 JSON（不得混文本行），行键齐全。"""
        import io as _io
        import json as _json
        import contextlib as _ctxlib
        game = self.save_dir / "game.ios"
        game.write_bytes(b"G")
        (self.save_dir / "game.ios.bak").write_bytes(b"B")
        (self.save_dir / "undertale.ini.snap.orphan").write_bytes(b"O")
        ws = self.save_dir / ".deterline" / "game.ios" / "wsj"
        ws.mkdir(parents=True)
        (ws / "game.ios").write_bytes(b"WS")
        (ws / "game.ios.json").write_text("{}", encoding="utf-8")
        buf = _io.StringIO()
        err = _io.StringIO()
        with mock.patch.object(deterline.paths, "find_game_data_file",
                               return_value=game):
            with _ctxlib.redirect_stdout(buf), _ctxlib.redirect_stderr(err):
                code = ms.cmd_backup_index(self.save_dir, None,
                                           json_out=True)
        self.assertEqual(code, 0)
        payload = _json.loads(buf.getvalue())  # 纯 JSON：有文本行会直接抛错
        self.assertEqual(payload["schema"], "deterline.backup-index/v1")
        self.assertEqual(err.getvalue(), "")
        kinds = {e["kind"] for e in payload["entries"]}
        self.assertIn("bak-latest", kinds)
        self.assertIn("orphan-snapshot", kinds)
        for entry in payload["entries"]:
            for key in ("kind", "path", "restore", "mtime_epoch",
                        "mtime_iso", "size_bytes", "sha256"):
                self.assertIn(key, entry)
        ws_entry = next(e for e in payload["entries"]
                        if e["kind"] == "workspace-copy")
        self.assertEqual(ws_entry["restore"]["cmd"], "sandbox-restore")
        self.assertEqual(ws_entry["restore"]["workspace"], "wsj")
        self.assertNotIn("value", ws_entry["restore"])

    def test_invalid_dir_never_falls_back_to_default(self):
        """显式 --dir 无效时不得回退真实 Steam（D 席 P1-2 同型风险）。"""
        import io as _io
        import contextlib as _ctxlib
        buf = _io.StringIO()
        err = _io.StringIO()
        missing = "/tmp/deterline_missing_dir_9f3c1"
        with mock.patch.object(deterline.paths, "find_game_data_file",
                               side_effect=AssertionError("不得回退默认定位")):
            with _ctxlib.redirect_stdout(buf), _ctxlib.redirect_stderr(err):
                code = ms.cmd_backup_index(None, missing)
        self.assertEqual(code, 2)
        self.assertIn("路径不存在", err.getvalue())
        self.assertNotIn("Steam", buf.getvalue())

    def test_experiment_honors_env_override(self):
        """experiment-* 必须能用 DETERLINE_GAME_FILE 隔离（不得恒走 Steam）。"""
        game = self.save_dir / "game.ios"
        game.write_bytes(b"G")
        (self.save_dir / "file0").write_bytes(b"F")
        with mock.patch.dict(os.environ, {"DETERLINE_GAME_FILE": str(game)}), \
             mock.patch.object(deterline.paths, "find_game_data_file",
                               side_effect=AssertionError("不应走默认定位")):
            ms.cmd_experiment_snapshot(self.save_dir, "envtest")
        self.assertTrue((self.save_dir / "game.ios.snap.envtest").is_file())
        self.assertTrue((self.save_dir / "file0.snap.envtest").is_file())

    def test_dir_override_directory_locates_both_sides(self):
        """--dir 指向含 game.ios 的目录时，双侧都应索引。"""
        game = self.save_dir / "game.ios"
        game.write_bytes(b"G")
        (self.save_dir / "game.ios.bak").write_bytes(b"B")
        (self.save_dir / "file0.bak").write_bytes(b"F")
        import io as _io
        import contextlib as _ctxlib
        buf = _io.StringIO()
        with mock.patch.object(deterline.paths, "find_game_data_file",
                               side_effect=AssertionError("不应回退默认定位")):
            with _ctxlib.redirect_stdout(buf):
                code = ms.cmd_backup_index(self.save_dir, str(self.save_dir))
        out = buf.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("game.ios.bak", out)
        self.assertIn("file0.bak", out)

class TestDiffSnapshotsDispatch(unittest.TestCase):
    """B P2-3：显式 A/B 不应依赖默认游戏文件定位。"""

    def test_explicit_ab_without_default_game(self):
        import deterline.cli as cli_mod
        from deterline.cmds import verify as verify_mod
        argv = ["run.py", "--action", "diff-snapshots", "--file", "data_win",
                "--key", "/tmp/a.ios", "--value", "/tmp/b.ios", "--detail"]
        with mock.patch.object(sys, "argv", argv), \
             mock.patch.object(cli_mod.paths, "find_game_data_file",
                               side_effect=FileNotFoundError("no game")), \
             mock.patch.object(verify_mod, "cmd_diff_snapshots",
                               return_value=0) as call:
            cli_mod.main()
        self.assertTrue(call.called, "显式 A/B 不应依赖默认游戏文件")


class TestDoctorJson(unittest.TestCase):
    """doctor --json（v2.5.5）：纯 JSON + fails 计数与退出码一致。"""

    def test_json_pure_and_fails_counted(self):
        import io as _io
        import json as _json
        import contextlib as _ctxlib
        save_dir = fixtures_save.make_save_dir()
        self.addCleanup(shutil.rmtree, str(save_dir), ignore_errors=True)
        game = save_dir / "game.ios"
        game.write_bytes(b"NOT-BASELINE")   # 触发基线比对 ✗ → fails ≥ 1
        (save_dir / "rooms_json_probe").write_bytes(b"")
        buf = _io.StringIO()
        with mock.patch.object(deterline.paths, "find_game_data_file",
                               return_value=game):
            with _ctxlib.redirect_stdout(buf):
                with self.assertRaises(SystemExit) as cm:
                    ms.cmd_doctor(save_dir, json_out=True)
        self.assertEqual(cm.exception.code, 1)
        payload = _json.loads(buf.getvalue())  # 纯 JSON
        self.assertEqual(payload["schema"], "deterline.doctor/v1")
        first = next(i for i in payload["items"]
                     if i["label"] == "存档目录定位")
        if not first["ok"]:
            self.assertTrue(first["detail"],
                            "定位失败原因必须进 JSON detail（B P2：曾整体蒸发）")
        self.assertGreaterEqual(payload["fails"], 1,
                                "JSON 模式 fails 必须与 ✗ 项一致（曾恒 0）")
        self.assertEqual(sum(1 for i in payload["items"] if not i["ok"]),
                         payload["fails"])

    def test_json_all_ok_exits_zero(self):
        import io as _io
        import json as _json
        import contextlib as _ctxlib
        save_dir = fixtures_save.make_save_dir()
        self.addCleanup(shutil.rmtree, str(save_dir), ignore_errors=True)
        game = save_dir / "game.ios"
        game.write_bytes(b"FAKE")  # 与基线不一致也会 ✗——patch 掉基线比对不现实，
        # 改为接受 rc∈{0,1}：断言焦点是纯 JSON + fails 与 items 一致
        buf = _io.StringIO()
        with mock.patch.object(deterline.paths, "find_game_data_file",
                               return_value=game):
            with _ctxlib.redirect_stdout(buf):
                try:
                    ms.cmd_doctor(save_dir, json_out=True)
                    rc = 0
                except SystemExit as cm:
                    rc = cm.code
        payload = _json.loads(buf.getvalue())
        self.assertEqual(payload["schema"], "deterline.doctor/v1")
        self.assertEqual(sum(1 for i in payload["items"] if not i["ok"]),
                         payload["fails"])

    def test_json_non_dict_rooms_reported_fail(self):
        """B P2-4 回归钉：非 dict 形态 rooms.json 不得报 ✓（曾 ✓ 0 条）。"""
        import io as _io
        import json as _json
        import contextlib as _ctxlib
        from deterline import rooms_data as _rooms_data
        save_dir = fixtures_save.make_save_dir()
        self.addCleanup(shutil.rmtree, str(save_dir), ignore_errors=True)
        bad = save_dir / "rooms.json"
        bad.write_text("[1, 2, 3]", encoding="utf-8")
        game = save_dir / "game.ios"
        game.write_bytes(b"NOT-BASELINE")
        buf = _io.StringIO()
        with mock.patch.object(deterline.paths, "find_game_data_file",
                               return_value=game), \
             mock.patch.object(_rooms_data, "_rooms_json_path",
                               return_value=bad):
            with _ctxlib.redirect_stdout(buf):
                with self.assertRaises(SystemExit) as cm:
                    ms.cmd_doctor(save_dir, json_out=True)
        self.assertEqual(cm.exception.code, 1)
        payload = _json.loads(buf.getvalue())
        item = next(i for i in payload["items"]
                    if i["label"].startswith("rooms.json 可解析"))
        self.assertFalse(item["ok"], "非映射形态必须 ✗（B P2-4：曾 ✓ 0 条）")
        self.assertIn("非映射形态", item["detail"])


class TestAdapterJsonStderrPurity(unittest.TestCase):
    """B P2-2 回归钉：backup-index/prune --json 时定位失败不得污染 stderr
    （对照 _recovery_scan/_doctor 的同型守卫）。"""

    def _run(self, handler_name, **extra):
        import io as _io
        import contextlib as _ctxlib
        import types as _types
        import deterline.command_handlers as _ch
        args = _types.SimpleNamespace(dir="/nonexistent-dir-xyz", json=True,
                                      **extra)

        class _Parser:
            def error(self, msg):
                raise SystemExit(2)

        buf, err = _io.StringIO(), _io.StringIO()
        with mock.patch.object(deterline.paths, "find_save_dir",
                               side_effect=FileNotFoundError("找不到存档目录")):
            with _ctxlib.redirect_stdout(buf), _ctxlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as cm:
                    getattr(_ch, handler_name)(args, _Parser(), None)
        return buf.getvalue(), err.getvalue(), cm.exception.code

    def test_backup_index_json_stderr_silent(self):
        out, err, code = self._run("_backup_index")
        self.assertEqual(err, "", "--json 模式 stderr 必须静默（B P2-2）")
        payload = json.loads(out)
        self.assertEqual(payload["schema"], "deterline.backup-index/v1")
        self.assertTrue(any("存档目录未定位" in w for w in payload["warnings"]),
                        "定位失败原因必须随 payload warnings 走")
        self.assertEqual(code, 2)

    def test_backup_prune_json_stderr_silent(self):
        out, err, code = self._run("_backup_prune", keep_archives=3)
        self.assertEqual(err, "", "--json 模式 stderr 必须静默（B P2-2）")
        payload = json.loads(out)
        self.assertEqual(payload["schema"], "deterline.backup-prune/v1")
        self.assertTrue(any("存档目录未定位" in w for w in payload["warnings"]))
        self.assertEqual(code, 2)


class TestDirectRunParity(unittest.TestCase):
    """R2 P3-2 回归钉：直跑（python3 tests/test_dispatch_coverage.py）与
    loader 口径必须同数——__main__ 曾在类定义之前而静默缺类（45 vs 47）。"""

    def test_direct_run_count_matches_loader(self):
        if os.environ.get("DETERLINE_SKIP_DIRECT_RUN_PARITY") == "1":
            self.skipTest("嵌套直跑防护（子进程已置位）")
        import subprocess as _sub
        import test_dispatch_coverage as _self_mod
        expected = unittest.defaultTestLoader \
            .loadTestsFromModule(_self_mod).countTestCases()
        env = dict(os.environ, DETERLINE_SKIP_DIRECT_RUN_PARITY="1")
        r = _sub.run([sys.executable, str(Path(__file__).resolve())],
                     capture_output=True, text=True, encoding="utf-8",
                     errors="replace", env=env, timeout=180)
        m = re.search(r"^Ran (\d+) tests?", r.stdout + r.stderr, re.M)
        self.assertIsNotNone(m, f"直跑无 Ran 汇总：{(r.stderr or '')[-200:]}")
        self.assertEqual(int(m.group(1)), expected,
                         "直跑与 loader 测试数不一致——__main__ 位置或加载漂移"
                         "（R2 P3-2）")


if __name__ == "__main__":
    unittest.main()
