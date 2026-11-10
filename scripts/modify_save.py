#!/usr/bin/env python3
"""Deterline — UNDERTALE Save Editor (modify undertale.ini and file0).

使用提示:
  - 每次实验前用 experiment-snapshot 创建命名快照
  - 实验会永久修改 game.ios，后续实验继承所有前置修改
"""

__version__ = "2.3.0"

import argparse
import configparser
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# BG generator (P4-2) — optional, for create-bg-asset with --generate
try:
    from scripts.bg_generator import generate_gradient, generate_stripes, generate_checkerboard, generate_dotted, generate_starfield
    _HAS_BG_GENERATOR = True
except ImportError:
    _HAS_BG_GENERATOR = False

# 包引导（O2 步 1，复核 P1-1）：deterline 与本文件同层（scripts/）。
# `python3 scripts/modify_save.py` 的 sys.path[0] 天然是本目录，但 -I / -P /
# `python3 -m scripts.modify_save` 等调用形态不保证——显式自举保持父版
# 全部调用形态可用（复核席实测父版三形态 exit 0）。
_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# ============================================================
# O2 拆包（研讨会2/01 §2.2 步 1）：叶子域迁入 deterline/ 包
# （errors/config/state/paths）；本文件保留命令实现与 dispatch，
# 并 re-export 兼容面（tests 的 ms.* 引用与 patch 点，A8）。
# 旗标读写纪律：一律 state.X 模块属性形式（test_o2_step1 AST 扫描强制）。
# ============================================================
from deterline import state
from deterline.errors import DeterlineError, ValidationError, NotFoundError  # noqa: F401 (兼容 re-export)
from deterline.config import (FLAG_INDEX_MAX, FLAG_CUSTOM_START, FLAG_CUSTOM_END,  # noqa: F401
                              FACE_CHOICES, SANS_EMOTIONS, DISTANCE_TRIGGER,
                              QUEST_STATE_INIT, ROOM_BG_WARNING)

# ============================================================
# Sandbox mode（旗标已迁 deterline/state.py 步 1，_md5_file 已迁 utmt.py 步 3）
# ============================================================

# 兼容 re-export（hasattr 兼容面，A8）：可变旗标的**行为读写**不走这里的
# 快照绑定，一律 state.X —— 否则 state 侧写入与本副本读数静默分叉
# （stale-read 陷阱；test_o2_step1 以 AST 扫描强制）。
from deterline.state import (SANDBOX_ACTIVE, SANDBOX_ORIGINAL, COMMIT_ACTIVE,  # noqa: F401
                             NO_STEAM_SYNC, AUTO_SNAPSHOT, ALLOW_CJK)


# ============================================================
# Path Detection（已迁 deterline/paths.py，O2 步 1；此处 re-export 兼容面）
# ============================================================

from deterline.paths import (find_save_dir, find_game_data_file,  # noqa: F401
                             backup_file, list_backups)


# ============================================================
# INI / rooms.json / file0（已迁 deterline/{rooms_data,inifile,file0}.py，O2 步 2）
# 此处 re-export 兼容面：函数与只读表可安全导入时绑定。ROOMS 例外
# （_load_rooms 会重绑定 rooms_data.ROOMS）——不 re-export，读者必须走
# rooms_data.ROOMS 模块属性（stale-dict 陷阱，与 state 旗标同源）。
# ============================================================
from deterline import rooms_data
from deterline.rooms_data import (_load_rooms, _update_rooms_json, resolve_room,  # noqa: F401
                                  format_room)
from deterline.inifile import (format_ini_value, parse_ini_value, KNOWN_KEYS,  # noqa: F401
                               normalize_key, _CasePreservingConfigParser, _read_ini,
                               _write_ini, cmd_ini_list, cmd_ini_get, cmd_ini_set,
                               INI_TO_FILE0_SYNC, FILE0_ONLY_KEYS)
from deterline.file0 import (FILE0_FIELDS, DERIVED_STAT_FORMULAS, DERIVED_STAT_VARS,  # noqa: F401
                             derived_stat_value, INVENTORY_FIELDS, BOSS_FIELDS,
                             BOSS_STATE_DESC, AREA_KILLS_FIELDS, FLAG_FIELDS,
                             _ALL_FILE0_FIELDS, ITEMS, WEAPON_AT, ARMOR_DF,
                             _file0_field_name, _file0_field_hint, _parse_file0,
                             _write_file0, _resolve_file0_key, cmd_file0_list,
                             cmd_file0_get, cmd_file0_find, cmd_file0_set)

# ============================================================
# UTMT 脊柱（已迁 deterline/utmt.py，O2 步 3；含步 2 推迟项 _room_id_by_name）
# 测试 patch 点：ms._run_utmt 与 deterline.utmt._run_utmt 双挂（tests/_o2_patch.py）
# ============================================================
from deterline.utmt import (_md5_file, _find_utmt_cli, _csx_escape,  # noqa: F401
                            validate_flag_index, _validate_ascii_text,
                            _csx_verbatim_escape, _effective_game_file,
                            _resolve_write_target, _run_utmt, _bool_or_none,
                            _parse_msg, _fail_if_no_match, NO_MATCH_EXIT_CODE,
                            _room_id_by_name)
# ============================================================
# save_cmds（undo/list-backups/reset-*/system-info/experiment-*）
# 已迁 deterline/cmds/save_cmds.py，O2 步 4
# ============================================================
from deterline.cmds.save_cmds import (cmd_undo, cmd_list_backups,  # noqa: F401
                                      cmd_reset_flags, cmd_reset_all,
                                      cmd_create_system_info,
                                      cmd_experiment_snapshot,
                                      cmd_experiment_list,
                                      cmd_experiment_restore)

# ============================================================
# Dialogue Editor Commands (game.ios / data.win) — UTMT CLI
# ============================================================


# ============================================================
# Code Editor Commands (game.ios / data.win) — UTMT CLI
# ============================================================


# ============================================================
# set-derived: lock LV-derived stats (HP/AT/DF) in game scripts
# ============================================================


# ============================================================
# gml-bg (Auto-generate runtime background GML injection)
# ============================================================

def _parse_layers(spec: str | None) -> list[int]:
    """Parse a layer spec like "0,1,2" into [0, 1, 2]. Empty/None -> []."""
    if not spec:
        return []
    out: list[int] = []
    for part in str(spec).replace(" ", "").split(","):
        if not part:
            continue
        try:
            v = int(part)
        except ValueError:
            raise ValueError(f"无效的层索引: {part!r} (应为 0-7 整数, 逗号分隔)")
        if not 0 <= v <= 7:
            raise ValueError(f"层索引越界: {v} (允许 0-7)")
        out.append(v)
    return out


def build_gml_bg_code(room_name: str, bg_asset: str, slots: list[int],
                      speedx: float = 0.0, speedy: float = 0.0,
                      hide_above: bool = False, vtiled: bool = True,
                      foreground: bool = False) -> str:
    """Build the runtime-background GML injected by `gml-bg`.

    Pure function (no I/O) so it can be unit-tested.

    - slots: background layer indices to assign `bg_asset` to.
    - hide_above: hide every layer above max(slots) to avoid occlusion
      (higher slots are drawn on top of lower slots).
    - vtiled/foreground: applied to every slot.
    """
    if not slots:
        slots = [0]
    esc_room = _csx_escape(room_name)
    bg_ref = bg_asset if bg_asset.isdigit() else _csx_escape(bg_asset)
    slot_key = "_".join(str(s) for s in slots)
    asset_key = bg_asset.replace('"', "")
    flag_name = f"det_bg_{esc_room}_{slot_key}_{asset_key}"

    setup: list[str] = []
    for s in slots:
        setup.append(f"background_visible[{s}] = true;")
        setup.append(f"background_index[{s}] = {bg_ref};")
        setup.append(f"background_htiled[{s}] = true;")
        setup.append(f"background_vtiled[{s}] = {'true' if vtiled else 'false'};")
        setup.append(f"background_foreground[{s}] = {'true' if foreground else 'false'};")
    if hide_above:
        top = max(slots)
        setup.append(
            f"for (var _det_i = {top} + 1; _det_i < 8; _det_i++) "
            "{ background_visible[_det_i] = false; }"
        )

    parallax: list[str] = []
    for s in slots:
        parallax.append(
            f"background_x[{s}] = floor(view_xview[0] - (view_xview[0] * {speedx}));"
        )
        parallax.append(
            f"background_y[{s}] = floor(view_yview[0] - (view_yview[0] * {speedy}));"
        )

    setup_block = "\n".join(setup)
    parallax_block = "\n".join(parallax)
    return f'''if (room == {esc_room})
{{
if (!variable_global_exists("{flag_name}"))
{{
global.{flag_name} = 1;
{setup_block}
}}
{parallax_block}
}}'''


def cmd_gml_bg(game_file: Path, room_name: str, bg_asset: str,
               slot: int = 0, speedx: float | None = None,
               speedy: float | None = None,
               layers: str | None = None,
               all_layers: bool = False,
               hide_above: bool = False,
               vtiled: bool = True,
               foreground: bool = False) -> None:
    """Inject runtime-background GML into obj_mainchara_Step_0.

    Handles multiple layers and occlusion: higher slots draw on top of
    lower ones, so `--hide-above` disables every layer above the target.
    """
    slots = _parse_layers(layers)
    if all_layers:
        slots = list(range(8))
    if not slots:
        slots = [slot]
    gml = build_gml_bg_code(
        room_name, bg_asset, slots,
        speedx=speedx if speedx is not None else 0.0,
        speedy=speedy if speedy is not None else 0.0,
        hide_above=hide_above, vtiled=vtiled, foreground=foreground,
    )
    cmd_code_append(game_file, "gml_Object_obj_mainchara_Step_0", gml)


def cmd_remove_tile(game_file: Path, room_name: str,
                    instance: int | None = None) -> None:
    """Remove tiles from a room. If --instance given, removes only that tile.
    Otherwise removes ALL tiles from the room."""
    esc_room = _csx_escape(room_name)

    if instance is not None:
        # Remove single tile by instance ID
        csx = f'''
var room = Data.Rooms.ByName("{esc_room}");
if (room == null) {{ ScriptMessage("ERROR: Room not found"); return; }}
int removed = 0;
for (int i = room.Tiles.Count - 1; i >= 0; i--) {{
    if (room.Tiles[i].InstanceID == {instance}) {{
        room.Tiles.RemoveAt(i);
        removed++;
        break;
    }}
}}
ScriptMessage("OK: Removed " + removed + " tile(s) from " + "{esc_room}");
'''
    else:
        # Remove all tiles
        csx = f'''
var room = Data.Rooms.ByName("{esc_room}");
if (room == null) {{ ScriptMessage("ERROR: Room not found"); return; }}
int count = room.Tiles.Count;
room.Tiles.Clear();
ScriptMessage("OK: Cleared " + count + " tiles from " + "{esc_room}");
'''

    out = _run_utmt(csx, game_file, save=True)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)


# ============================================================
# Text Data Commands (global.text_data_en map)
# ============================================================


# ============================================================
# Variable Search (search for variable usage across all code)
# ============================================================


# ============================================================
# Script Management (create new code entries)
# ============================================================


# ============================================================
# Room Object Inspector (list objects in a specific room)
# ============================================================

def cmd_room_objects(game_file: Path, room_name: str) -> None:
    """List all object instances in a room by its internal name."""
    esc = _csx_escape(room_name)
    csx = f'''
bool found = false;
for (int r = 0; r < Data.Rooms.Count; r++) {{
    var room = Data.Rooms[r];
    if (room.Name.Content.IndexOf("{esc}", StringComparison.OrdinalIgnoreCase) >= 0) {{
        found = true;
        ScriptMessage("Room[" + r + "]: " + room.Name.Content);
        var _seenIds = new System.Collections.Generic.HashSet<uint>();
        foreach (var go in room.GameObjects) {{
            string objName = go.ObjectDefinition?.Name?.Content ?? "(unknown)";
            string idMark = "";
            if (go.ObjectDefinition != null && (go.InstanceID == 0 || !_seenIds.Add(go.InstanceID)))
                idMark = "  ⚠️ ID=0/重复";
            ScriptMessage("  [" + go.InstanceID + "] " + objName + " at (" + go.X + "," + go.Y + ")" + idMark);
            // Show code events for this object
            string objDefName = "gml_Object_" + objName + "_";
            bool hasAny = false;
            foreach (var code in Data.Code) {{
                string cname = code.Name.Content;
                if (cname.StartsWith(objDefName)) {{
                    if (!hasAny) {{ ScriptMessage("    Events:"); hasAny = true; }}
                    string evt = cname.Substring(objDefName.Length);
                    ScriptMessage("      " + evt);
                }}
            }}
        }}
    }}
}}
if (!found) {{
    ScriptMessage("(no matching room found)");
}}
'''
    out = _run_utmt(csx, game_file, save=False)
    for line in _parse_msg(out):
        print(line)


# ============================================================
# Room Object Spawn/Remove (room layout editing)
# ============================================================

def _spawn_obj_internal(game_file: Path, room_name: str, obj_name: str, x: int, y: int,
                        quiet: bool = False) -> int | None:
    """Spawn an object instance in a room. Returns the new instance ID (or None on failure).

    Shared by cmd_spawn_obj and cmd_npc_dialogue. When quiet=True, suppresses
    non-essential output (used by higher-level commands that report their own progress).
    """
    esc_room = _csx_escape(room_name)
    esc_obj = _csx_escape(obj_name)
    csx = f'''
var room = Data.Rooms.ByName("{esc_room}");
if (room == null) {{
    for (int r = 0; r < Data.Rooms.Count; r++) {{
        if (Data.Rooms[r].Name.Content.IndexOf("{esc_room}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            room = Data.Rooms[r];
            break;
        }}
    }}
}}
if (room == null) {{
    ScriptMessage("ERROR: Room not found: {esc_room}");
    // Suggest similar rooms
    string suggest = "";
    int found = 0;
    for (int r = 0; r < Data.Rooms.Count && found < 5; r++) {{
        string rn = Data.Rooms[r].Name.Content;
        if (rn.IndexOf("{esc_room}", StringComparison.OrdinalIgnoreCase) >= 0 ||
            "{esc_room}".IndexOf(rn, StringComparison.OrdinalIgnoreCase) >= 0) {{
            suggest += (found > 0 ? ", " : "") + rn;
            found++;
        }}
    }}
    if (found > 0) ScriptMessage("HINT: Did you mean: " + suggest);
    return;
}}
var objDef = Data.GameObjects.ByName("{esc_obj}");
if (objDef == null) {{
    for (int o = 0; o < Data.GameObjects.Count; o++) {{
        if (Data.GameObjects[o].Name.Content.IndexOf("{esc_obj}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            objDef = Data.GameObjects[o];
            break;
        }}
    }}
}}
if (objDef == null) {{
    ScriptMessage("ERROR: Object not found: {esc_obj}");
    // Suggest similar objects
    string suggest = "";
    int found = 0;
    for (int o = 0; o < Data.GameObjects.Count && found < 5; o++) {{
        string on = Data.GameObjects[o].Name.Content;
        if (on.IndexOf("{esc_obj}", StringComparison.OrdinalIgnoreCase) >= 0 ||
            "{esc_obj}".IndexOf(on, StringComparison.OrdinalIgnoreCase) >= 0) {{
            suggest += (found > 0 ? ", " : "") + on;
            found++;
        }}
    }}
    if (found > 0) ScriptMessage("HINT: Did you mean: " + suggest);
    return;
}}
// Native interactable detection (parent chain walk)
bool objNativeInteract = false;
var objChainCur = objDef;
int objChainGuard = 0;
while (objChainCur != null && objChainGuard < 30)
{{
    string objChainName = objChainCur.Name?.Content ?? "";
    if (objChainName == "obj_interactable" || objChainName == "obj_readablesolid")
    {{
        objNativeInteract = true;
        break;
    }}
    objChainCur = objChainCur.ParentId;
    objChainGuard++;
}}
if (objNativeInteract)
{{
    ScriptMessage("WARN: 该对象继承原生交互系统 (obj_readablesolid/obj_interactable)");
    ScriptMessage("     若注入 myinteract 距离触发会与默认对话重叠 → 改用 flag 状态机 + 守卫 Alarm_0,");
    ScriptMessage("     或直接用 npc-dialogue / guard-npc-alarm 命令。");
}}
// Self-destructing pickup detection (experiment 20: obj_pie_pickup hides via instance_destroy in Step_1).
// Exact whitelist only: these 3 pickups vanish every frame once their "taken" flag is set.
string objSelName = objDef.Name?.Content ?? "";
string objSelFlag = "";
if (objSelName == "obj_pie_pickup") objSelFlag = "global.flag[103]";
else if (objSelName == "obj_knife_pickup") objSelFlag = "global.flag[102]";
else if (objSelName == "obj_ribbon_pickup") objSelFlag = "global.flag[100]";
if (objSelFlag.Length > 0)
{{
    ScriptMessage("WARN: " + objSelName + " 是自毁拾取物 → " + objSelFlag + "!=1（物品未拿走）时每帧 instance_destroy()，spawn 后会立刻消失");
    ScriptMessage("     若只是摆放展示，改用无自毁逻辑的对象（如 obj_bigpie）。");
}}
// Check for nearby objects (overlap warning)
int nearCount = 0;
int nearThreshold = 30;
foreach (var go in room.GameObjects) {{
    int dx = go.X - {x};
    int dy = go.Y - {y};
    if (dx * dx + dy * dy < nearThreshold * nearThreshold) {{
        nearCount++;
        if (nearCount <= 3) ScriptMessage("WARN: Near existing obj " + (go.ObjectDefinition?.Name?.Content ?? "?") + " at (" + go.X + "," + go.Y + ")");
    }}
}}
if (nearCount > 0) ScriptMessage("(found " + nearCount + " objects within " + nearThreshold + "px)");

ulong _maxInstId = 0;
foreach (var _r in Data.Rooms)
{{
    foreach (var _g in _r.GameObjects)
    {{
        if (_g.InstanceID > _maxInstId) _maxInstId = _g.InstanceID;
    }}
}}
uint newId = (uint)(System.Math.Max((long)Data.GeneralInfo.LastObj, (long)_maxInstId) + 1);
Data.GeneralInfo.LastObj = newId;
room.GameObjects.Add(new UndertaleRoom.GameObject() {{
    InstanceID = newId,
    ObjectDefinition = objDef,
    X = {x},
    Y = {y}
}});
string objName = objDef.Name?.Content ?? "(unknown)";
string rName = room.Name?.Content ?? "(unknown)";
ScriptMessage("OK: Spawned [" + newId + "] " + objName + " in " + rName + " at ({x}, {y})");
ScriptMessage("SPAWN_RESULT:" + newId + ":" + (objNativeInteract ? "1" : "0"));
'''
    csx += _instances_check_snippet()
    out = _run_utmt(csx, game_file, save=True)
    new_id: int | None = None
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("HINT:"):
            print(line, file=sys.stderr)
        elif line.startswith("WARN:"):
            if not quiet:
                print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            if not quiet:
                print(line)
        elif line.startswith("SPAWN_RESULT:"):
            parts = line.split(":")
            try:
                new_id = int(parts[1])
            except (IndexError, ValueError):
                new_id = None
        else:
            if not quiet:
                print(line)
    return new_id


def cmd_spawn_obj(game_file: Path, room_name: str, obj_name: str, x: int, y: int) -> None:
    """Spawn an object instance in a room at given coordinates."""
    _spawn_obj_internal(game_file, room_name, obj_name, x, y)


def cmd_remove_obj(game_file: Path, room_name: str, obj_name: str,
                   instance_id: int | None = None, remove_all: bool = False) -> None:
    """Remove an object instance from a room.

    If instance_id is given, remove that specific instance.
    Otherwise, remove by object name (first match unless --all).
    """
    if instance_id is not None:
        esc_room = _csx_escape(room_name)
        csx = f'''
var room = Data.Rooms.ByName("{esc_room}");
if (room == null) {{
    for (int r = 0; r < Data.Rooms.Count; r++) {{
        if (Data.Rooms[r].Name.Content.IndexOf("{esc_room}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            room = Data.Rooms[r];
            break;
        }}
    }}
}}
if (room == null) {{
    ScriptMessage("ERROR: Room not found: {esc_room}");
    return;
}}
var target = room.GameObjects.ByInstanceID({instance_id});
if (target == null) {{
    ScriptMessage("ERROR: Instance [{instance_id}] not found in " + (room.Name?.Content ?? "(unknown)"));
    return;
}}
string objName = target.ObjectDefinition?.Name?.Content ?? "(unknown)";
room.GameObjects.Remove(target);
ScriptMessage("OK: Removed [" + {instance_id} + "] " + objName + " from " + (room.Name?.Content ?? "(unknown)"));
'''
    else:
        esc_room = _csx_escape(room_name)
        esc_obj = _csx_escape(obj_name)
        remove_all_flag = "true" if remove_all else "false"
        csx = f'''
var room = Data.Rooms.ByName("{esc_room}");
if (room == null) {{
    for (int r = 0; r < Data.Rooms.Count; r++) {{
        if (Data.Rooms[r].Name.Content.IndexOf("{esc_room}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            room = Data.Rooms[r];
            break;
        }}
    }}
}}
if (room == null) {{
    ScriptMessage("ERROR: Room not found: {esc_room}");
    return;
}}
var objDef = Data.GameObjects.ByName("{esc_obj}");
if (objDef == null) {{
    for (int o = 0; o < Data.GameObjects.Count; o++) {{
        if (Data.GameObjects[o].Name.Content.IndexOf("{esc_obj}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            objDef = Data.GameObjects[o];
            break;
        }}
    }}
}}
if (objDef == null) {{
    ScriptMessage("ERROR: Object not found: {esc_obj}");
    return;
}}
int removed = 0;
bool removeAll = {remove_all_flag};
if (removeAll) {{
    for (int i = room.GameObjects.Count - 1; i >= 0; i--) {{
        if (room.GameObjects[i].ObjectDefinition == objDef) {{
            room.GameObjects.RemoveAt(i);
            removed++;
        }}
    }}
}} else {{
    for (int i = 0; i < room.GameObjects.Count; i++) {{
        if (room.GameObjects[i].ObjectDefinition == objDef) {{
            room.GameObjects.RemoveAt(i);
            removed++;
            break;
        }}
    }}
}}
string objName = objDef.Name?.Content ?? "(unknown)";
string rName = room.Name?.Content ?? "(unknown)";
ScriptMessage("OK: Removed " + removed + " instance(s) of " + objName + " from " + rName);
'''
    out = _run_utmt(csx, game_file, save=True)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)
        else:
            print(line)


# ============================================================
# Safe NPC dialogue (npc-dialogue / guard-npc-alarm)
# ============================================================

def _query_npc_target(game_file: Path, obj_name: str) -> dict | None:
    """Query object inheritance (native interactable?) + its own Step/Alarm code entries.

    Returns {"obj", "native", "step_code", "alarm_code"} or None if not found.
    native=True means the object inherits obj_readablesolid/obj_interactable
    (has a native Z-key/touch interaction system that conflicts with myinteract triggers).
    """
    esc = _csx_escape(obj_name)
    csx = f'''
var obj = Data.GameObjects.ByName("{esc}");
if (obj == null) {{ obj = Data.GameObjects.ByName("{esc}", true); }}
if (obj == null) {{
    string q = "{esc}";
    int first = -1;
    int count = 0;
    for (int o = 0; o < Data.GameObjects.Count; o++) {{
        string on = Data.GameObjects[o].Name.Content;
        if (on.IndexOf(q, StringComparison.OrdinalIgnoreCase) >= 0) {{
            if (first < 0) first = o;
            count++;
        }}
    }}
    if (first >= 0) {{
        obj = Data.GameObjects[first];
        ScriptMessage("NPC_TARGET:MATCH:" + obj.Name.Content + ":" + count);
    }}
}}
if (obj == null) {{
    ScriptMessage("NPC_TARGET:NOT_FOUND");
    return;
}}
bool native = false;
var cur = obj;
int guard = 0;
while (cur != null && guard < 30) {{
    string cn = cur.Name?.Content ?? "";
    if (cn == "obj_interactable" || cn == "obj_readablesolid") {{
        native = true;
        break;
    }}
    cur = cur.ParentId;
    guard++;
}}
string oname = obj.Name.Content;
string stepCode = "";
string[] stepNames = new string[] {{
    "gml_Object_" + oname + "_Step_1",
    "gml_Object_" + oname + "_Step_0",
    "gml_Object_" + oname + "_Step_2"
}};
foreach (string sn in stepNames) {{
    if (Data.Code.ByName(sn) != null) {{
        stepCode = sn;
        break;
    }}
}}
string alarmCode = "";
var acur = obj;
guard = 0;
while (acur != null && guard < 30) {{
    string cand = "gml_Object_" + acur.Name.Content + "_Alarm_0";
    if (Data.Code.ByName(cand) != null) {{
        alarmCode = cand;
        break;
    }}
    acur = acur.ParentId;
    guard++;
}}
ScriptMessage("NPC_TARGET:RESULT:" + oname + ":" + (native ? "1" : "0") + ":" + stepCode + ":" + alarmCode);
'''
    out = _run_utmt(csx, game_file, save=False)
    for line in _parse_msg(out):
        if line.startswith("NPC_TARGET:RESULT:"):
            body = line[len("NPC_TARGET:RESULT:"):]
            parts = body.split(":")
            if len(parts) >= 4:
                return {
                    "obj": parts[0],
                    "native": parts[1] == "1",
                    "step_code": parts[2],
                    "alarm_code": ":".join(parts[3:]),
                }
        if line.startswith("NPC_TARGET:NOT_FOUND"):
            return None
    return None


def _build_npc_step_block(instance_id: int, text_key: str, face: int, emotion: int,
                          native: bool, once: bool = False, range_: int = 50) -> str:
    """Build distance-trigger GML for a spawned NPC instance.

    ⚠️⚠️ 形态约束（2026-11-07 游戏内实测 15 次启动实验矩阵，见 AUDIT_2026-11-07/域F）：
    本环境（UndertaleModCli 0.9.1.2 + Undertale Mac Runner）对附加/替换代码块存在
    未定位的字节级问题——触发 create 一旦被"状态条件"门控就静默失效，无论：
      - 状态存哪（新实例变量 deterline_state / global.flag[510] / 内建变量 friction）
      - 条件在哪一层（外层链 / 嵌套内层）
      - 写入在 create 之前还是之后
    而"纯扁平块"（id 守卫 + !instance_exists 三件套 + 嵌套距离判断，块内无任何
    状态读写）经多次启动稳定工作。因此本生成器只生成已验证形态：

      if (id == N && !exists×3) { if (dist < range) { <建对话框> } }

    once=True  → 触发后在同一块内 instance_destroy() 自毁（对话框是独立实例不受影响），
                 实现"只说一次"；NPC 说完即从房间消失（工具会打印此行为说明）。
    once=False → 可重复触发：关闭对话后若仍在范围内会再次弹出（走出范围即停止）；
                 ⚠️ 不设置 global.interact=1——无状态机时无处复位，会把玩家软锁。

    `native` 只影响 Alarm_0 守卫（调用方处理），与本块无关。
    """
    once_line = "\n            instance_destroy();" if once else ""
    return f'''if (id == {instance_id} && !instance_exists(obj_dialoguer) && !instance_exists(OBJ_WRITER) && !instance_exists(obj_choicer))
{{
    if (distance_to_object(obj_mainchara) < {range_})
    {{
        global.msc = 0;
        global.typer = 5;
        global.facechoice = {face};
        global.faceemotion = {emotion};
        global.msg[0] = scr_gettext("{text_key}");
        global.msg[1] = "%%%";
        instance_create(0, 0, obj_dialoguer);{once_line}
    }}
}}
'''


