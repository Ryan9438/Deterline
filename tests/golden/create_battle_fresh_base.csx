
var code = Data.Code.ByName("gml_Object_obj_deterline_battle_Create_0");
if (code == null) {
    ScriptMessage("ERROR: not found");
    return;
}
try {
    string gml = GetDecompiledText(code);
    var lines = gml.Split(new[] { "/r/n", "/r", "/n" }, StringSplitOptions.None);
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
    importGroup.QueueReplace("gml_Object_obj_deterline_battle_Create_0", @"/// obj_deterline_battle — Create event
var _rn = room_get_name(room);
if (_rn == ""room_golden"" && x == 320 && y == 240) {
    battlegroup_id = 3;
    border = 1;
    exit;
}
battlegroup_id = -1;
border = 0;
");
    importGroup.QueueReplace("gml_Object_obj_deterline_battle_Step_0", @"/// obj_deterline_battle — Step event
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

var batObj = Data.GameObjects.ByName("obj_deterline_battle");
if (batObj == null) {
    ScriptMessage("ERROR: obj_deterline_battle was not created");
    return;
}

var markerSpr = Data.Sprites.ByName("spr_markerB");
if (markerSpr != null) {
    batObj.Sprite = markerSpr;
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
    ObjectDefinition = batObj,
    X = 320,
    Y = 240
});
ScriptMessage("OK: Battle trigger [" + newId + "] in " + room.Name.Content + " (group " + 3 + ")");

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
