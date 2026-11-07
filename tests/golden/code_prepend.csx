
var code = Data.Code.ByName("gml_Object_obj_golden_Step_0");
if (code == null) {
    ScriptMessage("ERROR: Code entry not found: gml_Object_obj_golden_Step_0");
    return;
}
if (code.ParentEntry != null) {
    ScriptMessage("SKIP: child entry, use parent instead");
    return;
}
try {
    CodeImportGroup importGroup = new(Data)
    {
        MainThreadAction = MainThreadAction
    };
    importGroup.QueuePrepend(code, @"// prepended");
    importGroup.Import();
    ScriptMessage("OK: Prepended to " + "gml_Object_obj_golden_Step_0");
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.Message);
}
