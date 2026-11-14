"""O2-step0 A8（研讨会2/01 §2.4）：modify_save.py 兼容面显式测试。

测试套件实际引用的 ms.* 名字钉成显式清单（2026-11-11 O2 步 1：+1 "state"——
旗标单点 canonical 模块句柄，test_o2_step1 的活绑定校验需要；−4 旗标名
（SANDBOX_ACTIVE/SANDBOX_ORIGINAL/COMMIT_ACTIVE/NO_STEAM_SYNC）——步 1 把
test_write_policy 的 patch/断言改指 deterline.state 后无测试再经 ms.* 引用，
活提取集合 diff 如实报告；shim 的旗标 re-export 本体保留，其活绑定由
test_o2_step1.test_flags_reexport_same_object 独立守护。步 6 复核补 room-list（+1=76）；步 7-10 复核后清偿 + 覆盖棘轮冒烟经 ms.* 引用 6 名（cmd_undo/cmd_reset_flags/cmd_create_system_info/cmd_experiment_list/cmd_experiment_restore/FLAG_CUSTOM_START），cjk-check +1=88、doctor +1=89、阶段 1.1/1.2 的 cmd_smoke_test 编排层回归测试 +1=90、backup-index +1=91（2026-11-12）。
拆包后 modify_save.py 变 shim——本测试防止有人在 shim 上"清理"导出
（shim 只能 import 与 re-export，见研讨会2/01 风险 #9）。

维护方式：tests/ 新增 ms.* 引用后把名字加进 COMPAT_SURFACE；
test_live_reference_set_matches 会用提取器做集合 diff，漂移即爆红。
提取注意：正则须带 (?<[A-Za-z]) 否则 "rooms.json" 子串误报出 "json"；
patch.object(ms, "<名字>") 与 getattr(ms, "<名字>") 的字符串形式也算（提取器两种都收）。"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import modify_save as ms

COMPAT_SURFACE = [
    "FILE0_FIELDS",
    "ITEMS",
    "NotFoundError",
    "ValidationError",
    "_build_cjk_pass1_csx",
    "_build_cjk_pass2_csx",
    "_build_cjk_trigger_csx",
    "_build_npc_choice_block",
    "_build_npc_step_block",
    "_csx_escape",
    "_csx_verbatim_escape",
    "_effective_game_file",
    "_gml_escape",
    "_instances_check_snippet",
    "_load_gml_value",
    "_parse_file0",
    "_parse_instance_audit",
    "_parse_layers",
    "_parse_msg",
    "_patch_stat_assignments",
    "_read_ini",
    "_resolve_file0_key",
    "_resolve_write_target",
    "_run_utmt",
    "_validate_ascii_text",
    "build_gml_bg_code",
    "build_set_room_bg_stmts",
    "cjk_wrap_text",
    "cmd_backup_index",
    "cmd_backup_prune",
    "cmd_md5",
    "cmd_sandbox_restore",
    "cmd_batch_textdata",
    "cmd_smoke_test",
    "cmd_undo",
    "cmd_cjk_font",
    "cmd_cjk_check",
    "cmd_cjk_trigger",
    "cmd_doctor",
    "cmd_code_append",
    "cmd_code_find_replace",
    "cmd_code_prepend",
    "cmd_code_replace",
    "cmd_create_battle",
    "cmd_create_bg_asset",
    "cmd_create_door",
    "cmd_create_pit",
    "cmd_create_script",
    "cmd_create_system_info",
    "cmd_experiment_list",
    "cmd_experiment_restore",
    "cmd_file0_set",
    "cmd_gml_bg",
    "cmd_guard_npc_alarm",
    "cmd_experiment_snapshot",
    "cmd_guided_add_dialogue",
    "cmd_handler_extract",
    "cmd_list_backups",
    "cmd_ini_set",
    "cmd_obj_set_sprite",
    "cmd_remove_door",
    "cmd_remove_obj",
    "cmd_remove_tile",
    "cmd_search_vars",
    "cmd_set_derived",
    "cmd_set_room_bg",
    "cmd_set_room_prop",
    "cmd_set_room_solid_bg",
    "cmd_set_room_view",
    "cmd_spawn_obj",
    "cmd_sprite_duplicate",
    "cmd_sprite_replace",
    "cmd_strg_add",
    "cmd_strg_delete",
    "cmd_strg_replace",
    "cmd_strg_search",
    "cmd_strg_set",
    "cmd_quest_init",
    "cmd_quest_status",
    "cmd_reset_all",
    "cmd_reset_flags",
    "cmd_textdata_add",
    "cmd_textdata_delete",
    "cmd_textdata_search",
    "cmd_textdata_update",
    "cmd_verify_instances",
    "cmd_verify_nsid",
    "derived_stat_value",
    "FLAG_CUSTOM_START",
    "parse_ini_value",
    "cmd_room_list",
    "resolve_room",
    "state",
    "validate_flag_index",
]


class TestCompatSurface(unittest.TestCase):
    def test_all_compat_names_exist(self):
        """A8：shim 不得"清理"任何被测试引用的名字。"""
        missing = [n for n in COMPAT_SURFACE if not hasattr(ms, n)]
        self.assertEqual(missing, [], f"modify_save.py 兼容面缺名: {missing}")

    def test_live_reference_set_matches(self):
        """复核席 P1-1/P2-6：清单与测试实际引用集合 diff——漂移即爆红。"""
        import re as _re2
        refs = set()
        pat_dotted = _re2.compile(r'(?<![A-Za-z])ms\.([A-Za-z_][A-Za-z0-9_]*)')
        pat_str = _re2.compile(r'(?:patch\.object|getattr)\(\s*ms,\s*["\']([A-Za-z_][A-Za-z0-9_]*)["\']')
        for f in Path(__file__).resolve().parent.glob("test_*.py"):
            t = f.read_text(encoding="utf-8")
            refs.update(pat_dotted.findall(t))
            refs.update(pat_str.findall(t))
        refs.discard("json")  # "rooms.json" 子串防误报兜底（负向环视已挡大部分）
        listed = set(COMPAT_SURFACE)
        self.assertEqual(refs - listed, set(),
                         f"测试引用了清单外的 ms.* 名字（请加入 COMPAT_SURFACE）: {sorted(refs - listed)}")
        self.assertEqual(listed - refs, set(),
                         f"清单列出了已无人引用的名字（请移除并归因）: {sorted(listed - refs)}")

    def test_surface_count_reported(self):
        # 面扩大是正常演进（新命令），缩小是事故；此断言让增减在 diff 里可见
        self.assertGreaterEqual(len(COMPAT_SURFACE), 91,
                                "兼容面缩水——若为有意清理，先更新本清单并归因")


# 全量导出面冻结（风险席 2026-11-13：91 名只是测试引用子集，shim 活导出
# 215 名中约 121 名无任何守护——一次 shim"清理"可静默删掉它们）。
# 有意变更（新增/删除/改名）必须同步更新本清单并在提交信息归因。
FROZEN_EXPORTS = [
    "ALLOW_CJK",
    "AREA_KILLS_FIELDS",
    "ARMOR_DF",
    "AUTO_SNAPSHOT",
    "BATTLE_CREATE_BASE",
    "BATTLE_CREATE_BRANCH",
    "BATTLE_CREATE_FALLBACK",
    "BATTLE_STEP_CODE",
    "BOSS_FIELDS",
    "BOSS_STATE_DESC",
    "CJK_TYPER_TABLE",
    "COMMIT_ACTIVE",
    "DERIVED_STAT_FORMULAS",
    "DERIVED_STAT_VARS",
    "DERIVED_TARGET_SCRIPTS",
    "DETECTED_PATTERNS",
    "DISTANCE_TRIGGER",
    "DOOR_CREATE_BASE",
    "DOOR_CREATE_BRANCH",
    "DOOR_CREATE_FALLBACK",
    "DOOR_GOTO_BACK_SCRIPT",
    "DOOR_STEP_CODE",
    "DeterlineError",
    "FACE_CHOICES",
    "FILE0_FIELDS",
    "FILE0_ONLY_KEYS",
    "FLAG_CUSTOM_END",
    "FLAG_CUSTOM_START",
    "FLAG_FIELDS",
    "FLAG_INDEX_MAX",
    "INI_TO_FILE0_SYNC",
    "INVENTORY_FIELDS",
    "ITEMS",
    "KNOWN_KEYS",
    "NO_MATCH_EXIT_CODE",
    "NO_STEAM_SYNC",
    "NotFoundError",
    "PIT_CREATE_BASE",
    "PIT_CREATE_BRANCH",
    "PIT_CREATE_FALLBACK",
    "PIT_STEP_CODE",
    "Path",
    "QUEST_STATE_INIT",
    "ROOM_BG_WARNING",
    "SANDBOX_ACTIVE",
    "SANDBOX_ORIGINAL",
    "SANS_EMOTIONS",
    "ValidationError",
    "WEAPON_AT",
    "_ALL_FILE0_FIELDS",
    "_CJK_PASS1_CSX",
    "_CJK_PASS2_CSX",
    "_CasePreservingConfigParser",
    "_DIFF_SNAPSHOT_CSX",
    "_HERE",
    "_append_to_code",
    "_assign_room_bg_layers",
    "_bg_asset_exists",
    "_bool_or_none",
    "_build_cjk_pass1_csx",
    "_build_cjk_pass2_csx",
    "_build_cjk_trigger_csx",
    "_build_npc_choice_block",
    "_build_npc_step_block",
    "_csx_escape",
    "_csx_verbatim_escape",
    "_decompile_to_lines",
    "_dump_structure_signature",
    "_effective_game_file",
    "_enabled_bg_layers",
    "_ensure_var_initialized",
    "_export_sprite_json",
    "_fail_if_no_match",
    "_file0_field_hint",
    "_file0_field_name",
    "_find_create_code",
    "_find_utmt_cli",
    "_get_decompiled_code",
    "_gml_escape",
    "_guard_alarm_for_instance",
    "_inject_face_control",
    "_instances_check_snippet",
    "_load_gml_value",
    "_load_rooms",
    "_md5_file",
    "_parse_file0",
    "_parse_instance_audit",
    "_parse_layers",
    "_parse_msg",
    "_patch_stat_assignments",
    "_prepend_to_code",
    "_print_diff",
    "_query_npc_target",
    "_read_ini",
    "_read_room_size",
    "_replace_code_entry",
    "_replace_step_code",
    "_resolve_file0_key",
    "_resolve_room_csx",
    "_resolve_write_target",
    "_room_id_by_name",
    "_run_utmt",
    "_spawn_obj_internal",
    "_update_rooms_json",
    "_validate_ascii_text",
    "_validate_facechoice",
    "_write_file0",
    "_write_ini",
    "backup_file",
    "build_gml_bg_code",
    "build_set_room_bg_stmts",
    "cjk_wrap_text",
    "cmd_backup_index",
    "cmd_backup_prune",
    "cmd_batch_textdata",
    "cmd_cjk_check",
    "cmd_cjk_font",
    "cmd_cjk_trigger",
    "cmd_code_append",
    "cmd_code_decompile",
    "cmd_code_find_replace",
    "cmd_code_list",
    "cmd_code_prepend",
    "cmd_code_replace",
    "cmd_create_battle",
    "cmd_create_bg_asset",
    "cmd_create_door",
    "cmd_create_pit",
    "cmd_create_room",
    "cmd_create_script",
    "cmd_create_system_info",
    "cmd_diff_snapshots",
    "cmd_doctor",
    "cmd_experiment_list",
    "cmd_experiment_restore",
    "cmd_experiment_snapshot",
    "cmd_file0_find",
    "cmd_file0_get",
    "cmd_file0_list",
    "cmd_file0_set",
    "cmd_gml_bg",
    "cmd_guard_npc_alarm",
    "cmd_guided_add_dialogue",
    "cmd_handler_extract",
    "cmd_ini_get",
    "cmd_ini_list",
    "cmd_ini_set",
    "cmd_list_backups",
    "cmd_list_doors",
    "cmd_list_game_bgs",
    "cmd_md5",
    "cmd_npc_choice",
    "cmd_npc_dialogue",
    "cmd_obj_get",
    "cmd_obj_set_sprite",
    "cmd_quest_init",
    "cmd_quest_status",
    "cmd_remove_door",
    "cmd_remove_obj",
    "cmd_remove_tile",
    "cmd_reset_all",
    "cmd_reset_flags",
    "cmd_room_bg_info",
    "cmd_room_info",
    "cmd_room_list",
    "cmd_room_objects",
    "cmd_sandbox_restore",
    "cmd_search_sctext",
    "cmd_search_vars",
    "cmd_set_derived",
    "cmd_set_room_bg",
    "cmd_set_room_prop",
    "cmd_set_room_solid_bg",
    "cmd_set_room_view",
    "cmd_smoke_test",
    "cmd_spawn_obj",
    "cmd_sprite_colorize",
    "cmd_sprite_dump_all",
    "cmd_sprite_duplicate",
    "cmd_sprite_export",
    "cmd_sprite_list",
    "cmd_sprite_preview",
    "cmd_sprite_replace",
    "cmd_sprite_search",
    "cmd_strg_add",
    "cmd_strg_delete",
    "cmd_strg_get",
    "cmd_strg_list",
    "cmd_strg_replace",
    "cmd_strg_search",
    "cmd_strg_set",
    "cmd_textdata_add",
    "cmd_textdata_delete",
    "cmd_textdata_search",
    "cmd_textdata_update",
    "cmd_texture_export",
    "cmd_texture_list",
    "cmd_texture_replace",
    "cmd_undo",
    "cmd_verify_code",
    "cmd_verify_instances",
    "cmd_verify_nsid",
    "derived_stat_value",
    "find_game_data_file",
    "find_save_dir",
    "format_ini_value",
    "format_room",
    "list_backups",
    "main",
    "normalize_key",
    "parse_ini_value",
    "resolve_room",
    "state",
    "sys",
    "validate_flag_index",
]


class TestFullExportSurface(unittest.TestCase):
    def test_shim_full_export_surface_frozen(self):
        """A8 强化：shim 全量公开导出面（非 dunder）逐名冻结。
        dir() 快照 = 兼容面全集；任何缩减（哪怕未被测试引用）在此爆红。"""
        live = sorted(n for n in dir(ms) if not n.startswith("__"))
        self.assertEqual(
            live, FROZEN_EXPORTS,
            "shim 全量导出面漂移——若为有意变更，更新 FROZEN_EXPORTS 并在提交信息归因；"
            f"差异：+{sorted(set(live) - set(FROZEN_EXPORTS))} "
            f"-{sorted(set(FROZEN_EXPORTS) - set(live))}")

    def test_full_surface_count_reported(self):
        live = [n for n in dir(ms) if not n.startswith("__")]
        self.assertGreaterEqual(len(live), 215,
                                "全量导出面缩水——若为有意清理，先更新清单并归因")


if __name__ == "__main__":
    unittest.main()
