
try {
    var existing = Data.Code.ByName("gml_Script_goldenFunc");
    if (existing != null) {
        ScriptMessage("WARN:EXISTS:" + existing.Name.Content);
    }
    CodeImportGroup importGroup = new(Data)
    {
        AutoCreateAssets = true,
        MainThreadAction = MainThreadAction
    };
    importGroup.QueueReplace("gml_Script_goldenFunc", @"return 0;");
    importGroup.Import();
    ScriptMessage("OK: Created/replaced " + "gml_Script_goldenFunc");
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.Message);
}
