// C3b recon probe 1: full font inventory dump (READ-ONLY, no save)
// Run: dotnet UndertaleModCli.dll load game.ios -s p1_fonts_dump.csx
// API shape confirmed by p0: UndertaleFont.Texture (not TexturePage),
// UndertaleFont.Glyph {Character,SourceX/Y/W/H,Offset,Shift,Kerning,UnknownAlwaysZero}
using System;
using System.Linq;
using System.Collections.Generic;
using System.Reflection;
using System.IO;

// ---- helpers: reflect a property or field by name, never throw ----
Func<object, string, object> P = (o, name) => {
    if (o == null) return null;
    var t = o.GetType();
    var pi = t.GetProperty(name, BindingFlags.Public | BindingFlags.Instance);
    if (pi != null) { try { return pi.GetValue(o); } catch (Exception e) { return "ERR:" + e.InnerException?.Message; } }
    var fi = t.GetField(name, BindingFlags.Public | BindingFlags.Instance);
    if (fi != null) { try { return fi.GetValue(o); } catch (Exception e) { return "ERR:" + e.InnerException?.Message; } }
    return "MISSING:" + name;
};
Func<object, string> S = (o) => {
    if (o == null) return "(null)";
    if (o is UndertaleString us) return us.Content;
    return o.ToString();
};
Func<object, string> ShortVal = (o) => {
    if (o == null) return "null";
    if (o is UndertaleString us) return "\"" + us.Content + "\"";
    if (o is UndertaleTexturePageItem ti) {
        int tpi = Data.TexturePageItems.IndexOf(ti);
        int emb = (ti.TexturePage != null) ? Data.EmbeddedTextures.IndexOf(ti.TexturePage) : -1;
        return "TPI#" + tpi + "(emb:" + emb + ")";
    }
    if (o is System.Collections.IList il) return "List[" + il.Count + "]";
    return o.ToString();
};
// TPI geometry one-liner
Func<UndertaleTexturePageItem, string> TpiGeom = (tp) => {
    if (tp == null) return "NONE";
    int emb = (tp.TexturePage != null) ? Data.EmbeddedTextures.IndexOf(tp.TexturePage) : -1;
    return "TPI#" + Data.TexturePageItems.IndexOf(tp)
        + "/emb#" + emb
        + " src=" + tp.SourceX + "," + tp.SourceY + " " + tp.SourceWidth + "x" + tp.SourceHeight
        + " target=" + tp.TargetX + "," + tp.TargetY + " " + tp.TargetWidth + "x" + tp.TargetHeight
        + " bounding=" + tp.BoundingWidth + "x" + tp.BoundingHeight
        + " name=" + S(tp.Name);
};

ScriptMessage("=== P1 FONT INVENTORY ===");
ScriptMessage("FONTCOUNT:" + Data.Fonts.Count);
ScriptMessage("TEXTPAGEITEM_COUNT:" + Data.TexturePageItems.Count);
ScriptMessage("EMBEDDEDTEX_COUNT:" + Data.EmbeddedTextures.Count);
ScriptMessage("NOTE:Data.Textures does not exist in this UTMT build (CS1061 confirmed in first run)");

// ---- per-font summary lines ----
foreach (var f in Data.Fonts) {
    ScriptMessage("FONT|" + f.Name.Content
        + "|glyphs=" + f.Glyphs.Count
        + "|range=" + f.RangeStart + "-" + f.RangeEnd
        + "|charset=" + f.Charset
        + "|aa=" + f.AntiAliasing
        + "|emSize=" + f.EmSize + "(float=" + f.EmSizeIsFloat + ")"
        + "|lineHeight=" + f.LineHeight + "|ascender=" + f.Ascender + "/" + f.AscenderOffset
        + "|scale=" + f.ScaleX + "," + f.ScaleY
        + "|bold=" + f.Bold + "|italic=" + f.Italic
        + "|dispName=" + S(f.DisplayName));
    ScriptMessage("  " + TpiGeom(f.Texture));
}

