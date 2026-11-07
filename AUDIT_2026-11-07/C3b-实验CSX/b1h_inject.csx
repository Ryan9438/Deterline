// B1h：单臂、出生点旁、逐字复刻已验证生成器形态（typer5 + facechoice + 纯 ASCII）
using System;
using System.Linq;
try {
    var room = Data.Rooms.First(r => r.Name.Content == "room_ruins1");
    var cactus = Data.GameObjects.First(o => o.Name.Content == "obj_cactus");
    string stepName = "gml_Object_obj_cactus_Step_1";
    var stepCode = Data.Code.ByName(stepName);
    string tgml = GetDecompiledText(stepName);
    uint iid = Data.GeneralInfo.LastObj;
    Data.GeneralInfo.LastObj = iid + 1;
    var inst = new UndertaleRoom.GameObject();
    inst.InstanceID = iid;
    inst.X = 350; inst.Y = 260;
    inst.ObjectDefinition = cactus;
    room.GameObjects.Add(inst);
    string block =
        "if (id == " + iid + " && !instance_exists(obj_dialoguer) && !instance_exists(OBJ_WRITER) && !instance_exists(obj_choicer))\n" +
        "{\n" +
        "    if (distance_to_object(obj_mainchara) < 60)\n" +
        "    {\n" +
        "        global.msc = 0;\n" +
        "        global.typer = 5;\n" +
        "        global.facechoice = 0;\n" +
        "        global.faceemotion = 0;\n" +
        "        global.msg[0] = \"* HELLO B1H abc 123\";\n" +
        "        global.msg[1] = \"%%%\";\n" +
        "        instance_create(0, 0, obj_dialoguer);\n" +
        "    }\n" +
        "}\n";
    tgml = tgml + "\n" + block;
    var ig = new CodeImportGroup(Data) { MainThreadAction = MainThreadAction };
    ig.QueueReplace(stepCode, tgml);
    ig.Import();
    ScriptMessage("B1H_OK id=" + iid);
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.GetType().Name + ": " + ex.Message);
}
