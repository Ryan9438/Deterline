"""NPC 对话触发域命令（O2 步 8：从 modify_save.py 1:1 平移，方案 §1.2 npc 项）。

npc 家族（dialogue/choice/guard-alarm）+ 构造器 + verify-nsid/verify-instances
（方案归 npc 域）+ 共享助手。跨模块一律模块属性形式：
utmt./code./dialogue./room./file0./rooms_data./paths./errors.
（cmds 域间引用 = 方案明文允许的显式模块属性形态）。
"""

import sys
from pathlib import Path

from .. import errors, file0, paths, rooms_data, utmt
from . import code, dialogue, room

def _query_npc_target(game_file: Path, obj_name: str) -> dict | None:
    """Query object inheritance (native interactable?) + its own Step/Alarm code entries.

    Returns {"obj", "native", "step_code", "alarm_code"} or None if not found.
    native=True means the object inherits obj_readablesolid/obj_interactable
    (has a native Z-key/touch interaction system that conflicts with myinteract triggers).
    """
    esc = utmt._csx_escape(obj_name)
    csx = f'''
var obj = Data.GameObjects.ByName("{esc}");
if (obj == null) {{ obj = Data.GameObjects.ByName("{esc}", true); }}
if (obj == null) {{
    string q = "{esc}";
    int first = -1;
    int count = 0;
    for (int o = 0; o < Data.GameObjects.Count; o++) {{
        string on = Data.GameObjects[o].Name.Content;
        if (on.IndexOf(q, StringComparison.OrdinalIgnoreCase) >= 0) {{
            if (first < 0) first = o;
            count++;
        }}
    }}
    if (first >= 0) {{
        obj = Data.GameObjects[first];
        ScriptMessage("NPC_TARGET:MATCH:" + obj.Name.Content + ":" + count);
    }}
}}
if (obj == null) {{
    ScriptMessage("NPC_TARGET:NOT_FOUND");
    return;
}}
bool native = false;
var cur = obj;
int guard = 0;
while (cur != null && guard < 30) {{
    string cn = cur.Name?.Content ?? "";
    if (cn == "obj_interactable" || cn == "obj_readablesolid") {{
        native = true;
        break;
    }}
    cur = cur.ParentId;
    guard++;
}}
string oname = obj.Name.Content;
string stepCode = "";
string[] stepNames = new string[] {{
    "gml_Object_" + oname + "_Step_1",
    "gml_Object_" + oname + "_Step_0",
    "gml_Object_" + oname + "_Step_2"
}};
foreach (string sn in stepNames) {{
    if (Data.Code.ByName(sn) != null) {{
        stepCode = sn;
        break;
    }}
}}
string alarmCode = "";
var acur = obj;
guard = 0;
while (acur != null && guard < 30) {{
    string cand = "gml_Object_" + acur.Name.Content + "_Alarm_0";
    if (Data.Code.ByName(cand) != null) {{
        alarmCode = cand;
        break;
    }}
    acur = acur.ParentId;
    guard++;
}}
ScriptMessage("NPC_TARGET:RESULT:" + oname + ":" + (native ? "1" : "0") + ":" + stepCode + ":" + alarmCode);
'''
    out = utmt._run_utmt(csx, game_file, save=False)
    for line in utmt._parse_msg(out):
        if line.startswith("NPC_TARGET:RESULT:"):
            body = line[len("NPC_TARGET:RESULT:"):]
            parts = body.split(":")
            if len(parts) >= 4:
                return {
                    "obj": parts[0],
                    "native": parts[1] == "1",
                    "step_code": parts[2],
                    "alarm_code": ":".join(parts[3:]),
                }
        if line.startswith("NPC_TARGET:NOT_FOUND"):
            return None
    return None


