"""验证域命令（O2 步 9：从 modify_save.py 1:1 平移，方案修订 2 verify 项）。

smoke-test / diff-snapshots / verify-code / md5（_md5_file 在 utmt 脊柱）。
Phase1 新命令域的正式边界。跨模块一律模块属性形式：
utmt./state./dialogue./room./inifile./errors.
"""

import json
import subprocess as _sp
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from .. import errors, inifile, paths, state, transactions, utmt
from . import code, dialogue, npc, room

_DIFF_SNAPSHOT_CSX = """
// O7: 结构签名 dump（只读）——房间摘要 + 代码条目长度 + 计数 + 资源级明细
using System.Security.Cryptography;
using System.Text;
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
string Sha(string s){ return Convert.ToHexString(SHA1.HashData(Encoding.UTF8.GetBytes(s))).ToLowerInvariant(); }
foreach (var s in Data.Strings)
    ScriptMessage("STR|" + Encoding.UTF8.GetByteCount(s.Content ?? "") + "|" + Sha(s.Content ?? ""));
foreach (var room in Data.Rooms)
    foreach (var g in room.GameObjects) {
        ScriptMessage("INST|" + room.Name.Content + "|" + g.InstanceID + "|"
            + (g.ObjectDefinition != null ? g.ObjectDefinition.Name.Content : "?") + "|"
            + g.X.ToString(System.Globalization.CultureInfo.InvariantCulture) + "|"
            + g.Y.ToString(System.Globalization.CultureInfo.InvariantCulture));
    }
foreach (var c in Data.Code) {
    var locals = Data.CodeLocals.ByName(c.Name.Content) ?? new UndertaleCodeLocals();
    ScriptMessage("CODEF|" + c.Name.Content + "|" + c.Instructions.Count + "|"
        + Sha(c.Disassemble(Data.Variables, locals, true)));
}
foreach (var f in Data.Fonts) {
    var sb = new System.Text.StringBuilder();
    foreach (var gl in f.Glyphs) sb.Append(gl.Character).Append(',').Append(gl.SourceX)
        .Append(',').Append(gl.SourceY).Append(',').Append(gl.SourceWidth)
        .Append(',').Append(gl.SourceHeight).Append(';');
    // 字形(=UndertaleTexturePageItem)自带 TexturePage 反引用（属页探针实证），
    // 经 Data.EmbeddedTextures 查索引；字形数为 0 时 tex 记 -1
    int tex = -1;
    if (f.Texture != null) {
        for (int ti = 0; ti < Data.EmbeddedTextures.Count && tex < 0; ti++)
            if (Data.EmbeddedTextures[ti] == f.Texture.TexturePage)
                tex = ti;
    }
    ScriptMessage("FONT|" + (f.Name != null ? f.Name.Content : "?") + "|" + f.Glyphs.Count
        + "|" + tex + "|" + Sha(sb.ToString()));
}
"""


@dataclass(frozen=True)
class SmokeVerdict:
    """W3 三段裁决（阶段 1.1）：started/triggered/restored 分别判定。

    verdict：三段皆 ok → pass(0)；started ok 且 triggered fail 且按键可用
    → fail(1)（真死代码/卡场景）；其余 → unverified(2)（未能验证，可重跑）。
    """
    started: str      # ok / fail / skipped
    triggered: str    # ok / fail / skipped
    restored: str     # ok / fail
    keys_ok: bool = True
    reason: str = ""

    @property
    def verdict(self) -> str:
        if self.started == "ok" and self.triggered == "ok" and self.restored == "ok":
            return "pass"
        if self.restored == "fail":
            return "fail"  # 恢复失败是真失败，不是"未能验证"
        if self.started == "ok" and self.triggered == "fail" and self.keys_ok:
            return "fail"
        return "unverified"

    @property
    def ok(self) -> bool:
        return self.verdict == "pass"


