
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
room.DrawBackgroundColor = false;
room.Backgrounds[0].Enabled = true;

var bgDef = Data.Backgrounds.ByName("bg_golden");
if (bgDef != null) {
    room.Backgrounds[0].BackgroundDefinition = bgDef;
} else {
    ScriptMessage("WARN: Background not found: bg_golden");
}
ScriptMessage("OK: Updated BG[0] for " + room.Name.Content);