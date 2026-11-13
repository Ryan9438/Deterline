#!/usr/bin/env python3
"""Deterline — UNDERTALE Save Editor（O2 拆包后兼容 shim）。

本文件**只许 import 与 re-export**（A8 兼容面反向锁死；tests/test_o2_step1
 purity 断言）。全部实现位于 deterline/ 包：deterline.cli.main 为入口，
scripts/deterline/{errors,config,state,paths,utmt,rooms_data,inifile,file0}
为脊柱层，scripts/deterline/cmds/* 为命令域。
运行入口不变：python3 scripts/modify_save.py ...（与 run.py 子进程转发）。
"""

__version__ = "2.5.6"

import sys
from pathlib import Path

# 包引导（复核 P1-1）：-I/-P/-m 调用形态保持
_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from deterline import state  # noqa: E402,F401 (兼容面: state 模块句柄)
from deterline.errors import DeterlineError, ValidationError, NotFoundError  # noqa: E402,F401
from deterline.config import (FLAG_INDEX_MAX, FLAG_CUSTOM_START, FLAG_CUSTOM_END,  # noqa: E402,F401
                              FACE_CHOICES, SANS_EMOTIONS, DISTANCE_TRIGGER,
                              QUEST_STATE_INIT, ROOM_BG_WARNING)
from deterline.state import (SANDBOX_ACTIVE, SANDBOX_ORIGINAL, COMMIT_ACTIVE,  # noqa: E402,F401
                             NO_STEAM_SYNC, AUTO_SNAPSHOT, ALLOW_CJK)
from deterline.paths import (find_save_dir, find_game_data_file, backup_file,  # noqa: E402,F401
                             list_backups)
from deterline.rooms_data import (_load_rooms, _update_rooms_json, resolve_room,  # noqa: E402,F401
                                  format_room)
from deterline.inifile import (format_ini_value, parse_ini_value, KNOWN_KEYS,  # noqa: E402,F401
                               normalize_key, _CasePreservingConfigParser, _read_ini,
                               _write_ini, cmd_ini_list, cmd_ini_get, cmd_ini_set,
                               INI_TO_FILE0_SYNC, FILE0_ONLY_KEYS)
from deterline.file0 import (FILE0_FIELDS, DERIVED_STAT_FORMULAS, DERIVED_STAT_VARS,  # noqa: E402,F401
                             derived_stat_value, INVENTORY_FIELDS, BOSS_FIELDS,
                             BOSS_STATE_DESC, AREA_KILLS_FIELDS, FLAG_FIELDS,
                             _ALL_FILE0_FIELDS, ITEMS, WEAPON_AT, ARMOR_DF,
                             _file0_field_name, _file0_field_hint, _parse_file0,
                             _write_file0, _resolve_file0_key, cmd_file0_list,
                             cmd_file0_get, cmd_file0_find, cmd_file0_set)
from deterline.utmt import (_md5_file, _find_utmt_cli, _csx_escape,  # noqa: E402,F401
                            validate_flag_index, _validate_ascii_text,
                            _csx_verbatim_escape, _effective_game_file,
                            _resolve_write_target, _run_utmt, _bool_or_none,
                            _parse_msg, _fail_if_no_match, NO_MATCH_EXIT_CODE,
                            _room_id_by_name, _instances_check_snippet)
from deterline.cmds.save_cmds import (cmd_undo, cmd_list_backups, cmd_reset_flags,  # noqa: E402,F401
                                      cmd_reset_all, cmd_create_system_info,
                                      cmd_experiment_snapshot, cmd_experiment_list,
                                      cmd_experiment_restore)
from deterline.cmds.dialogue import (cmd_strg_list, cmd_strg_get, cmd_strg_set,  # noqa: E402,F401
                                     cmd_strg_add, cmd_strg_delete, cmd_strg_replace,
                                     cmd_strg_search, cmd_textdata_search,
                                     _validate_facechoice, _inject_face_control,
                                     cmd_textdata_add, cmd_guided_add_dialogue,
                                     cmd_textdata_delete, cmd_textdata_update,
                                     cmd_search_sctext, cmd_quest_init,
                                     cmd_quest_status, cmd_batch_textdata)
