"""包 21：O7 结构化逐对象断言测试（计数相同而对象不同的识别矩阵）。

_v2_declared_assertions 是纯函数（结构化 dict → 拒绝清单）——合成
baseline 镜像样例产物形态（依据 /tmp/dl16w1 真回执 o7 字段），对
实例换名/代码换名/字符串篡改/房间增量错位/font 缺失逐臂钉拒绝与
字段指向。无 UTMT 依赖。
"""

import hashlib
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import modify_save as ms  # noqa: E402,F401
from deterline.storyline.commands import (  # noqa: E402
    _categories_from_structured, _v2_declared_assertions)
from tests.test_storyline_states import MAIN_V2, _defn  # noqa: E402


def _sig(text: str) -> list:
    raw = text.encode("utf-8")
    return [len(raw), hashlib.sha1(raw).hexdigest()]


PLAN = {
    "doors": {
        "to_pickup": {"from": {"name": "room_ruins1"},
                      "to": {"name": "room_ruins2"},
                      "x": 300, "y": 120, "spawn_x": 40, "spawn_y": 120},
        "to_turn_in": {"from": {"name": "room_ruins2"},
                       "to": {"name": "room_ruins4"},
                       "x": 300, "y": 120, "spawn_x": 40, "spawn_y": 120},
    },
    "rooms": {"start": {"name": "room_ruins1"},
              "pickup": {"name": "room_ruins2"},
              "turn_in": {"name": "room_ruins4"}},
    "npcs": {"requester": {"object": "obj_npc_marker", "room": "start",
                           "x": 100, "y": 200},
             "star": {"object": "obj_npc_marker", "room": "pickup",
                      "x": 160, "y": 150},
             "receiver": {"object": "obj_npc_marker", "room": "turn_in",
                          "x": 160, "y": 150}},
    "ops": [
        {"op": "npc", "ref": "requester",
         "npc": {"room": "start", "object": "obj_npc_marker",
                 "x": 100, "y": 200}},
        {"op": "door", "ref": "to_pickup",
         "door": {"from": {"name": "room_ruins1"},
                  "to": {"name": "room_ruins2"},
                  "x": 300, "y": 120, "spawn_x": 40, "spawn_y": 120}},
        {"op": "npc", "ref": "star",
         "npc": {"room": "pickup", "object": "obj_npc_marker",
                 "x": 160, "y": 150}},
        {"op": "door", "ref": "to_turn_in",
         "door": {"from": {"name": "room_ruins2"},
                  "to": {"name": "room_ruins4"},
                  "x": 300, "y": 120, "spawn_x": 40, "spawn_y": 120}},
        {"op": "npc", "ref": "receiver",
         "npc": {"room": "turn_in", "object": "obj_npc_marker",
                 "x": 160, "y": 150}},
    ],
}


