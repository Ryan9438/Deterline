"""O7 集成层：真实 UTMT 三组对照（阶段 1.3 验收，03 手册 §5.3）。

需要本机 UTMT CLI + dotnet + 基线 game.ios（tests/fixtures_utmt 校验），
且默认跳过——设 DETERLINE_RUN_UTMT_INTEGRATION=1 才运行（全套件保持秒级，
集成层 ~4 分钟：4 次 dump + 4 次写命令，全部在 tmp 副本上）。

三组对照（02 验收判据）：
  A 原地改台词：strg_add → strg_set 同 index 改内容 → STR 差异检出、计数不变
  B 等指令数改脚本：create_script 推入字符串常量 → 改该字符串内容 →
    CODEF 指纹必变而指令数不变
  C 移动现有实例：spawn 后夹具 CSX 改坐标 → INST move（非 add/remove）
全部走 --detail --expected 范围判定。
"""

import json
import os
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tests"))
sys.path.insert(0, str(REPO / "scripts"))

from fixtures_utmt import tmp_game_copy, utmt_available  # noqa: E402

os.environ.setdefault("DETERLINE_RUN_UTMT_INTEGRATION", "0")

if os.environ.get("DETERLINE_RUN_UTMT_INTEGRATION") == "1":
    import sys
    sys.path.insert(0, str(REPO / "scripts"))
    import modify_save as ms  # noqa: E402
    from deterline.cmds import verify as verify_mod  # noqa: E402
    from deterline import state as state, utmt as utmt_mod  # noqa: E402


@unittest.skipUnless(
    os.environ.get("DETERLINE_RUN_UTMT_INTEGRATION") == "1"
    and utmt_available(),
    "集成层需 UTMT CLI + dotnet + 基线文件，且 DETERLINE_RUN_UTMT_INTEGRATION=1")
class TestO7Integration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # 提交语义与 smoke-test 内建流同款：写命令直写 tmp 副本（不经工作区），
        # 与 read-through 显式 dump 对齐——否则写进工作区、dump 读显式路径，
        # 变更互相不可见（本轮集成首跑教训）
        cls._policy = (state.COMMIT_ACTIVE, state.SANDBOX_ACTIVE,
                       state.NO_STEAM_SYNC)
        state.COMMIT_ACTIVE = True
        state.SANDBOX_ACTIVE = False
        state.NO_STEAM_SYNC = True
        cls.game = tmp_game_copy(cls)  # tmp 副本（基线 sha 91a8acf1…）
        cls.before = verify_mod._dump_structure_signature(cls.game, timeout=300)

    @classmethod
    def tearDownClass(cls):
        state.COMMIT_ACTIVE, state.SANDBOX_ACTIVE, state.NO_STEAM_SYNC = cls._policy

    def _dump(self):
        return verify_mod._dump_structure_signature(self.game, timeout=300)

    def test_a_string_change_detected(self):
        """A：同 index 原地改台词 → STR change 检出、STRGCOUNT 不变。"""
        a = self._dump()
        ms.cmd_strg_set(self.game, 11432, "* A3 NEW text/")
        b = self._dump()
        rd = verify_mod._diff_detail_resources(a, b)
        changes = [e for op, e in rd["strings"] if op == "change"]
        self.assertGreaterEqual(len(changes), 1,
                         f"原地改台词必须检出（change 含 11432 内容哈希锚）: {rd['strings'][:3]}")
        self.assertEqual(a["counts"]["STRGCOUNT"], b["counts"]["STRGCOUNT"])
        rd2 = verify_mod._diff_detail_resources(a, b)
        ok_scope = verify_mod._evaluate_expected(
            rd2, {"strings": "any", "code": ["gml_Script_textdata_en"]})
        self.assertEqual(ok_scope, [],
                         "声明 strings any + textdata_en 指纹连带后应全部在范围内"
                         f"——实测发现: {ok_scope}")

    def test_b_equal_instruction_count_code_change_detected(self):
        """B：create_script 推入字符串常量 → 改字符串内容 → CODEF 指纹变而
        指令数不变（同指令数改代码的最稳构造，议会补席方案）。"""
        ms.cmd_create_script(self.game, "gml_Script_o7_probe",
                             'show_message("O7_PROBE_OLD");')
        a = self._dump()
        # 找到 O7_PROBE_OLD 的字符串 index 并改内容（指令数不变）
        csx = '''
foreach (var s in Data.Strings)
    if (s.Content == "O7_PROBE_OLD") { s.Content = "O7_PROBE_NEW"; ScriptMessage("CHANGED:" + Data.Strings.IndexOf(s)); break; }
'''
        out = utmt_mod._run_utmt(csx, self.game, save=True, timeout=300)
        self.assertIn("CHANGED:", out)
        b = self._dump()
        rd = verify_mod._diff_detail_resources(a, b)
        self.assertIn("gml_Script_o7_probe", rd["code"]["changed"],
                      "等指令数改代码必须由指纹检出")
        self.assertEqual(a["codefp"]["gml_Script_o7_probe"][0],
                         b["codefp"]["gml_Script_o7_probe"][0],
                         "构造要求：指令数不变")

    def test_c_instance_move_detected(self):
        """C：移动现有实例（id/数量不变，坐标变）→ move 而非 add/remove。"""
        ms.cmd_spawn_obj(self.game, "room_ruins1", "obj_cactus", 220, 330)
        a = self._dump()
        moved_ids = [i for r, i, o, x, y in a["instances"]
                     if r == "room_ruins1" and o == "obj_cactus" and x == 220]
        self.assertTrue(moved_ids, "spawn 后应能在 room_ruins1 找到实例")
        target_id = moved_ids[0]
        csx = f'''
var room = Data.Rooms.ByName("room_ruins1");
foreach (var g in room.GameObjects)
    if (g.InstanceID == {target_id}) {{ g.X += 5; g.Y += 7; ScriptMessage("MOVED:" + g.InstanceID); break; }}
'''
        out = utmt_mod._run_utmt(csx, self.game, save=True, timeout=300)
        self.assertIn("MOVED:", out)
        b = self._dump()
        rd = verify_mod._diff_detail_resources(a, b)
        moved = [m for m in rd["instances"]["moved"] if m[1] == target_id]
        self.assertEqual(len(moved), 1,
                         "移动实例必须以 move（而非 add/remove）检出")
        rd2 = verify_mod._diff_detail_resources(a, b)
        scope = verify_mod._evaluate_expected(
            rd2, {"instances": {"room_ruins1": ["move"]}})
        self.assertEqual(scope, [], "声明 move 后应在范围内")


if __name__ == "__main__":
    unittest.main()
