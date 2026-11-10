"""door/pit/battle 三胞胎命令域（O2 步 8：从 modify_save.py 1:1 平移）。

1:1 平移不合并（方案修订 3：三胞胎合并留给 O3b 单独做，拆包 commit 禁语义手术）。
CSX 模板常量随域整体平移。跨模块一律模块属性形式：
utmt./code./rooms_data./paths./errors.
"""

import sys
from pathlib import Path

from .. import errors, paths, rooms_data, utmt
from . import code

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

    esc_cur = utmt._csx_escape(cur_room)
    esc_target = utmt._csx_escape(target_room)

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
    idx_out = utmt._run_utmt(idx_csx, game_file, save=False)
    target_idx = -1
    for line in utmt._parse_msg(idx_out):
        if line.startswith("IDX:"):
            target_idx = int(line.split(":")[1])
            break
    if target_idx < 0:
        raise errors.NotFoundError(f"目标房间不存在: {target_room}")

    # Read existing Create_0 code or start from base
    existing_create = code._get_decompiled_code(game_file, OBJ_CREATE)
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

    verb_back = utmt._csx_verbatim_escape(DOOR_GOTO_BACK_SCRIPT)
    verb_create = utmt._csx_verbatim_escape(new_create)
    verb_step = utmt._csx_verbatim_escape(DOOR_STEP_CODE)

    esc_name_create = utmt._csx_escape(OBJ_CREATE)
    esc_name_step = utmt._csx_escape(OBJ_STEP)
    esc_name_back = utmt._csx_escape("gml_Script_deterline_door_back")

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
    csx += utmt._instances_check_snippet()
    out = utmt._run_utmt(csx, game_file, save=True)
    for line in utmt._parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)
    rooms_data._update_rooms_json(target_room, target_room)


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

    esc_cur = utmt._csx_escape(cur_room)
    esc_target = utmt._csx_escape(target_room)

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
    idx_out = utmt._run_utmt(idx_csx, game_file, save=False)
    target_idx = -1
    for line in utmt._parse_msg(idx_out):
        if line.startswith("IDX:"):
            target_idx = int(line.split(":")[1])
            break
    if target_idx < 0:
        raise errors.NotFoundError(f"目标房间不存在: {target_room}")

    # Read existing Create_0 or start from base
    existing_create = code._get_decompiled_code(game_file, OBJ_CREATE)
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

    verb_create = utmt._csx_verbatim_escape(new_create)
    verb_step = utmt._csx_verbatim_escape(PIT_STEP_CODE)
    esc_name_create = utmt._csx_escape(OBJ_CREATE)
    esc_name_step = utmt._csx_escape(OBJ_STEP)

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
    csx += utmt._instances_check_snippet()
    out = utmt._run_utmt(csx, game_file, save=True)
    for line in utmt._parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)
    rooms_data._update_rooms_json(target_room, target_room)


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

    esc_cur = utmt._csx_escape(cur_room)

    existing_create = code._get_decompiled_code(game_file, OBJ_CREATE)
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

    verb_create = utmt._csx_verbatim_escape(new_create)
    verb_step = utmt._csx_verbatim_escape(BATTLE_STEP_CODE)
    esc_name_create = utmt._csx_escape(OBJ_CREATE)
    esc_name_step = utmt._csx_escape(OBJ_STEP)

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
    csx += utmt._instances_check_snippet()
    out = utmt._run_utmt(csx, game_file, save=True)
    for line in utmt._parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)


def cmd_list_doors(game_file: Path, room_name: str) -> None:
    """List all Deterline doors in a room."""
    OBJ_CREATE = "gml_Object_obj_deterline_door_Create_0"
    create_code = code._get_decompiled_code(game_file, OBJ_CREATE)
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
    esc = utmt._csx_escape(room_name)
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
    out = utmt._run_utmt(csx, game_file, save=False)
    for line in utmt._parse_msg(out):
        print(line)


def cmd_remove_door(game_file: Path, room_name: str,
                    x: int | None, y: int | None,
                    remove_all: bool = False) -> None:
    """Remove a Deterline door by coordinates, or all doors with --all."""
    OBJ_CREATE = "gml_Object_obj_deterline_door_Create_0"
    esc_room = utmt._csx_escape(room_name)

    # Step 1: Remove from Create_0 code
    create_code = code._get_decompiled_code(game_file, OBJ_CREATE)
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
    verb_create = utmt._csx_verbatim_escape(new_create)
    esc_create = utmt._csx_escape(OBJ_CREATE)

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
    out = utmt._run_utmt(csx, game_file, save=True)
    for line in utmt._parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)
    print(f"已从 Create_0 中移除 {removed_count} 条分支")
