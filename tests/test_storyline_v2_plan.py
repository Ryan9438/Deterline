"""storyline v2 计划编译/语义指纹/图诊断测试（16 号计划包 08/09，
R-0610 P2-2 清偿：编译层自动化钉）。

探针全部 mock（进程内，无 UTMT 依赖）：idx_room_lookup / _room_name_by_idx /
_room_match_count / npc._query_npc_target / npc._find_create_code。
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import modify_save as ms  # noqa: E402,F401  （初始化 deterline 包路径）
from deterline.storyline import build_plan_v2, load_definition  # noqa: E402

MAIN_V2 = """schema: deterline.storyline/v2
patch_id: det_t1
cjk: false
rooms:
  start: room_ruins1
  pickup: room_ruins2
  turn_in: room_ruins4
npcs:
  requester:
    room: start
    object: obj_npc_marker
    x: 100
    y: 200
    prompt: "* Hi& &         Yes         No      \\C "
    yes_text: "* Yes./%%"
    no_text: "* No./%%"
    once: false
  star:
    room: pickup
    object: obj_npc_marker
    x: 160
    y: 150
    prompt: "* Star./%%"
    once: false
doors:
  to_pickup:
    from: start
    to: pickup
    x: 300
    y: 120
    spawn_x: 40
    spawn_y: 120
order:
  - npc:requester
  - door:to_pickup
  - npc:star
"""

MAIN_V2_CONTENT_EDIT = MAIN_V2.replace("y: 150", "y: 151")

PROBES = {
    "room_ruins1": 6,
    "room_ruins2": 7,
    "room_ruins4": 9,
}


def _make_plan(text: str, tmp: str):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "d.yaml"
        p.write_text(text, encoding="utf-8")
        defn = load_definition(p)
        game_file = Path(tmp) / "game.ios"
        with mock.patch("deterline.cmds.template_common.idx_room_lookup",
                        side_effect=lambda gf, name: PROBES.get(name, -1)), \
             mock.patch("deterline.storyline._room_name_by_idx",
                        side_effect=lambda gf, idx: next(
                            (k for k, v in PROBES.items() if v == idx), None)), \
             mock.patch("deterline.storyline._room_match_count",
                        return_value=(1, 0)), \
             mock.patch("deterline.cmds.npc._query_npc_target",
                        return_value={"obj": "obj_npc_marker",
                                      "native": False, "step_code": None,
                                      "alarm_code": None}), \
             mock.patch("deterline.cmds.npc._find_create_code",
                        return_value=None):
            return build_plan_v2(defn, game_file)


class TestV2PlanCompile(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="c1_plan_")
        self.addCleanup(self._tmp.cleanup)

    def test_ops_compile_and_rooms_resolved(self):
        plan = _make_plan(MAIN_V2, self._tmp.name)
        self.assertEqual(plan["schema"], "deterline.storyline-plan/v2")
        self.assertEqual([r["name"] for r in plan["rooms"].values()],
                         ["room_ruins1", "room_ruins2", "room_ruins4"])
        self.assertEqual([o["op"] for o in plan["ops"]],
                         ["npc", "door", "npc"])
        self.assertEqual(plan["ops"][0]["npc"]["choice"], True)
        self.assertEqual(plan["ops"][2]["npc"]["choice"], False)

    def test_semantic_fingerprint_stable_across_reorder(self):
        # 等价重排版：rooms 映射键序重排（内容逐字不变）→ 同一指纹
        reordered = MAIN_V2.replace(
            "rooms:\n  start: room_ruins1\n  pickup: room_ruins2\n"
            "  turn_in: room_ruins4\n",
            "rooms:\n  turn_in: room_ruins4\n  start: room_ruins1\n"
            "  pickup: room_ruins2\n")
        p1 = _make_plan(MAIN_V2, self._tmp.name)
        p2 = _make_plan(reordered, self._tmp.name)
        self.assertEqual(p1["semantic_sha256"], p2["semantic_sha256"])

    def test_semantic_fingerprint_changes_with_content(self):
        p1 = _make_plan(MAIN_V2, self._tmp.name)
        p2 = _make_plan(MAIN_V2_CONTENT_EDIT, self._tmp.name)
        self.assertNotEqual(p1["semantic_sha256"], p2["semantic_sha256"])

    def test_unreachable_rooms_diagnosed(self):
        nodoors = MAIN_V2.rsplit("doors:", 1)[0] + "order:\n" + \
            "\n".join(l for l in MAIN_V2.splitlines()
                      if l.strip().startswith("- npc:"))
        plan = _make_plan(nodoors, self._tmp.name)
        joined = "\n".join(plan["diagnostics"])
        self.assertIn("不可达的房间", joined)
        self.assertIn("pickup", joined)

    def test_dead_end_room_diagnosed(self):
        # 删反向能力：turn_in 无出向门 → 死路诊断（start 豁免）
        no_out = MAIN_V2  # 主定义本身 turn_in 无出向门
        plan = _make_plan(no_out, self._tmp.name)
        joined = "\n".join(plan["diagnostics"])
        self.assertIn("无出向门（死路）的房间", joined)
        self.assertIn("turn_in", joined)

    def test_rooms_alias_must_be_identifier(self):
        # R-0610 P3-3：数字形键 "1" 不得作引用别名（标识符合同）
        bad = MAIN_V2.replace("  start: room_ruins1", "  1: room_ruins1", 1)
        with self.assertRaises(Exception) as cm:
            _make_plan(bad, self._tmp.name)
        self.assertIn("别名必须是标识符", str(cm.exception))