def _good_structured(defn: dict) -> dict:
    """真实构建形态的合成镜像（fw_d 回执口径：STR 35 / INST 7 / code 5+3）。"""
    npcs = defn["npcs"]
    strings = []
    for ref, spec in npcs.items():
        if "\\C" in spec["prompt"]:
            for sfx in ("_choice", "_yes", "_no"):
                key = f"det_{defn['patch_id']}_{ref}{sfx}"
                strings.append(["add", _sig(key)])
            strings.append(["add", _sig(spec["prompt"])])
            strings.append(["add", _sig(spec["yes_text"])])
            strings.append(["add", _sig(spec["no_text"])])
        else:
            key = f"det_{defn['patch_id']}_{ref}"
            strings.append(["add", _sig(key)])
            strings.append(["add", _sig(spec["prompt"])])
    # 模板内部串（计数补齐用；断言只做成员检查）
    for i in range(20):
        strings.append(["add", _sig(f"internal_{i}")])
    instances = [[
        "room_ruins1", 113928, "obj_npc_marker", 100, 200],
        ["room_ruins1", 113931, "obj_deterline_door", 300, 120],
        ["room_ruins2", 113930, "obj_npc_marker", 160, 150],
        ["room_ruins2", 113933, "obj_deterline_door", 300, 120],
        ["room_ruins4", 113932, "obj_npc_marker", 160, 150],
    ]
    return {
        "schema": "deterline.o7-diff/v1",
        "counts": {"STRGCOUNT": {"a": 1000, "b": 1025, "delta": 25},
                   "CODECOUNT": {"a": 6272, "b": 6277, "delta": 5},
                   "LASTOBJ": {"a": 7, "b": 12, "delta": 5},
                   "VARS": {"a": 64024, "b": 64037, "delta": 13}},
        "rooms": {
            "removed": [], "added": [],
            "changed": {"room_ruins1": {"a": ["320x480", "inst=3", "tiles=1", "bg="],
                                        "b": ["320x480", "inst=5", "tiles=1", "bg="]},
                        "room_ruins2": {"a": ["320x240", "inst=2", "tiles=1", "bg="],
                                        "b": ["320x240", "inst=4", "tiles=1", "bg="]},
                        "room_ruins4": {"a": ["320x240", "inst=2", "tiles=1", "bg="],
                                        "b": ["320x240", "inst=3", "tiles=1", "bg="]}},
            "inst_delta": {"room_ruins1": 2, "room_ruins2": 2,
                           "room_ruins4": 1},
        },
        "vardeterline": {"a": [], "b": ["deterline_state:1:1"]},
        "strings": {"ops": strings},
        "instances": {"added": instances, "removed": [], "moved": []},
        "code": {"added": ["gml_Object_obj_deterline_door_Create_0",
                           "gml_Object_obj_deterline_door_Step_0",
                           "gml_Object_obj_npc_marker_Create_0",
                           "gml_Object_obj_npc_marker_Step_0",
                           "gml_Script_deterline_door_back"],
                 "changed": ["gml_Script_textdata_en"],
                 "removed": []},
        "fonts": {"changed": [], "added": [], "removed": []},
    }


class TestDeclaredAssertions(unittest.TestCase):
    def setUp(self):
        self.defn = _defn(MAIN_V2)
        self.structured = _good_structured(self.defn)

    def test_good_baseline_passes(self):
        self.assertEqual(
            _v2_declared_assertions(self.structured, self.defn, PLAN), [])

    def test_same_count_different_instance_object_identified(self):
        # 类别计数不变（INST add 仍 5），一个实例对象被换名 → 逐项点名
        self.structured["instances"]["added"][1][2] = "obj_evil"
        refusals = _v2_declared_assertions(self.structured, self.defn, PLAN)
        self.assertTrue(any("INST 未声明新增" in r and "obj_evil" in r
                            for r in refusals), refusals)
        self.assertTrue(any("INST 声明实例缺失" in r for r in refusals))

    def test_same_count_different_code_entry_identified(self):
        # 替换一个新增代码条目名（计数不变）→ 未声明条目点名
        self.structured["code"]["added"].append("gml_Object_obj_evil_Step_0")
        self.structured["code"]["added"].remove("gml_Script_deterline_door_back")
        refusals = _v2_declared_assertions(self.structured, self.defn, PLAN)
        self.assertTrue(any("CODE added 未声明条目" in r and "obj_evil" in r
                            for r in refusals), refusals)

    def test_declared_string_tampered(self):
        # 一个声明字符串的 sha 被换（内容不同长度同）→ 声明签名缺失点名
        _, sha = _sig("det_det_t1_requester_choice")
        for entry in self.structured["strings"]["ops"]:
            if entry[1][1] == sha:
                entry[1][1] = "0" * 40
                break
        refusals = _v2_declared_assertions(self.structured, self.defn, PLAN)
        self.assertTrue(any("STR 声明签名缺失" in r
                            and "requester_choice" in r
                            for r in refusals), refusals)

    def test_instance_moved_refused(self):
        # R-40（双席 A M23 存活变异）：INST moved 非空必须拒绝
        self.structured["instances"]["moved"].append(
            ["room_ruins1", 113928, "obj_npc_marker", 100, 200,
             "(100,200)→(120,220)"])
        refusals = _v2_declared_assertions(self.structured, self.defn, PLAN)
        self.assertTrue(any("INST moved 非空" in r for r in refusals),
                        refusals)

    def test_room_inst_delta_mismatch_named(self):
        self.structured["rooms"]["inst_delta"]["room_ruins2"] = 3
        refusals = _v2_declared_assertions(self.structured, self.defn, PLAN)
        self.assertTrue(any("ROOM inst room_ruins2" in r for r in refusals))

    def test_room_size_change_refused(self):
        pair = self.structured["rooms"]["changed"]["room_ruins1"]
        pair["b"][0] = "640x480"
        refusals = _v2_declared_assertions(self.structured, self.defn, PLAN)
        self.assertTrue(any("ROOM 变化: room_ruins1" in r for r in refusals))

    def test_font_change_in_ascii_build_refused(self):
        self.structured["fonts"]["changed"].append("fnt_ja_maintext")
        refusals = _v2_declared_assertions(self.structured, self.defn, PLAN)
        self.assertTrue(any("FONT 非声明构建不得变化" in r for r in refusals))

    def test_code_removed_refused(self):
        self.structured["code"]["removed"].append("gml_Script_textdata_en")
        refusals = _v2_declared_assertions(self.structured, self.defn, PLAN)
        self.assertTrue(any("CODE removed 非空" in r for r in refusals))


