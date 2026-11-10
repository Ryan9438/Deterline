"""O2-step0 A8（研讨会2/01 §2.4）：modify_save.py 兼容面显式测试。

测试套件实际引用的 ms.* 名字（2026-11-10 全量提取，73 个）钉成显式清单。
拆包后 modify_save.py 变 shim——本测试防止有人在 shim 上"清理"导出
（shim 只能 import 与 re-export，见研讨会2/01 风险 #9）。
维护方式：tests/ 中新增 ms.* 引用后，把名字加进 COMPAT_SURFACE。

清单来源：grep -rhoE "ms\\.[A-Za-z_][A-Za-z0-9_]*" tests/*.py | sort -u
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import modify_save as ms

COMPAT_SURFACE = [
    "FILE0_FIELDS",
    "ITEMS",
    "NotFoundError",
    "SANDBOX_ACTIVE",
    "SANDBOX_ORIGINAL",
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
    "_validate_ascii_text",
    "build_gml_bg_code",
    "build_set_room_bg_stmts",
    "cjk_wrap_text",
    "cmd_batch_textdata",
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
    "validate_flag_index",
]


class TestCompatSurface(unittest.TestCase):
    def test_all_compat_names_exist(self):
        """A8：shim 不得"清理"任何被测试引用的名字。"""
        missing = [n for n in COMPAT_SURFACE if not hasattr(ms, n)]
        self.assertEqual(missing, [], f"modify_save.py 兼容面缺名: {missing}")

    def test_surface_count_reported(self):
        # 面扩大是正常演进（新命令），缩小是事故；此断言让增减在 diff 里可见
        self.assertGreaterEqual(len(COMPAT_SURFACE), 73,
                                "兼容面缩水——若为有意清理，先更新本清单并归因")


if __name__ == "__main__":
    unittest.main()
