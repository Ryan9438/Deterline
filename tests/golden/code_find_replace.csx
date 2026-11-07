
var code = Data.Code.ByName("gml_Script_golden");
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

var code = Data.Code.ByName("gml_Script_golden");
if (code == null) {
    ScriptMessage("ERROR: Code entry not found: gml_Script_golden");
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
    importGroup.QueueReplace(code, @"if (global.maxhp == 50) {
    global.maxhp = 50;
}");
    importGroup.Import();
    ScriptMessage("OK: Replaced " + "gml_Script_golden");
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.Message);
}
