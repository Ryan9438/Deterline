"""Golden CSX snapshot tests (V4).

Every command that generates a CSX script is pinned to a recorded golden file
(tests/golden/<name>.csx).  If a change to CSX generation is INTENTIONAL,
regenerate with:

    GOLDEN_UPDATE=1 python3 -m unittest tests.test_golden_csx -v

and mention the change in the commit message (双轨机制：区分"意外漂移"与"有意演进"，
见 AUDIT_2026-11-07/01-ROADMAP 验收原则).
"""

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import modify_save as ms

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"


def _capture(fn, *args, **kwargs):
    """Patch _run_utmt to record every generated CSX; returns (list_of_csx, fn_result)."""
    captured = []

    def fake_run(csx_code, game_file, save=True):
        captured.append(csx_code)
        return "VERIFY_NSID:bad=0 fixed=0\nVERIFY_INSTANCES:bad=0 zero=0 dup=0 null=0 nonexist=0 fixed=0"

    with mock.patch.object(ms, "_run_utmt", side_effect=fake_run):
        result = fn(*args, **kwargs)
    return captured, result


def _golden_path(name: str) -> Path:
    return GOLDEN_DIR / f"{name}.csx"


def _check_golden(testcase, name: str, captured):
    text = "\n=== CALL ===\n".join(captured)
    path = _golden_path(name)
    if os.environ.get("GOLDEN_UPDATE") == "1":
        GOLDEN_DIR.mkdir(exist_ok=True)
        path.write_text(text, encoding="utf-8")
    testcase.assertTrue(
        path.exists(), f"golden 缺失: {path}（跑 GOLDEN_UPDATE=1 生成）")
    expected = path.read_text(encoding="utf-8")
    testcase.assertEqual(expected, text,
                         f"CSX 与 golden 不一致: {name}（有意变更则 GOLDEN_UPDATE=1 重录）")


class TestGoldenStrg(unittest.TestCase):
    def test_strg_set(self):
        cap, _ = _capture(ms.cmd_strg_set, Path("/tmp/golden_test/game.ios"), "11432", "* New text/")
        _check_golden(self, "strg_set", cap)

    def test_strg_add(self):
        cap, _ = _capture(ms.cmd_strg_add, Path("/tmp/golden_test/game.ios"), "* New dialogue/%%")
        _check_golden(self, "strg_add", cap)

    def test_strg_delete(self):
        cap, _ = _capture(ms.cmd_strg_delete, Path("/tmp/golden_test/game.ios"), "64000")
        _check_golden(self, "strg_delete", cap)

    def test_strg_search(self):
        cap, _ = _capture(ms.cmd_strg_search, Path("/tmp/golden_test/game.ios"), "Toriel", 30)
        _check_golden(self, "strg_search", cap)


class TestGoldenTextdata(unittest.TestCase):
    def test_textdata_add_plain(self):
        cap, _ = _capture(ms.cmd_textdata_add, Path("/tmp/golden_test/game.ios"),
                          "obj_golden_001", "* Hello golden/%%")
        _check_golden(self, "textdata_add_plain", cap)

    def test_textdata_add_with_face(self):
        cap, _ = _capture(ms.cmd_textdata_add, Path("/tmp/golden_test/game.ios"),
                          "obj_golden_002", "* Hi/%%", face=3, emotion=1)
        _check_golden(self, "textdata_add_face", cap)

    def test_textdata_update(self):
        cap, _ = _capture(ms.cmd_textdata_update, Path("/tmp/golden_test/game.ios"),
                          "obj_golden_001", "* Updated text/%%")
        _check_golden(self, "textdata_update", cap)

    def test_textdata_delete(self):
        cap, _ = _capture(ms.cmd_textdata_delete, Path("/tmp/golden_test/game.ios"),
                          "obj_golden_001")
        _check_golden(self, "textdata_delete", cap)

    def test_textdata_search(self):
        cap, _ = _capture(ms.cmd_textdata_search, Path("/tmp/golden_test/game.ios"),
                          "sans", 30)
        _check_golden(self, "textdata_search", cap)


class TestGoldenCode(unittest.TestCase):
    def test_code_replace(self):
        cap, _ = _capture(ms.cmd_code_replace, Path("/tmp/golden_test/game.ios"),
                          "gml_Script_scr_golden", "return 20;")
        _check_golden(self, "code_replace", cap)

    def test_code_append(self):
        cap, _ = _capture(ms.cmd_code_append, Path("/tmp/golden_test/game.ios"),
                          "gml_Object_obj_golden_Step_0", "// appended")
        _check_golden(self, "code_append", cap)

    def test_code_prepend(self):
        cap, _ = _capture(ms.cmd_code_prepend, Path("/tmp/golden_test/game.ios"),
                          "gml_Object_obj_golden_Step_0", "// prepended")
        _check_golden(self, "code_prepend", cap)

    def test_create_script(self):
        cap, _ = _capture(ms.cmd_create_script, Path("/tmp/golden_test/game.ios"),
                          "gml_Script_goldenFunc", "return 0;")
        _check_golden(self, "create_script", cap)

    def test_search_vars(self):
        cap, _ = _capture(ms.cmd_search_vars, Path("/tmp/golden_test/game.ios"),
                          "global.flag", 30)
        _check_golden(self, "search_vars", cap)


