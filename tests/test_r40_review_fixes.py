"""R-40 双席复核修复面测试（合同/合成/撤销/闸门反向/回执形状）。

对应两席 findings 的回归钉：doors 类型、id 标识符、合成 states 携带与
单射、defn_sha 顺序无关、闸门反向断言（条件化代码白名单/变量白名单/
逐 op 代码证据）、undo 假 no-op 与陈旧备份择指纹、apply 回执形状、
v1 候选开关拒绝。全部离线（无 UTMT）。
"""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import modify_save as ms  # noqa: E402,F401
from deterline import transactions  # noqa: E402
from deterline.storyline import StorylineError, _read_definition_v2  # noqa: E402
from deterline.storyline import load_definition  # noqa: E402
from deterline.storyline.commands import (  # noqa: E402
    _load_composed, _v2_declared_assertions, cmd_storyline_apply,
    cmd_storyline_build, cmd_storyline_undo)
from deterline.storyline.ownership import compose_definitions  # noqa: E402
from tests.test_storyline_o7_structured import (  # noqa: E402
    PLAN, _good_structured)
from tests.test_storyline_states import MAIN_V2, _defn  # noqa: E402

MAIN = REPO / "samples" / "zhi_x" / "defn_v2_main.yaml"
NOTICE = REPO / "samples" / "zhi_x" / "defn_v2_notice.yaml"


class TestContractFixes(unittest.TestCase):
    def test_doors_non_mapping_clean_reject(self):
        text = ("schema: deterline.storyline/v2\npatch_id: det_t1\n"
                "rooms:\n  start: room_ruins1\n"
                "npcs:\n  n1:\n    room: start\n"
                "    object: obj_npc_marker\n    x: 100\n    y: 200\n"
                "    prompt: \"* Hi.\"\n"
                "doors: 5\norder:\n  - npc:n1\n")
        with self.assertRaises(StorylineError) as cm:
            _read_definition_v2(text)
        self.assertIn("doors 必须是映射", str(cm.exception))

    def test_npc_id_double_underscore_rejected(self):
        text = MAIN_V2.replace("  requester:", "  b__x:")
        with self.assertRaises(StorylineError) as cm:
            _read_definition_v2(text)
        self.assertIn("不含 '__'", str(cm.exception))

    def test_door_id_double_underscore_rejected(self):
        text = MAIN_V2.replace("  to_pickup:", "  to__pickup:")
        with self.assertRaises(StorylineError) as cm:
            _read_definition_v2(text)
        self.assertIn("不含 '__'", str(cm.exception))


class TestComposeFixes(unittest.TestCase):
    def test_states_carried_and_prefixed(self):
        comp = compose_definitions(load_definition(MAIN),
                                   load_definition(NOTICE))
        st = comp["states"]
        self.assertEqual(st["persistence"], "session")
        self.assertIn("det_zhi_x__receiver",
                      [s["enter"]["npc"] for s in st["map"].values()
                       if "enter" in s])

    def test_both_states_refused(self):
        a = load_definition(MAIN)
        b = load_definition(MAIN)  # 两个都含 states（patch_id 不同）
        b = dict(b)
        b["patch_id"] = "det_other"
        b["rooms"] = {"start2": "room_ruins2"}
        b["npcs"] = {"n1": {**b["npcs"]["star"], "room": "start2",
                            "x": 40, "y": 40}}
        b["order"] = ["npc:n1"]
        b["doors"] = {}
        with self.assertRaises(StorylineError) as cm:
            compose_definitions(a, b)
        self.assertIn("双方均声明 states", str(cm.exception))

    def test_defn_sha_input_order_invariant(self):
        with tempfile.TemporaryDirectory() as td:
            a = Path(td) / "a.yaml"
            b = Path(td) / "b.yaml"
            a.write_text(MAIN.read_text(encoding="utf-8"), encoding="utf-8")
            b.write_text(NOTICE.read_text(encoding="utf-8"), encoding="utf-8")
            c1, _a1, _b1 = _load_composed(str(a), str(b))
            c2, _a2, _b2 = _load_composed(str(b), str(a))
            self.assertEqual(c1["_sha256"], c2["_sha256"])
            self.assertEqual(c1["patch_id"], c2["patch_id"])


