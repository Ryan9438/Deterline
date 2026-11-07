// C3b recon probe 3a: glyph structure reflection + in-memory glyph construction test (READ-ONLY, no save)
using System;
using System.Linq;
using System.Reflection;
using System.Collections.Generic;

Func<object, string> enumKV = (o) => {
    if (o == null) return "null";
    var parts = new List<string>();
    foreach (var p in o.GetType().GetProperties(BindingFlags.Public | BindingFlags.Instance))
        parts.Add(p.Name + "=" + p.GetValue(o));
    return string.Join("/", parts);
};

ScriptMessage("=== P3a GLYPH STRUCTURE ===");

// full shape of Glyph nested type and its Kerning element type
Type glyphType = null;
var fnt = Data.Fonts.First(fo => fo.Name.Content == "fnt_main");
foreach (var g in fnt.Glyphs) { glyphType = g.GetType(); break; }
ScriptMessage("GLYPH_TYPE:" + glyphType.FullName);
foreach (var p in glyphType.GetProperties(BindingFlags.Public | BindingFlags.Instance).OrderBy(p => p.Name))
    ScriptMessage("  PROP " + p.PropertyType.FullName + " " + p.Name);

var kernProp = glyphType.GetProperty("Kerning");
if (kernProp != null) {
    var kernList = kernProp.GetValue(fnt.Glyphs.First());
    ScriptMessage("KERNING_LIST_TYPE:" + kernList.GetType().FullName);
    Type enumType = kernList.GetType().GetGenericArguments().FirstOrDefault();
    if (enumType == null) {
        foreach (var g in fnt.Glyphs) {
            var kl = kernProp.GetValue(g);
            if (kl != null) { var first = ((System.Collections.IEnumerable)kl).Cast<object>().FirstOrDefault(); if (first != null) { enumType = first.GetType(); break; } }
        }
    }
    if (enumType != null) {
        ScriptMessage("KERNING_ELEM_TYPE:" + enumType.FullName);
        foreach (var p in enumType.GetProperties(BindingFlags.Public | BindingFlags.Instance))
            ScriptMessage("  KPROP " + p.PropertyType.Name + " " + p.Name);
    } else ScriptMessage("KERNING: no populated examples found");
}

// first 10 glyphs of dialog-candidate fonts with all fields
foreach (string fname in new string[] { "fnt_main", "fnt_maintext", "fnt_curs" }) {
    var f = Data.Fonts.FirstOrDefault(fo => fo.Name.Content == fname);
    if (f == null) { ScriptMessage("ERROR: font not found " + fname); continue; }
    ScriptMessage("--- " + fname + " first 10 of " + f.Glyphs.Count + " ---");
    int n = 0;
    foreach (var g in f.Glyphs) {
        if (n++ >= 10) break;
        string k = "";
        if (g.Kerning != null && g.Kerning.Count > 0) {
            var items = ((System.Collections.IEnumerable)g.Kerning).Cast<object>().Take(3).Select(enumKV);
            k = " kern=" + string.Join(";", items);
        }
        ScriptMessage("  U+" + ((int)g.Character).ToString("X4")
            + " src=" + g.SourceX + "," + g.SourceY + " " + g.SourceWidth + "x" + g.SourceHeight
            + " off=" + g.Offset + " shift=" + g.Shift + " uaz=" + g.UnknownAlwaysZero + k);
    }
}

// CJK examples present in fnt_ja_main (structure sample for non-ASCII glyph)
var ja = Data.Fonts.FirstOrDefault(fo => fo.Name.Content == "fnt_ja_main");
if (ja != null) {
    ScriptMessage("--- fnt_ja_main sample CJK glyphs (first 6 with char>=0x4E00) ---");
    int n = 0;
    foreach (var g in ja.Glyphs.Where(x => x.Character >= 0x4E00)) {
        if (n++ >= 6) break;
        ScriptMessage("  U+" + ((int)g.Character).ToString("X4")
            + " src=" + g.SourceX + "," + g.SourceY + " " + g.SourceWidth + "x" + g.SourceHeight
            + " off=" + g.Offset + " shift=" + g.Shift);
    }
}

// in-memory glyph construction test (NOT saved)
ScriptMessage("--- in-memory Glyph construction test ---");
try {
    var ng = new UndertaleFont.Glyph();
    ng.Character = 0x4E2D; // 中
    ng.SourceX = 100; ng.SourceY = 100; ng.SourceWidth = 20; ng.SourceHeight = 20;
    ng.Offset = 0; ng.Shift = 22;
    ScriptMessage("GLYPH_NEW_OK: U+" + ((int)ng.Character).ToString("X4") + " src=" + ng.SourceX + "," + ng.SourceY + " " + ng.SourceWidth + "x" + ng.SourceHeight + " off=" + ng.Offset + " shift=" + ng.Shift);
    var tmpFont = new UndertaleFont();
    tmpFont.Name = Data.Strings.MakeString("fnt_c3b_probe_tmp");
    tmpFont.Glyphs.Add(ng);
    ScriptMessage("GLYPH_ATTACH_OK: tmpFont.Glyphs.Count=" + tmpFont.Glyphs.Count);
} catch (Exception e) { ScriptMessage("ERROR: glyph construction failed: " + e.GetType().Name + ": " + e.Message); }

ScriptMessage("P3a_DONE");
