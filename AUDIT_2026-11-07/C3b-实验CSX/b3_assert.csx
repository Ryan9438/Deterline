// B3 断言复检（对保存后的 game.ios 副本运行；产物 PNG 供离线 PIL 复核）
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
string atlasDir = @"/Users/ryan/Desktop/UT 存档修改/Deterline/build/font_cjk_inpage";
try {
    var spec = System.Text.Json.JsonDocument.Parse(
        File.ReadAllText(Path.Combine(atlasDir, "glyphs_inpage.json"))).RootElement;
    int nShared = spec.GetProperty("glyphs").GetArrayLength();

    ScriptMessage("A_COUNT fonts=" + Data.Fonts.Count + " tex=" + Data.EmbeddedTextures.Count
        + " tpi=" + Data.TexturePageItems.Count + " (基线应为 20/tex基线+1/tpi基线+1)");

    // tex19 页位图落盘（离线核对品红区）
    var tex19 = Data.EmbeddedTextures.First(t => t.Name != null && t.Name.Content == "Texture 19");
    using (var fs = File.Create("/tmp/b3_tex19_page.png"))
        tex19.TextureData.Image.SavePng(fs);
    ScriptMessage("A_EMB19 dumped " + tex19.TextureWidth + "x" + tex19.TextureHeight);

    // 新页存在且 256²，ja_plain 指向它
    var texLast = Data.EmbeddedTextures[Data.EmbeddedTextures.Count - 1];
    ScriptMessage("A_NEWPAGE last=" + texLast.Name.Content + " " + texLast.TextureWidth + "x" + texLast.TextureHeight);

    var jaMain = Data.Fonts.First(f => f.Name.Content == "fnt_ja_main");
    var jaPlain = Data.Fonts.First(f => f.Name.Content == "fnt_ja_plain");
    var mtSrc = Data.Fonts.First(f => f.Name.Content == "fnt_maintext");
    var curs = Data.Fonts.First(f => f.Name.Content == "fnt_curs");

    ScriptMessage("A_JAMAIN n=" + jaMain.Glyphs.Count + "(期望" + (nShared + 1) + "=4064+canary) tpiSX=" + jaMain.Texture.SourceX
        + " tpiSY=" + jaMain.Texture.SourceY + "(期望 0,1024 原TPI不动) scale=" + jaMain.ScaleX + "x" + jaMain.ScaleY);
    var codesM = jaMain.Glyphs.Select(g => (int)g.Character).ToList();
    ScriptMessage("A_JAMAIN_TABLE sorted=" + codesM.SequenceEqual(codesM.OrderBy(c => c))
        + " uniq=" + (codesM.Distinct().Count() == codesM.Count)
        + " canary=" + codesM.Contains(0x9FFF) + " ascii_n=" + codesM.Count(c => c >= 32 && c <= 126));

    bool plainOnNew = jaPlain.Texture.TexturePage == texLast;
    var codesP = jaPlain.Glyphs.Select(g => (int)g.Character).ToList();
    ScriptMessage("A_JAPLAIN onNewPage=" + plainOnNew + " n=" + jaPlain.Glyphs.Count + "(期望269)"
        + " sorted=" + codesP.SequenceEqual(codesP.OrderBy(c => c))
        + " mtTextureStill=" + (mtSrc.Texture.TexturePage == tex19));

    // 未动字体核对
    var mtTpi = mtSrc.Texture;
    ScriptMessage("A_UNTOUCHED maintext n=" + mtSrc.Glyphs.Count + " tpi=(" + mtTpi.SourceX + "," + mtTpi.SourceY
        + "," + mtTpi.SourceWidth + "," + mtTpi.SourceHeight + ")(期望 768,0,256,256)"
        + " curs n=" + curs.Glyphs.Count + "(期望96)");

    string sf = GetDecompiledText("gml_Script_scr_setfont");
    // ⚠️ 反编译会剥注释、重排花括号——判重一律用反编译稳定串+计数（基线各含 1 处 ja 分支映射）
    int nMain = sf.Split(new[]{"newfont = fnt_ja_main;"}, StringSplitOptions.None).Length - 1;
    int nPlain = sf.Split(new[]{"newfont = fnt_ja_plain;"}, StringSplitOptions.None).Length - 1;
    int nMt = sf.Split(new[]{"newfont = fnt_ja_maintext;"}, StringSplitOptions.None).Length - 1;
    ScriptMessage("A_SETFONT main=" + nMain + "(期望2) plain=" + nPlain + "(期望2) maintext=" + nMt + "(期望1)");
    string pr = GetDecompiledText("gml_Script_scr_preload_textures");
    int nPre = pr.Split(new[]{"sprite_prefetch(spr_fonts_ja_preload);"}, StringSplitOptions.None).Length - 1;
    ScriptMessage("A_PRELOAD uncond=" + nPre + "(期望2)");

    string st = GetDecompiledText("gml_Object_obj_cactus_Step_1");
    ScriptMessage("A_STEP typer_sets=" + (st.Split(new[]{"global.typer = "}, StringSplitOptions.None).Length - 1)
        + " msc0=" + (st.Split(new[]{"global.msc = 0;"}, StringSplitOptions.None).Length - 1)
        + " face3=" + (st.Split(new[]{"global.facechoice = 3;"}, StringSplitOptions.None).Length - 1)
        + " msg1=" + (st.Split(new[]{"global.msg[1] = \"%%%\";"}, StringSplitOptions.None).Length - 1)
        + " ids=" + st.Contains("id == 113927") + st.Contains("id == 113931")
        + " probe=" + st.Contains("zcode_lang_probe.txt"));
    var room = Data.Rooms.First(r => r.Name.Content == "room_ruins1");
    ScriptMessage("A_DONE");
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.GetType().Name + ": " + ex.Message);
}