class TestGateReverse(unittest.TestCase):
    """R-40：闸门反向断言（此前单向——额外资源可通过）。"""

    def setUp(self):
        self.defn = _defn(MAIN_V2)
        self.structured = _good_structured(self.defn)

    def test_door_code_on_doorless_plan_refused(self):
        doorless = dict(PLAN)
        doorless["ops"] = [o for o in PLAN["ops"] if o["op"] != "door"]
        st = self.structured
        # 去掉实例门行，保留代码门条目（模拟"无门计划冒出 door 脚本"）
        st["instances"]["added"] = [r for r in st["instances"]["added"]
                                    if r[2] != "obj_deterline_door"]
        refusals = _v2_declared_assertions(st, self.defn, doorless)
        self.assertTrue(any("CODE added 未声明条目" in r
                            and "deterline_door" in r
                            for r in refusals), refusals)

    def test_alarm_on_non_native_refused(self):
        st = self.structured
        st["code"]["changed"].append("gml_Object_obj_npc_marker_Alarm_0")
        refusals = _v2_declared_assertions(st, self.defn, PLAN)
        self.assertTrue(any("Alarm_0" in r for r in refusals), refusals)

    def test_undeclared_deterline_var_refused(self):
        st = self.structured
        st["vardeterline"]["b"].append("deterline_evil:1:1")
        refusals = _v2_declared_assertions(st, self.defn, PLAN)
        self.assertTrue(any("VAR 未声明变量" in r and "evil" in r
                            for r in refusals), refusals)

    def test_npc_op_without_code_evidence_refused(self):
        st = self.structured
        st["code"]["added"] = [n for n in st["code"]["added"]
                               if not n.startswith(
                                   "gml_Object_obj_npc_marker")]
        st["code"]["changed"] = [n for n in st["code"]["changed"]
                                 if not n.startswith(
                                     "gml_Object_obj_npc_marker")]
        refusals = _v2_declared_assertions(st, self.defn, PLAN)
        self.assertTrue(any("无对象代码证据" in r for r in refusals),
                        refusals)


