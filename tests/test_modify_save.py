"""Unit tests for Deterline's pure-Python logic (no UTMT/Steam required).

Run: python3 -m unittest discover tests
"""

import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import deterline.cmds.code as dcode
import deterline.file0 as dfile0  # O2 步 5：patch 点随域迁移（mock 静默失效防线）
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _o2_patch import dual_patch_utmt  # O2 步 3：双路径 patch

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
    """⚠️ 形态不变量（2026-11-07 游戏内 13 次启动实测确立，见 AUDIT_2026-11-07/域F）：
    只允许"纯扁平触发块"——任何状态条件门控 create 都会在游戏内静默失效。"""

    def test_default_range(self):
        block = ms._build_npc_step_block(100, "obj_hi", 3, 1, False, once=True)
        self.assertIn("distance_to_object(obj_mainchara) < 50", block)
        self.assertIn("if (id == 100 && !instance_exists(obj_dialoguer)"
                      " && !instance_exists(OBJ_WRITER) && !instance_exists(obj_choicer))", block)

    def test_custom_range(self):
        block = ms._build_npc_step_block(100, "obj_hi", 3, 1, False, once=True, range_=160)
        self.assertIn("distance_to_object(obj_mainchara) < 160", block)

    def test_pure_flat_no_state(self):
        """回归测试：块内出现任何状态读写都曾导致游戏内静默死代码。"""
        for once in (True, False):
            block = ms._build_npc_step_block(100, "obj_hi", 0, 0, False, once=once)
            self.assertNotIn("deterline_state", block)
            self.assertNotIn("global.flag[", block)
            self.assertNotIn("friction", block)
            self.assertNotIn("global.interact", block)  # 无状态机时无处复位，禁用锁移动
            self.assertIn("if (id == 100 && !instance_exists(obj_dialoguer)"
                          " && !instance_exists(OBJ_WRITER) && !instance_exists(obj_choicer))", block)

    def test_once_self_destructs(self):
        block = ms._build_npc_step_block(100, "obj_hi", 0, 0, False, once=True)
        self.assertIn("instance_destroy()", block)

    def test_repeat_does_not_destroy(self):
        block = ms._build_npc_step_block(100, "obj_hi", 0, 0, False, once=False)
        self.assertNotIn("instance_destroy()", block)

    def test_contains_dialoguer(self):
        block = ms._build_npc_step_block(100, "obj_hi", 0, 0, False, once=True)
        self.assertIn("instance_create(0, 0, obj_dialoguer)", block)
        self.assertIn('global.msg[0] = scr_gettext("obj_hi")', block)

    def test_no_bare_python_bool(self):
        """GML 里不允许出现 Python 布尔字面量 True/False（大小写敏感）。"""
        for once in (True, False):
            block = ms._build_npc_step_block(100, "obj_hi", 0, 0, False, once=once)
            self.assertNotIn("True", block)
            self.assertNotIn("False", block)


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

    def test_no_state_anywhere(self):
        block = ms._build_npc_choice_block(200, "obj_ask", "obj_yes", "obj_no", 0, 0)
        self.assertIn("if (id == 200 && !instance_exists(obj_dialoguer)"
                      " && !instance_exists(OBJ_WRITER) && !instance_exists(obj_choicer))", block)
        self.assertNotIn("deterline_state", block)
        self.assertNotIn("global.flag[", block)
        self.assertNotIn("global.interact", block)

    def test_single_shot_self_destructs_by_default(self):
        block = ms._build_npc_choice_block(200, "obj_ask", "obj_yes", "obj_no", 0, 0)
        self.assertIn("instance_destroy()", block)

    def test_repeat_keeps_npc_alive(self):
        block = ms._build_npc_choice_block(200, "obj_ask", "obj_yes", "obj_no", 0, 0,
                                           repeat=True)
        self.assertNotIn("instance_destroy()", block)

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


