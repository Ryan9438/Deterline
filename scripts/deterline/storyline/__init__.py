"""storyline——支线编排层（12 计划 C2/C3/C4）。

给现有内核加一层编排：定义（YAML v1 合同）→ 只读计划（storyline-plan）→
有名工作区构建 + 声明差异核验（storyline-build）→ 整包应用 + 回执 +
幂等/漂移拒绝（storyline-apply）。领域逻辑继续由 npc/dialogue/room 等
域生成器负责；写入只由事务层提交。合同范围 v1：一个已存在房间、一个
NPC、短对话（ASCII）、一组选择、一个独占 flag（声明保留——模板写入
无实机证据，按 12 §C2 记诊断不写入）。

证据分级：build/apply 在 sandbox 副本验证；实机证据挂 B5/R2 矩阵。
"""

import hashlib
import json
import re
from pathlib import Path

from . import yaml_min
from .. import errors, rooms_data, transactions

DEFN_SCHEMA = "deterline.storyline/v1"
PLAN_SCHEMA = "deterline.storyline-plan/v1"
BUILD_SCHEMA = "deterline.storyline-build/v1"
APPLY_SCHEMA = "deterline.storyline-apply/v1"

# v2 合同（16 号计划包 06）：三房间、双分支、显式 ID 与稳定执行顺序。
# 计划层先交付（只读）；build/apply 接入在包 11–15（第三周）。
DEFN_SCHEMA_V2 = "deterline.storyline/v2"
PLAN_SCHEMA_V2 = "deterline.storyline-plan/v2"
V2_TOP_FIELDS = {"schema", "patch_id", "flag_id", "cjk",
                 "rooms", "npcs", "doors", "order"}
V2_NPC_FIELDS = {"room", "object", "x", "y", "range", "prompt",
                 "yes_text", "no_text", "once"}
V2_DOOR_FIELDS = {"from", "to", "x", "y", "spawn_x", "spawn_y"}
V2_ORDER_KINDS = {"npc", "door"}

# v1 合同字段集（严格封闭：未知字段拒绝）
TOP_FIELDS = {"schema", "patch_id", "room", "npc", "flag_id", "cjk"}
NPC_FIELDS = {"object", "x", "y", "range", "prompt", "yes_text", "no_text",
              "yes_goto", "yes_item", "once"}
PATCH_ID_RE = re.compile(r"[a-z0-9][a-z0-9_]{2,63}")   # fullmatch 使用（R13 P3：$ 可被换行绕过）
FLAG_RANGE = (500, 999)      # 自定义独占区（quest 工具区 510+ 与本区重叠由冲突检查裁决）

NPC_PROMPT_MAX_LINES = 3     # npc-choice 3 行限制（含选项行）


class StorylineError(errors.DeterlineError):
    """支线合同/编排错误（可行动消息）。"""