def _build_npc_step_block(instance_id: int, text_key: str, face: int, emotion: int,
                          native: bool, once: bool = False, range_: int = 50) -> str:
    """Build distance-trigger GML for a spawned NPC instance.

    ⚠️⚠️ 形态约束（2026-11-07 游戏内实测 15 次启动实验矩阵，见 AUDIT_2026-11-07/域F）：
    本环境（UndertaleModCli 0.9.1.2 + Undertale Mac Runner）对附加/替换代码块存在
    未定位的字节级问题——触发 create 一旦被"状态条件"门控就静默失效，无论：
      - 状态存哪（新实例变量 deterline_state / global.flag[510] / 内建变量 friction）
      - 条件在哪一层（外层链 / 嵌套内层）
      - 写入在 create 之前还是之后
    而"纯扁平块"（id 守卫 + !instance_exists 三件套 + 嵌套距离判断，块内无任何
    状态读写）经多次启动稳定工作。因此本生成器只生成已验证形态：

      if (id == N && !exists×3) { if (dist < range) { <建对话框> } }

    once=True  → 触发后在同一块内 instance_destroy() 自毁（对话框是独立实例不受影响），
                 实现"只说一次"；NPC 说完即从房间消失（工具会打印此行为说明）。
    once=False → 可重复触发：关闭对话后若仍在范围内会再次弹出（走出范围即停止）；
                 ⚠️ 不设置 global.interact=1——无状态机时无处复位，会把玩家软锁。

    `native` 只影响 Alarm_0 守卫（调用方处理），与本块无关。
    """
    once_line = "\n            instance_destroy();" if once else ""
    return f'''if (id == {instance_id} && !instance_exists(obj_dialoguer) && !instance_exists(OBJ_WRITER) && !instance_exists(obj_choicer))
{{
    if (distance_to_object(obj_mainchara) < {range_})
    {{
        global.msc = 0;
        global.typer = 5;
        global.facechoice = {face};
        global.faceemotion = {emotion};
        global.msg[0] = scr_gettext("{text_key}");
        global.msg[1] = "%%%";
        instance_create(0, 0, obj_dialoguer);{once_line}
    }}
}}
'''


def _build_npc_choice_block(instance_id: int, choice_key: str, yes_key: str | None,
                            no_key: str, face: int, emotion: int, range_: int = 50,
                            goto_room: str | None = None, item_id: int | None = None,
                            repeat: bool = False) -> str:
    """Build a distance-trigger GML block for a YES/NO choice NPC.

    ⚠️⚠️ 形态约束同 _build_npc_step_block（2026-11-07 游戏内实测 15 次启动）：只生成
    已验证的扁平形态，块内禁止任何状态读写；分支体保持单层平铺语句。

    - trigger: player within range_ px → show the `\\C` choice text
    - YES (global.choice == 0): replace msg[0] with yes text (no \\C); optionally
      give an item (scr_itemget) and/or teleport (room_goto)
    - NO (global.choice == 1): replace msg[0] with no text (no \\C)
    - CRITICAL: branch texts MUST replace global.msg[0] with a non-\\C text —
      otherwise obj_choicer's alarm (2 frames later) re-copies the `\\C` text via
      scr_msgup and the choice box pops up again in a loop.
    - 单次语义（默认）通过"答完后 instance_destroy() 自毁"实现（触发块不再被状态门控）；
      repeat=True 时 NPC 存活，走开再靠近可再次提问。
    - ⚠️ 已知限制（2026-11 复核）：选择处理分支按 global.choice 响应、无法区分同房间的
      多个选择 NPC——同一房间放多个 obj 选择 NPC 时，回答会串（窄场景；不同对象/不同
      房间不受影响）。
    """
    yes_lines = ""
    if yes_key:
        yes_lines += f'''        global.typer = 5;
        global.facechoice = {face};
        global.faceemotion = {emotion};
        global.msg[0] = scr_gettext("{yes_key}");
        global.msg[1] = "%%%";
'''
    if item_id is not None:
        yes_lines += f"        script_execute(scr_itemget, {item_id});\n"
    if goto_room:
        yes_lines += f"        room_goto({goto_room});\n"
    if not repeat:
        yes_lines += "        instance_destroy();\n"

    no_destroy = "        instance_destroy();\n" if not repeat else ""
    return f'''if (id == {instance_id} && !instance_exists(obj_dialoguer) && !instance_exists(OBJ_WRITER) && !instance_exists(obj_choicer))
{{
    if (distance_to_object(obj_mainchara) < {range_})
    {{
        global.msc = 0;
        global.typer = 5;
        global.facechoice = {face};
        global.faceemotion = {emotion};
        global.msg[0] = scr_gettext("{choice_key}");
        global.msg[1] = "%%%";
        instance_create(0, 0, obj_dialoguer);
    }}
}}
if (id == {instance_id} && global.choice != -1)
{{
    if (global.choice == 0)
    {{
        global.choice = -1;
        global.msc = -1;
{yes_lines}    }}
    else
    {{
        global.choice = -1;
        global.msc = -1;
        global.typer = 5;
        global.facechoice = {face};
        global.faceemotion = {emotion};
        global.msg[0] = scr_gettext("{no_key}");
        global.msg[1] = "%%%";
{no_destroy}    }}
}}
'''


