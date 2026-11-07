
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
room.Views[0].Enabled = true;
room.Views[0].ViewWidth = 320;
room.Views[0].ViewHeight = 240;
room.Views[0].PortWidth = 640;
room.Views[0].PortHeight = 480;

var followObj = Data.GameObjects.ByName("obj_mainchara");
if (followObj != null) {
    room.Views[0].ObjectId = followObj;
} else {
    ScriptMessage("WARN: Object not found: obj_mainchara");
}

ScriptMessage("OK: Updated View[0] for " + room.Name.Content);