def _read_definition(text: str) -> dict:
    """解析 + 结构校验（严格封闭字段集；未知/缺失/类型错一律拒绝）。"""
    doc = yaml_min.parse(text)
    if not isinstance(doc, dict):
        raise StorylineError("定义必须是映射")
    unknown = set(doc) - TOP_FIELDS
    if unknown:
        raise StorylineError(
            f"未知字段: {sorted(unknown)}（允许: {sorted(TOP_FIELDS)}）")
    missing = {"schema", "patch_id", "room", "npc"} - set(doc)
    if missing:
        raise StorylineError(f"缺少必需字段: {sorted(missing)}")
    if doc["schema"] != DEFN_SCHEMA:
        raise StorylineError(
            f"schema 必须是 {DEFN_SCHEMA}（收到 {doc['schema']!r}）——版本漂移拒绝")
    pid = doc["patch_id"]
    if not isinstance(pid, str) or not PATCH_ID_RE.fullmatch(pid):
        raise StorylineError(
            f"patch_id 须匹配 {PATCH_ID_RE.pattern}（收到 {pid!r}）")
    if not isinstance(doc["room"], str) or not doc["room"]:
        raise StorylineError("room 必须是非空字符串")
    flag = doc.get("flag_id")
    if not isinstance(flag, int) or isinstance(flag, bool) \
            or not (FLAG_RANGE[0] <= flag <= FLAG_RANGE[1]):
        raise StorylineError(
            f"flag_id 必须是 {FLAG_RANGE[0]}-{FLAG_RANGE[1]} 的整数（独占区）")
    npc = doc["npc"]
    if not isinstance(npc, dict):
        raise StorylineError("npc 必须是映射")
    unknown_npc = set(npc) - NPC_FIELDS
    if unknown_npc:
        raise StorylineError(
            f"npc 未知字段: {sorted(unknown_npc)}（允许: {sorted(NPC_FIELDS)}）")
    missing_npc = {"object", "x", "y", "prompt", "yes_text", "no_text"} - set(npc)
    if missing_npc:
        raise StorylineError(f"npc 缺少必需字段: {sorted(missing_npc)}")
    if not isinstance(npc["object"], str) or not npc["object"]:
        raise StorylineError("npc.object 必须是非空字符串")
    for k in ("x", "y"):
        if not isinstance(npc[k], int) or isinstance(npc[k], bool):
            raise StorylineError(f"npc.{k} 必须是整数")
    rng = npc.get("range", 60)
    if not isinstance(rng, int) or isinstance(rng, bool) or rng <= 0:
        raise StorylineError("npc.range 必须是正整数")
    prompt = npc["prompt"]
    if not isinstance(prompt, str) or "\\C" not in prompt:
        raise StorylineError('npc.prompt 必须含 \\C 选择框标记')
    if prompt.count("&") + 1 > NPC_PROMPT_MAX_LINES:
        raise StorylineError(
            f"npc.prompt 共 {prompt.count('&') + 1} 行，超过 {NPC_PROMPT_MAX_LINES} 行限制")
    for k in ("yes_text", "no_text"):
        v = npc[k]
        if not isinstance(v, str) or not v:
            raise StorylineError(f"npc.{k} 必须是非空字符串")
        if "\\C" in v:
            raise StorylineError(f"npc.{k} 不得含 \\C（分支文本防选择框重弹）")
    for k in ("yes_goto",):
        if k in npc and (not isinstance(npc[k], str) or not npc[k]):
            raise StorylineError(f"npc.{k} 必须是非空字符串")
    if "yes_item" in npc:
        it = npc["yes_item"]
        if not isinstance(it, int) or isinstance(it, bool):
            raise StorylineError("npc.yes_item 必须是整数")
    once = npc.get("once", True)
    if not isinstance(once, bool):
        raise StorylineError("npc.once 必须是布尔")
    # 字符集合同：默认 v1 全 ASCII；cjk: true 显式声明中文组合（构建链先
    # 注入 CJK 字体栈——fusion-pixel 12px OFL，typer=31 B4 实证）
    cjk = doc.get("cjk", False)
    if not isinstance(cjk, bool):
        raise StorylineError("cjk 必须是布尔（true = 中文组合构建）")
    if not cjk:
        for k in ("prompt", "yes_text", "no_text"):
            v = npc[k]
            try:
                v.encode("ascii")
            except UnicodeEncodeError:
                raise StorylineError(
                    f"npc.{k} 含非 ASCII 字符——v1 默认合同为 ASCII；中文组合"
                    "请在定义顶层声明 cjk: true（构建链先注入 CJK 字体栈，"
                    "typer=31；渲染语义待 R2-CJK 实机收口）")
    return doc


