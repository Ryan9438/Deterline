// C3b pass1 (READ-ONLY): dump source fonts metadata + shared texture page
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
string dumpDir = @"/tmp/golden_cjk_work";
string[] srcNames = { "fnt_main", "fnt_maintext", "fnt_plain" };
try {
    if (Data.Fonts.Any(f => f.Name != null && f.Name.Content == "fnt_cjk_main")) {
        ScriptMessage("ERROR: fnt_cjk_main 已存在（重复注入）——先 experiment-restore/undo 回滚");
        return;
    }
    var sb = new System.Text.StringBuilder();
    UndertaleEmbeddedTexture page = null;
    foreach (string nm in srcNames) {
        var f = Data.Fonts.FirstOrDefault(x => x.Name != null && x.Name.Content == nm);
        if (f == null || f.Texture == null) { ScriptMessage("ERROR: font not found: " + nm); return; }
        var tpi = f.Texture;
        var emb = tpi.TexturePage;
        if (emb == null || emb.TextureData == null) { ScriptMessage("ERROR: no texture page for " + nm); return; }
        if (page == null) { page = emb; }
        else if (page != emb) { ScriptMessage("ERROR: 源字体不在同一纹理页（MVP 仅支持共享页布局）"); return; }
        sb.AppendLine("PAGE " + nm + " " + tpi.SourceX + " " + tpi.SourceY + " " + tpi.SourceWidth + " " + tpi.SourceHeight
                      + " " + emb.TextureData.Width + " " + emb.TextureData.Height);
        sb.AppendLine("FONT " + nm + " " + f.EmSize + " " + (f.EmSizeIsFloat ? 1 : 0) + " " + f.Charset + " "
                      + f.AntiAliasing + " " + f.LineHeight + " " + f.Ascender + " " + f.AscenderOffset + " "
                      + f.RangeStart + " " + f.RangeEnd + " " + (f.Bold ? 1 : 0) + " "
                      + tpi.SourceX + " " + tpi.SourceY + " " + tpi.SourceWidth + " " + tpi.SourceHeight);
        foreach (var g in f.Glyphs) {
            string kern = "";
            foreach (var k in g.Kerning) kern += " " + k.Character + ":" + k.ShiftModifier;
            sb.AppendLine("GLYPH " + nm + " " + g.Character + " " + g.SourceX + " " + g.SourceY + " "
                          + g.SourceWidth + " " + g.SourceHeight + " " + g.Offset + " " + g.Shift + " "
                          + g.Kerning.Count + kern);
        }
    }
    File.WriteAllText(Path.Combine(dumpDir, "fonts.txt"), sb.ToString());
    using (var fs = File.Create(Path.Combine(dumpDir, "emb_page.png"))) {
        page.TextureData.Image.SavePng(fs);
    }
    ScriptMessage("CJK_PASS1_OK fonts=" + srcNames.Length + " page=" + page.TextureData.Width + "x" + page.TextureData.Height);
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.GetType().Name + ": " + ex.Message);
}