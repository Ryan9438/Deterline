// B4 谱系修正步骤（当时只在 /tmp，现补档）：把 B3 旧 E-KANA(113928) 挪出可达区，
// 隔离 B4-MAIN(113933)@(220,330)（二者原同位，低 id 先赢会遮蔽）。
// B4 实际 boot 文件 = b3c.ios + b4_inject + 本步骤 = b4f.ios（谱系见报告 §九 谱系披露）。
using System;
using System.Linq;
var room = Data.Rooms.First(r => r.Name.Content == "room_ruins1");
var inst = room.GameObjects.FirstOrDefault(g => g.InstanceID == 113928u);
if (inst == null) { ScriptMessage("ERROR: no 113928"); return; }
inst.X = 320; inst.Y = 400;
ScriptMessage("MOVED_EKANA_OUT (320,400)");