def _build_npc_choice_block(instance_id: int, choice_key: str, yes_key: str | None,
                            no_key: str, face: int, emotion: int, range_: int = 50,
                            goto_room: str | None = None, item_id: int | None = None,
                            repeat: bool = False) -> str:
    """Build a distance-trigger GML block for a YES/NO choice NPC.

    ⚠️⚠️ 形态约束同 _build_npc_step_block（2026-11-07 游戏内实测 15 次启动）：只生成
    已验证的扁平形态，块内禁止任何状态读写；分支体保持单层平铺语句。

    - trigger: player within range_ px → show the `\\C` choice text
    - YES (global.choice == 0): replace msg[0] with yes text (no \\C); optionally
      give an item (scr_itemget) and/or teleport (room_goto)
    - NO (global.choice == 1): replace msg[0] with no text (no \\C)
    - CRITICAL: branch texts MUST replace global.msg[0] with a non-\\C text —
      otherwise obj_choicer's alarm (2 frames later) re-copies the `\\C` text via
      scr_msgup and the choice box pops up again in a loop.
    - 单次语义（默认）通过"答完后 instance_destroy() 自毁"实现（触发块不再被状态门控）；
      repeat=True 时 NPC 存活，走开再靠近可再次提问。
    - ⚠️ 已知限制（2026-11 复核）：选择处理分支按 global.choice 响应、无法区分同房间的
      多个选择 NPC——同一房间放多个 obj 选择 NPC 时，回答会串（窄场景；不同对象/不同
      房间不受影响）。
    """
    yes_lines = ""
    if yes_key:
        yes_lines += f'''        global.typer = 5;
        global.facechoice = {face};
        global.faceemotion = {emotion};
        global.msg[0] = scr_gettext("{yes_key}");
        global.msg[1] = "%%%";
'''
    if item_id is not None:
        yes_lines += f"        script_execute(scr_itemget, {item_id});\n"
    if goto_room:
        yes_lines += f"        room_goto({goto_room});\n"
    if not repeat:
        yes_lines += "        instance_destroy();\n"

    no_destroy = "        instance_destroy();\n" if not repeat else ""
    return f'''if (id == {instance_id} && !instance_exists(obj_dialoguer) && !instance_exists(OBJ_WRITER) && !instance_exists(obj_choicer))
{{
    if (distance_to_object(obj_mainchara) < {range_})
    {{
        global.msc = 0;
        global.typer = 5;
        global.facechoice = {face};
        global.faceemotion = {emotion};
        global.msg[0] = scr_gettext("{choice_key}");
        global.msg[1] = "%%%";
        instance_create(0, 0, obj_dialoguer);
    }}
}}
if (id == {instance_id} && global.choice != -1)
{{
    if (global.choice == 0)
    {{
        global.choice = -1;
        global.msc = -1;
{yes_lines}    }}
    else
    {{
        global.choice = -1;
        global.msc = -1;
        global.typer = 5;
        global.facechoice = {face};
        global.faceemotion = {emotion};
        global.msg[0] = scr_gettext("{no_key}");
        global.msg[1] = "%%%";
{no_destroy}    }}
}}
'''


def _guard_alarm_for_instance(game_file: Path, alarm_code: str, instance_id: int) -> bool:
    """Prepend `if (id == N) exit;` to an Alarm_0 entry (idempotent). Returns True if added."""
    esc = _csx_escape(alarm_code)
    guard = f"if (id == {instance_id})\n{{\n    exit;\n}}"
    verb = _csx_verbatim_escape(guard)
    # Single round trip: decompile → check idempotency → prepend guard.
    csx = f'''
var code = Data.Code.ByName("{esc}");
if (code == null) {{
    ScriptMessage("ERROR: Code entry not found: {esc}");
    return;
}}
try {{
    string existingGml = GetDecompiledText(code);
    if (existingGml.IndexOf("id == {instance_id}") >= 0) {{
        ScriptMessage("SKIP: guard already present");
        return;
    }}
    string newGml = @"{verb}" + "\\n" + existingGml;
    CodeImportGroup importGroup = new(Data)
    {{
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueueReplace(code, newGml);
    importGroup.Import();
    ScriptMessage("OK: guarded");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    out = _run_utmt(csx, game_file, save=True)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
            return False
        elif line.startswith("SKIP:"):
            print(f"  ⏭️  守卫已存在: {alarm_code} (id == {instance_id})")
            return False
        elif line.startswith("OK:"):
            print(f"  ✅ 已守卫 Alarm_0: {alarm_code}")
            return True
    return False


def _find_create_code(game_file: Path, obj_name: str) -> str | None:
    """Find the effective Create event code entry for an object (self or parent chain).

    Walks the parent chain like _query_npc_target does for Step/Alarm, so a child
    object without its own Create event still maps to the inherited one.
    """
    esc = _csx_escape(obj_name)
    csx = f'''
var obj = Data.GameObjects.ByName("{esc}");
if (obj == null) {{
    for (int o = 0; o < Data.GameObjects.Count; o++) {{
        if (Data.GameObjects[o].Name.Content.IndexOf("{esc}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            obj = Data.GameObjects[o];
            break;
        }}
    }}
}}
if (obj == null) {{
    ScriptMessage("FIND_CREATE:NOT_FOUND");
    return;
}}
string found = "";
var cur = obj;
int guard = 0;
while (cur != null && guard < 30) {{
    string cand = "gml_Object_" + cur.Name.Content + "_Create_0";
    if (Data.Code.ByName(cand) != null) {{
        found = cand;
        break;
    }}
    cur = cur.ParentId;
    guard++;
}}
ScriptMessage("FIND_CREATE:" + (found.Length > 0 ? found : "NONE"));
'''
    out = _run_utmt(csx, game_file, save=False)
    for line in _parse_msg(out):
        if line.startswith("FIND_CREATE:"):
            val = line[len("FIND_CREATE:"):]
            return None if val == "NONE" else val
    return None


def _ensure_var_initialized(game_file: Path, obj_name: str, var_name: str) -> bool:
    """Ensure a per-instance variable is initialized (registered) for an object.

    Root cause of the NSID=0 crash: a new instance variable that is only referenced
    in one code entry gets Occurrences=0 (→ NameStringID=0) if that entry is ever
    overwritten without the variable. Initializing it in Create_0 keeps it referenced
    forever, so its NameStringID stays valid.

    Idempotent: skips if the var is already referenced in the effective Create_0.
    Returns True if the variable is (or already was) initialized.
    """
    create_code = _find_create_code(game_file, obj_name)
    esc_var = _csx_escape(var_name)
    verb_var = _csx_verbatim_escape(var_name)

    if create_code is None:
        # No Create event anywhere → create one with the init line (AutoCreateAssets links the event).
        esc_obj = _csx_escape(obj_name)
        create_name = f"gml_Object_{obj_name}_Create_0"
        esc_name = _csx_escape(create_name)
        init = f"{var_name} = 0;"
        verb = _csx_verbatim_escape(init)
        csx = f'''
