
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
var target = room.GameObjects.ByInstanceID(113928);
if (target == null) {
    ScriptMessage("ERROR: Instance [113928] not found in " + (room.Name?.Content ?? "(unknown)"));
    return;
}
string objName = target.ObjectDefinition?.Name?.Content ?? "(unknown)";
room.GameObjects.Remove(target);
ScriptMessage("OK: Removed [" + 113928 + "] " + objName + " from " + (room.Name?.Content ?? "(unknown)"));
