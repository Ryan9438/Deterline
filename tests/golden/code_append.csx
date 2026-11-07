
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
    string existingGml = GetDecompiledText(code);
    string newGml = existingGml + "\n" + @"// appended";
    CodeImportGroup importGroup = new(Data)
    {
        MainThreadAction = MainThreadAction
    };
    importGroup.QueueReplace(code, newGml);
    importGroup.Import();
    ScriptMessage("OK: Appended to " + "gml_Object_obj_golden_Step_0" + " (len " + newGml.Length + ")");
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.Message);
}
