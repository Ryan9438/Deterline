// C3b recon probe 2c: SCR_TEXTSETUP + global.language setter chain (READ-ONLY)
using System;
using System.Linq;
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;

ScriptMessage("=== P2c LAST LINK ===");

// SCR_TEXTSETUP full decompile
try {
    string txt = GetDecompiledText("gml_Script_SCR_TEXTSETUP");
    File.WriteAllText("/Users/ryan/Desktop/UT 存档修改/Deterline/AUDIT_2026-11-07/C3b侦察-字体/decompiled/gml_Script_SCR_TEXTSETUP.txt", txt);
    ScriptMessage("SCR_TEXTSETUP lines=" + txt.Split('\n').Length);
    foreach (var line in txt.Split('\n'))
        if (line.Contains("myfont") || line.Contains("font") || line.Contains("OBJ_WRITER") || line.Contains("writer"))
            ScriptMessage("  | " + line.Trim());
} catch (Exception e) { ScriptMessage("ERROR: SCR_TEXTSETUP decompile failed: " + e.Message); }

// find where global.language is assigned (setter chain) — full scan for 'global.language ='
ScriptMessage("--- global.language assignment scan ---");
var rx = new Regex(@"global\.language\s*=[^=]");
var rxLang = new Regex(@"\bscr_language\w*|\bset_language\b|\blang_\w+");
var hits = new List<string>();
int scanned = 0;
foreach (var c in Data.Code) {
    if (c.ParentEntry != null) continue;
    string txt;
    try { txt = GetDecompiledText(c.Name.Content); } catch { continue; }
    scanned++;
    foreach (Match m in rx.Matches(txt)) {
        var line = txt.Split('\n').FirstOrDefault(l => l.Contains("global.language") && l.Contains("=") && !l.Contains("=="));
        if (line != null && !hits.Contains(c.Name.Content)) {
            hits.Add(c.Name.Content);
            ScriptMessage("LANGSET|" + c.Name.Content + " | " + line.Trim());
        }
    }
}
ScriptMessage("SCAN:" + scanned + " entries, language-setter codes=" + hits.Count);

// language scripts inventory
ScriptMessage("--- scripts with 'lang' in name ---");
foreach (var s in Data.Scripts)
    if (s.Name.Content.ToLower().Contains("lang") && s.Code != null && s.Code.ParentEntry == null)
        ScriptMessage("  SCR|" + s.Name.Content + " -> " + s.Code.Name.Content);

ScriptMessage("P2c_DONE");
