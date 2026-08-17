"""Unit tests for Deterline's pure-Python logic (no UTMT/Steam required).

Run: python3 -m unittest discover tests
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import modify_save as ms


class TestCsxEscape(unittest.TestCase):
    def test_escape_roundtrip(self):
        for s in ["plain", "with\"quote", "back\\slash", "line\nbreak",
                  "tab\there", "mix\\\"\n\r\t"]:
            self.assertEqual(ms._csx_escape(s), s
                             .replace("\\", "\\\\")
                             .replace("\"", "\\\"")
                             .replace("\n", "\\n")
                             .replace("\r", "\\r")
                             .replace("\t", "\\t"))

    def test_verbatim_escape_doubles_quotes_only(self):
        self.assertEqual(ms._csx_verbatim_escape('a"b'), 'a""b')
        self.assertEqual(ms._csx_verbatim_escape("no_quotes"), "no_quotes")
        self.assertEqual(ms._csx_verbatim_escape('say "hi"'), 'say ""hi""')


class TestParseMsg(unittest.TestCase):
    def test_filters_noise(self):
        out = ("Trying to load Data.win...\n"
               "[MESSAGE]: keep me\n"
               "OK: done\n"
               "\n"
               "ERROR: bad\n")
        lines = ms._parse_msg(out)
        self.assertEqual(lines, ["OK: done", "ERROR: bad"])


class TestValidateAscii(unittest.TestCase):
    def test_ascii_ok(self):
        ms._validate_ascii_text("* Hello/%%")  # should not raise

    def test_chinese_rejected(self):
        with self.assertRaises(ms.ValidationError):
            ms._validate_ascii_text("* 你好/%%")

    def test_mixed_rejected(self):
        with self.assertRaises(ms.ValidationError):
            ms._validate_ascii_text("* hi 世界/%%")


class TestValidateFlagIndex(unittest.TestCase):
    def test_valid_range(self):
        ms.validate_flag_index(0)
        ms.validate_flag_index(511)

    def test_out_of_range_warns(self):
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            ms.validate_flag_index(512)
        self.assertIn("警告", buf.getvalue())


class TestResolveRoom(unittest.TestCase):
    def test_numeric_passthrough(self):
        self.assertEqual(ms.resolve_room("134"), "134")

    def test_chinese_name(self):
        self.assertEqual(ms.resolve_room("雪镇 - 船夫(妇)"), "70")

    def test_partial_unique_match(self):
        self.assertEqual(ms.resolve_room("雪镇 - 船夫"), "70")

    def test_multiple_match_raises(self):
        with self.assertRaises(ms.NotFoundError):
            ms.resolve_room("船夫")  # 雪镇 + 热域 两个船夫(妇)

    def test_no_match_raises(self):
        with self.assertRaises(ms.NotFoundError):
            ms.resolve_room("不存在的房间xyz")


class TestBuildNpcStepBlock(unittest.TestCase):
    def test_default_range(self):
        block = ms._build_npc_step_block(100, "obj_hi", 3, 1, False, once=True)
        self.assertIn("if (dist < 50)", block)
        self.assertIn("if (id == 100)", block)

    def test_custom_range(self):
        block = ms._build_npc_step_block(100, "obj_hi", 3, 1, False, once=True, range_=160)
        self.assertIn("if (dist < 160)", block)

    def test_once_has_no_rearm(self):
        block = ms._build_npc_step_block(100, "obj_hi", 0, 0, False, once=True)
        self.assertNotIn(">= 60", block)

    def test_repeatable_has_rearm(self):
        block = ms._build_npc_step_block(100, "obj_hi", 0, 0, False, once=False)
        self.assertIn("deterline_state == 2 && distance_to_object(obj_mainchara) >= 60", block)

    def test_contains_dialoguer(self):
        block = ms._build_npc_step_block(100, "obj_hi", 0, 0, False, once=True)
        self.assertIn("instance_create(0, 0, obj_dialoguer)", block)
        self.assertIn('global.msg[0] = scr_gettext("obj_hi")', block)


class TestBuildNpcChoiceBlock(unittest.TestCase):
    def test_branches_replace_msg(self):
        block = ms._build_npc_choice_block(200, "obj_ask", "obj_yes", "obj_no", 3, 1)
        # YES branch must set msg[0] to yes text (non-\C)
        self.assertIn('global.msg[0] = scr_gettext("obj_yes")', block)
        # NO branch must set msg[0] to no text (non-\C)
        self.assertIn('global.msg[0] = scr_gettext("obj_no")', block)
        self.assertIn('global.msg[0] = scr_gettext("obj_ask")', block)

    def test_goto_and_item(self):
        block = ms._build_npc_choice_block(200, "obj_ask", "obj_yes", "obj_no",
                                           3, 1, goto_room="70", item_id=48)
        self.assertIn("room_goto(70)", block)
        self.assertIn("script_execute(scr_itemget, 48)", block)

    def test_no_yes_text_no_goto(self):
        block = ms._build_npc_choice_block(200, "obj_ask", None, "obj_no", 0, 0)
        self.assertNotIn("global.msg[0] = scr_gettext(\"obj_yes\")", block)
        self.assertNotIn("room_goto", block)
        self.assertNotIn("scr_itemget", block)

    def test_single_trigger_default(self):
        block = ms._build_npc_choice_block(200, "obj_ask", "obj_yes", "obj_no", 0, 0)
        self.assertNotIn(">= 60", block)

    def test_repeat(self):
        block = ms._build_npc_choice_block(200, "obj_ask", "obj_yes", "obj_no", 0, 0,
                                           repeat=True)
        self.assertIn("deterline_state == 2 && distance_to_object(obj_mainchara) >= 60", block)

    def test_choice_uses_msc_negative(self):
        block = ms._build_npc_choice_block(200, "obj_ask", "obj_yes", "obj_no", 0, 0)
        self.assertIn("global.msc = -1", block)
        self.assertIn("global.choice = -1", block)


class TestLoadGmlValue(unittest.TestCase):
    def test_inline_value(self):
        self.assertEqual(ms._load_gml_value("x = 1;", False), "x = 1;")

    def test_file_value(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "code.gml"
            p.write_text("x = 2;", encoding="utf-8")
            self.assertEqual(ms._load_gml_value(str(p), True), "x = 2;")

    def test_missing_file_raises(self):
        with self.assertRaises(ms.NotFoundError):
            ms._load_gml_value("/nonexistent/file.gml", True)


class TestItemsDict(unittest.TestCase):
    def test_covers_known_items(self):
        self.assertEqual(ms.ITEMS[0], "(空)")
        self.assertEqual(ms.ITEMS[48], "牛仔帽")


class TestInstancesCheckSnippet(unittest.TestCase):
    def test_returns_csharp_snippet(self):
        s = ms._instances_check_snippet()
        # References the in-scope `room` variable and only reports (no writes).
        self.assertIn("foreach (var _chkG in room.GameObjects)", s)
        self.assertIn("_chkZero", s)
        self.assertIn("_chkDup", s)
        self.assertIn("WARN_INSTANCES:", s)
        # Must never mutate (no write patterns: no LastObj bump, no reassignment).
        self.assertNotIn("Data.GeneralInfo", s)
        self.assertNotIn("nextId", s)
        self.assertNotIn("LastObj", s)
        self.assertNotIn("= nextId", s)


class TestParseInstanceAudit(unittest.TestCase):
    def test_clean_output(self):
        out = ("VERIFY_INSTANCES:bad=0 zero=0 dup=0 null=0 nonexist=0 fixed=0\n")
        info = ms._parse_instance_audit(out)
        self.assertEqual(info["bad"], 0)
        self.assertEqual(info["fixed"], 0)
        self.assertEqual(info["bad_lines"], [])

    def test_parses_bad_lines_and_counts(self):
        out = (
            "BAD_INSTANCE: room='room_tundra_dangerbridge' obj=obj_solidwide "
            "id=0 x=0 y=160 zero=True dup=False null=False nonexist=False\n"
            "BAD_INSTANCE: room='r2' obj=obj_solidsmall id=7 x=1 y=2 "
            "zero=False dup=True null=False nonexist=False\n"
            "VERIFY_INSTANCES:bad=2 zero=1 dup=1 null=0 nonexist=0 fixed=0\n"
        )
        info = ms._parse_instance_audit(out)
        self.assertEqual(info["bad"], 2)
        self.assertEqual(info["zero"], 1)
        self.assertEqual(info["dup"], 1)
        self.assertEqual(info["fixed"], 0)
        self.assertEqual(len(info["bad_lines"]), 2)
        self.assertIn("obj=obj_solidwide", info["bad_lines"][0])

    def test_parses_warn(self):
        out = "WARN_INSTANCES:zero=0 dup=1 (room=r1)\n"
        info = ms._parse_instance_audit(out)
        self.assertEqual(info["warn"], "zero=0 dup=1 (room=r1)")

    def test_no_verify_line_returns_none(self):
        info = ms._parse_instance_audit("some other output\n")
        self.assertIsNone(info["bad"])


if __name__ == "__main__":
    unittest.main()