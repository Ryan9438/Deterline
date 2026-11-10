"""房间域命令（O2 步 6：从 modify_save.py 1:1 平移，方案 §1.2 room 项）。

Inspector + spawn/remove + gml-bg/remove-tile + P4-2 全家 + solid-bg +
room-list。跨模块一律模块属性形式：utmt./rooms_data./config./errors./code.
（cmd_gml_bg 的收尾经 cmds.code.cmd_code_append——cmds 域间显式模块属性引用）。
"""

import os
import sys
from pathlib import Path

from .. import config, errors, rooms_data, utmt
from . import code

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
    esc_room = utmt._csx_escape(room_name)
    bg_ref = bg_asset if bg_asset.isdigit() else utmt._csx_escape(bg_asset)
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
    code.cmd_code_append(game_file, "gml_Object_obj_mainchara_Step_0", gml)


def cmd_remove_tile(game_file: Path, room_name: str,
                    instance: int | None = None) -> None:
    """Remove tiles from a room. If --instance given, removes only that tile.
    Otherwise removes ALL tiles from the room."""
    esc_room = utmt._csx_escape(room_name)

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

    out = utmt._run_utmt(csx, game_file, save=True)
    for line in utmt._parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)


def cmd_room_objects(game_file: Path, room_name: str) -> None:
    """List all object instances in a room by its internal name."""
    esc = utmt._csx_escape(room_name)
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
    out = utmt._run_utmt(csx, game_file, save=False)
    for line in utmt._parse_msg(out):
        print(line)


def _spawn_obj_internal(game_file: Path, room_name: str, obj_name: str, x: int, y: int,
                        quiet: bool = False) -> int | None:
    """Spawn an object instance in a room. Returns the new instance ID (or None on failure).

    Shared by cmd_spawn_obj and cmd_npc_dialogue. When quiet=True, suppresses
    non-essential output (used by higher-level commands that report their own progress).
    """
    esc_room = utmt._csx_escape(room_name)
    esc_obj = utmt._csx_escape(obj_name)
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
    csx += utmt._instances_check_snippet()
    out = utmt._run_utmt(csx, game_file, save=True)
    new_id: int | None = None
    for line in utmt._parse_msg(out):
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
        esc_room = utmt._csx_escape(room_name)
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
        esc_room = utmt._csx_escape(room_name)
        esc_obj = utmt._csx_escape(obj_name)
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
    out = utmt._run_utmt(csx, game_file, save=True)
    for line in utmt._parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)
        else:
            print(line)


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
    esc = utmt._csx_escape(room_name)
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
    out = utmt._run_utmt(csx, game_file, save=False)
    for line in utmt._parse_msg(out):
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
    raise errors.DeterlineError(
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
    esc_name = utmt._csx_escape(room_name)
    esc_cap = utmt._csx_escape(caption)
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
    out = utmt._run_utmt(csx, game_file, save=True)
    for line in utmt._parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)
        else:
            print(line)
    rooms_data._update_rooms_json(room_name, caption or room_name)


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
            esc_bg = utmt._csx_escape(bg_name)
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
    for warn_line in config.ROOM_BG_WARNING:
        print(warn_line, file=sys.stderr)
    esc_room = utmt._csx_escape(room_name)
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

    out = utmt._run_utmt(csx, game_file, save=True)
    for line in utmt._parse_msg(out):
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
    esc_room = utmt._csx_escape(room_name)
    esc_cap = utmt._csx_escape(caption or "")
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
    out = utmt._run_utmt(csx, game_file, save=True)
    for line in utmt._parse_msg(out):
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
    esc_room = utmt._csx_escape(room_name)
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
        esc_follow = utmt._csx_escape(follow)
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
    out = utmt._run_utmt(csx, game_file, save=True)
    for line in utmt._parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("WARN:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)


def cmd_list_game_bgs(game_file: Path, filter_str: str = "") -> None:
    """List all background assets available in the game data."""
    esc = utmt._csx_escape(filter_str)
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
    out = utmt._run_utmt(csx, game_file, save=False)
    for line in utmt._parse_msg(out):
        print(line)


def cmd_create_bg_asset(game_file: Path, bg_name: str, png_path: str) -> None:
    """Create a new background asset from a PNG file.
    Injects a new UndertaleBackground + EmbeddedTexture + TexturePageItem.
    """
    esc_bg = utmt._csx_escape(bg_name)
    png_path = str(Path(png_path).expanduser().resolve())
    if not Path(png_path).exists():
        print(f"错误: PNG 文件不存在: {png_path}", file=sys.stderr)
        return

    csx = f'''
string bgName = "{esc_bg}";
string pngPath = @"{utmt._csx_verbatim_escape(png_path)}";

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
    out = utmt._run_utmt(csx, game_file, save=True)
    for line in utmt._parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)


def _read_room_size(game_file: Path, room_name: str) -> tuple[int, int]:
    """Return (width, height) of a room via a read-only UTMT pass."""
    esc = utmt._csx_escape(room_name)
    csx = _resolve_room_csx(esc) + '''
ScriptMessage("SIZE:" + room.Width + ":" + room.Height);
'''
    out = utmt._run_utmt(csx, game_file, save=False)
    for line in utmt._parse_msg(out):
        if line.startswith("SIZE:"):
            _, w, h = line.split(":", 2)
            return int(w), int(h)
    raise RuntimeError(f"无法读取房间尺寸: {room_name}")


def _bg_asset_exists(game_file: Path, bg_name: str) -> bool:
    """Return True if a background asset with this name already exists."""
    esc = utmt._csx_escape(bg_name)
    csx = f'''
var bg = Data.Backgrounds.ByName("{esc}");
ScriptMessage("EXISTS:" + (bg != null));
'''
    out = utmt._run_utmt(csx, game_file, save=False)
    for line in utmt._parse_msg(out):
        if line.startswith("EXISTS:"):
            return line.split(":", 1)[1].strip().lower() == "true"
    return False


def _enabled_bg_layers(game_file: Path, room_name: str) -> list[int]:
    """Return the indices of the room's currently-enabled background layers."""
    esc = utmt._csx_escape(room_name)
    csx = _resolve_room_csx(esc) + '''
for (int i = 0; i < (room.Backgrounds?.Count ?? 0); i++) {
    if (room.Backgrounds[i].Enabled) ScriptMessage("ENABLED:" + i);
}
'''
    out = utmt._run_utmt(csx, game_file, save=False)
    res: list[int] = []
    for line in utmt._parse_msg(out):
        if line.startswith("ENABLED:"):
            res.append(int(line.split(":", 1)[1]))
    return res


def _assign_room_bg_layers(game_file: Path, room_name: str, bg_name: str,
                           layers: list[int]) -> None:
    """Point the given room background layers at bg_name (room-data edit)."""
    esc_room = utmt._csx_escape(room_name)
    esc_bg = utmt._csx_escape(bg_name)
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
    out = utmt._run_utmt(csx, game_file, save=True)
    for line in utmt._parse_msg(out):
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
    esc = utmt._csx_escape(room_name)
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
    out = utmt._run_utmt(csx, game_file, save=False)
    enabled = 0
    has_bg_obj = False
    for line in utmt._parse_msg(out):
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


def cmd_room_list(args_filter: str = "") -> None:
    rooms_data._load_rooms()
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
