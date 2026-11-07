
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
    // Suggest similar rooms
    string suggest = "";
    int found = 0;
    for (int r = 0; r < Data.Rooms.Count && found < 5; r++) {
        string rn = Data.Rooms[r].Name.Content;
        if (rn.IndexOf("room_golden", StringComparison.OrdinalIgnoreCase) >= 0 ||
            "room_golden".IndexOf(rn, StringComparison.OrdinalIgnoreCase) >= 0) {
            suggest += (found > 0 ? ", " : "") + rn;
            found++;
        }
    }
    if (found > 0) ScriptMessage("HINT: Did you mean: " + suggest);
    return;
}
var objDef = Data.GameObjects.ByName("obj_golden_npc");
if (objDef == null) {
    for (int o = 0; o < Data.GameObjects.Count; o++) {
        if (Data.GameObjects[o].Name.Content.IndexOf("obj_golden_npc", StringComparison.OrdinalIgnoreCase) >= 0) {
            objDef = Data.GameObjects[o];
            break;
        }
    }
}
if (objDef == null) {
    ScriptMessage("ERROR: Object not found: obj_golden_npc");
    // Suggest similar objects
    string suggest = "";
    int found = 0;
    for (int o = 0; o < Data.GameObjects.Count && found < 5; o++) {
        string on = Data.GameObjects[o].Name.Content;
        if (on.IndexOf("obj_golden_npc", StringComparison.OrdinalIgnoreCase) >= 0 ||
            "obj_golden_npc".IndexOf(on, StringComparison.OrdinalIgnoreCase) >= 0) {
            suggest += (found > 0 ? ", " : "") + on;
            found++;
        }
    }
    if (found > 0) ScriptMessage("HINT: Did you mean: " + suggest);
    return;
}
// Native interactable detection (parent chain walk)
bool objNativeInteract = false;
var objChainCur = objDef;
int objChainGuard = 0;
while (objChainCur != null && objChainGuard < 30)
{
    string objChainName = objChainCur.Name?.Content ?? "";
    if (objChainName == "obj_interactable" || objChainName == "obj_readablesolid")
    {
        objNativeInteract = true;
        break;
    }
    objChainCur = objChainCur.ParentId;
    objChainGuard++;
}
if (objNativeInteract)
{
    ScriptMessage("WARN: 该对象继承原生交互系统 (obj_readablesolid/obj_interactable)");
    ScriptMessage("     若注入 myinteract 距离触发会与默认对话重叠 → 改用 flag 状态机 + 守卫 Alarm_0,");
    ScriptMessage("     或直接用 npc-dialogue / guard-npc-alarm 命令。");
}
// Self-destructing pickup detection (experiment 20: obj_pie_pickup hides via instance_destroy in Step_1).
// Exact whitelist only: these 3 pickups vanish every frame once their "taken" flag is set.
string objSelName = objDef.Name?.Content ?? "";
string objSelFlag = "";
if (objSelName == "obj_pie_pickup") objSelFlag = "global.flag[103]";
else if (objSelName == "obj_knife_pickup") objSelFlag = "global.flag[102]";
else if (objSelName == "obj_ribbon_pickup") objSelFlag = "global.flag[100]";
if (objSelFlag.Length > 0)
{
    ScriptMessage("WARN: " + objSelName + " 是自毁拾取物 → " + objSelFlag + "!=1（物品未拿走）时每帧 instance_destroy()，spawn 后会立刻消失");
    ScriptMessage("     若只是摆放展示，改用无自毁逻辑的对象（如 obj_bigpie）。");
}
// Check for nearby objects (overlap warning)
int nearCount = 0;
int nearThreshold = 30;
foreach (var go in room.GameObjects) {
    int dx = go.X - 320;
    int dy = go.Y - 240;
    if (dx * dx + dy * dy < nearThreshold * nearThreshold) {
        nearCount++;
        if (nearCount <= 3) ScriptMessage("WARN: Near existing obj " + (go.ObjectDefinition?.Name?.Content ?? "?") + " at (" + go.X + "," + go.Y + ")");
    }
}
if (nearCount > 0) ScriptMessage("(found " + nearCount + " objects within " + nearThreshold + "px)");

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
    ObjectDefinition = objDef,
    X = 320,
    Y = 240
});
string objName = objDef.Name?.Content ?? "(unknown)";
string rName = room.Name?.Content ?? "(unknown)";
ScriptMessage("OK: Spawned [" + newId + "] " + objName + " in " + rName + " at (320, 240)");
ScriptMessage("SPAWN_RESULT:" + newId + ":" + (objNativeInteract ? "1" : "0"));

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
