
try {
    string gml = GetDecompiledText(Data.Code.ByName("gml_Script_textdata_en"));
    var lines = gml.Split(new[] { "\r\n", "\r", "\n" }, StringSplitOptions.None);
    int found = 0;
    for (int i = 0; i < lines.Length && found < 30; i++) {
        if (lines[i].IndexOf("sans", StringComparison.OrdinalIgnoreCase) >= 0) {
            ScriptMessage(lines[i]);
            found++;
        }
    }
    if (found == 0) {
        ScriptMessage("(no matches)");
    }
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.Message);
}
