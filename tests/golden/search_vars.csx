
int found = 0;
int totalCodes = Data.Code.Count;
ScriptMessage("SCANNING:" + totalCodes);
for (int ci = 0; ci < totalCodes && found < 30; ci++) {
    try {
        string gml = GetDecompiledText(Data.Code[ci]);
        if (gml.IndexOf("global.flag", StringComparison.OrdinalIgnoreCase) >= 0) {
            string name = Data.Code[ci].Name.Content;
            // Extract first matching line
            var lines = gml.Split(new[] { "\r\n", "\r", "\n" }, StringSplitOptions.None);
            for (int li = 0; li < lines.Length; li++) {
                if (lines[li].IndexOf("global.flag", StringComparison.OrdinalIgnoreCase) >= 0) {
                    ScriptMessage("[" + ci + "] " + name + ": " + lines[li].Trim());
                    break;
                }
            }
            found++;
        }
    } catch { }
}
if (found == 0) {
    ScriptMessage("(no matches)");
}
