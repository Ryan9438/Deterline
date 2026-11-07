// B2：真正的四臂实验（face3 修正版）——页内图集 + 无条件映射 + 预加载 + 四臂
// 臂C=typer5(fnt_ja_maintext@共享图集,主判据) 臂M=typer0(fnt_ja_main@图集 Scale2)
// 臂N=typer2(fnt_ja_plain@新页原表,约束④证伪) 臂T=typer3(fnt_curs 原版对照)
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UndertaleModLib.Util;
string atlasDir = @"/Users/ryan/Desktop/UT 存档修改/Deterline/build/font_cjk_inpage";
try {
    var spec = System.Text.Json.JsonDocument.Parse(
        File.ReadAllText(Path.Combine(atlasDir, "glyphs_inpage.json"))).RootElement;

    // 1) emb#20 象限替换（页身份不变）
    byte[] png20 = File.ReadAllBytes(Path.Combine(atlasDir, "emb20_page_new.png"));
    var img20 = GMImage.FromPng(png20, false);
    var tex20 = Data.EmbeddedTextures.First(t => t.Name != null && t.Name.Content == "Texture 20");
    tex20.TextureData.Image = img20;

    // 2) 三字体共享表（每字体独立 Glyph 实例！PointerList 按对象实例索引）
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
                        && t.SourceWidth == 1024 && t.SourceHeight == 1024 && t.TexturePage == tex20);
    loadShared(jaMain);
    // Scale2 移除（B2 实测扰乱 writer 全局字符推进）
    jaText.Texture = jaMain.Texture;
    loadShared(jaText);
    jaPlain.Texture = jaMain.Texture;
    loadShared(jaPlain);
    ScriptMessage("B2C_FONTS_OK main=" + jaMain.Glyphs.Count + " text=" + jaText.Glyphs.Count
        + " plain=" + jaPlain.Glyphs.Count);

    // 3) scr_setfont 无条件映射 ×3
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
    // 4) preload：无条件 prefetch ja 预加载精灵（既有页）
    var pc = Data.Code.ByName("gml_Script_scr_preload_textures");
    string pgml = GetDecompiledText("gml_Script_scr_preload_textures");
    int pcAnchor = pgml.IndexOf("sprite_prefetch(spr_maincharad);");
    if (!pgml.Contains("B2_UNCOND") && pcAnchor >= 0) {
        pgml = pgml.Insert(pcAnchor, "sprite_prefetch(spr_fonts_ja_preload); // B2_UNCOND\n");
        var ig2 = new CodeImportGroup(Data) { MainThreadAction = MainThreadAction };
        ig2.QueueReplace(pc, pgml);
        ig2.Import();
    }
    ScriptMessage("B2C_CODES_OK");

    // 5) 四臂（全 facechoice=3，消息带 /%%，msc=0，射程 60，分散布点避花坛）
    var room = Data.Rooms.First(r => r.Name.Content == "room_ruins1");
    var cactus = Data.GameObjects.First(o => o.Name.Content == "obj_cactus");
    string stepName = "gml_Object_obj_cactus_Step_1";
    var stepCode = Data.Code.ByName(stepName);
    string tgml = GetDecompiledText(stepName);
    var arms = new[] {
        new { typer = 5, x = 480, y = 400, msg = "* C-ARM 中 文 测 试 /%%", fc = 3 },
        new { typer = 0, x = 160, y = 400, msg = "* M-ARM 中 文 测 试 /%%", fc = 3 },
        new { typer = 2, x = 480, y = 240, msg = "* N-ARM abc 123/%%", fc = 3 },
        new { typer = 3, x = 160, y = 240, msg = "* T-CTRL abc 123/%%", fc = 3 },
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
        blocks.Append("if (id == " + iid + " && !instance_exists(obj_dialoguer) && !instance_exists(OBJ_WRITER) && !instance_exists(obj_choicer))\n{\n");
        blocks.Append("    if (distance_to_object(obj_mainchara) < 60)\n    {\n");
        blocks.Append("        global.msc = 0;\n        global.typer = " + arm.typer + ";\n");
        blocks.Append("        global.facechoice = " + arm.fc + ";\n        global.faceemotion = 0;\n");
        blocks.Append("        global.msg[0] = \"" + arm.msg + "\";\n");
        blocks.Append("        instance_create(0, 0, obj_dialoguer);\n    }\n}\n");
        ScriptMessage("B2C_ARM id=" + iid + " typer=" + arm.typer + " @(" + arm.x + "," + arm.y + ")");
    }
    tgml = tgml + "\n" + blocks.ToString();
    var ig3 = new CodeImportGroup(Data) { MainThreadAction = MainThreadAction };
    ig3.QueueReplace(stepCode, tgml);
    ig3.Import();
    ScriptMessage("B2C_COMPLETE");
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.GetType().Name + ": " + ex.Message);
}