// ---- glyph samples: first 10 glyphs of key fonts ----
string[] interesting = new string[] { "fnt_marsneedcunnilingus" };
foreach (var f in Data.Fonts) {
    bool want = interesting.Contains(f.Name.Content)
        || f.Name.Content.ToLower().Contains("ja")
        || f.Name.Content.ToLower().Contains("jpn")
        || f.Name.Content.ToLower().Contains("cjk");
    if (!want) continue;
    ScriptMessage("=== GLYPH SAMPLES " + f.Name.Content + " (first 10 of " + f.Glyphs.Count + ") ===");
    int n = 0;
    foreach (var g in f.Glyphs) {
        if (n++ >= 10) break;
        string kern = (g.Kerning != null && g.Kerning.Count > 0) ? " kern[" + g.Kerning.Count + "]" : "";
        var titem = P(g, "TextureItem");
        ScriptMessage("  U+" + ((int)g.Character).ToString("X4") + " '" + (g.Character >= 33 && g.Character < 127 ? ((char)g.Character).ToString() : "?") + "'"
            + " | srcXY=" + g.SourceX + "," + g.SourceY
            + " | WH=" + g.SourceWidth + "x" + g.SourceHeight
            + " | Offset=" + g.Offset + " | Shift=" + g.Shift
            + " | UnknownAlwaysZero=" + g.UnknownAlwaysZero + kern
            + " | TextureItem=" + (titem is string ? (string)titem : ShortVal(titem)));
    }
}

// ---- page occupancy of every font's texture region ----
ScriptMessage("=== FONT TEXTURE PAGE OCCUPANCY ===");
foreach (var f in Data.Fonts) {
    var tp = f.Texture;
    if (tp == null || tp.TexturePage == null) { ScriptMessage("OCC|" + f.Name.Content + "|no texture"); continue; }
    int emb = Data.EmbeddedTextures.IndexOf(tp.TexturePage);
    int pw = tp.TexturePage.TextureWidth, ph = tp.TexturePage.TextureHeight;
    var texData = tp.TexturePage.TextureData;
    int dw = texData != null ? texData.Width : -1, dh = texData != null ? texData.Height : -1;
    // glyph bounding box within the page (glyph SourceX/Y appear page-absolute in GMS1 fonts)
    int minX = int.MaxValue, minY = int.MaxValue, maxX = int.MinValue, maxY = int.MinValue;
    foreach (var g in f.Glyphs) {
        if (g.SourceWidth == 0 || g.SourceHeight == 0) continue;
        minX = Math.Min(minX, g.SourceX); minY = Math.Min(minY, g.SourceY);
        maxX = Math.Max(maxX, g.SourceX + g.SourceWidth); maxY = Math.Max(maxY, g.SourceY + g.SourceHeight);
    }
    bool hasGlyphs = maxX >= minX;
    ScriptMessage("OCC|" + f.Name.Content
        + "|page emb#" + emb + " " + pw + "x" + ph
        + "|texdataWH=" + dw + "x" + dh
        + "|tpiRegion=" + tp.SourceX + "," + tp.SourceY + " " + tp.SourceWidth + "x" + tp.SourceHeight
        + "|glyphBox=" + (hasGlyphs ? (minX + "," + minY + " - " + maxX + "," + maxY + " (" + (maxX - minX) + "x" + (maxY - minY) + ")") : "n/a")
        + "|tpiRegionOverlapsPage=" + (tp.SourceX + tp.SourceWidth <= pw && tp.SourceY + tp.SourceHeight <= ph));
}

// ---- other occupants of the main font's page (to know free space) ----
ScriptMessage("=== CO-OCCUPANTS OF PAGE USED BY fnt_marsneedcunnilingus ===");
var mainFont = Data.Fonts.FirstOrDefault(fo => fo.Name.Content == "fnt_marsneedcunnilingus");
if (mainFont != null && mainFont.Texture != null && mainFont.Texture.TexturePage != null) {
    int emb = Data.EmbeddedTextures.IndexOf(mainFont.Texture.TexturePage);
    ScriptMessage("MAIN_FONT_PAGE emb#" + emb + " size=" + mainFont.Texture.TexturePage.TextureWidth + "x" + mainFont.Texture.TexturePage.TextureHeight);
    foreach (var tpi in Data.TexturePageItems) {
        if (tpi.TexturePage == null || Data.EmbeddedTextures.IndexOf(tpi.TexturePage) != emb) continue;
        // who references this TPI? fonts, sprites, backgrounds
        string usedBy = "";
        foreach (var fo in Data.Fonts) if (fo.Texture == tpi) usedBy += "font:" + fo.Name.Content + " ";
        if (usedBy == "") {
            var spr = Data.Sprites.FirstOrDefault(s => s.Textures != null && s.Textures.Any(tx => tx != null && tx.Texture == tpi));
            if (spr != null) usedBy = "sprite:" + spr.Name.Content;
            var bg = Data.Backgrounds.FirstOrDefault(b => b.Texture == tpi);
            if (bg != null) usedBy = "bg:" + bg.Name.Content;
        }
        ScriptMessage("  TPI#" + Data.TexturePageItems.IndexOf(tpi) + " src=" + tpi.SourceX + "," + tpi.SourceY + " " + tpi.SourceWidth + "x" + tpi.SourceHeight + " usedBy=" + (usedBy == "" ? "?" : usedBy));
    }
}

