// B1l：双臂同 boot——arm1=face3/1+字面量(带/%%)；arm2=face0/0+scr_gettext
using System;
using System.Linq;
try {
    var room = Data.Rooms.First(r => r.Name.Content == "room_ruins1");
    var cactus = Data.GameObjects.First(o => o.Name.Content == "obj_cactus");
    string stepName = "gml_Object_obj_cactus_Step_1";
    var stepCode = Data.Code.ByName(stepName);
    string tgml = GetDecompiledText(stepName);
    var arms = new[] {
        new { fc = 3, fe = 1, msg = "global.msg[0] = \"* B1L-FACE3 literal abc/%%\";", tag = "face3" },
        new { fc = 0, fe = 0, msg = "global.msg[0] = scr_gettext(\"obj_b1l\");", tag = "gettext" },
    };
    var blocks = new System.Text.StringBuilder();
    foreach (var arm in arms) {
        uint iid = Data.GeneralInfo.LastObj;
        Data.GeneralInfo.LastObj = iid + 1;
        var inst = new UndertaleRoom.GameObject();
        inst.InstanceID = iid;
        inst.X = 350; inst.Y = 260;
        inst.ObjectDefinition = cactus;
        room.GameObjects.Add(inst);
        blocks.Append("if (id == " + iid + " && !instance_exists(obj_dialoguer) && !instance_exists(OBJ_WRITER) && !instance_exists(obj_choicer))\n{\n");
        blocks.Append("    if (distance_to_object(obj_mainchara) < 99999)\n    {\n");
        blocks.Append("        global.msc = 0;\n        global.typer = 5;\n");
        blocks.Append("        global.facechoice = " + arm.fc + ";\n        global.faceemotion = " + arm.fe + ";\n");
        blocks.Append("        " + arm.msg + "\n");
        blocks.Append("        global.msg[1] = \"%%%\";\n");
        blocks.Append("        instance_create(0, 0, obj_dialoguer);\n    }\n}\n");
        ScriptMessage("B1L_ARM id=" + iid + " tag=" + arm.tag);
    }
    tgml = tgml + "\n" + blocks.ToString();
    var ig = new CodeImportGroup(Data) { MainThreadAction = MainThreadAction };
    ig.QueueReplace(stepCode, tgml);
    ig.Import();
    ScriptMessage("B1L_OK");
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.GetType().Name + ": " + ex.Message);
}