def cmd_smoke_test(game_file: Path, save_dir: Path, room_name: str = "room_torielroom",
                   obj_name: str = "obj_cactus", x: int = 160, y: int = 150,
                   timeout: int = 120, send_keys: str = "external") -> "SmokeVerdict":
    """W3：游戏内冒烟测试（半自动，≈90 秒/次，验证级别 in-game）。

    阶段 1.1 重设计（AUDIT 02/03）：三段裁决模型——
      started   游戏进程在轮询期内真实出现过（pgrep Mac_Runner ≥1 次命中；
                steam://run 的返回码只表示 URL 已递给 Steam，不作数）。
                编辑目标 ≠ Steam 安装路径时拒绝启动（started=skipped，注入+恢复
                照常作演练）；DETERLINE_SMOKE_ALLOW_NONSTEAM=1 显式豁免。
      triggered 本 run 唯一标记文件出现且正文三字段（run/room/inst）与本次
                运行完全一致——文件名与内容双钥，旧标记/伪造正文无法误判；
                标记只认存档目录一个落点（候选目录探测已删除：无内容校验的
                多候选是假 PASS 洞）。
      restored  pkill 后轮询进程真正消失（SIGTERM 回写竞态）再全量恢复，
                game.ios/file0/undertale.ini 三件 MD5 与运行前一致。
    verdict：三段皆 ok → PASS(0)；started ok 而 triggered fail → FAIL(1)
    （真死代码或卡场景）；其余（启动失败/skipped/按键不可用）→ UNVERIFIED(2)
    （未能验证，可重跑）。报告含机器可读行
    SMOKE_RESULT: started=… triggered=… restored=… verdict=… reason=…
    """
    import os as _os

    if state.PREVIEW or state.WORKSPACE or state.SANDBOX_ACTIVE:
        raise errors.ValidationError(
            "smoke-test 内建提交流，不得与 --preview / --workspace / --sandbox 组合"
            "（库级调用亦受此守卫——argparse 层之下的第二道防线）")

    ts = time.strftime("%Y%m%d_%H%M%S")
    run_id = f"{ts}_{_os.getpid()}"
    marker_name = f"zcode_smoke_{run_id}.txt"
    game_exe_running = lambda: _sp.run(["pgrep", "-x", "Mac_Runner"],
                                       capture_output=True).returncode == 0
    if game_exe_running():
        raise errors.ValidationError("检测到 Undertale 正在运行——smoke-test 需要游戏处于关闭状态（请先退出游戏）")
    pre_baks = set(p.name for p in game_file.parent.glob("game.ios.bak.*"))

    text_key = f"smoke_test_{run_id}"
    print(f"--- smoke-test (W3) run={run_id} ---")
    print(f"  房间: {room_name} @ ({x},{y})  对象: {obj_name}")

    # ── 0. 加载路径一致性（阶段 1.1）──
    launch_allowed, launch_reason = _check_launch_path(game_file)
    if not launch_allowed:
        print("  ⚠️ 拒绝启动（注入+恢复作演练）：", launch_reason, sep="\n     ")
        if _os.environ.get("DETERLINE_SMOKE_ALLOW_NONSTEAM") == "1":
            launch_allowed = True
            print("     DETERLINE_SMOKE_ALLOW_NONSTEAM=1 —— 显式豁免，照常启动。")

    # ── 1. 备份三件 ──
    f0 = save_dir / "file0"
    ini = save_dir / "undertale.ini"
    b_game = game_file.with_name(f"game.ios.snap.smoke_{ts}")
    b_f0 = f0.with_name(f"file0.snap.smoke_{ts}")
    b_ini = ini.with_name(f"undertale.ini.snap.smoke_{ts}")
    backups = {b_game: game_file}
    backups.update({snapshot: target for snapshot, target in ((b_f0, f0), (b_ini, ini))
                    if target.is_file()})
    transactions.write_many(backups)
    md5_before = utmt._md5_file(game_file)
    print(f"  备份: {b_game.name} / {b_f0.name} / {b_ini.name}")

    started, triggered, content, keys_ok = "fail", "skipped", "", True
    marker = save_dir / marker_name  # P0-1：finally 引用——审核席 B 动态复现的 NameError
    try:
        # AUTO_SNAPSHOT 一并压制（审核席 A P2-4）：smoke 自带三件显式备份，
        # 全局 --auto-snapshot 会再插一枚 snap.auto_*（约 250MB）且清理面
        # 不覆盖它——每轮净泄漏
        previous_policy = (state.COMMIT_ACTIVE, state.SANDBOX_ACTIVE,
                           state.NO_STEAM_SYNC, state.AUTO_SNAPSHOT)
        state.COMMIT_ACTIVE = True
        state.SANDBOX_ACTIVE = False
        state.NO_STEAM_SYNC = True
        state.AUTO_SNAPSHOT = False
        # ── 2. 注入（内建 commit 流；run_id/inst 写进标记正文）──
        try:
            with utmt.game_edit("smoke-test"):
                dialogue.cmd_textdata_add(game_file, text_key, f"* SMOKE OK {run_id}/%%")
                new_id = room._spawn_obj_internal(game_file, room_name, obj_name, x, y, quiet=True)
                if new_id is None:
                    raise RuntimeError("smoke-test: 生成实例失败")
                print(f"  实例: [{new_id}]")
                info = npc._query_npc_target(game_file, obj_name)
                if info is None:
                    raise RuntimeError(f"smoke-test: 对象未找到 {obj_name}")
                marker_body = (f"SMOKE_OK|run={run_id}|room={room_name}"
                               f"|inst={new_id}")
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
            file_text_write_string(smokefile, "{marker_body}|t=" + string(current_time));
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
            # ── 3. 传送到目标房（内部名 → 数字 ID）──
            room_id = utmt._room_id_by_name(game_file, room_name)
            inifile.cmd_ini_set(save_dir, "General", "Room", room_id)
        finally:
            state.COMMIT_ACTIVE, state.SANDBOX_ACTIVE, state.NO_STEAM_SYNC, \
                state.AUTO_SNAPSHOT = previous_policy

        # ── 4. 清理旧标记（卫生，非判据；只删文件，目录名不炸——审核席 A P3-d）──
        for stale in save_dir.glob("zcode_smoke_*.txt"):
            if stale.is_file():
                stale.unlink(missing_ok=True)
        started, triggered, content, keys_ok, elapsed = _launch_and_poll(
            save_dir, timeout, send_keys, run_id, new_id, marker_name,
            launch_allowed=launch_allowed, game_exe_running=game_exe_running)
    finally:
        # ── 5. 全量恢复（任何路径：PASS/FAIL/异常 都恢复）──
        state.COMMIT_ACTIVE, state.SANDBOX_ACTIVE, state.NO_STEAM_SYNC, \
            state.AUTO_SNAPSHOT = previous_policy
        _sp.run(["pkill", "-x", "Mac_Runner"], capture_output=True)
        for _ in range(8):  # 轮询进程真正消失（SIGTERM 回写竞态，复核席 3）
            time.sleep(1)
            if not game_exe_running():
                break
        transactions.write_many({target: snapshot for snapshot, target in backups.items()},
                                backup=False)
        f0_ok = not b_f0.exists() or utmt._md5_file(f0) == utmt._md5_file(b_f0)
        ini_ok = not b_ini.exists() or utmt._md5_file(ini) == utmt._md5_file(b_ini)
        marker.unlink(missing_ok=True)
        md5_after = utmt._md5_file(game_file)
        restored = (md5_after == md5_before and f0_ok and ini_ok)
        print(f"  恢复: game.ios {'✅ MD5 一致' if md5_after == md5_before else '❌ 不一致'}"
              f" | file0 {'✅' if f0_ok else '❌'} | ini {'✅' if ini_ok else '❌'}")
        if restored:
            b_game.unlink(missing_ok=True)
            b_f0.unlink(missing_ok=True)
            b_ini.unlink(missing_ok=True)
            for p_ in game_file.parent.glob("game.ios.bak.*"):
                if p_.name not in pre_baks:
                    p_.unlink(missing_ok=True)

    if not restored:
        reason = "恢复校验失败——现场未完全还原（快照保留供取证）"
    elif started == "fail":
        reason = "轮询期内未检测到游戏进程（启动失败或秒退）"
    elif started == "skipped":
        reason = "编辑目标非 Steam 安装路径——演练模式（未启动）"
    elif not keys_ok and triggered != "ok":
        reason = "osascript 按键全部失败（辅助功能权限？）"
    elif triggered == "fail":
        reason = "标记未出现或内容不符（未进入可测试场景 / 触发未执行 / 卡场景）"
    else:
        reason = ""
    verdict = SmokeVerdict(started, triggered,
                           "ok" if restored else "fail", keys_ok=keys_ok,
                           reason=reason)
    # elapsed 由 _launch_and_poll 返回（未启动 = 0）
    print(f"\n{'✅' if verdict.verdict == 'pass' else '⚠️' if verdict.verdict == 'unverified' else '❌'}"
          f" smoke-test {verdict.verdict.upper()}（{elapsed:.0f}s，验证级别: "
          f"{'in-game' if verdict.verdict != 'unverified' else '未能验证'}）")
    if triggered == "ok":
        print(f"   标记内容: {content}")
    if verdict.verdict == "unverified":
        print(f"   未能验证原因: {reason}")
    elif verdict.verdict == "fail":
        print("   排查: 1) 游戏是否停在开场/菜单等 Z（external 模式无人按键——无人值守建议 --keys osascript）")
        print("         2) 游戏窗口是否失焦（失焦时 Undertale 会暂停）")
        print("         3) 玩家出生点与 NPC 距离 >50px? 或触发块真死代码（域F 矩阵）")
    print(f"   SMOKE_RESULT: started={verdict.started} triggered={verdict.triggered}"
          f" restored={verdict.restored} verdict={verdict.verdict} reason={reason}")
    return verdict


