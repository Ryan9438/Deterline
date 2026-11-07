
var code = Data.Code.ByName("gml_Script_scr_golden");
if (code == null) {
    ScriptMessage("ERROR: Code entry not found: gml_Script_scr_golden");
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
    importGroup.QueueReplace(code, "return 20;");
    importGroup.Import();
    ScriptMessage("OK: Replaced " + "gml_Script_scr_golden");
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.Message);
}
