
var r = Data.Rooms.ByName("room_golden_b");
if (r == null) {
    for (int i = 0; i < Data.Rooms.Count; i++) {
        if (Data.Rooms[i].Name.Content.IndexOf("room_golden_b", StringComparison.OrdinalIgnoreCase) >= 0) {
            r = Data.Rooms[i];
            break;
        }
    }
}
if (r != null) {
    ScriptMessage("IDX:" + Data.Rooms.IndexOf(r));
} else {
    ScriptMessage("IDX:-1");
}

=== CALL ===

var code = Data.Code.ByName("gml_Object_obj_deterline_pit_Create_0");
if (code == null) {
    ScriptMessage("ERROR: not found");
    return;
}
try {
    string gml = GetDecompiledText(code);
    var lines = gml.Split(new[] { "\r\n", "\r", "\n" }, StringSplitOptions.None);
    for (int i = 0; i < lines.Length; i++) {
        ScriptMessage("GML_LINE:" + i + ":" + lines[i]);
    }
    ScriptMessage("GML_COUNT:" + lines.Length);
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.Message);
}

=== CALL ===

try {
    CodeImportGroup importGroup = new(Data)
    {
        AutoCreateAssets = true,
        MainThreadAction = MainThreadAction
    };
    importGroup.QueueReplace("gml_Object_obj_deterline_pit_Create_0", @"/// obj_deterline_pit — Create event
var _rn = room_get_name(room);
if (_rn == ""room_seed"" && x == 100 && y == 100) {
    target_room = 70;
    spawn_x = 10;
    spawn_y = 20;
    exit;
}
if (_rn == ""room_golden"" && x == 320 && y == 240) {
    target_room = 70;
    spawn_x = 100;
    spawn_y = 200;
    exit;
}
target_room = -1;
spawn_x = 0;
spawn_y = 0;
");
    importGroup.QueueReplace("gml_Object_obj_deterline_pit_Step_0", @"/// obj_deterline_pit — Step event
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
");
    importGroup.Import();
    ScriptMessage("OK: Scripts created/updated");
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.Message);
    return;
}

var room = Data.Rooms.ByName("room_golden");
if (room == null) {
    for (int r = 0; r < Data.Rooms.Count; r++) {
        if (Data.Rooms[r].Name.Content.IndexOf("room_golden", StringComparison.OrdinalIgnoreCase) >= 0) {
            room = Data.Rooms[r];
            break;
        }
    }
}
if (room == null) {
    ScriptMessage("ERROR: Room not found: room_golden");
    return;
}

var pitObj = Data.GameObjects.ByName("obj_deterline_pit");
if (pitObj == null) {
    ScriptMessage("ERROR: obj_deterline_pit was not created");
    return;
}

var pitSpr = Data.Sprites.ByName("spr_markerX");
if (pitSpr == null) {
    pitSpr = Data.Sprites.ByName("spr_stardrop");
}
if (pitSpr != null) {
    pitObj.Sprite = pitSpr;
}

ulong _maxInstId = 0;
foreach (var _r in Data.Rooms)
{
    foreach (var _g in _r.GameObjects)
    {
        if (_g.InstanceID > _maxInstId) _maxInstId = _g.InstanceID;
    }
}
uint newId = (uint)(System.Math.Max((long)Data.GeneralInfo.LastObj, (long)_maxInstId) + 1);
Data.GeneralInfo.LastObj = newId;
room.GameObjects.Add(new UndertaleRoom.GameObject() {
    InstanceID = newId,
    ObjectDefinition = pitObj,
    X = 320,
    Y = 240
});
ScriptMessage("OK: Pit [" + newId + "] created in " + room.Name.Content + " -> " + "room_golden_b");

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
