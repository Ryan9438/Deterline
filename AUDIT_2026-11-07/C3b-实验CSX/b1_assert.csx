// S4 断言复检（对 /tmp/b1.ios 运行）
using System;
using System.Linq;
ScriptMessage("A_COUNT fonts=" + Data.Fonts.Count + " textures=" + Data.EmbeddedTextures.Count
    + " tpis=" + Data.TexturePageItems.Count);
var jm = Data.Fonts.First(f => f.Name.Content == "fnt_ja_main");
var jt = Data.Fonts.First(f => f.Name.Content == "fnt_ja_maintext");
var jp = Data.Fonts.First(f => f.Name.Content == "fnt_ja_plain");
ScriptMessage("A_PTR main==text:" + (jm.Texture == jt.Texture) + " plain@newpage:" + (jp.Texture.TexturePage != jm.Texture.TexturePage)
    + " scale=" + jm.ScaleX + "x" + jm.ScaleY);
var codes = jt.Glyphs.Select(g => (int)g.Character).ToList();
ScriptMessage("A_TABLE text=" + codes.Count + " sorted=" + codes.SequenceEqual(codes.OrderBy(c => c))
    + " uniq=" + (codes.Distinct().Count() == codes.Count)
    + " range=" + codes.Min() + "-" + codes.Max() + " canary=" + codes.Contains(0x9FFF));
var codesM = jm.Glyphs.Select(g => (int)g.Character).ToList();
ScriptMessage("A_TABLE main=" + codesM.Count + " sorted=" + codesM.SequenceEqual(codesM.OrderBy(c => c))
    + " uniq=" + (codesM.Distinct().Count() == codesM.Count));
var codesP = jp.Glyphs.Select(g => (int)g.Character).ToList();
ScriptMessage("A_TABLE plain=" + codesP.Count + " sorted=" + codesP.SequenceEqual(codesP.OrderBy(c => c)));
var room = Data.Rooms.First(r => r.Name.Content == "room_ruins1");
int b1 = room.GameObjects.Count(g => g.InstanceID >= 113927 && g.InstanceID <= 113930);
ScriptMessage("A_ROOM instances=" + b1 + " lastobj=" + Data.GeneralInfo.LastObj);
string sf = GetDecompiledText("gml_Script_scr_setfont");
ScriptMessage("A_SETFONT zh_uncond=" + sf.Contains("newfont = fnt_ja_main;"));
string pr = GetDecompiledText("gml_Script_scr_preload_textures");
ScriptMessage("A_PRELOAD uncond_count=" + (pr.Split(new[]{"sprite_prefetch(spr_fonts_ja_preload);"}, StringSplitOptions.None).Length - 1) + " (>=2 即无条件分支已加)");
string st = GetDecompiledText("gml_Object_obj_cactus_Step_1");
ScriptMessage("A_STEP typer_sets=" + (st.Split(new[]{"global.typer = "}, StringSplitOptions.None).Length - 1) + " flat_ok=" + st.Contains("!instance_exists(obj_dialoguer)") + " ids=" + st.Contains("id == 113927") + st.Contains("id == 113930"));
ScriptMessage("A_DONE");
