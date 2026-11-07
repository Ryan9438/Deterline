
try {
    string gml = GetDecompiledText(Data.Code.ByName("gml_Script_textdata_en"));
    string search = @"ds_map_add(global.text_data_en, ""obj_golden_001"", ";
    var lines = gml.Split(new[] { "\r\n", "\r", "\n" }, StringSplitOptions.None);
    System.Text.StringBuilder sb = new System.Text.StringBuilder();
    int removed = 0;
    for (int i = 0; i < lines.Length; i++) {
        if (lines[i].TrimStart().StartsWith(search)) {
            removed++;
        } else {
            if (sb.Length > 0) sb.Append("\r\n");
            sb.Append(lines[i]);
        }
    }
    if (removed == 0) {
        ScriptMessage("ERROR: No entry found for key 'obj_golden_001'");
        return;
    }
    string newGml = sb.ToString();
    CodeImportGroup importGroup = new(Data)
    {
        MainThreadAction = MainThreadAction
    };
    importGroup.QueueReplace(Data.Code.ByName("gml_Script_textdata_en"), newGml);
    importGroup.Import();
    ScriptMessage("OK: Removed " + removed + " entry(s) for '" + "obj_golden_001" + "'");
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.Message);
}
