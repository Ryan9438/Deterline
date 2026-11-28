"""storyline v2 定义合同测试（16 号计划包 06/07）。

纯合同层（零 UTMT 依赖）：_read_definition_v2 的 fail-closed 校验、
load_definition 的版本分派（v1 路径兼容）、order 稳定排序合同。
计划编译/图诊断的 UTMT 探针部分见 test_storyline_cli 集成层与真 CLI 验收。
"""

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from deterline.storyline import (  # noqa: E402
    DEFN_SCHEMA_V2,
    StorylineError,
    _read_definition_v2,
    load_definition,
)

MIN_V2 = """schema: deterline.storyline/v2
patch_id: det_zhi_min
cjk: false
rooms:
  only: room_ruins1
npcs:
  greeter:
    room: only
    object: obj_npc_marker
    x: 100
    y: 200
    prompt: "* Hello./%%"
    once: false
order:
  - npc:greeter
"""


class TestV2Contract(unittest.TestCase):

    def test_minimal_v2_parses(self):
        doc = _read_definition_v2(MIN_V2)
        self.assertEqual(doc["schema"], DEFN_SCHEMA_V2)
        self.assertEqual(doc["patch_id"], "det_zhi_min")
        self.assertEqual(doc["rooms"], {"only": "room_ruins1"})
        self.assertFalse(doc["cjk"])
        self.assertEqual(doc["order"], ["npc:greeter"])
        self.assertNotIn("doors", doc)          # 可选缺省
        self.assertNotIn("flag_id", doc)        # 可选缺省

    def test_load_definition_dispatches_v2(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "min.yaml"
            p.write_text(MIN_V2, encoding="utf-8")
            doc = load_definition(p)
        self.assertEqual(doc["_version"], "v2")
        self.assertEqual(doc["_sha256"],
                         hashlib.sha256(MIN_V2.encode("utf-8")).hexdigest())

    def test_v1_still_dispatches_v1(self):
        v1 = """schema: deterline.storyline/v1
patch_id: det_cli_test
room: room_ruins1
flag_id: 505
npc:
  object: obj_npc_marker
  x: 100
  y: 200
  prompt: "* Hi& &         Yes         No      \\C "
  yes_text: "* Yes./%%"
  no_text: "* No./%%"
"""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "v1.yaml"
            p.write_text(v1, encoding="utf-8")
            doc = load_definition(p)
        self.assertEqual(doc["_version"], "v1")
        self.assertEqual(doc["patch_id"], "det_cli_test")

    def test_unknown_field_rejected(self):
        bad = MIN_V2 + "extra: 1\n"
        with self.assertRaises(StorylineError) as cm:
            _read_definition_v2(bad)
        self.assertIn("未知字段", str(cm.exception))
        self.assertIn("extra", str(cm.exception))

    def test_duplicate_key_rejected_with_line(self):
        # yaml_min 层错误 = YamlMinError（ValueError 子类）——与 v1 同口径
        bad = MIN_V2 + "patch_id: det_other\n"
        with self.assertRaises(ValueError) as cm:
            _read_definition_v2(bad)
        self.assertIn("重复键", str(cm.exception))

    def test_missing_order_rejected(self):
        bad = MIN_V2.rsplit("order:", 1)[0]
        with self.assertRaises(StorylineError) as cm:
            _read_definition_v2(bad)
        self.assertIn("缺少必需字段", str(cm.exception))
        self.assertIn("order", str(cm.exception))

    def test_unknown_order_kind_rejected(self):
        bad = MIN_V2.replace("- npc:greeter", "- warp:greeter")
        with self.assertRaises(StorylineError) as cm:
            _read_definition_v2(bad)
        self.assertIn("未知 kind", str(cm.exception))

    def test_unknown_order_ref_rejected(self):
        bad = MIN_V2.replace("- npc:greeter", "- npc:ghost")
        with self.assertRaises(StorylineError) as cm:
            _read_definition_v2(bad)
        self.assertIn("引用不存在", str(cm.exception))

    def test_duplicate_order_ref_rejected(self):
        bad = MIN_V2.replace("order:\n  - npc:greeter",
                             "order:\n  - npc:greeter\n  - npc:greeter")
        with self.assertRaises(StorylineError) as cm:
            _read_definition_v2(bad)
        self.assertIn("重复引用", str(cm.exception))

    def test_entity_missing_from_order_rejected(self):
        bad = MIN_V2.replace(
            "order:\n  - npc:greeter",
            "  ghost:\n    room: only\n    object: obj_npc_marker\n"
            "    x: 1\n    y: 1\n    prompt: \"* Boo./%%\"\n"
            "order:\n  - npc:greeter")
        with self.assertRaises(StorylineError) as cm:
            _read_definition_v2(bad)
        self.assertIn("未出现在 order", str(cm.exception))

    def test_npc_unknown_room_alias_rejected(self):
        bad = MIN_V2.replace("room: only", "room: nowhere")
        with self.assertRaises(StorylineError) as cm:
            _read_definition_v2(bad)
        self.assertIn("引用未知房间别名", str(cm.exception))

    def test_door_unknown_alias_rejected(self):
        bad = MIN_V2 + (
            "doors:\n"
            "  d1:\n"
            "    from: start\n"
            "    to: nowhere\n"
            "    x: 1\n"
            "    y: 1\n"
            "    spawn_x: 1\n"
            "    spawn_y: 1\n"
        )
        with self.assertRaises(StorylineError) as cm:
            _read_definition_v2(bad)
        self.assertIn("必须引用 rooms 别名", str(cm.exception))

    def test_pure_dialog_with_branch_texts_rejected(self):
        bad = MIN_V2.replace('prompt: "* Hello./%%"',
                             'prompt: "* Hello./%%"\n'
                             '    yes_text: "* Yes./%%"\n'
                             '    no_text: "* No./%%"')
        with self.assertRaises(StorylineError) as cm:
            _read_definition_v2(bad)
        self.assertIn("无 \\C 的 prompt", str(cm.exception))

    def test_choice_missing_yes_text_rejected(self):
        bad = MIN_V2.replace('prompt: "* Hello./%%"',
                             'prompt: "* Hello?& &         Yes         No      \\C "')
        with self.assertRaises(StorylineError) as cm:
            _read_definition_v2(bad)
        self.assertIn("yes_text", str(cm.exception))

    def test_quoted_cjk_bool_rejected(self):
        bad = MIN_V2.replace("cjk: false", 'cjk: "false"')
        with self.assertRaises(StorylineError) as cm:
            _read_definition_v2(bad)
        self.assertIn("cjk 必须是布尔", str(cm.exception))

    def test_flag_range_rejected(self):
        bad = MIN_V2 + "flag_id: 12345\n"
        with self.assertRaises(StorylineError) as cm:
            _read_definition_v2(bad)
        self.assertIn("flag_id 必须是 500-999", str(cm.exception))

    def test_once_non_bool_rejected(self):
        bad = MIN_V2.replace("once: false", "once: 1")
        with self.assertRaises(StorylineError) as cm:
            _read_definition_v2(bad)
        self.assertIn("once 必须是布尔", str(cm.exception))

    def test_ascii_contract_without_cjk(self):
        bad = MIN_V2.replace('prompt: "* Hello./%%"',
                             'prompt: "* 你好。/%%"')
        with self.assertRaises(StorylineError) as cm:
            _read_definition_v2(bad)
        self.assertIn("非 ASCII", str(cm.exception))

    def test_three_room_main_definition_parses(self):
        main = (REPO / "samples/zhi_x/defn_v2_main.yaml").read_text(
            encoding="utf-8")
        doc = _read_definition_v2(main)
        self.assertEqual(set(doc["rooms"]),
                         {"start", "pickup", "turn_in"})
        self.assertEqual(len(doc["doors"]), 4)
        self.assertEqual(len(doc["order"]), 7)
        self.assertTrue(doc["cjk"])


if __name__ == "__main__":
    unittest.main()
