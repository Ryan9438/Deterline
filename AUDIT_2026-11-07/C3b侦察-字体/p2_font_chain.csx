// C3b recon probe 2: dialog font chain (READ-ONLY)
// Full decompile scan for draw_set_font / fnt_ references + dialoguer object inventory.
using System;
using System.Linq;
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;

ScriptMessage("=== P2 DIALOG FONT CHAIN ===");

// Phase A: dialog/text-related game objects (name only; code linkage comes from Phase B)
ScriptMessage("--- Phase A: GameObjects matching dialog/text/font ---");
foreach (var go in Data.GameObjects) {
    string n = go.Name.Content.ToLower();
    if (n.Contains("dialog") || n.Contains("text") || n.Contains("font")) {
        ScriptMessage("OBJ|" + go.Name.Content);
    }
}

// Phase B: code entries whose NAME references dialoguer/text/font (fast targeted set)
ScriptMessage("--- Phase B: code names matching dialoguer/dialog/font ---");
var namedCodes = new List<UndertaleCode>();
foreach (var c in Data.Code) {
    if (c.ParentEntry != null) continue;
    string n = c.Name.Content.ToLower();
    if (n.Contains("dialoguer") || n.Contains("setfont") || n.Contains("scr_text")) namedCodes.Add(c);
}
ScriptMessage("NAMED_MATCH_COUNT:" + namedCodes.Count);
foreach (var c in namedCodes) ScriptMessage("  CODE_NAME:" + c.Name.Content);

// Phase C: FULL decompile scan of every parent code entry for draw_set_font / fnt_ usage
ScriptMessage("--- Phase C: full decompile scan (this may take a while) ---");
var fontUsage = new Dictionary<string, List<string>>();   // font name -> code entries
var setFontCalls = new List<string>();                    // code entries calling draw_set_font
var rx = new Regex(@"draw_set_font\s*\(\s*([A-Za-z0-9_]+)");
var rxFont = new Regex(@"\bfnt_[A-Za-z0-9_]+");
int scanned = 0, failed = 0;
var sw = System.Diagnostics.Stopwatch.StartNew();
var fileLines = new List<string>();
foreach (var c in Data.Code) {
    if (c.ParentEntry != null) continue;
    string txt;
    try { txt = GetDecompiledText(c.Name.Content); }
    catch { failed++; continue; }
    scanned++;
    bool hasSetFont = txt.Contains("draw_set_font");
    if (!hasSetFont && !txt.Contains("fnt_")) continue;
    string codeName = c.Name.Content;
    foreach (Match m in rx.Matches(txt)) {
        setFontCalls.Add(codeName + " -> " + m.Groups[1].Value);
        List<string> l;
        if (!fontUsage.TryGetValue(m.Groups[1].Value, out l)) fontUsage[m.Groups[1].Value] = l = new List<string>();
        if (!l.Contains(codeName)) l.Add(codeName);
    }
    foreach (Match m in rxFont.Matches(txt)) {
        List<string> l;
        if (!fontUsage.TryGetValue(m.Value, out l)) fontUsage[m.Value] = l = new List<string>();
        if (!l.Contains(codeName)) l.Add(codeName);
    }
    // keep matched lines for file output
    foreach (var line in txt.Split('\n')) {
        if (line.Contains("draw_set_font") || line.Contains("fnt_"))
            fileLines.Add(codeName + " | " + line.Trim());
    }
}
sw.Stop();
ScriptMessage("SCAN_DONE scanned=" + scanned + " failed=" + failed + " seconds=" + sw.Elapsed.TotalSeconds.ToString("F1"));

ScriptMessage("--- Phase D: font usage map ---");
foreach (var kv in fontUsage.OrderBy(k => k.Key))
    ScriptMessage("USE|" + kv.Key + "|count=" + kv.Value.Count + "|entries=" + string.Join(",", kv.Value.Take(25)) + (kv.Value.Count > 25 ? ",..." : ""));

ScriptMessage("--- Phase E: draw_set_font call sites (first 80) ---");
int i = 0;
foreach (var s in setFontCalls) {
    if (i++ >= 80) { ScriptMessage("  ...more=" + (setFontCalls.Count - 80)); break; }
    ScriptMessage("SETFONT|" + s);
}

// write full matched-lines file
File.WriteAllLines("/Users/ryan/Desktop/UT 存档修改/Deterline/AUDIT_2026-11-07/C3b侦察-字体/p2_fnt_lines.txt", fileLines);
ScriptMessage("FILE_WRITTEN:p2_fnt_lines.txt lines=" + fileLines.Count);
ScriptMessage("P2_DONE");
