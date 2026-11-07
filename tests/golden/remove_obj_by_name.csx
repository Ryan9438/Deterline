
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
    return;
}
int removed = 0;
bool removeAll = false;
if (removeAll) {
    for (int i = room.GameObjects.Count - 1; i >= 0; i--) {
        if (room.GameObjects[i].ObjectDefinition == objDef) {
            room.GameObjects.RemoveAt(i);
            removed++;
        }
    }
} else {
    for (int i = 0; i < room.GameObjects.Count; i++) {
        if (room.GameObjects[i].ObjectDefinition == objDef) {
            room.GameObjects.RemoveAt(i);
            removed++;
            break;
        }
    }
}
string objName = objDef.Name?.Content ?? "(unknown)";
string rName = room.Name?.Content ?? "(unknown)";
ScriptMessage("OK: Removed " + removed + " instance(s) of " + objName + " from " + rName);