class TestGoldenRoom(unittest.TestCase):
    def test_gml_bg(self):
        cap, _ = _capture(ms.cmd_gml_bg, Path("/tmp/golden_test/game.ios"),
                          "room_golden", "bg_golden", slot=0, speedx=0.5)
        _check_golden(self, "gml_bg", cap)

    def test_set_room_bg(self):
        cap, _ = _capture(ms.cmd_set_room_bg, Path("/tmp/golden_test/game.ios"),
                          "room_golden", index=0, enable=True, bg_name="bg_golden")
        _check_golden(self, "set_room_bg", cap)

    def test_set_room_prop_size_only(self):
        """v2.3.0: --width/--height 不得触碰 Views[0]（形态不变量）。"""
        cap, _ = _capture(ms.cmd_set_room_prop, Path("/tmp/golden_test/game.ios"),
                          "room_golden", width=800, height=480)
        _check_golden(self, "set_room_prop_size", cap)
        for csx in cap:
            self.assertNotIn("Views[0]", csx,
                             "set-room-prop 尺寸变更不得触碰 Views[0]（回归 v2.3.0 前的副作用）")

    def test_set_room_prop_caption(self):
        cap, _ = _capture(ms.cmd_set_room_prop, Path("/tmp/golden_test/game.ios"),
                          "room_golden", caption="Golden Room")
        _check_golden(self, "set_room_prop_caption", cap)

    def test_set_room_view(self):
        cap, _ = _capture(ms.cmd_set_room_view, Path("/tmp/golden_test/game.ios"),
                          "room_golden", index=0, enable=True,
                          view_w=320, view_h=240, port_w=640, port_h=480,
                          follow="obj_mainchara")
        _check_golden(self, "set_room_view", cap)

    def test_remove_tile_all(self):
        cap, _ = _capture(ms.cmd_remove_tile, Path("/tmp/golden_test/game.ios"),
                          "room_golden", None)
        _check_golden(self, "remove_tile_all", cap)

    def test_verify_nsid(self):
        cap, _ = _capture(ms.cmd_verify_nsid, Path("/tmp/golden_test/game.ios"), fix=False)
        _check_golden(self, "verify_nsid", cap)

    def test_verify_instances(self):
        cap, _ = _capture(ms.cmd_verify_instances, Path("/tmp/golden_test/game.ios"), fix=False)
        _check_golden(self, "verify_instances", cap)


class TestGoldenGenerators(unittest.TestCase):
    """生成器函数的精确输出快照（npc 触发块是死代码事故区，钉死形态）。"""

    def test_npc_step_block_repeat(self):
        block = ms._build_npc_step_block(113928, "obj_k", 3, 1, True, once=False, range_=50)
        _check_golden(self, "gen_npc_step_repeat", [block])

    def test_npc_step_block_once(self):
        block = ms._build_npc_step_block(113928, "obj_k", 3, 1, True, once=True, range_=50)
        _check_golden(self, "gen_npc_step_once", [block])

    def test_npc_choice_block(self):
        block = ms._build_npc_choice_block(
            113930, "obj_ask", "obj_yes", "obj_no", 3, 1, range_=160,
            goto_room="70", item_id=48, repeat=False)
        _check_golden(self, "gen_npc_choice", [block])

    def test_npc_choice_block_repeat(self):
        block = ms._build_npc_choice_block(
            113930, "obj_ask", "obj_yes", "obj_no", 3, 1, repeat=True)
        _check_golden(self, "gen_npc_choice_repeat", [block])


class TestGoldenCjkFont(unittest.TestCase):
    """C3b：cjk-font 两段 CSX 模板钉形（work_dir 用固定假路径保证字节稳定）。"""

    def test_cjk_pass1_csx(self):
        _check_golden(self, "cjk_pass1",
                      [ms._build_cjk_pass1_csx("/tmp/golden_cjk_work")])

    def test_cjk_pass2_csx(self):
        _check_golden(self, "cjk_pass2",
                      [ms._build_cjk_pass2_csx("/tmp/golden_cjk_work")])


if __name__ == "__main__":
    unittest.main()
