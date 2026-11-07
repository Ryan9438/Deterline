// B1 综合判别 boot 注入（研讨会2 价值派 S2；一次性实验 CSX，不进生产管线）
// 前置：基线 + 空 room_ruins1（无其他注入）；产物由 S4 断言脚本复检后才允许 boot
// 臂：Ctrl=typer3(fnt_curs 不映射) / Arm-C=typer5(fnt_ja_maintext@共享图集) /
//     Arm-M=typer0(fnt_ja_main@图集 Scale2) / Arm-N=typer30(fnt_ja_papyrus_btl@新页原表)
// 顺带：canary U+9FFF（maintext 表内、坐标在 TPI 外 → 测 UV 钳位 U2b）+
//       裸文件名语言探针（bootv 缺陷修正版）
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UndertaleModLib.Util;

string workDir = @"/Users/ryan/Library/Application Support/Steam/steamapps/common/Undertale/UNDERTALE.app/Contents/Resources/cjk_work";
string atlasDir = @"/Users/ryan/Desktop/UT 存档修改/Deterline/build/font_cjk_inpage";
try {
    // ── 0) 幂等守卫 ──
    if (Data.Fonts.First(f => f.Name.Content == "fnt_ja_maintext").Texture ==
        Data.Fonts.First(f => f.Name.Content == "fnt_ja_main").Texture) {
        ScriptMessage("ERROR: B1 已注入（maintext 已重指向）——先 experiment-restore");
        return;
    }
    var spec = System.Text.Json.JsonDocument.Parse(
        File.ReadAllText(Path.Combine(atlasDir, "glyphs_inpage.json"))).RootElement;

    // ── 1) emb#20 页位图原位替换（GMImage.FromPng → 既有 TexData；页身份不变）──
    byte[] png20 = File.ReadAllBytes(Path.Combine(atlasDir, "emb20_page_new.png"));
    var img20 = GMImage.FromPng(png20, false);
    var tex20 = Data.EmbeddedTextures.First(t => t.Name != null && t.Name.Content == "Texture 20");
    tex20.TextureData.Image = img20;

    // ── 2) 三字体改造：共享表（升序+去重，TPI 相对坐标）──
    // ⚠️ 每字体必须新建 Glyph 对象——UndertalePointerList 按“对象实例”建序列化索引，
    // 同一实例加进两个列表 = save 期 "same key" IOException（S4 彩排实证）
    var jaMain = Data.Fonts.First(f => f.Name.Content == "fnt_ja_main");
    var jaText = Data.Fonts.First(f => f.Name.Content == "fnt_ja_maintext");
    var jaPlain = Data.Fonts.First(f => f.Name.Content == "fnt_ja_plain");
    Action<UndertaleFont> loadShared = (UndertaleFont f) => {
        f.Glyphs.Clear();
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
            f.Glyphs.Add(g);
        }
    };
    jaMain.Texture = Data.TexturePageItems.First(t => t.SourceX == 0 && t.SourceY == 1024
                        && t.SourceWidth == 1024 && t.SourceHeight == 1024
                        && t.TexturePage == tex20);   // TPI#6543（原指针，显式重申）
    loadShared(jaMain);
    jaMain.ScaleX = 2f; jaMain.ScaleY = 2f;            // Arm-M：12px→24px 试验位
    jaText.Texture = jaMain.Texture;                   // 重指向（同页内）
    loadShared(jaText);
    // canary：仅 maintext 表内、按码点序插入（保持排序不变量；坐标在 TPI 外 → U2b）
    var canary = new UndertaleFont.Glyph();
    canary.Character = (ushort)spec.GetProperty("canary").GetProperty("code").GetInt32();
    canary.SourceX = (ushort)spec.GetProperty("canary").GetProperty("x").GetInt32();
    canary.SourceY = (ushort)spec.GetProperty("canary").GetProperty("y").GetInt32();
    canary.SourceWidth = 12; canary.SourceHeight = 12;
    canary.Offset = 0; canary.Shift = 12; canary.UnknownAlwaysZero = 0;
    int ci = 0;
    while (ci < jaText.Glyphs.Count && jaText.Glyphs[ci].Character < canary.Character) ci++;
    jaText.Glyphs.Insert(ci, canary);
    jaPlain.Texture = jaMain.Texture;                  // 重指向（同页内）
    loadShared(jaPlain);
    ScriptMessage("B1_FONTS_OK main=" + jaMain.Glyphs.Count + " text=" + jaText.Glyphs.Count
        + " plain=" + jaPlain.Glyphs.Count + " scale2=true canary=true");

    // ── 3) Arm-N：新页 + 新 TPI（零新字体）+ fnt_ja_plain 指过去（maintext 原表原像素搬运）──
    // 修订注：价值派原案用 typer30→papyrus_btl，但 SCR_TEXTTYPE 从不引用 ja 字体
    // （ja 转换全在 scr_setfont）——改用 typer2→fnt_plain→(无条件映射)→fnt_ja_plain。
    // 新页 256² = fnt_maintext 原 TPI 区域像素（emb19 (768,0,256,256) 裁出），
    // fnt_ja_plain.Glyphs = fnt_maintext 原 glyph 列表（emSize 同 12，度量匹配）。
    var btl = Data.Fonts.First(f => f.Name.Content == "fnt_ja_plain");
    byte[] pngNew = File.ReadAllBytes(Path.Combine(atlasDir, "armn_page.png"));
    var imgNew = GMImage.FromPng(pngNew, false);
    var texN = new UndertaleEmbeddedTexture();
    texN.Name = Data.Strings.MakeString("Texture " + Data.EmbeddedTextures.Count);
    texN.Scaled = 0; texN.GeneratedMips = 0; texN.TextureLoaded = true;
    texN.TextureWidth = imgNew.Width; texN.TextureHeight = imgNew.Height;
    texN.TextureData = new UndertaleEmbeddedTexture.TexData();
    texN.TextureData.Image = imgNew;
    Data.EmbeddedTextures.Add(texN);
    var tpiN = new UndertaleTexturePageItem();
    tpiN.Name = Data.Strings.MakeString("PageItem " + Data.TexturePageItems.Count);
    tpiN.SourceX = 0; tpiN.SourceY = 0;
    tpiN.SourceWidth = (ushort)imgNew.Width; tpiN.SourceHeight = (ushort)imgNew.Height;
    tpiN.TargetX = 0; tpiN.TargetY = 0;
    tpiN.TargetWidth = (ushort)imgNew.Width; tpiN.TargetHeight = (ushort)imgNew.Height;
    tpiN.BoundingWidth = (ushort)imgNew.Width; tpiN.BoundingHeight = (ushort)imgNew.Height;
    tpiN.TexturePage = texN;
    Data.TexturePageItems.Add(tpiN);
    btl.Texture = tpiN;                                 // 原表不动、像素已搬运到新页
    var mtSrc = Data.Fonts.First(f => f.Name.Content == "fnt_maintext");
    btl.Glyphs.Clear();
    foreach (var gSrc in mtSrc.Glyphs) {
        var g = new UndertaleFont.Glyph();
        g.Character = gSrc.Character; g.SourceX = gSrc.SourceX; g.SourceY = gSrc.SourceY;
        g.SourceWidth = gSrc.SourceWidth; g.SourceHeight = gSrc.SourceHeight;
        g.Offset = gSrc.Offset; g.Shift = gSrc.Shift; g.UnknownAlwaysZero = 0;
        btl.Glyphs.Add(g);
    }
    ScriptMessage("B1_ARMN_OK tex=" + texN.Name.Content + " " + imgNew.Width + "x" + imgNew.Height
        + " plainGlyphs=" + btl.Glyphs.Count + "(maintext 原表)");

    // ── 4) scr_setfont 无条件映射 ×3 ──
    var sf = Data.Code.ByName("gml_Script_scr_setfont");
    string sgml = GetDecompiledText("gml_Script_scr_setfont");
    if (!sgml.Contains("newfont = fnt_ja_main;")) {
        int anchor = sgml.IndexOf("draw_set_font(newfont);");
        string pre = "if (newfont == fnt_main) { newfont = fnt_ja_main; }\n" +
                     "if (newfont == fnt_maintext) { newfont = fnt_ja_maintext; }\n" +
                     "if (newfont == fnt_plain) { newfont = fnt_ja_plain; }\n";
        sgml = sgml.Insert(anchor, pre);
        var ig1 = new CodeImportGroup(Data) { MainThreadAction = MainThreadAction };
        ig1.QueueReplace(sf, sgml);
        ig1.Import();
    }
    // ── 5) scr_preload_textures：无条件 prefetch 既有 ja 预加载精灵（既有页）──
    var pc = Data.Code.ByName("gml_Script_scr_preload_textures");
    string pgml = GetDecompiledText("gml_Script_scr_preload_textures");
    int pcAnchor = pgml.IndexOf("sprite_prefetch(spr_maincharad);");
    if (pcAnchor < 0) { ScriptMessage("ERROR: preload anchor missing"); return; }
    if (!pgml.Contains("B1_UNCOND")) {
        pgml = pgml.Insert(pcAnchor, "sprite_prefetch(spr_fonts_ja_preload); // B1_UNCOND\n");
        var ig2 = new CodeImportGroup(Data) { MainThreadAction = MainThreadAction };
        ig2.QueueReplace(pc, pgml);
        ig2.Import();
    }
    ScriptMessage("B1_CODES_OK setfont+preload patched");

    // ── 6) 四臂 NPC：room_ruins1 内 4×obj_cactus 实例 + id 触发块（扁平已验证形态）──
    // Ctrl=typer3(fnt_curs 原版) / Arm-C=typer5(共享图集+canary+探针) /
    // Arm-M=typer0(共享图集 Scale2) / Arm-N=typer2(fnt_ja_plain@新页原表)
    var room = Data.Rooms.First(r => r.Name.Content == "room_ruins1");
    var cactus = Data.GameObjects.First(o => o.Name.Content == "obj_cactus");
    string stepName = "gml_Object_obj_cactus_Step_1";
    var stepCode = Data.Code.ByName(stepName);
    string tgml = GetDecompiledText(stepName);
    if (tgml.Contains("B1_ARM")) { ScriptMessage("ERROR: B1 臂已注入"); return; }
    var canaryChar = "\u9FFF";
    var arms = new[] {
        new { typer = 3, x = 160, y = 160, msg = "* T3-CTRL abc 123", probe = false },
        new { typer = 2, x = 480, y = 160, msg = "* N-ARM abc 123", probe = false },
        new { typer = 0, x = 160, y = 320, msg = "* M-ARM 中文测试", probe = false },
        new { typer = 5, x = 480, y = 320, msg = "* C-ARM 中文测试" + canaryChar, probe = true },
    };
    var blocks = new System.Text.StringBuilder();
    foreach (var arm in arms) {
        uint iid = Data.GeneralInfo.LastObj;
        Data.GeneralInfo.LastObj = iid + 1;
        var inst = new UndertaleRoom.GameObject();
        inst.InstanceID = iid;
        inst.X = arm.x; inst.Y = arm.y;
        inst.ObjectDefinition = cactus;
        room.GameObjects.Add(inst);
        string probeCode = arm.probe
            ? "var _pf = file_text_open_write(\"zcode_lang_probe.txt\");\n            " +
              "file_text_write_string(_pf, \"lang=[\" + global.language + \"] locale=[\" + global.locale + \"]\");\n            " +
              "file_text_close(_pf);\n            "
            : "";
        blocks.Append("if (id == " + iid + " && !instance_exists(obj_dialoguer) && !instance_exists(OBJ_WRITER) && !instance_exists(obj_choicer))\n{\n");
        blocks.Append("    if (distance_to_object(obj_mainchara) < 99999)\n    {\n");
        blocks.Append("        global.typer = " + arm.typer + ";\n        " + probeCode);
        blocks.Append("global.msg[0] = \"" + arm.msg + "\";\n");
        blocks.Append("        global.msg[1] = \"%%%\";\n");
        blocks.Append("        instance_create(0, 0, obj_dialoguer);\n    }\n}\n");
        ScriptMessage("B1_ARM_INST id=" + iid + " typer=" + arm.typer + " @(" + arm.x + "," + arm.y + ")");
    }
    tgml = tgml + "\n// B1_ARM begin\n" + blocks.ToString() + "// B1_ARM end\n";
    var ig3 = new CodeImportGroup(Data) { MainThreadAction = MainThreadAction };
    ig3.QueueReplace(stepCode, tgml);
    ig3.Import();
    ScriptMessage("B1_INJECT_COMPLETE");
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.GetType().Name + ": " + ex.Message);
}
