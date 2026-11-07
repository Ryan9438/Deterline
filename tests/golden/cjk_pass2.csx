// C3b pass2 (WRITE): inject CJK fonts — plan B (recon report §4 方案B)
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UndertaleModLib.Util;   // GMImage.FromPng 静态调用需要（p3d 实证签名 (byte[], bool verifyHeader)）
string workDir = @"/tmp/golden_cjk_work";
try {
    if (Data.Fonts.Any(f => f.Name != null && f.Name.Content == "fnt_cjk_main")) {
        ScriptMessage("ERROR: fnt_cjk_main 已存在（重复注入）");
        return;
    }
    var spec = System.Text.Json.JsonDocument.Parse(
        File.ReadAllText(Path.Combine(workDir, "atlas_glyphs.json"))).RootElement;
    // 1) 新纹理页 ×2（GMImage.FromPng；本文件页格式为直通 alpha PNG，已由探针 3d 往返实证）
    var texs = new UndertaleEmbeddedTexture[2];
    for (int i = 0; i < 2; i++) {
        byte[] png = File.ReadAllBytes(Path.Combine(workDir, "atlas_page_" + i + ".png"));
        var img = GMImage.FromPng(png, false);
        var tex = new UndertaleEmbeddedTexture();
        tex.Name = Data.Strings.MakeString("Texture " + (Data.EmbeddedTextures.Count + i));
        tex.Scaled = 0; tex.GeneratedMips = 0; tex.TextureLoaded = true;
        tex.TextureWidth = img.Width; tex.TextureHeight = img.Height;
        tex.TextureData = new UndertaleEmbeddedTexture.TexData();
        tex.TextureData.Image = img;
        Data.EmbeddedTextures.Add(tex);
        texs[i] = tex;
    }
    // 2) TexturePageItem ×3（区域 = 字体行带）
    var fontRoot = spec.GetProperty("fonts");
    var tpis = new System.Collections.Generic.Dictionary<string, UndertaleTexturePageItem>();
    foreach (var fdef in new[] { "fnt_cjk_main", "fnt_cjk_maintext", "fnt_cjk_plain" }) {
        var fr = fontRoot.GetProperty(fdef);
        int pageIdx = fr.GetProperty("page").GetInt32();
        int y0 = fr.GetProperty("region_y0").GetInt32();
        int rows = fr.GetProperty("rows").GetInt32();
        int cellH = fr.GetProperty("cell")[1].GetInt32();
        int h = rows * cellH;
        var tpi = new UndertaleTexturePageItem();
        tpi.Name = Data.Strings.MakeString("PageItem " + (Data.TexturePageItems.Count + tpis.Count));
        tpi.SourceX = 0; tpi.SourceY = (ushort)y0;
        tpi.SourceWidth = 2048; tpi.SourceHeight = (ushort)h;
        tpi.TargetX = 0; tpi.TargetY = 0;   // Target 为 TPI 相对（侦察 dump: ja_main target=(0,0,1024,1024)）
        tpi.TargetWidth = 2048; tpi.TargetHeight = (ushort)h;
        tpi.BoundingWidth = 2048; tpi.BoundingHeight = (ushort)h;
        tpi.TexturePage = texs[pageIdx];
        Data.TexturePageItems.Add(tpi);
        tpis[fdef] = tpi;
    }
    // 3) UndertaleFont ×3（标量克隆源字体；ASCII 字形已拷入新图集，中英混排可用）
    var displayNames = new System.Collections.Generic.Dictionary<string, string> {
        { "fnt_cjk_main", "Fusion Pixel CJK Main" },
        { "fnt_cjk_maintext", "Fusion Pixel CJK Maintext" },
        { "fnt_cjk_plain", "Fusion Pixel CJK Plain" },
    };
    int glyphTotal = 0;
    foreach (var fdef in new[] { "fnt_cjk_main", "fnt_cjk_maintext", "fnt_cjk_plain" }) {
        var fr = fontRoot.GetProperty(fdef);
        var f = new UndertaleFont();
        f.Name = Data.Strings.MakeString(fdef);
        f.DisplayName = Data.Strings.MakeString(displayNames[fdef]);
        f.EmSize = fr.GetProperty("emSize").GetSingle();
        f.EmSizeIsFloat = fr.GetProperty("emSizeIsFloat").GetBoolean();
        f.Charset = fr.GetProperty("charset").GetByte();
        f.AntiAliasing = fr.GetProperty("antiAliasing").GetByte();
        f.RangeStart = (ushort)fr.GetProperty("rangeStart").GetInt32();
        f.RangeEnd = (uint)fr.GetProperty("rangeEnd").GetInt32();
        f.LineHeight = (uint)fr.GetProperty("lineHeight").GetInt32();
        f.Ascender = (uint)fr.GetProperty("ascender").GetInt32();
        f.AscenderOffset = fr.GetProperty("ascenderOffset").GetInt32();
        f.ScaleX = 1f; f.ScaleY = 1f; f.SDFSpread = 0;
        f.Bold = fr.GetProperty("bold").GetBoolean(); f.Italic = false;
        f.Texture = tpis[fdef];
        foreach (var ge in fr.GetProperty("glyphs").EnumerateArray()) {
            var g = new UndertaleFont.Glyph();
            g.Character = (ushort)ge[0].GetInt32();
            g.SourceX = (ushort)ge[1].GetInt32();
            g.SourceY = (ushort)ge[2].GetInt32();
            g.SourceWidth = (ushort)ge[3].GetInt32();
            g.SourceHeight = (ushort)ge[4].GetInt32();
            g.Offset = (short)ge[5].GetInt32();
            g.Shift = (short)ge[6].GetInt32();
            g.UnknownAlwaysZero = 0;
            foreach (var ke in ge[7].EnumerateArray()) {
                var k = new UndertaleFont.Glyph.GlyphKerning();
                k.Character = (short)ke[0].GetInt32();
                k.ShiftModifier = (short)ke[1].GetInt32();
                g.Kerning.Add(k);
            }
            f.Glyphs.Add(g);
        }
        glyphTotal += f.Glyphs.Count;
        Data.Fonts.Add(f);
    }
    // 3b) 预加载精灵 ×2（Mac runner 不按需加载新页——ja 页即经 scr_preload_textures
    //     的 sprite_prefetch(spr_fonts_ja_preload) 预加载；游戏内空框实证必要）
    var tpiMain = tpis["fnt_cjk_main"]; var tpiSmall = tpis["fnt_cjk_maintext"];
    var sprA = new UndertaleSprite();
    sprA.Name = Data.Strings.MakeString("spr_fonts_cjk_preload_main");
    sprA.Width = 2; sprA.Height = 2;
    sprA.Textures.Add(new UndertaleSprite.TextureEntry { Texture = tpiMain });
    Data.Sprites.Add(sprA);
    var sprB = new UndertaleSprite();
    sprB.Name = Data.Strings.MakeString("spr_fonts_cjk_preload_small");
    sprB.Width = 2; sprB.Height = 2;
    sprB.Textures.Add(new UndertaleSprite.TextureEntry { Texture = tpiSmall });
    Data.Sprites.Add(sprB);
    // 3c) scr_preload_textures：ja/en 之间插 zh 分支
    var preCode = Data.Code.ByName("gml_Script_scr_preload_textures");
    if (preCode == null) { ScriptMessage("ERROR: gml_Script_scr_preload_textures not found"); return; }
    string preGml = GetDecompiledText("gml_Script_scr_preload_textures");
    // 4) 代码改动：preload zh 分支 + scr_setfont zh 映射（单一 CodeImportGroup）
    var importGroup = new CodeImportGroup(Data) { MainThreadAction = MainThreadAction };
    if (preGml.Contains("spr_fonts_cjk_preload_main")) {
        ScriptMessage("SKIP: preload already patched");
    } else {
        const string anchor = "}\nelse\n{\n    sprite_prefetch(spr_fonts_en_preload);\n}";
        if (!preGml.Contains(anchor)) { ScriptMessage("ERROR: preload anchor not found"); return; }
        preGml = preGml.Replace(anchor,
            "}\nelse if (global.language == \"zh\")\n{\n" +
            "    sprite_prefetch(spr_fonts_cjk_preload_main);\n" +
            "    sprite_prefetch(spr_fonts_cjk_preload_small);\n" +
            "}\nelse\n{\n    sprite_prefetch(spr_fonts_en_preload);\n}");
        importGroup.QueueReplace(preCode, preGml);
    }
    var code = Data.Code.ByName("gml_Script_scr_setfont");
    if (code == null) { ScriptMessage("ERROR: gml_Script_scr_setfont not found"); return; }
    string gml = GetDecompiledText("gml_Script_scr_setfont");
    if (gml.Contains("fnt_cjk_main")) {
        ScriptMessage("SKIP: scr_setfont already patched");
    } else {
        int anchor = gml.IndexOf("draw_set_font(newfont);");
        if (anchor < 0) { ScriptMessage("ERROR: scr_setfont anchor not found"); return; }
        string zh = "if (global.language == \"zh\")\n{\n" +
                    "    if (newfont == fnt_main)\n    {\n        newfont = fnt_cjk_main;\n    }\n" +
                    "    if (newfont == fnt_maintext)\n    {\n        newfont = fnt_cjk_maintext;\n    }\n" +
                    "    if (newfont == fnt_plain)\n    {\n        newfont = fnt_cjk_plain;\n    }\n" +
                    "}\n";
        gml = gml.Insert(anchor, zh);
        importGroup.QueueReplace(code, gml);
    }
    importGroup.Import();
    ScriptMessage("CJK_PASS2_OK fonts=3 textures=2 tpis=3 sprites=2 glyphs=" + glyphTotal);
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.GetType().Name + ": " + ex.Message);
}