// ---- JSON dump ----
try {
    var fontsArr = new List<object>();
    foreach (var f in Data.Fonts) {
        var glyphs = new List<object>();
        foreach (var g in f.Glyphs) {
            var gd = new Dictionary<string, object> {
                ["char"] = g.Character,
                ["charHex"] = "U+" + ((int)g.Character).ToString("X4"),
                ["sourceX"] = g.SourceX, ["sourceY"] = g.SourceY,
                ["sourceW"] = g.SourceWidth, ["sourceH"] = g.SourceHeight,
                ["offset"] = g.Offset, ["shift"] = g.Shift,
                ["unknownAlwaysZero"] = g.UnknownAlwaysZero,
                ["kerningCount"] = (g.Kerning != null ? g.Kerning.Count : 0)
            };
            glyphs.Add(gd);
        }
        var tp = f.Texture;
        var tpInfo = new Dictionary<string, object>();
        if (tp != null) {
            tpInfo["texturePageItemIndex"] = Data.TexturePageItems.IndexOf(tp);
            tpInfo["embeddedTextureIndex"] = (tp.TexturePage != null) ? Data.EmbeddedTextures.IndexOf(tp.TexturePage) : -1;
            tpInfo["sourceX"] = tp.SourceX; tpInfo["sourceY"] = tp.SourceY;
            tpInfo["sourceW"] = tp.SourceWidth; tpInfo["sourceH"] = tp.SourceHeight;
            tpInfo["targetX"] = tp.TargetX; tpInfo["targetY"] = tp.TargetY;
            tpInfo["targetW"] = tp.TargetWidth; tpInfo["targetH"] = tp.TargetHeight;
            tpInfo["boundingW"] = tp.BoundingWidth; tpInfo["boundingH"] = tp.BoundingHeight;
        }
        fontsArr.Add(new Dictionary<string, object> {
            ["name"] = f.Name.Content,
            ["displayName"] = S(f.DisplayName),
            ["bold"] = f.Bold, ["italic"] = f.Italic,
            ["rangeStart"] = f.RangeStart, ["rangeEnd"] = f.RangeEnd,
            ["charset"] = f.Charset, ["antiAliasing"] = f.AntiAliasing,
            ["emSize"] = f.EmSize, ["emSizeIsFloat"] = f.EmSizeIsFloat,
            ["lineHeight"] = f.LineHeight, ["ascender"] = f.Ascender, ["ascenderOffset"] = f.AscenderOffset,
            ["scaleX"] = f.ScaleX, ["scaleY"] = f.ScaleY, ["sdfSpread"] = f.SDFSpread,
            ["glyphCount"] = f.Glyphs.Count,
            ["texture"] = tpInfo,
            ["glyphs"] = glyphs
        });
    }
    string json = Newtonsoft.Json.JsonConvert.SerializeObject(fontsArr, Newtonsoft.Json.Formatting.Indented);
    File.WriteAllText("/Users/ryan/Desktop/UT 存档修改/Deterline/AUDIT_2026-11-07/C3b侦察-字体/fonts_dump.json", json);
    ScriptMessage("JSON_WRITTEN:fonts_dump.json bytes=" + json.Length);
} catch (Exception e) {
    ScriptMessage("WARN: JSON dump failed: " + e.Message);
}

ScriptMessage("P1_DONE");
