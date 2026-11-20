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

# v1 合同字段集（严格封闭：未知字段拒绝）
TOP_FIELDS = {"schema", "patch_id", "room", "npc", "flag_id"}
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
    # ASCII 合同（v1）：CJK 组合另列验收（C1 实录发现）
    for k in ("prompt", "yes_text", "no_text"):
        v = npc[k]
        try:
            v.encode("ascii")
        except UnicodeEncodeError:
            raise StorylineError(
                f"npc.{k} 含非 ASCII 字符——v1 合同为 ASCII；CJK 组合按 05/C1 "
                "另列验收")
    return doc


def load_definition(path: Path) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    doc = _read_definition(text)
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


def build_plan(defn: dict, game_file: Path) -> dict:
    """只读计划（零写盘）：房间/对象解析 + goto 预解析 + 期望资源集 +
    诊断。解析失败（错房/歧义/缺对象）在写目标前拒绝（12 §C2 验收）。"""
    from ..cmds import template_common, npc as npc_mod

    plan: dict = {"schema": PLAN_SCHEMA,
                  "patch_id": defn["patch_id"],
                  "defn_sha256": defn["_sha256"],
                  "tool_version": _tool_version()}
    # 房间解析（两段式预查，只读 CSX）+ 歧义拒绝（R13 P2-3：子串首中
    # 曾静默绑定——定义侧要求唯一解析：exact==1 且无其余子串命中；
    # exact==0 且恰一子串命中 = 两段式回退合法形态）
    target_idx = template_common.idx_room_lookup(game_file, defn["room"])
    if target_idx < 0:
        raise errors.NotFoundError(f"定义房间不存在: {defn['room']}")
    exact_hits, partial_hits = _room_match_count(game_file, defn["room"])
    plan["room"] = {"name": defn["room"], "idx": target_idx,
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
    # 期望资源集（O7 **汇总行**全量计数口径——R14 P1-1 对齐真实形态；
    # 模板常数，干净基线实证标定）：STR total 9 = 3 对话键 + 6 模板内部串
    # 且明细 op 全为 add；CODEF added = Create_0 +（create 路径）Step_0；
    # CODEF changed = textdata_en 恒 1 +（append 路径 Step_0）+（Alarm 守卫）；
    # INST add 1 / 其余类别 0（变更/删除/移动/字体一票拒绝）；goto/item
    # 变体不改变计数（C1 两分支实证）
    alarm_guard = bool(info["native"] and info["alarm_code"])
    plan["expected_resources"] = {
        "str_total": 9,
        "str_ops": ["add"],
        "inst_adds": 1, "inst_removes": 0, "inst_moves": 0,
        "code_added": 1 if info["step_code"] else 2,
        "code_changed": (1 + (1 if info["step_code"] else 0)
                         + (1 if alarm_guard else 0)),
        "code_removed": 0,
        "code_entry": (info["step_code"] or f"gml_Object_{info['obj']}_Step_0"),
        "code_mode": "append" if info["step_code"] else "create",
        "instance_spawn": {"room": defn["room"], "count": 1},
        "alarm_guard": alarm_guard,
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
    diag.extend(plan.pop("diagnostics_extra", []))
    plan["diagnostics"] = diag
    plan["build_command"] = {
        "action": "npc-choice",
        "args": {
            "room": defn["room"], "object": defn["npc"]["object"],
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


def receipt_path(game_file: Path, patch_id: str) -> Path:
    return _receipt_dir(game_file) / patch_id / "receipt.json"
