
try {
    string gml = GetDecompiledText(Data.Code.ByName("gml_Script_textdata_en"));
    string search = @"ds_map_add(global.text_data_en, ""obj_golden_001"", ";
    string newLine = @"ds_map_add(global.text_data_en, ""obj_golden_001"", ""* Updated text/%%"");";
    var lines = gml.Split(new[] { "\r\n", "\r", "\n" }, StringSplitOptions.None);
    int updated = 0;
    for (int i = 0; i < lines.Length; i++) {
        if (lines[i].TrimStart().StartsWith(search)) {
            int indent = lines[i].Length - lines[i].TrimStart().Length;
            lines[i] = new string(' ', indent) + newLine;
            updated++;
        }
    }
    if (updated == 0) {
        ScriptMessage("ERROR: No entry found for key 'obj_golden_001' (use add-textentry first)");
        return;
    }
    string newGml = string.Join("\r\n", lines);
    CodeImportGroup importGroup = new(Data)
    {
        MainThreadAction = MainThreadAction
    };
    importGroup.QueueReplace(Data.Code.ByName("gml_Script_textdata_en"), newGml);
    importGroup.Import();
    ScriptMessage("OK: Updated " + updated + " entry(s) for '" + "obj_golden_001" + "'");
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.Message);
}