class TestTextdataUpdate(unittest.TestCase):
    def _capture(self, fake_out):
        captured = {}

        def fake_run(csx, game_file, save=True):
            captured["csx"] = csx
            captured["save"] = save
            return fake_out

        return captured, fake_run

    def test_builds_csx_with_existing_key_and_new_value(self):
        captured, fake_run = self._capture(
            "OK: Updated 1 entry(s) for 'obj_darksans1_345'\n")
        with dual_patch_utmt(side_effect=fake_run):
            ms.cmd_textdata_update(Path("game.ios"), "obj_darksans1_345", "* hello there, pal./")
        # 生成的 C# 用 verbatim 字符串：引号加倍
        self.assertIn('@"ds_map_add(global.text_data_en, ""obj_darksans1_345"", ""* hello there, pal./"");"',
                      captured["csx"])
        self.assertIn('new string(\' \', indent)', captured["csx"])
        self.assertTrue(captured["save"])

    def test_missing_key_reports_error(self):
        captured, fake_run = self._capture("ERROR: No entry found for key 'nope' (use add-textentry first)\n")
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            with dual_patch_utmt(side_effect=fake_run):
                ms.cmd_textdata_update(Path("game.ios"), "nope", "* x/")
        self.assertIn("No entry found", buf.getvalue())

    def test_rejects_non_ascii(self):
        with self.assertRaises(ms.ValidationError):
            ms.cmd_textdata_update(Path("game.ios"), "obj_darksans1_345", "* 你好/")

    def test_face_emotion_injected(self):
        captured, fake_run = self._capture("OK: Updated 1 entry(s) for 'k'\n")
        with dual_patch_utmt(side_effect=fake_run):
            ms.cmd_textdata_update(Path("game.ios"), "k", "* hi/", face=3, emotion=1)
        self.assertIn(r'\F3\E1* hi/', captured["csx"])


class TestFile0Fields(unittest.TestCase):
    def test_core_layout_matches_game_source(self):
        # 对照游戏源码 scr_load / scr_saveprocess
        self.assertEqual(ms.FILE0_FIELDS["LOVE"], 0)
        self.assertEqual(ms.FILE0_FIELDS["MAXHP"], 1)      # global.maxhp
        self.assertEqual(ms.FILE0_FIELDS["HP"], 1)         # 别名（游戏不存"当前HP"）
        self.assertEqual(ms.FILE0_FIELDS["MAXEN"], 2)      # global.maxen
        self.assertEqual(ms.FILE0_FIELDS["AT"], 3)
        self.assertEqual(ms.FILE0_FIELDS["WEAPON_AT"], 4)
        self.assertEqual(ms.FILE0_FIELDS["DF"], 5)
        self.assertEqual(ms.FILE0_FIELDS["ARMOR_DF"], 6)
        self.assertEqual(ms.FILE0_FIELDS["SP"], 7)
        self.assertEqual(ms.FILE0_FIELDS["EXP"], 8)
        self.assertEqual(ms.FILE0_FIELDS["GOLD"], 9)
        self.assertEqual(ms.FILE0_FIELDS["KILLS"], 10)

    def test_resolve_file0_keys(self):
        self.assertEqual(ms._resolve_file0_key("MAXHP"), 1)
        self.assertEqual(ms._resolve_file0_key("HP"), 1)
        self.assertEqual(ms._resolve_file0_key("MAXEN"), 2)
        self.assertEqual(ms._resolve_file0_key("SP"), 7)
        self.assertEqual(ms._resolve_file0_key("LOVE"), 0)
        self.assertEqual(ms._resolve_file0_key("Love"), 0)   # 大小写不敏感


class TestDerivedStats(unittest.TestCase):
    """HP/AT/DF 由 LV 推导，file0 值会被游戏重算 —— set-derived 必须改写脚本。"""

    def test_derived_values(self):
        self.assertEqual(ms.derived_stat_value("HP", 1), 20)
        self.assertEqual(ms.derived_stat_value("HP", 5), 36)
        self.assertEqual(ms.derived_stat_value("MAXHP", 5), 36)
        self.assertEqual(ms.derived_stat_value("AT", 5), 18)
        self.assertEqual(ms.derived_stat_value("DF", 5), 11)   # 9 + ceil(5/4)
        self.assertIsNone(ms.derived_stat_value("GOLD", 5))

    def test_patch_formula_but_not_condition(self):
        code = ("global.maxhp = 16 + (global.lv * 4);\n"
                "if (global.hp > (global.maxhp + 15))\n"
                "{\nglobal.hp = global.maxhp + 15;\n}")
        new, n = ms._patch_stat_assignments(code, "maxhp", 50)
        self.assertEqual(n, 1)
        self.assertIn("global.maxhp = 50;", new)
        self.assertIn("if (global.hp > (global.maxhp + 15))", new)

    def test_patch_relocks_existing_literal(self):
        new, n = ms._patch_stat_assignments("global.at = 18;", "at", 99)
        self.assertEqual(n, 1)
        self.assertEqual(new, "global.at = 99;")

    def test_patch_no_match_leaves_code(self):
        code = "global.df = 5;"
        new, n = ms._patch_stat_assignments(code, "at", 99)
        self.assertEqual(n, 0)
        self.assertEqual(new, code)

    def test_set_derived_writes_file0_and_patches_both_scripts(self):
        calls = {"file0": [], "replace": []}
        code_map = {
            "gml_Object_obj_battlecontroller_Create_0": "global.maxhp = 16 + (global.lv * 4);",
            "gml_Script_scr_levelup": "global.maxhp = 16 + (global.lv * 4);",
        }
        with mock.patch.object(dfile0, "cmd_file0_set",
                               lambda sd, k, v, **kw: calls["file0"].append((k, v))), \
             mock.patch.object(dcode, "_get_decompiled_code",
                               lambda gf, name: code_map.get(name)), \
             mock.patch.object(dcode, "cmd_code_replace",
                               lambda gf, name, code: calls["replace"].append((name, code))):
            ms.cmd_set_derived(Path("."), Path("game.ios"), "HP", "50")
        self.assertEqual(calls["file0"], [("MAXHP", "50")])
        self.assertEqual(len(calls["replace"]), 2)
        for _name, code in calls["replace"]:
            self.assertIn("global.maxhp = 50;", code)

    def test_set_derived_rejects_unknown_key(self):
        with self.assertRaises(ms.ValidationError):
            ms.cmd_set_derived(Path("."), Path("game.ios"), "GOLD", "5")

    def test_set_derived_rejects_non_int(self):
        with self.assertRaises(ms.ValidationError):
            ms.cmd_set_derived(Path("."), Path("game.ios"), "HP", "abc")

    def test_set_derived_raises_when_no_scripts_found(self):
        with mock.patch.object(dfile0, "cmd_file0_set", lambda *a, **k: None), \
             mock.patch.object(dcode, "_get_decompiled_code", lambda *a, **k: None):
            with self.assertRaises(RuntimeError):
                ms.cmd_set_derived(Path("."), Path("game.ios"), "HP", "50")