def _read_definition_v2(text: str) -> dict:
    """v2 合同解析（包 06/07）：三房间、双分支、显式 ID + 稳定执行顺序。

    与 v1 同一 fail-closed 风格：YAML 层错误带行号（yaml_min），合同层
    错误指向字段。结构 = rooms（别名→房间名）+ npcs（id→规格）+
    doors（id→连接）+ order（"<kind>:<id>" 稳定执行序）。
    """
    doc = yaml_min.parse(text)
    if not isinstance(doc, dict):
        raise StorylineError("定义必须是映射")
    unknown = set(doc) - V2_TOP_FIELDS
    if unknown:
        raise StorylineError(
            f"未知字段: {sorted(unknown)}（允许: {sorted(V2_TOP_FIELDS)}）")
    missing = {"schema", "patch_id", "rooms", "npcs", "order"} - set(doc)
    if missing:
        raise StorylineError(f"缺少必需字段: {sorted(missing)}")
    if doc["schema"] != DEFN_SCHEMA_V2:
        raise StorylineError(
            f"schema 必须是 {DEFN_SCHEMA_V2}（收到 {doc['schema']!r}）——版本漂移拒绝")
    pid = doc["patch_id"]
    if not isinstance(pid, str) or not PATCH_ID_RE.fullmatch(pid):
        raise StorylineError(
            f"patch_id 须匹配 {PATCH_ID_RE.pattern}（收到 {pid!r}）")
    flag = doc.get("flag_id")
    if flag is not None and (
            not isinstance(flag, int) or isinstance(flag, bool)
            or not (FLAG_RANGE[0] <= flag <= FLAG_RANGE[1])):
        raise StorylineError(
            f"flag_id 必须是 {FLAG_RANGE[0]}-{FLAG_RANGE[1]} 的整数（声明保留）"
            "；缺省 = 不声明（状态写入为包 18 候选）")
    cjk = doc.get("cjk", False)
    if not isinstance(cjk, bool):
        raise StorylineError("cjk 必须是布尔（true = 中文组合构建）")
    rooms = doc["rooms"]
    if not isinstance(rooms, dict) or not rooms:
        raise StorylineError("rooms 必须是非空映射（别名 → 房间名）")
    import re as _re
    for alias, name in rooms.items():
        # yaml_min 键恒为字符串；仍要求标识符形态（R-0610 P3-3：数字形键
        # "1" 可作引用键无诊断——别名是 npcs/doors/order 的引用键，收紧）
        if not isinstance(alias, str) or not alias \
                or not _re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", alias):
            raise StorylineError(
                f"rooms 别名必须是标识符（[A-Za-z_][A-Za-z0-9_]{{0,63}}，"
                f"收到 {alias!r}）——别名是 npcs/doors/order 的引用键")
        if not isinstance(name, str) or not name:
            raise StorylineError(f"rooms.{alias} 必须是非空字符串（房间名）")
    npcs = doc.get("npcs") or {}
    doors = doc.get("doors") or {}
    if not isinstance(npcs, dict) or not npcs:
        raise StorylineError("npcs 必须是非空映射（npc id → 规格）")
    for nid, spec in npcs.items():
        if not isinstance(spec, dict):
            raise StorylineError(f"npcs.{nid} 必须是映射")
        unknown_npc = set(spec) - V2_NPC_FIELDS
        if unknown_npc:
            raise StorylineError(
                f"npcs.{nid} 未知字段: {sorted(unknown_npc)}"
                f"（允许: {sorted(V2_NPC_FIELDS)}）")
        miss = {"room", "object", "x", "y", "prompt"} - set(spec)
        if miss:
            raise StorylineError(f"npcs.{nid} 缺少必需字段: {sorted(miss)}")
        if not isinstance(spec["room"], str) or not spec["room"]:
            raise StorylineError(f"npcs.{nid}.room 必须是 rooms 别名（字符串）")
        if spec["room"] not in rooms:
            raise StorylineError(
                f"npcs.{nid}.room 引用未知房间别名 '{spec['room']}'"
                f"（已有: {sorted(rooms)}）")
        if not isinstance(spec["object"], str) or not spec["object"]:
            raise StorylineError(f"npcs.{nid}.object 必须是非空字符串")
        for k in ("x", "y"):
            if not isinstance(spec[k], int) or isinstance(spec[k], bool):
                raise StorylineError(f"npcs.{nid}.{k} 必须是整数")
        rng = spec.get("range", 60)
        if not isinstance(rng, int) or isinstance(rng, bool) or rng <= 0:
            raise StorylineError(f"npcs.{nid}.range 必须是正整数")
        prompt = spec["prompt"]
        if not isinstance(prompt, str) or not prompt:
            raise StorylineError(f"npcs.{nid}.prompt 必须是非空字符串")
        has_choice = "\\C" in prompt
        if has_choice:
            for k in ("yes_text", "no_text"):
                v = spec.get(k)
                if not isinstance(v, str) or not v:
                    raise StorylineError(
                        f"npcs.{nid}.{k} 必须是非空字符串（prompt 含 \\C "
                        "即选择语义，YES/NO 分支文本必填）")
                if "\\C" in v:
                    raise StorylineError(
                        f"npcs.{nid}.{k} 不得含 \\C（分支文本防选择框重弹）")
        elif "yes_text" in spec or "no_text" in spec:
            raise StorylineError(
                f"npcs.{nid}: 无 \\C 的 prompt 是纯对话，不得带 yes_text/no_text"
                "（选择语义需在 prompt 内加 \\C）")
        once = spec.get("once", True)
        if not isinstance(once, bool):
            raise StorylineError(f"npcs.{nid}.once 必须是布尔")
        if not cjk:
            keys = ["prompt"] + [k for k in ("yes_text", "no_text") if k in spec]
            for k in keys:
                try:
                    spec[k].encode("ascii")
                except UnicodeEncodeError:
                    raise StorylineError(
                        f"npcs.{nid}.{k} 含非 ASCII 字符——默认合同为 ASCII；"
                        "中文组合请在定义顶层声明 cjk: true")
    for did, spec in doors.items():
        if not isinstance(spec, dict):
            raise StorylineError(f"doors.{did} 必须是映射")
        unknown_door = set(spec) - V2_DOOR_FIELDS
        if unknown_door:
            raise StorylineError(
                f"doors.{did} 未知字段: {sorted(unknown_door)}"
                f"（允许: {sorted(V2_DOOR_FIELDS)}）")
        miss = set(V2_DOOR_FIELDS) - set(spec)
        if miss:
            raise StorylineError(f"doors.{did} 缺少必需字段: {sorted(miss)}")
        for k in ("from", "to"):
            if not isinstance(spec[k], str) or spec[k] not in rooms:
                raise StorylineError(
                    f"doors.{did}.{k} 必须引用 rooms 别名"
                    f"（收到 {spec[k]!r}；已有: {sorted(rooms)}）")
        for k in ("x", "y", "spawn_x", "spawn_y"):
            if not isinstance(spec[k], int) or isinstance(spec[k], bool):
                raise StorylineError(f"doors.{did}.{k} 必须是整数")
    order = doc["order"]
    if not isinstance(order, list) or not order:
        raise StorylineError(
            "order 必须是非空标量序列（\"<kind>:<id>\" 稳定执行序）")
    seen: dict[str, int] = {}
    for i, ref in enumerate(order, 1):
        if not isinstance(ref, str) or ":" not in ref:
            raise StorylineError(
                f"order[{i}] 必须是 \"<kind>:<id>\"（kind ∈ "
                f"{sorted(V2_ORDER_KINDS)}；收到 {ref!r}）")
        kind, _, oid = ref.partition(":")
        if kind not in V2_ORDER_KINDS:
            raise StorylineError(
                f"order[{i}] 未知 kind '{kind}'（允许: {sorted(V2_ORDER_KINDS)}）")
        table = npcs if kind == "npc" else doors
        if oid not in table:
            raise StorylineError(
                f"order[{i}] 引用不存在的 {kind} id '{oid}'"
                f"（已有: {sorted(table)}）")
        key = f"{kind}:{oid}"
        if key in seen:
            raise StorylineError(
                f"order[{i}] 重复引用 {key}（首次在 order[{seen[key]}]）")
        seen[key] = i
    for kind, table in (("npc", npcs), ("door", doors)):
        for oid in table:
            if f"{kind}:{oid}" not in seen:
                raise StorylineError(
                    f"{kind} '{oid}' 未出现在 order 中（每个 npc/door 必须"
                    "恰好排入执行序一次——稳定排序合同）")
    return doc


