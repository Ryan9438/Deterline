"""storyline --flag-write 候选接线测试（16 号计划包 18）。

resolve_flag_writes（纯函数 fail-closed 拒绝矩阵）+ 块级生成器
（_build_npc_step_block flag 写入行插入/形态白名单/默认字节回归）。

无 UTMT 依赖。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import modify_save as ms  # noqa: E402,F401  （初始化 deterline 包路径）
from deterline import errors  # noqa: E402
from deterline.cmds.npc import _build_npc_step_block  # noqa: E402
from deterline.storyline import StorylineError  # noqa: E402
from deterline.storyline.commands import resolve_flag_writes  # noqa: E402
from deterline.storyline.state import QuestMachine  # noqa: E402
from tests.test_storyline_states import (  # noqa: E402
    FLAG_V2, MAIN_V2, _defn)

# 会话载体夹具：flag 520（空带）+ delivered talk enter code 4
SESSION_CARRIER = MAIN_V2.replace(
    "patch_id: det_t1", "patch_id: det_t1\nflag_id: 520").replace(
    "    require: carrying", "    require: carrying\n    code: 4")


class TestResolveFlagWrites(unittest.TestCase):
    """拒绝矩阵（每臂独立、错误可行动）+ 正例接线点。"""

    def test_session_carrier_resolved(self):
        writes = resolve_flag_writes(_defn(SESSION_CARRIER))
        self.assertEqual(writes, [{"npc": "receiver", "state": "delivered",
                                   "code": 4,
                                   "line": "global.flag[520] = 4;"}])

    def test_requires_states(self):
        with self.assertRaises(StorylineError) as cm:
            resolve_flag_writes(_defn(MAIN_V2.rsplit("states:", 1)[0]))
        self.assertIn("states 块", str(cm.exception))

    def test_requires_flag_id(self):
        with self.assertRaises(StorylineError) as cm:
            resolve_flag_writes(_defn(MAIN_V2))
        self.assertIn("flag_id", str(cm.exception))

    def test_refuses_occupied_flag(self):
        text = SESSION_CARRIER.replace("flag_id: 520", "flag_id: 509")
        with self.assertRaises(StorylineError) as cm:
            resolve_flag_writes(_defn(text))
        self.assertIn("被游戏代码占用", str(cm.exception))

    def test_refuses_flag_persistence(self):
        # persistence=flag → 本基线持久区全占用，拒绝。511 实际先被占用
        # 检查拦截（500-511 全占用 = persistence 臂为纵深防御）——用空
        # 占用 mock 单独钉该臂
        from unittest import mock
        with mock.patch("deterline.storyline.projection.check_flag_occupancy",
                        return_value=[]):
            with self.assertRaises(StorylineError) as cm:
                resolve_flag_writes(_defn(FLAG_V2))
            self.assertIn("无净空持久槽", str(cm.exception))
        # 未 mock 的真实口径：511 被占用 → 占用臂先行拒绝
        with self.assertRaises(StorylineError) as cm:
            resolve_flag_writes(_defn(FLAG_V2))
        self.assertIn("被游戏代码占用", str(cm.exception))

    def test_refuses_choice_npc_coded_enter(self):
        text = SESSION_CARRIER.replace(
            "      answer: yes\n    require: not_started\n",
            "      answer: yes\n    require: not_started\n    code: 1\n", 1)
        with self.assertRaises(StorylineError) as cm:
            resolve_flag_writes(_defn(text))
        self.assertIn("选择 npc", str(cm.exception))
        self.assertIn("requester", str(cm.exception))

    def test_refuses_multiple_coded_talk_enters(self):
        # 同一 talk npc 两个 code enter → 触发点无法按态分派
        text = SESSION_CARRIER.replace(
            "      npc: receiver\n    require: carrying\n    code: 4\n",
            "      npc: receiver\n    require: carrying\n    code: 4\n"
            "  delivered2:\n    enter:\n      npc: receiver\n"
            "    require: delivered\n    code: 5\n")
        with self.assertRaises(StorylineError) as cm:
            resolve_flag_writes(_defn(text))
        self.assertIn("多个 code enter", str(cm.exception))

    def test_refuses_no_writes(self):
        # 有 states/flag 但无任何 code talk enter → 无写入点
        text = MAIN_V2.replace("patch_id: det_t1",
                               "patch_id: det_t1\nflag_id: 520")
        with self.assertRaises(StorylineError) as cm:
            resolve_flag_writes(_defn(text))
        self.assertIn("无可接线写入点", str(cm.exception))

    def test_carrier_value_matches_machine_projection_shape(self):
        # 接线值与模型层轨迹一致：delivered = code 4（单场景交付写）
        m = QuestMachine(_defn(SESSION_CARRIER))
        m.trigger("requester", "yes")
        m.trigger("star", "yes")
        m.trigger("receiver")
        self.assertEqual(m.state, "delivered")
        writes = resolve_flag_writes(_defn(SESSION_CARRIER))
        self.assertEqual(writes[0]["code"], 4)


class TestStepBlockFlagWrite(unittest.TestCase):
    """块级生成器：插入位置（对话框创建后）、形态白名单、默认字节回归。"""

    def test_default_form_unchanged(self):
        # 默认（无 flag 写入行）与既有形态逐字节一致（R-1215 口径回归钉）
        block = _build_npc_step_block(113928, "det_x_receiver", 0, 0, False,
                                      once=False, range_=60, typer=5)
        self.assertEqual(block, '''if (id == 113928 && !instance_exists(obj_dialoguer) && !instance_exists(OBJ_WRITER) && !instance_exists(obj_choicer))
{
    if (distance_to_object(obj_mainchara) < 60)
    {
        global.msc = 0;
        global.typer = 5;
        global.facechoice = 0;
        global.faceemotion = 0;
        global.msg[0] = scr_gettext("det_x_receiver");
        global.msg[1] = "%%%";
        instance_create(0, 0, obj_dialoguer);
    }
}
''')

    def test_flag_write_line_inserted_after_create(self):
        block = _build_npc_step_block(
            113930, "det_x_receiver", 0, 0, False, once=False, range_=60,
            typer=5, flag_write_line="global.flag[520] = 4;")
        self.assertIn(
            '        instance_create(0, 0, obj_dialoguer);\n'
            '            global.flag[520] = 4;\n', block)
        # 写入行在无条件路径（创建后、块内无新增条件）
        self.assertNotIn("if (global.flag", block)

    def test_flag_write_line_with_once(self):
        block = _build_npc_step_block(
            1, "k", 0, 0, False, once=True, range_=50, typer=5,
            flag_write_line="global.flag[513] = 1;")
        self.assertIn("global.flag[513] = 1;", block)
        self.assertIn("instance_destroy();", block)
        # 次序：写旗标 → 自毁（destroy 仍是最后一行）
        self.assertLess(block.index("global.flag[513]"),
                        block.index("instance_destroy();"))

    def test_flag_write_line_shape_whitelist(self):
        for bad in ("global.flag[520] = 4", "flag[520] = 4;",
                    "global.flag[x] = 4;", "global.flag[520] = -4;",
                    "global.flag[520] += 4;", "if (global.flag[520] = 4;"):
            with self.assertRaises(errors.ValidationError) as cm:
                _build_npc_step_block(1, "k", 0, 0, False, typer=5,
                                      flag_write_line=bad)
            self.assertIn("形态不合法", str(cm.exception))

    def test_typer_whitelist_still_enforced(self):
        with self.assertRaises(errors.ValidationError):
            _build_npc_step_block(1, "k", 0, 0, False, typer=7)


if __name__ == "__main__":
    unittest.main()
