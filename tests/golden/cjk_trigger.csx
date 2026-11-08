// C3b S6 cjk-trigger：CJK 对话触发块（B4 实证全形态）
using System;
using System.Linq;
try {
    var room = Data.Rooms.First(r => r.Name.Content == "room_ruins1");
    var obj = Data.GameObjects.First(o => o.Name.Content == "obj_cactus");
    string stepName = "gml_Object_obj_cactus_Step_1";
    var stepCode = Data.Code.ByName(stepName);
    string tgml = GetDecompiledText(stepName);
    if (tgml.Contains("CJK_TRIGGER")) { ScriptMessage("ERROR: CJK 触发块已存在——先回滚"); return; }
    // 幂等守卫（计数式）：ja_maintext 共享表未注入则拒绝（触发块依赖 CJK 栈）
    var jaText = Data.Fonts.FirstOrDefault(f => f.Name != null && f.Name.Content == "fnt_ja_maintext");
    if (jaText == null || jaText.Glyphs.Count <= 1000) {
        ScriptMessage("ERROR: CJK 页内栈未注入——先运行 cjk-font"); return;
    }
    uint iid = Data.GeneralInfo.LastObj;
    Data.GeneralInfo.LastObj = iid + 1;
    var inst = new UndertaleRoom.GameObject();
    inst.InstanceID = iid;
    inst.X = 220; inst.Y = 330;
    inst.ObjectDefinition = obj;
    room.GameObjects.Add(inst);
    string block = ""
        + "if (id == " + iid + " && !instance_exists(obj_dialoguer) && !instance_exists(OBJ_WRITER) && !instance_exists(obj_choicer))\n"
        + "{\n"
        + "    if (distance_to_object(obj_mainchara) < 60)\n"
        + "    {\n"
        + "        global.msc = 0;\n"
        + "        global.typer = 31;\n"
        + "        global.facechoice = 3;\n        global.faceemotion = 0;\n"
        + "        global.msg[0] = \"* 托丽尔你好，这里是中文测试。&第二行内容稍微长一些需要折行。/%%\";\n"
        + "        global.msg[1] = \"%%%\";\n"
        + "        instance_create(0, 0, obj_dialoguer);\n"
        + "    }\n"
        + "}\n"
        + "// CJK_TRIGGER\n";
    tgml = tgml + "\n" + block;
    var ig = new CodeImportGroup(Data) { MainThreadAction = MainThreadAction };
    ig.QueueReplace(stepCode, tgml);
    ig.Import();
    ScriptMessage("CJK_TRIGGER_OK id=" + iid + " typer=31 @(220,330)");
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.GetType().Name + ": " + ex.Message);
}