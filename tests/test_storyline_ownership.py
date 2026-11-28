"""双补丁组合测试（16 号计划包 26/27）。

所有权提取/冲突分类/合成定义纯函数（无 UTMT）+ storyline-compose 命令
（探针 mock 的进程内计划构建）。验收：冲突表分类可读（独立/重名/共享
脚本/同 flag）、调换输入产生同一合成计划、不一致 cjk/双 flag/坐标重叠
拒绝。
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import modify_save as ms  # noqa: E402,F401
from deterline.storyline import StorylineError, load_definition  # noqa: E402
from deterline.storyline.ownership import (  # noqa: E402
    compare_ownership, compose_definitions, extract_ownership)
from deterline.storyline.commands import cmd_storyline_compose  # noqa: E402

MAIN = REPO / "samples" / "zhi_x" / "defn_v2_main.yaml"
NOTICE = REPO / "samples" / "zhi_x" / "defn_v2_notice.yaml"

PROBES = {"room_ruins1": 6, "room_ruins2": 7, "room_ruins4": 9}


def _plan(patch: str, *, flag: int | None = None, obj: str = "obj_npc_marker",
          room: str = "room_ruins1", x: int = 100, y: int = 200) -> dict:
    """合成计划（所有权测试口径的最小形态）。"""
    return {
        "patch_id": patch, "cjk": False,
        "rooms": {"r": {"name": room, "idx": 6}},
        "npcs": {"n1": {"object": obj, "room": "r", "x": x, "y": y,
                        "choice": False}},
        "doors": {},
        "ops": [{"op": "npc", "ref": "n1",
                 "npc": {"room": "r", "object": obj, "x": x, "y": y,
                         "choice": False, "native": False},
                 "prompt": "* hi"}],
        "flag": {"id": flag},
    }


class TestOwnership(unittest.TestCase):

    def test_extract_classes(self):
        own = extract_ownership(_plan("p1", flag=520))
        kinds = {(c["kind"], c["id"]): c["class"] for c in own["claims"]}
        self.assertEqual(kinds[("patch", "p1")], "exclusive")
        self.assertEqual(kinds[("room_inst", "room_ruins1")], "mergeable")
        self.assertEqual(kinds[("object_script",
                                "gml_Object_obj_npc_marker_Step_0")],
                         "shared-script")
        self.assertEqual(kinds[("text", "det_p1_n1")], "exclusive")
        self.assertEqual(kinds[("flag", "520")], "exclusive")
        self.assertEqual(kinds[("code", "gml_Script_textdata_en")],
                         "shared-script")

    def test_compare_independent_same_object_shared(self):
        # 不同 flag、不同文本键、同对象脚本 → 可合并（需合成构建）
        t = compare_ownership(extract_ownership(_plan("p1", flag=520)),
                              extract_ownership(_plan("p2", flag=521)))
        self.assertTrue(t["mergeable"])
        obj_claims = [c for c in t["conflicts"]
                      if c["kind"] == "object_script"]
        self.assertIn("gml_Object_obj_npc_marker_Step_0",
                      [c["id"] for c in obj_claims])
        self.assertTrue(all(c["class"] == "shared-script"
                            for c in t["conflicts"]))
        self.assertIn("合成构建", t["advice"])

    def test_compare_same_flag_exclusive(self):
        t = compare_ownership(extract_ownership(_plan("p1", flag=520)),
                              extract_ownership(_plan("p2", flag=520)))
        self.assertFalse(t["mergeable"])
        self.assertEqual(t["conflicts"][0]["class"], "exclusive")
        self.assertEqual(t["conflicts"][0]["kind"], "flag")

    def test_compare_same_patch_id(self):
        t = compare_ownership(extract_ownership(_plan("p1")),
                              extract_ownership(_plan("p1")))
        self.assertFalse(t["mergeable"])
        self.assertIn("patch_id 相同", t["conflicts"][0]["advice"])

    def test_compare_additive_only(self):
        t = compare_ownership(extract_ownership(_plan("p1", obj="obj_a")),
                              extract_ownership(_plan("p2", obj="obj_b")))
        self.assertTrue(t["mergeable"])
        room = [c for c in t["additive"] if c["kind"] == "room_inst"]
        self.assertEqual(len(room), 1)


class TestCompose(unittest.TestCase):

    def test_composed_ids_prefixed_and_order_canonical(self):
        a = load_definition(MAIN)
        b = load_definition(NOTICE)
        comp = compose_definitions(a, b)
        self.assertEqual(comp["patch_id"], "det_notice+det_zhi_x")
        self.assertTrue(all("__" in k for k in comp["npcs"]))
        self.assertTrue(comp["order"][0].startswith("npc:det_notice__"))
        swap = compose_definitions(b, a)
        # 调换输入 → 同一合成定义（含 order 全序）
        self.assertEqual(comp, swap)

    def test_cjk_mismatch_refused(self):
        a = load_definition(MAIN)
        b = load_definition(NOTICE)
        b = dict(b)
        b["cjk"] = False
        with self.assertRaises(StorylineError) as cm:
            compose_definitions(a, b)
        self.assertIn("cjk 期望不一致", str(cm.exception))

    def test_double_flag_refused(self):
        a = dict(load_definition(MAIN))
        b = dict(load_definition(NOTICE))
        b["flag_id"] = 521
        with self.assertRaises(StorylineError) as cm:
            compose_definitions(a, b)
        self.assertIn("双方均声明 flag", str(cm.exception))

    def test_position_overlap_refused(self):
        a = load_definition(MAIN)
        b = load_definition(NOTICE)
        b = dict(b)
        b["npcs"] = {"notice": dict(b["npcs"]["notice"], x=100, y=200)}
        # main 的 requester 在 room_ruins1 (100,200)；notice 同房同坐标
        with self.assertRaises(StorylineError) as cm:
            compose_definitions(a, b)
        self.assertIn("相同坐标", str(cm.exception))

    def test_v1_refused(self):
        a = {"_version": "v1", "patch_id": "p1"}
        with self.assertRaises(StorylineError):
            compose_definitions(a, load_definition(NOTICE))


class TestComposeCommand(unittest.TestCase):
    """storyline-compose（mock 探针进程内；JSON 与退出码一致）。"""

    def _run(self, a: Path, b: Path, json_out: bool) -> int:
        with mock.patch(
                "deterline.cmds.template_common.idx_room_lookup",
                side_effect=lambda gf, name: PROBES.get(name, -1)), \
             mock.patch("deterline.storyline._room_name_by_idx",
                        side_effect=lambda gf, idx: next(
                            (k for k, v in PROBES.items() if v == idx),
                            None)), \
             mock.patch("deterline.storyline._room_match_count",
                        return_value=(1, 0)), \
             mock.patch("deterline.storyline._room_size_by_idx",
                        side_effect=lambda gf, idx: {
                            6: (320, 480), 7: (320, 240),
                            9: (320, 240)}.get(idx)), \
             mock.patch("deterline.cmds.npc._query_npc_target",
                        return_value={"obj": "obj_npc_marker",
                                      "native": False, "step_code": None,
                                      "alarm_code": None}), \
             mock.patch("deterline.cmds.npc._find_create_code",
                        return_value=None):
            return cmd_storyline_compose(
                Path("/tmp/ghost.ios"), str(a), str(b), json_out=json_out)

    def test_compose_preview_ok(self):
        self.assertEqual(self._run(MAIN, NOTICE, json_out=False), 0)

    def test_compose_json_error_shell_and_exit(self):
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad.yaml"
            bad.write_text(MAIN.read_text(encoding="utf-8").replace(
                "cjk: true", "cjk: false"), encoding="utf-8")
            self.assertEqual(self._run(bad, NOTICE, json_out=True), 1)


class TestPackCommand(unittest.TestCase):
    """包 30：可重建包命令（mock 探针；JSON 含定义原文与期望指纹）。"""

    def test_pack_emits_definitions_and_expected(self):
        import contextlib
        import io
        from deterline.storyline.commands import cmd_storyline_pack
        buf = io.StringIO()
        with mock.patch(
                "deterline.cmds.template_common.idx_room_lookup",
                side_effect=lambda gf, name: PROBES.get(name, -1)), \
             mock.patch("deterline.storyline._room_name_by_idx",
                        side_effect=lambda gf, idx: next(
                            (k for k, v in PROBES.items() if v == idx),
                            None)), \
             mock.patch("deterline.storyline._room_match_count",
                        return_value=(1, 0)), \
             mock.patch("deterline.storyline._room_size_by_idx",
                        side_effect=lambda gf, idx: {
                            6: (320, 480), 7: (320, 240),
                            9: (320, 240)}.get(idx)), \
             mock.patch("deterline.cmds.npc._query_npc_target",
                        return_value={"obj": "obj_npc_marker",
                                      "native": False, "step_code": None,
                                      "alarm_code": None}), \
             mock.patch("deterline.cmds.npc._find_create_code",
                        return_value=None), \
             contextlib.redirect_stdout(buf):
            rc = cmd_storyline_pack(
                Path("/tmp/ghost.ios"), str(MAIN), str(NOTICE))
        self.assertEqual(rc, 0)
        import json as _json
        pack = _json.loads(buf.getvalue())
        self.assertEqual(pack["schema"], "deterline.storyline-pack/v1")
        self.assertIn("text", pack["definitions"]["a"])
        self.assertIn("schema: deterline.storyline/v2",
                      pack["definitions"]["a"]["text"])
        self.assertEqual(pack["expected"]["merged_patch_id"],
                         "det_notice+det_zhi_x")
        self.assertEqual(len(pack["expected"]["semantic_sha256"]), 64)
        self.assertEqual(len(pack["expected"]["ops"]), 8)
        # 包内不含游戏数据（只允许定义文本与元数据键）
        self.assertEqual(set(pack), {
            "schema", "tool_version", "tool_requirements", "composition",
            "definitions", "expected"})


if __name__ == "__main__":
    unittest.main()