class TestFile0DerivedWarning(unittest.TestCase):
    """直接 set file0 的 HP/AT/DF 时应提示会被 LV 重算覆盖。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.save_dir = Path(self._tmp.name)
        (self.save_dir / "file0").write_text("Ryan\n5 \n36 \n", encoding="utf-8")

    def test_warns_when_value_differs_from_lv(self):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            ms.cmd_file0_set(self.save_dir, "HP", "50")
        msg = buf.getvalue()
        self.assertIn("set-derived", msg)
        # 必须说清"读档后显示设置值，进战斗/升级才重算"，不能误导成"当前显示 36"
        self.assertIn("读档后菜单会显示", msg)
        self.assertIn("进入战斗/升级", msg)

    def test_no_warning_when_value_matches_lv(self):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            ms.cmd_file0_set(self.save_dir, "HP", "36")
        self.assertEqual(buf.getvalue(), "")


class TestIniFile0Sync(unittest.TestCase):
    """ini [General] 的 Love/Kills/Room 只是镜像副本，游戏读 file0 —— cmd_ini_set 必须同步 file0。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.save_dir = Path(self._tmp.name)

    def _write_save(self, n=550):
        (self.save_dir / "undertale.ini").write_text("[General]\n", encoding="utf-8")
        lines = ["Ryan\n"] + ["0 \n"] * n
        (self.save_dir / "file0").write_text("".join(lines), encoding="utf-8")

    def _nums(self):
        _, nums = ms._parse_file0(self.save_dir / "file0")
        return nums

    def test_love_syncs_to_file0(self):
        self._write_save()
        ms.cmd_ini_set(self.save_dir, "General", "Love", "5")
        self.assertEqual(self._nums()[0], 5)   # file0[0] = global.lv
        cp = ms._read_ini(self.save_dir / "undertale.ini")
        self.assertEqual(ms.parse_ini_value(cp.get("General", "Love")), "5")

    def test_kills_syncs_to_file0(self):
        self._write_save()
        ms.cmd_ini_set(self.save_dir, "General", "Kills", "12")
        self.assertEqual(self._nums()[10], 12)

    def test_room_syncs_to_file0_location(self):
        self._write_save()
        ms.cmd_ini_set(self.save_dir, "General", "Room", "70")
        self.assertEqual(self._nums()[546], 70)

    def test_non_general_section_does_not_sync(self):
        self._write_save()
        ms.cmd_ini_set(self.save_dir, "Sans", "Love", "9")
        self.assertEqual(self._nums()[0], 0)   # 非 [General] 不触发 file0 同步


class TestParseLayers(unittest.TestCase):
    def test_comma_list(self):
        self.assertEqual(ms._parse_layers("0,1,2"), [0, 1, 2])

    def test_whitespace_tolerated(self):
        self.assertEqual(ms._parse_layers(" 0 , 1 "), [0, 1])

    def test_empty_is_empty(self):
        self.assertEqual(ms._parse_layers(None), [])
        self.assertEqual(ms._parse_layers(""), [])

    def test_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            ms._parse_layers("8")
        with self.assertRaises(ValueError):
            ms._parse_layers("-1")

    def test_non_int_raises(self):
        with self.assertRaises(ValueError):
            ms._parse_layers("a")