class TestUndoFixes(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="r40_undo_")
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.game = root / "game.ios"
        self.defn = root / "defn.yaml"
        self.defn.write_text(json.dumps({}), encoding="utf-8")
        # 用真实 v2 定义文件（undo 需要 load_definition）
        self.defn.write_text(
            (REPO / "samples/zhi_x/defn_v2_min.yaml").read_text(
                encoding="utf-8"), encoding="utf-8")
        self.rcpt_dir = (root / ".deterline" / "storyline" / "game.ios"
                         / "det_zhi_min")
        self.rcpt_dir.mkdir(parents=True)
        self.rcpt = self.rcpt_dir / "receipt.json"

    def _fixture(self, target: bytes, backup: bytes | None,
                 status: str = "applied"):
        self.game.write_bytes(target)
        bak = self.game.with_suffix(self.game.suffix + ".bak")
        if backup is not None:
            bak.write_bytes(backup)
        before = transactions.fingerprint(bak) if backup is not None else "0" * 64
        after = transactions.fingerprint(self.game)
        self.rcpt.write_text(json.dumps({
            "schema": "deterline.storyline-apply/v1",
            "patch_id": "det_zhi_min", "defn_sha256": "x",
            "baseline_sha256": before, "before_sha256": before,
            "after_sha256": after, "product_sha256": after,
            "status": status,
        }), encoding="utf-8")
        return before, after

    def test_stale_backup_refused(self):
        # 仅有指纹不匹配的 .bak → 拒绝（防叠加补丁撤销错代）
        self._fixture(b"PATCHED", backup=b"BASE")
        self.game.with_suffix(self.game.suffix + ".bak").write_bytes(
            b"STALE-OTHER-PATCH")
        rc = cmd_storyline_undo(self.game, str(self.defn))
        self.assertEqual(rc, 1)
        self.assertEqual(self.game.read_bytes(), b"PATCHED")

    def test_matching_backup_preferred_over_newer(self):
        # .bak 错（新）+ .bak.<ts> 对（旧）→ 必须选指纹匹配者
        before, _after = self._fixture(b"PATCHED", backup=b"BASE")
        bak = self.game.with_suffix(self.game.suffix + ".bak")
        bak.write_bytes(b"STALE-NEW")
        good = self.game.with_suffix(self.game.suffix + ".bak.20260101_000000")
        good.write_bytes(b"BASE")
        rc = cmd_storyline_undo(self.game, str(self.defn))
        self.assertEqual(rc, 0)
        self.assertEqual(self.game.read_bytes(), b"BASE")

    def test_undone_receipt_with_modified_target_refused(self):
        before, _after = self._fixture(b"PATCHED", backup=b"BASE",
                                       status="undone")
        self.game.write_bytes(b"THIRD-PARTY")
        rc = cmd_storyline_undo(self.game, str(self.defn))
        self.assertEqual(rc, 1)
        self.assertEqual(self.game.read_bytes(), b"THIRD-PARTY")

    def test_crash_window_reconciles_receipt(self):
        # 目标已回前态但回执未记账（status=applied）→ no-op + 补账
        before, _after = self._fixture(b"BASE", backup=b"BASE",
                                       status="applied")
        rc = cmd_storyline_undo(self.game, str(self.defn))
        self.assertEqual(rc, 0)
        rcpt = json.loads(self.rcpt.read_text(encoding="utf-8"))
        self.assertEqual(rcpt["status"], "undone")


class TestReceiptShapeAndV1(unittest.TestCase):
    def test_corrupt_prior_receipt_clean_reject(self):
        # apply 对非对象 receipt.json → 干净拒绝（此前 AttributeError）
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            game = root / "game.ios"
            game.write_bytes(b"GAME")
            defn = root / "d.yaml"
            defn.write_text(
                (REPO / "samples/zhi_x/defn_v2_min.yaml").read_text(
                    encoding="utf-8"), encoding="utf-8")
            rd = root / ".deterline" / "storyline" / "game.ios" / "det_zhi_min"
            rd.mkdir(parents=True)
            (rd / "receipt.json").write_text("[]", encoding="utf-8")
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                rc = cmd_storyline_apply(None, game, str(defn), "ws")
            self.assertEqual(rc, 1)
            self.assertIn("形状不符", buf.getvalue())

    def test_v1_build_with_candidates_refused(self):
        # v1 定义 + --flag-write/--view-track → 显式拒绝（不静默忽略）
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            game = root / "game.ios"
            game.write_bytes(b"GAME")
            defn = root / "d.yaml"
            defn.write_text(
                "schema: deterline.storyline/v1\npatch_id: det_v1t\n"
                "room: room_ruins1\nnpc:\n  object: obj_npc_marker\n"
                "  x: 100\n  y: 200\n  prompt: \"* Hi& &   Yes   No  \\C\"\n"
                "  yes_text: \"* Y./%%\"\n  no_text: \"* N./%%\"\n"
                "flag_id: 512\n",
                encoding="utf-8")
            with mock.patch("deterline.storyline.build_plan",
                            return_value={"tool_version": "t"}):
                for kw in ({"flag_write": True}, {"view_track": True}):
                    buf = io.StringIO()
                    with contextlib.redirect_stderr(buf):
                        rc = cmd_storyline_build(
                            game, str(defn), "ws1", **kw)
                    self.assertEqual(rc, 1)
                    self.assertIn("需要 v2 定义", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
