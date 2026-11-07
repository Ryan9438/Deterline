// C3b recon probe 2b: dump decompiled dialog font chain codes (READ-ONLY)
using System;
using System.Linq;
using System.Collections.Generic;
using System.IO;

ScriptMessage("=== P2b DIALOGUE CODE DUMP ===");
string outDir = "/Users/ryan/Desktop/UT 存档修改/Deterline/AUDIT_2026-11-07/C3b侦察-字体/decompiled";

// obj_dialoguer code entries (parents only) + chain scripts
var wanted = new List<string>();
foreach (var c in Data.Code) {
    if (c.ParentEntry != null) continue;
    string n = c.Name.Content;
    if (n.StartsWith("gml_Object_obj_dialoguer")) wanted.Add(n);
}
string[] scripts = new string[] {
    "gml_Script_scr_setfont", "gml_Script_SCR_TEXTTYPE",
    "gml_Object_obj_base_writer_Draw_0", "gml_Object_obj_base_writer_Create_0",
    "gml_Script_scr_draw_name_curs", "gml_Script_scr_textspec",
    "gml_Script_scr_setfontja", "gml_Script_scr_54tilde"
};
foreach (var s in scripts) if (Data.Code.Any(c => c.ParentEntry == null && c.Name.Content == s)) wanted.Add(s);

ScriptMessage("DUMP_COUNT:" + wanted.Count);
foreach (var name in wanted) {
    try {
        string txt = GetDecompiledText(name);
        string safe = name.Replace("/", "_");
        File.WriteAllText(Path.Combine(outDir, safe + ".txt"), txt);
        // print only font-relevant lines for the report
        var hits = txt.Split('\n').Select((l, i) => new { l = l.Trim(), i })
            .Where(x => x.l.Contains("draw_set_font") || x.l.Contains("fnt_") || x.l.Contains("global.lang") || x.l.Contains("font"))
            .Take(12);
        foreach (var h in hits) ScriptMessage("HIT|" + name + ":" + (h.i + 1) + "| " + h.l);
        ScriptMessage("WROTE|" + name + " lines=" + txt.Split('\n').Length);
    } catch (Exception e) {
        ScriptMessage("ERROR|decompile failed " + name + ": " + e.Message);
    }
}
ScriptMessage("P2b_DONE");
