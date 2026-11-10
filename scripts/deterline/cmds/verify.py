"""验证域命令（O2 步 9：从 modify_save.py 1:1 平移，方案修订 2 verify 项）。

smoke-test / diff-snapshots / verify-code / md5（_md5_file 在 utmt 脊柱）。
Phase1 新命令域的正式边界。跨模块一律模块属性形式：
utmt./state./dialogue./room./inifile./paths./errors.
"""

import json
import shutil
import sys
import time
from pathlib import Path

from .. import errors, inifile, paths, state, utmt
from . import code, dialogue, npc, room

_DIFF_SNAPSHOT_CSX = """
// O7: 结构签名 dump（只读）——房间摘要 + 代码条目长度 + 计数
ScriptMessage("LASTOBJ:" + Data.GeneralInfo.LastObj);
ScriptMessage("STRGCOUNT:" + Data.Strings.Count);
ScriptMessage("CODECOUNT:" + Data.Code.Count);
ScriptMessage("SPRCOUNT:" + Data.Sprites.Count);
ScriptMessage("TEXCOUNT:" + Data.EmbeddedTextures.Count);
ScriptMessage("VARS:" + Data.Variables.Count);
foreach (var v in Data.Variables)
    if (v.Name != null && (v.Name.Content.IndexOf("deterline", StringComparison.OrdinalIgnoreCase) >= 0))
        ScriptMessage("VARDETERLINE:" + v.Name.Content + ":" + v.NameStringID + ":" + v.Occurrences);
foreach (var room in Data.Rooms) {{
    string bgs = "";
    for (int i = 0; i < room.Backgrounds.Count; i++)
        if (room.Backgrounds[i].Enabled && room.Backgrounds[i].BackgroundDefinition != null)
            bgs += room.Backgrounds[i].BackgroundDefinition.Name.Content + ",";
    ScriptMessage("ROOM|" + room.Name.Content + "|" + room.Width + "x" + room.Height
        + "|inst=" + room.GameObjects.Count + "|tiles=" + room.Tiles.Count
        + "|bg=" + bgs);
}}
foreach (var c in Data.Code)
    ScriptMessage("CODE|" + c.Name.Content + "|" + c.Instructions.Count);
"""


