"""B1（12 计划，原 3.5）现状行为夹具：把模板的房间/对象解析语义钉在测试层。

语义全部是 **CSX 内嵌**（运行时由 UTMT 执行），离线只能钉"生成的 CSX 形态"
——golden 钉字节，本文件钉语义片段（两段式 = exact ByName + OrdinalIgnoreCase
子串回退）。B2 兼容切片若改变这些形态，此处必红——评审有据。

对照 11 §2b 的口径：
- door/pit/battle 的 cur_room 与 door/pit 的 target_room = 两段式（exact + 子串回退）
- room._spawn_obj_internal（NPC 对话/选择命令 Step 3 的落点）= 两段式房 + 两段式对象
  + 双向子串建议扫描（not found 时列出候选）
- npc._query_npc_target = exact ByName → ByName(ignoreCase=true) → 子串回退 + 父链回溯
- utmt._room_id_by_name = **exact-only**（无子串回退），报错带 "smoke-test: " 前缀
  （verify.py 在用——文案修正属单独决策，不并入 B2）

注：door/pit/battle 的反编译应答用真实 "ERROR: not found" 形态（B3 三分类后
空应答=协议异常须拒绝；golden 捕获的 CSX 与应答值无关，字节零变化）。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "tests"))

import modify_save as ms  # noqa: E402
import deterline.utmt as utmt  # noqa: E402
from test_golden_csx import _capture_stateful, dual_patch_utmt, DEFAULT_UTMT_OUT  # noqa: E402

GAME = Path("/tmp/golden_test/game.ios")

# 反编译读请求的应答：真实 not-found 形态（fresh-base 分支）
NOT_FOUND_REPLY = "ERROR: not found"


class TestTwoStageRoomResolution(unittest.TestCase):
    """door/pit target + cur 房解析、battle cur 房解析的两段式形态。"""

    def _door(self, fn, *args, **kwargs):
        captured, result = _capture_stateful(
            fn, GAME, *args,
            replies={'ScriptMessage("IDX:': "IDX:70",
                     'ScriptMessage("GML_LINE:': NOT_FOUND_REPLY},
            **kwargs)
        return captured, result

    def test_door_target_resolution_two_stage(self):
        captured, _ = self._door(ms.cmd_create_door,
                                 "room_golden", "room_golden_b", 320, 240, 100, 200)
        idx_csx = captured[0]
        # 阶段 1：exact ByName
        self.assertIn('Data.Rooms.ByName("room_golden_b")', idx_csx)
        # 阶段 2：大小写不敏感子串回退
        self.assertIn('IndexOf("room_golden_b", StringComparison.OrdinalIgnoreCase)',
                      idx_csx)

    def test_door_cur_room_resolution_two_stage(self):
        captured, _ = self._door(ms.cmd_create_door,
                                 "room_golden", "room_golden_b", 320, 240, 100, 200)
        write_csx = captured[-1]  # 写入阶段 CSX（含 cur 房解析）
        self.assertIn('Data.Rooms.ByName("room_golden")', write_csx)
        self.assertIn('IndexOf("room_golden", StringComparison.OrdinalIgnoreCase)',
                      write_csx)

    def test_pit_target_resolution_two_stage(self):
        captured, _ = _capture_stateful(
            ms.cmd_create_pit, GAME, "room_golden", "room_golden_b",
            320, 240, 100, 200,
            replies={'ScriptMessage("IDX:': "IDX:70",
                     'ScriptMessage("GML_LINE:': NOT_FOUND_REPLY})
        self.assertIn('Data.Rooms.ByName("room_golden_b")', captured[0])
        self.assertIn('IndexOf("room_golden_b", StringComparison.OrdinalIgnoreCase)',
                      captured[0])

    def test_battle_cur_room_resolution_two_stage(self):
        """battle 与 door/pit 同构（cur 房两段式）；**无**目标房预检——
        B1 建议默认：battle 延后（前置 ensure_room = 全命令 capture 新增
        CALL 段，不能声称 golden 零重录——11 §2b 收尾席复核口径）。"""
        captured, _ = _capture_stateful(
            ms.cmd_create_battle, GAME, "room_golden", battlegroup_id=3,
            border=1, x=320, y=240,
            replies={'ScriptMessage("GML_LINE:': NOT_FOUND_REPLY})
        joined = "\n".join(captured)
        self.assertIn('Data.Rooms.ByName("room_golden")', joined)
        self.assertIn('IndexOf("room_golden", StringComparison.OrdinalIgnoreCase)',
                      joined)
        # battle 现状无独立 IDX 预检调用（与 door/pit 的差异钉住）
        door_cap, _ = self._door(ms.cmd_create_door,
                                 "room_golden", "room_golden_b", 320, 240, 100, 200)
        self.assertEqual(len(door_cap) > len(captured),
                         True, "door 应比 battle 多一次 IDX 预检调用")


class TestSpawnAndNpcResolution(unittest.TestCase):
    """room._spawn_obj_internal（npc Step 3 落点）与 npc 对象查询的两段式。"""

    def test_spawn_obj_room_and_object_two_stage(self):
        captured, _ = _capture_stateful(
            ms.cmd_spawn_obj, GAME, "room_golden", "obj_golden_npc", 320, 240,
            replies={'ScriptMessage("GML_LINE:': NOT_FOUND_REPLY})
        csx = "\n".join(captured)
        self.assertIn('Data.Rooms.ByName("room_golden")', csx)
        self.assertIn('IndexOf("room_golden", StringComparison.OrdinalIgnoreCase)',
                      csx)
        self.assertIn('Data.GameObjects.ByName("obj_golden_npc")', csx)
        self.assertIn('IndexOf("obj_golden_npc", StringComparison.OrdinalIgnoreCase)',
                      csx)
        # not-found 候选建议扫描是**双向**子串（房名含查询词或查询词含房名）
        self.assertIn('rn.IndexOf("room_golden", StringComparison.OrdinalIgnoreCase) >= 0 ||',
                      csx)

    def test_npc_query_object_resolution_shape(self):
        from deterline.cmds import npc
        NPC_REPLY = ("NPC_TARGET:RESULT:obj_golden_npc:0:"
                     "gml_Object_obj_golden_npc_Step_0:"
                     "gml_Object_obj_golden_npc_Alarm_0")
        captured, info = _capture_stateful(
            npc._query_npc_target, GAME, "obj_golden_npc",
            replies={'ScriptMessage("NPC_TARGET:': NPC_REPLY})
        self.assertIsNotNone(info)
        csx = "\n".join(captured)
        # _query_npc_target：exact → ignoreCase → 子串回退
        self.assertIn('Data.GameObjects.ByName("obj_golden_npc")', csx)
        self.assertIn('Data.GameObjects.ByName("obj_golden_npc", true)', csx)
        self.assertIn('on.IndexOf(q, StringComparison.OrdinalIgnoreCase)', csx)


class TestRoomIdByNameExactOnly(unittest.TestCase):
    """utmt._room_id_by_name：exact-only + smoke 前缀（现状钉，B2 不动）。
    fake 按 CSX 内 `== "名字"` 精确键应答——模拟 exact-only 运行时语义。"""

    def _patch(self, matched_name: str):
        calls = []

        def fake_run(csx, game_file, save=True):
            calls.append(csx)
            if f'== "{matched_name}"' in csx:
                return "ROOM_ID:42"
            return DEFAULT_UTMT_OUT

        return calls, fake_run

    def test_exact_match_returns_id(self):
        _calls, fake_run = self._patch("room_exact")
        with dual_patch_utmt(side_effect=fake_run):
            self.assertEqual(utmt._room_id_by_name(GAME, "room_exact"), "42")

    def test_partial_name_not_matched_raises_with_smoke_prefix(self):
        _calls, fake_run = self._patch("room_exact")  # 应答方只认 room_exact
        with dual_patch_utmt(side_effect=fake_run):
            try:
                utmt._room_id_by_name(GAME, "room_part")  # exact 比对不命中
            except Exception as exc:
                self.assertIn("smoke-test: 房间未找到", str(exc))
            else:
                self.fail("exact-only 语义下部分名应 NotFoundError")


class TestB3DecompileClassification(unittest.TestCase):
    """B3/O3b：反编译三分类——"条目不存在"与"工具读失败"分开。

    合格出口只有两种：ok（含空内容→模板自裁决 fresh-base）与 not-found
    （显式不存在→fresh-base 允许）；error（工具异常/协议异常）必须拒绝，
    不生成替代脚本、不提交变更。"""

    def test_ok_full_lines(self):
        from deterline.cmds import code
        _cap, result = _capture_stateful(
            code.decompile_classified, GAME, "gml_something",
            replies={'ScriptMessage("GML_LINE:':
                     "GML_COUNT:2\nGML_LINE:0:first\nGML_LINE:1:second"})
        self.assertEqual(result[0], "ok")
        self.assertEqual(result[1], ["first", "second"])
        self.assertIsNone(result[2])

    def test_not_found_explicit(self):
        from deterline.cmds import code
        _cap, result = _capture_stateful(
            code.decompile_classified, GAME, "gml_missing",
            replies={'ScriptMessage("GML_LINE:': "ERROR: not found"})
        self.assertEqual(result[0], "not-found")
        self.assertIsNone(result[1])
        self.assertEqual(result[2], "ERROR: not found")

    def test_error_tool_failure(self):
        from deterline.cmds import code
        _cap, result = _capture_stateful(
            code.decompile_classified, GAME, "gml_broken",
            replies={'ScriptMessage("GML_LINE:': "ERROR: decompile exploded"})
        self.assertEqual(result[0], "error")
        self.assertIn("decompile exploded", result[2])

    def test_error_protocol_anomaly_empty_output(self):
        """空应答（无 GML_COUNT 无 ERROR）= 协议异常 → error（B3 核心语义）。"""
        from deterline.cmds import code
        _cap, result = _capture_stateful(
            code.decompile_classified, GAME, "gml_any",
            replies={'ScriptMessage("GML_LINE:': ""})
        self.assertEqual(result[0], "error")
        self.assertIn("GML_COUNT 缺失", result[2])

    def test_error_missing_line_sequence(self):
        from deterline.cmds import code
        _cap, result = _capture_stateful(
            code.decompile_classified, GAME, "gml_any",
            replies={'ScriptMessage("GML_LINE:':
                     "GML_COUNT:3\nGML_LINE:0:a\nGML_LINE:2:c"})
        self.assertEqual(result[0], "error")
        self.assertIn("序列不全", result[2])

    def test_door_read_failure_refuses_before_write(self):
        """读失败 → DeterlineError；idx 预查之外**零** CSX 发出（无写入）。"""
        captured = []
        table = [('ScriptMessage("IDX:', "IDX:70"),
                 ('ScriptMessage("GML_LINE:', "ERROR: tool blew up")]

        def fake_run(csx_code, game_file, save=True):
            captured.append(csx_code)
            for probe, response in table:
                if probe in csx_code:
                    return response
            return DEFAULT_UTMT_OUT

        with dual_patch_utmt(side_effect=fake_run):
            with self.assertRaises(Exception) as ctx:
                ms.cmd_create_door(GAME, "room_golden", "room_golden_b",
                                   320, 240, 100, 200)
        self.assertIn("反编译读失败", str(ctx.exception))
        # 两次只读调用（idx 预查 + 反编译读取），零写入 CSX
        self.assertEqual(len(captured), 2)
        self.assertIn("IDX:", captured[0])
        self.assertIn("Data.Code.ByName", captured[1])
        self.assertTrue(all("CodeImportGroup" not in c for c in captured),
                        "读失败不得发出任何写入 CSX")

    def test_door_exists_but_empty_still_fresh_base(self):
        """ok + 空内容 = "存在且已读"——fresh-base 由模板自裁决（合法路径）。"""
        captured, _ = _capture_stateful(
            ms.cmd_create_door, GAME, "room_golden", "room_golden_b",
            320, 240, 100, 200,
            replies={'ScriptMessage("IDX:': "IDX:70",
                     'ScriptMessage("GML_LINE:':
                     "GML_COUNT:1\nGML_LINE:0:"})
        self.assertGreaterEqual(len(captured), 2, "空内容应走 fresh-base 完成写入")


if __name__ == "__main__":
    unittest.main()