var obj = Data.GameObjects.ByName("{esc_obj}");
if (obj == null) {{
    for (int o = 0; o < Data.GameObjects.Count; o++) {{
        if (Data.GameObjects[o].Name.Content.IndexOf("{esc_obj}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            obj = Data.GameObjects[o];
            break;
        }}
    }}
}}
if (obj == null) {{
    ScriptMessage("ERROR: Object not found: {esc_obj}");
    return;
}}
try {{
    CodeImportGroup importGroup = new(Data)
    {{
        AutoCreateAssets = true,
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueueReplace("{esc_name}", @"{verb}");
    importGroup.Import();
    ScriptMessage("OK: Created " + "{create_name}" + " with `{var_name} = 0;`");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
        out = _run_utmt(csx, game_file, save=True)
        ok = any(line.startswith("OK:") for line in _parse_msg(out))
        if ok:
            print(f"  ✅ 已创建 Create 事件并初始化变量 {var_name} ({create_name})")
        return ok

    # Check existing Create_0: does it already reference var_name? (idempotency)
    lines = _decompile_to_lines(game_file, create_code)
    if lines is not None and any(var_name in ln for ln in lines):
        print(f"  ⏭️  变量 {var_name} 已在 {create_code} 初始化")
        return True

    # Prepend the init line to the effective Create_0.
    esc_name = _csx_escape(create_code)
    init = f"{var_name} = 0;"
    verb = _csx_verbatim_escape(init)
    csx = f'''
var code = Data.Code.ByName("{esc_name}");
if (code == null) {{
    ScriptMessage("ERROR: Code entry not found: {esc_name}");
    return;
}}
try {{
    string existingGml = GetDecompiledText(code);
    string newGml = @"{verb}" + "\\n" + existingGml;
    CodeImportGroup importGroup = new(Data)
    {{
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueueReplace(code, newGml);
    importGroup.Import();
    ScriptMessage("OK: Prepended `{var_name} = 0;` to {esc_name}");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    out = _run_utmt(csx, game_file, save=True)
    ok = any(line.startswith("OK:") for line in _parse_msg(out))
    if ok:
        print(f"  ✅ 已在 {create_code} 初始化变量 {var_name}")
    return ok


def _instances_check_snippet() -> str:
    """Return a C# snippet that audits the in-scope `room` for invalid instance IDs.

    Appended to the CSX of room-write commands (spawn/door/pit/battle) so that any
    operation adding instances reports ID=0 / duplicate-ID problems immediately,
    without an extra UTMT round-trip.  Only reports — never mutates.  The `room`
    variable must be non-null at the point of insertion.
    """
    return r'''
// --- instance ID audit (experiment 19: ID=0/duplicate breaks per-instance vars) ---
int _chkZero = 0;
int _chkDup = 0;
var _chkSeen = new System.Collections.Generic.HashSet<uint>();
foreach (var _chkG in room.GameObjects)
{
    if (_chkG.ObjectDefinition == null) continue;
    if (_chkG.InstanceID == 0) { _chkZero++; }
    else if (!_chkSeen.Add(_chkG.InstanceID)) { _chkDup++; }
}
if (_chkZero > 0 || _chkDup > 0)
{
    ScriptMessage("WARN_INSTANCES:zero=" + _chkZero + " dup=" + _chkDup + " (room=" + room.Name.Content + ")");
    ScriptMessage("  提示: 实例 ID=0/重复会使 per-instance 变量表冲突(Create 写入不生效 → 崩溃/漏口)。");
    ScriptMessage("  请运行: --action verify-instances --fix --file data_win");
}
'''


def _parse_instance_audit(output: str) -> dict:
    """Parse VERIFY_INSTANCES / BAD_INSTANCE / WARN_INSTANCES output into a dict.

    Keys: bad (int|None), zero, dup, null, nonexist, fixed, bad_lines (list).
    """
    result: dict = {"bad": None, "zero": 0, "dup": 0, "null": 0, "nonexist": 0,
                    "fixed": 0, "bad_lines": []}
    for line in _parse_msg(output):
        if line.startswith("BAD_INSTANCE:"):
            result["bad_lines"].append(line[len("BAD_INSTANCE:"):])
        elif line.startswith("VERIFY_INSTANCES:"):
            body = line[len("VERIFY_INSTANCES:"):]
            parts = dict(p.split("=") for p in body.split() if "=" in p)
            result["bad"] = int(parts.get("bad", 0))
            result["zero"] = int(parts.get("zero", 0))
            result["dup"] = int(parts.get("dup", 0))
            result["null"] = int(parts.get("null", 0))
            result["nonexist"] = int(parts.get("nonexist", 0))
            result["fixed"] = int(parts.get("fixed", 0))
        elif line.startswith("WARN_INSTANCES:"):
            result["warn"] = line[len("WARN_INSTANCES:"):]
    return result


def cmd_verify_nsid(game_file: Path, fix: bool = False) -> None:
    """Check for variables with corrupted NameStringID (0 while referenced).

    Such variables crash the game when read (the NSID=0 trap). By default reports;
    with --fix, resets each broken variable's NameStringID to the correct STRG index.
    """
    csx = f'''
int bad = 0;
int fixedCnt = 0;
for (int i = 0; i < Data.Variables.Count; i++)
{{
    var v = Data.Variables[i];
    string vname = v.Name?.Content ?? "";
    if (vname.Length == 0) continue;
    bool corrupt = v.NameStringID <= 0 && v.Occurrences > 0;
    if (v.NameStringID > 0)
    {{
        // Sanity: NSID must point back to the same name in the STRG table.
        var pointed = (v.NameStringID < Data.Strings.Count) ? (Data.Strings[v.NameStringID]?.Content ?? "") : "";
        if (pointed != vname) corrupt = true;
    }}
    if (corrupt)
    {{
        int correct = Data.Strings.IndexOf(v.Name);
        bad++;
        if ({( "true" if fix else "false" )})
        {{
            v.NameStringID = correct;
            fixedCnt++;
        }}
        ScriptMessage("BAD_NSID: name='" + vname + "' nsid=" + v.NameStringID + " occ=" + v.Occurrences + " correct=" + correct + " fixed=" + ({( "true" if fix else "false" )}));
    }}
}}
ScriptMessage("VERIFY_NSID:bad=" + bad + " fixed=" + fixedCnt);
'''
    out = _run_utmt(csx, game_file, save=fix)
    bad = fixed = None
    for line in _parse_msg(out):
        if line.startswith("BAD_NSID:"):
            print(f"  ⚠️  {line[len('BAD_NSID:'):]}")
        elif line.startswith("VERIFY_NSID:"):
            body = line[len("VERIFY_NSID:"):]
            parts = dict(p.split("=") for p in body.split() if "=" in p)
            bad = int(parts.get("bad", 0))
            fixed = int(parts.get("fixed", 0))
    if bad is None:
        print("错误: 无法解析 verify-nsid 结果", file=sys.stderr)
        return
    if bad == 0:
        print("✅ verify-nsid: 无损坏变量（全部 NameStringID 有效）")
    else:
        if fix:
            print(f"⚠️ verify-nsid: 发现 {bad} 个损坏变量，已修复 {fixed} 个")
        else:
            print(f"⚠️ verify-nsid: 发现 {bad} 个损坏变量（用 --fix 自动修复）")


def cmd_smoke_test(game_file: Path, save_dir: Path, room_name: str = "room_torielroom",
                   obj_name: str = "obj_cactus", x: int = 160, y: int = 150,
                   timeout: int = 120, send_keys: str = "external") -> None:
    """W3：游戏内冒烟测试（半自动，≈90 秒/次，验证级别 in-game）。

    流程：备份三件 → 注入"扁平触发块 + 标记文件写入"到 obj 的 Step 事件 →
    写 file0 Room 传送到目标房 → 提交真实文件（本命令是唯一内建 --commit 流）
    → steam://run 启动 → 轮询存档目录的 zcode_smoke_marker.txt（可选盲发 Z）
    → 断言 → pkill 游戏 → 全量恢复（MD5 校验）。

    标记由游戏内 file_text_open_write 写出（探针已证实函数存在且写往存档目录）。
    PASS = 触发块在游戏内真实执行过。这是第五层验证（游戏内）的自动化。
    FAIL 时退出码 1；成功自动清理备份，失败保留供取证。

    ⚠️ 环境敏感性：external 按键模式下，若游戏停在开场/菜单等 Z 或窗口失焦，
    无人值守可能假阴性 FAIL（12:13 PASS / 12:56 FAIL 实例）——无人值守推荐
    `--keys osascript`（需辅助功能权限），或人工按键配合 `--timeout` 放宽。
    """
    import time as _time
    import subprocess as _sp

    ts = _time.strftime("%Y%m%d_%H%M%S")
    marker_name = "zcode_smoke_marker.txt"
    marker = save_dir / marker_name
    game_exe_running = lambda: _sp.run(["pgrep", "-x", "Mac_Runner"],
                                       capture_output=True).returncode == 0
    if game_exe_running():
        raise ValidationError("检测到 Undertale 正在运行——smoke-test 需要游戏处于关闭状态（请先退出游戏）")
    # 记录运行前已存在的 .bak.*（运行后新增的属于本次、成功后清理，防 ≈250MB/次 堆盘）
    pre_baks = set(p.name for p in game_file.parent.glob("game.ios.bak.*"))

    text_key = f"smoke_test_{ts}"
    print(f"--- smoke-test (W3) ts={ts} ---")
    print(f"  房间: {room_name} @ ({x},{y})  对象: {obj_name}")

    # ── 1. 备份三件 ──
    f0 = save_dir / "file0"
    ini = save_dir / "undertale.ini"
    b_game = game_file.with_name(f"game.ios.snap.smoke_{ts}")
    b_f0 = f0.with_name(f"file0.snap.smoke_{ts}")
    b_ini = ini.with_name(f"undertale.ini.snap.smoke_{ts}")
    shutil.copy2(str(game_file), str(b_game))
    if f0.exists():
        shutil.copy2(str(f0), str(b_f0))
    if ini.exists():
        shutil.copy2(str(ini), str(b_ini))
    md5_before = _md5_file(game_file)
    print(f"  备份: {b_game.name} / {b_f0.name} / {b_ini.name}")

    # ── 2. 注入（本命令是内建 commit 流：直写真实文件；任何失败都走 finally 恢复）──
    passed = False
    marker_content = ""
    try:
        state.COMMIT_ACTIVE = True
        cmd_textdata_add(game_file, text_key, f"* SMOKE OK {ts}/%%")
        new_id = _spawn_obj_internal(game_file, room_name, obj_name, x, y, quiet=True)
        if new_id is None:
            raise RuntimeError("smoke-test: 生成实例失败")
        print(f"  实例: [{new_id}]")

        info = _query_npc_target(game_file, obj_name)
        if info is None:
            raise RuntimeError(f"smoke-test: 对象未找到 {obj_name}")
        # 触发块 = 已验证扁平形态 + 标记写入（同为块内单层语句）
        block = f"""if (id == {new_id} && !instance_exists(obj_dialoguer) && !instance_exists(OBJ_WRITER) && !instance_exists(obj_choicer))
{{
    if (distance_to_object(obj_mainchara) < 50)
    {{
        global.msc = 0;
        global.typer = 5;
        global.facechoice = 0;
        global.faceemotion = 0;
        global.msg[0] = scr_gettext("{text_key}");
        global.msg[1] = "%%%";
        instance_create(0, 0, obj_dialoguer);
        var smokefile = file_text_open_write("{marker_name}");
        file_text_write_string(smokefile, "SMOKE_OK id={new_id} t=" + string(current_time));
        file_text_close(smokefile);
    }}
}}
"""
        step_code = info["step_code"]
        if step_code:
            _append_to_code(game_file, step_code, block)
        else:
            cmd_create_script(game_file, f"gml_Object_{info['obj']}_Step_0", block)
        if info["native"] and info["alarm_code"]:
            _guard_alarm_for_instance(game_file, info["alarm_code"], new_id)

        # ── 3. 传送到目标房（内部名 → 数字 ID；resolve_room 不认内部名）──
        room_id = _room_id_by_name(game_file, room_name)
        cmd_ini_set(save_dir, "General", "Room", room_id)

        # ── 4. 清理旧标记 + 启动 + 轮询 ──
        marker.unlink(missing_ok=True)
        print(f"  启动游戏 (steam://run/391540)... 轮询标记 ≤{timeout}s（按键模式: {send_keys}）")
        _sp.run(["open", "steam://run/391540"], check=False)
        start = _time.time()
        key_count = 0
        while _time.time() - start < timeout:
            _time.sleep(2)
            if send_keys == "osascript" and key_count < 40:
                _sp.run(["osascript", "-e",
                         'tell application "System Events" to keystroke "z"'],
                        capture_output=True)
                key_count += 1
            if marker.exists():
                passed = True
                try:
                    marker_content = marker.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    marker_content = "(读取失败)"
                break
        if not passed:
            # 多候选探测：file_text_open_write 的落点可能是存档目录或游戏目录
            for cand in (game_file.parent / marker_name,
                         Path.cwd() / marker_name,
                         Path.home() / marker_name):
                if cand.exists():
                    passed = True
                    marker = cand
                    try:
                        marker_content = cand.read_text(encoding="utf-8", errors="replace")
                    except OSError:
                        marker_content = "(读取失败)"
                    print(f"  ℹ️  标记出现在备选位置: {cand}")
                    break
    finally:
        # ── 5. 全量恢复（任何路径：PASS/FAIL/异常 都恢复）──
        state.COMMIT_ACTIVE = False
        _sp.run(["pkill", "-x", "Mac_Runner"], capture_output=True)
        _time.sleep(2)
        shutil.copy2(str(b_game), str(game_file))
        f0_ok = ini_ok = True
        if b_f0.exists():
            shutil.copy2(str(b_f0), str(f0))
            f0_ok = (_md5_file(f0) == _md5_file(b_f0))
        if b_ini.exists():
            shutil.copy2(str(b_ini), str(ini))
            ini_ok = (_md5_file(ini) == _md5_file(b_ini))
        marker.unlink(missing_ok=True)
        md5_after = _md5_file(game_file)
        restored = (md5_after == md5_before and f0_ok and ini_ok)
        print(f"  恢复: game.ios {'✅ MD5 一致' if md5_after == md5_before else '❌ 不一致'}"
              f" | file0 {'✅' if f0_ok else '❌'} | ini {'✅' if ini_ok else '❌'}")
        if restored:
            # 恢复成功 → 清理本轮快照与 .bak 时间戳备份；失败则保留供取证
            b_game.unlink(missing_ok=True)
            b_f0.unlink(missing_ok=True)
            b_ini.unlink(missing_ok=True)
            for p_ in game_file.parent.glob("game.ios.bak.*"):
                if p_.name not in pre_baks:
                    p_.unlink(missing_ok=True)

    elapsed = _time.time() - start if 'start' in dir() else -1
    if passed:
        print(f"\n✅ smoke-test PASS（{elapsed:.0f}s，验证级别: in-game）")
        print(f"   标记内容: {marker_content}")
        print("   触发块在游戏内真实执行（标记文件由游戏写出）")
    else:
        print(f"\n❌ smoke-test FAIL（{elapsed:.0f}s 内未出现标记）")
        print("   排查: 1) 游戏是否停在开场/菜单等 Z（external 模式无人按键——无人值守建议 --keys osascript）")
        print("         2) 游戏窗口是否失焦（失焦时 Undertale 会暂停）")
        print("         3) 玩家出生点与 NPC 距离 >50px?")
        print("   （环境已恢复原状，可重跑）")
    return passed
_DIFF_SNAPSHOT_CSX = """
// O7: 结构签名 dump（只读）——房间摘要 + 代码条目长度 + 计数
ScriptMessage("LASTOBJ:" + Data.GeneralInfo.LastObj);
ScriptMessage("STRGCOUNT:" + Data.Strings.Count);
ScriptMessage("CODECOUNT:" + Data.Code.Count);
ScriptMessage("SPRCOUNT:" + Data.Sprites.Count);
ScriptMessage("TEXCOUNT:" + Data.EmbeddedTextures.Count);
ScriptMessage("VARS:" + Data.Variables.Count);
foreach (var v in Data.Variables)
    if (v.Name != null && (v.Name.Content.IndexOf("deterline", StringComparison.OrdinalIgnoreCase) >= 0))
        ScriptMessage("VARDETERLINE:" + v.Name.Content + ":" + v.NameStringID + ":" + v.Occurrences);
foreach (var room in Data.Rooms) {{
    string bgs = "";
    for (int i = 0; i < room.Backgrounds.Count; i++)
        if (room.Backgrounds[i].Enabled && room.Backgrounds[i].BackgroundDefinition != null)
            bgs += room.Backgrounds[i].BackgroundDefinition.Name.Content + ",";
    ScriptMessage("ROOM|" + room.Name.Content + "|" + room.Width + "x" + room.Height
        + "|inst=" + room.GameObjects.Count + "|tiles=" + room.Tiles.Count
        + "|bg=" + bgs);
}}
foreach (var c in Data.Code)
    ScriptMessage("CODE|" + c.Name.Content + "|" + c.Instructions.Count);
"""


def _dump_structure_signature(game_file: Path) -> dict:
    """单次只读 UTMT 遍历，输出结构签名（供快照 diff）。"""
    out = _run_utmt(_DIFF_SNAPSHOT_CSX, game_file, save=False)
    sig = {"rooms": {}, "code": {}, "counts": {}, "vardeterline": []}
    for line in _parse_msg(out):
        if line.startswith("ROOM|"):
            _, name, size, inst, tiles, bg = line.split("|", 5)
            sig["rooms"][name] = (size, inst, tiles, bg)
        elif line.startswith("CODE|"):
            _, name, n = line.split("|", 2)
            sig["code"][name] = int(n)
        elif line.startswith(("LASTOBJ:", "STRGCOUNT:", "CODECOUNT:", "SPRCOUNT:", "TEXCOUNT:", "VARS:")):
            k, v = line.split(":", 1)
            sig["counts"][k] = int(v)
        elif line.startswith("VARDETERLINE:"):
            sig["vardeterline"].append(line[len("VARDETERLINE:"):])
    return sig


def cmd_diff_snapshots(file_a: Path, file_b: Path) -> None:
    """O7 snapshot-diff：两份 game.ios 的结构化差异报告（实验隔离/泄漏取证）。

    对比维度：LastObj、各房间（尺寸/实例数/Tile 数/启用背景层）、代码条目
    （增删/指令数变化）、字符串/精灵/纹理/变量计数、deterline* 变量。
    只读，两次 UTMT 遍历。
    """
    for f in (file_a, file_b):
        if not f.exists():
            raise NotFoundError(f"文件不存在: {f}")
    print(f"--- diff-snapshots ---\n  A={file_a}\n  B={file_b}")
    a = _dump_structure_signature(file_a)
    b = _dump_structure_signature(file_b)
    diffs = 0

    for k in sorted(set(a["counts"]) | set(b["counts"])):
        va, vb = a["counts"].get(k), b["counts"].get(k)
        if va != vb:
            print(f"  COUNT {k}: {va} → {vb}")
            diffs += 1
    if a["vardeterline"] != b["vardeterline"]:
        print(f"  VARDETERLINE: {a['vardeterline']} → {b['vardeterline']}")
        diffs += 1

    rooms_a, rooms_b = a["rooms"], b["rooms"]
    for name in sorted(set(rooms_a) - set(rooms_b)):
        print(f"  ROOM 移除: {name}"); diffs += 1
    for name in sorted(set(rooms_b) - set(rooms_a)):
        print(f"  ROOM 新增: {name}"); diffs += 1
    for name in sorted(set(rooms_a) & set(rooms_b)):
        if rooms_a[name] != rooms_b[name]:
            print(f"  ROOM 变化: {name}: {rooms_a[name]} → {rooms_b[name]}")
            diffs += 1

    code_a, code_b = a["code"], b["code"]
    for name in sorted(set(code_a) - set(code_b)):
        print(f"  CODE 移除: {name}"); diffs += 1
    for name in sorted(set(code_b) - set(code_a)):
        print(f"  CODE 新增: {name} (instr={code_b[name]})"); diffs += 1
    for name in sorted(set(code_a) & set(code_b)):
        if code_a[name] != code_b[name]:
            print(f"  CODE 变化: {name}: instr {code_a[name]} → {code_b[name]}")
            diffs += 1

    if diffs == 0:
        print("✅ 结构完全一致（0 差异）")
    else:
        print(f"\n⚠️ 共 {diffs} 处结构差异")
    return diffs


def cmd_verify_code(game_file: Path, code_name: str, show_asm: bool = False) -> bool:
    """V1（收窄版）：对指定代码条目做字节级体检并输出结构化指纹。

    产出（Agent 可读）：
      FINGERPRINT: name=... instr=N branches=B push=P pop=P call=C exit=E
      VARREF: WRITE <var> ×k / READ <var> ×k        （从反汇编文本解析）
      ROUNDTRIP: instr N -> N2 text_identical=true/false
      ASM_DIFF: lines=k first=[...]                  （仅往返不一致时）
      OK: roundtrip stable / WARN: 往返不稳定...

    语义：roundtrip 不一致说明"反编译→重编译"在该条目上不稳定（域F 死代码
    事故的怀疑层），此时返回 False（CLI 退出码 1）；VARREF 写分布是活/死语料
    比对的原料（W3 提供标签）。完整反汇编文本用 --asm 查看。全程只读
    （内存内 Import，不落盘）。
    """
    esc = _csx_escape(code_name)
    csx = f"""
string name = "{esc}";
var code = Data.Code.ByName(name);
if (code == null) {{
    ScriptMessage("ERROR: code not found: " + name);
    return;
}}
name = code.Name.Content;
var locals = Data.CodeLocals.ByName(name);
if (locals == null) locals = new UndertaleCodeLocals();
string asm1 = code.Disassemble(Data.Variables, locals, true);

int branches = 0, push = 0, pop = 0, call = 0, exitI = 0;
foreach (var instr in code.Instructions) {{
    if (instr.Kind == UndertaleInstruction.Opcode.B || instr.Kind == UndertaleInstruction.Opcode.Bt
        || instr.Kind == UndertaleInstruction.Opcode.Bf) branches++;
    else if (instr.Kind == UndertaleInstruction.Opcode.Pop) pop++;
    else if (instr.Kind == UndertaleInstruction.Opcode.Call) call++;
    else if (instr.Kind == UndertaleInstruction.Opcode.Exit || instr.Kind == UndertaleInstruction.Opcode.Ret) exitI++;
    else if (instr.Kind == UndertaleInstruction.Opcode.Push || instr.Kind == UndertaleInstruction.Opcode.PushI
        || instr.Kind == UndertaleInstruction.Opcode.PushLoc || instr.Kind == UndertaleInstruction.Opcode.PushGlb
        || instr.Kind == UndertaleInstruction.Opcode.PushBltn) push++;
}}
ScriptMessage("FINGERPRINT: name=" + name + " instr=" + code.Instructions.Count
    + " branches=" + branches + " push=" + push + " pop=" + pop + " call=" + call + " exit=" + exitI);
foreach (var line in asm1.Split(new[] {{ "\\r\\n", "\\r", "\\n" }}, System.StringSplitOptions.None)) {{
    string t = line.Trim();
    if (t.Length > 0) ScriptMessage("ASM| " + t);
}}

// 内存内往返：反编译 → 重编译 → 反汇编，比对稳定性
string gml = GetDecompiledText(code);
int n1 = code.Instructions.Count;
var grp = new CodeImportGroup(Data) {{ MainThreadAction = MainThreadAction }};
grp.QueueReplace(code, gml);
grp.Import();
var code2 = Data.Code.ByName(name);
var locals2 = Data.CodeLocals.ByName(name) ?? locals;
string asm2 = code2.Disassemble(Data.Variables, locals2, true);
int n2 = code2.Instructions.Count;
bool identical = (asm1 == asm2);
ScriptMessage("ROUNDTRIP: instr " + n1 + " -> " + n2 + " text_identical=" + (identical ? "true" : "false"));
if (!identical) {{
    string[] l1 = asm1.Split(new[] {{ "\\r\\n", "\\r", "\\n" }}, System.StringSplitOptions.None);
    string[] l2 = asm2.Split(new[] {{ "\\r\\n", "\\r", "\\n" }}, System.StringSplitOptions.None);
    int diffLines = 0; string first = "";
    for (int i = 0; i < System.Math.Max(l1.Length, l2.Length); i++) {{
        string a = i < l1.Length ? l1[i].Trim() : "<eof>";
        string b = i < l2.Length ? l2[i].Trim() : "<eof>";
        if (a != b) {{ diffLines++; if (diffLines == 1) first = a + "  =>  " + b; }}
    }}
    ScriptMessage("ASM_DIFF: lines=" + diffLines + " first=[" + first + "]");
    ScriptMessage("WARN: 往返不稳定——该条目的反编译/重编译不可信（对照 AUDIT_2026-11-07 域F）");
}} else {{
    ScriptMessage("OK: roundtrip stable");
}}
"""
    out = _run_utmt(csx, game_file, save=False)
    # Python 侧解析：FINGERPRINT/ROUNDTRIP 直通；ASM 行聚合为变量读写普查
    stable = None
    import collections
    writes = collections.Counter()
    reads = collections.Counter()
    for line in _parse_msg(out):
        if line.startswith("ASM| "):
            t = line[5:].strip()
            if show_asm:
                print(line)
            parts = t.split()
            if t.startswith("pop.") and len(parts) >= 2:
                var = parts[-1].split(".", 1)[-1]  # 去掉 self./global. 前缀
                writes[var] += 1
            elif t.startswith("push") and len(parts) >= 2 and "." in parts[-1]:
                var = parts[-1].split(".", 1)[-1]
                # 过滤噪声：数字字面量与字符串常量尾巴（如 ogg"@2615）
                if ('"' not in var and "@" not in var
                        and var.lstrip("-").replace(".", "").isdigit() is False):
                    reads[var] += 1
        elif line.startswith(("FINGERPRINT:", "VARREF:", "ASM_DIFF:", "ERROR:")):
            print(line)
        elif line.startswith("ROUNDTRIP:"):
            print(line)
            stable = "text_identical=true" in line
        elif line.startswith("WARN:"):
            print(line)
        elif line.startswith("OK:"):
            print(line)
    for var, n in sorted(writes.items()):
        print(f"VARREF: WRITE {var} x{n}")
    for var, n in sorted(reads.items()):
        print(f"VARREF: READ {var} x{n}")
    if writes or reads:
        print(f"VERIFY_CODE_SUMMARY: writes={sum(writes.values())} reads={sum(reads.values())}")
    return stable is not False


def cmd_verify_instances(game_file: Path, fix: bool = False) -> None:
    """Check every room for instances with invalid IDs (0 or duplicate).

    Such instances break GameMaker's per-instance variable tables: the Create
    event's writes (e.g. phase, image_xscale) don't land on the colliding
    instance, causing crashes (reading other.<var> unset) and visual leaks
    (unscaled solids).  By default reports; with --fix, reassigns unique IDs
    to ID=0/duplicate instances.  Null-ObjectDefinition / Nonexistent instances
    are reported only (cannot be auto-fixed).
    """
    fix_csx = "true" if fix else "false"
    csx = f'''
// Verify / fix room instance IDs across all rooms (experiment 19)
ulong maxUsed = 0;
var used = new System.Collections.Generic.HashSet<uint>();
foreach (var room in Data.Rooms)
{{
    foreach (var g in room.GameObjects)
    {{
        if (g.InstanceID != 0)
        {{
            used.Add(g.InstanceID);
            if (g.InstanceID > maxUsed) maxUsed = g.InstanceID;
        }}
    }}
}}
uint nextId = (uint)(System.Math.Max((long)Data.GeneralInfo.LastObj, (long)maxUsed) + 1);

int badZero = 0, badDup = 0, badNull = 0, badNonexist = 0, fixedCnt = 0;
var local = new System.Collections.Generic.HashSet<uint>();
foreach (var room in Data.Rooms)
{{
    local.Clear();
    string roomName = room.Name?.Content ?? "(unnamed)";
    foreach (var g in room.GameObjects)
    {{
        string objName = g.ObjectDefinition?.Name?.Content ?? "(null)";
        bool idZero = (g.InstanceID == 0);
        bool idDup = (!idZero && !local.Add(g.InstanceID));
        bool nullObj = (g.ObjectDefinition == null);
        bool nonexist = g.Nonexistent;
        if (idZero) badZero++;
        if (idDup) badDup++;
        if (nullObj) badNull++;
        if (nonexist) badNonexist++;
        if (idZero || idDup || nullObj || nonexist)
        {{
            ScriptMessage("BAD_INSTANCE: room='" + roomName + "' obj=" + objName + " id=" + g.InstanceID + " x=" + g.X + " y=" + g.Y + " zero=" + idZero + " dup=" + idDup + " null=" + nullObj + " nonexist=" + nonexist);
        }}
        if ({( "true" if fix else "false" )} && (idZero || idDup))
        {{
            g.InstanceID = nextId;
            nextId++;
            fixedCnt++;
        }}
    }}
}}
if ({( "true" if fix else "false" )})
{{
    Data.GeneralInfo.LastObj = nextId - 1;
}}
int bad = badZero + badDup + badNull + badNonexist;
ScriptMessage("VERIFY_INSTANCES:bad=" + bad + " zero=" + badZero + " dup=" + badDup + " null=" + badNull + " nonexist=" + badNonexist + " fixed=" + fixedCnt);
'''
    out = _run_utmt(csx, game_file, save=fix)
    info = _parse_instance_audit(out)
    if info["bad"] is None:
        print("错误: 无法解析 verify-instances 结果", file=sys.stderr)
        return
    for line in info["bad_lines"]:
        print(f"  ⚠️  {line}")
    if info["bad"] == 0:
        print("✅ verify-instances: 无异常实例（ID=0/重复/空对象/Nonexistent 均为 0）")
    else:
        fix_txt = f"，已修复 ID 类 {info['fixed']} 个（null/Nonexistent 仅报告，无法自动修）" if fix \
            else "（用 --fix 自动为 ID=0/重复实例分配唯一 ID）"
        print(f"⚠️ verify-instances: 异常 {info['bad']} 个 "
              f"(zero={info['zero']} dup={info['dup']} null={info['null']} "
              f"nonexist={info['nonexist']}){fix_txt}")


def cmd_npc_dialogue(game_file: Path, room_name: str, obj_name: str, x: int, y: int,
                     text_key: str, text: str, face: int = 0, emotion: int = 0,
                     once: bool = False, range_: int = 50) -> None:
    """One-shot safe NPC dialogue setup.

    1. Adds the dialogue to textdata_en
    2. Spawns the object instance
    3. Injects the verified flat distance-trigger block (AUDIT_2026-11-07/域F:
       state-gated trigger shapes are in-game dead code in this UTMT env —
       the generator emits only the flat verified form; no movement lock)
    4. If the object inherits a native interaction system, also guards Alarm_0
       with `if (id == N) exit;` to prevent the default dialogue from overlapping.

    range_ = trigger distance in pixels (default 50).
    """
    print("--- npc-dialogue ---")
    _validate_ascii_text(text, f"对话 '{text_key}'")
    _validate_facechoice(face)
    if "\\C" in text:
        raise ValidationError(
            f"对话 '{text_key}' 含选择框标记 \\C，但 npc-dialogue 只支持纯文本对话。\n"
            f"请改用 npc-choice 命令生成带 YES/NO 选择的分支对话。"
        )

    print("Step 1/4: 添加对话条目...")
    cmd_textdata_add(game_file, text_key, text, face=face, emotion=emotion)

    print("Step 2/4: 检查对象继承链...")
    info = _query_npc_target(game_file, obj_name)
    if info is None:
        raise NotFoundError(f"对象未找到: {obj_name}")
    native = info["native"]
    if once:
        print("  🔒 单次触发模式 → 已验证扁平触发块 + 触发后 NPC 自毁（说完即从房间消失）")
    elif native:
        print(f"  ⚠️  {info['obj']} 继承原生交互系统 → 已验证扁平触发块 + Alarm_0 守卫")
    else:
        print(f"  ✅  {info['obj']} 为普通对象 → 已验证扁平触发块")
    print("  ℹ️  v2.3.0 行为说明：触发后不再锁移动（状态机在当前 UTMT 环境下产生游戏内"
          "死代码，见 AUDIT_2026-11-07/域F）；可重复模式下关闭对话后若仍在范围内会再次弹出，走出范围即停止")

    print("Step 3/4: 生成对象实例...")
    new_id = _spawn_obj_internal(game_file, room_name, obj_name, x, y, quiet=True)
    if new_id is None:
        raise RuntimeError("生成对象失败（未获取到实例 ID）")
    print(f"  ✅ 已生成实例 [{new_id}]")

    print("Step 4/4: 注入触发代码...")
    _ensure_var_initialized(game_file, info["obj"], "deterline_state")
    block = _build_npc_step_block(new_id, text_key, face, emotion, native, once=once, range_=range_)
    step_code = info["step_code"]
    if step_code:
        _append_to_code(game_file, step_code, block)
        print(f"  ✅ 已追加到 Step 事件: {step_code}")
    else:
        create_name = f"gml_Object_{info['obj']}_Step_0"
        cmd_create_script(game_file, create_name, block)
        print(f"  ✅ 已创建 Step 事件: {create_name}")

    if native and info["alarm_code"]:
        _guard_alarm_for_instance(game_file, info["alarm_code"], new_id)
    if once:
        print(f"  ✅ 完成: {info['obj']} [{new_id}] 靠近 (<{range_}px) 说一次 '{text_key}'（触发后 NPC 自毁消失）")
    else:
        print(f"  ✅ 完成: {info['obj']} [{new_id}] 靠近 (<{range_}px) 说 '{text_key}'（可重复；关对话后仍在范围内会再触发，走出范围停止）")


def cmd_npc_choice(game_file: Path, room_name: str, obj_name: str, x: int, y: int,
                   choice_key: str, choice_text: str,
                   yes_key: str | None = None, yes_text: str | None = None,
                   no_key: str | None = None, no_text: str | None = None,
                   face: int = 0, emotion: int = 0, range_: int = 50,
                   goto_room: str | None = None, item_id: int | None = None,
                   repeat: bool = False) -> None:
    """One-shot safe NPC dialogue with a YES/NO choice (`\\C` box).

    Uses the in-game-verified flat trigger shape (v2.3.0, 2026-11-07 audit):
      1. Adds up to 3 textdata entries (choice / YES follow-up / NO follow-up)
      2. Spawns the object instance
      3. Injects the choice state machine into the object's Step event:
         trigger → `\\C` box → YES branch (optional follow-up text, item, teleport)
         / NO branch (follow-up text). Branch texts replace msg[0] with non-\\C
         text, which is what prevents the choice box from re-popping (scr_msgup
         re-copies global.msg[] 2 frames after the choice).
      4. Guards Alarm_0 for native-readable objects (like npc-dialogue).

    Repeatable by default (dialogue re-opens while in range; walk out of
    `--range` to stop); once=True self-destructs the NPC after triggering.
    repeat=True keeps the NPC (flat block, no state machine — v2.3.0).
    """
    print("--- npc-choice ---")
    # ── validation ──────────────────────────────────────────────
    if "\\C" not in choice_text:
        raise ValidationError(
            f"选择文本 '{choice_key}' 不含 \\C 标记（YES/NO 选择框不会出现）。\n"
            f"格式: \"* 提问& &         Yes         No      \\C \""
        )
    line_count = choice_text.count("&") + 1
    if line_count > 3:
        raise ValidationError(
            f"选择文本 '{choice_key}' 共 {line_count} 行（含选项行），超过 3 行限制，"
            f"选项会溢出对话框。\n格式: \"* 提问& &         Yes         No      \\C \""
        )
    if no_key is None or no_text is None:
        raise ValidationError("--no-text-key 和 --no-text 是必需的（NO 分支的回应文本）")
    if yes_key is None:
        # ⚠️ YES 分支必须替换 msg[0]（否则 scr_msgup 2 帧后重拷 \C 文本 → 选择框无限
        # 重弹；带 --item 时还会无限刷物品）。未提供 yes 文本时自动生成一条确认语。
        yes_key = f"{choice_key}_yes"
        yes_text = "* Okay./%%"
        print(f"  ℹ️  未提供 --yes-text，自动生成 YES 分支确认文本 '{yes_key}'")
    _validate_ascii_text(choice_text, f"选择文本 '{choice_key}'")
    for key, val, label in [(yes_key, yes_text, "YES 分支文本"),
                            (no_key, no_text, "NO 分支文本")]:
        if val is not None:
            _validate_ascii_text(val, f"{label} '{key}'")
            if "\\C" in val:
                raise ValidationError(
                    f"{label} '{key}' 含 \\C 标记——分支文本必须是不含选择框的纯文本，"
                    f"否则选择框会循环重弹。"
                )
    _validate_facechoice(face)
    if item_id is not None and item_id not in ITEMS:
        print(f"警告: 物品 ID {item_id} 不在已知物品表（{min(ITEMS)}-{max(ITEMS)}），仍将注入 scr_itemget", file=sys.stderr)

    # ── resolve teleport target (room name → ID or constant) ───
    goto_gml = None
    if goto_room:
        goto_gml = resolve_room(goto_room)  # numeric ID string works with room_goto()

    # ── execute ─────────────────────────────────────────────────
    print("Step 1/5: 添加对话条目...")
    cmd_textdata_add(game_file, choice_key, choice_text, face=face, emotion=emotion)
    if yes_key and yes_text:
        cmd_textdata_add(game_file, yes_key, yes_text, face=face, emotion=emotion)
    if no_key:
        cmd_textdata_add(game_file, no_key, no_text, face=face, emotion=emotion)

    print("Step 2/5: 检查对象继承链...")
    info = _query_npc_target(game_file, obj_name)
    if info is None:
        raise NotFoundError(f"对象未找到: {obj_name}")
    native = info["native"]
    if native:
        print(f"  ⚠️  {info['obj']} 继承原生交互系统 → 自动加 Alarm_0 守卫")

    print("Step 3/5: 生成对象实例...")
    new_id = _spawn_obj_internal(game_file, room_name, obj_name, x, y, quiet=True)
    if new_id is None:
        raise RuntimeError("生成对象失败（未获取到实例 ID）")
    print(f"  ✅ 已生成实例 [{new_id}]")

    print("Step 4/5: 注入选择触发块（已验证扁平形态）...")
    _ensure_var_initialized(game_file, info["obj"], "deterline_state")  # 保留兼容，非触发依赖
    block = _build_npc_choice_block(
        new_id, choice_key, yes_key, no_key, face, emotion,
        range_=range_, goto_room=goto_gml, item_id=item_id, repeat=repeat,
    )
    step_code = info["step_code"]
    if step_code:
        _append_to_code(game_file, step_code, block)
        print(f"  ✅ 已追加到 Step 事件: {step_code}")
    else:
        create_name = f"gml_Object_{info['obj']}_Step_0"
        cmd_create_script(game_file, create_name, block)
        print(f"  ✅ 已创建 Step 事件: {create_name}")

    print("Step 5/5: 守卫原生交互...")
    if native and info["alarm_code"]:
        _guard_alarm_for_instance(game_file, info["alarm_code"], new_id)

    extra = []
    if yes_key and yes_text:
        extra.append(f"YES→'{yes_key}'")
    if item_id is not None:
        extra.append(f"给物品 {ITEMS.get(item_id, item_id)}")
    if goto_room and goto_gml is not None:
        extra.append(f"传送→{format_room(goto_gml)}")
    if not extra:
        extra.append("YES→关闭对话")
    if repeat:
        extra.append("走开可再触发")
    else:
        extra.append("单次触发")
    print(f"  ✅ 完成: {info['obj']} [{new_id}] 靠近 (<{range_}px) 弹 '{choice_key}'（{'，'.join(extra)}）")


def cmd_guard_npc_alarm(game_file: Path, obj_name: str, instance_id: int,
                        text_key: str | None = None) -> None:
    """Fix an existing NPC whose injected myinteract trigger overlaps with the
    native readable dialogue.

    Automates the manual two-step fix:
    1. Prepends `if (id == N) exit;` to the effective Alarm_0 entry (idempotent).
    2. If --text-key is given, rewrites the object's Step trigger to the flag-state
       machine (removing the myinteract conflict).
    """
    print("--- guard-npc-alarm ---")
    info = _query_npc_target(game_file, obj_name)
    if info is None:
        raise NotFoundError(f"对象未找到: {obj_name}")

    if not info["alarm_code"]:
        print("警告: 未找到 Alarm_0 代码条目，无法加守卫", file=sys.stderr)
    else:
        _guard_alarm_for_instance(game_file, info["alarm_code"], instance_id)

    if text_key:
        print(f"→ 改写 Step 触发为 flag 状态机 (实例 {instance_id}, key {text_key})...")
        _ensure_var_initialized(game_file, info["obj"], "deterline_state")
        block = _build_npc_step_block(instance_id, text_key, 0, 0, native=True)
        step_code = info["step_code"]
        if step_code:
            _replace_step_code(game_file, step_code, instance_id, block)
            print(f"  ✅ 已改写: {step_code}")
        else:
            create_name = f"gml_Object_{info['obj']}_Step_0"
            cmd_create_script(game_file, create_name, block)
            print(f"  ✅ 已创建: {create_name}")
    print("  ✅ 完成")


# ============================================================
# P4-2 Room Commands (create, info, edit, background, assets)
# ============================================================

def _resolve_room_csx(esc_room: str) -> str:
    """Return CSX snippet that resolves a room name to a 'room' variable.
    Tries exact ByName first, then fuzzy search.
    """
    return f'''
var room = Data.Rooms.ByName("{esc_room}");
if (room == null) {{
    for (int r = 0; r < Data.Rooms.Count; r++) {{
        if (Data.Rooms[r].Name.Content.IndexOf("{esc_room}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            room = Data.Rooms[r];
            break;
        }}
    }}
}}
if (room == null) {{
    ScriptMessage("ERROR: Room not found: {esc_room}");
    return;
}}
'''


def cmd_room_info(game_file: Path, room_name: str) -> None:
    """Show detailed properties of a room."""
    esc = _csx_escape(room_name)
    csx = f'''
var room = Data.Rooms.ByName("{esc}");
if (room == null) {{
    for (int r = 0; r < Data.Rooms.Count; r++) {{
        if (Data.Rooms[r].Name.Content.IndexOf("{esc}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            room = Data.Rooms[r];
            break;
        }}
    }}
}}
if (room == null) {{
    ScriptMessage("ERROR: Room not found: {esc}");
    return;
}}

ScriptMessage("=== Room Info ===");
ScriptMessage("Name:       " + room.Name.Content);
ScriptMessage("Size:       " + room.Width + " x " + room.Height);
ScriptMessage("Speed:      " + room.Speed);
ScriptMessage("Caption:    " + (room.Caption?.Content ?? ""));
ScriptMessage("Persistent: " + room.Persistent);
ScriptMessage("Flags:      " + (uint)room.Flags);
ScriptMessage("BG Color:   " + room.BackgroundColor.ToString("X8"));
ScriptMessage("DrawBGColor: " + room.DrawBackgroundColor);

for (int i = 0; i < (room.Backgrounds?.Count ?? 0); i++) {{
    var bg = room.Backgrounds[i];
    string bgName = bg?.BackgroundDefinition?.Name?.Content ?? "(none)";
    ScriptMessage("  BG[" + i + "]: enabled=" + bg.Enabled + " bg=" + bgName + " fg=" + bg.Foreground+" speed=("+bg.SpeedX+","+bg.SpeedY+") tiled=("+bg.TiledHorizontally+","+bg.TiledVertically+")");
}}

for (int i = 0; i < (room.Views?.Count ?? 0); i++) {{
    var v = room.Views[i];
    if (!v.Enabled) continue;
    string follow = "(none)";
    if (v.ObjectId != null) {{
        try {{
            follow = v.ObjectId.Name?.Content ?? "(unnamed)";
        }} catch {{
            follow = "(unknown)";
        }}
    }}
    if (follow == "") follow = "(none)";
    ScriptMessage("  View[" + i + "]: (" + v.ViewX + "," + v.ViewY + ") " + v.ViewWidth + "x" + v.ViewHeight + " port=" + v.PortWidth + "x" + v.PortHeight + " follow=" + follow);
}}

ScriptMessage("Objects:    " + (room.GameObjects?.Count ?? 0));
ScriptMessage("Tiles:      " + (room.Tiles?.Count ?? 0));

if (room.GameObjects != null) {{
    var _seenIds2 = new System.Collections.Generic.HashSet<uint>();
    foreach (var go in room.GameObjects) {{
        string objName = go.ObjectDefinition?.Name?.Content ?? "(unknown)";
        string idMark = "";
        if (go.ObjectDefinition != null && (go.InstanceID == 0 || !_seenIds2.Add(go.InstanceID)))
            idMark = "  ⚠️ ID=0/重复";
        ScriptMessage("  [" + go.InstanceID + "] " + objName + " at (" + go.X + "," + go.Y + ")" + idMark);
    }}
}}

// Check RoomOrder
bool inOrder = false;
if (Data.GeneralInfo.RoomOrder != null) {{
    foreach (var entry in Data.GeneralInfo.RoomOrder) {{
        if (entry?.Resource?.Name?.Content == room.Name.Content) {{
            inOrder = true;
            break;
        }}
    }}
}}
ScriptMessage("In RoomOrder: " + inOrder);
'''
    out = _run_utmt(csx, game_file, save=False)
    for line in _parse_msg(out):
        print(line)


def cmd_create_room(game_file: Path, room_name: str,
                    width: int | None = None, height: int | None = None,
                    speed: int | None = None, caption: str = "",
                    bg_color: str = "000000") -> None:
    """Create a new room with default View (follows obj_mainchara).
    IMPORTANT: View is fixed at 320x240 (port 640x480, 2x scale).
    This is Undertale's standard — View=640x480 causes perspective to break.
    Room dimensions default to 640x480 (larger than View = scroll works).
    NOTE: This command is DEPRECATED — creating new room indices is FORBIDDEN.
    The game runtime cannot recognize added rooms and will teleport the player
    into the wrong room (annoying dog). Use existing rooms from ROOMS_GUIDE.md."""
    raise DeterlineError(
        "禁止新建房间序号（`create-room` 已废弃）："
        "游戏运行时无法识别新增房间，会导致传送进错房间、遇神烦狗。"
        "只能改造已有房间——请查阅 ROOMS_GUIDE.md 选房，"
        "用 set-room-prop / set-room-view / gml-bg / Tile 编辑改造。"
    )
    if width is None: width = 640
    if height is None: height = 480
    if speed is None: speed = 30
    # Use standard Undertale View size (320x240, port 640x480)
    view_w = 320
    view_h = 240
    esc_name = _csx_escape(room_name)
    esc_cap = _csx_escape(caption)
    # Parse bg_color: hex RGB -> C# hex literal string
    bg_color = bg_color.lstrip("#")
    try:
        rgb = int(bg_color, 16)
    except ValueError:
        print(f"错误: 无效的 bg-color: {bg_color}", file=sys.stderr)
        return
    argb_hex = f"0x{0xFF000000 | (rgb & 0xFFFFFF):08X}"

    csx = f'''
var existing = Data.Rooms.ByName("{esc_name}");
if (existing != null) {{
    ScriptMessage("ERROR: Room already exists: {esc_name}");
    return;
}}

var room = new UndertaleRoom();
room.Name = Data.Strings.MakeString("{esc_name}");
room.Caption = Data.Strings.MakeString("{esc_cap}");
room.Width = {width};
room.Height = {height};
room.Speed = {speed};
room.Flags = UndertaleRoom.RoomEntryFlags.EnableViews | UndertaleRoom.RoomEntryFlags.ClearViewBackground;
room.DrawBackgroundColor = true;
room.BackgroundColor = {argb_hex};

// Disable all 8 default backgrounds
for (int i = 0; i < 8; i++) {{
    room.Backgrounds[i].Enabled = false;
}}

// Configure View 0 (camera follow)
room.Views[0].Enabled = true;
room.Views[0].ViewX = 0; room.Views[0].ViewY = 0;
room.Views[0].ViewWidth = {view_w}; room.Views[0].ViewHeight = {view_h};
room.Views[0].PortX = 0; room.Views[0].PortY = 0;
room.Views[0].PortWidth = {view_w * 2}; room.Views[0].PortHeight = {view_h * 2};
room.Views[0].BorderX = 32; room.Views[0].BorderY = 32;

var playerObj = Data.GameObjects.ByName("obj_mainchara");
if (playerObj != null) {{
    room.Views[0].ObjectId = playerObj;
}}

// Add to data
Data.Rooms.Add(room);
Data.GeneralInfo.RoomOrder.Add(new UndertaleResourceById<UndertaleRoom, UndertaleChunkROOM>() {{ Resource = room }});

string followName = playerObj?.Name?.Content ?? "(none)";
ScriptMessage("OK: Created room '" + room.Name.Content + "' (" + room.Width + "x" + room.Height + ")");
ScriptMessage("  Index: " + (Data.Rooms.Count - 1) + "  View follows: " + followName);
'''
    out = _run_utmt(csx, game_file, save=True)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)
        else:
            print(line)
    _update_rooms_json(room_name, caption or room_name)


def build_set_room_bg_stmts(index: int,
                            enable: bool | None = None,
                            bg_name: str | None = None,
                            foreground: bool | None = None,
                            x: int | None = None, y: int | None = None,
                            speedx: float | None = None, speedy: float | None = None,
                            tiled_h: bool | None = None,
                            tiled_v: bool | None = None,
                            stretch: bool | None = None,
                            keep_bg_color: bool = False) -> str:
    """Build the C# statements for one background layer (pure, testable).

    Only properties explicitly passed (not None) are emitted, so callers must
    pass x/y=None unless the user really asked to move the layer.
    """
    stmts = ""
    if enable is True and not keep_bg_color:
        stmts += "room.DrawBackgroundColor = false;\n"
    if enable is not None:
        stmts += f"room.Backgrounds[{index}].Enabled = " + ("true" if enable else "false") + ";\n"
    if bg_name is not None:
        if bg_name.lower() == "none":
            stmts += f"room.Backgrounds[{index}].BackgroundDefinition = null;\n"
        else:
            esc_bg = _csx_escape(bg_name)
            stmts += f'''
var bgDef = Data.Backgrounds.ByName("{esc_bg}");
if (bgDef != null) {{
    room.Backgrounds[{index}].BackgroundDefinition = bgDef;
}} else {{
    ScriptMessage("WARN: Background not found: {esc_bg}");
}}
'''
    if foreground is not None:
        stmts += f"room.Backgrounds[{index}].Foreground = " + ("true" if foreground else "false") + ";\n"
    if x is not None:
        stmts += f"room.Backgrounds[{index}].X = {x};\n"
    if y is not None:
        stmts += f"room.Backgrounds[{index}].Y = {y};\n"
    if speedx is not None:
        stmts += f"room.Backgrounds[{index}].SpeedX = (int){speedx};\n"
    if speedy is not None:
        stmts += f"room.Backgrounds[{index}].SpeedY = (int){speedy};\n"
    if tiled_h is not None:
        stmts += f"room.Backgrounds[{index}].TiledHorizontally = " + ("true" if tiled_h else "false") + ";\n"
    if tiled_v is not None:
        stmts += f"room.Backgrounds[{index}].TiledVertically = " + ("true" if tiled_v else "false") + ";\n"
    if stretch is not None:
        stmts += f"room.Backgrounds[{index}].Stretch = " + ("true" if stretch else "false") + ";\n"
    return stmts


def cmd_set_room_bg(game_file: Path, room_name: str, index: int = 0,
                    enable: bool | None = None,
                    bg_name: str | None = None,
                    foreground: bool | None = None,
                    x: int | None = None, y: int | None = None,
                    speedx: float | None = None, speedy: float | None = None,
                    tiled_h: bool | None = None,
                    tiled_v: bool | None = None,
                    stretch: bool | None = None,
                    keep_bg_color: bool = False) -> None:
    """Configure a background layer in a room."""
    for warn_line in ROOM_BG_WARNING:
        print(warn_line, file=sys.stderr)
    esc_room = _csx_escape(room_name)
    # Build CSX parts
    parts = []
    parts.append(f'''
var room = Data.Rooms.ByName("{esc_room}");
if (room == null) {{
    for (int r = 0; r < Data.Rooms.Count; r++) {{
        if (Data.Rooms[r].Name.Content.IndexOf("{esc_room}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            room = Data.Rooms[r];
            break;
        }}
    }}
}}
if (room == null) {{
    ScriptMessage("ERROR: Room not found: {esc_room}");
    return;
}}
''')

    stmts = build_set_room_bg_stmts(
        index, enable=enable, bg_name=bg_name, foreground=foreground,
        x=x, y=y, speedx=speedx, speedy=speedy,
        tiled_h=tiled_h, tiled_v=tiled_v, stretch=stretch,
        keep_bg_color=keep_bg_color,
    )

    if not stmts:
        print("错误: 没有指定要修改的属性 (set-room-bg 只接受层属性; "
              "颜色请用 set-room-prop --bg-color)", file=sys.stderr)
        return

    parts.append(stmts)
    parts.append(f'''ScriptMessage("OK: Updated BG[{index}] for " + room.Name.Content);''')
    csx = ''.join(parts)

    out = _run_utmt(csx, game_file, save=True)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("WARN:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)
        else:
            print(line)


def cmd_set_room_prop(game_file: Path, room_name: str,
                      width: int | None = None, height: int | None = None,
                      speed: int | None = None, caption: str | None = None,
                      bg_color: str | None = None,
                      persistent: bool | None = None) -> None:
    """Modify room properties (width, height, speed, etc.)."""
    esc_room = _csx_escape(room_name)
    esc_cap = _csx_escape(caption or "")
    parts = [_resolve_room_csx(esc_room)]

    assigns = ""
    if width is not None:
        # ⚠️ 只改房间尺寸，不动 Views[0]——视角必须保持 320×240/port 640×480
        #（Undertale 标准，改动会破坏 2x 缩放与视角跟随）。改视角用 set-room-view。
        assigns += f"room.Width = {width};\n"
    if height is not None:
        assigns += f"room.Height = {height};\n"
    if speed is not None:
        assigns += f"room.Speed = {speed};\n"
    if caption is not None:
        assigns += f'room.Caption = Data.Strings.MakeString("{esc_cap}");\n'
    if bg_color is not None:
        bg_color = bg_color.lstrip("#")
        try:
            rgb = int(bg_color, 16)
        except ValueError:
            print(f"错误: 无效的 bg-color: {bg_color}", file=sys.stderr)
            return
        argb_hex = f"0x{0xFF000000 | (rgb & 0xFFFFFF):08X}"
        assigns += f"room.BackgroundColor = {argb_hex};\n"
    if persistent is not None:
        assigns += f"room.Persistent = " + ("true" if persistent else "false") + ";\n"

    if not assigns:
        print("错误: 没有指定要修改的属性", file=sys.stderr)
        return

    parts.append(f'''{assigns}
ScriptMessage("OK: Updated properties for " + room.Name.Content);
''')
    csx = ''.join(parts)
    out = _run_utmt(csx, game_file, save=True)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)


def cmd_set_room_view(game_file: Path, room_name: str, index: int = 0,
                      enable: bool | None = None,
                      view_w: int | None = None, view_h: int | None = None,
                      port_w: int | None = None, port_h: int | None = None,
                      follow: str | None = None,
                      border_x: int | None = None,
                      border_y: int | None = None) -> None:
    """Configure a camera view in a room."""
    esc_room = _csx_escape(room_name)
    parts = [_resolve_room_csx(esc_room)]

    assigns = ""
    if enable is not None:
        assigns += f"room.Views[{index}].Enabled = " + ("true" if enable else "false") + ";\n"
    if view_w is not None:
        assigns += f"room.Views[{index}].ViewWidth = {view_w};\n"
    if view_h is not None:
        assigns += f"room.Views[{index}].ViewHeight = {view_h};\n"
    if port_w is not None:
        assigns += f"room.Views[{index}].PortWidth = {port_w};\n"
    if port_h is not None:
        assigns += f"room.Views[{index}].PortHeight = {port_h};\n"
    if follow is not None:
        esc_follow = _csx_escape(follow)
        assigns += f'''
var followObj = Data.GameObjects.ByName("{esc_follow}");
if (followObj != null) {{
    room.Views[{index}].ObjectId = followObj;
}} else {{
    ScriptMessage("WARN: Object not found: {esc_follow}");
}}
'''
    if border_x is not None:
        assigns += f"room.Views[{index}].BorderX = {border_x};\n"
    if border_y is not None:
        assigns += f"room.Views[{index}].BorderY = {border_y};\n"

    if not assigns:
        print("错误: 没有指定要修改的视图属性", file=sys.stderr)
        return

    parts.append(f'''{assigns}
ScriptMessage("OK: Updated View[{index}] for " + room.Name.Content);
''')
    csx = ''.join(parts)
    out = _run_utmt(csx, game_file, save=True)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("WARN:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)


def cmd_list_game_bgs(game_file: Path, filter_str: str = "") -> None:
    """List all background assets available in the game data."""
    esc = _csx_escape(filter_str)
    csx = f'''
int found = 0;
for (int i = 0; i < Data.Backgrounds.Count; i++) {{
    var bg = Data.Backgrounds[i];
    string name = bg.Name?.Content ?? "(unnamed)";
    if ("{esc}".Length == 0 || name.IndexOf("{esc}", StringComparison.OrdinalIgnoreCase) >= 0) {{
        string texName = bg.Texture?.Name?.Content ?? "(no tex)";
        int tw = (int)(bg.Texture?.SourceWidth ?? 0);
        int th = (int)(bg.Texture?.SourceHeight ?? 0);
        ScriptMessage("[" + i + "] " + name + "  tex=" + texName + " (" + tw + "x" + th + ")");
        found++;
    }}
}}
if (found == 0) {{
    ScriptMessage("(no matching backgrounds)");
}} else {{
    ScriptMessage("(total: " + found + " matching, " + Data.Backgrounds.Count + " total)");
}}
'''
    out = _run_utmt(csx, game_file, save=False)
    for line in _parse_msg(out):
        print(line)


def cmd_create_bg_asset(game_file: Path, bg_name: str, png_path: str) -> None:
    """Create a new background asset from a PNG file.
    Injects a new UndertaleBackground + EmbeddedTexture + TexturePageItem.
    """
    esc_bg = _csx_escape(bg_name)
    png_path = str(Path(png_path).expanduser().resolve())
    if not Path(png_path).exists():
        print(f"错误: PNG 文件不存在: {png_path}", file=sys.stderr)
        return

    csx = f'''
string bgName = "{esc_bg}";
string pngPath = @"{_csx_verbatim_escape(png_path)}";

var existing = Data.Backgrounds.ByName(bgName);
if (existing != null) {{
    ScriptMessage("ERROR: Background already exists: " + bgName);
    return;
}}

byte[] pngBytes;
try {{ pngBytes = System.IO.File.ReadAllBytes(pngPath); }}
catch (System.Exception ex) {{ ScriptMessage("ERROR: " + ex.Message); return; }}

var tex = new UndertaleModLib.Models.UndertaleEmbeddedTexture();
tex.Name = Data.Strings.MakeString(bgName + "_tex");
tex.TextureData = new UndertaleModLib.Models.UndertaleEmbeddedTexture.TexData();
tex.TextureData.Image = UndertaleModLib.Util.GMImage.FromPng(pngBytes);
Data.EmbeddedTextures.Add(tex);

var mgk = new ImageMagick.MagickImage(pngBytes);
int imgW = (int)mgk.Width;
int imgH = (int)mgk.Height;
mgk.Dispose();

var item = new UndertaleModLib.Models.UndertaleTexturePageItem();
item.Name = Data.Strings.MakeString(bgName + "_item");
item.SourceX = 0; item.SourceY = 0;
item.SourceWidth = (ushort)imgW; item.SourceHeight = (ushort)imgH;
item.TargetX = 0; item.TargetY = 0;
item.TargetWidth = (ushort)imgW; item.TargetHeight = (ushort)imgH;
item.BoundingWidth = (ushort)imgW; item.BoundingHeight = (ushort)imgH;
item.TexturePage = tex;
Data.TexturePageItems.Add(item);

var bg = new UndertaleModLib.Models.UndertaleBackground();
bg.Name = Data.Strings.MakeString(bgName);
bg.Transparent = false; bg.Smooth = false; bg.Preload = true;
bg.Texture = item;
Data.Backgrounds.Add(bg);

ScriptMessage("OK: Created background '" + bgName + "' (" + imgW + "x" + imgH + ")");
ScriptMessage("  Use: set-room-bg --bg \\"" + bgName + "\\" --index N");
'''
    out = _run_utmt(csx, game_file, save=True)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)


# ============================================================
# Solid-color background + background diagnostics
# ============================================================

def _read_room_size(game_file: Path, room_name: str) -> tuple[int, int]:
    """Return (width, height) of a room via a read-only UTMT pass."""
    esc = _csx_escape(room_name)
    csx = _resolve_room_csx(esc) + '''
ScriptMessage("SIZE:" + room.Width + ":" + room.Height);
'''
    out = _run_utmt(csx, game_file, save=False)
    for line in _parse_msg(out):
        if line.startswith("SIZE:"):
            _, w, h = line.split(":", 2)
            return int(w), int(h)
    raise RuntimeError(f"无法读取房间尺寸: {room_name}")


def _bg_asset_exists(game_file: Path, bg_name: str) -> bool:
    """Return True if a background asset with this name already exists."""
    esc = _csx_escape(bg_name)
    csx = f'''
var bg = Data.Backgrounds.ByName("{esc}");
ScriptMessage("EXISTS:" + (bg != null));
'''
    out = _run_utmt(csx, game_file, save=False)
    for line in _parse_msg(out):
        if line.startswith("EXISTS:"):
            return line.split(":", 1)[1].strip().lower() == "true"
    return False


def _enabled_bg_layers(game_file: Path, room_name: str) -> list[int]:
    """Return the indices of the room's currently-enabled background layers."""
    esc = _csx_escape(room_name)
    csx = _resolve_room_csx(esc) + '''
for (int i = 0; i < (room.Backgrounds?.Count ?? 0); i++) {
    if (room.Backgrounds[i].Enabled) ScriptMessage("ENABLED:" + i);
}
'''
    out = _run_utmt(csx, game_file, save=False)
    res: list[int] = []
    for line in _parse_msg(out):
        if line.startswith("ENABLED:"):
            res.append(int(line.split(":", 1)[1]))
    return res


def _assign_room_bg_layers(game_file: Path, room_name: str, bg_name: str,
                           layers: list[int]) -> None:
    """Point the given room background layers at bg_name (room-data edit)."""
    esc_room = _csx_escape(room_name)
    esc_bg = _csx_escape(bg_name)
    assigns = ""
    for i in layers:
        assigns += f'''
if (room.Backgrounds.Count > {i}) {{
    room.Backgrounds[{i}].BackgroundDefinition = bgDef;
    room.Backgrounds[{i}].Enabled = true;
    room.Backgrounds[{i}].TiledHorizontally = true;
    room.Backgrounds[{i}].TiledVertically = true;
    room.Backgrounds[{i}].X = 0;
    room.Backgrounds[{i}].Y = 0;
    room.Backgrounds[{i}].Foreground = false;
}}
'''
    layer_list = ",".join(str(i) for i in layers)
    csx = _resolve_room_csx(esc_room) + f'''
var bgDef = Data.Backgrounds.ByName("{esc_bg}");
if (bgDef == null) {{ ScriptMessage("ERROR: Background not found: {esc_bg}"); return; }}
{assigns}
ScriptMessage("OK: Assigned {esc_bg} to layers [{layer_list}] of " + room.Name.Content);
'''
    out = _run_utmt(csx, game_file, save=True)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)


def cmd_set_room_solid_bg(game_file: Path, room_name: str, color: str,
                          asset_name: str | None = None,
                          layers: str | None = None,
                          runtime: bool = True) -> None:
    """One-shot: make a room's background a solid color.

    Workflow (previously manual): read room size -> generate a solid PNG ->
    create-bg-asset -> point all enabled layers at it (room data) ->
    optionally inject a runtime override (gml-bg with --hide-above).
    """
    color = color.lstrip("#").upper()
    if len(color) != 6 or any(c not in "0123456789ABCDEF" for c in color):
        print(f"错误: 颜色须为 6 位 hex RGB (如 0000FF): {color}", file=sys.stderr)
        return
    rgb = int(color, 16)
    if asset_name is None:
        asset_name = f"bg_solid_{color.lower()}"

    # 1) room size (so the image covers the room without relying on tiling)
    w, h = _read_room_size(game_file, room_name)

    # 2) generate solid PNG
    try:
        from PIL import Image
    except ImportError:
        print("错误: 需要 Pillow (pip install Pillow)", file=sys.stderr)
        return
    import tempfile
    fd, png_path = tempfile.mkstemp(suffix=".png", prefix="det_solid_")
    os.close(fd)
    try:
        Image.new("RGBA", (w, h),
                  ((rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF, 255)
                  ).save(png_path)
        # 3) create asset (reuse if present)
        if _bg_asset_exists(game_file, asset_name):
            print(f"提示: 背景资源已存在，复用 {asset_name}", file=sys.stderr)
        else:
            cmd_create_bg_asset(game_file, asset_name, png_path)
    finally:
        try:
            os.unlink(png_path)
        except OSError:
            pass

    # 4) target layers: explicit > currently-enabled > [0]
    target = _parse_layers(layers)
    if not target:
        target = _enabled_bg_layers(game_file, room_name) or [0]

    # 5) room data
    _assign_room_bg_layers(game_file, room_name, asset_name, target)

    # 6) runtime override (covers object-driven rooms and hides occluders)
    if runtime:
        cmd_gml_bg(game_file, room_name, asset_name,
                   slot=target[0],
                   layers=",".join(str(s) for s in target),
                   hide_above=True)


def cmd_room_bg_info(game_file: Path, room_name: str) -> None:
    """Diagnose how a room renders its background (category A / B / C)."""
    esc = _csx_escape(room_name)
    csx = _resolve_room_csx(esc) + '''
ScriptMessage("=== Room BG Info ===");
ScriptMessage("Name:  " + room.Name.Content);
ScriptMessage("Size:  " + room.Width + " x " + room.Height);
int enabled = 0;
for (int i = 0; i < (room.Backgrounds?.Count ?? 0); i++) {
    var bg = room.Backgrounds[i];
    string bgName = bg?.BackgroundDefinition?.Name?.Content ?? "(none)";
    if (bg.Enabled) {
        enabled++;
        ScriptMessage("  BG[" + i + "] ENABLED bg=" + bgName
            + " fg=" + bg.Foreground
            + " tiled=(" + bg.TiledHorizontally + "," + bg.TiledVertically + ")");
    }
}
bool hasBgObj = false;
if (room.GameObjects != null) {
    foreach (var go in room.GameObjects) {
        string on = go.ObjectDefinition?.Name?.Content ?? "";
        if (on.StartsWith("obj_backgrounder_")) {
            hasBgObj = true;
            ScriptMessage("  backgrounder obj: " + on);
        }
    }
}
ScriptMessage("ENABLEDCOUNT:" + enabled);
ScriptMessage("HASBG:" + hasBgObj);
'''
    out = _run_utmt(csx, game_file, save=False)
    enabled = 0
    has_bg_obj = False
    for line in _parse_msg(out):
        if line.startswith("ENABLEDCOUNT:"):
            enabled = int(line.split(":", 1)[1])
        elif line.startswith("HASBG:"):
            has_bg_obj = line.split(":", 1)[1].strip().lower() == "true"
        else:
            print(line)
    if enabled == 0 and not has_bg_obj:
        cat = "A (纯 Tile 房)"
        hint = ("渲染器跳过背景阶段；房间数据改动无效。"
                "需先 set-room-bg --enable true 启用一层，或放 backgrounder 对象")
    elif has_bg_obj:
        cat = "C (对象驱动)"
        hint = "obj_backgrounder_* 在运行时覆盖房间数据；用 gml-bg 注入（可 --hide-above）"
    else:
        cat = "B (房间数据驱动)"
        hint = "房间数据即渲染来源；set-room-bg 有效，注意高 slot 层会盖住低层"
    print(f"Category: {cat}")
    print(f"Hint:     {hint}")
    print("Tip:      可用 `search-vars --value <背景资源名>` 复核（无命中=>B类）")


# ============================================================
# SCR_TEXT Case Viewer (search for text cases in SCR_TEXT)
# ============================================================


# ============================================================
# Quest Management Commands
# ============================================================


# ============================================================
# Batch Textdata Import
# ============================================================

# ============================================================
# Handler Extraction (A6: clean up obj_time_Step_2)
# ============================================================


# ============================================================
# Door System (S3 — Room Connectivity)
# ============================================================

DOOR_GOTO_BACK_SCRIPT = '''/// door_goto_back()
/// Return to the previous room
if (global.deterline_lastroom >= 0)
{
    global.deterline_pending_x = global.deterline_lastx;
    global.deterline_pending_y = global.deterline_lasty;
    room_goto(global.deterline_lastroom);
}
'''

DOOR_CREATE_BASE = '''/// obj_deterline_door — Create event
var _rn = room_get_name(room);
if (variable_global_exists("deterline_pending_x") && global.deterline_pending_x >= 0)
{
    if (instance_exists(obj_mainchara))
    {
        obj_mainchara.x = global.deterline_pending_x;
        obj_mainchara.y = global.deterline_pending_y;
    }
    global.deterline_pending_x = -1;
}
'''
DOOR_CREATE_BRANCH = '''
if (_rn == "{room}" && x == {x} && y == {y}) {{
    target_room = {target_idx};
    spawn_x = {sx};
    spawn_y = {sy};
    exit;
}}'''

DOOR_CREATE_FALLBACK = '''
target_room = -1;
spawn_x = 0;
spawn_y = 0;
'''

DOOR_STEP_CODE = '''/// obj_deterline_door — Step event
if (target_room >= 0 && instance_exists(obj_mainchara))
{
    if (point_distance(x, y, obj_mainchara.x, obj_mainchara.y) < 80)
    {
        global.deterline_lastroom = room;
        global.deterline_lastx = obj_mainchara.x;
        global.deterline_lasty = obj_mainchara.y;
        global.deterline_lastdir = obj_mainchara.image_index;
        global.deterline_pending_x = spawn_x;
        global.deterline_pending_y = spawn_y;
        room_goto(target_room);
    }
}
'''


def cmd_create_door(game_file: Path, cur_room: str, target_room: str,
                    x: int, y: int, spawn_x: int, spawn_y: int) -> None:
    """Create a teleport door in cur_room that leads to target_room."""
    OBJ_CREATE = "gml_Object_obj_deterline_door_Create_0"
    OBJ_STEP = "gml_Object_obj_deterline_door_Step_0"

    esc_cur = _csx_escape(cur_room)
    esc_target = _csx_escape(target_room)

    # Look up target room numeric index via CSX
    idx_csx = f'''
var r = Data.Rooms.ByName("{esc_target}");
if (r == null) {{
    for (int i = 0; i < Data.Rooms.Count; i++) {{
        if (Data.Rooms[i].Name.Content.IndexOf("{esc_target}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            r = Data.Rooms[i];
            break;
        }}
    }}
}}
if (r != null) {{
    ScriptMessage("IDX:" + Data.Rooms.IndexOf(r));
}} else {{
    ScriptMessage("IDX:-1");
}}
'''
    idx_out = _run_utmt(idx_csx, game_file, save=False)
    target_idx = -1
    for line in _parse_msg(idx_out):
        if line.startswith("IDX:"):
            target_idx = int(line.split(":")[1])
            break
    if target_idx < 0:
        raise NotFoundError(f"目标房间不存在: {target_room}")

    # Read existing Create_0 code or start from base
    existing_create = _get_decompiled_code(game_file, OBJ_CREATE)
    if existing_create and existing_create.strip():
        existing_create = existing_create.strip()
        # Check if this door branch already exists
        marker = f'_rn == "{esc_cur}" && x == {x} && y == {y}'
        if marker in existing_create:
            print(f"警告: 在 ({x},{y}) 已有门", file=sys.stderr)
    else:
        existing_create = DOOR_CREATE_BASE.strip()

    # Append new branch before fallback
    new_branch = DOOR_CREATE_BRANCH.format(room=esc_cur, x=x, y=y,
                                            target_idx=target_idx, sx=spawn_x, sy=spawn_y)
    # Remove any existing fallback, we'll add it at the end
    if existing_create.endswith(DOOR_CREATE_FALLBACK.strip()):
        existing_create = existing_create[:-len(DOOR_CREATE_FALLBACK.strip())].rstrip()
    new_create = existing_create + new_branch + DOOR_CREATE_FALLBACK

    verb_back = _csx_verbatim_escape(DOOR_GOTO_BACK_SCRIPT)
    verb_create = _csx_verbatim_escape(new_create)
    verb_step = _csx_verbatim_escape(DOOR_STEP_CODE)

    esc_name_create = _csx_escape(OBJ_CREATE)
    esc_name_step = _csx_escape(OBJ_STEP)
    esc_name_back = _csx_escape("gml_Script_deterline_door_back")

    csx = f'''
try {{
    CodeImportGroup importGroup = new(Data)
    {{
        AutoCreateAssets = true,
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueueReplace("{esc_name_back}", @"{verb_back}");
    importGroup.QueueReplace("{esc_name_create}", @"{verb_create}");
    importGroup.QueueReplace("{esc_name_step}", @"{verb_step}");
    importGroup.Import();
    ScriptMessage("OK: Scripts created/updated");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
    return;
}}

var room = Data.Rooms.ByName("{esc_cur}");
if (room == null) {{
    for (int r = 0; r < Data.Rooms.Count; r++) {{
        if (Data.Rooms[r].Name.Content.IndexOf("{esc_cur}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            room = Data.Rooms[r];
            break;
        }}
    }}
}}
if (room == null) {{
    ScriptMessage("ERROR: Room not found: {esc_cur}");
    return;
}}

var doorObj = Data.GameObjects.ByName("obj_deterline_door");
if (doorObj == null) {{
    ScriptMessage("ERROR: obj_deterline_door was not created");
    return;
}}

// Assign visible sprite so player can find the door
var cactusSpr = Data.Sprites.ByName("spr_cactus");
if (cactusSpr != null) {{
    doorObj.Sprite = cactusSpr;
}}

ulong _maxInstId = 0;
foreach (var _r in Data.Rooms)
{{
    foreach (var _g in _r.GameObjects)
    {{
        if (_g.InstanceID > _maxInstId) _maxInstId = _g.InstanceID;
    }}
}}
uint newId = (uint)(System.Math.Max((long)Data.GeneralInfo.LastObj, (long)_maxInstId) + 1);
Data.GeneralInfo.LastObj = newId;
room.GameObjects.Add(new UndertaleRoom.GameObject() {{
    InstanceID = newId,
    ObjectDefinition = doorObj,
    X = {x},
    Y = {y}
}});
ScriptMessage("OK: Door [" + newId + "] created in " + room.Name.Content + " -> " + "{esc_target}");
'''
    csx += _instances_check_snippet()
    out = _run_utmt(csx, game_file, save=True)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)
    _update_rooms_json(target_room, target_room)


# ============================================================
# Pit System (S3 — Fall / Pit Hazards)
# ============================================================

PIT_CREATE_BASE = '''/// obj_deterline_pit — Create event
var _rn = room_get_name(room);
'''
PIT_CREATE_BRANCH = '''
if (_rn == "{room}" && x == {x} && y == {y}) {{
    target_room = {target_idx};
    spawn_x = {sx};
    spawn_y = {sy};
    exit;
}}'''
PIT_CREATE_FALLBACK = '''
target_room = -1;
spawn_x = 0;
spawn_y = 0;
'''

PIT_STEP_CODE = '''/// obj_deterline_pit — Step event
if (target_room >= 0 && instance_exists(obj_mainchara))
{
    if (place_meeting(x, y, obj_mainchara))
    {
        global.deterline_lastroom = room;
        global.deterline_lastx = obj_mainchara.x;
        global.deterline_lasty = obj_mainchara.y;
        global.deterline_lastdir = obj_mainchara.image_index;
        global.deterline_pending_x = spawn_x;
        global.deterline_pending_y = spawn_y;
        room_goto(target_room);
    }
}
'''


def cmd_create_pit(game_file: Path, cur_room: str, target_room: str,
                   x: int, y: int, spawn_x: int, spawn_y: int) -> None:
    """Create a pit/hazard in cur_room that teleports player to target_room."""
    OBJ_CREATE = "gml_Object_obj_deterline_pit_Create_0"
    OBJ_STEP = "gml_Object_obj_deterline_pit_Step_0"

    esc_cur = _csx_escape(cur_room)
    esc_target = _csx_escape(target_room)

    # Look up target room numeric index
    idx_csx = f'''
var r = Data.Rooms.ByName("{esc_target}");
if (r == null) {{
    for (int i = 0; i < Data.Rooms.Count; i++) {{
        if (Data.Rooms[i].Name.Content.IndexOf("{esc_target}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            r = Data.Rooms[i];
            break;
        }}
    }}
}}
if (r != null) {{
    ScriptMessage("IDX:" + Data.Rooms.IndexOf(r));
}} else {{
    ScriptMessage("IDX:-1");
}}
'''
    idx_out = _run_utmt(idx_csx, game_file, save=False)
    target_idx = -1
    for line in _parse_msg(idx_out):
        if line.startswith("IDX:"):
            target_idx = int(line.split(":")[1])
            break
    if target_idx < 0:
        raise NotFoundError(f"目标房间不存在: {target_room}")

    # Read existing Create_0 or start from base
    existing_create = _get_decompiled_code(game_file, OBJ_CREATE)
    if existing_create and existing_create.strip():
        existing_create = existing_create.strip()
        marker = f'_rn == "{esc_cur}" && x == {x} && y == {y}'
        if marker in existing_create:
            print(f"警告: 在 ({x},{y}) 已有坑", file=sys.stderr)
    else:
        existing_create = PIT_CREATE_BASE.strip()

    new_branch = PIT_CREATE_BRANCH.format(room=esc_cur, x=x, y=y,
                                           target_idx=target_idx, sx=spawn_x, sy=spawn_y)
    if existing_create.endswith(PIT_CREATE_FALLBACK.strip()):
        existing_create = existing_create[:-len(PIT_CREATE_FALLBACK.strip())].rstrip()
    new_create = existing_create + new_branch + PIT_CREATE_FALLBACK

    verb_create = _csx_verbatim_escape(new_create)
    verb_step = _csx_verbatim_escape(PIT_STEP_CODE)
    esc_name_create = _csx_escape(OBJ_CREATE)
    esc_name_step = _csx_escape(OBJ_STEP)

    csx = f'''
try {{
    CodeImportGroup importGroup = new(Data)
    {{
        AutoCreateAssets = true,
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueueReplace("{esc_name_create}", @"{verb_create}");
    importGroup.QueueReplace("{esc_name_step}", @"{verb_step}");
    importGroup.Import();
    ScriptMessage("OK: Scripts created/updated");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
    return;
}}

var room = Data.Rooms.ByName("{esc_cur}");
if (room == null) {{
    for (int r = 0; r < Data.Rooms.Count; r++) {{
        if (Data.Rooms[r].Name.Content.IndexOf("{esc_cur}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            room = Data.Rooms[r];
            break;
        }}
    }}
}}
if (room == null) {{
    ScriptMessage("ERROR: Room not found: {esc_cur}");
    return;
}}

var pitObj = Data.GameObjects.ByName("obj_deterline_pit");
if (pitObj == null) {{
    ScriptMessage("ERROR: obj_deterline_pit was not created");
    return;
}}

var pitSpr = Data.Sprites.ByName("spr_markerX");
if (pitSpr == null) {{
    pitSpr = Data.Sprites.ByName("spr_stardrop");
}}
if (pitSpr != null) {{
    pitObj.Sprite = pitSpr;
}}

ulong _maxInstId = 0;
foreach (var _r in Data.Rooms)
{{
    foreach (var _g in _r.GameObjects)
    {{
        if (_g.InstanceID > _maxInstId) _maxInstId = _g.InstanceID;
    }}
}}
uint newId = (uint)(System.Math.Max((long)Data.GeneralInfo.LastObj, (long)_maxInstId) + 1);
Data.GeneralInfo.LastObj = newId;
room.GameObjects.Add(new UndertaleRoom.GameObject() {{
    InstanceID = newId,
    ObjectDefinition = pitObj,
    X = {x},
    Y = {y}
}});
ScriptMessage("OK: Pit [" + newId + "] created in " + room.Name.Content + " -> " + "{esc_target}");
'''
    csx += _instances_check_snippet()
    out = _run_utmt(csx, game_file, save=True)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)
    _update_rooms_json(target_room, target_room)


# ============================================================
# Battle System (Direction B — custom encounter triggers)
# ============================================================

BATTLE_CREATE_BASE = '''/// obj_deterline_battle — Create event
var _rn = room_get_name(room);
'''
BATTLE_CREATE_BRANCH = '''
if (_rn == "{room}" && x == {x} && y == {y}) {{
    battlegroup_id = {bg_id};
    border = {border};
    exit;
}}'''
BATTLE_CREATE_FALLBACK = '''
battlegroup_id = -1;
border = 0;
'''

BATTLE_STEP_CODE = '''/// obj_deterline_battle — Step event
if (battlegroup_id >= 0 && instance_exists(obj_mainchara))
{
    if (place_meeting(x, y, obj_mainchara) && global.interact == 0)
    {
        global.battlegroup = battlegroup_id;
        global.border = border;
        instance_create(0, 0, obj_battleblcon);
        instance_destroy();
    }
}
'''


def cmd_create_battle(game_file: Path, cur_room: str,
                      battlegroup_id: int, border: int = 0,
                      x: int = 320, y: int = 240) -> None:
    """Create a battle trigger in cur_room."""
    OBJ_CREATE = "gml_Object_obj_deterline_battle_Create_0"
    OBJ_STEP = "gml_Object_obj_deterline_battle_Step_0"

    esc_cur = _csx_escape(cur_room)

    existing_create = _get_decompiled_code(game_file, OBJ_CREATE)
    if existing_create and existing_create.strip():
        existing_create = existing_create.strip()
        marker = f'_rn == "{esc_cur}" && x == {x} && y == {y}'
        if marker in existing_create:
            print(f"警告: 在 ({x},{y}) 已有战斗", file=sys.stderr)
    else:
        existing_create = BATTLE_CREATE_BASE.strip()

    new_branch = BATTLE_CREATE_BRANCH.format(room=esc_cur, x=x, y=y,
                                              bg_id=battlegroup_id, border=border)
    if existing_create.endswith(BATTLE_CREATE_FALLBACK.strip()):
        existing_create = existing_create[:-len(BATTLE_CREATE_FALLBACK.strip())].rstrip()
    new_create = existing_create + new_branch + BATTLE_CREATE_FALLBACK

    verb_create = _csx_verbatim_escape(new_create)
    verb_step = _csx_verbatim_escape(BATTLE_STEP_CODE)
    esc_name_create = _csx_escape(OBJ_CREATE)
    esc_name_step = _csx_escape(OBJ_STEP)

    csx = f'''
try {{
    CodeImportGroup importGroup = new(Data)
    {{
        AutoCreateAssets = true,
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueueReplace("{esc_name_create}", @"{verb_create}");
    importGroup.QueueReplace("{esc_name_step}", @"{verb_step}");
    importGroup.Import();
    ScriptMessage("OK: Scripts created/updated");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
    return;
}}

var room = Data.Rooms.ByName("{esc_cur}");
if (room == null) {{
    for (int r = 0; r < Data.Rooms.Count; r++) {{
        if (Data.Rooms[r].Name.Content.IndexOf("{esc_cur}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            room = Data.Rooms[r];
            break;
        }}
    }}
}}
if (room == null) {{
    ScriptMessage("ERROR: Room not found: {esc_cur}");
    return;
}}

var batObj = Data.GameObjects.ByName("obj_deterline_battle");
if (batObj == null) {{
    ScriptMessage("ERROR: obj_deterline_battle was not created");
    return;
}}

var markerSpr = Data.Sprites.ByName("spr_markerB");
if (markerSpr != null) {{
    batObj.Sprite = markerSpr;
}}

ulong _maxInstId = 0;
foreach (var _r in Data.Rooms)
{{
    foreach (var _g in _r.GameObjects)
    {{
        if (_g.InstanceID > _maxInstId) _maxInstId = _g.InstanceID;
    }}
}}
uint newId = (uint)(System.Math.Max((long)Data.GeneralInfo.LastObj, (long)_maxInstId) + 1);
Data.GeneralInfo.LastObj = newId;
room.GameObjects.Add(new UndertaleRoom.GameObject() {{
    InstanceID = newId,
    ObjectDefinition = batObj,
    X = {x},
    Y = {y}
}});
ScriptMessage("OK: Battle trigger [" + newId + "] in " + room.Name.Content + " (group " + {battlegroup_id} + ")");
'''
    csx += _instances_check_snippet()
    out = _run_utmt(csx, game_file, save=True)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)


def cmd_list_doors(game_file: Path, room_name: str) -> None:
    """List all Deterline doors in a room."""
    OBJ_CREATE = "gml_Object_obj_deterline_door_Create_0"
    create_code = _get_decompiled_code(game_file, OBJ_CREATE)
    if create_code is None:
        print("该房间没有传送门", file=sys.stderr)
        return

    # Find branches matching this room
    lines = create_code.split("\n")
    print(f"--- {room_name} 的传送门 ---")
    found = 0
    import re
    for i, ln in enumerate(lines):
        m = re.search(r'_rn == "([^"]+)"\s*&&\s*x == (\d+)\s*&&\s*y == (\d+)', ln)
        if m:
            rn_part = m.group(1)
            x_part = int(m.group(2))
            y_part = int(m.group(3))
            target_line = ""
            for j in range(i, min(i + 6, len(lines))):
                if lines[j].strip().startswith("target_room "):
                    target_line = lines[j].strip()
                    break
            target_val = target_line.split("=")[1].strip().rstrip(";")
            if rn_part.lower() != room_name.lower():
                continue
            found += 1
            print(f"  [{found}] ({x_part},{y_part}) → 房间 {target_val}")

    if found == 0:
        print("该房间没有传送门实例", file=sys.stderr)
        return

    # Also check for actual instances in the room
    esc = _csx_escape(room_name)
    csx = f'''
int found = 0;
for (int r = 0; r < Data.Rooms.Count; r++) {{
    if (Data.Rooms[r].Name.Content.IndexOf("{esc}", StringComparison.OrdinalIgnoreCase) >= 0) {{
        foreach (var go in Data.Rooms[r].GameObjects) {{
            string on = go.ObjectDefinition?.Name?.Content ?? "";
            if (on == "obj_deterline_door") {{
                ScriptMessage("  Instance[" + go.InstanceID + "] obj_deterline_door at (" + go.X + "," + go.Y + ")");
                found++;
            }}
        }}
        break;
    }}
}}
if (found == 0) ScriptMessage("  (no instances in room data)");
'''
    out = _run_utmt(csx, game_file, save=False)
    for line in _parse_msg(out):
        print(line)


def cmd_remove_door(game_file: Path, room_name: str,
                    x: int | None, y: int | None,
                    remove_all: bool = False) -> None:
    """Remove a Deterline door by coordinates, or all doors with --all."""
    OBJ_CREATE = "gml_Object_obj_deterline_door_Create_0"
    esc_room = _csx_escape(room_name)

    # Step 1: Remove from Create_0 code
    create_code = _get_decompiled_code(game_file, OBJ_CREATE)
    if create_code is None:
        print("该房间没有传送门", file=sys.stderr)
        return

    lines = create_code.split("\n")
    new_lines: list[str] = []
    skip_block = False
    removed_count = 0
    i = 0
    import re
    while i < len(lines):
        ln = lines[i]
        dore = re.search(r'_rn == "([^"]+)"\s*&&\s*x == (\d+)\s*&&\s*y == (\d+)', ln)
        if dore:
            rn_part = dore.group(1)
            x_part = int(dore.group(2))
            y_part = int(dore.group(3))
            match = False
            if remove_all and rn_part == esc_room:
                match = True
            elif not remove_all and x is not None and y is not None:
                if rn_part == esc_room and x_part == x and y_part == y:
                    match = True
            if match:
                removed_count += 1
                i += 1
                while i < len(lines) and 'exit;' not in lines[i]:
                    i += 1
                # Skip exit; and the closing } that follows
                i += 2
                continue
        if not skip_block:
            new_lines.append(ln)
        i += 1

    if removed_count == 0:
        if x is not None:
            print(f"错误: 未找到 ({x},{y}) 处的门", file=sys.stderr)
        else:
            print("该房间没有传送门", file=sys.stderr)
        return

    new_create = "\n".join(new_lines)
    verb_create = _csx_verbatim_escape(new_create)
    esc_create = _csx_escape(OBJ_CREATE)

    # Step 2: Remove instances from room data
    instance_cond = ""
    if not remove_all and x is not None and y is not None:
        instance_cond = f"go.X == {x} && go.Y == {y}"
    else:
        instance_cond = "true"

    csx = f'''
// Remove instances
for (int r = 0; r < Data.Rooms.Count; r++) {{
    if (Data.Rooms[r].Name.Content.IndexOf("{esc_room}", StringComparison.OrdinalIgnoreCase) >= 0) {{
        for (int i = Data.Rooms[r].GameObjects.Count - 1; i >= 0; i--) {{
            var go = Data.Rooms[r].GameObjects[i];
            string on = go.ObjectDefinition?.Name?.Content ?? "";
            if (on == "obj_deterline_door" && ({instance_cond})) {{
                Data.Rooms[r].GameObjects.RemoveAt(i);
            }}
        }}
        break;
    }}
}}

// Update Create_0 code
try {{
    CodeImportGroup importGroup = new(Data)
    {{
        AutoCreateAssets = true,
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueueReplace("{esc_create}", @"{verb_create}");
    importGroup.Import();
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
    return;
}}
ScriptMessage("OK: Removed " + {removed_count} + " door(s) from " + "{esc_room}");
'''
    out = _run_utmt(csx, game_file, save=True)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)
    print(f"已从 Create_0 中移除 {removed_count} 条分支")


# ============================================================
# P4-1 Sprite & Object Commands
# ============================================================

def cmd_sprite_list(game_file: Path, limit: int) -> None:
    """List all sprites with name, dimensions, frame count."""
    csx = f'''
int limit = {limit};
int count = 0;
for (int i = 0; i < Data.Sprites.Count && count < limit; i++) {{
    var spr = Data.Sprites[i];
    string fcount = (spr.Textures != null) ? spr.Textures.Count.ToString() : "0";
    string stype = spr.IsSpecialType ? spr.SSpriteType.ToString() : "Normal";
    ScriptMessage(spr.Name.Content + " | " + spr.Width + "x" + spr.Height + " | frames=" + fcount + " | type=" + stype);
    count++;
}}
ScriptMessage("(total: " + Data.Sprites.Count + " sprites, showing " + count + ")");
'''
    out = _run_utmt(csx, game_file, save=False)
    for line in _parse_msg(out):
        print(line)


def cmd_sprite_search(game_file: Path, query: str, limit: int) -> None:
    """Search sprites by name."""
    esc = _csx_escape(query)
    csx = f'''
int limit = {limit};
int found = 0;
for (int i = 0; i < Data.Sprites.Count && found < limit; i++) {{
    var spr = Data.Sprites[i];
    if (spr.Name.Content.IndexOf("{esc}", StringComparison.OrdinalIgnoreCase) >= 0) {{
        string fcount = (spr.Textures != null) ? spr.Textures.Count.ToString() : "0";
        ScriptMessage(spr.Name.Content + " | " + spr.Width + "x" + spr.Height + " | frames=" + fcount);
        found++;
    }}
}}
if (found == 0) {{
    ScriptMessage("(no matching sprites)");
}} else {{
    ScriptMessage("(found " + found + " sprites)");
}}
'''
    out = _run_utmt(csx, game_file, save=False)
    lines = _parse_msg(out)
    for line in lines:
        print(line)
    _fail_if_no_match(lines, "search-sprite", query)


def cmd_obj_get(game_file: Path, obj_name: str) -> None:
    """Show detailed info about a game object, including its sprite."""
    esc = _csx_escape(obj_name)
    csx = f'''
var obj = Data.GameObjects.ByName("{esc}");
if (obj == null) {{
    obj = Data.GameObjects.ByName("{esc}", true);
}}
if (obj == null) {{
    string query = "{esc}";
    int first = -1;
    int count = 0;
    for (int o = 0; o < Data.GameObjects.Count; o++) {{
        string on = Data.GameObjects[o].Name.Content;
        if (on.IndexOf(query, StringComparison.OrdinalIgnoreCase) >= 0) {{
            if (first < 0) first = o;
            count++;
        }}
    }}
    if (first >= 0) {{
        obj = Data.GameObjects[first];
        if (count > 1) ScriptMessage("(found " + count + " matches, using: " + obj.Name.Content + ")");
    }}
}}
if (obj == null) {{
    ScriptMessage("ERROR: Object not found: {esc}");
    string suggest = "";
    int found = 0;
    for (int o = 0; o < Data.GameObjects.Count && found < 5; o++) {{
        string on = Data.GameObjects[o].Name.Content;
        if (on.IndexOf("{esc}", StringComparison.OrdinalIgnoreCase) >= 0 ||
            "{esc}".IndexOf(on, StringComparison.OrdinalIgnoreCase) >= 0) {{
            suggest += (found > 0 ? ", " : "") + on;
            found++;
        }}
    }}
    if (found > 0) ScriptMessage("HINT: Did you mean: " + suggest);
    return;
}}
ScriptMessage("=== " + obj.Name.Content + " ===");
ScriptMessage("Sprite: " + (obj.Sprite?.Name?.Content ?? "(none)"));
ScriptMessage("Sprite Size: " + (obj.Sprite?.Width ?? 0) + "x" + (obj.Sprite?.Height ?? 0));
ScriptMessage("Visible: " + obj.Visible + " | Solid: " + obj.Solid);
ScriptMessage("Depth: " + obj.Depth + " | Persistent: " + obj.Persistent);
ScriptMessage("TextureMask: " + (obj.TextureMaskId?.Name?.Content ?? "(none)"));
ScriptMessage("Physics: " + obj.UsesPhysics);
// Full inheritance chain (walk ParentId to root)
var chainNames = new List<string>();
var chainCur = obj;
int chainGuard = 0;
bool nativeInteractable = false;
while (chainCur != null && chainGuard < 30)
{{
    string cn = chainCur.Name?.Content ?? "(unknown)";
    chainNames.Add(cn);
    if (cn == "obj_interactable" || cn == "obj_readablesolid") nativeInteractable = true;
    chainCur = chainCur.ParentId;
    chainGuard++;
}}
ScriptMessage("Parent Chain: " + string.Join(" → ", chainNames));
if (nativeInteractable)
{{
    ScriptMessage("WARN: 原生交互对象 (继承 obj_readablesolid/obj_interactable)");
    ScriptMessage("     该对象有原生 Z 键/触碰交互系统 (myinteract → alarm[0] → Alarm_0 默认对话)。");
    ScriptMessage("     用 myinteract 做距离触发会与默认对话重叠 → 改用 flag 状态机 + 守卫 Alarm_0，");
    ScriptMessage("     或直接用 npc-dialogue / guard-npc-alarm 命令。");
}}
int evtCount = 0;
for (int e = 0; e < obj.Events.Count; e++) {{
    var evtList = obj.Events[e];
    if (evtList != null && evtList.Count > 0) {{
        evtCount += evtList.Count;
    }}
}}
ScriptMessage("Events: " + evtCount + " total");
'''
    out = _run_utmt(csx, game_file, save=False)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("HINT:"):
            print(line, file=sys.stderr)
        else:
            print(line)


def cmd_obj_set_sprite(game_file: Path, obj_name: str, sprite_name: str) -> None:
    """Change the sprite reference of a game object."""
    esc_obj = _csx_escape(obj_name)
    esc_spr = _csx_escape(sprite_name)
    csx = f'''
var obj = Data.GameObjects.ByName("{esc_obj}");
if (obj == null) {{
    obj = Data.GameObjects.ByName("{esc_obj}", true);
}}
if (obj == null) {{
    string query = "{esc_obj}";
    int first = -1;
    int count = 0;
    for (int o = 0; o < Data.GameObjects.Count; o++) {{
        string on = Data.GameObjects[o].Name.Content;
        if (on.IndexOf(query, StringComparison.OrdinalIgnoreCase) >= 0) {{
            if (first < 0) first = o;
            count++;
        }}
    }}
    if (first >= 0) {{
        obj = Data.GameObjects[first];
        if (count > 1) ScriptMessage("(found " + count + " matches, using: " + obj.Name.Content + ")");
    }}
}}
if (obj == null) {{
    ScriptMessage("ERROR: Object not found: {esc_obj}");
    string suggest = "";
    int found = 0;
    for (int o = 0; o < Data.GameObjects.Count && found < 5; o++) {{
        string on = Data.GameObjects[o].Name.Content;
        if (on.IndexOf("{esc_obj}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            suggest += (found > 0 ? ", " : "") + on;
            found++;
        }}
    }}
    if (found > 0) ScriptMessage("HINT: Did you mean: " + suggest);
    return;
}}
var spr = Data.Sprites.ByName("{esc_spr}");
if (spr == null) {{
    spr = Data.Sprites.ByName("{esc_spr}", true);
}}
if (spr == null) {{
    string query = "{esc_spr}";
    int first = -1;
    int count = 0;
    for (int s = 0; s < Data.Sprites.Count; s++) {{
        string sn = Data.Sprites[s].Name.Content;
        if (sn.IndexOf(query, StringComparison.OrdinalIgnoreCase) >= 0) {{
            if (first < 0) first = s;
            count++;
        }}
    }}
    if (first >= 0) {{
        spr = Data.Sprites[first];
        if (count > 1) ScriptMessage("(found " + count + " sprites, using: " + spr.Name.Content + ")");
    }}
}}
if (spr == null) {{
    ScriptMessage("ERROR: Sprite not found: {esc_spr}");
    string suggest = "";
    int found = 0;
    for (int s = 0; s < Data.Sprites.Count && found < 5; s++) {{
        string sn = Data.Sprites[s].Name.Content;
        if (sn.IndexOf("{esc_spr}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            suggest += (found > 0 ? ", " : "") + sn;
            found++;
        }}
    }}
    if (found > 0) ScriptMessage("HINT: Did you mean: " + suggest);
    return;
}}
string oldSpr = obj.Sprite?.Name?.Content ?? "(none)";
obj.Sprite = spr;
ScriptMessage("OK: " + obj.Name.Content + ": " + oldSpr + " → " + spr.Name.Content);
ScriptMessage("(Sprite size: " + spr.Width + "x" + spr.Height + ")");
'''
    out = _run_utmt(csx, game_file, save=True)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)
        else:
            print(line)


# ============================================================
# P4-1-1 Texture & Sprite Export/Replace
# ============================================================

def cmd_texture_list(game_file: Path, limit: int) -> None:
    """List all embedded textures (TXTR)."""
    csx = f'''
int limit = {limit};
for (int i = 0; i < Data.EmbeddedTextures.Count && i < limit; i++) {{
    var t = Data.EmbeddedTextures[i];
    int w = t.TextureData?.Width ?? 0;
    int h = t.TextureData?.Height ?? 0;
    string texName = t.Name?.Content ?? "(unnamed)";
    ScriptMessage(texName + " | " + w + "x" + h + " | external=" + t.TextureExternal);
}}
ScriptMessage("(total: " + Data.EmbeddedTextures.Count + " textures)");
'''
    out = _run_utmt(csx, game_file, save=False)
    for line in _parse_msg(out):
        print(line)


def _export_sprite_json(game_file: Path, sprite_name: str) -> None:
    """Export sprite metadata as JSON to stderr."""
    esc = _csx_escape(sprite_name)
    csx = f'''
var spr = Data.Sprites.ByName("{esc}");
if (spr == null) {{
    spr = Data.Sprites.ByName("{esc}", true);
}}
if (spr == null) return;
string frames = "[";
for (int i = 0; i < (spr.Textures?.Count ?? 0); i++) {{
    if (i > 0) frames += ",";
    var t = spr.Textures[i]?.Texture;
    if (t != null) {{
        frames += "{{";
        frames += "\\"frame\\":\\"" + i + "\\",";
        frames += "\\"src\\":\\"" + t.SourceX + "," + t.SourceY + " " + t.SourceWidth + "x" + t.SourceHeight + "\\",";
        frames += "\\"target\\":\\"" + t.TargetX + "," + t.TargetY + " " + t.TargetWidth + "x" + t.TargetHeight + "\\",";
        frames += "\\"bound\\":\\"" + t.BoundingWidth + "x" + t.BoundingHeight + "\\",";
        frames += "\\"page\\":\\"" + (t.TexturePage?.Name?.Content ?? "?") + "\\"";
        frames += "}}";
    }}
}}
frames += "]";
ScriptMessage("JSON:" + "{{");
ScriptMessage("JSON:  \\"name\\": \\"" + spr.Name.Content + "\\",");
ScriptMessage("JSON:  \\"width\\": " + spr.Width + ",");
ScriptMessage("JSON:  \\"height\\": " + spr.Height + ",");
ScriptMessage("JSON:  \\"frames\\": " + (spr.Textures?.Count ?? 0) + ",");
ScriptMessage("JSON:  \\"tex_entries\\": " + frames);
ScriptMessage("JSON:}}");
'''
    out = _run_utmt(csx, game_file, save=False)
    for line in _parse_msg(out):
        if line.startswith("JSON:"):
            print(line[5:])  # print JSON fragment to stdout


def cmd_sprite_export(game_file: Path, sprite_name: str, output: str, frame: int = -1) -> None:
    """Export sprite frame(s) as PNG.

    If frame is -1, export all frames to output directory.
    If frame >= 0, export single frame to output path.
    """
    esc = _csx_escape(sprite_name)
    esc_path = _csx_escape(output)
    csx = f'''
using UndertaleModLib.Util;
using ImageMagick;
var spr = Data.Sprites.ByName("{esc}");
if (spr == null) {{
    spr = Data.Sprites.ByName("{esc}", true);
}}
if (spr == null) {{
    int first = -1;
    int count = 0;
    for (int s = 0; s < Data.Sprites.Count; s++) {{
        var sn = Data.Sprites[s].Name.Content;
        if (sn.IndexOf("{esc}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            if (first < 0) first = s;
            count++;
        }}
    }}
    if (first >= 0) spr = Data.Sprites[first];
}}
if (spr == null) {{
    ScriptMessage("ERROR: Sprite not found: {esc}");
    return;
}}
if (spr.Textures == null || spr.Textures.Count == 0) {{
    ScriptMessage("ERROR: Sprite has no textures");
    return;
}}
int frameNum = {frame};
int totalFrames = spr.Textures.Count;
var worker = new TextureWorker();
if (frameNum < 0) {{
    string outDir = "{esc_path}";
    System.IO.Directory.CreateDirectory(outDir);
    for (int i = 0; i < totalFrames; i++) {{
        var entry = spr.Textures[i];
        if (entry?.Texture == null) continue;
        string fp = System.IO.Path.Combine(outDir, spr.Name.Content + "_" + i + ".png");
        worker.ExportAsPNG(entry.Texture, fp);
    }}
    ScriptMessage("OK: Exported " + totalFrames + " frames to " + outDir);
}} else {{
    if (frameNum >= totalFrames) {{
        ScriptMessage("ERROR: Frame " + frameNum + " out of range (0-" + (totalFrames - 1) + ")");
        return;
    }}
    var entry = spr.Textures[frameNum];
    if (entry?.Texture == null) {{
        ScriptMessage("ERROR: Frame " + frameNum + " has no texture");
        return;
    }}
    worker.ExportAsPNG(entry.Texture, "{esc_path}");
    ScriptMessage("OK: Exported " + spr.Name.Content + "[" + frameNum + "] → {esc_path}");
}}
'''
    out = _run_utmt(csx, game_file, save=False)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        else:
            print(line)


def cmd_sprite_replace(game_file: Path, sprite_name: str, png_path: str, frame: int = 0, all_frames: bool = False) -> None:
    """Replace a sprite frame's texture with a PNG file.

    If all_frames is True, replace all frames with the same PNG.
    """
    esc = _csx_escape(sprite_name)
    esc_png = _csx_escape(png_path)
    all_flag = "true" if all_frames else "false"
    csx = f'''
using UndertaleModLib.Util;
using ImageMagick;
var spr = Data.Sprites.ByName("{esc}");
if (spr == null) {{
    spr = Data.Sprites.ByName("{esc}", true);
}}
if (spr == null) {{
    int first = -1;
    int count = 0;
    for (int s = 0; s < Data.Sprites.Count; s++) {{
        var sn = Data.Sprites[s].Name.Content;
        if (sn.IndexOf("{esc}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            if (first < 0) first = s;
            count++;
        }}
    }}
    if (first >= 0) spr = Data.Sprites[first];
}}
if (spr == null) {{
    ScriptMessage("ERROR: Sprite not found: {esc}");
    return;
}}
string pngPath = "{esc_png}";
if (!System.IO.File.Exists(pngPath)) {{
    ScriptMessage("ERROR: File not found: " + pngPath);
    return;
}}
byte[] pngBytes = System.IO.File.ReadAllBytes(pngPath);
bool allMode = {all_flag};
int totalFrames = spr.Textures?.Count ?? 0;
int frameNum = {frame};
int startFrame = allMode ? 0 : frameNum;
int endFrame = allMode ? totalFrames - 1 : frameNum;
int replaced = 0;
for (int f = startFrame; f <= endFrame; f++) {{
    if (spr.Textures == null || spr.Textures.Count <= f) continue;
    var entry = spr.Textures[f];
    if (entry?.Texture?.TexturePage == null) continue;
    var texItem = entry.Texture;
    var embeddedTex = texItem.TexturePage;
    try {{
        using var editImg = new MagickImage(pngBytes);
        uint sw = texItem.SourceWidth;
        uint sh = texItem.SourceHeight;
        bool resized = false;
        if (editImg.Width != sw || editImg.Height != sh) {{
            ScriptMessage("Resize[" + f + "]: " + editImg.Width + "x" + editImg.Height + " -> " + sw + "x" + sh);
            editImg.InterpolativeResize(sw, sh, PixelInterpolateMethod.Bilinear);
            resized = true;
        }}
        var worker = new TextureWorker();
        var pageImg = worker.GetEmbeddedTexture(embeddedTex);
        lock (pageImg) {{
            pageImg.Composite(editImg, (int)texItem.SourceX, (int)texItem.SourceY, CompositeOperator.Copy);
        }}
        using var ms = new System.IO.MemoryStream();
        pageImg.Write(ms, MagickFormat.Png);
        embeddedTex.TextureData.Image = GMImage.FromPng(ms.ToArray());
        replaced++;
        ScriptMessage("OK: Replaced " + spr.Name.Content + "[" + f + "]");
        if (totalFrames > 1) ScriptMessage("(progress: " + replaced + "/" + (endFrame - startFrame + 1) + ")");
    }} catch (System.Exception ex) {{
        ScriptMessage("ERROR: [" + f + "] " + ex.Message);
    }}
}}
if (replaced == 0) {{
    ScriptMessage("ERROR: No frames were replaced");
}} else {{
    ScriptMessage("Done: " + replaced + " frame(s) replaced");
}}
'''
    out = _run_utmt(csx, game_file, save=True)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("WARN:") or line.startswith("Resize"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:") or line.startswith("Done:"):
            print(line)
        else:
            print(line)


def cmd_sprite_duplicate(game_file: Path, src_name: str, dst_name: str) -> None:
    """Duplicate a sprite with a new name for independent editing."""
    esc_src = _csx_escape(src_name)
    esc_dst = _csx_escape(dst_name)
    csx = f'''
var src = Data.Sprites.ByName("{esc_src}");
if (src == null) {{
    src = Data.Sprites.ByName("{esc_src}", true);
}}
if (src == null) {{
    int first = -1;
    for (int s = 0; s < Data.Sprites.Count; s++) {{
        if (Data.Sprites[s].Name.Content.IndexOf("{esc_src}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            if (first < 0) first = s;
        }}
    }}
    if (first >= 0) src = Data.Sprites[first];
}}
if (src == null) {{
    ScriptMessage("ERROR: Source sprite not found: {esc_src}");
    return;
}}
// Check if destination already exists
var existing = Data.Sprites.ByName("{esc_dst}");
if (existing != null) {{
    ScriptMessage("ERROR: Destination sprite already exists: {esc_dst}");
    return;
}}
var dst = new UndertaleModLib.Models.UndertaleSprite();
dst.Name = Data.Strings.MakeString("{esc_dst}");
dst.Width = src.Width;
dst.Height = src.Height;
dst.MarginLeft = src.MarginLeft;
dst.MarginRight = src.MarginRight;
dst.MarginTop = src.MarginTop;
dst.MarginBottom = src.MarginBottom;
dst.Transparent = src.Transparent;
dst.Smooth = src.Smooth;
dst.Preload = src.Preload;
dst.BBoxMode = src.BBoxMode;
dst.SepMasks = src.SepMasks;
dst.OriginX = src.OriginX;
dst.OriginY = src.OriginY;
// Copy textures with INDEPENDENT texture data
if (src.Textures != null) {{
    dst.Textures = new UndertaleModLib.UndertaleSimpleList<UndertaleModLib.Models.UndertaleSprite.TextureEntry>();
    var worker = new UndertaleModLib.Util.TextureWorker();
    for (int i = 0; i < src.Textures.Count; i++) {{
        var srcEntry = src.Textures[i];
        if (srcEntry?.Texture == null) continue;
        // Extract frame's pixel data from texture page as PNG bytes
        var frameImg = worker.GetTextureFor(srcEntry.Texture, src.Name.Content + "_frame" + i);
        var ms = new System.IO.MemoryStream();
        frameImg.Write(ms, ImageMagick.MagickFormat.Png);
        byte[] pngBytes = ms.ToArray();
        ms.Dispose();
        // Create new standalone embedded texture for this frame
        var newTex = new UndertaleModLib.Models.UndertaleEmbeddedTexture();
        newTex.Name = Data.Strings.MakeString(dst.Name.Content + "_frame" + i);
        newTex.TextureData = new UndertaleModLib.Models.UndertaleEmbeddedTexture.TexData();
        newTex.TextureData.Image = UndertaleModLib.Util.GMImage.FromPng(pngBytes);
        Data.EmbeddedTextures.Add(newTex);
        // Create new TexturePageItem pointing to standalone texture
        var newItem = new UndertaleModLib.Models.UndertaleTexturePageItem();
        newItem.Name = Data.Strings.MakeString(dst.Name.Content + "_item" + i);
        newItem.SourceX = 0;
        newItem.SourceY = 0;
        newItem.SourceWidth = (ushort)frameImg.Width;
        newItem.SourceHeight = (ushort)frameImg.Height;
        newItem.TargetX = srcEntry.Texture.TargetX;
        newItem.TargetY = srcEntry.Texture.TargetY;
        newItem.TargetWidth = srcEntry.Texture.TargetWidth;
        newItem.TargetHeight = srcEntry.Texture.TargetHeight;
        newItem.BoundingWidth = srcEntry.Texture.BoundingWidth;
        newItem.BoundingHeight = srcEntry.Texture.BoundingHeight;
        newItem.TexturePage = newTex;
        Data.TexturePageItems.Add(newItem);
        frameImg.Dispose();
        // Point sprite frame to new item
        var entry = new UndertaleModLib.Models.UndertaleSprite.TextureEntry();
        entry.Texture = newItem;
        dst.Textures.Add(entry);
    }}
    worker.Dispose();
}}
// Copy collision masks
if (src.CollisionMasks != null) {{
    dst.CollisionMasks = new UndertaleModLib.UndertaleObservableList<UndertaleModLib.Models.UndertaleSprite.MaskEntry>();
    for (int i = 0; i < src.CollisionMasks.Count; i++) {{
        var srcMask = src.CollisionMasks[i];
        byte[] maskData = new byte[srcMask.Data.Length];
        System.Array.Copy(srcMask.Data, maskData, srcMask.Data.Length);
        dst.CollisionMasks.Add(new UndertaleModLib.Models.UndertaleSprite.MaskEntry(maskData, srcMask.Width, srcMask.Height));
    }}
}}
Data.Sprites.Add(dst);
ScriptMessage("OK: Duplicated " + src.Name.Content + " → " + dst.Name.Content + " (" + (src.Textures?.Count ?? 0) + " frames)");
    ScriptMessage("(Use replace-sprite to edit the copy independently)");
'''
    out = _run_utmt(csx, game_file, save=True)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)
        else:
            print(line)


def cmd_sprite_preview(game_file: Path, sprite_name: str) -> None:
    """Preview a sprite as ASCII art in terminal."""
    import tempfile
    from PIL import Image
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "preview.png"
        cmd_sprite_export(game_file, sprite_name, str(p), frame=0)
        if not p.exists():
            print("(sprite not found)", file=sys.stderr)
            return
        img = Image.open(str(p)).convert("RGBA")
        w, h = img.size
        print(f"{sprite_name}: {w}x{h}")
        chars = " .:oO8@"
        for y in range(h):
            row = ""
            for x in range(w):
                r, g, b, a = img.getpixel((x, y))
                if a == 0:
                    row += " "
                else:
                    bri = int(0.299 * r + 0.587 * g + 0.114 * b)
                    row += chars[min(bri * len(chars) // 256, len(chars) - 1)]
            print(row)


def cmd_sprite_colorize(game_file: Path, src_name: str, dst_name: str,
                         hue_from: tuple[float, float], hue_to: float,
                         sat_min: float = 0.05, val_min: float = 0.15, val_max: float = 0.95) -> None:
    """Duplicate a sprite and apply HSV-based selective color shift."""
    from PIL import Image
    import colorsys

    # Step 1: duplicate
    cmd_sprite_duplicate(game_file, src_name, dst_name)
    path_base = Path(tempfile.mktemp(suffix=""))
    temp_dir = path_base.parent / f"_clr_{path_base.name}"
    temp_dir.mkdir(exist_ok=True)
    try:
        # Step 2: export all frames
        cmd_sprite_export(game_file, dst_name, str(temp_dir))
        # Step 3: process each frame
        for f in sorted(temp_dir.iterdir()):
            if not f.name.endswith(".png"):
                continue
            img = Image.open(str(f)).convert("RGBA")
            px = img.load()
            w, h = img.size
            changed = 0
            for x in range(w):
                for y in range(h):
                    r, g, b, a = px[x, y]
                    if a == 0:
                        continue
                    hh, ss, vv = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
                    in_hue = (hue_from[0] <= hh <= hue_from[1]) if hue_from[0] <= hue_from[1] else (hh >= hue_from[0] or hh <= hue_from[1])
                    if in_hue and ss > sat_min and val_min < vv < val_max:
                        nr, ng, nb = colorsys.hsv_to_rgb(hue_to / 360.0, ss, vv)
                        px[x, y] = (int(nr * 255), int(ng * 255), int(nb * 255), a)
                        changed += 1
            img.save(str(f))
            print(f"  {f.name}: {changed} pixels shifted")
        # Step 4: replace all frames
        for f in sorted(temp_dir.iterdir()):
            if not f.name.endswith(".png"):
                continue
            frame_str = f.stem.rsplit("_", 1)[-1]
            try:
                frame = int(frame_str)
            except ValueError:
                continue
            cmd_sprite_replace(game_file, dst_name, str(f), frame=frame)
    finally:
        shutil.rmtree(str(temp_dir), ignore_errors=True)
    print(f"✓ {src_name} → {dst_name}: hue shift {hue_from[0]*360:.0f}°-{hue_from[1]*360:.0f}° → {hue_to}°")


def cmd_texture_export(game_file: Path, texture_name: str | None, output_dir: str) -> None:
    """Export embedded texture(s) as PNG.

    If texture_name is None, export all (via UTMT CLI dump -t).
    If texture_name is given, export single texture (via CSX).
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    if texture_name is None:
        # Export all textures via UTMT CLI dump -t
        cmd = ["dotnet", _find_utmt_cli(), "dump", str(_effective_game_file(game_file)), "-t", "-o", str(out_path)]
        subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=True)
        print(f"✓ 所有纹理已导出到: {out_path}")
    else:
        # Export single texture via CSX
        esc = _csx_escape(texture_name)
        esc_path = _csx_escape(str(out_path))
        csx = f'''
using UndertaleModLib.Util;
var tex = Data.EmbeddedTextures.ByName("{esc}");
if (tex == null) {{
    for (int i = 0; i < Data.EmbeddedTextures.Count; i++) {{
        if (Data.EmbeddedTextures[i].Name.Content.IndexOf("{esc}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            tex = Data.EmbeddedTextures[i];
            break;
        }}
    }}
}}
if (tex == null) {{
    ScriptMessage("ERROR: Texture not found: {esc}");
    return;
}}
string outPath = "{esc_path}";
System.IO.Directory.CreateDirectory(outPath);
string fp = System.IO.Path.Combine(outPath, tex.Name.Content + ".png");
if (tex.TextureData?.Image != null) {{
    using var fs = new System.IO.FileStream(fp, System.IO.FileMode.Create);
    tex.TextureData.Image.SavePng(fs);
    ScriptMessage("OK: Exported " + tex.Name.Content + " → " + fp);
}} else {{
    ScriptMessage("ERROR: Texture has no image data");
}}
'''
        out = _run_utmt(csx, game_file, save=False)
        for line in _parse_msg(out):
            if line.startswith("ERROR:"):
                print(line, file=sys.stderr)
            elif line.startswith("OK:"):
                print(line)
            else:
                print(line)


def cmd_texture_replace(game_file: Path, texture_name: str, png_path: str) -> None:
    """Replace an embedded texture with a PNG file (via UTMT CLI replace -t)."""
    p = Path(png_path)
    if not p.exists():
        raise NotFoundError(f"文件不存在: {png_path}")
    cli = _find_utmt_cli()
    target = _resolve_write_target(game_file)
    _before = _md5_file(target)
    if not state.SANDBOX_ACTIVE:
        backup_file(target)
    cmd = ["dotnet", cli, "replace", str(target), "-t", f"{texture_name}={png_path}", "-o", str(target)]
    subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=True)
    _after = _md5_file(target)
    _scope = "仅沙箱副本" if state.SANDBOX_ACTIVE else "真实文件（目标即 Steam 路径，无需同步）"
    print(f"📝 写入回执: {target}")
    print(f"   MD5: {_before[:12]}… → {_after[:12]}… | 范围: {_scope}")
    if state.SANDBOX_ACTIVE:
        print("   应用: --commit 直写 或 sandbox-restore；放弃: 直接删除 *.sandbox")
    else:
        print("   退路: undo --value data_win / list-backups")
    print(f"✓ {texture_name} 已替换: {png_path}")


def cmd_sprite_dump_all(game_file: Path, output_dir: str) -> None:
    """Dump ALL sprites as PNGs to a directory (via UTMT CLI dump --sprites)."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    cli = _find_utmt_cli()
    cmd = ["dotnet", cli, "dump", str(_effective_game_file(game_file)), "--sprites", "-o", str(out_path)]
    subprocess.run(cmd, capture_output=True, text=True, timeout=600, check=True)
    print(f"✓ 所有精灵已导出到: {out_path}")


# ============================================================
# C3b: 中文字体注入（方案 B —— 侦察报告 AUDIT_2026-11-07/C3b侦察-字体/）
# ============================================================

# pass1（只读）：dump 源字体行式元数据 + 共享纹理页 PNG 到 work_dir
_CJK_PASS1_CSX = r'''// C3b pass1 (READ-ONLY): dump source fonts metadata + shared texture page
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
string dumpDir = @"__WORKDIR__";
string[] srcNames = { "fnt_main", "fnt_maintext", "fnt_plain" };
try {
    // 幂等守卫（S6 页内栈）：ja_maintext 被共享表替换过（glyph 数 >1000）即已注入
    var jaTextChk = Data.Fonts.FirstOrDefault(f => f.Name != null && f.Name.Content == "fnt_ja_maintext");
    if (jaTextChk != null && jaTextChk.Glyphs.Count > 1000) {
        ScriptMessage("ERROR: CJK 页内栈已注入（fnt_ja_maintext glyph=" + jaTextChk.Glyphs.Count + "）——先 experiment-restore/undo 回滚");
        return;
    }
    var sb = new System.Text.StringBuilder();
    UndertaleEmbeddedTexture page = null;
    foreach (string nm in srcNames) {
        var f = Data.Fonts.FirstOrDefault(x => x.Name != null && x.Name.Content == nm);
        if (f == null || f.Texture == null) { ScriptMessage("ERROR: font not found: " + nm); return; }
        var tpi = f.Texture;
        var emb = tpi.TexturePage;
        if (emb == null || emb.TextureData == null) { ScriptMessage("ERROR: no texture page for " + nm); return; }
        if (page == null) { page = emb; }
        else if (page != emb) { ScriptMessage("ERROR: 源字体不在同一纹理页（MVP 仅支持共享页布局）"); return; }
        sb.AppendLine("PAGE " + nm + " " + tpi.SourceX + " " + tpi.SourceY + " " + tpi.SourceWidth + " " + tpi.SourceHeight
                      + " " + emb.TextureData.Width + " " + emb.TextureData.Height);
        sb.AppendLine("FONT " + nm + " " + f.EmSize + " " + (f.EmSizeIsFloat ? 1 : 0) + " " + f.Charset + " "
                      + f.AntiAliasing + " " + f.LineHeight + " " + f.Ascender + " " + f.AscenderOffset + " "
                      + f.RangeStart + " " + f.RangeEnd + " " + (f.Bold ? 1 : 0) + " "
                      + tpi.SourceX + " " + tpi.SourceY + " " + tpi.SourceWidth + " " + tpi.SourceHeight);
        foreach (var g in f.Glyphs) {
            string kern = "";
            foreach (var k in g.Kerning) kern += " " + k.Character + ":" + k.ShiftModifier;
            sb.AppendLine("GLYPH " + nm + " " + g.Character + " " + g.SourceX + " " + g.SourceY + " "
                          + g.SourceWidth + " " + g.SourceHeight + " " + g.Offset + " " + g.Shift + " "
                          + g.Kerning.Count + kern);
        }
    }
    File.WriteAllText(Path.Combine(dumpDir, "fonts.txt"), sb.ToString());
    using (var fs = File.Create(Path.Combine(dumpDir, "emb_page.png"))) {
        page.TextureData.Image.SavePng(fs);
    }
    // S6：另 dump emb20（ja 字体共享页）——页内重排换页（font_emb20_compose）的底图
    var tex20 = Data.EmbeddedTextures.FirstOrDefault(t => t.Name != null && t.Name.Content == "Texture 20");
    if (tex20 == null || tex20.TextureData == null) { ScriptMessage("ERROR: Texture 20 not found"); return; }
    using (var fs = File.Create(Path.Combine(dumpDir, "emb20_page.png"))) {
        tex20.TextureData.Image.SavePng(fs);
    }
    ScriptMessage("CJK_PASS1_OK fonts=" + srcNames.Length + " page=" + page.TextureData.Width + "x" + page.TextureData.Height
                  + " emb20=" + tex20.TextureData.Width + "x" + tex20.TextureData.Height);
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.GetType().Name + ": " + ex.Message);
}'''

# pass2（写入）：新 EmbeddedTexture×2 + TexturePageItem×3 + UndertaleFont×3
#              + scr_setfont 加 zh 分支（方案 B 唯一代码改动点）
_CJK_PASS2_CSX = r'''// C3b S6 pass2 (WRITE): 中文页内重排栈（B4 实证形态，AUDIT 报告 §九）
//   emb20 象限换页（页身份不变）+ fnt_ja_maintext 重指向 TPI#6543 + 共享表 4064 字形
//   + scr_setfont 单行映射（槽位判重）+ preload 无条件 prefetch
//   ⚠️ 守卫不能 Contains "newfont = fnt_ja_maintext;"（基线 ja 分支本就含，恒真陷阱）
using System;
using System.IO;
using System.Linq;
using UndertaleModLib.Util;   // GMImage.FromPng(byte[], bool verifyHeader)
string workDir = @"__WORKDIR__";
try {
    // ── 0) 幂等守卫（计数式：基线 ja 分支含 1 处 fnt_ja_maintext 映射）──
    var sfChk = GetDecompiledText("gml_Script_scr_setfont");
    int nMap = sfChk.Split(new[]{"newfont = fnt_ja_maintext;"}, StringSplitOptions.None).Length - 1;
    if (nMap > 1) { ScriptMessage("ERROR: CJK 映射已存在（n=" + nMap + "）——先回滚"); return; }
    var jaText = Data.Fonts.FirstOrDefault(f => f.Name != null && f.Name.Content == "fnt_ja_maintext");
    if (jaText == null) { ScriptMessage("ERROR: fnt_ja_maintext not found"); return; }
    if (jaText.Glyphs.Count > 1000) { ScriptMessage("ERROR: 共享表已注入（glyph=" + jaText.Glyphs.Count + "）"); return; }

    // ── 1) emb20 象限换页（页身份不变；换页底图已由 font_emb20_compose 离线合成并 --verify）──
    byte[] png20 = File.ReadAllBytes(Path.Combine(workDir, "emb20_page_new.png"));
    var img20 = GMImage.FromPng(png20, false);
    var tex20 = Data.EmbeddedTextures.FirstOrDefault(t => t.Name != null && t.Name.Content == "Texture 20");
    if (tex20 == null || tex20.TextureData == null || tex20.TextureData.Width != 2048) {
        ScriptMessage("ERROR: Texture 20 缺失或尺寸异常"); return;
    }
    tex20.TextureData.Image = img20;

    // ── 2) fnt_ja_maintext：TPI 重指向 #6543（(0,1024) 1024² 象限）+ 共享表 ──
    var tpi = Data.TexturePageItems.FirstOrDefault(t => t.SourceX == 0 && t.SourceY == 1024
                    && t.SourceWidth == 1024 && t.SourceHeight == 1024 && t.TexturePage == tex20);
    if (tpi == null) { ScriptMessage("ERROR: TPI#6543 not found"); return; }
    jaText.Texture = tpi;
    var spec = System.Text.Json.JsonDocument.Parse(
        File.ReadAllText(Path.Combine(workDir, "glyphs_inpage.json"))).RootElement;
    jaText.Glyphs.Clear();
    int n = 0;
    foreach (var ge in spec.GetProperty("glyphs").EnumerateArray()) {
        var g = new UndertaleFont.Glyph();
        g.Character = (ushort)ge[0].GetInt32();
        g.SourceX = (ushort)ge[1].GetInt32();
        g.SourceY = (ushort)ge[2].GetInt32();
        g.SourceWidth = (ushort)ge[3].GetInt32();
        g.SourceHeight = (ushort)ge[4].GetInt32();
        g.Offset = (short)ge[5].GetInt32();
        g.Shift = (short)ge[6].GetInt32();
        g.UnknownAlwaysZero = 0;
        jaText.Glyphs.Add(g);
        n++;
    }
    // 排序/去重不变量（RV-B）：引擎字形查找假定按码点有序
    var codes = jaText.Glyphs.Select(x => (int)x.Character).ToList();
    if (!codes.SequenceEqual(codes.OrderBy(c => c)) || codes.Distinct().Count() != codes.Count) {
        ScriptMessage("ERROR: glyph 表排序/去重不变量破坏"); return;
    }

    // ── 3) scr_setfont 单行映射（唯一代码改动点；计数判重见守卫）──
    var sf = Data.Code.ByName("gml_Script_scr_setfont");
    string sgml = GetDecompiledText("gml_Script_scr_setfont");
    int anchor = sgml.IndexOf("draw_set_font(newfont);");
    if (anchor < 0) { ScriptMessage("ERROR: setfont anchor missing"); return; }
    sgml = sgml.Insert(anchor, "// CJK_MAP\nif (newfont == fnt_maintext) { newfont = fnt_ja_maintext; }\n");
    var ig1 = new CodeImportGroup(Data) { MainThreadAction = MainThreadAction };
    ig1.QueueReplace(sf, sgml);
    ig1.Import();

    // ── 4) preload 无条件 prefetch（既有页）──
    var pc = Data.Code.ByName("gml_Script_scr_preload_textures");
    string pgml = GetDecompiledText("gml_Script_scr_preload_textures");
    int pcAnchor = pgml.IndexOf("sprite_prefetch(spr_maincharad);");
    if (pcAnchor < 0) { ScriptMessage("ERROR: preload anchor missing"); return; }
    int nPre = pgml.Split(new[]{"sprite_prefetch(spr_fonts_ja_preload);"}, StringSplitOptions.None).Length - 1;
    if (nPre > 1 || pgml.Contains("// CJK_UNCOND")) { ScriptMessage("ERROR: preload 已有无条件分支（n=" + nPre + "）"); return; }
    pgml = pgml.Insert(pcAnchor, "sprite_prefetch(spr_fonts_ja_preload); // CJK_UNCOND\n");
    var ig2 = new CodeImportGroup(Data) { MainThreadAction = MainThreadAction };
    ig2.QueueReplace(pc, pgml);
    ig2.Import();

    ScriptMessage("CJK_PASS2_OK glyphs=" + n + " tpi=(0,1024) setfont_map=1 preload_uncond=1");
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.GetType().Name + ": " + ex.Message);
}''' 


def _build_cjk_pass1_csx(work_dir: str) -> str:
    """pass1 CSX（work_dir 占位替换；纯函数，供 golden 钉形）。"""
    return _CJK_PASS1_CSX.replace("__WORKDIR__", work_dir)


def _build_cjk_pass2_csx(work_dir: str) -> str:
    """pass2 CSX（work_dir 占位替换；纯函数，供 golden 钉形）。"""
    return _CJK_PASS2_CSX.replace("__WORKDIR__", work_dir)


def cmd_cjk_font(game_file: Path, build_dir: Path,
                 work_dir: Path = None, skip_pass1: bool = False) -> bool:
    """C3b S6：中文页内重排注入（B4 实证栈，AUDIT 报告 §九）。五步管线：

    1. pass1（只读 CSX）：dump 源字体元数据 + emb19 页 + emb20 页 PNG → work_dir
    2. tools/font_cjk_atlas.py --mode in-page：ASCII 拷贝 + CJK 排版 → 1024² 共享图集
    3. tools/font_emb20_compose.py --verify：emb20 象限合成（页身份不变；像素 diff 自证）
    4. pass2（写 CSX，默认沙箱）：emb20 换页 + fnt_ja_maintext@TPI6543 共享表 4064 字形
       + scr_setfont 单行映射（计数守卫）+ preload 无条件 prefetch
    5. verify-code gml_Script_scr_setfont（域F 教训：代码改动必须字节级体检）

    build_dir 为 tools/font_cjk_build.py 的输出（meta.json/glyphs.json/cjk_page_*.png）。
    约束：不新增字体资产（fonts=20 不变）；不新增纹理页（约束④：新页不被字体渲染器加载）。
    对话触发块生成见 cjk-trigger 命令；游戏内渲染已由 B4 boot 实证（`* B4中文测试ABC`）。
    """
    import json as _json
    work_dir = work_dir or (game_file.parent / "cjk_work")
    work_dir.mkdir(parents=True, exist_ok=True)

    # 1) build_dir 校验
    meta_path = build_dir / "meta.json"
    if not meta_path.exists():
        raise RuntimeError(f"缺 {meta_path}——先运行 tools/font_cjk_build.py 生成字形页")
    meta = _json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("px") != 12 or meta.get("cell") != 13:
        raise RuntimeError(f"build_dir 度量不符（px={meta.get('px')} cell={meta.get('cell')}，"
                           f"需 12/13）——重新运行 font_cjk_build.py")
    if not (build_dir / "glyphs.json").exists() or not (build_dir / "cjk_page_0.png").exists():
        raise RuntimeError(f"build_dir 缺 glyphs.json/cjk_page_*.png: {build_dir}")

    # 2) pass1（只读）
    if not skip_pass1:
        out = _run_utmt(_build_cjk_pass1_csx(str(work_dir)), game_file, save=False)
        if "CJK_PASS1_OK" not in out:
            raise RuntimeError(f"pass1 失败（未注入任何内容）：\\n{out}")

    # 3) 共享图集构建（in-page 模式，纯 Python，确定性）
    atlas_tool = Path(__file__).resolve().parent.parent / "tools" / "font_cjk_atlas.py"
    r = subprocess.run(
        [sys.executable, str(atlas_tool),
         "--build-dir", str(build_dir), "--pass1-dir", str(work_dir),
         "--out-dir", str(work_dir), "--mode", "in-page"],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("图集构建失败：\\n" + r.stdout + r.stderr)
    print(r.stdout.strip())

    # 4) emb20 象限合成（像素 diff 自证；越界变化 → 硬失败）
    compose_tool = Path(__file__).resolve().parent.parent / "tools" / "font_emb20_compose.py"
    r = subprocess.run(
        [sys.executable, str(compose_tool),
         "--emb20", str(work_dir / "emb20_page.png"),
         "--atlas", str(work_dir / "font_atlas_inpage.png"),
         "--out", str(work_dir / "emb20_page_new.png"), "--verify"],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("emb20 合成失败：\\n" + r.stdout + r.stderr)
    print(r.stdout.strip())

    # 5) pass2（写，默认沙箱）
    out = _run_utmt(_build_cjk_pass2_csx(str(work_dir)), game_file, save=True)
    if "CJK_PASS2_OK" not in out:
        raise RuntimeError(f"pass2 失败（沙箱未变更/回退）：\\n{out}")

    # 6) scr_setfont 字节级体检（WARN/不稳定 → 返回 False）
    print("→ verify-code gml_Script_scr_setfont（域F 协议）")
    return cmd_verify_code(game_file, "gml_Script_scr_setfont")


# ============================================================
# C3b S6：CJK 折行 util + 对话触发块生成器
# ============================================================

# typer → (spacing, writingxend)；spacing = writer 逐字推进常数（SCR_TEXTSETUP arg8）。
# 只收录经 B3/B4 实证或 SCR_TEXTTYPE 反编译核对过几何的 typer。
CJK_TYPER_TABLE = {
    31: (12, 9999),   # fnt_maintext, x+20 起步，无自动折行（B4 主臂实证）
    5: (8, 290),      # fnt_maintext, 标准对话（引擎按 writingxend 自动折行）
    3: (10, 100),     # fnt_curs, writingy 在框上缘外（设计性）
    2: (9, 190),      # fnt_plain
    68: (9, 500),     # fnt_plain, c_white
    30: (20, 9999),   # fnt_main, 大间距无折行
}


def cjk_wrap_text(text: str, chars_per_line: int) -> str:
    """按 writer 均匀步距模型折行：typer 的 spacing 对每个字符一视同仁
    （Draw_0 逐字符 letterx += spacing，空格也占一格），故一格 = 一字符。

    规则：
    - ASCII 词 [A-Za-z0-9'] 整体打包不切分（超长词硬切）；CJK 逐字可断
    - 断行处空格吞掉（rstrip），行中空格占格
    - 已有的 "&"（writer 硬换行）重置行计数；行间插 "&"（SCR_NEWLINE 标记）
    - 短于限宽原样返回
    """
    if chars_per_line <= 0 or not text:
        return text
    out = []
    for seg in text.split("&"):
        if seg == "":
            out.append("")               # 保留显式空行（"&&"）
            continue
        # 词元化：ASCII 词整体 / 单个非 ASCII 字符 / 空格
        tokens = []
        i = 0
        while i < len(seg):
            ch = seg[i]
            if ch == " ":
                tokens.append(" ")
                i += 1
            elif ch.isascii() and (ch.isalnum() or ch == "'"):
                j = i
                while j < len(seg) and seg[j].isascii() and (seg[j].isalnum() or seg[j] == "'"):
                    j += 1
                tokens.append(seg[i:j])
                i = j
            else:
                tokens.append(ch)
                i += 1
        cur = ""
        for tok in tokens:
            if tok == " ":
                if cur:
                    cur += tok       # 行尾空格暂挂，落行时 rstrip
                continue
            if len(tok) > chars_per_line:
                if cur:
                    out.append(cur.rstrip(" "))
                w = tok
                while len(w) > chars_per_line:
                    out.append(w[:chars_per_line])
                    w = w[chars_per_line:]
                cur = w
                continue
            if len(cur) + len(tok) <= chars_per_line:   # cur 含试探性尾随空格
                cur += tok
            else:
                out.append(cur.rstrip(" "))
                cur = tok
        if cur:
            out.append(cur.rstrip(" "))
    return "&".join(out)


def _gml_escape(text: str) -> str:
    """GML 字符串字面量转义：反斜杠 1→2、双引号 → \"（GML 层）。"""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _csx_escape(text: str) -> str:
    """C# 常规字符串字面量转义：反斜杠/双引号/真实换行（CSX 宿主层）。

    嵌套次序：原始文本 → _gml_escape（GML 层）→ _csx_escape（C# 层）。
    C# 反转义后即得 GML 转义形态，GML 反转义后即得原始文本。
    """
    return (text.replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t"))


def _build_cjk_trigger_csx(room_name: str, obj_name: str, x: int, y: int,
                           typer: int, text: str, wrap: bool = True,
                           width_room_px: int = None) -> str:
    """生成单个 CJK 对话触发块 CSX（追加到 obj_<名>_Step_1）。

    触发块形态 = B4 实证全形态（缺一即幽灵框/空框，见 AUDIT §八/§九）：
    msc=0 / typer / facechoice=3 / faceemotion=0 / msg[0] 带 "/%%" 终止符 /
    msg[1]="%%%" / id 守卫三连 / distance<60。
    typer 必须在 CJK_TYPER_TABLE 内（几何未核对的 typer 拒绝）。
    位置硬校验：0 <= x < 320（房间宽 320——越界即物理不可触发，B2 教训）。
    """
    if typer not in CJK_TYPER_TABLE:
        raise RuntimeError(f"typer {typer} 几何未核对（合法值："
                           f"{sorted(CJK_TYPER_TABLE)}）——查 SCR_TEXTTYPE 后再加表")
    if not (0 <= x < 320 and 0 <= y < 480):
        raise RuntimeError(f"触发位 ({x},{y}) 越界——房间 320×480，越界即不可触发"
                           f"（B2 教训：报告 §九）")
    if not text or not text.strip():
        raise RuntimeError("text 为空")
    if "\n" in text or "\r" in text:
        raise RuntimeError("text 含真实换行——多行对话请用 writer 硬换行标记 & 或拆多条触发块")
    if "\t" in text:
        raise RuntimeError("text 含制表符——writer 无此字形，请改空格")
    # 终止符摘出（折行不得劈开 "/%%"），中部 writer 专用字符校验
    terminator = ""
    if text.endswith("/%%"):
        text, terminator = text[:-3], "/%%"
    for ch in ("/", "%"):
        if ch in text:
            raise RuntimeError(f"text 含 writer 专用字符 {ch!r}（halt/翻页语义）——"
                               f"请改写文本（百分号用中文表述）")
    if wrap:
        spacing, wxend = CJK_TYPER_TABLE[typer]
        if width_room_px is None:
            # typer31 无引擎折行（wxend=9999）→ 默认按标准框宽 202（view+290 − view+88）
            width_room_px = 202
        if 0 < wxend < 9000:                       # 引擎会按 wxend 二次折行 → 预折行不超它
            width_room_px = min(width_room_px, wxend)
        text = cjk_wrap_text(text, max(1, width_room_px // spacing))
    text = text + terminator
    if not text.endswith("/%%"):
        text = text + "/%%"
    gml_text = _csx_escape(_gml_escape(text))
    step_name = f"gml_Object_{obj_name}_Step_1"
    return f'''// C3b S6 cjk-trigger：CJK 对话触发块（B4 实证全形态）
using System;
using System.Linq;
try {{
    var room = Data.Rooms.First(r => r.Name.Content == "{room_name}");
    var obj = Data.GameObjects.First(o => o.Name.Content == "{obj_name}");
    string stepName = "{step_name}";
    var stepCode = Data.Code.ByName(stepName);
    string tgml = GetDecompiledText(stepName);
    if (tgml.Contains("CJK_TRIGGER")) {{ ScriptMessage("ERROR: CJK 触发块已存在——先回滚"); return; }}
    // 幂等守卫（计数式）：ja_maintext 共享表未注入则拒绝（触发块依赖 CJK 栈）
    var jaText = Data.Fonts.FirstOrDefault(f => f.Name != null && f.Name.Content == "fnt_ja_maintext");
    if (jaText == null || jaText.Glyphs.Count <= 1000) {{
        ScriptMessage("ERROR: CJK 页内栈未注入——先运行 cjk-font"); return;
    }}
    uint iid = Data.GeneralInfo.LastObj;
    Data.GeneralInfo.LastObj = iid + 1;
    var inst = new UndertaleRoom.GameObject();
    inst.InstanceID = iid;
    inst.X = {x}; inst.Y = {y};
    inst.ObjectDefinition = obj;
    room.GameObjects.Add(inst);
    string block = ""
        + "if (id == " + iid + " && !instance_exists(obj_dialoguer) && !instance_exists(OBJ_WRITER) && !instance_exists(obj_choicer))\\n"
        + "{{\\n"
        + "    if (distance_to_object(obj_mainchara) < 60)\\n"
        + "    {{\\n"
        + "        global.msc = 0;\\n"
        + "        global.typer = {typer};\\n"
        + "        global.facechoice = 3;\\n        global.faceemotion = 0;\\n"
        + "        global.msg[0] = \\"{gml_text}\\";\\n"
        + "        global.msg[1] = \\"%%%\\";\\n"
        + "        instance_create(0, 0, obj_dialoguer);\\n"
        + "    }}\\n"
        + "}}\\n"
        + "// CJK_TRIGGER\\n";
    tgml = tgml + "\\n" + block;
    var ig = new CodeImportGroup(Data) {{ MainThreadAction = MainThreadAction }};
    ig.QueueReplace(stepCode, tgml);
    ig.Import();
    ScriptMessage("CJK_TRIGGER_OK id=" + iid + " typer={typer} @({x},{y})");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.GetType().Name + ": " + ex.Message);
}}'''


def cmd_cjk_trigger(game_file: Path, room_name: str, obj_name: str, x: int, y: int,
                    typer: int, text: str, wrap: bool = True,
                    width_room_px: int = None) -> bool:
    """C3b S6：注入单个 CJK 对话触发块（默认沙箱）+ 触发后体检。"""
    csx = _build_cjk_trigger_csx(room_name, obj_name, x, y, typer, text, wrap, width_room_px)
    out = _run_utmt(csx, game_file, save=True)
    if "CJK_TRIGGER_OK" not in out:
        raise RuntimeError(f"cjk-trigger 失败（沙箱未变更/回退）：\\n{out}")
    print(out.strip().splitlines()[-1])
    step_name = f"gml_Object_{obj_name}_Step_1"
    print(f"→ verify-code {step_name}（域F 协议）")
    return cmd_verify_code(game_file, step_name)


# ============================================================
# Main
# ============================================================

def cmd_room_list(args_filter: str = "") -> None:
    _load_rooms()
    items = sorted(rooms_data.ROOMS.items(), key=lambda x: int(x[0]))
    for rid, name in items:
        if args_filter:
            if args_filter.lower() in name.lower():
                pass
            elif args_filter == rid or (args_filter.isdigit() and int(args_filter) == int(rid)):
                pass
            else:
                continue
        print(f"  [{rid:>3}] {name}")


# ============================================================
# O2 迁移 re-export 区（各域命令经此保持 ms.* 兼容面与 dispatch 裸名调用；
# 本区只许 import + re-export——A8 兼容面/活提取测试反向锁死）
# ============================================================
from deterline.cmds.dialogue import (cmd_strg_list, cmd_strg_get,  # noqa: F401
                                     cmd_strg_set, cmd_strg_add,
                                     cmd_strg_delete, cmd_strg_replace,
                                     cmd_strg_search, cmd_textdata_search,
                                     _validate_facechoice, _inject_face_control,
                                     cmd_textdata_add, cmd_guided_add_dialogue,
                                     cmd_textdata_delete, cmd_textdata_update,
                                     cmd_search_sctext, cmd_quest_init,
                                     cmd_quest_status, cmd_batch_textdata)
from deterline.cmds.code import (cmd_code_list, cmd_code_decompile,  # noqa: F401
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


def main():
    parser = argparse.ArgumentParser(
        description="UNDERTALE Save Editor — 修改 undertale.ini / file0",
        epilog="""
示例:
  %(prog)s --action get  --key Love
  %(prog)s --action set  --key LOVE --value 20
  %(prog)s --action set  --key Kills --value 0
  %(prog)s --action set  --key Room --value 31
  %(prog)s --action set  --key Room --value "安黛因竞技场"
  %(prog)s --action list
  %(prog)s --action room-list
  %(prog)s --action room-list --value 瀑布
  %(prog)s --action reset-flags
  %(prog)s --action reset-all   # 全量重置（BOSS、物品、击杀、plot），保留自定义 flag
  %(prog)s --action set  --key HP  --value 99 --file file0
  %(prog)s --action get  --key HP  --file file0
  %(prog)s --action list --file file0
  %(prog)s --action set  --key WEAPON --value 51 --file file0   (自动 AT=99)
  %(prog)s --action set  --key TORIEL --value 5 --file file0    (宽恕)
  %(prog)s --action set  --key RUINS_KILLS --value 20 --file file0
  %(prog)s --action create-system-info --value 962
  
  # Dialogue editing (game.ios / data.win) — via UndertaleModTool
  %(prog)s --action list-strings --file data_win --limit 10
  %(prog)s --action get-string --key 500 --file data_win
  %(prog)s --action set-string --key 500 --value "Hello" --file data_win
  %(prog)s --action add-string --value "新对话内容" --file data_win
  %(prog)s --action delete-string --key 50000 --file data_win
  %(prog)s --action search-strings --value "Toriel" --file data_win
  %(prog)s --action replace-string --old "Toriel" --value "TORIEL" --file data_win
  
  # Code editing (game.ios / data.win) — via UndertaleModTool
  %(prog)s --action list-codes --file data_win --limit 10
  %(prog)s --action decompile-code --key "gml_Object_obj_dialoguer_Create_0" --file data_win
  %(prog)s --action replace-code --key "gml_Script_test" --value "return 0;" --file data_win
  %(prog)s --action replace-code --key "gml_Script_test" --value "./mycode.gml" --file-path --file data_win
  %(prog)s --action find-replace-code --key "gml_Object_obj_dialoguer_Step_0" --old "old_code" --value "new_code" --file data_win
  
  # Text data editing (game.ios / data.win) — via UndertaleModTool
  %(prog)s --action search-textdata --value "darksans1" --file data_win
  %(prog)s --action add-textentry --key "obj_myevent_001" --value "我的新对话/" --file data_win
  %(prog)s --action delete-textentry --key "obj_test_entry" --file data_win
  
  # Variable/code search
  %(prog)s --action search-vars --value "global.flag" --file data_win
  %(prog)s --action create-script --key "gml_Script_myFunc" --value "return 0;" --file data_win
  
  # Room inspection
  %(prog)s --action room-objects --value "torielroom" --file data_win

  # Room layout editing
  %(prog)s --action spawn-obj --value "room_asrielroom" --key "obj_dummy1" --x 160 --y 120 --file data_win
  %(prog)s --action remove-obj --value "room_asrielroom" --instance 113930 --file data_win
  %(prog)s --action remove-obj --value "room_asrielroom" --key "obj_dummy1" --all --file data_win

  # Safe NPC dialogue (one-shot: spawn + textdata + flag-state trigger + Alarm_0 guard)
  %(prog)s --action npc-dialogue --value "room_torielroom" --key "obj_cactus" --x 170 --y 180 --text-key "obj_cactus_deterline" --text "* Stay determined!/%%" --file data_win
  # Guard an existing NPC whose myinteract trigger overlaps native dialogue
  %(prog)s --action guard-npc-alarm --key "obj_cactus" --instance 113927 --text-key "obj_cactus_deterline" --file data_win
  # Single-trigger NPC dialogue (NPC self-destructs after trigger; no movement lock)
  %(prog)s --action npc-dialogue --value "room_asrielroom" --key "obj_dummy1" --x 170 --y 180 --text-key "obj_dummy_hi" --text "* Hi!/%%" --once --file data_win
  # Choice NPC: YES/NO box + follow-up texts + teleport on YES (single-trigger by default)
  %(prog)s --action npc-choice --value "room_water_undynefinal" --key "obj_kitchentable" --x 160 --y 420 --text-key "obj_table_ask" --text "* Let's go?& &         Yes         No      \\C " --yes-text-key "obj_table_yes" --yes-text "* Okay!/%%" --no-text-key "obj_table_no" --no-text "* .../%%" --goto "雪镇 - 船夫(妇)" --item 48 --range 160 --file data_win
  # Check for corrupted variable NameStringID (crash trap), --fix to repair
  %(prog)s --action verify-nsid --file data_win
  %(prog)s --action verify-nsid --fix --file data_win
  %(prog)s --action verify-instances --file data_win
  %(prog)s --action verify-instances --fix --file data_win

  # Lock LV-derived stats so the game stops recomputing them (writes file0 + patches game scripts)
  %(prog)s --action set-derived --key HP --value 50
  %(prog)s --action set-derived --key AT --value 99

  # Code append/prepend (新增，无需完全替换)
  %(prog)s --action append-code --key "gml_Object_obj_dummy1_Step_0" --value "if (global.flag[510]==99) instance_destroy();" --file data_win
  %(prog)s --action append-code --key "gml_Object_obj_dummy1_Step_0" --value "./append.gml" --file-path --file data_win
  %(prog)s --action prepend-code --key "gml_Object_obj_dummy1_Step_0" --value "// custom code here" --file data_win

  # Batch import dialogues from JSON
  %(prog)s --action batch-add-textentry --value "./dialogues.json" --face 3 --file data_win

  # Quest management
  %(prog)s --action quest-init
  %(prog)s --action quest-init --flag 511
  %(prog)s --action quest-status

  # SCR_TEXT case search
  %(prog)s --action search-sctext --value "Toriel" --file data_win
  
  # P4-1 Sprite/Texture replacement
  %(prog)s --action list-textures --file data_win --limit 10
  %(prog)s --action export-sprite --key "spr_sans_d" --value "sans.png" --frame 0 --file data_win
  %(prog)s --action replace-sprite --key "spr_sans_d" --value "sans_edit.png" --frame 0 --file data_win
  %(prog)s --action duplicate-sprite --key "spr_sans_d" --value "spr_sans_d_red" --file data_win
  %(prog)s --action colorize-sprite --key "spr_sans_d" --value "spr_sans_d_red" --hue-from "180-260" --hue-to 0 --file data_win
  %(prog)s --action preview-sprite --key "spr_sans_d" --file data_win
  %(prog)s --action export-texture --value "./textures" --file data_win
  %(prog)s --action replace-texture --key "Texture 0" --value "tex0.png" --file data_win
  %(prog)s --action dump-sprites --value "./sprites" --file data_win

  # Experiment snapshots (isolate experiments from each other)
  %(prog)s --action experiment-snapshot --value "sans_face_test"
  %(prog)s --action experiment-list
  %(prog)s --action experiment-restore --value "sans_face_test"

  # Backups
  %(prog)s --action list-backups --value data_win
  %(prog)s --action undo --value data_win --backup 20240714_193500
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--action", required=True,
                        choices=["get", "set", "list", "find", "reset-flags", "reset-all",
                                 "room-list", "create-system-info", "undo",
                                 "list-backups",
                                 "list-strings", "get-string", "set-string",
                                 "add-string", "delete-string",
                                 "replace-string", "search-strings",
                                 "list-codes", "decompile-code",
                                 "replace-code", "find-replace-code",
                                 "append-code", "prepend-code",
                                  "search-textdata", "add-textentry", "update-textentry",
                                  "delete-textentry",
                                   "batch-add-textentry",
                                   "guided-add-dialogue",
                                 "search-vars", "search-code", "create-script",
                                   "room-objects", "search-sctext",
                                    "spawn-obj", "remove-obj",
                                    "npc-dialogue", "npc-choice", "guard-npc-alarm",
                                   "quest-init", "quest-status",
                                   "sandbox-restore",
                                   "list-sprites", "search-sprite",
                                   "get-obj", "set-obj-sprite",
                                   "list-textures", "export-sprite",
                                   "replace-sprite", "duplicate-sprite",
                                   "preview-sprite", "colorize-sprite",
                                   "export-texture", "replace-texture",
                                   "dump-sprites",
                                    "experiment-snapshot", "experiment-list",
                                    "experiment-restore",
                                    "room-info", "create-room",
                                    "set-room-bg", "set-room-prop", "set-room-view",
                                    "list-game-bgs", "create-bg-asset",
                                    "gml-bg", "set-room-solid-bg", "room-bg-info",
                                     "remove-tile",
                                     "handler-extract",
                                     "create-door",
                                     "list-doors",
                                     "remove-door",
                                     "create-pit",
                                     "create-battle",
                                     "verify-nsid", "verify-instances", "verify-code", "smoke-test", "diff-snapshots", "set-derived",
                                     "cjk-font", "cjk-trigger", "md5"])
    parser.add_argument("--key", help="键名或数字索引 (file0 用数字)")
    parser.add_argument("--value", help="要设置/搜索的值 (set/find 操作必需)")
    parser.add_argument("--old", help="replace-string 的旧文本 (decompile-code 兼容别名，等同 --search)")
    parser.add_argument("--search", help="decompile-code: 仅显示匹配该文本的行 (等同行过滤)")
    parser.add_argument("--dry-run", action="store_true",
                        help="预览替换结果/匹配数，不写入文件 (replace-code/find-replace-code 用)")
    parser.add_argument("--section", default="General",
                        help="INI 节名 (默认: General)")
    parser.add_argument("--file", choices=["ini", "file0", "data_win"], default="ini",
                        help="目标文件 (默认: ini)")
    parser.add_argument("--dir", help="手动指定存档目录或游戏数据文件路径")
    parser.add_argument("--limit", type=int, default=30,
                        help="最大显示条数 (默认: 30)")
    parser.add_argument("--offset", type=int, default=0,
                        help="起始偏移 (list-strings 用)")
    parser.add_argument("--hex", action="store_true",
                        help="显示十六进制 (list-strings 用)")
    parser.add_argument("--file-path", action="store_true",
                        help="--value 是文件路径而非内联内容 (replace-code 用)")
    parser.add_argument("--backup", type=str, default=None,
                        help="备份时间戳 (undo 恢复到指定版本, list-backups 可查看)")
    parser.add_argument("--x", type=int, default=None,
                        help="X 坐标 (spawn-obj/create-door 用, 默认: 320)")
    parser.add_argument("--y", type=int, default=None,
                        help="Y 坐标 (spawn-obj/create-door 用, 默认: 240)")
    parser.add_argument("--spawn-x", type=int, default=160,
                        help="目标房间出生 X (create-door 用, 默认: 160)")
    parser.add_argument("--spawn-y", type=int, default=120,
                        help="目标房间出生 Y (create-door 用, 默认: 120)")
    parser.add_argument("--border", type=int, default=0,
                        help="战斗边框样式 (create-battle 用, 默认: 0)")
    parser.add_argument("--all", action="store_true",
                        help="移除所有匹配实例 (remove-obj 用)")
    parser.add_argument("--instance", type=int, default=None,
                        help="实例 ID (remove-obj 用, 优先级高于 --key 匹配)")
    parser.add_argument("--face", type=int, default=0,
                        help="头像角色 (0=无, 1=Toriel, 2=Flowey, 3=Sans, 4=Papyrus, 5=Undyne, 6=Alphys, 7=Asgore, 8=Mettaton, 9=Asriel)")
    parser.add_argument("--emotion", type=int, default=0,
                        help="头像表情 (Sans: 0=普通, 1=轻笑, 2=眨眼, 3=慢眨眼, 4=无眼)")
    parser.add_argument("--flag", type=int, default=None,
                        help="flag 索引 (quest-init 用, 默认 510)")
    parser.add_argument("--text-key", type=str, default=None,
                        help="textdata key (npc-dialogue/guard-npc-alarm/npc-choice 用)")
    parser.add_argument("--text", type=str, default=None,
                        help="对话文本 (npc-dialogue 用 ASCII；cjk-trigger 用 CJK，触发框全形态+预折行自动补全)")
    parser.add_argument("--yes-text-key", type=str, default=None,
                        help="YES 分支 textdata key (npc-choice 用)")
    parser.add_argument("--yes-text", type=str, default=None,
                        help="YES 分支对话内容 ASCII (npc-choice 用)")
    parser.add_argument("--no-text-key", type=str, default=None,
                        help="NO 分支 textdata key (npc-choice 用, 必需)")
    parser.add_argument("--no-text", type=str, default=None,
                        help="NO 分支对话内容 ASCII (npc-choice 用, 必需)")
    parser.add_argument("--goto", type=str, default=None,
                        help="YES 分支传送目标房间（中文名/ID，npc-choice 用）")
    parser.add_argument("--item", type=int, default=None,
                        help="YES 分支奖励物品 ID (npc-choice 用, 0-65)")
    parser.add_argument("--range", type=int, default=50,
                        help="触发距离像素 (npc-dialogue/npc-choice 用, 默认: 50)")
    parser.add_argument("--repeat", action="store_true",
                        help="可重复触发（走开再靠近可再触发；npc-choice 用，默认单次）")
    parser.add_argument("--frame", type=int, default=None,
                        help="帧索引 (export-sprite/replace-sprite 用, 默认: replace 全部帧的 0 / export 全部帧到目录; "
                             "export 时 --value 以 .png 结尾则默认单帧导出到该文件)")
    parser.add_argument("--show-diff", action="store_true",
                        help="替换代码时显示新旧 diff (replace-code 用)")
    parser.add_argument("--json", action="store_true",
                        help="导出时同时输出 JSON 元数据 (export-sprite 用)")
    parser.add_argument("--hue-from", type=str, default=None,
                        help="色相范围 \"min-max\" (colorize-sprite 用, 如 \"180-260\")")
    parser.add_argument("--hue-to", type=float, default=None,
                        help="目标色相角度 0-360 (colorize-sprite 用)")
    parser.add_argument("--sandbox", action="store_true",
                        help="沙箱模式: 在 game.ios.sandbox 副本上操作（v2 起写操作默认即沙箱，此参数保留为显式声明）")
    parser.add_argument("--commit", action="store_true",
                        help="v2 写入安全: 直写真实文件（默认写操作只落沙箱副本）；含 Steam 同步")
    parser.add_argument("--no-steam-sync", action="store_true",
                        help="v2 写入安全: 即使 --commit 也不同步 Steam 路径")
    parser.add_argument("--allow-cjk", action="store_true",
                        help="C3a: 放行 CJK 对话文本（需中文字体注入支持，否则显示空白）")
    parser.add_argument("--asm", action="store_true",
                        help="verify-code: 输出完整反汇编文本（ASM| 行）")
    parser.add_argument("--work-dir", type=str, default=None,
                        help="cjk-font: 中间产物目录（pass1 dump/图集；默认 game 文件旁 cjk_work/）")
    parser.add_argument("--room", type=str, default="room_ruins1",
                        help="cjk-trigger: 目标房间名（默认 room_ruins1）")
    parser.add_argument("--object", type=str, default="obj_cactus",
                        help="cjk-trigger: 承载触发块的对象名（其 Step_1 被追加；默认 obj_cactus）")
    parser.add_argument("--typer", type=int, default=31,
                        help="cjk-trigger: SCR_TEXTTYPE 编号（默认 31 = fnt_maintext spacing12；须在 CJK_TYPER_TABLE）")
    # cjk-trigger 复用全局 --x/--y/--text/--width：x,y=触发位（x 须<320）、text=对话文本、width=预折行宽度(房间像素)
    parser.add_argument("--no-wrap", action="store_true",
                        help="cjk-trigger: 关闭预折行（默认开）")
    parser.add_argument("--auto-snapshot", action="store_true",
                        help="每次写入操作前自动创建实验快照")
    parser.add_argument("--apply", action="store_true",
                        help="应用模式 (handler-extract 用, 默认仅诊断)")
    parser.add_argument("--once", action="store_true",
                        help="单次触发（触发后 NPC 自毁消失；不锁移动——状态机形态 v2.3.0 已废弃）")
    parser.add_argument("--timeout", type=int, default=None,
                        help="smoke-test 轮询超时秒数 (默认 120)")
    parser.add_argument("--keys", type=str, default=None, choices=["external", "osascript"],
                        help="smoke-test 按键模式: external(默认,由调用方按键)/osascript(盲发 Z,需辅助功能权限)")
    parser.add_argument("--fix", action="store_true",
                        help="自动修复 (verify-nsid 用: 重置损坏变量的 NameStringID；verify-instances 用: 为 ID=0/重复实例分配唯一 ID)")

    # Room editing (P4-2)
    parser.add_argument("--width", type=int, default=None,
                        help="房间宽度 (create-room/set-room-prop)；cjk-trigger: 预折行宽度（房间像素，默认 typer31=202 且不超该 typer 的 writingxend）")
    parser.add_argument("--height", type=int, default=None,
                        help="房间高度 (create-room/set-room-prop 用)")
    parser.add_argument("--speed", type=int, default=None,
                        help="房间帧率 (create-room/set-room-prop 用)")
    parser.add_argument("--caption", type=str, default="",
                        help="房间标题 (create-room/set-room-prop 用)")
    parser.add_argument("--bg-color", type=str, default="000000",
                        help="背景色 hex RGB (create-room/set-room-prop 用, 默认: 000000)")
    parser.add_argument("--persistent", action="store_true",
                        help="房间是否持久化 (set-room-prop 用)")
    parser.add_argument("--bg", type=str, default=None,
                        help="背景资源名 (set-room-bg/gml-bg 用; create-bg-asset 的资产名走 --value, PNG 走 --image)")
    parser.add_argument("--index", type=int, default=0,
                        help="背景/视图层索引 (set-room-bg/set-room-view 用, 默认: 0)")
    parser.add_argument("--enable", type=str, default=None,
                        help="启用/禁用 bool (set-room-bg/set-room-view 用)")
    parser.add_argument("--foreground", type=str, default=None,
                        help="是否前景层 bool (set-room-bg 用)")
    parser.add_argument("--speedx", type=float, default=None,
                        help="背景水平视差速度 (set-room-bg 用)")
    parser.add_argument("--speedy", type=float, default=None,
                        help="背景垂直视差速度 (set-room-bg 用)")
    parser.add_argument("--tiled-h", type=str, default=None,
                        help="水平平铺 bool (set-room-bg 用)")
    parser.add_argument("--tiled-v", type=str, default=None,
                        help="垂直平铺 bool (set-room-bg 用)")
    parser.add_argument("--stretch", type=str, default=None,
                        help="拉伸 bool (set-room-bg 用)")
    parser.add_argument("--follow", type=str, default=None,
                        help="视角跟随对象 (set-room-view 用, 如 obj_mainchara)")
    parser.add_argument("--view-w", type=int, default=None,
                        help="视图宽度 (set-room-view 用)")
    parser.add_argument("--view-h", type=int, default=None,
                        help="视图高度 (set-room-view 用)")
    parser.add_argument("--port-w", type=int, default=None,
                        help="视口宽度 (set-room-view 用)")
    parser.add_argument("--port-h", type=int, default=None,
                        help="视口高度 (set-room-view 用)")
    parser.add_argument("--border-x", type=int, default=None,
                        help="视图跟随水平边界 (set-room-view 用)")
    parser.add_argument("--border-y", type=int, default=None,
                        help="视图跟随垂直边界 (set-room-view 用)")
    parser.add_argument("--image", type=str, default=None,
                        help="PNG 图片路径 (create-bg-asset 用)")
    parser.add_argument("--slot", type=int, default=0,
                        help="背景槽位索引 (gml-bg 用, 默认: 0)")
    parser.add_argument("--layers", type=str, default=None,
                        help="背景层索引列表, 逗号分隔 (gml-bg/set-room-solid-bg 用, 如 0,1)")
    parser.add_argument("--all-layers", action="store_true",
                        help="应用到全部 8 个背景层 (gml-bg 用)")
    parser.add_argument("--hide-above", action="store_true",
                        help="隐藏目标层之上的所有层, 防止遮挡 (gml-bg 用)")
    parser.add_argument("--keep-bg-color", action="store_true",
                        help="启用背景层时保留 DrawBackgroundColor (set-room-bg 用)")
    parser.add_argument("--color", type=str, default=None,
                        help="纯色 hex RGB, 6 位 (set-room-solid-bg 用, 如 0000FF)")
    parser.add_argument("--asset-name", type=str, default=None,
                        help="背景资源名 (set-room-solid-bg 用, 默认 bg_solid_<color>)")
    parser.add_argument("--no-runtime", action="store_true",
                        help="只改房间数据, 不注入运行时覆盖 (set-room-solid-bg 用)")
    args = parser.parse_args()

    # --x/--y default to None so remove-door can require explicit coordinates;
    # other commands keep the historical 320/240 default.
    x_explicit = args.x is not None
    y_explicit = args.y is not None
    # cjk-trigger 用原始 None 判定（其默认 220/330 与 spawn 的 320/240 不同）
    args.x_raw = args.x
    args.y_raw = args.y
    if args.x is None:
        args.x = 320
    if args.y is None:
        args.y = 240

    # Activate sandbox mode
    if args.sandbox and args.commit:
        print("错误: --sandbox 与 --commit 互斥（沙箱=彩排，commit=直写，二选一）", file=sys.stderr)
        sys.exit(2)
    if args.sandbox:
        state.SANDBOX_ACTIVE = True
    if args.commit:
        state.COMMIT_ACTIVE = True
    if getattr(args, "no_steam_sync", False):
        state.NO_STEAM_SYNC = True
    if getattr(args, "allow_cjk", False):
        state.ALLOW_CJK = True
    if args.auto_snapshot:
        state.AUTO_SNAPSHOT = True

    # Handle sandbox-restore before file-type checks
    if args.action == "sandbox-restore":
        try:
            game_file = find_game_data_file(args.dir)
            sandbox_path = game_file.with_suffix(game_file.suffix + ".sandbox")
            if not sandbox_path.exists():
                print(f"错误: 沙箱备份不存在: {sandbox_path}", file=sys.stderr)
                sys.exit(1)
            shutil.copy2(str(sandbox_path), str(game_file))
            sandbox_path.unlink()
            print(f"✓ 沙箱备份已恢复: {sandbox_path.name} → {game_file.name}")
        except FileNotFoundError as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # Handle md5 before file-type checks (read-only; prints game data file hash).
    # Lets a report include the raw hash so "did the file actually change?" is
    # verifiable in one line.
    if args.action == "md5":
        try:
            game_file = find_game_data_file(args.dir)
        except FileNotFoundError as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)
        digest = hashlib.md5(game_file.read_bytes()).hexdigest()
        print(f"{digest}  {game_file}")
        return

    # Handle set-derived before file-type checks (touches both file0 and data_win)
    if args.action == "set-derived":
        if args.key is None or args.value is None:
            parser.error("set-derived 需要 --key (HP/MAXHP/AT/DF) 和 --value")
        try:
            save_dir = find_save_dir(args.dir)
            game_file = find_game_data_file(args.dir)
        except FileNotFoundError as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)
        try:
            cmd_set_derived(save_dir, game_file, args.key, args.value)
        except (FileNotFoundError, ValueError, RuntimeError, DeterlineError) as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # ── Dialogue editor actions (data_win) ────────────────
    if args.file == "data_win":
        try:
            game_file = find_game_data_file(args.dir)
        except FileNotFoundError as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)

        if state.SANDBOX_ACTIVE:
            sandbox_path = game_file.with_suffix(game_file.suffix + ".sandbox")
            print(f"🔒 沙箱模式: 所有操作作用于 {sandbox_path.name}", file=sys.stderr)

        try:
            if args.action == "list-strings":
                cmd_strg_list(game_file, args.limit, args.offset, args.hex)
            elif args.action == "get-string":
                if args.key is None:
                    parser.error("--key 是必需的 (字符串索引)")
                cmd_strg_get(game_file, int(args.key))
            elif args.action == "set-string":
                if args.key is None or args.value is None:
                    parser.error("--key 和 --value 是必需的")
                cmd_strg_set(game_file, int(args.key), args.value)
            elif args.action == "add-string":
                if args.value is None:
                    parser.error("--value 是必需的 (新对话文本)")
                cmd_strg_add(game_file, args.value)
            elif args.action == "delete-string":
                if args.key is None:
                    parser.error("--key 是必需的 (要删除的索引)")
                cmd_strg_delete(game_file, int(args.key))
            elif args.action == "replace-string":
                if args.old is None or args.value is None:
                    parser.error("--old 和 --value 是必需的")
                cmd_strg_replace(game_file, args.old, args.value)
            elif args.action == "search-strings":
                if args.value is None:
                    parser.error("--value 是必需的 (搜索关键词)")
                cmd_strg_search(game_file, args.value, args.limit)
            elif args.action == "list-codes":
                cmd_code_list(game_file, args.limit, args.offset)
            elif args.action == "decompile-code":
                if args.key is None:
                    parser.error("--key 是必需的 (代码名称)")
                cmd_code_decompile(game_file, args.key, args.limit, search=args.search or args.old or "")
            elif args.action == "replace-code":
                if args.key is None or args.value is None:
                    parser.error("--key 和 --value 是必需的 (代码名称 + GML 源码或文件路径)")
                cmd_code_replace(game_file, args.key, args.value, value_is_file=args.file_path,
                                 show_diff=args.show_diff, dry_run=args.dry_run)
            elif args.action == "find-replace-code":
                if args.key is None or args.old is None or args.value is None:
                    parser.error("--key, --old 和 --value 是必需的")
                cmd_code_find_replace(game_file, args.key, args.old, args.value,
                                      show_diff=args.show_diff, dry_run=args.dry_run)
            elif args.action == "search-textdata":
                if args.value is None:
                    parser.error("--value 是必需的 (搜索关键词)")
                cmd_textdata_search(game_file, args.value, args.limit)
            elif args.action == "add-textentry":
                if args.key is None or args.value is None:
                    parser.error("--key 和 --value 是必需的")
                cmd_textdata_add(game_file, args.key, args.value,
                                 face=args.face, emotion=args.emotion)
            elif args.action == "guided-add-dialogue":
                if args.key is None or args.value is None:
                    parser.error("--key (文本 key) 和 --value (对话内容) 是必需的")
                cmd_guided_add_dialogue(game_file, args.key, args.value,
                                        face=args.face, emotion=args.emotion)
            elif args.action == "delete-textentry":
                if args.key is None:
                    parser.error("--key 是必需的 (要删除的 textdata key)")
                cmd_textdata_delete(game_file, args.key)
            elif args.action == "update-textentry":
                if args.key is None or args.value is None:
                    parser.error("--key 和 --value 是必需的 (已存在的 textdata key + 新文本)")
                cmd_textdata_update(game_file, args.key, args.value,
                                    face=args.face, emotion=args.emotion)
            elif args.action in ("search-vars", "search-code"):
                if args.value is None:
                    parser.error("--value 是必需的 (变量名/精灵名/任意代码片段)")
                cmd_search_vars(game_file, args.value, args.limit)
            elif args.action == "room-objects":
                if args.value is None:
                    parser.error("--value 是必需的 (房间内部名，如 torielroom)")
                cmd_room_objects(game_file, args.value)
            elif args.action == "create-script":
                if args.key is None or args.value is None:
                    parser.error("--key 和 --value 是必需的 (代码名 + GML 源码或文件路径)")
                cmd_create_script(game_file, args.key, args.value, value_is_file=args.file_path)
            elif args.action == "search-sctext":
                if args.value is None:
                    parser.error("--value 是必需的 (搜索关键词)")
                cmd_search_sctext(game_file, args.value, args.limit)
            elif args.action == "spawn-obj":
                if args.value is None or args.key is None:
                    parser.error("--value (房间名) 和 --key (对象名) 是必需的")
                cmd_spawn_obj(game_file, args.value, args.key, args.x, args.y)
            elif args.action == "npc-dialogue":
                if args.value is None or args.key is None:
                    parser.error("--value (房间名) 和 --key (对象名) 是必需的")
                if args.text_key is None or args.text is None:
                    parser.error("--text-key (textdata key) 和 --text (对话内容) 是必需的")
                cmd_npc_dialogue(game_file, args.value, args.key, args.x, args.y,
                                 args.text_key, args.text,
                                 face=args.face, emotion=args.emotion, once=args.once,
                                 range_=args.range)
            elif args.action == "npc-choice":
                if args.value is None or args.key is None:
                    parser.error("--value (房间名) 和 --key (对象名) 是必需的")
                if args.text_key is None or args.text is None:
                    parser.error("--text-key (选择文本 key) 和 --text (选择文本) 是必需的")
                cmd_npc_choice(game_file, args.value, args.key, args.x, args.y,
                               args.text_key, args.text,
                               yes_key=args.yes_text_key, yes_text=args.yes_text,
                               no_key=args.no_text_key, no_text=args.no_text,
                               face=args.face, emotion=args.emotion, range_=args.range,
                               goto_room=args.goto, item_id=args.item,
                               repeat=args.repeat)
            elif args.action == "guard-npc-alarm":
                if args.key is None or args.instance is None:
                    parser.error("--key (对象名) 和 --instance (实例 ID) 是必需的")
                cmd_guard_npc_alarm(game_file, args.key, args.instance, text_key=args.text_key)
            elif args.action == "verify-nsid":
                cmd_verify_nsid(game_file, fix=args.fix)
            elif args.action == "verify-instances":
                cmd_verify_instances(game_file, fix=args.fix)
            elif args.action == "verify-code":
                if args.key is None:
                    parser.error("--key (代码条目名) 是必需的")
                _stable = cmd_verify_code(game_file, args.key, show_asm=args.asm)
                if _stable is False:
                    sys.exit(1)  # 往返不稳定（WARN）必须非零退出
            elif args.action == "diff-snapshots":
                if args.key is None or args.value is None:
                    parser.error("--key (基线文件) 和 --value (对比文件) 是必需的")
                cmd_diff_snapshots(Path(args.key).expanduser(), Path(args.value).expanduser())
            elif args.action == "smoke-test":
                # 注意: --dir 在 data_win 语境下是游戏数据文件；存档目录固定走默认定位
                _ok = cmd_smoke_test(game_file, find_save_dir(None),
                               room_name=args.value or "room_torielroom",
                               obj_name=args.key or "obj_cactus",
                               x=args.x if args.x is not None else 160,
                               y=args.y if args.y is not None else 150,
                               timeout=args.timeout or 120,
                               send_keys=args.keys or "external")
                if not _ok:
                    sys.exit(1)  # FAIL 必须非零退出，否则自动化无法感知
            elif args.action == "create-door":
                if args.value is None or args.key is None:
                    parser.error("--value (当前房间名) 和 --key (目标房间名) 是必需的")
                cmd_create_door(game_file, args.value, args.key,
                                args.x, args.y, args.spawn_x, args.spawn_y)
            elif args.action == "list-doors":
                if args.value is None:
                    parser.error("--value 是必需的 (房间名)")
                cmd_list_doors(game_file, args.value)
            elif args.action == "remove-door":
                if args.value is None:
                    parser.error("--value 是必需的 (房间名)")
                if not args.all and not (x_explicit and y_explicit):
                    parser.error("--x 和 --y (坐标) 或 --all (全部移除) 是必需的")
                cmd_remove_door(game_file, args.value,
                                args.x if x_explicit else None,
                                args.y if y_explicit else None,
                                remove_all=args.all)
            elif args.action == "create-pit":
                if args.value is None or args.key is None:
                    parser.error("--value (当前房间名) 和 --key (目标房间名) 是必需的")
                cmd_create_pit(game_file, args.value, args.key,
                               args.x, args.y, args.spawn_x, args.spawn_y)
            elif args.action == "create-battle":
                if args.value is None or args.key is None:
                    parser.error("--value (房间名) 和 --key (battlegroup ID) 是必需的")
                try:
                    bg_id = int(args.key)
                except ValueError:
                    parser.error("--key 必须是数字 (battlegroup ID)")
                cmd_create_battle(game_file, args.value, bg_id,
                                  border=args.border, x=args.x, y=args.y)
            elif args.action == "remove-obj":
                if args.value is None:
                    parser.error("--value 是必需的 (房间名)")
                if args.instance is None and args.key is None:
                    parser.error("--instance (实例 ID) 或 --key (对象名) 是必需的")
                cmd_remove_obj(game_file, args.value, args.key or "",
                               instance_id=args.instance, remove_all=args.all)
            elif args.action == "room-info":
                if args.value is None:
                    parser.error("--value 是必需的 (房间名)")
                cmd_room_info(game_file, args.value)
            elif args.action == "create-room":
                if args.value is None:
                    parser.error("--value 是必需的 (房间内部名)")
                cmd_create_room(game_file, args.value, args.width, args.height,
                                args.speed, args.caption, args.bg_color)
            elif args.action == "set-room-bg":
                if args.value is None:
                    parser.error("--value 是必需的 (房间名)")
                cmd_set_room_bg(game_file, args.value, args.index,
                                enable=_bool_or_none(args.enable),
                                bg_name=args.bg,
                                foreground=_bool_or_none(args.foreground),
                                x=(args.x if x_explicit else None),
                                y=(args.y if y_explicit else None),
                                speedx=args.speedx, speedy=args.speedy,
                                tiled_h=_bool_or_none(args.tiled_h),
                                tiled_v=_bool_or_none(args.tiled_v),
                                stretch=_bool_or_none(args.stretch),
                                keep_bg_color=args.keep_bg_color)
            elif args.action == "set-room-solid-bg":
                if args.value is None or args.color is None:
                    parser.error("--value (房间名) 和 --color (6位hex RGB) 是必需的")
                try:
                    _parse_layers(args.layers)
                except ValueError as e:
                    parser.error(str(e))
                cmd_set_room_solid_bg(game_file, args.value, args.color,
                                      asset_name=args.asset_name,
                                      layers=args.layers,
                                      runtime=not args.no_runtime)
            elif args.action == "room-bg-info":
                if args.value is None:
                    parser.error("--value 是必需的 (房间名)")
                cmd_room_bg_info(game_file, args.value)
            elif args.action == "set-room-prop":
                if args.value is None:
                    parser.error("--value 是必需的 (房间名)")
                cmd_set_room_prop(game_file, args.value,
                                  width=args.width, height=args.height,
                                  speed=args.speed, caption=args.caption,
                                  bg_color=args.bg_color,
                                  persistent=args.persistent)
            elif args.action == "set-room-view":
                if args.value is None:
                    parser.error("--value 是必需的 (房间名)")
                cmd_set_room_view(game_file, args.value, args.index,
                                  enable=_bool_or_none(args.enable),
                                  view_w=args.view_w, view_h=args.view_h,
                                  port_w=args.port_w, port_h=args.port_h,
                                  follow=args.follow,
                                  border_x=args.border_x, border_y=args.border_y)
            elif args.action == "list-game-bgs":
                cmd_list_game_bgs(game_file, args.value or "")
            elif args.action == "create-bg-asset":
                if args.value is None or args.image is None:
                    parser.error("--value (背景名) 和 --image (PNG 路径) 是必需的")
                cmd_create_bg_asset(game_file, args.value, args.image)
            elif args.action == "gml-bg":
                if args.value is None or args.bg is None:
                    parser.error("--value (房间名) 和 --bg (背景名/ID) 是必需的")
                try:
                    _parse_layers(args.layers)
                except ValueError as e:
                    parser.error(str(e))
                cmd_gml_bg(game_file, args.value, args.bg, args.slot,
                           args.speedx, args.speedy,
                           layers=args.layers, all_layers=args.all_layers,
                           hide_above=args.hide_above,
                           vtiled=(_bool_or_none(args.tiled_v) is not False),
                           foreground=(_bool_or_none(args.foreground) is True))
            elif args.action == "remove-tile":
                if args.value is None:
                    parser.error("--value 是必需的 (房间名)")
                cmd_remove_tile(game_file, args.value, instance=args.instance)
            elif args.action == "handler-extract":
                cmd_handler_extract(game_file, apply=args.apply)
            elif args.action == "append-code":
                if args.key is None or args.value is None:
                    parser.error("--key (代码名) 和 --value (GML) 是必需的")
                cmd_code_append(game_file, args.key, args.value, value_is_file=args.file_path)
            elif args.action == "prepend-code":
                if args.key is None or args.value is None:
                    parser.error("--key (代码名) 和 --value (GML) 是必需的")
                cmd_code_prepend(game_file, args.key, args.value, value_is_file=args.file_path)
            elif args.action == "batch-add-textentry":
                if args.value is None:
                    parser.error("--value 是必需的 (JSON 文件路径)")
                cmd_batch_textdata(game_file, args.value,
                                   face=args.face, emotion=args.emotion)
            elif args.action == "list-sprites":
                cmd_sprite_list(game_file, args.limit)
            elif args.action == "search-sprite":
                if args.value is None:
                    parser.error("--value 是必需的 (搜索关键词)")
                cmd_sprite_search(game_file, args.value, args.limit)
            elif args.action == "get-obj":
                if args.key is None:
                    parser.error("--key 是必需的 (对象名称)")
                cmd_obj_get(game_file, args.key)
            elif args.action == "set-obj-sprite":
                if args.key is None or args.value is None:
                    parser.error("--key (对象名) 和 --value (精灵名) 是必需的")
                cmd_obj_set_sprite(game_file, args.key, args.value)
            elif args.action == "list-textures":
                cmd_texture_list(game_file, args.limit)
            elif args.action == "export-sprite":
                if args.key is None:
                    parser.error("--key 是必需的 (精灵名)")
                if args.json:
                    _export_sprite_json(game_file, args.key)
                else:
                    if args.value is None:
                        parser.error("--value 是必需的 (路径)")
                    # --value 以 .png 结尾且未显式指定 --frame 时，按"单帧导出到文件"处理
                    if args.frame is not None:
                        frame = args.frame
                    elif args.value.lower().endswith(".png"):
                        frame = 0
                    else:
                        frame = -1
                    cmd_sprite_export(game_file, args.key, args.value, frame=frame)
            elif args.action == "replace-sprite":
                if args.key is None or args.value is None:
                    parser.error("--key (精灵名) 和 --value (PNG 路径) 是必需的")
                cmd_sprite_replace(game_file, args.key, args.value, frame=args.frame if args.frame is not None else 0, all_frames=args.all)
            elif args.action == "duplicate-sprite":
                if args.key is None or args.value is None:
                    parser.error("--key (源精灵名) 和 --value (新精灵名) 是必需的")
                cmd_sprite_duplicate(game_file, args.key, args.value)
            elif args.action == "preview-sprite":
                if args.key is None:
                    parser.error("--key 是必需的 (精灵名)")
                cmd_sprite_preview(game_file, args.key)
            elif args.action == "colorize-sprite":
                if args.key is None or args.value is None or args.hue_from is None or args.hue_to is None:
                    parser.error("--key (源), --value (目标名), --hue-from (如 180-260), --hue-to (目标色相) 是必需的")
                try:
                    hf = tuple(float(x) / 360.0 for x in args.hue_from.split("-"))
                except Exception:
                    parser.error("--hue-from 格式错误，应为 \"180-260\"")
                cmd_sprite_colorize(game_file, args.key, args.value, hue_from=hf, hue_to=args.hue_to)
            elif args.action == "export-texture":
                if args.value is None:
                    parser.error("--value 是必需的 (输出目录)")
                cmd_texture_export(game_file, args.key, args.value)
            elif args.action == "replace-texture":
                if args.key is None or args.value is None:
                    parser.error("--key (纹理名) 和 --value (PNG 路径) 是必需的")
                cmd_texture_replace(game_file, args.key, args.value)
            elif args.action == "dump-sprites":
                if args.value is None:
                    parser.error("--value 是必需的 (输出目录)")
                cmd_sprite_dump_all(game_file, args.value)
            elif args.action == "cjk-font":
                if args.value is None:
                    parser.error("--value 是必需的 (font_cjk_build.py 输出目录)")
                if not cmd_cjk_font(game_file, Path(args.value).expanduser(),
                                    Path(args.work_dir).expanduser() if args.work_dir else None):
                    sys.exit(1)  # scr_setfont 字节级体检 WARN 必须非零退出
            elif args.action == "cjk-trigger":
                if args.text is None:
                    parser.error("--text 是必需的 (对话文本)")
                if not cmd_cjk_trigger(game_file, args.room, args.object,
                                       220 if args.x_raw is None else args.x_raw,
                                       330 if args.y_raw is None else args.y_raw,
                                       args.typer, args.text,
                                       wrap=not args.no_wrap,
                                       width_room_px=args.width):
                    sys.exit(1)  # Step_1 字节级体检 WARN 必须非零退出
            else:
                parser.error(f"'{args.action}' 不支持 data_win 文件")
        except (FileNotFoundError, ValueError, IndexError, RuntimeError, DeterlineError) as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # ── Save editor actions (ini / file0) ────────────────
    try:
        save_dir = find_save_dir(args.dir)
    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        if args.file == "file0":
            if args.action == "list":
                cmd_file0_list(save_dir)
            elif args.action == "find":
                if args.value is None:
                    parser.error("--value 是必需的 (搜索目标值)")
                cmd_file0_find(save_dir, args.value)
            elif args.action == "get":
                if not args.key:
                    parser.error("--key 是必需的")
                cmd_file0_get(save_dir, args.key)
            elif args.action == "set":
                if not args.key or args.value is None:
                    parser.error("--key 和 --value 是必需的")
                cmd_file0_set(save_dir, args.key, args.value)
            else:
                parser.error(f"'{args.action}' 仅支持 INI 文件")
        else:
            if args.action == "list":
                cmd_ini_list(save_dir)
            elif args.action == "room-list":
                cmd_room_list(args.value or "")
            elif args.action == "get":
                if not args.key:
                    parser.error("--key 是必需的")
                cmd_ini_get(save_dir, args.section, args.key)
            elif args.action == "set":
                if not args.key or args.value is None:
                    parser.error("--key 和 --value 是必需的")
                cmd_ini_set(save_dir, args.section, args.key, args.value)
            elif args.action == "find":
                print("find 仅支持 file0 (在 INI 中用 get 或 list)", file=sys.stderr)
                sys.exit(1)
            elif args.action == "undo":
                if not args.value:
                    parser.error("--value 是必需的 (ini, file0, 或 data_win)")
                cmd_undo(save_dir, args.value, backup_ts=args.backup,
                         dir_override=args.dir)
            elif args.action == "list-backups":
                if not args.value:
                    parser.error("--value 是必需的 (ini, file0, 或 data_win)")
                cmd_list_backups(save_dir, args.value, dir_override=args.dir)
            elif args.action == "create-system-info":
                if args.value is None:
                    parser.error("--value 是必需的 (962 或 963)")
                cmd_create_system_info(save_dir, args.value)
            elif args.action == "quest-init":
                flag_idx = args.flag if args.flag is not None else FLAG_CUSTOM_START
                cmd_quest_init(save_dir, flag_idx)
            elif args.action == "quest-status":
                cmd_quest_status(save_dir)
            elif args.action == "reset-all":
                cmd_reset_all(save_dir)
            elif args.action == "experiment-snapshot":
                cmd_experiment_snapshot(save_dir, args.value)
            elif args.action == "experiment-list":
                cmd_experiment_list(save_dir)
            elif args.action == "experiment-restore":
                if not args.value:
                    parser.error("--value 是必需的 (快照标签)")
                cmd_experiment_restore(save_dir, args.value)
            elif args.action == "reset-flags":
                cmd_reset_flags(save_dir)
            else:
                parser.error(
                    f"'{args.action}' 仅支持 --file data_win (游戏数据) 操作；"
                    f"ini/file0 模式不适用该命令"
                )
    except (FileNotFoundError, ValueError, DeterlineError) as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
