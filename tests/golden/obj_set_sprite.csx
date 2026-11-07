
var obj = Data.GameObjects.ByName("obj_golden_npc");
if (obj == null) {
    obj = Data.GameObjects.ByName("obj_golden_npc", true);
}
if (obj == null) {
    string query = "obj_golden_npc";
    int first = -1;
    int count = 0;
    for (int o = 0; o < Data.GameObjects.Count; o++) {
        string on = Data.GameObjects[o].Name.Content;
        if (on.IndexOf(query, StringComparison.OrdinalIgnoreCase) >= 0) {
            if (first < 0) first = o;
            count++;
        }
    }
    if (first >= 0) {
        obj = Data.GameObjects[first];
        if (count > 1) ScriptMessage("(found " + count + " matches, using: " + obj.Name.Content + ")");
    }
}
if (obj == null) {
    ScriptMessage("ERROR: Object not found: obj_golden_npc");
    string suggest = "";
    int found = 0;
    for (int o = 0; o < Data.GameObjects.Count && found < 5; o++) {
        string on = Data.GameObjects[o].Name.Content;
        if (on.IndexOf("obj_golden_npc", StringComparison.OrdinalIgnoreCase) >= 0) {
            suggest += (found > 0 ? ", " : "") + on;
            found++;
        }
    }
    if (found > 0) ScriptMessage("HINT: Did you mean: " + suggest);
    return;
}
var spr = Data.Sprites.ByName("spr_golden");
if (spr == null) {
    spr = Data.Sprites.ByName("spr_golden", true);
}
if (spr == null) {
    string query = "spr_golden";
    int first = -1;
    int count = 0;
    for (int s = 0; s < Data.Sprites.Count; s++) {
        string sn = Data.Sprites[s].Name.Content;
        if (sn.IndexOf(query, StringComparison.OrdinalIgnoreCase) >= 0) {
            if (first < 0) first = s;
            count++;
        }
    }
    if (first >= 0) {
        spr = Data.Sprites[first];
        if (count > 1) ScriptMessage("(found " + count + " sprites, using: " + spr.Name.Content + ")");
    }
}
if (spr == null) {
    ScriptMessage("ERROR: Sprite not found: spr_golden");
    string suggest = "";
    int found = 0;
    for (int s = 0; s < Data.Sprites.Count && found < 5; s++) {
        string sn = Data.Sprites[s].Name.Content;
        if (sn.IndexOf("spr_golden", StringComparison.OrdinalIgnoreCase) >= 0) {
            suggest += (found > 0 ? ", " : "") + sn;
            found++;
        }
    }
    if (found > 0) ScriptMessage("HINT: Did you mean: " + suggest);
    return;
}
string oldSpr = obj.Sprite?.Name?.Content ?? "(none)";
obj.Sprite = spr;
ScriptMessage("OK: " + obj.Name.Content + ": " + oldSpr + " → " + spr.Name.Content);
ScriptMessage("(Sprite size: " + spr.Width + "x" + spr.Height + ")");
