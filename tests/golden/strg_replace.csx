
int count = 0;
for (int i = 0; i < Data.Strings.Count; i++) {
    if (Data.Strings[i].Content == "* Old line/%%") {
        Data.Strings[i].Content = "* New line/%%";
        ScriptMessage("Replaced [" + i + "]: " + "* Old line/%%" + " → " + "* New line/%%");
        count++;
    }
}
ScriptMessage("DONE:" + count + " replacements");
