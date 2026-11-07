// C3b recon probe 3c: in-memory font construction + Data.Fonts.Add/remove (NO SAVE)
using System;
using System.Linq;
using System.Reflection;
using System.Collections.Generic;

ScriptMessage("=== P3c IN-MEMORY FONT CONSTRUCTION (no save) ===");

var emb20 = Data.EmbeddedTextures[20];
var jaMain = Data.Fonts.First(f => f.Name.Content == "fnt_ja_main");
int beforeFonts = Data.Fonts.Count;
int beforeTPIs = Data.TexturePageItems.Count;

// --- 1. construct a new UndertaleTexturePageItem pointing at existing page emb#20 ---
try {
    var tpi = new UndertaleTexturePageItem();
    tpi.SourceX = 1536; tpi.SourceY = 1416; tpi.SourceWidth = 512; tpi.SourceHeight = 512;
    tpi.TargetX = 0; tpi.TargetY = 0; tpi.TargetWidth = 512; tpi.TargetHeight = 512;
    tpi.BoundingWidth = 512; tpi.BoundingHeight = 512;
    tpi.TexturePage = emb20;
    tpi.Name = Data.Strings.MakeString("PageItem c3b_probe");
    Data.TexturePageItems.Add(tpi);
    int tpiIdx = Data.TexturePageItems.IndexOf(tpi);
    ScriptMessage("TPI_NEW_OK: index=" + tpiIdx + " src=1536,1416 512x512 page=emb#20 name=" + tpi.Name.Content);
    // read back
    var back = Data.TexturePageItems[tpiIdx];
    ScriptMessage("TPI_READBACK_OK: " + back.SourceX + "," + back.SourceY + " " + back.SourceWidth + "x" + back.SourceHeight + " page==emb20:" + (back.TexturePage == emb20));
} catch (Exception e) { ScriptMessage("ERROR: TPI construction failed: " + e.GetType().Name + ": " + e.Message); }

// --- 2. construct a new UndertaleFont and add to Data.Fonts ---
try {
    var f = new UndertaleFont();
    f.Name = Data.Strings.MakeString("fnt_c3b_probe");
    f.DisplayName = Data.Strings.MakeString("C3b Recon Probe Font");
    f.EmSize = 24;
    f.EmSizeIsFloat = false;
    f.RangeStart = 0x4E00;
    f.RangeEnd = 0x9FFF;
    f.Charset = 1;
    f.AntiAliasing = 1;
    f.Bold = false; f.Italic = false;
    f.LineHeight = 40; f.Ascender = 36; f.AscenderOffset = 0;
    f.ScaleX = 1; f.ScaleY = 1; f.SDFSpread = 0;
    // attach to the new TPI (use last added, or ja_main's TPI if step 1 failed)
    var tpi = Data.TexturePageItems.Last();
    f.Texture = tpi;
    // add 4 glyph entries (structure only; no pixels anywhere yet)
    ushort[] chars = { 0x4E2D, 0x6587, 0x6D4B, 0x8BD5 }; // 中文测试
    for (int i = 0; i < chars.Length; i++) {
        var g = new UndertaleFont.Glyph();
        g.Character = chars[i];
        g.SourceX = (ushort)(1536 + 4 + i * 32); g.SourceY = 1420;
        g.SourceWidth = 28; g.SourceHeight = 28;
        g.Offset = 0; g.Shift = 28;
        f.Glyphs.Add(g);
    }
    Data.Fonts.Add(f);
    ScriptMessage("FONT_ADD_OK: Data.Fonts.Count=" + beforeFonts + "->" + Data.Fonts.Count);
    // read back by name
    var back = Data.Fonts.FirstOrDefault(x => x.Name.Content == "fnt_c3b_probe");
    if (back == null) ScriptMessage("ERROR: font lookup by name failed after Add");
    else {
        ScriptMessage("FONT_READBACK_OK: name=" + back.Name.Content + " glyphs=" + back.Glyphs.Count
            + " emSize=" + back.EmSize + " range=" + back.RangeStart + "-" + back.RangeEnd
            + " texture=TPI#" + Data.TexturePageItems.IndexOf(back.Texture)
            + " firstGlyph=U+" + ((int)back.Glyphs[0].Character).ToString("X4"));
    }
    // kerning add test
    var g0 = back.Glyphs[0];
    var k = new UndertaleFont.Glyph.GlyphKerning();
    k.Character = 0x6587; k.ShiftModifier = 2;
    g0.Kerning.Add(k);
    ScriptMessage("KERNING_ADD_OK: count=" + g0.Kerning.Count + " [0].Character=" + g0.Kerning[0].Character + " ShiftModifier=" + g0.Kerning[0].ShiftModifier);
    // modify existing font in-memory: append a glyph to fnt_ja_main (NOT saved)
    int before = jaMain.Glyphs.Count;
    var gNew = new UndertaleFont.Glyph();
    gNew.Character = 0x9FA5; gNew.SourceX = 1900; gNew.SourceY = 1500; gNew.SourceWidth = 28; gNew.SourceHeight = 28; gNew.Shift = 28;
    jaMain.Glyphs.Add(gNew);
    ScriptMessage("EXISTING_FONT_APPEND_OK: fnt_ja_main glyphs " + before + "->" + jaMain.Glyphs.Count);
    // cleanup memory
    jaMain.Glyphs.Remove(gNew);
    Data.Fonts.Remove(f);
    ScriptMessage("CLEANUP_OK: Data.Fonts.Count=" + Data.Fonts.Count + " jaMain.Glyphs=" + jaMain.Glyphs.Count);
} catch (Exception e) { ScriptMessage("ERROR: font construction failed: " + e.GetType().Name + ": " + e.Message + " @ " + e.StackTrace); }

ScriptMessage("NOTE: in-memory mutations are discarded because CLI is run WITHOUT -o (nothing saved to disk)");
ScriptMessage("P3c_DONE");