class TestCorrelateOps(unittest.TestCase):
    """包 22：逐 op 产物对应证据（一对一匹配 + 缺失拒绝）。"""

    def _evidence(self):
        return [
            {"op": "npc", "ref": "requester", "room": "room_ruins1",
             "object": "obj_npc_marker", "text_keys": ["k"]},
            {"op": "door", "ref": "to_pickup"},
            {"op": "npc", "ref": "star", "room": "room_ruins2",
             "object": "obj_npc_marker", "text_keys": ["k"]},
            {"op": "door", "ref": "to_turn_in"},
            {"op": "npc", "ref": "receiver", "room": "room_ruins4",
             "object": "obj_npc_marker", "text_keys": ["k"]},
        ]

    def test_correlates_all_ops(self):
        from deterline.storyline.commands import _correlate_ops
        defn = _defn(MAIN_V2)
        out = _correlate_ops(PLAN, self._evidence(),
                             _good_structured(defn), defn)
        self.assertEqual(len(out), 5)
        ids = [ev["o7_instance"]["instance_id"] for ev in out]
        self.assertEqual(len(set(ids)), 5)  # 一对一，无重复占用
        npc_ev = out[0]
        self.assertEqual(npc_ev["o7_instance"]["room"], "room_ruins1")
        self.assertEqual(npc_ev["o7_instance"]["object"], "obj_npc_marker")
        self.assertIn("gml_Object_obj_npc_marker_Step_0", npc_ev["o7_code"])
        door_ev = out[1]
        self.assertEqual(door_ev["o7_instance"]["object"],
                         "obj_deterline_door")
        self.assertIn("gml_Script_deterline_door_back", door_ev["o7_code"])

    def test_missing_correspondence_refused(self):
        from deterline.storyline.commands import _correlate_ops
        defn = _defn(MAIN_V2)
        st = _good_structured(defn)
        st["instances"]["added"] = [r for r in st["instances"]["added"]
                                    if r[0] != "room_ruins4"]
        from deterline.storyline import StorylineError
        with self.assertRaises(StorylineError) as cm:
            _correlate_ops(PLAN, self._evidence(), st, defn)
        self.assertIn("对应证据缺失", str(cm.exception))
        self.assertIn("receiver", str(cm.exception))

    def test_duplicate_same_key_gets_distinct_rows(self):
        from deterline.storyline.commands import _correlate_ops
        defn = _defn(MAIN_V2)
        st = _good_structured(defn)
        # 同一 (room,obj,x,y) 两行（两 op 同坐标的构造）——逐 op 各占一行
        st["instances"]["added"].append(
            ["room_ruins1", 113999, "obj_npc_marker", 100, 200])
        ev = self._evidence() + [{"op": "npc", "ref": "requester",
                                  "room": "room_ruins1",
                                  "object": "obj_npc_marker",
                                  "text_keys": ["k2"]}]
        out = _correlate_ops(PLAN, ev, st, defn)
        last = out[-1]["o7_instance"]["instance_id"]
        self.assertEqual(last, 113999)  # 第二个 requester 占第二行
        first = out[0]["o7_instance"]["instance_id"]
        self.assertEqual(first, 113928)


