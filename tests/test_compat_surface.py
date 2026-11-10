"""O2-step0 A8（研讨会2/01 §2.4）：modify_save.py 兼容面显式测试。

测试套件实际引用的 ms.* 名字钉成显式清单（2026-11-11 O2 步 1：+1 "state"——
旗标单点 canonical 模块句柄，test_o2_step1 的活绑定校验需要；−4 旗标名
（SANDBOX_ACTIVE/SANDBOX_ORIGINAL/COMMIT_ACTIVE/NO_STEAM_SYNC）——步 1 把
test_write_policy 的 patch/断言改指 deterline.state 后无测试再经 ms.* 引用，
活提取集合 diff 如实报告；shim 的旗标 re-export 本体保留，其活绑定由
test_o2_step1.test_flags_reexport_same_object 独立守护。共 76 个）。
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
    "cmd_batch_textdata",
    "cmd_cjk_font",
    "cmd_cjk_trigger",
    "cmd_code_append",
    "cmd_code_find_replace",
    "cmd_code_prepend",
    "cmd_code_replace",
    "cmd_create_battle",
    "cmd_create_bg_asset",
    "cmd_create_door",
    "cmd_create_pit",
    "cmd_create_script",
    "cmd_file0_set",
    "cmd_gml_bg",
    "cmd_guard_npc_alarm",
    "cmd_guided_add_dialogue",
    "cmd_handler_extract",
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
    "cmd_textdata_add",
    "cmd_textdata_delete",
    "cmd_textdata_search",
    "cmd_textdata_update",
    "cmd_verify_instances",
    "cmd_verify_nsid",
    "derived_stat_value",
    "parse_ini_value",
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
        self.assertGreaterEqual(len(COMPAT_SURFACE), 75,
                                "兼容面缩水——若为有意清理，先更新本清单并归因")


if __name__ == "__main__":
    unittest.main()