def _check_launch_path(game_file: Path) -> tuple[bool, str]:
    """编辑目标必须与 Steam 启动器实际加载路径一致（阶段 1.1）。

    smoke-test 经 steam://run 启动——游戏加载的是 Steam 安装副本；编辑目标
    不一致时，注入码永远到不了被启动的游戏（必然假 FAIL）。
    """
    steam_path = paths.steam_game_file()
    allowed = (steam_path is not None
               and game_file.resolve() == steam_path.resolve())
    reason = "" if allowed else (
        f"编辑目标 {game_file} ≠ Steam 启动器加载路径 "
        f"{steam_path or '(本机未找到 Steam 安装)'}")
    return allowed, reason


def _launch_and_poll(save_dir: Path, timeout: int, send_keys: str, run_id: str,
                     new_id: str, marker_name: str, *, launch_allowed: bool,
                     game_exe_running, room_name: str = "") -> tuple[str, str, str, bool, float]:
    """启动 + 轮询唯一标记（文件名+内容双钥）。返回 (started, triggered,
    content, keys_ok, elapsed)。"""
    marker = save_dir / marker_name
    if not launch_allowed:
        print("  注入+恢复演练完成（未启动游戏）。")
        return "skipped", "skipped", "", True, 0.0
    print(f"  启动游戏 (steam://run/391540)... 轮询标记 ≤{timeout}s（按键模式: {send_keys}）")
    _sp.run(["open", "steam://run/391540"], check=False)
    start = time.time()
    saw_game = False
    key_count = 0
    osascript_failures = 0
    osascript_sends = 0
    mismatch = ""
    while time.time() - start < timeout:
        time.sleep(2)
        if not saw_game:
            saw_game = game_exe_running()
        if send_keys == "osascript" and key_count < 40 and saw_game:
            osascript_sends += 1
            proc = _sp.run(["osascript", "-e",
                            'tell application "System Events" to keystroke "z"'],
                           capture_output=True)
            if proc.returncode != 0:
                osascript_failures += 1
            key_count += 1
        if marker.is_file():
            ok, content = _accept_marker(marker, run_id, str(new_id), room_name)
            if ok:
                return ("ok" if saw_game else "fail", "ok", content, True,
                        time.time() - start)
            mismatch = content[:60]
            print(f"  ⚠️ 标记出现但内容不符（{mismatch}…），继续轮询")
    keys_ok = not (send_keys == "osascript" and osascript_sends > 0
                   and osascript_failures == osascript_sends)
    return ("ok" if saw_game else "fail", "fail", mismatch, keys_ok,
            time.time() - start)


