
var code = Data.Code.ByName("gml_Object_obj_deterline_door_Create_0");
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

// Remove instances
for (int r = 0; r < Data.Rooms.Count; r++) {
    if (Data.Rooms[r].Name.Content.IndexOf("room_golden", StringComparison.OrdinalIgnoreCase) >= 0) {
        for (int i = Data.Rooms[r].GameObjects.Count - 1; i >= 0; i--) {
            var go = Data.Rooms[r].GameObjects[i];
            string on = go.ObjectDefinition?.Name?.Content ?? "";
            if (on == "obj_deterline_door" && (go.X == 320 && go.Y == 240)) {
                Data.Rooms[r].GameObjects.RemoveAt(i);
            }
        }
        break;
    }
}

// Update Create_0 code
try {
    CodeImportGroup importGroup = new(Data)
    {
        AutoCreateAssets = true,
        MainThreadAction = MainThreadAction
    };
    importGroup.QueueReplace("gml_Object_obj_deterline_door_Create_0", @"/// obj_deterline_door — Create event
var _rn = room_get_name(room);
if (_rn == ""room_golden"" && x == 500 && y == 100) {
    target_room = 71;
    spawn_x = 100;
    spawn_y = 200;
    exit;
}
target_room = -1;
spawn_x = 0;
spawn_y = 0;");
    importGroup.Import();
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.Message);
    return;
}
ScriptMessage("OK: Removed " + 1 + " door(s) from " + "room_golden");