from deterline.cmds.code import (cmd_code_list, cmd_code_decompile,  # noqa: E402,F401
                                 _decompile_to_lines, _get_decompiled_code,
                                 _print_diff, cmd_code_replace,
                                 cmd_code_find_replace, _load_gml_value,
                                 cmd_code_append, cmd_code_prepend,
                                 DERIVED_TARGET_SCRIPTS, _patch_stat_assignments,
                                 cmd_set_derived, cmd_search_vars,
                                 cmd_create_script, DETECTED_PATTERNS,
                                 cmd_handler_extract, _prepend_to_code,
                                 _append_to_code, _replace_step_code,
                                 _replace_code_entry)
from deterline.cmds.room import (_resolve_room_csx, _parse_layers, build_gml_bg_code,  # noqa: E402,F401
                                 cmd_gml_bg, cmd_remove_tile, cmd_room_objects,
                                 _spawn_obj_internal, cmd_spawn_obj, cmd_remove_obj,
                                 cmd_room_info, cmd_create_room,
                                 build_set_room_bg_stmts, cmd_set_room_bg,
                                 cmd_set_room_prop, cmd_set_room_view,
                                 cmd_list_game_bgs, cmd_create_bg_asset,
                                 _read_room_size, _bg_asset_exists,
                                 _enabled_bg_layers, _assign_room_bg_layers,
                                 cmd_set_room_solid_bg, cmd_room_bg_info,
                                 cmd_room_list)
from deterline.cmds.npc import (_query_npc_target, _build_npc_step_block,  # noqa: E402,F401
                                _build_npc_choice_block, _guard_alarm_for_instance,
                                _find_create_code, _ensure_var_initialized,
                                _parse_instance_audit, cmd_verify_nsid,
                                cmd_verify_instances, cmd_npc_dialogue,
                                cmd_npc_choice, cmd_guard_npc_alarm)
from deterline.cmds.door import (DOOR_GOTO_BACK_SCRIPT, DOOR_CREATE_BASE,  # noqa: E402,F401
                                 DOOR_CREATE_BRANCH, DOOR_CREATE_FALLBACK,
                                 DOOR_STEP_CODE, cmd_create_door,
                                 PIT_CREATE_BASE, PIT_CREATE_BRANCH,
                                 PIT_CREATE_FALLBACK, PIT_STEP_CODE,
                                 cmd_create_pit, BATTLE_CREATE_BASE,
                                 BATTLE_CREATE_BRANCH, BATTLE_CREATE_FALLBACK,
                                 BATTLE_STEP_CODE, cmd_create_battle,
                                 cmd_list_doors, cmd_remove_door)
from deterline.cmds.sprite import (cmd_sprite_list, cmd_sprite_search,  # noqa: E402,F401
                                   cmd_obj_get, cmd_obj_set_sprite,
                                   cmd_texture_list, _export_sprite_json,
                                   cmd_sprite_export, cmd_sprite_replace,
                                   cmd_sprite_duplicate, cmd_sprite_preview,
                                   cmd_sprite_colorize, cmd_texture_export,
                                   cmd_texture_replace, cmd_sprite_dump_all)
from deterline.cmds.verify import (_DIFF_SNAPSHOT_CSX, cmd_smoke_test,  # noqa: E402,F401
                                   _dump_structure_signature,
                                   cmd_diff_snapshots, cmd_verify_code)
from deterline.cmds.cjk import (CJK_TYPER_TABLE, _CJK_PASS1_CSX,  # noqa: E402,F401
                                _CJK_PASS2_CSX, _build_cjk_pass1_csx,
                                _build_cjk_pass2_csx, cmd_cjk_font,
                                cjk_wrap_text, _gml_escape, _csx_escape,
                                _build_cjk_trigger_csx, cmd_cjk_trigger,
                                cmd_cjk_check)
from deterline.cmds.doctor import cmd_doctor  # noqa: E402,F401
from deterline.cmds.save_cmds import (cmd_backup_index,  # noqa: E402,F401
                                      cmd_backup_prune, cmd_md5,
                                      cmd_sandbox_restore)
from deterline.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
