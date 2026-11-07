// B1f：纯四臂注入（二分隔离用——emb20/armn/preload/setfont 全部不碰）
using System;
using System.Linq;
try {
    var room = Data.Rooms.First(r => r.Name.Content == "room_ruins1");
    var cactus = Data.GameObjects.First(o => o.Name.Content == "obj_cactus");
    string stepName = "gml_Object_obj_cactus_Step_1";
    var stepCode = Data.Code.ByName(stepName);
    string tgml = GetDecompiledText(stepName);
    if (tgml.Contains("global.typer = 5;") && tgml.Contains("id == 113930")) {
        ScriptMessage("ERROR: 臂已存在");
        return;
    }
    var canaryChar = "\u9FFF";
    var arms = new[] {
        new { typer = 5, x = 480, y = 400, msg = "* C-ARM 中 文 测 试 " + canaryChar, probe = true },
        new { typer = 0, x = 160, y = 400, msg = "* M-ARM 中 文 测 试", probe = false },
        new { typer = 2, x = 480, y = 240, msg = "* N-ARM abc 123", probe = false },
        new { typer = 3, x = 160, y = 240, msg = "* T3-CTRL abc 123", probe = false },
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
            ? "var _pp = file_text_open_write(\"zcode_lang_probe.txt\");\n            " +
              "file_text_write_string(_pp, \"lang=[\" + global.language + \"] locale=[\" + global.locale + \"]\");\n            " +
              "file_text_close(_pp);\n            "
            : "";
        probeCode += "var _pm = file_text_open_write(\"b1f_arm_" + arm.typer + ".txt\");\n            " +
              "file_text_write_string(_pm, \"fired typer=" + arm.typer + "\");\n            " +
              "file_text_close(_pm);\n            ";
        blocks.Append("if (id == " + iid + " && !instance_exists(obj_dialoguer) && !instance_exists(OBJ_WRITER) && !instance_exists(obj_choicer))\n{\n");
        blocks.Append("    if (distance_to_object(obj_mainchara) < 60)\n    {\n");
        blocks.Append("        global.msc = 0;\n");
        blocks.Append("        global.typer = " + arm.typer + ";\n        " + probeCode);
        blocks.Append("global.msg[0] = \"" + arm.msg + "\";\n");
        blocks.Append("        global.msg[1] = \"%%%\";\n");
        blocks.Append("        instance_create(0, 0, obj_dialoguer);\n    }\n}\n");
        ScriptMessage("B1F_ARM id=" + iid + " typer=" + arm.typer);
    }
    tgml = tgml + "\n" + blocks.ToString();
    var ig = new CodeImportGroup(Data) { MainThreadAction = MainThreadAction };
    ig.QueueReplace(stepCode, tgml);
    ig.Import();
    ScriptMessage("B1F_COMPLETE");
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.GetType().Name + ": " + ex.Message);
}