def _accept_marker(path: Path, run_id: str, new_id: str,
                   room_name: str = "") -> tuple[bool, str]:
    """读取并校验标记正文（文件名+内容双钥；阶段 1.1）。

    返回 (ok, content)。ok 要求：正文以 SMOKE_OK| 开头，且按 | 切分的
    run/room/inst 三字段与本次运行完全一致（字段级精确比对——子串匹配会
    让 run=…_123 误过 run=…_1234，审核席 A P2-3）。
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"  ⚠️ 标记读取失败: {exc}", file=sys.stderr)
        return False, f"(unreadable: {exc})"
    if not text.startswith("SMOKE_OK|"):
        return False, text
    fields = {}
    for part in text.strip().split("|"):
        if "=" in part:
            k, v = part.split("=", 1)
            fields[k] = v
    if (fields.get("run") != run_id
            or fields.get("inst") != str(new_id)
            or (room_name and fields.get("room") != room_name)):
        return False, text
    return True, text
def _dump_structure_signature(game_file: Path, timeout: int = 300) -> dict:
    """单次只读 UTMT 遍历，输出结构签名（供快照 diff）。

    显式输入 read-through 直读（阶段 1.3：工作区选择不得替换显式 A/B
    输入；只读遍历也不产生 ensure_workspace 复制副作用）。
    """
    out = utmt._run_utmt(_DIFF_SNAPSHOT_CSX, game_file, save=False,
                         resolve_workspace=False, timeout=timeout)
    sig = {"rooms": {}, "code": {}, "counts": {}, "vardeterline": [],
           "strings": [], "instances": [], "codefp": {}, "fonts": {}}
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
        elif line.startswith("STR|"):
            _, ln, sha = line.split("|", 2)
            sig["strings"].append((int(ln), sha))
        elif line.startswith("INST|"):
            _, room_n, iid, obj, xx, yy = line.split("|", 5)
            sig["instances"].append((room_n, int(iid), obj, int(xx), int(yy)))
        elif line.startswith("CODEF|"):
            _, name, n, digest = line.split("|", 3)
            sig["codefp"][name] = (int(n), digest)
        elif line.startswith("FONT|"):
            _, name, glyphs, tex, digest = line.split("|", 4)
            sig["fonts"][name] = (int(glyphs), int(tex), digest)
    return sig


def _diff_detail_resources(a: dict, b: dict) -> dict:
    """资源级差异（阶段 1.3）：字符串 LCS 锚点 / 实例操作分类 / 代码指纹 /
    字体状态。返回可直接打印的明细 dict。"""
    import difflib as _difflib
    out: dict = {}
    # 字符串：有序 (len, sha1) 序列做 LCS——插入/删除使 index 位移，锚点不可见
    sm = _difflib.SequenceMatcher(a=[x[1] for x in a["strings"]],
                                  b=[x[1] for x in b["strings"]], autojunk=False)
    str_changes = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "replace":
            for k in range(min(i2 - i1, j2 - j1)):
                str_changes.append(("change", b["strings"][j1 + k]))
            if i2 - i1 > j2 - j1:
                for k in range(j2 - j1, i2 - i1):
                    str_changes.append(("remove", a["strings"][i1 + k]))
            elif j2 - j1 > i2 - i1:
                for k in range(i2 - i1, j2 - j1):
                    str_changes.append(("add", b["strings"][j1 + k]))
        elif tag == "delete":
            for k in range(i1, i2):
                str_changes.append(("remove", a["strings"][k]))
        elif tag == "insert":
            for k in range(j1, j2):
                str_changes.append(("add", b["strings"][k]))
    out["strings"] = str_changes

    inst_a = {(r, i, o, x, y) for r, i, o, x, y in a["instances"]}
    inst_b = {(r, i, o, x, y) for r, i, o, x, y in b["instances"]}
    removed = inst_a - inst_b
    added = inst_b - inst_a
    moves = []
    for (r1, i1, o1, x1, y1) in sorted(removed):
        same_id = [t for t in added if t[1] == i1]
        if same_id:
            t = same_id[0]
            moves.append((t[0], i1, t[2], t[3], t[4], f"({x1},{y1})→({t[3]},{t[4]})"))
            added.discard(t)
            removed.discard((r1, i1, o1, x1, y1))
    out["instances"] = {"added": sorted(added), "removed": sorted(removed),
                        "moved": sorted(moves)}

    fp_a, fp_b = a["codefp"], b["codefp"]
    out["code"] = {
        "changed": sorted(k for k in fp_a.keys() & fp_b.keys() if fp_a[k] != fp_b[k]),
        "added": sorted(fp_b.keys() - fp_a.keys()),
        "removed": sorted(fp_a.keys() - fp_b.keys()),
    }
    f_a, f_b = a["fonts"], b["fonts"]
    out["fonts"] = {
        "changed": sorted(k for k in f_a.keys() & f_b.keys() if f_a[k] != f_b[k]),
        "added": sorted(f_b.keys() - f_a.keys()),
        "removed": sorted(f_a.keys() - f_b.keys()),
    }
    return out


def _evaluate_expected(detail: dict, expected: dict) -> list[str]:
    """1.4：--expected 声明允许改变的资源范围 → 范围外差异清单（空 = 全部在范围内）。

    形态（03 1.4）：{"strings": "any" | ["sha1", ...],
                     "code": "any" | ["条目名", ...],
                     "instances": {"房间名": ["move", "add", "remove"]},
                     "fonts": "any"}
    counts 允许性由类别推导：声明 strings/code/fonts 任一 → 对应 COUNT 可变。
    """
    violations = []
    strings_scope = expected.get("strings")
    if strings_scope != "any":
        allowed = set(strings_scope or [])
        for op, entry in detail["strings"]:
            if entry[1] not in allowed:
                violations.append(f"STR {op} {entry}")
    code_scope = expected.get("code")
    if code_scope != "any":
        allowed = set(code_scope or [])
        for k in detail["code"]["changed"] + detail["code"]["added"]:
            if k not in allowed:
                violations.append(f"CODE changed/added {k}")
        for k in detail["code"]["removed"]:
            if k not in allowed:
                violations.append(f"CODE removed {k}")
    inst_scope = expected.get("instances") or {}
    for op, items in (("add", detail["instances"]["added"]),
                      ("remove", detail["instances"]["removed"]),
                      ("move", detail["instances"]["moved"])):
        for item in items:
            room = item[0]
            room_scope = (inst_scope.get(room)
                          if room in inst_scope else inst_scope.get("any", []))
            if op not in (room_scope or []):
                violations.append(f"INST {op} {item}")
    fonts_scope = expected.get("fonts")
    if fonts_scope != "any":
        for k in (detail["fonts"]["changed"] + detail["fonts"]["added"]
                  + detail["fonts"]["removed"]):
            violations.append(f"FONT {k}")
    return violations


def cmd_diff_snapshots(file_a: Path, file_b: Path, detail: bool = False,
                       expected: dict | None = None,
                       utmt_timeout: int = 300) -> int:
    """O7 snapshot-diff：两份 game.ios 的结构化差异报告（实验隔离/泄漏取证）。

    对比维度：LastObj、各房间（尺寸/实例数/Tile 数/启用背景层）、代码条目
    （增删/指令数变化）、字符串/精灵/纹理/变量计数、deterline* 变量。
    阶段 1.3 起单次遍历同时携带资源级明细（STR 内容哈希 / 实例坐标 /
    CODEF 反汇编指纹 / FONT 字形+纹理页）——`detail=True` 时输出资源级
    差异报告；`expected` 声明允许改变的资源范围，范围外差异退出码 1（1.4）。
    只读，两次 UTMT 遍历；显式 A/B 输入走 read-through 直读（工作区选择
    不得替换任一输入）。返回结构差异数（含范围外差异）；调用方据以设退出码。
    """
    for f in (file_a, file_b):
        if not f.exists():
            raise errors.NotFoundError(f"文件不存在: {f}")
    print(f"--- diff-snapshots ---\n  A={file_a}\n  B={file_b}")
    a = _dump_structure_signature(file_a, timeout=utmt_timeout)
    b = _dump_structure_signature(file_b, timeout=utmt_timeout)
    diffs = 0

    # counts 允许性由类别推导（审核席 B P2-2）：声明 strings/code/fonts/
    # instances → 对应计数（STRGCOUNT/CODECOUNT/TEXCOUNT/LASTOBJ）可变
    derived_allowed = set()
    if expected:
        if expected.get("strings") is not None:
            derived_allowed.add("STRGCOUNT")
        if expected.get("code") is not None:
            derived_allowed.add("CODECOUNT")
        if expected.get("fonts") is not None:
            derived_allowed.add("TEXCOUNT")
        if expected.get("instances") is not None:
            derived_allowed.add("LASTOBJ")
    for k in sorted(set(a["counts"]) | set(b["counts"])):
        va, vb = a["counts"].get(k), b["counts"].get(k)
        if va != vb:
            if k in derived_allowed:
                print(f"  COUNT {k}: {va} → {vb}（--expected 类别推导，允许）")
            else:
                print(f"  COUNT {k}: {va} → {vb}")
                diffs += 1
    if a["vardeterline"] != b["vardeterline"]:
        print(f"  VARDETERLINE: {a['vardeterline']} → {b['vardeterline']}")
        diffs += 1

    # 结构投影豁免（阶段 1.5 语义缺口修复，议会双席最小切片）：
    # expected.instances 声明房间的操作 → 该房间 ROOM 元组的 inst 计数分量
    # 属声明操作的结构投影（如触发块 spawn）；size/tiles/bg 分量仍计违规
    # （席2 修正案：元组拆分防"整条豁免掩护真实结构变化"）。
    # expected.code 名单/any → 该条目的 CODE 指令数投影豁免；CODEF 指纹仍由
    # 资源级裁决（--detail）。ROOM/CODE 整体增删不豁免。
    rooms_a, rooms_b = a["rooms"], b["rooms"]
    inst_scope = (expected or {}).get("instances") or {}
    for name in sorted(set(rooms_a) - set(rooms_b)):
        print(f"  ROOM 移除: {name}"); diffs += 1
    for name in sorted(set(rooms_b) - set(rooms_a)):
        print(f"  ROOM 新增: {name}"); diffs += 1
    for name in sorted(set(rooms_a) & set(rooms_b)):
        ra, rb = rooms_a[name], rooms_b[name]
        if ra == rb:
            continue
        size_a, inst_a, tiles_a, bg_a = ra
        size_b, inst_b, tiles_b, bg_b = rb
        room_scope = (inst_scope.get(name)
                      if name in inst_scope else inst_scope.get("any", []))
        if inst_a != inst_b and room_scope:
            print(f"  ROOM inst {name}: {inst_a} → {inst_b}"
                  f"（--expected 结构投影，允许）")
        elif inst_a != inst_b:
            print(f"  ROOM inst {name}: {inst_a} → {inst_b}")
            diffs += 1
        if (size_a, tiles_a, bg_a) != (size_b, tiles_b, bg_b):
            print(f"  ROOM 变化: {name}: {ra} → {rb}（inst 计数外的分量变化）")
            diffs += 1

    code_a, code_b = a["code"], b["code"]
    code_scope = (expected or {}).get("code")
    def _code_allowed(name):
        return code_scope == "any" or (isinstance(code_scope, list) and name in code_scope)
    for name in sorted(set(code_a) - set(code_b)):
        print(f"  CODE 移除: {name}"); diffs += 1
    for name in sorted(set(code_b) - set(code_a)):
        if _code_allowed(name):
            print(f"  CODE 新增: {name} (instr={code_b[name]})"
                  f"（--expected 结构投影，允许）")
        else:
            print(f"  CODE 新增: {name} (instr={code_b[name]})"); diffs += 1
    for name in sorted(set(code_a) & set(code_b)):
        if code_a[name] != code_b[name]:
            if _code_allowed(name):
                print(f"  CODE 变化: {name}: instr {code_a[name]} → {code_b[name]}"
                      f"（--expected 结构投影，允许）")
            else:
                print(f"  CODE 变化: {name}: instr {code_a[name]} → {code_b[name]}")
                diffs += 1

    if detail:
        rd = _diff_detail_resources(a, b)
        print("--- 资源级差异（--detail） ---")
        print(f"  字符串: {len(rd['strings'])} 处变化（add/change/remove，内容哈希锚定）")
        print(f"  实例: add={len(rd['instances']['added'])} "
              f"remove={len(rd['instances']['removed'])} "
              f"move={len(rd['instances']['moved'])}")
        print(f"  代码指纹: changed={len(rd['code']['changed'])} "
              f"added={len(rd['code']['added'])} removed={len(rd['code']['removed'])}")
        print(f"  字体: changed={len(rd['fonts']['changed'])} "
              f"added={len(rd['fonts']['added'])} removed={len(rd['fonts']['removed'])}")
        for op, entry in rd["strings"][:10]:
            print(f"    STR {op} len={entry[0]} sha={entry[1][:16]}")
        for item in rd["instances"]["moved"][:10]:
            print(f"    INST move {item[0]} id={item[1]} {item[5]}")
        for k in rd["code"]["changed"][:10]:
            print(f"    CODEF changed {k}")
        violations = _evaluate_expected(rd, expected or {}) if expected is not None else []
        if violations:
            print(f"  ✗ 计划外差异 {len(violations)} 项（超出 --expected 声明范围）:")
            for v in violations[:20]:
                print(f"    {v}")
            diffs += 1
    if diffs == 0:
        print("✅ 结构完全一致（0 差异；资源级明细见上）" if detail
              else "✅ 结构完全一致（0 差异）")
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