def _guard_alarm_for_instance(game_file: Path, alarm_code: str, instance_id: int) -> bool:
    """Prepend `if (id == N) exit;` to an Alarm_0 entry (idempotent). Returns True if added."""
    esc = utmt._csx_escape(alarm_code)
    guard = f"if (id == {instance_id})\n{{\n    exit;\n}}"
    verb = utmt._csx_verbatim_escape(guard)
    # Single round trip: decompile → check idempotency → prepend guard.
    csx = f'''
var code = Data.Code.ByName("{esc}");
if (code == null) {{
    ScriptMessage("ERROR: Code entry not found: {esc}");
    return;
}}
try {{
    string existingGml = GetDecompiledText(code);
    if (existingGml.IndexOf("id == {instance_id}") >= 0) {{
        ScriptMessage("SKIP: guard already present");
        return;
    }}
    string newGml = @"{verb}" + "\\n" + existingGml;
    CodeImportGroup importGroup = new(Data)
    {{
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueueReplace(code, newGml);
    importGroup.Import();
    ScriptMessage("OK: guarded");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    out = utmt._run_utmt(csx, game_file, save=True)
    for line in utmt._parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
            return False
        elif line.startswith("SKIP:"):
            print(f"  ⏭️  守卫已存在: {alarm_code} (id == {instance_id})")
            return False
        elif line.startswith("OK:"):
            print(f"  ✅ 已守卫 Alarm_0: {alarm_code}")
            return True
    return False


def _find_create_code(game_file: Path, obj_name: str) -> str | None:
    """Find the effective Create event code entry for an object (self or parent chain).

    Walks the parent chain like _query_npc_target does for Step/Alarm, so a child
    object without its own Create event still maps to the inherited one.
    """
    esc = utmt._csx_escape(obj_name)
    csx = f'''
var obj = Data.GameObjects.ByName("{esc}");
if (obj == null) {{
    for (int o = 0; o < Data.GameObjects.Count; o++) {{
        if (Data.GameObjects[o].Name.Content.IndexOf("{esc}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            obj = Data.GameObjects[o];
            break;
        }}
    }}
}}
if (obj == null) {{
    ScriptMessage("FIND_CREATE:NOT_FOUND");
    return;
}}
string found = "";
var cur = obj;
int guard = 0;
while (cur != null && guard < 30) {{
    string cand = "gml_Object_" + cur.Name.Content + "_Create_0";
    if (Data.Code.ByName(cand) != null) {{
        found = cand;
        break;
    }}
    cur = cur.ParentId;
    guard++;
}}
ScriptMessage("FIND_CREATE:" + (found.Length > 0 ? found : "NONE"));
'''
    out = utmt._run_utmt(csx, game_file, save=False)
    for line in utmt._parse_msg(out):
        if line.startswith("FIND_CREATE:"):
            val = line[len("FIND_CREATE:"):]
            return None if val == "NONE" else val
    return None


def _ensure_var_initialized(game_file: Path, obj_name: str, var_name: str) -> bool:
    """Ensure a per-instance variable is initialized (registered) for an object.

    Root cause of the NSID=0 crash: a new instance variable that is only referenced
    in one code entry gets Occurrences=0 (→ NameStringID=0) if that entry is ever
    overwritten without the variable. Initializing it in Create_0 keeps it referenced
    forever, so its NameStringID stays valid.

    Idempotent: skips if the var is already referenced in the effective Create_0.
    Returns True if the variable is (or already was) initialized.
    """
    create_code = _find_create_code(game_file, obj_name)
    esc_var = utmt._csx_escape(var_name)
    verb_var = utmt._csx_verbatim_escape(var_name)

    if create_code is None:
        # No Create event anywhere → create one with the init line (AutoCreateAssets links the event).
        esc_obj = utmt._csx_escape(obj_name)
        create_name = f"gml_Object_{obj_name}_Create_0"
        esc_name = utmt._csx_escape(create_name)
        init = f"{var_name} = 0;"
        verb = utmt._csx_verbatim_escape(init)
        csx = f'''
