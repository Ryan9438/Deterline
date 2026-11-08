// B3：变量分解 boot（2026-11-08）——每臂只动一个变量，分解 B2 "C-ARM 空框"歧义
// 布局定论（离线精读 Draw_0+SCR_TEXTTYPE）：writer 推进=spacing(typer 固定常数)，
//   glyph Shift/Offset 只影响单字定位不影响步进 → CJK 12px 最佳 typer=31(spacing 12, wxend 9999)
// 臂矩阵（全 facechoice=3 / faceemotion=0 / msc=0 / msg[0]带"/%%" / msg[1]="%%%"）：
//   A-SWP  typer5 @(160,400) fnt_maintext 原表 + emb19 maintext 区品红重染  → V3 页内像素换是否触达字体渲染
//   E-KANA typer31 @(320,400) fnt_maintext 原表 + 同上重染 + 假名消息       → V4 码点(>0x3041)是否到达字体查找
//   B-TBL  typer30 @(480,400) fnt_main→映射→fnt_ja_main 原TPI#6543+共享表  → V1 glyph 表替换+查找链路（期待乱码瓦片）
//          （消息尾带 canary U+9FFF：表内码位、坐标在 TPI 外 → 测 UV 钳位）
//   C-NPG  typer68 @(480,240) fnt_plain→映射→fnt_ja_plain 新256²页+fnt_maintext原表 → V2/约束④（face3 修正版）
//   D-CTRL typer3  @(160,240) fnt_curs 原版对照（B2 已证渲染，teal、typer3 设计性上移出框）
//   D-CTRL 触发块内附语言探针（relative + 绝对路径双写 zcode_lang_probe.txt）
// ⚠️ scr_setfont 只映射 main/plain 两行（故意不动 fnt_maintext——A/E 臂要走原字体）
// ⚠️ 复现前先 experiment-restore（基线 fc049850）；SIGTERM 退出会回写 game.ios，pkill 后必须重新 restore
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UndertaleModLib.Util;
string atlasDir = @"/Users/ryan/Desktop/UT 存档修改/Deterline/build/font_cjk_inpage";
try {
    var spec = System.Text.Json.JsonDocument.Parse(
        File.ReadAllText(Path.Combine(atlasDir, "glyphs_inpage.json"))).RootElement;

    // ── 0) 幂等守卫 ──
    // ⚠️ 不能用 "newfont = fnt_ja_main;" 判重——基线 scr_setfont 的 ja 分支本就含该串
    //    （B1/B2 的同款守卫因此恒真→映射从未注入！B3 守卫改用单行插入形态 + 注释标记）
    var sf0 = GetDecompiledText("gml_Script_scr_setfont");
    if (sf0.Contains("B3_MAP") || sf0.Contains("if (newfont == fnt_main) { newfont = fnt_ja_main; }")) {
        ScriptMessage("ERROR: setfont 已有 B3 映射——先 experiment-restore"); return; }
    string stepName = "gml_Object_obj_cactus_Step_1";
    if (GetDecompiledText(stepName).Contains("B3_ARM")) { ScriptMessage("ERROR: B3 臂已注入"); return; }

    // ── 1) emb19 页内像素重染（仅 fnt_maintext TPI 区 (768,0,256,256) → 品红；页身份不变）──
    byte[] png19 = File.ReadAllBytes(Path.Combine(atlasDir, "emb19_page_new.png"));
    var img19 = GMImage.FromPng(png19, false);
    var tex19 = Data.EmbeddedTextures.First(t => t.Name != null && t.Name.Content == "Texture 19");
    if (tex19.TextureData.Width != 1024) { ScriptMessage("ERROR: Texture 19 尺寸异常 " + tex19.TextureData.Width); return; }
    tex19.TextureData.Image = img19;
    ScriptMessage("B3_EMB19_OK");

    // ── 2) fnt_ja_main：原 TPI 不动，仅换 glyph 表为共享表（V1 隔离：表路径）──
    var jaMain = Data.Fonts.First(f => f.Name.Content == "fnt_ja_main");
    jaMain.Glyphs.Clear();
    int nShared = 0;
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
        jaMain.Glyphs.Add(g);
        nShared++;
    }
    // canary U+9FFF：按码点序插入（⚠️ 表内有 U+FF5E"～">0x9FFF，不能尾追加）；
    // 坐标在 TPI(0,1024,1024²) 之外 → B-TBL 消息尾渲染品红块=按页绝对坐标采样（无钳位），
    // 乱码瓦片=钳位到 TPI 边缘
    var canarySpec = spec.GetProperty("canary");
    var canary = new UndertaleFont.Glyph();
    canary.Character = (ushort)canarySpec.GetProperty("code").GetInt32();
    canary.SourceX = (ushort)canarySpec.GetProperty("x").GetInt32();
    canary.SourceY = (ushort)canarySpec.GetProperty("y").GetInt32();
    canary.SourceWidth = 12; canary.SourceHeight = 12;
    canary.Offset = 0; canary.Shift = 12; canary.UnknownAlwaysZero = 0;
    int ci = 0;
    while (ci < jaMain.Glyphs.Count && jaMain.Glyphs[ci].Character < canary.Character) ci++;
    jaMain.Glyphs.Insert(ci, canary);
    nShared++;
    ScriptMessage("B3_JAMAIN_OK n=" + nShared + " tpiSX=" + jaMain.Texture.SourceX + " tpiSY=" + jaMain.Texture.SourceY);

    // ── 3) fnt_ja_plain：新 256² 页 + 新 TPI + fnt_maintext 原表（V2/约束④）──
    var jaPlain = Data.Fonts.First(f => f.Name.Content == "fnt_ja_plain");
    var mtSrc = Data.Fonts.First(f => f.Name.Content == "fnt_maintext");
    if (mtSrc.Glyphs.Count != 269) { ScriptMessage("ERROR: fnt_maintext glyph 数异常 " + mtSrc.Glyphs.Count); return; }
    byte[] pngN = File.ReadAllBytes(Path.Combine(atlasDir, "armn_page.png"));
    var imgN = GMImage.FromPng(pngN, false);
    var texN = new UndertaleEmbeddedTexture();
    texN.Name = Data.Strings.MakeString("Texture " + Data.EmbeddedTextures.Count);
    texN.Scaled = 0; texN.GeneratedMips = 0; texN.TextureLoaded = true;
    texN.TextureWidth = imgN.Width; texN.TextureHeight = imgN.Height;
    texN.TextureData = new UndertaleEmbeddedTexture.TexData();
    texN.TextureData.Image = imgN;
    Data.EmbeddedTextures.Add(texN);
    var tpiN = new UndertaleTexturePageItem();
    tpiN.Name = Data.Strings.MakeString("PageItem " + Data.TexturePageItems.Count);
    tpiN.SourceX = 0; tpiN.SourceY = 0;
    tpiN.SourceWidth = (ushort)imgN.Width; tpiN.SourceHeight = (ushort)imgN.Height;
    tpiN.TargetX = 0; tpiN.TargetY = 0;
    tpiN.TargetWidth = (ushort)imgN.Width; tpiN.TargetHeight = (ushort)imgN.Height;
    tpiN.BoundingWidth = (ushort)imgN.Width; tpiN.BoundingHeight = (ushort)imgN.Height;
    tpiN.TexturePage = texN;
    Data.TexturePageItems.Add(tpiN);
    jaPlain.Texture = tpiN;
    jaPlain.Glyphs.Clear();
    foreach (var gSrc in mtSrc.Glyphs) {
        var g = new UndertaleFont.Glyph();
        g.Character = gSrc.Character; g.SourceX = gSrc.SourceX; g.SourceY = gSrc.SourceY;
        g.SourceWidth = gSrc.SourceWidth; g.SourceHeight = gSrc.SourceHeight;
        g.Offset = gSrc.Offset; g.Shift = gSrc.Shift; g.UnknownAlwaysZero = 0;
        jaPlain.Glyphs.Add(g);
    }
    ScriptMessage("B3_JAPLAIN_OK page=" + texN.Name.Content + " " + imgN.Width + "x" + imgN.Height
        + " glyphs=" + jaPlain.Glyphs.Count + "(maintext原表)");

    // ── 4) scr_setfont 无条件映射 ×2（故意不含 fnt_maintext）──
    var sf = Data.Code.ByName("gml_Script_scr_setfont");
    string sgml = GetDecompiledText("gml_Script_scr_setfont");
    int anchor = sgml.IndexOf("draw_set_font(newfont);");
    if (anchor < 0) { ScriptMessage("ERROR: setfont anchor missing"); return; }
    string pre = "// B3_MAP\n" +
                 "if (newfont == fnt_main) { newfont = fnt_ja_main; }\n" +
                 "if (newfont == fnt_plain) { newfont = fnt_ja_plain; }\n";
    sgml = sgml.Insert(anchor, pre);
    var ig1 = new CodeImportGroup(Data) { MainThreadAction = MainThreadAction };
    ig1.QueueReplace(sf, sgml);
    ig1.Import();

    // ── 5) preload 无条件 prefetch（既有页）──
    var pc = Data.Code.ByName("gml_Script_scr_preload_textures");
    string pgml = GetDecompiledText("gml_Script_scr_preload_textures");
    int pcAnchor = pgml.IndexOf("sprite_prefetch(spr_maincharad);");
    if (pcAnchor < 0) { ScriptMessage("ERROR: preload anchor missing"); return; }
    pgml = pgml.Insert(pcAnchor, "sprite_prefetch(spr_fonts_ja_preload); // B3_UNCOND\n");
    var ig2 = new CodeImportGroup(Data) { MainThreadAction = MainThreadAction };
    ig2.QueueReplace(pc, pgml);
    ig2.Import();
    ScriptMessage("B3_CODES_OK");

    // ── 6) 五臂注入（扁平已验证形态 + 语言探针）──
    var room = Data.Rooms.First(r => r.Name.Content == "room_ruins1");
    var cactus = Data.GameObjects.First(o => o.Name.Content == "obj_cactus");
    var stepCode = Data.Code.ByName(stepName);
    string tgml = GetDecompiledText(stepName);
    var arms = new[] {
        new { name = "A-SWP",  typer = 5,  x = 160, y = 400,
              msg = "* A-SWP 123/%%", probe = false },
        new { name = "E-KANA", typer = 31, x = 320, y = 400,
              msg = "* E-KANAあいうえお/%%", probe = false },
        new { name = "B-TBL",  typer = 30, x = 480, y = 400,
              msg = "* B-TBL 456\u9FFF/%%", probe = false },
        new { name = "C-NPG",  typer = 68, x = 480, y = 240,
              msg = "* C-NPG 789/%%", probe = false },
        new { name = "D-CTRL", typer = 3,  x = 160, y = 240,
              msg = "* D-CTRL 123/%%", probe = true },
    };
    string probeContent = "\"lang=[\" + string(global.language) + \"] locale=[\" + string(global.locale) + \"] oslang=[\" + os_get_language() + \"] osregion=[\" + os_get_region() + \"\"";
    var blocks = new System.Text.StringBuilder();
    var ids = new List<uint>();
    foreach (var arm in arms) {
        uint iid = Data.GeneralInfo.LastObj;
        Data.GeneralInfo.LastObj = iid + 1;
        ids.Add(iid);
        var inst = new UndertaleRoom.GameObject();
        inst.InstanceID = iid;
        inst.X = arm.x; inst.Y = arm.y;
        inst.ObjectDefinition = cactus;
        room.GameObjects.Add(inst);
        string probeCode = "";
        if (arm.probe) {
            probeCode = "        var _pp = file_text_open_write(\"zcode_lang_probe.txt\");\n" +
                "        file_text_write_string(_pp, " + probeContent + ");\n" +
                "        file_text_close(_pp);\n" +
                "        var _pq = file_text_open_write(\"/Users/ryan/Library/Application Support/Undertale/zcode_lang_probe.txt\");\n" +
                "        file_text_write_string(_pq, " + probeContent + ");\n" +
                "        file_text_close(_pq);\n";
        }
        blocks.Append("// B3_ARM " + arm.name + "\n");
        blocks.Append("if (id == " + iid + " && !instance_exists(obj_dialoguer) && !instance_exists(OBJ_WRITER) && !instance_exists(obj_choicer))\n{\n");
        blocks.Append("    if (distance_to_object(obj_mainchara) < 60)\n    {\n");
        blocks.Append("        global.msc = 0;\n");
        blocks.Append("        global.typer = " + arm.typer + ";\n");
        blocks.Append("        global.facechoice = 3;\n        global.faceemotion = 0;\n");
        blocks.Append("        global.msg[0] = \"" + arm.msg + "\";\n");
        blocks.Append("        global.msg[1] = \"%%%\";\n");
        if (arm.probe) blocks.Append(probeCode);
        blocks.Append("        instance_create(0, 0, obj_dialoguer);\n");
        blocks.Append("    }\n}\n");
        ScriptMessage("B3_ARM " + arm.name + " id=" + iid + " typer=" + arm.typer + " @(" + arm.x + "," + arm.y + ")");
    }
    tgml = tgml + "\n" + blocks.ToString();
    var ig3 = new CodeImportGroup(Data) { MainThreadAction = MainThreadAction };
    ig3.QueueReplace(stepCode, tgml);
    ig3.Import();
    ScriptMessage("B3_COMPLETE ids=" + string.Join(",", ids) + " shared_n=" + nShared
        + " fonts=" + Data.Fonts.Count + " tex=" + Data.EmbeddedTextures.Count + " tpi=" + Data.TexturePageItems.Count);
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.GetType().Name + ": " + ex.Message);
}
