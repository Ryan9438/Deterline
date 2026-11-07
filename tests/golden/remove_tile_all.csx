
var room = Data.Rooms.ByName("room_golden");
if (room == null) { ScriptMessage("ERROR: Room not found"); return; }
int count = room.Tiles.Count;
room.Tiles.Clear();
ScriptMessage("OK: Cleared " + count + " tiles from " + "room_golden");
