"""模板公共层（12 计划 B1/B2，原 3.5）：把"有真实调用方"的解析规则
单点化，并文档化各模板保留的解析策略差异。

解析策略地图（B1 评审包口径，对照 11 §2b）：
- door / pit 的 target_room：`idx_room_lookup`（本模块，两段式 = exact
  `ByName` + `OrdinalIgnoreCase` 子串回退，1:1 平移自 door.py——CSX 字节
  不变，golden 零重录）。
- door / pit / battle 的 cur_room：写入 CSX 内联两段式（不做前置调用——
  抽取会新增 CALL 段，破坏 golden 零重录）。
- npc-dialogue / npc-choice / spawn-obj 的房间落点：`room._spawn_obj_internal`
  （两段式房 + 两段式对象 + 双向子串建议）——本就是共享函数，不重复抽取。
- npc 对象解析：`npc._query_npc_target`（exact → ignoreCase → 子串回退 +
  父链回溯）——npc 专属语义，不并入通用层。
- verify.py 的房间解析：`utmt._room_id_by_name`（**exact-only**，报错带
  "smoke-test: " 前缀）——文案修正属单独决策，B2 不动。

battle 的前置 `ensure_room`：**延后**（B1 建议默认）——battle 是全命令
capture，前置查询 = 新增 CALL 段，不能声称 golden 零重录；要进时单独交
两枚 golden 的预期 diff（11 §2b 收尾席复核口径）。
"""

import sys

from .. import errors, utmt


def idx_room_lookup(game_file, room_name: str) -> int:
    """两段式房间序号预查：exact `ByName`，未中则大小写不敏感子串回退
    （首个命中胜出）。返回序号；不存在返回 -1（由调用方语义化拒绝）。
    CSX 1:1 平移自 door.py（golden 字节零变化）。"""
    esc_target = utmt._csx_escape(room_name)
    idx_csx = f'''
var r = Data.Rooms.ByName("{esc_target}");
if (r == null) {{
    for (int i = 0; i < Data.Rooms.Count; i++) {{
        if (Data.Rooms[i].Name.Content.IndexOf("{esc_target}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            r = Data.Rooms[i];
            break;
        }}
    }}
}}
if (r != null) {{
    ScriptMessage("IDX:" + Data.Rooms.IndexOf(r));
}} else {{
    ScriptMessage("IDX:-1");
}}
'''
    idx_out = utmt._run_utmt(idx_csx, game_file, save=False)
    for line in utmt._parse_msg(idx_out):
        if line.startswith("IDX:"):
            return int(line.split(":")[1])
    return -1


def reject_if(condition: bool, message: str,
              exc: type[Exception] = errors.ValidationError) -> None:
    """语义化拒绝语法糖：条件成立即抛（默认 ValidationError，可传
    NotFoundError 等 DeterlineError 子类）。"""
    if condition:
        raise exc(message)


def warn(msg: str) -> None:
    """模板层 stderr 警告单点（避免各模板裸 print(file=sys.stderr) 漂移）。"""
    print(msg, file=sys.stderr)