def cmd_smoke_test(game_file: Path, save_dir: Path, room_name: str = "room_torielroom",
                   obj_name: str = "obj_cactus", x: int = 160, y: int = 150,
                   timeout: int = 120, send_keys: str = "external") -> None:
    """W3：游戏内冒烟测试（半自动，≈90 秒/次，验证级别 in-game）。

    流程：备份三件 → 注入"扁平触发块 + 标记文件写入"到 obj 的 Step 事件 →
    写 file0 Room 传送到目标房 → 提交真实文件（本命令是唯一内建 --commit 流）
    → steam://run 启动 → 轮询存档目录的 zcode_smoke_marker.txt（可选盲发 Z）
    → 断言 → pkill 游戏 → 全量恢复（MD5 校验）。

    标记由游戏内 file_text_open_write 写出（探针已证实函数存在且写往存档目录）。
    PASS = 触发块在游戏内真实执行过。这是第五层验证（游戏内）的自动化。
    FAIL 时退出码 1；成功自动清理备份，失败保留供取证。

    ⚠️ 环境敏感性：external 按键模式下，若游戏停在开场/菜单等 Z 或窗口失焦，
    无人值守可能假阴性 FAIL（12:13 PASS / 12:56 FAIL 实例）——无人值守推荐
    `--keys osascript`（需辅助功能权限），或人工按键配合 `--timeout` 放宽。
    """
    import time as _time
    import subprocess as _sp

    ts = _time.strftime("%Y%m%d_%H%M%S")
    marker_name = "zcode_smoke_marker.txt"
    marker = save_dir / marker_name
    game_exe_running = lambda: _sp.run(["pgrep", "-x", "Mac_Runner"],
                                       capture_output=True).returncode == 0
    if game_exe_running():
        raise errors.ValidationError("检测到 Undertale 正在运行——smoke-test 需要游戏处于关闭状态（请先退出游戏）")
    # 记录运行前已存在的 .bak.*（运行后新增的属于本次、成功后清理，防 ≈250MB/次 堆盘）
    pre_baks = set(p.name for p in game_file.parent.glob("game.ios.bak.*"))

    text_key = f"smoke_test_{ts}"
    print(f"--- smoke-test (W3) ts={ts} ---")
    print(f"  房间: {room_name} @ ({x},{y})  对象: {obj_name}")

    # ── 1. 备份三件 ──
    f0 = save_dir / "file0"
    ini = save_dir / "undertale.ini"
    b_game = game_file.with_name(f"game.ios.snap.smoke_{ts}")
    b_f0 = f0.with_name(f"file0.snap.smoke_{ts}")
    b_ini = ini.with_name(f"undertale.ini.snap.smoke_{ts}")
    shutil.copy2(str(game_file), str(b_game))
    if f0.exists():
        shutil.copy2(str(f0), str(b_f0))
    if ini.exists():
        shutil.copy2(str(ini), str(b_ini))
    md5_before = utmt._md5_file(game_file)
    print(f"  备份: {b_game.name} / {b_f0.name} / {b_ini.name}")

    # ── 2. 注入（本命令是内建 commit 流：直写真实文件；任何失败都走 finally 恢复）──
    passed = False
    marker_content = ""
    try:
        state.COMMIT_ACTIVE = True
        dialogue.cmd_textdata_add(game_file, text_key, f"* SMOKE OK {ts}/%%")
        new_id = room._spawn_obj_internal(game_file, room_name, obj_name, x, y, quiet=True)
        if new_id is None:
            raise RuntimeError("smoke-test: 生成实例失败")
        print(f"  实例: [{new_id}]")

        info = npc._query_npc_target(game_file, obj_name)
        if info is None:
            raise RuntimeError(f"smoke-test: 对象未找到 {obj_name}")
        # 触发块 = 已验证扁平形态 + 标记写入（同为块内单层语句）
        block = f"""if (id == {new_id} && !instance_exists(obj_dialoguer) && !instance_exists(OBJ_WRITER) && !instance_exists(obj_choicer))
{{
    if (distance_to_object(obj_mainchara) < 50)
    {{
        global.msc = 0;
        global.typer = 5;
        global.facechoice = 0;
        global.faceemotion = 0;
        global.msg[0] = scr_gettext("{text_key}");
        global.msg[1] = "%%%";
        instance_create(0, 0, obj_dialoguer);
        var smokefile = file_text_open_write("{marker_name}");
        file_text_write_string(smokefile, "SMOKE_OK id={new_id} t=" + string(current_time));
        file_text_close(smokefile);
    }}
}}
"""
        step_code = info["step_code"]
        if step_code:
            code._append_to_code(game_file, step_code, block)
        else:
            code.cmd_create_script(game_file, f"gml_Object_{info['obj']}_Step_0", block)
        if info["native"] and info["alarm_code"]:
            npc._guard_alarm_for_instance(game_file, info["alarm_code"], new_id)

        # ── 3. 传送到目标房（内部名 → 数字 ID；resolve_room 不认内部名）──
        room_id = utmt._room_id_by_name(game_file, room_name)
        inifile.cmd_ini_set(save_dir, "General", "Room", room_id)

        # ── 4. 清理旧标记 + 启动 + 轮询 ──
        marker.unlink(missing_ok=True)
        print(f"  启动游戏 (steam://run/391540)... 轮询标记 ≤{timeout}s（按键模式: {send_keys}）")
        _sp.run(["open", "steam://run/391540"], check=False)
        start = _time.time()
        key_count = 0
        while _time.time() - start < timeout:
            _time.sleep(2)
            if send_keys == "osascript" and key_count < 40:
                _sp.run(["osascript", "-e",
                         'tell application "System Events" to keystroke "z"'],
                        capture_output=True)
                key_count += 1
            if marker.exists():
                passed = True
                try:
                    marker_content = marker.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    marker_content = "(读取失败)"
                break
        if not passed:
            # 多候选探测：file_text_open_write 的落点可能是存档目录或游戏目录
            for cand in (game_file.parent / marker_name,
                         Path.cwd() / marker_name,
                         Path.home() / marker_name):
                if cand.exists():
                    passed = True
                    marker = cand
                    try:
                        marker_content = cand.read_text(encoding="utf-8", errors="replace")
                    except OSError:
                        marker_content = "(读取失败)"
                    print(f"  ℹ️  标记出现在备选位置: {cand}")
                    break
    finally:
        # ── 5. 全量恢复（任何路径：PASS/FAIL/异常 都恢复）──
        state.COMMIT_ACTIVE = False
        _sp.run(["pkill", "-x", "Mac_Runner"], capture_output=True)
        _time.sleep(2)
        shutil.copy2(str(b_game), str(game_file))
        f0_ok = ini_ok = True
        if b_f0.exists():
            shutil.copy2(str(b_f0), str(f0))
            f0_ok = (utmt._md5_file(f0) == utmt._md5_file(b_f0))
        if b_ini.exists():
            shutil.copy2(str(b_ini), str(ini))
            ini_ok = (utmt._md5_file(ini) == utmt._md5_file(b_ini))
        marker.unlink(missing_ok=True)
        md5_after = utmt._md5_file(game_file)
        restored = (md5_after == md5_before and f0_ok and ini_ok)
        print(f"  恢复: game.ios {'✅ MD5 一致' if md5_after == md5_before else '❌ 不一致'}"
              f" | file0 {'✅' if f0_ok else '❌'} | ini {'✅' if ini_ok else '❌'}")
        if restored:
            # 恢复成功 → 清理本轮快照与 .bak 时间戳备份；失败则保留供取证
            b_game.unlink(missing_ok=True)
            b_f0.unlink(missing_ok=True)
            b_ini.unlink(missing_ok=True)
            for p_ in game_file.parent.glob("game.ios.bak.*"):
                if p_.name not in pre_baks:
                    p_.unlink(missing_ok=True)

    elapsed = _time.time() - start if 'start' in dir() else -1
    if passed:
        print(f"\n✅ smoke-test PASS（{elapsed:.0f}s，验证级别: in-game）")
        print(f"   标记内容: {marker_content}")
        print("   触发块在游戏内真实执行（标记文件由游戏写出）")
    else:
        print(f"\n❌ smoke-test FAIL（{elapsed:.0f}s 内未出现标记）")
        print("   排查: 1) 游戏是否停在开场/菜单等 Z（external 模式无人按键——无人值守建议 --keys osascript）")
        print("         2) 游戏窗口是否失焦（失焦时 Undertale 会暂停）")
        print("         3) 玩家出生点与 NPC 距离 >50px?")
        print("   （环境已恢复原状，可重跑）")
    return passed


