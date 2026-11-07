
var code = Data.Code.ByName("gml_Object_obj_time_Step_2");
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
    importGroup.QueueReplace("gml_Object_obj_deterline_handler_Step_0", @"// Deterline extracted handler (from obj_time_Step_2)
// Runs every step via obj_deterline_handler
if (!variable_global_exists(""deterline_handler_active"")) {
    global.deterline_handler_active = true;

    // Extracted block (lines 1-2)
    if (global.choice != -1) {
        msg[0] = ""resumed"";

    global.choice = -1;
}");
    importGroup.QueueReplace("gml_Object_obj_deterline_handler_Create_0", @"global.deterline_handler_active = true;");
    importGroup.QueueReplace("gml_Object_obj_time_Step_2", @"}
exit;");
    importGroup.Import();
    ScriptMessage("OK: Created " + "gml_Object_obj_deterline_handler_Step_0");
    ScriptMessage("OK: Created " + "gml_Object_obj_deterline_handler_Create_0");
    ScriptMessage("OK: Cleaned " + "gml_Object_obj_time_Step_2");
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.Message);
}
