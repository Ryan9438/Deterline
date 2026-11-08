// B3b：修正三臂位置（房间仅 320 宽，(320,·)/(480,·) 在墙外/房外——B2 N-ARM 未记录同因）
// 新位：E-KANA→(250,400) B-TBL→(250,240) C-NPG→(70,240)（花坛东/西两侧，避开花体碰撞 x110-210）
using System;
using System.Linq;
try {
    var room = Data.Rooms.First(r => r.Name.Content == "room_ruins1");
    var moves = new[] {
        new { id = 113928u, x = 220, y = 330, name = "E-KANA" },
        new { id = 113929u, x = 235, y = 240, name = "B-TBL" },
        new { id = 113930u, x = 70,  y = 240, name = "C-NPG" },
    };
    foreach (var m in moves) {
        var inst = room.GameObjects.FirstOrDefault(g => g.InstanceID == m.id);
        if (inst == null) { ScriptMessage("ERROR: 缺实例 " + m.id); return; }
        inst.X = m.x; inst.Y = m.y;
        ScriptMessage("MOVED " + m.name + " id=" + m.id + " -> (" + m.x + "," + m.y + ")");
    }
    ScriptMessage("B3B_COMPLETE");
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.GetType().Name + ": " + ex.Message);
}