def _dump_structure_signature(game_file: Path) -> dict:
    """单次只读 UTMT 遍历，输出结构签名（供快照 diff）。"""
    out = utmt._run_utmt(_DIFF_SNAPSHOT_CSX, game_file, save=False)
    sig = {"rooms": {}, "code": {}, "counts": {}, "vardeterline": []}
    for line in utmt._parse_msg(out):
        if line.startswith("ROOM|"):
            _, name, size, inst, tiles, bg = line.split("|", 5)
            sig["rooms"][name] = (size, inst, tiles, bg)
        elif line.startswith("CODE|"):
            _, name, n = line.split("|", 2)
            sig["code"][name] = int(n)
        elif line.startswith(("LASTOBJ:", "STRGCOUNT:", "CODECOUNT:", "SPRCOUNT:", "TEXCOUNT:", "VARS:")):
            k, v = line.split(":", 1)
            sig["counts"][k] = int(v)
        elif line.startswith("VARDETERLINE:"):
            sig["vardeterline"].append(line[len("VARDETERLINE:"):])
    return sig


def cmd_diff_snapshots(file_a: Path, file_b: Path) -> None:
    """O7 snapshot-diff：两份 game.ios 的结构化差异报告（实验隔离/泄漏取证）。

    对比维度：LastObj、各房间（尺寸/实例数/Tile 数/启用背景层）、代码条目
    （增删/指令数变化）、字符串/精灵/纹理/变量计数、deterline* 变量。
    只读，两次 UTMT 遍历。
    """
    for f in (file_a, file_b):
        if not f.exists():
            raise errors.NotFoundError(f"文件不存在: {f}")
    print(f"--- diff-snapshots ---\n  A={file_a}\n  B={file_b}")
    a = _dump_structure_signature(file_a)
    b = _dump_structure_signature(file_b)
    diffs = 0

    for k in sorted(set(a["counts"]) | set(b["counts"])):
        va, vb = a["counts"].get(k), b["counts"].get(k)
        if va != vb:
            print(f"  COUNT {k}: {va} → {vb}")
            diffs += 1
    if a["vardeterline"] != b["vardeterline"]:
        print(f"  VARDETERLINE: {a['vardeterline']} → {b['vardeterline']}")
        diffs += 1

    rooms_a, rooms_b = a["rooms"], b["rooms"]
    for name in sorted(set(rooms_a) - set(rooms_b)):
        print(f"  ROOM 移除: {name}"); diffs += 1
    for name in sorted(set(rooms_b) - set(rooms_a)):
        print(f"  ROOM 新增: {name}"); diffs += 1
    for name in sorted(set(rooms_a) & set(rooms_b)):
        if rooms_a[name] != rooms_b[name]:
            print(f"  ROOM 变化: {name}: {rooms_a[name]} → {rooms_b[name]}")
            diffs += 1

    code_a, code_b = a["code"], b["code"]
    for name in sorted(set(code_a) - set(code_b)):
        print(f"  CODE 移除: {name}"); diffs += 1
    for name in sorted(set(code_b) - set(code_a)):
        print(f"  CODE 新增: {name} (instr={code_b[name]})"); diffs += 1
    for name in sorted(set(code_a) & set(code_b)):
        if code_a[name] != code_b[name]:
            print(f"  CODE 变化: {name}: instr {code_a[name]} → {code_b[name]}")
            diffs += 1

    if diffs == 0:
        print("✅ 结构完全一致（0 差异）")
    else:
        print(f"\n⚠️ 共 {diffs} 处结构差异")
    return diffs


