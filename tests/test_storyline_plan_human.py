"""storyline-plan v2 人读/JSON 互证测试（16 号计划包 32）。

同一输入两种输出逐项互证：房间/NPC/门/执行序/状态机/指纹/诊断/未验证
清单在 human 输出的每一行都能回读为 JSON 字段（可读输出不是另一套）。
探针全 mock（进程内）。
"""

import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import modify_save as ms  # noqa: E402,F401
from deterline.storyline.commands import cmd_storyline_plan  # noqa: E402

MAIN = REPO / "samples" / "zhi_x" / "defn_v2_main.yaml"
PROBES = {"room_ruins1": 6, "room_ruins2": 7, "room_ruins4": 9}


def _probe_patches():
    return [
        mock.patch("deterline.cmds.template_common.idx_room_lookup",
                   side_effect=lambda gf, name: PROBES.get(name, -1)),
        mock.patch("deterline.storyline._room_name_by_idx",
                   side_effect=lambda gf, idx: next(
                       (k for k, v in PROBES.items() if v == idx), None)),
        mock.patch("deterline.storyline._room_match_count",
                   return_value=(1, 0)),
        mock.patch("deterline.storyline._room_size_by_idx",
                   side_effect=lambda gf, idx: {
                       6: (320, 480), 7: (320, 240), 9: (320, 240)}.get(idx)),
        mock.patch("deterline.cmds.npc._query_npc_target",
                   return_value={"obj": "obj_npc_marker", "native": False,
                                 "step_code": None, "alarm_code": None}),
        mock.patch("deterline.cmds.npc._find_create_code",
                   return_value=None),
    ]


def _run(json_out: bool) -> tuple[int, str]:
    buf = io.StringIO()
    patches = _probe_patches()
    with contextlib.ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        with contextlib.redirect_stdout(buf):
            rc = cmd_storyline_plan(Path("/tmp/ghost.ios"), str(MAIN),
                                    json_out=json_out)
    return rc, buf.getvalue()


class TestPlanHumanJsonInterlock(unittest.TestCase):

    def setUp(self):
        rc_h, self.human = _run(json_out=False)
        rc_j, raw = _run(json_out=True)
        self.rc = (rc_h, rc_j)
        self.plan = json.loads(raw)

    def test_both_modes_exit_zero(self):
        self.assertEqual(self.rc, (0, 0))
        self.assertEqual(self.plan["schema"], "deterline.storyline-plan/v2")

    def _find(self, needle: str) -> str:
        for line in self.human.splitlines():
            if needle in line:
                return line
        self.fail(f"human 输出缺行: {needle}\n---\n{self.human}")

    def test_rooms_interlock(self):
        for alias, r in self.plan["rooms"].items():
            line = self._find(f"房间 {alias}:")
            self.assertIn(r["name"], line)
            self.assertIn(f"idx {r['idx']}", line)

    def test_npcs_interlock(self):
        for oid, n in self.plan["npcs"].items():
            line = self._find(f"NPC {oid}:")
            self.assertIn(n["object"], line)
            self.assertIn(f"@({n['x']},{n['y']})", line)
            self.assertIn(f"in {n['room']}", line)
            self.assertIn("choice" if n["choice"] else "talk", line)
            self.assertIn(f"once={n['once']}", line)

    def test_doors_interlock(self):
        for oid, d in self.plan["doors"].items():
            line = self._find(f"门 {oid}:")
            self.assertIn(d["from"]["name"], line)
            self.assertIn(d["to"]["name"], line)
            self.assertIn(f"door@({d['x']},{d['y']})", line)
            self.assertIn(f"spawn@({d['spawn_x']},{d['spawn_y']})", line)

    def test_ops_order_interlock(self):
        block = self.human.split("执行序:", 1)[1].split("语义指纹", 1)[0]
        human_ops = [l.strip().removeprefix("- ") for l in block.splitlines()
                     if l.strip().startswith("- ")]
        self.assertEqual(human_ops,
                         [f"{o['op']}:{o['ref']}" for o in self.plan["ops"]])

    def test_states_interlock(self):
        st = self.plan["states"]
        head = self._find("状态机:")
        self.assertIn(st["initial"], head)
        self.assertIn(st["persistence"], head)
        for s in st["declared"]:
            line = self._find(f"    {s['id']}")
            if "enter" in s:
                self.assertIn(f"npc={s['enter']['npc']}", line)
            if "require" in s:
                self.assertIn(f"require={s['require']}", line)
            if "code" in s:
                self.assertIn(f"code={s['code']}", line)

    def test_fingerprint_and_diagnostics_interlock(self):
        self.assertIn(self.plan["semantic_sha256"][:16], self.human)
        for d in self.plan["diagnostics"]:
            self.assertIn(d, self.human)
        for u in self.plan["unverified"]:
            self.assertIn(u, self.human)


if __name__ == "__main__":
    unittest.main()