var obj = Data.GameObjects.ByName("{esc_obj}");
if (obj == null) {{
    for (int o = 0; o < Data.GameObjects.Count; o++) {{
        if (Data.GameObjects[o].Name.Content.IndexOf("{esc_obj}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            obj = Data.GameObjects[o];
            break;
        }}
    }}
}}
if (obj == null) {{
    ScriptMessage("ERROR: Object not found: {esc_obj}");
    return;
}}
try {{
    CodeImportGroup importGroup = new(Data)
    {{
        AutoCreateAssets = true,
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueueReplace("{esc_name}", @"{verb}");
    importGroup.Import();
    ScriptMessage("OK: Created " + "{create_name}" + " with `{var_name} = 0;`");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
        out = utmt._run_utmt(csx, game_file, save=True)
        ok = any(line.startswith("OK:") for line in utmt._parse_msg(out))
        if ok:
            print(f"  ✅ 已创建 Create 事件并初始化变量 {var_name} ({create_name})")
        return ok

    # Check existing Create_0: does it already reference var_name? (idempotency)
    lines = code._decompile_to_lines(game_file, create_code)
    if lines is not None and any(var_name in ln for ln in lines):
        print(f"  ⏭️  变量 {var_name} 已在 {create_code} 初始化")
        return True

    # Prepend the init line to the effective Create_0.
    esc_name = utmt._csx_escape(create_code)
    init = f"{var_name} = 0;"
    verb = utmt._csx_verbatim_escape(init)
    csx = f'''
var code = Data.Code.ByName("{esc_name}");
if (code == null) {{
    ScriptMessage("ERROR: Code entry not found: {esc_name}");
    return;
}}
try {{
    string existingGml = GetDecompiledText(code);
    string newGml = @"{verb}" + "\\n" + existingGml;
    CodeImportGroup importGroup = new(Data)
    {{
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueueReplace(code, newGml);
    importGroup.Import();
    ScriptMessage("OK: Prepended `{var_name} = 0;` to {esc_name}");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    out = utmt._run_utmt(csx, game_file, save=True)
    ok = any(line.startswith("OK:") for line in utmt._parse_msg(out))
    if ok:
        print(f"  ✅ 已在 {create_code} 初始化变量 {var_name}")
    return ok


def _parse_instance_audit(output: str) -> dict:
    """Parse VERIFY_INSTANCES / BAD_INSTANCE / WARN_INSTANCES output into a dict.

    Keys: bad (int|None), zero, dup, null, nonexist, fixed, bad_lines (list).
    """
    result: dict = {"bad": None, "zero": 0, "dup": 0, "null": 0, "nonexist": 0,
                    "fixed": 0, "bad_lines": []}
    for line in utmt._parse_msg(output):
        if line.startswith("BAD_INSTANCE:"):
            result["bad_lines"].append(line[len("BAD_INSTANCE:"):])
        elif line.startswith("VERIFY_INSTANCES:"):
            body = line[len("VERIFY_INSTANCES:"):]
            parts = dict(p.split("=") for p in body.split() if "=" in p)
            result["bad"] = int(parts.get("bad", 0))
            result["zero"] = int(parts.get("zero", 0))
            result["dup"] = int(parts.get("dup", 0))
            result["null"] = int(parts.get("null", 0))
            result["nonexist"] = int(parts.get("nonexist", 0))
            result["fixed"] = int(parts.get("fixed", 0))
        elif line.startswith("WARN_INSTANCES:"):
            result["warn"] = line[len("WARN_INSTANCES:"):]
    return result


def cmd_verify_nsid(game_file: Path, fix: bool = False) -> None:
    """Check for variables with corrupted NameStringID (0 while referenced).

    Such variables crash the game when read (the NSID=0 trap). By default reports;
    with --fix, resets each broken variable's NameStringID to the correct STRG index.
    """
    csx = f'''
int bad = 0;
int fixedCnt = 0;
for (int i = 0; i < Data.Variables.Count; i++)
{{
    var v = Data.Variables[i];
    string vname = v.Name?.Content ?? "";
    if (vname.Length == 0) continue;
    bool corrupt = v.NameStringID <= 0 && v.Occurrences > 0;
    if (v.NameStringID > 0)
    {{
        // Sanity: NSID must point back to the same name in the STRG table.
        var pointed = (v.NameStringID < Data.Strings.Count) ? (Data.Strings[v.NameStringID]?.Content ?? "") : "";
        if (pointed != vname) corrupt = true;
    }}
    if (corrupt)
    {{
        int correct = Data.Strings.IndexOf(v.Name);
        bad++;
        if ({( "true" if fix else "false" )})
        {{
            v.NameStringID = correct;
            fixedCnt++;
        }}
        ScriptMessage("BAD_NSID: name='" + vname + "' nsid=" + v.NameStringID + " occ=" + v.Occurrences + " correct=" + correct + " fixed=" + ({( "true" if fix else "false" )}));
    }}
}}
ScriptMessage("VERIFY_NSID:bad=" + bad + " fixed=" + fixedCnt);
'''
    out = utmt._run_utmt(csx, game_file, save=fix)
    bad = fixed = None
    for line in utmt._parse_msg(out):
        if line.startswith("BAD_NSID:"):
            print(f"  ⚠️  {line[len('BAD_NSID:'):]}")
        elif line.startswith("VERIFY_NSID:"):
            body = line[len("VERIFY_NSID:"):]
            parts = dict(p.split("=") for p in body.split() if "=" in p)
            bad = int(parts.get("bad", 0))
            fixed = int(parts.get("fixed", 0))
    if bad is None:
        print("错误: 无法解析 verify-nsid 结果", file=sys.stderr)
        return
    if bad == 0:
        print("✅ verify-nsid: 无损坏变量（全部 NameStringID 有效）")
    else:
        if fix:
            print(f"⚠️ verify-nsid: 发现 {bad} 个损坏变量，已修复 {fixed} 个")
        else:
            print(f"⚠️ verify-nsid: 发现 {bad} 个损坏变量（用 --fix 自动修复）")


def cmd_verify_instances(game_file: Path, fix: bool = False) -> None:
    """Check every room for instances with invalid IDs (0 or duplicate).

    Such instances break GameMaker's per-instance variable tables: the Create
    event's writes (e.g. phase, image_xscale) don't land on the colliding
    instance, causing crashes (reading other.<var> unset) and visual leaks
    (unscaled solids).  By default reports; with --fix, reassigns unique IDs
    to ID=0/duplicate instances.  Null-ObjectDefinition / Nonexistent instances
    are reported only (cannot be auto-fixed).
    """
    fix_csx = "true" if fix else "false"
    csx = f'''
// Verify / fix room instance IDs across all rooms (experiment 19)
ulong maxUsed = 0;
var used = new System.Collections.Generic.HashSet<uint>();
foreach (var room in Data.Rooms)
{{
    foreach (var g in room.GameObjects)
    {{
        if (g.InstanceID != 0)
        {{
            used.Add(g.InstanceID);
            if (g.InstanceID > maxUsed) maxUsed = g.InstanceID;
        }}
    }}
}}
uint nextId = (uint)(System.Math.Max((long)Data.GeneralInfo.LastObj, (long)maxUsed) + 1);

int badZero = 0, badDup = 0, badNull = 0, badNonexist = 0, fixedCnt = 0;
var local = new System.Collections.Generic.HashSet<uint>();
foreach (var room in Data.Rooms)
{{
    local.Clear();
    string roomName = room.Name?.Content ?? "(unnamed)";
    foreach (var g in room.GameObjects)
    {{
        string objName = g.ObjectDefinition?.Name?.Content ?? "(null)";
        bool idZero = (g.InstanceID == 0);
        bool idDup = (!idZero && !local.Add(g.InstanceID));
        bool nullObj = (g.ObjectDefinition == null);
        bool nonexist = g.Nonexistent;
        if (idZero) badZero++;
        if (idDup) badDup++;
        if (nullObj) badNull++;
        if (nonexist) badNonexist++;
        if (idZero || idDup || nullObj || nonexist)
        {{
            ScriptMessage("BAD_INSTANCE: room='" + roomName + "' obj=" + objName + " id=" + g.InstanceID + " x=" + g.X + " y=" + g.Y + " zero=" + idZero + " dup=" + idDup + " null=" + nullObj + " nonexist=" + nonexist);
        }}
        if ({( "true" if fix else "false" )} && (idZero || idDup))
        {{
            g.InstanceID = nextId;
            nextId++;
            fixedCnt++;
        }}
    }}
}}
if ({( "true" if fix else "false" )})
{{
    Data.GeneralInfo.LastObj = nextId - 1;
}}
int bad = badZero + badDup + badNull + badNonexist;
ScriptMessage("VERIFY_INSTANCES:bad=" + bad + " zero=" + badZero + " dup=" + badDup + " null=" + badNull + " nonexist=" + badNonexist + " fixed=" + fixedCnt);
'''
    out = utmt._run_utmt(csx, game_file, save=fix)
    info = _parse_instance_audit(out)
    if info["bad"] is None:
        print("错误: 无法解析 verify-instances 结果", file=sys.stderr)
        return
    for line in info["bad_lines"]:
        print(f"  ⚠️  {line}")
    if info["bad"] == 0:
        print("✅ verify-instances: 无异常实例（ID=0/重复/空对象/Nonexistent 均为 0）")
    else:
        fix_txt = f"，已修复 ID 类 {info['fixed']} 个（null/Nonexistent 仅报告，无法自动修）" if fix \
            else "（用 --fix 自动为 ID=0/重复实例分配唯一 ID）"
        print(f"⚠️ verify-instances: 异常 {info['bad']} 个 "
              f"(zero={info['zero']} dup={info['dup']} null={info['null']} "
              f"nonexist={info['nonexist']}){fix_txt}")


def cmd_npc_dialogue(game_file: Path, room_name: str, obj_name: str, x: int, y: int,
                     text_key: str, text: str, face: int = 0, emotion: int = 0,
                     once: bool = False, range_: int = 50) -> None:
    """One-shot safe NPC dialogue setup.

    1. Adds the dialogue to textdata_en
    2. Spawns the object instance
    3. Injects the verified flat distance-trigger block (AUDIT_2026-11-07/域F:
       state-gated trigger shapes are in-game dead code in this UTMT env —
       the generator emits only the flat verified form; no movement lock)
    4. If the object inherits a native interaction system, also guards Alarm_0
       with `if (id == N) exit;` to prevent the default dialogue from overlapping.

    range_ = trigger distance in pixels (default 50).
    """
    print("--- npc-dialogue ---")
    utmt._validate_ascii_text(text, f"对话 '{text_key}'")
    dialogue._validate_facechoice(face)
    if "\\C" in text:
        raise errors.ValidationError(
            f"对话 '{text_key}' 含选择框标记 \\C，但 npc-dialogue 只支持纯文本对话。\n"
            f"请改用 npc-choice 命令生成带 YES/NO 选择的分支对话。"
        )

    print("Step 1/4: 添加对话条目...")
    dialogue.cmd_textdata_add(game_file, text_key, text, face=face, emotion=emotion)

    print("Step 2/4: 检查对象继承链...")
    info = _query_npc_target(game_file, obj_name)
    if info is None:
        raise errors.NotFoundError(f"对象未找到: {obj_name}")
    native = info["native"]
    if once:
        print("  🔒 单次触发模式 → 已验证扁平触发块 + 触发后 NPC 自毁（说完即从房间消失）")
    elif native:
        print(f"  ⚠️  {info['obj']} 继承原生交互系统 → 已验证扁平触发块 + Alarm_0 守卫")
    else:
        print(f"  ✅  {info['obj']} 为普通对象 → 已验证扁平触发块")
    print("  ℹ️  v2.3.0 行为说明：触发后不再锁移动（状态机在当前 UTMT 环境下产生游戏内"
          "死代码，见 AUDIT_2026-11-07/域F）；可重复模式下关闭对话后若仍在范围内会再次弹出，走出范围即停止")

    print("Step 3/4: 生成对象实例...")
    new_id = room._spawn_obj_internal(game_file, room_name, obj_name, x, y, quiet=True)
    if new_id is None:
        raise RuntimeError("生成对象失败（未获取到实例 ID）")
    print(f"  ✅ 已生成实例 [{new_id}]")

    print("Step 4/4: 注入触发代码...")
    _ensure_var_initialized(game_file, info["obj"], "deterline_state")
    block = _build_npc_step_block(new_id, text_key, face, emotion, native, once=once, range_=range_)
    step_code = info["step_code"]
    if step_code:
        code._append_to_code(game_file, step_code, block)
        print(f"  ✅ 已追加到 Step 事件: {step_code}")
    else:
        create_name = f"gml_Object_{info['obj']}_Step_0"
        code.cmd_create_script(game_file, create_name, block)
        print(f"  ✅ 已创建 Step 事件: {create_name}")

    if native and info["alarm_code"]:
        _guard_alarm_for_instance(game_file, info["alarm_code"], new_id)
    if once:
        print(f"  ✅ 完成: {info['obj']} [{new_id}] 靠近 (<{range_}px) 说一次 '{text_key}'（触发后 NPC 自毁消失）")
    else:
        print(f"  ✅ 完成: {info['obj']} [{new_id}] 靠近 (<{range_}px) 说 '{text_key}'（可重复；关对话后仍在范围内会再触发，走出范围停止）")


def cmd_npc_choice(game_file: Path, room_name: str, obj_name: str, x: int, y: int,
                   choice_key: str, choice_text: str,
                   yes_key: str | None = None, yes_text: str | None = None,
                   no_key: str | None = None, no_text: str | None = None,
                   face: int = 0, emotion: int = 0, range_: int = 50,
                   goto_room: str | None = None, item_id: int | None = None,
                   repeat: bool = False) -> None:
    """One-shot safe NPC dialogue with a YES/NO choice (`\\C` box).

    Uses the in-game-verified flat trigger shape (v2.3.0, 2026-11-07 audit):
      1. Adds up to 3 textdata entries (choice / YES follow-up / NO follow-up)
      2. Spawns the object instance
      3. Injects the choice state machine into the object's Step event:
         trigger → `\\C` box → YES branch (optional follow-up text, item, teleport)
         / NO branch (follow-up text). Branch texts replace msg[0] with non-\\C
         text, which is what prevents the choice box from re-popping (scr_msgup
         re-copies global.msg[] 2 frames after the choice).
      4. Guards Alarm_0 for native-readable objects (like npc-dialogue).

    Repeatable by default (dialogue re-opens while in range; walk out of
    `--range` to stop); once=True self-destructs the NPC after triggering.
    repeat=True keeps the NPC (flat block, no state machine — v2.3.0).
    """
    print("--- npc-choice ---")
    # ── validation ──────────────────────────────────────────────
    if "\\C" not in choice_text:
        raise errors.ValidationError(
            f"选择文本 '{choice_key}' 不含 \\C 标记（YES/NO 选择框不会出现）。\n"
            f"格式: \"* 提问& &         Yes         No      \\C \""
        )
    line_count = choice_text.count("&") + 1
    if line_count > 3:
        raise errors.ValidationError(
            f"选择文本 '{choice_key}' 共 {line_count} 行（含选项行），超过 3 行限制，"
            f"选项会溢出对话框。\n格式: \"* 提问& &         Yes         No      \\C \""
        )
    if no_key is None or no_text is None:
        raise errors.ValidationError("--no-text-key 和 --no-text 是必需的（NO 分支的回应文本）")
    if yes_key is None:
        # ⚠️ YES 分支必须替换 msg[0]（否则 scr_msgup 2 帧后重拷 \C 文本 → 选择框无限
        # 重弹；带 --item 时还会无限刷物品）。未提供 yes 文本时自动生成一条确认语。
        yes_key = f"{choice_key}_yes"
        yes_text = "* Okay./%%"
        print(f"  ℹ️  未提供 --yes-text，自动生成 YES 分支确认文本 '{yes_key}'")
    utmt._validate_ascii_text(choice_text, f"选择文本 '{choice_key}'")
    for key, val, label in [(yes_key, yes_text, "YES 分支文本"),
                            (no_key, no_text, "NO 分支文本")]:
        if val is not None:
            utmt._validate_ascii_text(val, f"{label} '{key}'")
            if "\\C" in val:
                raise errors.ValidationError(
                    f"{label} '{key}' 含 \\C 标记——分支文本必须是不含选择框的纯文本，"
                    f"否则选择框会循环重弹。"
                )
    dialogue._validate_facechoice(face)
    if item_id is not None and item_id not in file0.ITEMS:
        print(f"警告: 物品 ID {item_id} 不在已知物品表（{min(file0.ITEMS)}-{max(file0.ITEMS)}），仍将注入 scr_itemget", file=sys.stderr)

    # ── resolve teleport target (room name → ID or constant) ───
    goto_gml = None
    if goto_room:
        goto_gml = rooms_data.resolve_room(goto_room)  # numeric ID string works with room_goto()

    # ── execute ─────────────────────────────────────────────────
    print("Step 1/5: 添加对话条目...")
    dialogue.cmd_textdata_add(game_file, choice_key, choice_text, face=face, emotion=emotion)
    if yes_key and yes_text:
        dialogue.cmd_textdata_add(game_file, yes_key, yes_text, face=face, emotion=emotion)
    if no_key:
        dialogue.cmd_textdata_add(game_file, no_key, no_text, face=face, emotion=emotion)

    print("Step 2/5: 检查对象继承链...")
    info = _query_npc_target(game_file, obj_name)
    if info is None:
        raise errors.NotFoundError(f"对象未找到: {obj_name}")
    native = info["native"]
    if native:
        print(f"  ⚠️  {info['obj']} 继承原生交互系统 → 自动加 Alarm_0 守卫")

    print("Step 3/5: 生成对象实例...")
    new_id = room._spawn_obj_internal(game_file, room_name, obj_name, x, y, quiet=True)
    if new_id is None:
        raise RuntimeError("生成对象失败（未获取到实例 ID）")
    print(f"  ✅ 已生成实例 [{new_id}]")

    print("Step 4/5: 注入选择触发块（已验证扁平形态）...")
    _ensure_var_initialized(game_file, info["obj"], "deterline_state")  # 保留兼容，非触发依赖
    block = _build_npc_choice_block(
        new_id, choice_key, yes_key, no_key, face, emotion,
        range_=range_, goto_room=goto_gml, item_id=item_id, repeat=repeat,
    )
    step_code = info["step_code"]
    if step_code:
        code._append_to_code(game_file, step_code, block)
        print(f"  ✅ 已追加到 Step 事件: {step_code}")
    else:
        create_name = f"gml_Object_{info['obj']}_Step_0"
        code.cmd_create_script(game_file, create_name, block)
        print(f"  ✅ 已创建 Step 事件: {create_name}")

    print("Step 5/5: 守卫原生交互...")
    if native and info["alarm_code"]:
        _guard_alarm_for_instance(game_file, info["alarm_code"], new_id)

    extra = []
    if yes_key and yes_text:
        extra.append(f"YES→'{yes_key}'")
    if item_id is not None:
        extra.append(f"给物品 {file0.ITEMS.get(item_id, item_id)}")
    if goto_room and goto_gml is not None:
        extra.append(f"传送→{rooms_data.format_room(goto_gml)}")
    if not extra:
        extra.append("YES→关闭对话")
    if repeat:
        extra.append("走开可再触发")
    else:
        extra.append("单次触发")
    print(f"  ✅ 完成: {info['obj']} [{new_id}] 靠近 (<{range_}px) 弹 '{choice_key}'（{'，'.join(extra)}）")


def cmd_guard_npc_alarm(game_file: Path, obj_name: str, instance_id: int,
                        text_key: str | None = None) -> None:
    """Fix an existing NPC whose injected myinteract trigger overlaps with the
    native readable dialogue.

    Automates the manual two-step fix:
    1. Prepends `if (id == N) exit;` to the effective Alarm_0 entry (idempotent).
    2. If --text-key is given, rewrites the object's Step trigger to the flag-state
       machine (removing the myinteract conflict).
    """
    print("--- guard-npc-alarm ---")
    info = _query_npc_target(game_file, obj_name)
    if info is None:
        raise errors.NotFoundError(f"对象未找到: {obj_name}")

    if not info["alarm_code"]:
        print("警告: 未找到 Alarm_0 代码条目，无法加守卫", file=sys.stderr)
    else:
        _guard_alarm_for_instance(game_file, info["alarm_code"], instance_id)

    if text_key:
        print(f"→ 改写 Step 触发为 flag 状态机 (实例 {instance_id}, key {text_key})...")
        _ensure_var_initialized(game_file, info["obj"], "deterline_state")
        block = _build_npc_step_block(instance_id, text_key, 0, 0, native=True)
        step_code = info["step_code"]
        if step_code:
            code._replace_step_code(game_file, step_code, instance_id, block)
            print(f"  ✅ 已改写: {step_code}")
        else:
            create_name = f"gml_Object_{info['obj']}_Step_0"
            code.cmd_create_script(game_file, create_name, block)
            print(f"  ✅ 已创建: {create_name}")
    print("  ✅ 完成")