def cmd_verify_code(game_file: Path, code_name: str, show_asm: bool = False) -> bool:
    """V1（收窄版）：对指定代码条目做字节级体检并输出结构化指纹。

    产出（Agent 可读）：
      FINGERPRINT: name=... instr=N branches=B push=P pop=P call=C exit=E
      VARREF: WRITE <var> ×k / READ <var> ×k        （从反汇编文本解析）
      ROUNDTRIP: instr N -> N2 text_identical=true/false
      ASM_DIFF: lines=k first=[...]                  （仅往返不一致时）
      OK: roundtrip stable / WARN: 往返不稳定...

    语义：roundtrip 不一致说明"反编译→重编译"在该条目上不稳定（域F 死代码
    事故的怀疑层），此时返回 False（CLI 退出码 1）；VARREF 写分布是活/死语料
    比对的原料（W3 提供标签）。完整反汇编文本用 --asm 查看。全程只读
    （内存内 Import，不落盘）。
    """
    esc = utmt._csx_escape(code_name)
    csx = f"""
string name = "{esc}";
var code = Data.Code.ByName(name);
if (code == null) {{
    ScriptMessage("ERROR: code not found: " + name);
    return;
}}
name = code.Name.Content;
var locals = Data.CodeLocals.ByName(name);
if (locals == null) locals = new UndertaleCodeLocals();
string asm1 = code.Disassemble(Data.Variables, locals, true);

int branches = 0, push = 0, pop = 0, call = 0, exitI = 0;
foreach (var instr in code.Instructions) {{
    if (instr.Kind == UndertaleInstruction.Opcode.B || instr.Kind == UndertaleInstruction.Opcode.Bt
        || instr.Kind == UndertaleInstruction.Opcode.Bf) branches++;
    else if (instr.Kind == UndertaleInstruction.Opcode.Pop) pop++;
    else if (instr.Kind == UndertaleInstruction.Opcode.Call) call++;
    else if (instr.Kind == UndertaleInstruction.Opcode.Exit || instr.Kind == UndertaleInstruction.Opcode.Ret) exitI++;
    else if (instr.Kind == UndertaleInstruction.Opcode.Push || instr.Kind == UndertaleInstruction.Opcode.PushI
        || instr.Kind == UndertaleInstruction.Opcode.PushLoc || instr.Kind == UndertaleInstruction.Opcode.PushGlb
        || instr.Kind == UndertaleInstruction.Opcode.PushBltn) push++;
}}
ScriptMessage("FINGERPRINT: name=" + name + " instr=" + code.Instructions.Count
    + " branches=" + branches + " push=" + push + " pop=" + pop + " call=" + call + " exit=" + exitI);
foreach (var line in asm1.Split(new[] {{ "\\r\\n", "\\r", "\\n" }}, System.StringSplitOptions.None)) {{
    string t = line.Trim();
    if (t.Length > 0) ScriptMessage("ASM| " + t);
}}

// 内存内往返：反编译 → 重编译 → 反汇编，比对稳定性
string gml = GetDecompiledText(code);
int n1 = code.Instructions.Count;
var grp = new CodeImportGroup(Data) {{ MainThreadAction = MainThreadAction }};
grp.QueueReplace(code, gml);
grp.Import();
var code2 = Data.Code.ByName(name);
var locals2 = Data.CodeLocals.ByName(name) ?? locals;
string asm2 = code2.Disassemble(Data.Variables, locals2, true);
int n2 = code2.Instructions.Count;
bool identical = (asm1 == asm2);
ScriptMessage("ROUNDTRIP: instr " + n1 + " -> " + n2 + " text_identical=" + (identical ? "true" : "false"));
if (!identical) {{
    string[] l1 = asm1.Split(new[] {{ "\\r\\n", "\\r", "\\n" }}, System.StringSplitOptions.None);
    string[] l2 = asm2.Split(new[] {{ "\\r\\n", "\\r", "\\n" }}, System.StringSplitOptions.None);
    int diffLines = 0; string first = "";
    for (int i = 0; i < System.Math.Max(l1.Length, l2.Length); i++) {{
        string a = i < l1.Length ? l1[i].Trim() : "<eof>";
        string b = i < l2.Length ? l2[i].Trim() : "<eof>";
        if (a != b) {{ diffLines++; if (diffLines == 1) first = a + "  =>  " + b; }}
    }}
    ScriptMessage("ASM_DIFF: lines=" + diffLines + " first=[" + first + "]");
    ScriptMessage("WARN: 往返不稳定——该条目的反编译/重编译不可信（对照 AUDIT_2026-11-07 域F）");
}} else {{
    ScriptMessage("OK: roundtrip stable");
}}
"""
    out = utmt._run_utmt(csx, game_file, save=False)
    # Python 侧解析：FINGERPRINT/ROUNDTRIP 直通；ASM 行聚合为变量读写普查
    stable = None
    import collections
    writes = collections.Counter()
    reads = collections.Counter()
    for line in utmt._parse_msg(out):
        if line.startswith("ASM| "):
            t = line[5:].strip()
            if show_asm:
                print(line)
            parts = t.split()
            if t.startswith("pop.") and len(parts) >= 2:
                var = parts[-1].split(".", 1)[-1]  # 去掉 self./global. 前缀
                writes[var] += 1
            elif t.startswith("push") and len(parts) >= 2 and "." in parts[-1]:
                var = parts[-1].split(".", 1)[-1]
                # 过滤噪声：数字字面量与字符串常量尾巴（如 ogg"@2615）
                if ('"' not in var and "@" not in var
                        and var.lstrip("-").replace(".", "").isdigit() is False):
                    reads[var] += 1
        elif line.startswith(("FINGERPRINT:", "VARREF:", "ASM_DIFF:", "ERROR:")):
            print(line)
        elif line.startswith("ROUNDTRIP:"):
            print(line)
            stable = "text_identical=true" in line
        elif line.startswith("WARN:"):
            print(line)
        elif line.startswith("OK:"):
            print(line)
    for var, n in sorted(writes.items()):
        print(f"VARREF: WRITE {var} x{n}")
    for var, n in sorted(reads.items()):
        print(f"VARREF: READ {var} x{n}")
    if writes or reads:
        print(f"VERIFY_CODE_SUMMARY: writes={sum(writes.values())} reads={sum(reads.values())}")
    return stable is not False