class TestReceiptMetaValidation(unittest.TestCase):
    """包 22：回执元数据版本/关联字段校验（apply 写前拒绝）。"""

    def _rcpt(self):
        return {"schema": "deterline.storyline-build/v2",
                "patch_id": "det_t1", "defn_sha256": "x",
                "baseline_sha256": "y", "product": "/p",
                "product_sha256": "z", "tool_version": "2.6.0"}

    def test_v2_receipt_passes(self):
        from deterline.storyline.commands import _validate_build_receipt_meta
        defn = _defn(MAIN_V2)
        defn["_version"] = "v2"
        _validate_build_receipt_meta(self._rcpt(), defn)  # 不抛

    def test_schema_version_mismatch(self):
        from deterline.storyline.commands import _validate_build_receipt_meta
        from deterline.storyline import StorylineError
        defn = _defn(MAIN_V2)
        defn["_version"] = "v2"
        rcpt = self._rcpt()
        rcpt["schema"] = "deterline.storyline-build/v1"
        with self.assertRaises(StorylineError) as cm:
            _validate_build_receipt_meta(rcpt, defn)
        self.assertIn("版本不匹配", str(cm.exception))

    def test_unknown_schema_and_missing_fields(self):
        from deterline.storyline.commands import _validate_build_receipt_meta
        from deterline.storyline import StorylineError
        defn = _defn(MAIN_V2)
        defn["_version"] = "v2"
        rcpt = self._rcpt()
        rcpt["schema"] = "deterline.storyline-build/v9"
        with self.assertRaises(StorylineError):
            _validate_build_receipt_meta(rcpt, defn)
        rcpt = self._rcpt()
        del rcpt["product_sha256"]
        with self.assertRaises(StorylineError) as cm:
            _validate_build_receipt_meta(rcpt, defn)
        self.assertIn("缺关联字段", str(cm.exception))

    def test_patch_id_mismatch(self):
        from deterline.storyline.commands import _validate_build_receipt_meta
        from deterline.storyline import StorylineError
        defn = _defn(MAIN_V2)
        defn["_version"] = "v2"
        rcpt = self._rcpt()
        rcpt["patch_id"] = "det_other"
        with self.assertRaises(StorylineError) as cm:
            _validate_build_receipt_meta(rcpt, defn)
        self.assertIn("patch_id 不符", str(cm.exception))


class TestCategoriesFromStructured(unittest.TestCase):
    def test_legacy_shapes_roundtrip(self):
        defn = _defn(MAIN_V2)
        st = _good_structured(defn)
        parsed = _categories_from_structured(st)
        self.assertEqual(parsed["counts"]["STR total"], 25)
        self.assertEqual(parsed["counts"]["INST add"], 5)
        self.assertEqual(parsed["counts"]["CODEF changed"], 1)
        self.assertEqual(parsed["str_ops"],
                         [op for op, _e in st["strings"]["ops"]])
        self.assertEqual(parsed["struct"]["room_inst"],
                         {"room_ruins1": 2, "room_ruins2": 2,
                          "room_ruins4": 1})
        self.assertEqual(parsed["struct"]["code_added"],
                         st["code"]["added"])
        self.assertIsNone(parsed["struct"]["vardeterline"] if False else None)
        # vardeterline 两侧不等 → 元组形态
        self.assertEqual(parsed["struct"]["vardeterline"],
                         ([], ["deterline_state:1:1"]))


if __name__ == "__main__":
    unittest.main()
