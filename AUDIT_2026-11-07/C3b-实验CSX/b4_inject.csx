// B4：完整中文栈集成（B3 全组件分别实证后的整合 boot）
//   V1 表替换 ✓(B-TBL) + V3 页内像素换 ✓(A-SWP/E-KANA) + V4 码点 ✓(E-KANA 假名) + typer31 排版 ✓
// 栈：emb20 象限换页(身份不变) + fnt_ja_maintext@TPI6543 共享表 + scr_setfont maintext 映射(单行 B4_MAP 守卫)
//     + preload 无条件 prefetch + 两臂：
//       D-CTRL typer3 @(160,240) 原版对照 + 语言探针（harness）
//       B4-MAIN typer31 @(220,330) 无空格 CJK：msg "* B4中文测试ABC/%%"（B3 实证可行走地面）
// ⚠️ 守卫不能用 "newfont = fnt_ja_maintext;"（基线 ja 分支本就含）——用 B4_MAP 标记 + 单行形态
using System;
using System.IO;
using System.Linq;
using UndertaleModLib.Util;
string atlasDir = @"/Users/ryan/Desktop/UT 存档修改/Deterline/build/font_cjk_inpage";
try {
    var spec = System.Text.Json.JsonDocument.Parse(
        File.ReadAllText(Path.Combine(atlasDir, "glyphs_inpage.json"))).RootElement;

    // ── 0) 幂等守卫 ──
    var sf0 = GetDecompiledText("gml_Script_scr_setfont");
    if (sf0.Contains("B4_MAP") || sf0.Contains("if (newfont == fnt_maintext) { newfont = fnt_ja_maintext; }")) {
        ScriptMessage("ERROR: setfont 已有 B4 映射——先 restore"); return; }
    string stepName = "gml_Object_obj_cactus_Step_1";
    if (GetDecompiledText(stepName).Contains("B4_ARM")) { ScriptMessage("ERROR: B4 臂已注入"); return; }

    // ── 1) emb20 象限换页（页身份不变，(0,1024)-(1023,2047) = 共享图集 + 金丝雀块）──
    byte[] png20 = File.ReadAllBytes(Path.Combine(atlasDir, "emb20_page_new.png"));
    var img20 = GMImage.FromPng(png20, false);
    var tex20 = Data.EmbeddedTextures.First(t => t.Name != null && t.Name.Content == "Texture 20");
    if (tex20.TextureData.Width != 2048) { ScriptMessage("ERROR: Texture 20 尺寸异常"); return; }
    tex20.TextureData.Image = img20;
    ScriptMessage("B4_EMB20_OK");

    // ── 2) fnt_ja_maintext：TPI 重指向 #6543（1024² 象限）+ 共享表 ──
    var jaText = Data.Fonts.First(f => f.Name.Content == "fnt_ja_maintext");
    jaText.Texture = Data.TexturePageItems.First(t => t.SourceX == 0 && t.SourceY == 1024
                        && t.SourceWidth == 1024 && t.SourceHeight == 1024
                        && t.TexturePage == tex20);
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
    ScriptMessage("B4_JATEXT_OK n=" + n + " tpi=(" + jaText.Texture.SourceX + "," + jaText.Texture.SourceY + ")");

    // ── 3) scr_setfont：仅 maintext 映射（单行 + 标记）──
    var sf = Data.Code.ByName("gml_Script_scr_setfont");
    string sgml = GetDecompiledText("gml_Script_scr_setfont");
    int anchor = sgml.IndexOf("draw_set_font(newfont);");
    if (anchor < 0) { ScriptMessage("ERROR: setfont anchor missing"); return; }
    sgml = sgml.Insert(anchor, "// B4_MAP\nif (newfont == fnt_maintext) { newfont = fnt_ja_maintext; }\n");
    var ig1 = new CodeImportGroup(Data) { MainThreadAction = MainThreadAction };
    ig1.QueueReplace(sf, sgml);
    ig1.Import();

    // ── 4) preload 无条件 prefetch ──
    var pc = Data.Code.ByName("gml_Script_scr_preload_textures");
    string pgml = GetDecompiledText("gml_Script_scr_preload_textures");
    int pcAnchor = pgml.IndexOf("sprite_prefetch(spr_maincharad);");
    if (pcAnchor < 0) { ScriptMessage("ERROR: preload anchor missing"); return; }
    pgml = pgml.Insert(pcAnchor, "sprite_prefetch(spr_fonts_ja_preload); // B4_UNCOND\n");
    var ig2 = new CodeImportGroup(Data) { MainThreadAction = MainThreadAction };
    ig2.QueueReplace(pc, pgml);
    ig2.Import();
    ScriptMessage("B4_CODES_OK");

    // ── 5) 两臂 ──
    var room = Data.Rooms.First(r => r.Name.Content == "room_ruins1");
    var cactus = Data.GameObjects.First(o => o.Name.Content == "obj_cactus");
    var stepCode = Data.Code.ByName(stepName);
    string tgml = GetDecompiledText(stepName);
    var arms = new[] {
        new { name = "D-CTRL", typer = 3,  x = 160, y = 240,
              msg = "* D-CTRL 123/%%", probe = true },
        new { name = "B4-MAIN", typer = 31, x = 220, y = 330,
              msg = "* B4中文测试ABC/%%", probe = false },
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
                "        var _pq = file_text_open_write(\"/Users/ryan/Library/Application Support/com.tobyfox.undertale/zcode_lang_probe.txt\");\n" +
                "        file_text_write_string(_pq, " + probeContent + ");\n" +
                "        file_text_close(_pq);\n";
        }
        blocks.Append("// B4_ARM " + arm.name + "\n");
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
        ScriptMessage("B4_ARM " + arm.name + " id=" + iid + " typer=" + arm.typer + " @(" + arm.x + "," + arm.y + ")");
    }
    tgml = tgml + "\n" + blocks.ToString();
    var ig3 = new CodeImportGroup(Data) { MainThreadAction = MainThreadAction };
    ig3.QueueReplace(stepCode, tgml);
    ig3.Import();
    ScriptMessage("B4_COMPLETE ids=" + string.Join(",", ids) + " fonts=" + Data.Fonts.Count
        + " tex=" + Data.EmbeddedTextures.Count + " tpi=" + Data.TexturePageItems.Count);
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.GetType().Name + ": " + ex.Message);
}
