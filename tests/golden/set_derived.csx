
var code = Data.Code.ByName("gml_Object_obj_battlecontroller_Create_0");
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

var code = Data.Code.ByName("gml_Object_obj_battlecontroller_Create_0");
if (code == null) {
    ScriptMessage("ERROR: Code entry not found: gml_Object_obj_battlecontroller_Create_0");
    return;
}
if (code.ParentEntry != null) {
    ScriptMessage("SKIP: child entry, replace parent instead");
    return;
}
try {
    CodeImportGroup importGroup = new(Data)
    {
        MainThreadAction = MainThreadAction
    };
    importGroup.QueueReplace(code, "global.maxhp = 50;\nif (global.lv > 18) {\n    global.maxhp = 50;\n}");
    importGroup.Import();
    ScriptMessage("OK: Replaced " + "gml_Object_obj_battlecontroller_Create_0");
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.Message);
}

=== CALL ===

var code = Data.Code.ByName("gml_Script_scr_levelup");
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

var code = Data.Code.ByName("gml_Script_scr_levelup");
if (code == null) {
    ScriptMessage("ERROR: Code entry not found: gml_Script_scr_levelup");
    return;
}
if (code.ParentEntry != null) {
    ScriptMessage("SKIP: child entry, replace parent instead");
    return;
}
try {
    CodeImportGroup importGroup = new(Data)
    {
        MainThreadAction = MainThreadAction
    };
    importGroup.QueueReplace(code, "global.maxhp = 50;\nif (global.lv > 18) {\n    global.maxhp = 50;\n}");
    importGroup.Import();
    ScriptMessage("OK: Replaced " + "gml_Script_scr_levelup");
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.Message);
}
