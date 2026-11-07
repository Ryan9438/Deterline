
var old = Data.Strings[64000].Content;
Data.Strings.RemoveAt(64000);
ScriptMessage("Deleted [" + 64000 + "]: " + old);
