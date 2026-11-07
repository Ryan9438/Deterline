
try {
    var s = Data.Strings.MakeString("* Batch one/%%");
    int strg_idx = Data.Strings.IndexOf(s);
    ScriptMessage("STRG_INDEX:" + strg_idx);

    string gml = GetDecompiledText(Data.Code.ByName("gml_Script_textdata_en"));
    if (gml.IndexOf(@"ds_map_add(global.text_data_en, ""obj_golden_b1"", ") >= 0) {
        ScriptMessage("WARN: Key '" + "obj_golden_b1" + "' already exists, skipping (use delete-textentry first)");
        return;
    }
    gml = gml.TrimEnd() + "\r\n" + @"ds_map_add(global.text_data_en, ""obj_golden_b1"", ""* Batch one/%%"");";

    CodeImportGroup importGroup = new(Data)
    {
        MainThreadAction = MainThreadAction
    };
    importGroup.QueueReplace(Data.Code.ByName("gml_Script_textdata_en"), gml);
    importGroup.Import();
    ScriptMessage("OK: Added textdata entry '" + "obj_golden_b1" + "' (STRG idx " + strg_idx + ")");
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.Message);
}

=== CALL ===

try {
    var s = Data.Strings.MakeString("\\F3\\E1* Batch two/%%");
    int strg_idx = Data.Strings.IndexOf(s);
    ScriptMessage("STRG_INDEX:" + strg_idx);

    string gml = GetDecompiledText(Data.Code.ByName("gml_Script_textdata_en"));
    if (gml.IndexOf(@"ds_map_add(global.text_data_en, ""obj_golden_b2"", ") >= 0) {
        ScriptMessage("WARN: Key '" + "obj_golden_b2" + "' already exists, skipping (use delete-textentry first)");
        return;
    }
    gml = gml.TrimEnd() + "\r\n" + @"ds_map_add(global.text_data_en, ""obj_golden_b2"", ""\F3\E1* Batch two/%%"");";

    CodeImportGroup importGroup = new(Data)
    {
        MainThreadAction = MainThreadAction
    };
    importGroup.QueueReplace(Data.Code.ByName("gml_Script_textdata_en"), gml);
    importGroup.Import();
    ScriptMessage("OK: Added textdata entry '" + "obj_golden_b2" + "' (STRG idx " + strg_idx + ")");
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.Message);
}
