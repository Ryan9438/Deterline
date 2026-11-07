
var code = Data.Code.ByName("gml_Object_obj_mainchara_Step_0");
if (code == null) {
    ScriptMessage("ERROR: Code entry not found: gml_Object_obj_mainchara_Step_0");
    return;
}
if (code.ParentEntry != null) {
    ScriptMessage("SKIP: child entry, use parent instead");
    return;
}
try {
    string existingGml = GetDecompiledText(code);
    string newGml = existingGml + "\n" + @"if (room == room_golden)
{
if (!variable_global_exists(""det_bg_room_golden_0_bg_golden""))
{
global.det_bg_room_golden_0_bg_golden = 1;
background_visible[0] = true;
background_index[0] = bg_golden;
background_htiled[0] = true;
background_vtiled[0] = true;
background_foreground[0] = false;
}
background_x[0] = floor(view_xview[0] - (view_xview[0] * 0.5));
background_y[0] = floor(view_yview[0] - (view_yview[0] * 0.0));
}";
    CodeImportGroup importGroup = new(Data)
    {
        MainThreadAction = MainThreadAction
    };
    importGroup.QueueReplace(code, newGml);
    importGroup.Import();
    ScriptMessage("OK: Appended to " + "gml_Object_obj_mainchara_Step_0" + " (len " + newGml.Length + ")");
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.Message);
}
