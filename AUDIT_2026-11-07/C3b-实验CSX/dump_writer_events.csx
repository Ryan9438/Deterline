// 离线 dump：obj_base_writer 全事件 + obj_dialoguer 其余事件（查 halt 翻页机制）
using System;
using System.IO;
string outDir = @"/Users/ryan/Desktop/UT 存档修改/Deterline/build/cjk_verify";
string[] targets = new string[] {
    "gml_Object_obj_base_writer_Step_0",
    "gml_Object_obj_base_writer_Step_1",
    "gml_Object_obj_base_writer_Step_2",
    "gml_Object_obj_base_writer_Alarm_0",
    "gml_Object_obj_base_writer_Alarm_1",
    "gml_Object_obj_base_writer_Other_10",
    "gml_Object_obj_base_writer_Other_11",
    "gml_Object_obj_dialoguer_Alarm_0",
    "gml_Object_obj_dialoguer_Step_1",
    "gml_Object_obj_dialoguer_Step_2",
};
foreach (string t in targets) {
    try {
        string s = GetDecompiledText(t);
        File.WriteAllText(Path.Combine(outDir, t + ".txt"), s);
        ScriptMessage("OK " + t + " len=" + s.Length);
    } catch (Exception ex) {
        ScriptMessage("MISS " + t + " (" + ex.Message + ")");
    }
}