class TestBuildGmlBgCode(unittest.TestCase):
    """gml-bg 必须同时设置 htiled/vtiled，并支持多层与遮挡隐藏。"""

    def test_sets_both_tiling_axes(self):
        gml = ms.build_gml_bg_code("room_x", "bg_blue", [0])
        self.assertIn("background_htiled[0] = true;", gml)
        self.assertIn("background_vtiled[0] = true;", gml)

    def test_vtiled_can_be_disabled(self):
        gml = ms.build_gml_bg_code("room_x", "bg_blue", [0], vtiled=False)
        self.assertIn("background_vtiled[0] = false;", gml)

    def test_hide_above_emits_loop(self):
        gml = ms.build_gml_bg_code("room_x", "bg_blue", [0], hide_above=True)
        self.assertIn("for (var _det_i = 0 + 1; _det_i < 8;", gml)
        self.assertIn("background_visible[_det_i] = false;", gml)

    def test_hide_above_uses_top_slot(self):
        gml = ms.build_gml_bg_code("room_x", "bg_blue", [0, 1], hide_above=True)
        self.assertIn("for (var _det_i = 1 + 1; _det_i < 8;", gml)

    def test_no_hide_above_by_default(self):
        gml = ms.build_gml_bg_code("room_x", "bg_blue", [0])
        self.assertNotIn("_det_i", gml)

    def test_multiple_slots_all_set(self):
        gml = ms.build_gml_bg_code("room_x", "bg_blue", [0, 1])
        for s in (0, 1):
            self.assertIn(f"background_index[{s}] = bg_blue;", gml)

    def test_numeric_asset_used_as_index(self):
        gml = ms.build_gml_bg_code("room_x", "27", [0])
        self.assertIn("background_index[0] = 27;", gml)

    def test_foreground_flag(self):
        gml = ms.build_gml_bg_code("room_x", "bg_blue", [0], foreground=True)
        self.assertIn("background_foreground[0] = true;", gml)

    def test_parallax_speed_applied(self):
        gml = ms.build_gml_bg_code("room_x", "bg_blue", [0], speedx=0.5)
        self.assertIn("view_xview[0] * 0.5", gml)

    def test_guard_flag_includes_asset(self):
        gml = ms.build_gml_bg_code("room_x", "bg_blue", [0])
        self.assertIn("det_bg_room_x_0_bg_blue", gml)

    def test_empty_slots_defaults_to_zero(self):
        gml = ms.build_gml_bg_code("room_x", "bg_blue", [])
        self.assertIn("background_index[0] = bg_blue;", gml)


class TestBuildSetRoomBgStmts(unittest.TestCase):
    """set-room-bg 不得在未显式传 x/y 时移动背景层。"""

    def test_no_props_is_empty(self):
        self.assertEqual(ms.build_set_room_bg_stmts(0), "")

    def test_x_y_omitted_by_default(self):
        stmts = ms.build_set_room_bg_stmts(0, bg_name="bg_x")
        self.assertNotIn(".X =", stmts)
        self.assertNotIn(".Y =", stmts)

    def test_x_y_emitted_when_given(self):
        stmts = ms.build_set_room_bg_stmts(0, x=5, y=6)
        self.assertIn("room.Backgrounds[0].X = 5;", stmts)
        self.assertIn("room.Backgrounds[0].Y = 6;", stmts)

    def test_enable_true_disables_bg_color(self):
        stmts = ms.build_set_room_bg_stmts(0, enable=True)
        self.assertIn("room.DrawBackgroundColor = false;", stmts)
        self.assertIn("room.Backgrounds[0].Enabled = true;", stmts)

    def test_keep_bg_color_suppresses_side_effect(self):
        stmts = ms.build_set_room_bg_stmts(0, enable=True, keep_bg_color=True)
        self.assertNotIn("DrawBackgroundColor", stmts)

    def test_bg_none_clears_definition(self):
        stmts = ms.build_set_room_bg_stmts(0, bg_name="none")
        self.assertIn("room.Backgrounds[0].BackgroundDefinition = null;", stmts)

    def test_bg_name_resolves(self):
        stmts = ms.build_set_room_bg_stmts(0, bg_name="bg_blue_solid")
        self.assertIn('Data.Backgrounds.ByName("bg_blue_solid")', stmts)

    def test_tiling_flags(self):
        stmts = ms.build_set_room_bg_stmts(0, tiled_h=True, tiled_v=False)
        self.assertIn("room.Backgrounds[0].TiledHorizontally = true;", stmts)
        self.assertIn("room.Backgrounds[0].TiledVertically = false;", stmts)


if __name__ == "__main__":
    unittest.main()