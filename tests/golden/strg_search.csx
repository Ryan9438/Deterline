
int found = 0;
for (int i = 0; i < Data.Strings.Count && found < 30; i++) {
    if (Data.Strings[i].Content.IndexOf("Toriel", StringComparison.OrdinalIgnoreCase) >= 0) {
        ScriptMessage("[" + i + "] " + Data.Strings[i].Content);
        found++;
    }
}
ScriptMessage("FOUND:" + found);