def load_definition(path: Path) -> dict:
    """定义载入 + 版本分派（包 07）：按 schema 分派 v1/v2 合同校验。

    v1 路径与既有调用方式完全兼容（未知 schema 落 v1 → 原样版本漂移拒绝）。
    """
    text = Path(path).read_text(encoding="utf-8")
    peek = yaml_min.parse(text)
    schema = peek.get("schema") if isinstance(peek, dict) else None
    if schema == DEFN_SCHEMA_V2:
        doc = _read_definition_v2(text)
        doc["_version"] = "v2"
    else:
        doc = _read_definition(text)
        doc["_version"] = "v1"
    doc["_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return doc





def _receipt_dir(game_file: Path) -> Path:
    """回执根：`<game 目录>/.deterline/storyline/<游戏文件名>/`——**按游戏
    文件隔离**（R13 CLI 复跑发现：目录级共享曾让 /tmp 下多个 *.ios 复用
    同一份 build/receipt，跨文件污染 → 陈旧构建上盘）。"""
    return game_file.parent / ".deterline" / "storyline" / game_file.name


def _load_receipts(game_file: Path) -> list[dict]:
    out = []
    rdir = _receipt_dir(game_file)
    if rdir.is_dir():
        for p in sorted(rdir.glob("*/receipt.json")):
            try:
                rec = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(rec, dict) and rec.get("schema") == APPLY_SCHEMA:
                    rec["_path"] = str(p)
                    out.append(rec)
            except (OSError, ValueError):
                continue
    return out


def _flag_conflicts(defn: dict, game_file: Path) -> list[str]:
    """flag 独占区冲突检查：同 flag 被其他补丁回执占用即冲突（v1 声明保留口径）。"""
    conflicts = []
    for rec in _load_receipts(game_file):
        if rec.get("patch_id") != defn["patch_id"] \
                and rec.get("flag_id") == defn.get("flag_id"):
            conflicts.append(f"{rec.get('patch_id')}（flag {rec.get('flag_id')}）")
    return conflicts


def _room_match_count(game_file: Path, name: str) -> tuple[int, int]:
    """只读 CSX 探针：房间名 exact / 其余子串命中数（R13 P2-3 歧义拒绝
    的计数证据）。独立于 template_common.idx_room_lookup（其 CSX 被
    door/pit golden 钉死，不可改动）。"""
    from .. import utmt
    esc = utmt._csx_escape(name)
    csx = f'''
int exact = 0; int partial = 0;
for (int i = 0; i < Data.Rooms.Count; i++) {{
    string rn = Data.Rooms[i].Name.Content;
    if (rn == "{esc}") {{ exact++; }}
    else if (rn.IndexOf("{esc}", StringComparison.OrdinalIgnoreCase) >= 0) {{ partial++; }}
}}
ScriptMessage("ROOM_MATCH:" + exact + ":" + partial);
'''
    out = utmt._run_utmt(csx, game_file, save=False)
    for line in utmt._parse_msg(out):
        if line.startswith("ROOM_MATCH:"):
            parts = line.split(":")
            return int(parts[1]), int(parts[2])
    return 0, 0


def _room_name_by_idx(game_file: Path, idx: int) -> str | None:
    """只读 CSX 探针：按序号取房间**实际名**（两段式子串回退时可能不同于
    定义名——结构闸门按实际名比对 ROOM 行，构建也以实际名为准）。"""
    from .. import utmt
    csx = f'''
if ({int(idx)} < 0 || {int(idx)} >= Data.Rooms.Count) {{
    ScriptMessage("ROOM_NAME:NOT_FOUND");
}} else {{
    ScriptMessage("ROOM_NAME:" + Data.Rooms[{int(idx)}].Name.Content);
}}
'''
    out = utmt._run_utmt(csx, game_file, save=False)
    for line in utmt._parse_msg(out):
        if line.startswith("ROOM_NAME:"):
            val = line[len("ROOM_NAME:"):]
            return None if val == "NOT_FOUND" else val
    return None


def _room_size_by_idx(game_file: Path, idx: int) -> tuple | None:
    """只读 CSX 探针：房间尺寸 (W, H)（包 11 资源清单：坐标范围校验依据）。"""
    from .. import utmt
    csx = f'''
if ({int(idx)} < 0 || {int(idx)} >= Data.Rooms.Count) {{
    ScriptMessage("ROOM_SIZE:NOT_FOUND");
}} else {{
    ScriptMessage("ROOM_SIZE:" + Data.Rooms[{int(idx)}].Width + "x"
                  + Data.Rooms[{int(idx)}].Height);
}}
'''
    out = utmt._run_utmt(csx, game_file, save=False)
    for line in utmt._parse_msg(out):
        if line.startswith("ROOM_SIZE:"):
            val = line[len("ROOM_SIZE:"):]
            if val == "NOT_FOUND":
                return None
            w, _, h = val.partition("x")
            return (int(w), int(h))
    return None


def build_plan(defn: dict, game_file: Path) -> dict:
    """只读计划（零写盘）：房间/对象解析 + goto 预解析 + 期望资源集 +
    诊断。解析失败（错房/歧义/缺对象）在写目标前拒绝（12 §C2 验收）。

    版本分派（包 07/10）：v2 定义走 build_plan_v2（三房间/双分支/操作序）。
    """
    if defn.get("_version") == "v2":
        return build_plan_v2(defn, game_file)
    from ..cmds import template_common, npc as npc_mod, code as code_mod

    plan: dict = {"schema": PLAN_SCHEMA,
                  "patch_id": defn["patch_id"],
                  "defn_sha256": defn["_sha256"],
                  "tool_version": _tool_version(),
                  "cjk": bool(defn.get("cjk", False))}
    # 房间解析（两段式预查，只读 CSX）+ 歧义拒绝（R13 P2-3：子串首中
    # 曾静默绑定——定义侧要求唯一解析：exact==1 且无其余子串命中；
    # exact==0 且恰一子串命中 = 两段式回退合法形态）
    target_idx = template_common.idx_room_lookup(game_file, defn["room"])
    if target_idx < 0:
        raise errors.NotFoundError(f"定义房间不存在: {defn['room']}")
    actual_room = _room_name_by_idx(game_file, target_idx)
    if actual_room is None:
        raise errors.ValidationError(
            f"房间序号 {target_idx} 越界（idx_room_lookup 与实际表不一致）")
    exact_hits, partial_hits = _room_match_count(game_file, defn["room"])
    plan["room"] = {"requested": defn["room"], "name": actual_room,
                    "idx": target_idx,
                    "exact_hits": exact_hits, "partial_hits": partial_hits}
    # 歧义判据（R13 P2-3 修订）：两段式语义下 exact 命中**确定性胜出**——
    # exact==1 恒唯一（前缀子集名如 room_ruins1 vs room_ruins10 合法）；
    # 仅 exact>1（重名不可能但防御）或 exact==0 且子串>1（回退首中不定）拒绝
    if exact_hits > 1 or (exact_hits == 0 and partial_hits > 1):
        raise errors.ValidationError(
            f"定义房间歧义: '{defn['room']}'（exact {exact_hits} / "
            f"其余子串 {partial_hits}）——请用完整唯一房间名（12 §C2 歧义写前拒绝）")
    # 对象解析（存在性/继承链，只读 CSX）
    info = npc_mod._query_npc_target(game_file, defn["npc"]["object"])
    if info is None:
        raise errors.NotFoundError(f"定义对象不存在: {defn['npc']['object']}")
    plan["npc"] = {"object": info["obj"], "native": bool(info["native"]),
                   "step_code": info["step_code"],
                   "x": defn["npc"]["x"], "y": defn["npc"]["y"],
                   "range": defn["npc"].get("range", 60)}
    if info["obj"].lower() != defn["npc"]["object"].lower():
        plan["diagnostics_extra"] = [
            f"对象经子串匹配首中: {defn['npc']['object']} → {info['obj']}"
            "（唯一性无计数证据——如需强唯一请用完整对象名）"]
    # goto 预解析（写前拒绝错目标）+ 数字形态越界拒绝（R13 P2-2）
    goto = defn["npc"].get("yes_goto")
    if goto:
        resolved = rooms_data.resolve_room(goto)
        if str(goto).lstrip("-").isdigit() and str(resolved) not in rooms_data.ROOMS:
            raise errors.ValidationError(
                f"yes_goto 数字目标越界: {goto}（不在已知房间序号内）")
        plan["goto"] = {"requested": goto, "resolved": resolved}
    # flag：声明保留 + 冲突诊断（模板 v1 不写入——无实机证据）
    conflicts = _flag_conflicts(defn, game_file)
    plan["flag"] = {"id": defn["flag_id"], "status": "declared-only",
                    "conflicts": conflicts,
                    "note": "模板 v1 不写入 flag——无实机证据的写入路径按 12 §C2 禁用"}
    # Create 事件探针（F2：期望分支按实际形态标定——此前仅 append/create
    # 两式，"自有/继承 Create_0 未引用 deterline_state → prepend"形态下
    # 期望集失真，闸门会误拒合法构建）：三式 =
    #   create  无任何 Create 事件 → 构建时新建（CODEF added +1）
    #   prepend 有效 Create_0 存在但未引用变量 → 前插初始化行（CODEF changed +1）
    #   skip    有效 Create_0 已引用 deterline_state → 零改动（干净基线下不可达，
    #           只在已打过 deterline 补丁的文件出现——闸门按干净基线拒绝该形态）
    create_code = npc_mod._find_create_code(game_file, info["obj"])
    create_mode = "create"
    if create_code is not None:
        status, create_lines, _detail = code_mod.decompile_classified(
            game_file, create_code)
        if status != "ok":
            raise StorylineError(
                f"Create 事件探针读失败（{create_code} status={status}）——"
                "无法标定期望资源集，拒绝（读失败不作空/已初始化假设，"
                "B3 三分类口径；工具超时/协议异常请复跑 storyline-plan）")
        create_mode = ("skip" if any("deterline_state" in ln for ln in create_lines)
                       else "prepend")
    # 期望资源集（O7 **汇总行**全量计数口径——R14 P1-1 对齐真实形态；
    # 模板常数，干净基线实证标定）：STR total 9 = 3 对话键 + 6 模板内部串
    # 且明细 op 全为 add；CODEF added =（create 路径 Step_0）+（create 路径
    # Create_0）；CODEF changed = textdata_en 恒 1 +（append 路径 Step_0）
    # +（Alarm 守卫）+（Create_0 前插）；INST add 1 / 其余类别 0（变更/
    # 删除/移动/字体一票拒绝）；goto/item 变体不改变计数（C1 两分支实证）
    alarm_guard = bool(info["native"] and info["alarm_code"])
    expected_code_added = []
    if not info["step_code"]:
        expected_code_added.append(f"gml_Object_{info['obj']}_Step_0")
    if create_code is None:
        expected_code_added.append(f"gml_Object_{info['obj']}_Create_0")
    expected_code_changed = ["gml_Script_textdata_en"]
    if info["step_code"]:
        expected_code_changed.append(info["step_code"])
    if alarm_guard:
        expected_code_changed.append(info["alarm_code"])
    if create_mode == "prepend":
        expected_code_changed.append(create_code)
    plan["expected_resources"] = {
        "str_total": 9,
        "str_ops": ["add"],
        "inst_adds": 1, "inst_removes": 0, "inst_moves": 0,
        "code_added": (0 if info["step_code"] else 1)
                      + (0 if create_code is not None else 1),
        "code_changed": (1 + (1 if info["step_code"] else 0)
                         + (1 if alarm_guard else 0)
                         + (1 if create_mode == "prepend" else 0)
                         + (2 if defn.get("cjk") else 0)),
        "code_removed": 0,
        "code_entry": (info["step_code"] or f"gml_Object_{info['obj']}_Step_0"),
        "code_mode": "append" if info["step_code"] else "create",
        "code_entry_create": create_code,
        "code_mode_create": create_mode,
        "instance_spawn": {"room": actual_room, "count": 1},
        "alarm_guard": alarm_guard,
        # CJK 组合：字体管线改 fnt_ja_maintext 字形表（FONT changed 1）；
        # 不新增字体资产/纹理页（约束④）
        "font_changed": 1 if defn.get("cjk") else 0,
    }
    # CJK 组合：字体管线改动两个代码条目（scr_setfont 单行映射 +
    # scr_preload_textures 无条件 prefetch——cjk.py pass2）
    if defn.get("cjk"):
        expected_code_changed.extend(["gml_Script_scr_setfont",
                                      "gml_Script_scr_preload_textures"])
    # 结构层期望（F1：O7 结构段——COUNT/VARDETERLINE/ROOM/CODE 行——进闸门
    # 比对；v1 此前只吃资源级汇总行，结构漂移仅经 CODEF/INST 间接可见）
    plan["expected_structure"] = {
        "count_deltas": {
            "STRGCOUNT": 9,
            "CODECOUNT": len(expected_code_added),
            "SPRCOUNT": 0, "TEXCOUNT": 0,
            # LastObj 实证标定（rc3 真 CLI 全链首跑）：CodeImportGroup/
            # AutoCreateAssets 新建代码条目时 LastObj +1（整体 +1，非逐条目）
            "LASTOBJ": 1 if expected_code_added else 0,
            # deterline_state 变量注册（Data.Variables +1）——skip 式不新增
            "VARS": 1,
        },
        # 干净基线合同：A 侧必须无 deterline* 变量；B 侧恰新增一条
        # deterline_state（NameStringID≠0——NSID=0 崩溃根因，见 npc.py
        # _ensure_var_initialized；Occurrences≥1——本模板仅 Create_0 一处引用）
        "var_added": "deterline_state",
        "room_inst": {actual_room: 1},
        "room_removed": [], "room_added": [], "room_changed": [],
        "code_added": sorted(expected_code_added),
        "code_removed": [],
        "code_changed": sorted(expected_code_changed),
    }
    # 诊断
    diag = []
    if defn["npc"].get("once", True):
        diag.append("once=true：触发后 NPC 自毁（v1 状态语义）")
    if goto:
        diag.append(f"YES 分支传送 → {plan['goto']['resolved']}")
    if "yes_item" in defn["npc"]:
        diag.append(f"YES 分支给物品 {defn['npc']['yes_item']}")
    if conflicts:
        diag.append("flag 冲突: " + "; ".join(conflicts))
    if create_mode == "prepend":
        own = create_code == f"gml_Object_{info['obj']}_Create_0"
        diag.append(
            f"Create 事件前插初始化行 → {create_code}"
            + ("" if own else "（**继承**自父对象——改动落在父对象条目）"))
    elif create_mode == "skip":
        diag.append(f"Create 事件已引用 deterline_state（{create_code}）——"
                    "基线非干净（已含 deterline 补丁），结构闸门将按干净基线拒绝")
    if actual_room != defn["room"]:
        diag.append(f"房间经两段式子串解析: {defn['room']} → {actual_room}")
    if defn.get("cjk"):
        diag.append("cjk=true：构建链先注入 CJK 字体栈（fusion-pixel 12px "
                    "OFL，typer=31 B4 实证）——选择框渲染语义待 R2-CJK 实机收口")
    diag.extend(plan.pop("diagnostics_extra", []))
    plan["diagnostics"] = diag
    plan["build_command"] = {
        "action": "npc-choice",
        "args": {
            "room": actual_room, "object": defn["npc"]["object"],
            "x": defn["npc"]["x"], "y": defn["npc"]["y"],
            "text_key": f"det_{defn['patch_id']}_choice",
            "yes_text_key": f"det_{defn['patch_id']}_yes",
            "no_text_key": f"det_{defn['patch_id']}_no",
        },
    }
    return plan


def _tool_version() -> str:
    import sys as _sys
    return _sys.modules[__package__.split(".")[0]].__version__


def build_plan_v2(defn: dict, game_file: Path) -> dict:
    """v2 只读计划（包 08 编译 + 包 09 图诊断）：别名解析、对象/Create 探针、
    操作序编译（order 即执行序）、门图连通性诊断、语义指纹。零写盘。"""
    from ..cmds import template_common, npc as npc_mod, code as code_mod

    rooms_def = defn["rooms"]
    npcs_def = defn.get("npcs") or {}
    doors_def = defn.get("doors") or {}
    plan: dict = {"schema": PLAN_SCHEMA_V2, "version": "v2",
                  "patch_id": defn["patch_id"],
                  "defn_sha256": defn["_sha256"],
                  "tool_version": _tool_version(),
                  "cjk": bool(defn.get("cjk", False))}
    # 房间别名解析（复用 v1 两段式预查 + 歧义判据，R13 P2-3 口径）
    resolved: dict[str, dict] = {}
    for alias, requested in rooms_def.items():
        idx = template_common.idx_room_lookup(game_file, requested)
        if idx < 0:
            raise errors.NotFoundError(f"rooms.{alias} 房间不存在: {requested}")
        actual = _room_name_by_idx(game_file, idx)
        if actual is None:
            raise errors.ValidationError(
                f"rooms.{alias} 房间序号 {idx} 越界"
                "（idx_room_lookup 与实际表不一致）")
        exact, partial = _room_match_count(game_file, requested)
        if exact > 1 or (exact == 0 and partial > 1):
            raise errors.ValidationError(
                f"rooms.{alias} 房间歧义: '{requested}'（exact {exact} / "
                f"其余子串 {partial}）——请用完整唯一房间名")
        resolved[alias] = {"requested": requested, "name": actual,
                           "idx": idx, "exact_hits": exact,
                           "partial_hits": partial}
        size = _room_size_by_idx(game_file, idx)
        if size is None:
            raise errors.ValidationError(
                f"rooms.{alias} 尺寸探针失败（idx {idx}）——拒绝"
                "（资源清单必须可读，包 11）")
        resolved[alias]["size_w"], resolved[alias]["size_h"] = size
        if actual != requested:
            resolved[alias]["note"] = f"两段式子串解析: {requested} → {actual}"
    plan["rooms"] = resolved
    # 坐标范围校验（包 11）：npc 与门坐标必须落在所属房间界内
    def _in_bounds(alias: str, x: int, y: int, field: str) -> None:
        r = resolved[alias]
        if not (0 <= x < r["size_w"]) or not (0 <= y < r["size_h"]):
            raise errors.ValidationError(
                f"{field} 坐标越界: ({x},{y}) 不在 rooms.{alias} "
                f"{r['size_w']}x{r['size_h']} 界内（包 11 资源清单）")
    for nid, spec in npcs_def.items():
        _in_bounds(npcs_def[nid]["room"], spec["x"], spec["y"],
                   f"npcs.{nid}")
    for did, spec in doors_def.items():
        _in_bounds(spec["from"], spec["x"], spec["y"], f"doors.{did}")
        _in_bounds(spec["to"], spec["spawn_x"], spec["spawn_y"],
                   f"doors.{did} spawn")
    # npc 规格 → 对象/Create 探针（复用 v1 探针；逐 npc 记录）
    npc_plan: dict = {}
    for nid, spec in npcs_def.items():
        info = npc_mod._query_npc_target(game_file, spec["object"])
        if info is None:
            raise errors.NotFoundError(
                f"npcs.{nid}.object 对象不存在: {spec['object']}")
        create_code = npc_mod._find_create_code(game_file, info["obj"])
        create_mode = "create"
        if create_code is not None:
            status, create_lines, _detail = code_mod.decompile_classified(
                game_file, create_code)
            if status != "ok":
                raise StorylineError(
                    f"npcs.{nid} Create 事件探针读失败（{create_code} "
                    f"status={status}）——无法标定期望资源集，拒绝"
                    "（读失败不作假设，B3 三分类口径）")
            create_mode = ("skip" if any("deterline_state" in ln
                                         for ln in create_lines) else "prepend")
        if create_mode == "skip":
            raise StorylineError(
                f"npcs.{nid}: {info['obj']} 的 Create 已引用 deterline_state"
                f"（{create_code}）——基线非干净，v2 拒绝（干净基线合同）")
        npc_plan[nid] = {"room": spec["room"], "object": info["obj"],
                         "native": bool(info["native"]),
                         "step_code": info["step_code"],
                         "x": spec["x"], "y": spec["y"],
                         "range": spec.get("range", 60),
                         "choice": "\\C" in spec["prompt"],
                         "once": spec.get("once", True),
                         "create_code": create_code,
                         "create_mode": create_mode}
    plan["npcs"] = npc_plan
    # 门解析（别名 → 已解析房间）
    door_plan: dict = {}
    for did, spec in doors_def.items():
        door_plan[did] = {"from": resolved[spec["from"]],
                          "to": resolved[spec["to"]],
                          "x": spec["x"], "y": spec["y"],
                          "spawn_x": spec["spawn_x"],
                          "spawn_y": spec["spawn_y"]}
    plan["doors"] = door_plan
    # 操作序编译（order 即执行序——稳定排序合同；顺序变更 = 语义变更）
    ops: list[dict] = []
    for ref in defn["order"]:
        kind, _, oid = ref.partition(":")
        if kind == "npc":
            spec = npcs_def[oid]
            ops.append({"op": "npc", "ref": oid, "npc": npc_plan[oid],
                        "prompt": spec["prompt"],
                        "yes_text": spec.get("yes_text"),
                        "no_text": spec.get("no_text")})
        else:
            ops.append({"op": "door", "ref": oid,
                        "door": door_plan[oid]})
    plan["ops"] = ops
    # 图诊断（包 09）：从首 npc 房间做可达性遍历（栈式 DFS——queue.pop()；
    # R-0610 P3-1 订正命名）；不可达/死路为诊断（非硬错误）
    diag: list[str] = []
    first_npc = next((o["ref"] for o in ops if o["op"] == "npc"), None)
    if first_npc is not None:
        start_alias = npcs_def[first_npc]["room"]
        adj: dict[str, set] = {a: set() for a in resolved}
        for spec in doors_def.values():
            adj[spec["from"]].add(spec["to"])
        seen_rooms = {start_alias}
        stack = [start_alias]
        while stack:
            cur = stack.pop()
            for nxt in sorted(adj.get(cur, ())):
                if nxt not in seen_rooms:
                    seen_rooms.add(nxt)
                    stack.append(nxt)
        unreachable = sorted(set(resolved) - seen_rooms)
        if unreachable:
            diag.append(f"从首 npc 房间 '{start_alias}' 不可达的房间: "
                        f"{unreachable}（检查 doors 连接）")
        dead = sorted(a for a in resolved
                      if not adj.get(a) and a != start_alias)
        if dead:
            diag.append(f"无出向门（死路）的房间: {dead}（若为终点可忽略）")
    for nid, spec in npcs_def.items():
        if spec.get("once", True):
            diag.append(f"npcs.{nid}.once=true：触发后自毁（v2 状态语义）")
    if defn.get("cjk"):
        diag.append("cjk=true：构建链先注入 CJK 字体栈（包 15 整包复用）")
    diag.append("flag 声明保留（v2 状态写入为独立候选——包 18）")
    plan["diagnostics"] = diag
    # 语义指纹（包 08）：规范化（sort_keys）哈希——**不含 defn_sha256**
    # （原始文本哈希；等价映射重排/注释差异必须产出同一指纹——R-0610 P2-1
    # 清偿；内容变更通过 ops/rooms/npcs/doors 中的实际值进入指纹）。
    semantic = {"patch_id": defn["patch_id"],
                "rooms": plan["rooms"], "npcs": npc_plan,
                "doors": door_plan, "ops": ops, "cjk": plan["cjk"]}
    plan["semantic_sha256"] = hashlib.sha256(
        json.dumps(semantic, sort_keys=True, ensure_ascii=False)
        .encode("utf-8")).hexdigest()
    plan["flag"] = {"id": defn.get("flag_id"), "status": "declared-only",
                    "conflicts": _flag_conflicts(defn, game_file),
                    "note": "v2 状态写入为独立候选（包 18），模板不写入"}
    plan["unverified"] = [
        "构建/应用接入（包 11–15，第三周）",
        "状态模型与存读档轨迹（包 16–17，第四周）",
        "游戏侧状态写入候选（包 18；缺实机时主样例交模拟轨迹+待验卡）",
        "渲染/按键/真实存读档（游戏前台，16 §7 附录）"]
    return plan


def receipt_path(game_file: Path, patch_id: str) -> Path:
    return _receipt_dir(game_file) / patch_id / "receipt.json"
