// C3b S6 pass2 (WRITE): 中文页内重排栈（B4 实证形态，AUDIT 报告 §九）
//   emb20 象限换页（页身份不变）+ fnt_ja_maintext 重指向 TPI#6543 + 共享表 4064 字形
//   + scr_setfont 单行映射（槽位判重）+ preload 无条件 prefetch
//   ⚠️ 守卫不能 Contains "newfont = fnt_ja_maintext;"（基线 ja 分支本就含，恒真陷阱）
using System;
using System.IO;
using System.Linq;
using UndertaleModLib.Util;   // GMImage.FromPng(byte[], bool verifyHeader)
string workDir = @"/tmp/golden_cjk_work";
try {
    // ── 0) 幂等守卫（计数式：基线 ja 分支含 1 处 fnt_ja_maintext 映射）──
    var sfChk = GetDecompiledText("gml_Script_scr_setfont");
    int nMap = sfChk.Split(new[]{"newfont = fnt_ja_maintext;"}, StringSplitOptions.None).Length - 1;
    if (nMap > 1) { ScriptMessage("ERROR: CJK 映射已存在（n=" + nMap + "）——先回滚"); return; }
    var jaText = Data.Fonts.FirstOrDefault(f => f.Name != null && f.Name.Content == "fnt_ja_maintext");
    if (jaText == null) { ScriptMessage("ERROR: fnt_ja_maintext not found"); return; }
    if (jaText.Glyphs.Count > 1000) { ScriptMessage("ERROR: 共享表已注入（glyph=" + jaText.Glyphs.Count + "）"); return; }

    // ── 1) emb20 象限换页（页身份不变；换页底图已由 font_emb20_compose 离线合成并 --verify）──
    byte[] png20 = File.ReadAllBytes(Path.Combine(workDir, "emb20_page_new.png"));
    var img20 = GMImage.FromPng(png20, false);
    var tex20 = Data.EmbeddedTextures.FirstOrDefault(t => t.Name != null && t.Name.Content == "Texture 20");
    if (tex20 == null || tex20.TextureData == null || tex20.TextureData.Width != 2048) {
        ScriptMessage("ERROR: Texture 20 缺失或尺寸异常"); return;
    }
    tex20.TextureData.Image = img20;

    // ── 2) fnt_ja_maintext：TPI 重指向 #6543（(0,1024) 1024² 象限）+ 共享表 ──
    var tpi = Data.TexturePageItems.FirstOrDefault(t => t.SourceX == 0 && t.SourceY == 1024
                    && t.SourceWidth == 1024 && t.SourceHeight == 1024 && t.TexturePage == tex20);
    if (tpi == null) { ScriptMessage("ERROR: TPI#6543 not found"); return; }
    jaText.Texture = tpi;
    var spec = System.Text.Json.JsonDocument.Parse(
        File.ReadAllText(Path.Combine(workDir, "glyphs_inpage.json"))).RootElement;
    jaText.Glyphs.Clear();
    int n = 0;
    foreach (var ge in spec.GetProperty("glyphs").EnumerateArray()) {
        var g = new UndertaleFont.Glyph();
        g.Character = (ushort)ge[0].GetInt32();
        g.SourceX = (ushort)ge[1].GetInt32();
        g.SourceY = (ushort)ge[2].GetInt32();
        g.SourceWidth = (ushort)ge[3].GetInt32();
        g.SourceHeight = (ushort)ge[4].GetInt32();
        g.Offset = (short)ge[5].GetInt32();
        g.Shift = (short)ge[6].GetInt32();
        g.UnknownAlwaysZero = 0;
        jaText.Glyphs.Add(g);
        n++;
    }
    // 排序/去重不变量（RV-B）：引擎字形查找假定按码点有序
    var codes = jaText.Glyphs.Select(x => (int)x.Character).ToList();
    if (!codes.SequenceEqual(codes.OrderBy(c => c)) || codes.Distinct().Count() != codes.Count) {
        ScriptMessage("ERROR: glyph 表排序/去重不变量破坏"); return;
    }

    // ── 3) scr_setfont 单行映射（唯一代码改动点；计数判重见守卫）──
    var sf = Data.Code.ByName("gml_Script_scr_setfont");
    string sgml = GetDecompiledText("gml_Script_scr_setfont");
    int anchor = sgml.IndexOf("draw_set_font(newfont);");
    if (anchor < 0) { ScriptMessage("ERROR: setfont anchor missing"); return; }
    sgml = sgml.Insert(anchor, "// CJK_MAP\nif (newfont == fnt_maintext) { newfont = fnt_ja_maintext; }\n");
    var ig1 = new CodeImportGroup(Data) { MainThreadAction = MainThreadAction };
    ig1.QueueReplace(sf, sgml);
    ig1.Import();

    // ── 4) preload 无条件 prefetch（既有页）──
    var pc = Data.Code.ByName("gml_Script_scr_preload_textures");
    string pgml = GetDecompiledText("gml_Script_scr_preload_textures");
    int pcAnchor = pgml.IndexOf("sprite_prefetch(spr_maincharad);");
    if (pcAnchor < 0) { ScriptMessage("ERROR: preload anchor missing"); return; }
    int nPre = pgml.Split(new[]{"sprite_prefetch(spr_fonts_ja_preload);"}, StringSplitOptions.None).Length - 1;
    if (nPre > 1) { ScriptMessage("ERROR: preload 已有无条件分支（n=" + nPre + "）"); return; }
    pgml = pgml.Insert(pcAnchor, "sprite_prefetch(spr_fonts_ja_preload); // CJK_UNCOND\n");
    var ig2 = new CodeImportGroup(Data) { MainThreadAction = MainThreadAction };
    ig2.QueueReplace(pc, pgml);
    ig2.Import();

    ScriptMessage("CJK_PASS2_OK glyphs=" + n + " tpi=(0,1024) setfont_map=1 preload_uncond=1");
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.GetType().Name + ": " + ex.Message);
}