
var obj = Data.GameObjects.ByName("obj_golden_npc");
if (obj == null) { obj = Data.GameObjects.ByName("obj_golden_npc", true); }
if (obj == null) {
    string q = "obj_golden_npc";
    int first = -1;
    int count = 0;
    for (int o = 0; o < Data.GameObjects.Count; o++) {
        string on = Data.GameObjects[o].Name.Content;
        if (on.IndexOf(q, StringComparison.OrdinalIgnoreCase) >= 0) {
            if (first < 0) first = o;
            count++;
        }
    }
    if (first >= 0) {
        obj = Data.GameObjects[first];
        ScriptMessage("NPC_TARGET:MATCH:" + obj.Name.Content + ":" + count);
    }
}
if (obj == null) {
    ScriptMessage("NPC_TARGET:NOT_FOUND");
    return;
}
bool native = false;
var cur = obj;
int guard = 0;
while (cur != null && guard < 30) {
    string cn = cur.Name?.Content ?? "";
    if (cn == "obj_interactable" || cn == "obj_readablesolid") {
        native = true;
        break;
    }
    cur = cur.ParentId;
    guard++;
}
string oname = obj.Name.Content;
string stepCode = "";
string[] stepNames = new string[] {
    "gml_Object_" + oname + "_Step_1",
    "gml_Object_" + oname + "_Step_0",
    "gml_Object_" + oname + "_Step_2"
};
foreach (string sn in stepNames) {
    if (Data.Code.ByName(sn) != null) {
        stepCode = sn;
        break;
    }
}
string alarmCode = "";
var acur = obj;
guard = 0;
while (acur != null && guard < 30) {
    string cand = "gml_Object_" + acur.Name.Content + "_Alarm_0";
    if (Data.Code.ByName(cand) != null) {
        alarmCode = cand;
        break;
    }
    acur = acur.ParentId;
    guard++;
}
ScriptMessage("NPC_TARGET:RESULT:" + oname + ":" + (native ? "1" : "0") + ":" + stepCode + ":" + alarmCode);

=== CALL ===

var code = Data.Code.ByName("gml_Object_obj_golden_npc_Alarm_0");
if (code == null) {
    ScriptMessage("ERROR: Code entry not found: gml_Object_obj_golden_npc_Alarm_0");
    return;
}
try {
    string existingGml = GetDecompiledText(code);
    if (existingGml.IndexOf("id == 113928") >= 0) {
        ScriptMessage("SKIP: guard already present");
        return;
    }
    string newGml = @"if (id == 113928)
{
    exit;
}" + "\n" + existingGml;
    CodeImportGroup importGroup = new(Data)
    {
        MainThreadAction = MainThreadAction
    };
    importGroup.QueueReplace(code, newGml);
    importGroup.Import();
    ScriptMessage("OK: guarded");
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.Message);
}
