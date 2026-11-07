
var s = Data.Strings.MakeString("* New dialogue/%%");
var idx = Data.Strings.IndexOf(s);
ScriptMessage("NEW_INDEX:" + idx);
ScriptMessage("Content: " + Data.Strings[idx].Content);
