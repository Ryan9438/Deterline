"""storyline 命令入口（12 计划 C2/C3/C4）：plan / build / apply。

plan（只读）：解析定义 → build_plan（房间/对象/goto 预解析）→ JSON stdout
（schema deterline.storyline-plan/v1）。

build：plan → 有名工作区构建（npc-choice 经域生成器）→ 工作区产物 vs 基线
O7 结构化差异 → 与计划期望资源集比对（未声明变更 = 拒绝出候选）→ 构建
回执（fingerprint/declared diff）。构建期间仅写工作区。

apply：构建回执 → 目标基线核对 + 幂等（同 ID 同内容且目标==after → 已应用）
/ 同 ID 不同内容或目标漂移拒绝 → 整包应用（复用 sandbox-restore 事务层）
→ 回执落盘 .deterline/storyline/<patch_id>/receipt.json。中断交给恢复
分类（journal 复用方案 A），不靠猜测宣布已应用。

退出码：0=成功/已应用/预览；1=拒绝（合同/解析/差异/漂移/冲突）——定位失败
在 dispatch 层呈拒绝形态（无 2 出口路径，R14 P3-3 如实化）。
"""

import json
import re
import sys
from pathlib import Path

from .. import errors, transactions


def _pkg():
    """运行时取本包模块（跨模块引用一律运行时属性查找——包纪律）。
    commands 由 __init__ 导入，此处 _sys.modules[__package__] 在运行期
    已完成初始化。"""
    import sys as _sys
    return _sys.modules[__package__]


def _load_composed(defn_path: str, value2: str) -> tuple[dict, dict, dict]:
    """包 27/28：载入两定义并合成（合成 defn_sha = 两组件 sha 的定值哈希——
    同一对文件恒同指纹，apply 侧可复算比对）。"""
    a = _pkg().load_definition(Path(defn_path))
    b = _pkg().load_definition(Path(value2))
    from . import ownership
    comp = ownership.compose_definitions(a, b)
    comp["_sha256"] = _pkg().hashlib.sha256(
        f"compose:{a['_sha256']}:{b['_sha256']}".encode()).hexdigest()
    return comp, a, b


def cmd_storyline_pack(game_file: Path, defn_path: str, value2: str,
                       json_out: bool = True) -> int:
    """包 30：本地可重建包（原创定义 + 元数据；不含游戏数据/产物）。

    包内 = 两份原创定义原文 + 工具/环境要求 + 期望（合成 patch_id /
    defn_sha256 / 语义指纹 / O7 摘要 / 执行序）。在另一独立检出解包
    重算可等价复现（验收：语义指纹与 defn_sha 逐位一致）。
    """
    try:
        comp, a, b = _load_composed(defn_path, value2)
        plan_c = _pkg().build_plan(comp, game_file)
        from . import ownership
        plan_a = _pkg().build_plan(a, game_file)
        plan_b = _pkg().build_plan(b, game_file)
        table = ownership.compare_ownership(
            ownership.extract_ownership(plan_a),
            ownership.extract_ownership(plan_b))
        if not table["mergeable"]:
            raise _pkg().StorylineError(
                "包生成拒绝：两定义不可合并——" + "; ".join(
                    f"[{c['class']}] {c['kind']}:{c['id']}"
                    for c in table["conflicts"]))
        pack = {
            "schema": "deterline.storyline-pack/v1",
            "tool_version": _pkg()._tool_version(),
            "tool_requirements": {
                "python": ">=3.13（release_check 金标口径）",
                "utmt_cli": "UndertaleModCli（dotnet 8+）",
                "cjk_deps": "Pillow + numpy（cjk 构建时）",
            },
            "composition": True,
            "definitions": {
                "a": {"filename": Path(defn_path).name,
                      "sha256": a["_sha256"],
                      "text": Path(defn_path).read_text(encoding="utf-8")},
                "b": {"filename": Path(value2).name,
                      "sha256": b["_sha256"],
                      "text": Path(value2).read_text(encoding="utf-8")},
            },
            "expected": {
                "merged_patch_id": comp["patch_id"],
                "merged_defn_sha256": comp["_sha256"],
                "semantic_sha256": plan_c["semantic_sha256"],
                "ops": [f"{o['op']}:{o['ref']}" for o in plan_c["ops"]],
                "conflict_table": table["conflicts"],
            },
        }
        print(json.dumps(pack, ensure_ascii=False, indent=2))
        return 0
    except (_pkg().StorylineError, errors.DeterlineError, FileNotFoundError,
            OSError, ValueError) as exc:
        print(json.dumps({"schema": "deterline.storyline-pack/v1",
                          "error": str(exc)},
                         ensure_ascii=False, indent=2))
        return 1


def cmd_storyline_compose(game_file: Path, defn_path: str, value2: str,
                          json_out: bool = False) -> int:
    """包 26/27：组合预览（只读）——所有权冲突表 + 合成计划摘要。"""
    try:
        comp, a, b = _load_composed(defn_path, value2)
        from . import ownership
        plan_a = _pkg().build_plan(a, game_file)
        plan_b = _pkg().build_plan(b, game_file)
        table = ownership.compare_ownership(
            ownership.extract_ownership(plan_a),
            ownership.extract_ownership(plan_b))
        if table["mergeable"]:
            plan_c = _pkg().build_plan(comp, game_file)
        else:
            plan_c = None
        out = {
            "schema": "deterline.storyline-compose/v1",
            "patches": [a["patch_id"], b["patch_id"]],
            "merged_patch_id": comp["patch_id"],
            "conflicts": table["conflicts"],
            "mergeable": table["mergeable"],
            "advice": table["advice"],
            "composed_plan": (None if plan_c is None else {
                "ops": [f"{o['op']}:{o['ref']}" for o in plan_c["ops"]],
                "semantic_sha256": plan_c["semantic_sha256"],
                "defn_sha256": comp["_sha256"],
            }),
        }
        if json_out:
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            print(f"--- storyline-compose（{a['patch_id']} + {b['patch_id']}） ---")
            print(f"  可合并: {table['mergeable']}  合成 patch_id: {comp['patch_id']}")
            for c in table["conflicts"]:
                print(f"  [{c['class']}] {c['kind']}:{c['id']}")
            if table.get("advice"):
                print(f"  建议: {table['advice']}")
            if plan_c is not None:
                print("  合成执行序:")
                for op in plan_c["ops"]:
                    print(f"    - {op['op']}:{op['ref']}")
                print(f"  合成语义指纹: {plan_c['semantic_sha256'][:16]}…")
                print(f"  合成 defn_sha256: {comp['_sha256'][:16]}…")
        return 0 if table["mergeable"] else 1
    except (_pkg().StorylineError, errors.DeterlineError, FileNotFoundError,
            OSError, ValueError) as exc:
        if json_out:
            print(json.dumps({"schema": "deterline.storyline-compose/v1",
                              "error": str(exc)},
                             ensure_ascii=False, indent=2))
        else:
            print(f"✗ storyline-compose 拒绝: {exc}", file=sys.stderr)
        return 1


def cmd_storyline_plan(game_file: Path, defn_path: str, json_out: bool = False) -> int:
    """只读计划：定义 → 计划 JSON（零写盘）。"""
    try:
        defn = _pkg().load_definition(Path(defn_path))
        plan = _pkg().build_plan(defn, game_file)
    except (_pkg().StorylineError, errors.DeterlineError, FileNotFoundError,
            OSError, ValueError) as exc:
        # ValueError 覆盖 yaml_min.YamlMinError（YAML 层解析拒绝）——JSON
        # 模式错误形态对 v1/v2 一致（包 10 合同：JSON 与实际退出码一致）。
        if json_out:
            print(json.dumps({"schema": _pkg().PLAN_SCHEMA, "error": str(exc)},
                             ensure_ascii=False, indent=2))
        else:
            print(f"✗ storyline-plan 拒绝: {exc}", file=sys.stderr)
        return 1
    if plan.get("version") == "v2":
        # v2 只读计划（包 10）：结构化 human 输出与 JSON 同源互证
        if json_out:
            print(json.dumps(plan, ensure_ascii=False, indent=2))
        else:
            print(f"--- storyline-plan v2（{plan['patch_id']}） ---")
            for alias, r in plan["rooms"].items():
                note = f"（{r['note']}）" if "note" in r else ""
                print(f"  房间 {alias}: {r['name']} (idx {r['idx']}){note}")
            for oid, n in plan["npcs"].items():
                kind = "choice" if n["choice"] else "talk"
                print(f"  NPC {oid}: {n['object']} @({n['x']},{n['y']}) "
                      f"in {n['room']} [{kind}] once={n['once']} "
                      f"create={n['create_mode']}")
            for oid, d in plan["doors"].items():
                print(f"  门 {oid}: {d['from']['name']} → {d['to']['name']} "
                      f"door@({d['x']},{d['y']}) "
                      f"spawn@({d['spawn_x']},{d['spawn_y']})")
            print("  执行序:")
            for op in plan["ops"]:
                print(f"    - {op['op']}:{op['ref']}")
            if "states" in plan:
                st = plan["states"]
                print(f"  状态机: initial={st['initial']} "
                      f"persistence={st['persistence']}")
                for s in st["declared"]:
                    desc = f"    {s['id']}"
                    if "enter" in s:
                        e = s["enter"]
                        desc += f" ← npc={e['npc']}"
                        if "answer" in e:
                            desc += f" answer={e['answer']}"
                    if "require" in s:
                        desc += f" require={s['require']}"
                    if "code" in s:
                        desc += f" code={s['code']}"
                    print(desc)
                if "flag_encoding" in st:
                    print(f"    旗标投影: flag[{st['flag_encoding']['flag_id']}]"
                          f" codes={st['flag_encoding']['codes']}")
            print(f"  语义指纹: {plan['semantic_sha256'][:16]}…")
            for d in plan["diagnostics"]:
                print(f"  ℹ️  {d}")
            for u in plan["unverified"]:
                print(f"  ⏳ 未验证: {u}")
        return 0
    if json_out:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print(f"--- storyline-plan（{plan['patch_id']}） ---")
        print(f"  房间: {plan['room']['name']} (idx {plan['room']['idx']})")
        print(f"  对象: {plan['npc']['object']}（native={plan['npc']['native']}，"
              f"code {plan['npc']['step_code'] or '(新建 Step_0)'}）")
        print(f"  期望资源: {plan['expected_resources']}")
        for d in plan["diagnostics"]:
            print(f"  ℹ️  {d}")
    return 0


def _parse_diff_categories(diff_output: str) -> dict:
    """解析 O7 --detail 输出（R14 P1-1 对齐真实形态）。

    **资源级汇总行**（verify.py 资源级段：全量计数，非 [:10] 截断明细）：
      字符串: N 处变化… / 实例: add=N remove=N move=N /
      代码指纹: changed=N added=N removed=N / 字体: changed=N added=N removed=N
    另收 STR 明细行的 op 序列（add/change/remove——干净构建应全为 add）。

    **结构段**（F1：此前未入闸门，结构漂移仅经 CODEF/INST 间接可见）：
      COUNT <K>: va → vb［（--expected 类别推导，允许）后缀可有可无］
      VARDETERLINE: [A 侧列表] → [B 侧列表]（缺行 = 两侧一致）
      ROOM inst <名>: inst=a → inst=b / ROOM 移除: 名 / ROOM 新增: 名 /
      ROOM 变化: 名: (…) → (…)（inst 计数外的分量变化）
      CODE 移除: 名 / CODE 新增: 名 (instr=N)［后缀可有可无］ /
      CODE 变化: 名: instr a → b［后缀可有可无］
    返回 {"counts", "str_ops", "struct"}——不设白名单：解析层漏看 = 假绿
    （C3 验收口径）。"""
    counts: dict[str, int] = {}
    str_ops: list[str] = []
    struct: dict = {
        "count_deltas": {},          # K: vb - va
        "vardeterline": None,        # (A 侧列表, B 侧列表)；None = 缺行（两侧一致）
        "room_inst": {},             # 名: Δinst
        "room_removed": [], "room_added": [], "room_changed": [],
        "code_removed": [], "code_added": [], "code_changed": [],
        "unclassified": [],          # G1 金丝雀：结构段家族行形漂移/未知类别
    }
    import re as _re
    import ast as _ast
    for line in diff_output.splitlines():
        s = line.strip()
        m = _re.match(r"^字符串:\s*(\d+)\s*处变化", s)
        if m:
            counts["STR total"] = int(m.group(1))
            continue
        m = _re.match(r"^实例:\s*add=(\d+)\s*remove=(\d+)\s*move=(\d+)", s)
        if m:
            counts["INST add"], counts["INST remove"], counts["INST move"] = \
                int(m.group(1)), int(m.group(2)), int(m.group(3))
            continue
        m = _re.match(r"^代码指纹:\s*changed=(\d+)\s*added=(\d+)\s*removed=(\d+)", s)
        if m:
            counts["CODEF changed"], counts["CODEF added"], counts["CODEF removed"] = \
                int(m.group(1)), int(m.group(2)), int(m.group(3))
            continue
        m = _re.match(r"^字体:\s*changed=(\d+)\s*added=(\d+)\s*removed=(\d+)", s)
        if m:
            counts["FONT changed"], counts["FONT added"], counts["FONT removed"] = \
                int(m.group(1)), int(m.group(2)), int(m.group(3))
            continue
        m = _re.match(r"^STR (add|change|remove)\b", s)
        if m:
            str_ops.append(m.group(1))
            continue
        # ---- 结构段（F1）----
        m = _re.match(r"^COUNT (\w+): (-?\d+) → (-?\d+)", s)
        if m:
            struct["count_deltas"][m.group(1)] = int(m.group(3)) - int(m.group(2))
            continue
        m = _re.match(r"^VARDETERLINE: (\[.*\]) → (\[.*\])$", s)
        if m:
            try:
                struct["vardeterline"] = (_ast.literal_eval(m.group(1)),
                                          _ast.literal_eval(m.group(2)))
            except (ValueError, SyntaxError, MemoryError, RecursionError):
                # R15 P3-1（R19 P3-3 补 RecursionError）：畸形 repr（理论
                # 形态——var 名含 "] → " 等）→ 显式畸形标记，闸门按不可解析
                # 拒绝（fail-closed 非裸栈）
                struct["vardeterline"] = (["<unparseable>"], ["<unparseable>"])
            continue
        m = _re.match(r"^ROOM 移除: (.+)$", s)
        if m:
            struct["room_removed"].append(m.group(1))
            continue
        m = _re.match(r"^ROOM 新增: (.+)$", s)
        if m:
            struct["room_added"].append(m.group(1))
            continue
        m = _re.match(r"^ROOM 变化: (.+?): ", s)
        if m:
            struct["room_changed"].append(m.group(1))
            continue
        m = _re.match(r"^ROOM inst (.+): inst=(\d+) → inst=(\d+)", s)
        if m:
            struct["room_inst"][m.group(1)] = int(m.group(3)) - int(m.group(2))
            continue
        m = _re.match(r"^CODE 移除: (.+)$", s)
        if m:
            struct["code_removed"].append(m.group(1))
            continue
        m = _re.match(r"^CODE 新增: (\S+) \(instr=(\d+)\)", s)
        if m:
            struct["code_added"].append(m.group(1))
            continue
        m = _re.match(r"^CODE 变化: (\S+): instr (-?\d+) → (-?\d+)", s)
        if m:
            struct["code_changed"].append(m.group(1))
            continue
        # G1 金丝雀（R15 P3-2）：结构段家族前缀 + 2 空格缩进（verify.py 结构
        # 行的统一形态）但未被任何已知正则消费 = verify.py 行形漂移或未知
        # 差异类别——显式拒绝（解析层漏看 = 假绿）。4 空格缩进的资源级明细
        # 行（STR/CODEF/INST move 等）不属结构段，不触发。
        if _re.match(r"^  (COUNT |VARDETERLINE:|ROOM |CODE )", line):
            struct["unclassified"].append(s)
    return {"counts": counts, "str_ops": str_ops, "struct": struct}


def _check_structure(parsed: dict, plan: dict) -> list[str]:
    """结构段比对（F1）：解析出的结构差异 vs plan.expected_structure——
    全类别严格相等（含期望为空而实测非空的形态）。返回未声明清单（空=过）。"""
    st = parsed["struct"]
    exp = plan["expected_structure"]
    out: list[str] = []
    for line in st["unclassified"]:
        out.append(f"未识别结构行（verify.py 行形漂移/未知类别——闸门不猜）: {line}")
    for k in sorted(set(st["count_deltas"]) | set(exp["count_deltas"])):
        got = st["count_deltas"].get(k, 0)
        want = exp["count_deltas"].get(k, 0)
        if got != want:
            out.append(f"COUNT {k} 变化 {got}（声明 {want}）")
    va, vb = st["vardeterline"] if st["vardeterline"] is not None else ([], [])
    if "<unparseable>" in va or "<unparseable>" in vb:
        # R19 P3-2：解析器畸形标记专用消息——否则会被"基线已含"分支吃掉，
        # 把解析失败误诊为"基线不干净"并给出无效补救
        out.append("VARDETERLINE 行不可解析（repr 畸形——verify.py 输出形态"
                   "漂移或字段含分隔符）——闸门不猜，请核对该文件 diff 输出")
        return out
    if va:
        out.append(f"基线已含 deterline* 变量 {va}——v1 合同以干净基线为目标"
                   "（先 undo/换干净副本再构建）")
    else:
        if len(vb) != 1:
            out.append(f"VARDETERLINE 新增 {len(vb)} 条（声明恰 1 条 "
                       f"{exp['var_added']}）: {vb}")
        else:
            try:
                name, nsid, occ = vb[0].rsplit(":", 2)
            except ValueError:
                out.append(f"VARDETERLINE 条目形状不符（name:nsid:occ）: {vb[0]!r}")
                name = nsid = occ = None
            if name is not None:
                if name != exp["var_added"]:
                    out.append(f"VARDETERLINE 新增变量 {name!r}（声明 "
                               f"{exp['var_added']!r}）")
                if str(nsid) == "0":
                    out.append(f"VARDETERLINE {name} NameStringID=0"
                               "（NSID=0 崩溃根因——Create_0 初始化未生效？）")
                if occ is None or not occ.isdigit() or int(occ) < 1:
                    out.append(f"VARDETERLINE {name} Occurrences={occ!r}"
                               "（须 ≥1——变量未被任何代码引用）")
    for name in st["room_removed"]:
        out.append(f"ROOM 移除: {name}")
    for name in st["room_added"]:
        out.append(f"ROOM 新增: {name}")
    for name in st["room_changed"]:
        out.append(f"ROOM 尺寸/tile/背景层变化: {name}")
    for name in sorted(set(st["room_inst"]) | set(exp["room_inst"])):
        got = st["room_inst"].get(name, 0)
        want = exp["room_inst"].get(name, 0)
        if got != want:
            out.append(f"ROOM inst {name} 变化 {got}（声明 {want}）")
    if sorted(st["code_added"]) != exp["code_added"]:
        out.append(f"CODE 新增 {sorted(st['code_added'])}"
                   f"（声明 {exp['code_added']}）")
    if st["code_removed"]:
        out.append(f"CODE 移除 {st['code_removed']}（声明无）")
    if sorted(st["code_changed"]) != exp["code_changed"]:
        out.append(f"CODE 指令数变化 {sorted(st['code_changed'])}"
                   f"（声明 {exp['code_changed']}）")
    return out


def _expected_categories(plan: dict) -> dict:
    """计划期望 → 允许的 O7 汇总计数集合（与 _parse_diff_categories 同键）。
    期望外的任何类别计数不等即拒绝（含期望为 0 而实测非 0 的形态——
    R14 P1-1：变更/删除/移动/字体类别全部进闸门）。
    注意：contract 的 code_changed **已含** Alarm 守卫（+native 时）——
    此处不再叠加（R13 P1-3 双计修正：曾放行一条未声明代码改动）。"""
    er = plan["expected_resources"]
    return {
        "STR total": er["str_total"],
        "INST add": er["inst_adds"], "INST remove": 0, "INST move": 0,
        "CODEF changed": er["code_changed"],
        "CODEF added": er["code_added"], "CODEF removed": 0,
        # CJK 组合声明 FONT changed 1（fnt_ja_maintext 字形表重指 + 共享表
        # 扩容）；ASCII 构建 font_changed 0 = 字体一票拒绝（R14 P1-1 口径）
        "FONT changed": er.get("font_changed", 0),
        "FONT added": 0, "FONT removed": 0,
    }


def _validate_workspace_name(workspace: str) -> None:
    """P2-4：工作区名白名单——防 `../evil` / 分隔符注入把工作区/manifest
    建到 `.deterline` 之外（API 直调可达，CLI 层 --workspace 同参）。"""
    import re as _re
    if not isinstance(workspace, str) \
            or not _re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", workspace):
        raise _pkg().StorylineError(
            f"工作区名须匹配 [a-z0-9][a-z0-9_-]{{0,63}}（收到 {workspace!r}）")


def _run_cjk_font_pipeline(game_file: Path, chars: list) -> None:
    """F4 中文组合（包 15：字形集由**调用方**按全定义文本一次汇总——
    v1 = 单 npc 三字段；v2 = 全部 npc 的 prompt/yes/no 汇总）。
    字形页预处理 + 五步字体管线（pass1/pass2 经外层 game_edit 批量写入
    当前工作区）。最小集，确定性：同定义 → 同字形集 → 同产物。

    字形页生成器以**进程内**方式调用（runpy 加载 tools/font_cjk_build.py
    → main() + sys.argv patch——与测试层同款进程内形态；subprocess+
    sys.executable 写法被本机安全扫描误报高危，登记）。
    """
    import contextlib as _ctx
    import io as _io
    import runpy as _runpy
    import sys as _sys
    import tempfile as _tmp
    from pathlib import Path as _Path
    from unittest import mock as _mock
    from ..cmds import cjk as _cjk

    repo_root = _Path(__file__).resolve().parents[3]  # storyline CJK 字形页/字体源
    font_src = (repo_root / "assets" / "fonts" / "vendor" /
                "fusion-pixel-12px" / "fusion-pixel-12px-monospaced-zh_hans.ttf")
    tool = repo_root / "tools" / "font_cjk_build.py"
    if not font_src.is_file():
        raise _pkg().StorylineError(f"OFL 字体源缺失: {font_src}")
    if not tool.is_file():
        raise _pkg().StorylineError(f"字形页生成器缺失: {tool}")
    with _tmp.TemporaryDirectory(prefix="deterline_cjk_") as td:
        chars_file = _Path(td) / "chars.txt"
        chars_file.write_text("".join(chars), encoding="utf-8")
        build_dir = _Path(td) / "font_build"
        work_dir = _Path(td) / "cjk_work"
        out, err = _io.StringIO(), _io.StringIO()
        try:
            # R19/R20 P2：run_path 必须在 try 内——工具的 `from PIL import …`
            # 在模块顶层，run_path 执行它；缺 Pillow 时 ImportError 从这里
            # 抛出（此前该 except 是死代码，承诺的行动指南不可达）
            tool_ns = _runpy.run_path(str(tool), run_name="deterline_font_build")
            with _mock.patch.object(_sys, "argv",
                                    ["font_cjk_build.py", "--font", str(font_src),
                                     "--only", str(chars_file),
                                     "--out-dir", str(build_dir)]), \
                    _ctx.redirect_stdout(out), _ctx.redirect_stderr(err):
                rc = tool_ns["main"]()
        except SystemExit as exc:
            # R15 P2：argparse 参数拒绝以 SystemExit(2) 呈现——错误文本已进
            # redirect 缓冲，必须带出（否则用户只见静默失败无诊断）
            rc = exc.code if isinstance(exc.code, int) else 1
            err.write(f"\n[SystemExit {exc.code}]")
        except ImportError as exc:
            rc = 1
            err.write(f"\n[ImportError] {exc}（Pillow 缺失？"
                      "python3 -m pip install pillow）")
        if rc != 0:
            raise _pkg().StorylineError(
                "字形页构建失败（font_cjk_build）:\n"
                + (out.getvalue() + err.getvalue())[-2000:])
        ok = _cjk.cmd_cjk_font(game_file, build_dir, work_dir=work_dir)
        if not ok:
            raise _pkg().StorylineError(
                "scr_setfont 字体栈注入后体检未过（域F 协议）——中止，"
                "工作区不产出候选")


def _categories_from_structured(structured: dict) -> dict:
    """包 21：结构化 O7 → 旧口径 parsed（counts/str_ops/struct）。

    回执字段与既有消费者（闸门/收据 declared_diff/declared_structure）
    形状不变；差异来源从文本解析切到结构化结果——类别计数相同而对象
    不同由 _v2_declared_assertions 逐对象识别。
    """
    counts: dict[str, int] = {}
    if "STRGCOUNT" in structured["counts"]:
        counts["STR total"] = structured["counts"]["STRGCOUNT"]["delta"]
    counts["INST add"] = len(structured["instances"]["added"])
    counts["INST remove"] = len(structured["instances"]["removed"])
    counts["INST move"] = len(structured["instances"]["moved"])
    counts["CODEF changed"] = len(structured["code"]["changed"])
    counts["CODEF added"] = len(structured["code"]["added"])
    counts["CODEF removed"] = len(structured["code"]["removed"])
    counts["FONT changed"] = len(structured["fonts"]["changed"])
    counts["FONT added"] = len(structured["fonts"]["added"])
    counts["FONT removed"] = len(structured["fonts"]["removed"])
    vd = structured["vardeterline"]
    struct = {
        "count_deltas": {k: v["delta"] for k, v in
                         structured["counts"].items()},
        "vardeterline": (vd["a"], vd["b"]) if vd["a"] != vd["b"] else None,
        "room_inst": dict(structured["rooms"]["inst_delta"]),
        "room_removed": list(structured["rooms"]["removed"]),
        "room_added": list(structured["rooms"]["added"]),
        "room_changed": sorted(structured["rooms"]["changed"]),
        "code_removed": list(structured["code"]["removed"]),
        "code_added": list(structured["code"]["added"]),
        "code_changed": list(structured["code"]["changed"]),
        "unclassified": [],
    }
    return {"counts": counts,
            "str_ops": [op for op, _e in structured["strings"]["ops"]],
            "struct": struct}


def _correlate_ops(plan: dict, op_evidence: list[dict],
                   structured: dict, defn: dict) -> list[dict]:
    """包 22：逐 op 的产物对应证据（计划变更 → 实例行 + 代码条目）。

    每个 npc/door op 必须在结构化 O7 的新增实例集合中恰有一行
    (room, object, x, y)（一对一，按集合扣除匹配；缺失/重复即拒绝）
    ——"每项计划变更在产物上有对应证据"由本函数落进回执 ops_evidence。
    代码条目按对象/模板前缀归属（npc 对象 Step/Create/Alarm；door
    模板 + door_back 脚本）。
    """
    from collections import defaultdict as _dd
    rows = [tuple(r) for r in structured["instances"]["added"]]
    by_key: dict[tuple, list[int]] = _dd(list)
    for i, (room, _iid, obj, x, y) in enumerate(rows):
        by_key[(room, obj, x, y)].append(i)
    used: set[int] = set()
    out: list[dict] = []
    npc_objs = {n["object"] for n in plan["npcs"].values()}
    code_names = (structured["code"]["added"]
                  + structured["code"]["changed"])
    for op in op_evidence:
        ev = dict(op)
        if op["op"] == "npc":
            n = plan["npcs"][op["ref"]]
            key = (op["room"], op["object"], n["x"], n["y"])
        else:
            d = plan["doors"][op["ref"]]
            key = (d["from"]["name"], "obj_deterline_door", d["x"], d["y"])
        cand = [i for i in by_key.get(key, []) if i not in used]
        if not cand:
            raise _pkg().StorylineError(
                f"包 22 对应证据缺失：op {op['op']}:{op['ref']} 在产物新增"
                f"实例中无匹配行 {key}——计划变更与产物不对应，拒绝出候选")
        idx = cand[0]
        used.add(idx)
        room, iid, obj, x, y = rows[idx]
        ev["o7_instance"] = {"room": room, "instance_id": iid,
                             "object": obj, "x": x, "y": y}
        if op["op"] == "npc":
            ev["o7_code"] = sorted(
                nm for nm in code_names
                if nm.startswith(f"gml_Object_{op['object']}_"))
        else:
            ev["o7_code"] = sorted(
                nm for nm in code_names
                if nm.startswith("gml_Object_obj_deterline_door_")
                or nm == "gml_Script_deterline_door_back")
        out.append(ev)
    return out


def _validate_build_receipt_meta(build_rcpt: dict, defn: dict) -> None:
    """包 22：构建回执元数据版本校验（apply 写前拒绝路径之一）。

    schema 必须与定义版本匹配（v1 ↔ BUILD_SCHEMA；v2 ↔ BUILD_SCHEMA_V2）
    且必需关联字段齐全——版本/元数据不匹配拒绝，绝不按猜测应用。
    """
    want = (_pkg().BUILD_SCHEMA_V2
            if defn.get("_version") == "v2" else _pkg().BUILD_SCHEMA)
    schema = build_rcpt.get("schema")
    if schema != want:
        raise _pkg().StorylineError(
            f"构建回执元数据版本不匹配：schema={schema!r}（定义版本 "
            f"{defn.get('_version')} 需要 {want}）——重新 storyline-build")
    missing = [k for k in ("patch_id", "defn_sha256", "baseline_sha256",
                           "product", "product_sha256", "tool_version")
               if k not in build_rcpt]
    if missing:
        raise _pkg().StorylineError(
            f"构建回执缺关联字段: {missing}——回执不完整，重新 storyline-build")
    if build_rcpt.get("patch_id") != defn.get("patch_id"):
        raise _pkg().StorylineError(
            f"构建回执 patch_id 不符: {build_rcpt.get('patch_id')!r} vs "
            f"{defn.get('patch_id')!r}——重新 storyline-build")


def _v2_declared_assertions(structured: dict, defn: dict,
                            plan: dict) -> list[str]:
    """包 21：v2 声明的逐对象断言（纯函数——结构化 O7 结果 → 拒绝清单）。

    **类别计数相同而对象不同**在此识别：实例集合按 (room, object, x, y)
    逐项比对；代码条目按名称白名单（样例模板实证集）逐条比对；字符串按
    声明键/内容的 (len, sha1) 签名逐项比对。cjk 构建的文本内容经预折行
    改写（内容签名不可预计算）——内容断言仅 ASCII 构建，键名恒断言
    （登记口径）。空返回 = 全部声明变化在产物上有对应证据。
    """
    import hashlib as _hashlib
    refusals: list[str] = []
    npcs = defn.get("npcs") or {}

    def _sig(text: str) -> tuple:
        raw = text.encode("utf-8")
        return (len(raw), _hashlib.sha1(raw).hexdigest())

    # —— 字符串：声明键（恒）+ 内容（非 cjk）必须出现在 added 集合 ——
    added_str = {(e[0], e[1]) for op, e in
                 ((op, entry) for op, entry in structured["strings"]["ops"])
                 if op == "add"}
    declared_str: dict[str, tuple] = {}
    for ref, spec in npcs.items():
        suffix = ("_choice", "_yes", "_no") if "\\C" in spec["prompt"] else ("",)
        for sfx in suffix:
            key = f"det_{defn['patch_id']}_{ref}{sfx}"
            declared_str[key] = _sig(key)
        if not defn.get("cjk"):
            declared_str[f"{ref}.prompt"] = _sig(spec["prompt"])
            if "\\C" in spec["prompt"]:
                declared_str[f"{ref}.yes_text"] = _sig(spec["yes_text"])
                declared_str[f"{ref}.no_text"] = _sig(spec["no_text"])
    for label, sig in sorted(declared_str.items()):
        if sig not in added_str:
            refusals.append(
                f"STR 声明签名缺失: {label}（len={sig[0]} "
                f"sha1={sig[1][:12]}…）——产物字符串与声明不符")

    # —— 实例：集合精确比对（npc 房间内实例 + door 门实例） ——
    expected_inst: list[tuple] = []
    for op in plan["ops"]:
        if op["op"] == "npc":
            n = op["npc"]
            expected_inst.append((plan["rooms"][n["room"]]["name"],
                                  n["object"], n["x"], n["y"]))
        else:
            d = op["door"]
            expected_inst.append((d["from"]["name"], "obj_deterline_door",
                                  d["x"], d["y"]))
    actual_added = [tuple(row) for row in
                    structured["instances"]["added"]]
    from collections import Counter as _Counter
    exp_c = _Counter(expected_inst)
    act_c = _Counter((room, obj, x, y) for room, _id, obj, x, y
                     in actual_added)
    for row, n in (act_c - exp_c).items():
        refusals.append(f"INST 未声明新增: {(row, n)}（(room, object, x, y) "
                        "逐项比对）")
    for row, n in (exp_c - act_c).items():
        refusals.append(f"INST 声明实例缺失: {(row, n)}——产物与计划不符")
    for op in ("removed", "moved"):
        if structured["instances"][op]:
            refusals.append(f"INST {op} 非空: "
                            f"{structured['instances'][op][:4]}")

    # —— 代码：名称白名单（样例模板实证集）+ 逐条归属 ——
    npc_objs = {n["object"] for n in plan["npcs"].values()}
    allowed_patterns = [
        re.compile(r"gml_Object_(" + "|".join(
            re.escape(o) for o in sorted(npc_objs))
            + r")_(Step_0|Create_0|Alarm_0)") if npc_objs else None,
        re.compile(r"gml_Object_obj_deterline_door_\w+"),
        re.compile(r"gml_Script_deterline_door_back"),
        re.compile(r"gml_Script_textdata_en"),
    ]
    if defn.get("cjk"):
        allowed_patterns += [
            re.compile(r"gml_Script_scr_setfont"),
            re.compile(r"gml_Script_scr_preload_textures"),
        ]
    allowed = [p for p in allowed_patterns if p is not None]
    for kind in ("added", "changed"):
        for name in structured["code"][kind]:
            if not any(p.fullmatch(name) for p in allowed):
                refusals.append(
                    f"CODE {kind} 未声明条目: {name}（名称不匹配任何计划"
                    "对象/脚本白名单）")
    if structured["code"]["removed"]:
        refusals.append(f"CODE removed 非空: {structured['code']['removed'][:4]}")

    # —— 字体：cjk ⇒ 恰 fnt_ja_maintext changed；否则全空 ——
    fonts = structured["fonts"]
    if defn.get("cjk"):
        if fonts["changed"] != ["fnt_ja_maintext"] or fonts["added"] \
                or fonts["removed"]:
            refusals.append(f"FONT 变更不符声明: {fonts}")
    elif fonts["changed"] or fonts["added"] or fonts["removed"]:
        refusals.append(f"FONT 非声明构建不得变化: {fonts}")

    # —— 房间：无增删/尺寸/瓦片/背景变化；inst 增量 = 计划逐房 op 计数 ——
    rooms = structured["rooms"]
    if rooms["removed"] or rooms["added"]:
        refusals.append(
            f"ROOM 增删非声明: removed={rooms['removed']} "
            f"added={rooms['added']}")
    exp_inst_delta: dict[str, int] = {}
    for op in plan["ops"]:
        if op["op"] == "npc":
            rn = plan["rooms"][op["npc"]["room"]]["name"]
        else:
            rn = op["door"]["from"]["name"]
        exp_inst_delta[rn] = exp_inst_delta.get(rn, 0) + 1
    for name, delta in sorted(rooms["inst_delta"].items()):
        if exp_inst_delta.get(name) != delta:
            refusals.append(
                f"ROOM inst {name}: Δ{delta} ≠ 计划 op 计数 "
                f"{exp_inst_delta.get(name, 0)}")
    for name, pair in sorted(rooms["changed"].items()):
        a, b = pair["a"], pair["b"]
        if (a[0], a[2], a[3]) != (b[0], b[2], b[3]):
            refusals.append(
                f"ROOM 变化: {name}: {a} → {b}（inst 计数外的分量变化）")
    return refusals


def resolve_flag_writes(defn: dict) -> list[dict]:
    """包 18：解析 --flag-write 接线点（纯函数，fail-closed）。

    载体 = 定义声明的 flag_id（会话级运行时旗标——包 17 普查：本基线
    无净空持久旗标槽，存档持久接线拒绝；运行时空带 513-999）。
    写入点 = talk npc 触发（对话框创建后无条件写——2026-11-07 矩阵：
    条件门控必失效，只生成无条件形态）；选择 npc 的答案分派在
    obj_dialoguer 内部，触发点写不出答案条件值——带 code enter 的选择
    npc 整体拒绝（登记限制）。**写入不受 require 守卫门控**（守卫需
    条件读取 = 死形族；本候选是写入点探针而非状态机实现——乱序触发
    即写 code，与 QuestMachine 轨迹在乱序输入下分叉，已在
    receipt/实录/待验卡登记，R-161720 P2 清偿口径）。返回
    [{"npc","state","code","require","line"}]。
    """
    st = defn.get("states")
    if not st:
        raise _pkg().StorylineError(
            "--flag-write 需要定义声明 states 块（无可接线写入点）")
    fid = defn.get("flag_id")
    if not fid:
        raise _pkg().StorylineError(
            "--flag-write 需要定义声明 flag_id（运行时载体槽）")
    from . import projection
    occ = projection.check_flag_occupancy(fid)
    if occ:
        raise _pkg().StorylineError(
            f"--flag-write 拒绝：flag {fid} 被游戏代码占用 {occ[:4]}"
            "（占用普查，包 17）——接线前请换旗标")
    if st["persistence"] == "flag":
        raise _pkg().StorylineError(
            "--flag-write 拒绝 persistence=flag：本基线持久区 500-511 "
            "全被游戏代码占用（包 17 普查）——无净空持久槽，存档持久"
            "接线不可交付；运行时载体仅支持 persistence=session")
    smap = st["map"]
    per_npc: dict[str, list[tuple[str, int]]] = {}
    for sid in sorted(smap):
        ent = smap[sid].get("enter")
        if ent and "code" in smap[sid]:
            per_npc.setdefault(ent["npc"], []).append((sid, smap[sid]["code"]))
    writes: list[dict] = []
    refused: list[str] = []
    for oid, spec in sorted((defn.get("npcs") or {}).items()):
        coded = per_npc.get(oid) or []
        if not coded:
            continue
        if "\\C" in spec["prompt"]:
            refused.append(f"npcs.{oid}（states.{sorted(s for s, _ in coded)}）")
            continue
        if len(coded) > 1:
            raise _pkg().StorylineError(
                f"--flag-write 拒绝：npcs.{oid} 有多个 code enter "
                f"{sorted(s for s, _ in coded)}——触发点无法按当前态分派"
                "（产物无状态读取），编码歧义拒绝")
        sid, code_val = coded[0]
        writes.append({"npc": oid, "state": sid, "code": code_val,
                       "require": smap[sid].get("require"),
                       "line": f"global.flag[{fid}] = {code_val};"})
    if refused:
        raise _pkg().StorylineError(
            "--flag-write 拒绝：选择 npc 的 code enter 不可接线（答案分派"
            f"在 obj_dialoguer 内部——触发点写不出答案条件值）: "
            + ", ".join(refused))
    if not writes:
        raise _pkg().StorylineError(
            "--flag-write 无可接线写入点（没有带 code 的 talk npc enter）"
            "——为 talk npc 的状态声明 code 或移除 --flag-write")
    return writes


def _build_v2(defn: dict, plan: dict, game_file: Path, workspace: str,
              base_sha: str, json_out: bool, flag_write: bool = False,
              view_track: bool = False) -> int:
    """包 12–15：v2 构建链——按 op 序接领域生成器进有名工作区。

    - npc op → cmd_npc_choice（含 \\C）/ cmd_npc_dialogue（纯对话），
      文本键 `det_<patch>_<ref>[_choice|_yes|_no]`（按 patch+节点分配，
      防共享脚本重复追加——包 12 命名规则）；typer = 31(cjk)/5。
    - door op → ensure_deterline_door_object（包 13：干净基线前置，
      幂等）+ cmd_create_door（共享门对象挂分支，双向各一 op）。
    - 包 15：cjk=true 时字形集 = 全定义 npc 文本一次汇总注入。
    - 闸门（O7 不变量 + 字段指向）：STR 全 add；INST remove/move=0；
      CODEF removed=0；FONT changed==cjk?1:0；INST add == npc op 数 +
      door op 数（每个 op 恰生成 1 实例）。多 op 组成的精确计数推导
      （对象共享变量/门对象首建）不进总数闸门——以 per-op 证据回执。
    """
    try:
        from .. import state, utmt
        from ..cmds import npc as npc_mod, door as door_mod
        prospective = (game_file.parent / ".deterline" / game_file.name /
                       workspace / game_file.name)
        if prospective.is_symlink():
            raise _pkg().StorylineError(
                f"工作区产物路径是符号链接（{prospective}）——拒绝")
        if prospective.is_file() \
                and transactions.fingerprint(prospective) != base_sha:
            raise _pkg().StorylineError(
                f"工作区 {workspace} 已存在**已补丁**产物（sha ≠ 当前基线）"
                "——构建是单次语义：换新工作区名或清除残留")
        old_ws, old_sbx = state.WORKSPACE, state.SANDBOX_ACTIVE
        old_cjk = state.ALLOW_CJK
        state.WORKSPACE = workspace
        state.SANDBOX_ACTIVE = True
        op_evidence: list[dict] = []
        flag_writes = resolve_flag_writes(defn) if flag_write else None
        write_by_npc = {w["npc"]: w for w in (flag_writes or [])}
        try:
            with utmt.game_edit("storyline-build-v2", read_workspace=False):
                if defn.get("cjk"):
                    state.ALLOW_CJK = True
                    chars = sorted({ch for spec in (defn.get("npcs") or {})
                                    .values()
                                    for ch in (spec.get("prompt", "")
                                               + spec.get("yes_text", "")
                                               + spec.get("no_text", ""))
                                    if ch not in "\r\n\t"})
                    _run_cjk_font_pipeline(game_file, chars)
                for op in plan["ops"]:
                    if op["op"] == "npc":
                        n = op["npc"]
                        spec = (defn.get("npcs") or {})[op["ref"]]
                        room_name = plan["rooms"][n["room"]]["name"]
                        typer = 31 if defn.get("cjk") else 5
                        if n["choice"]:
                            npc_mod.cmd_npc_choice(
                                game_file, room_name, spec["object"],
                                spec["x"], spec["y"],
                                f"det_{defn['patch_id']}_{op['ref']}_choice",
                                spec["prompt"],
                                yes_key=(f"det_{defn['patch_id']}"
                                         f"_{op['ref']}_yes"),
                                yes_text=spec["yes_text"],
                                no_key=(f"det_{defn['patch_id']}"
                                        f"_{op['ref']}_no"),
                                no_text=spec["no_text"],
                                face=0, emotion=0,
                                range_=spec.get("range", 60),
                                repeat=not spec.get("once", True),
                                typer=typer, view_track=view_track)
                            keys = [f"det_{defn['patch_id']}_{op['ref']}_choice",
                                    f"det_{defn['patch_id']}_{op['ref']}_yes",
                                    f"det_{defn['patch_id']}_{op['ref']}_no"]
                        else:
                            fw = write_by_npc.get(op["ref"])
                            npc_mod.cmd_npc_dialogue(
                                game_file, room_name, spec["object"],
                                spec["x"], spec["y"],
                                f"det_{defn['patch_id']}_{op['ref']}",
                                spec["prompt"], face=0, emotion=0,
                                range_=spec.get("range", 60),
                                once=spec.get("once", True),
                                typer=typer,
                                flag_write_line=(fw["line"] if fw else None),
                                view_track=view_track)
                            keys = [f"det_{defn['patch_id']}_{op['ref']}"]
                        op_evidence.append({"op": "npc", "ref": op["ref"],
                                            "room": room_name,
                                            "object": n["object"],
                                            "text_keys": keys,
                                            "typer": typer,
                                            **({"flag_write": write_by_npc[op["ref"]]}
                                               if op["ref"] in write_by_npc else {})})
                    else:
                        d = op["door"]
                        if op["op"] not in ("npc", "door"):
                            raise _pkg().StorylineError(
                                f"未知 op 类型: {op['op']}（V2_ORDER_KINDS "
                                "之外的 kind 不进构建——合同层应已拒绝）")
                        # ensure 幂等（R-1215：per-op 记录实际值，不缓存失真）
                        door_ready = door_mod.ensure_deterline_door_object(
                            game_file)
                        door_mod.cmd_create_door(
                            game_file, d["from"]["name"], d["to"]["name"],
                            d["x"], d["y"], d["spawn_x"], d["spawn_y"])
                        op_evidence.append({"op": "door", "ref": op["ref"],
                                            "from": d["from"]["name"],
                                            "to": d["to"]["name"],
                                            "door_object": door_ready})
        finally:
            state.WORKSPACE, state.SANDBOX_ACTIVE = old_ws, old_sbx
            state.ALLOW_CJK = old_cjk
        product = (game_file.parent / ".deterline" / game_file.name /
                   workspace / game_file.name)
        if not product.is_file():
            raise _pkg().StorylineError(f"工作区产物缺失: {product}")
        product_sha = transactions.fingerprint(product)
        # O7 差异采集（包 21：结构化结果直采——v2 闸门不再解析终端行
        # 文本；cmd_diff_snapshots 文本形态保留给既有使用者/显示）
        from ..cmds import verify
        structured = verify.diff_snapshots_structured(game_file, product)
        parsed = _categories_from_structured(structured)
        cats = parsed["counts"]
        n_inst = sum(1 for o in plan["ops"] if o["op"] in ("npc", "door"))
        refusals = []
        bad_ops = sorted({o for o in parsed["str_ops"] if o != "add"})
        if bad_ops:
            refusals.append(f"STR op 含非 add 形态: {','.join(bad_ops)}")
        if cats.get("INST remove", 0) or cats.get("INST move", 0):
            refusals.append("INST remove/move 非 0（实例只增不变位）")
        if cats.get("CODEF removed", 0):
            refusals.append("CODEF removed 非 0")
        font_want = 1 if defn.get("cjk") else 0
        if cats.get("FONT changed", 0) != font_want \
                or cats.get("FONT added", 0) or cats.get("FONT removed", 0):
            refusals.append(f"FONT 变更不符声明（changed {cats.get('FONT changed', 0)}"
                            f"/added {cats.get('FONT added', 0)}"
                            f"/removed {cats.get('FONT removed', 0)}，"
                            f"声明 changed {font_want}）")
        if cats.get("INST add", 0) != n_inst:
            refusals.append(
                f"INST add {cats.get('INST add', 0)}（声明 {n_inst}："
                "每个 npc/door op 恰 1 实例）")
        # 包 21：逐对象断言（计数相同而对象不同在此识别；O7 结构化）
        refusals.extend(_v2_declared_assertions(structured, defn, plan))
        # 包 22：逐 op 产物对应证据（缺失即拒绝——见 _correlate_ops）
        if not refusals:
            op_evidence = _correlate_ops(plan, op_evidence, structured, defn)
        if refusals:
            raise _pkg().StorylineError(
                "发现未声明资源/结构变更，拒绝出候选（12 §C3）: "
                + "; ".join(refusals) + f"（O7 计数: {cats}）")
        receipt = {
            "schema": _pkg().BUILD_SCHEMA_V2,
            "version": "v2",
            "patch_id": defn["patch_id"],
            "defn_sha256": defn["_sha256"],
            "semantic_sha256": plan["semantic_sha256"],
            "tool_version": plan["tool_version"],
            "baseline_sha256": base_sha,
            "target": str(game_file),
            "workspace": workspace,
            "product": str(product),
            "product_sha256": product_sha,
            "declared_diff": cats,
            "declared_str_ops": parsed["str_ops"],
            "declared_structure": parsed["struct"],
            "o7_structured": structured,
            "ops_evidence": op_evidence,
            "cjk": bool(defn.get("cjk", False)),
            "cjk_chars": (sorted({ch for spec in (defn.get("npcs") or {})
                                  .values()
                                  for ch in (spec.get("prompt", "")
                                             + spec.get("yes_text", "")
                                             + spec.get("no_text", ""))
                                  if ch not in "\r\n\t"})
                          if defn.get("cjk") else []),
            "flag": plan["flag"],
            "diagnostics": plan["diagnostics"],
            **({"flag_writes": {
                "enabled": True,
                "carrier": defn.get("flag_id"),
                "persistence": defn["states"]["persistence"],
                "ops": flag_writes,
                "scope_note": "会话级运行时载体（不入存档）；仅 talk npc "
                              "无条件写（2026-11-07 矩阵口径）；**写入不受 "
                              "require 守卫门控**——乱序触发即写 code，与模型"
                              "轨迹分叉（守卫需条件读取=死形族，本候选不实现；"
                              "R-161720 P2 登记，待验卡含乱序对照）；选择答案"
                              "分派在 dialoguer 内部不可接线（登记）；候选形态"
                              "待实机复验——待验卡见 16 实录包 18",
            }} if flag_write else {}),
            **({"view_track": {
                "enabled": True,
                "ops": [o["ref"] for o in plan["ops"] if o["op"] == "npc"],
                "scope_note": "滚屏候选方向 B（文字/红心与框同视图参考）：触发时"
                              "自校准捕获（deterline_wy/wy0）+ 逐帧跟踪；红心 = "
                              "view+55（choicer.Create_0 210−155 字节推导）；"
                              "单轴纵滚房间、同房单 npc 限定；候选形态待实机"
                              "复验——待验卡见 16 实录包 19/20",
            }} if view_track else {})}
        transactions._write_json_atomic(  # noqa: SLF001 原子写复用
            _pkg().receipt_path(game_file, defn["patch_id"]).with_name(
                "build.json"),
            receipt)
        if json_out:
            print(json.dumps(receipt, ensure_ascii=False, indent=2))
        else:
            print(f"--- storyline-build v2（{receipt['patch_id']}）候选就绪 ---")
            print(f"  工作区: {workspace}  产物 sha256 {product_sha[:16]}…")
            print(f"  op 证据: {len(op_evidence)} 项（npc {sum(1 for o in op_evidence if o['op'] == 'npc')} / door {sum(1 for o in op_evidence if o['op'] == 'door')}）")
            if flag_write:
                print(f"  flag 接线（候选，默认禁用）: flag[{defn.get('flag_id')}] "
                      f"{len(flag_writes)} 处 talk 触发写入——待实机复验")
            if view_track:
                print("  滚屏候选（--view-track）: 文字/红心与框同视图参考"
                      "（自校准捕获+逐帧跟踪）——单轴纵滚/同房单 npc 限定，"
                      "待实机复验")
            print(f"  声明差异: {cats}")
            for d in receipt["diagnostics"]:
                print(f"  ℹ️  {d}")
        return 0
    except (_pkg().StorylineError, errors.DeterlineError, FileNotFoundError,
            OSError, RuntimeError, ValueError) as exc:
        if json_out:
            print(json.dumps({"schema": _pkg().BUILD_SCHEMA_V2,
                              "error": str(exc)},
                             ensure_ascii=False, indent=2))
        else:
            print(f"✗ storyline-build v2 拒绝: {exc}", file=sys.stderr)
        return 1


def cmd_storyline_build(game_file: Path, defn_path: str, workspace: str,
                        json_out: bool = False,
                        flag_write: bool = False,
                        view_track: bool = False,
                        value2: str | None = None) -> int:
    """构建：plan → 工作区构建 → O7 差异核验 → 构建回执（仅写工作区）。
    `--preview` 不支持——构建即写工作区（EditPlan 预览不落盘会使产物
    缺失，语义冲突，R13 P3）。
    flag_write（包 18 候选，默认 False=产物与无接线构建逐字节一致）：
    开启后 talk npc 状态写入 flag_id 运行时载体——resolve_flag_writes
    fail-closed 前置（占用/持久化/选择 npc/多 code enter 拒绝）。"""
    defn = None
    try:
        from .. import state
        if state.PREVIEW:
            raise _pkg().StorylineError(
                "storyline-build 不支持 --preview（构建即写工作区；预览用 "
                "storyline-plan 或 build 后的 storyline-apply 预览）")
        _validate_workspace_name(workspace)
        game_file = Path(game_file).resolve()
        if value2:
            # 包 27/28：双补丁合成构建（同一干净基线一次构建）
            defn, _a, _b = _load_composed(defn_path, value2)
        else:
            defn = _pkg().load_definition(Path(defn_path))
        plan = _pkg().build_plan(defn, game_file)
        base_sha = transactions.fingerprint(game_file)
        if base_sha is None:
            raise errors.NotFoundError(f"基线文件不存在: {game_file}")
        if defn.get("_version") == "v2":
            # 包 12–15：v2 构建链（op 序 npc/door → 工作区；闸门不变量口径）
            # 包 18：flag_write=True 时接运行时载体写入（候选，默认禁用）
            return _build_v2(defn, plan, game_file, workspace, base_sha,
                             json_out, flag_write=flag_write,
                             view_track=view_track)
        # 域生成器构建（写入有名工作区，不触原文件）——自管 game_edit 上下文：
        # 批量提交在上下文**退出**时落盘（data_win 包装内读产物 = 基线副本，
        # C4 CLI 实测教训），指纹/O7 比对必须在其后
        prospective = (game_file.parent / ".deterline" / game_file.name /
                       workspace / game_file.name)
        if prospective.is_symlink():
            # R17 P2：产品路径链接 = 写穿链入口（ensure_workspace 复用 +
            # _resolve_write_target().resolve() 落到链接目标）——先拒。
            raise _pkg().StorylineError(
                f"工作区产物路径是符号链接（{prospective}）——拒绝"
                "（防'构建不触原文件'被写穿，A3 三道防线口径）")
        if prospective.is_file() \
                and transactions.fingerprint(prospective) != base_sha:
            # G2（R15 P3-4）：ensure_workspace 复用同名工作区旧产物 → 链式
            # 叠加（新批打到旧补丁上）。CLI 全局 --workspace 会置
            # SANDBOX_ACTIVE，plan 探针的读取路由会先创建**基线副本**——
            # 该副本 sha == 基线，属合法预置；只拒**已补丁**产物（sha ≠
            # 基线）：链式叠加的闸门增量翻倍虽 fail-closed，但错误难读，
            # 构建入口直接拒绝，行动点明确。
            raise _pkg().StorylineError(
                f"工作区 {workspace} 已存在**已补丁**产物（{prospective}，"
                "sha ≠ 当前基线）——构建是单次语义：换新工作区名，或确认"
                "残留后删除该工作区目录重试")
        from .. import state, utmt
        from ..cmds import npc as npc_mod
        old_ws, old_sbx = state.WORKSPACE, state.SANDBOX_ACTIVE
        old_cjk = state.ALLOW_CJK
        state.WORKSPACE = workspace
        state.SANDBOX_ACTIVE = True   # 写入定向到工作区产物（构建不触原文件）
        try:
            with utmt.game_edit("storyline-build", read_workspace=False):
                if defn.get("cjk"):
                    # F4 中文组合：先注入字体栈（同批写入工作区），再建选择
                    # NPC——typer=31（CJK_TYPER_TABLE B4 主臂实证）；文本校验
                    # 放行非 ASCII（ALLOW_CJK 仅在此作用域内开启）
                    state.ALLOW_CJK = True
                    npc = defn["npc"]
                    chars = sorted({ch for ch in (npc["prompt"] + npc["yes_text"]
                                                  + npc["no_text"])
                                    if ch not in "\r\n\t"})
                    _run_cjk_font_pipeline(game_file, chars)
                npc = defn["npc"]
                npc_mod.cmd_npc_choice(
                    game_file, plan["room"]["name"], npc["object"],
                    npc["x"], npc["y"],
                    f"det_{defn['patch_id']}_choice", npc["prompt"],
                    yes_key=f"det_{defn['patch_id']}_yes", yes_text=npc["yes_text"],
                    no_key=f"det_{defn['patch_id']}_no", no_text=npc["no_text"],
                    face=0, emotion=0, range_=npc.get("range", 60),
                    goto_room=npc.get("yes_goto"),
                    item_id=npc.get("yes_item"),
                    repeat=not npc.get("once", True),
                    typer=31 if defn.get("cjk") else 5)
        finally:
            state.WORKSPACE, state.SANDBOX_ACTIVE = old_ws, old_sbx
            state.ALLOW_CJK = old_cjk
        # 工作区产物
        product = (game_file.parent / ".deterline" / game_file.name /
                   workspace / game_file.name)
        if not product.is_file():
            raise _pkg().StorylineError(f"工作区产物缺失: {product}")
        product_sha = transactions.fingerprint(product)
        # O7 差异核验（基线 vs 工作区产物；verify.cmd_diff_snapshots 返回差异数）
        from ..cmds import verify
        import io as _io
        import contextlib as _ctx
        buf = _io.StringIO()
        with _ctx.redirect_stdout(buf):
            verify.cmd_diff_snapshots(game_file, product, detail=True)
        parsed = _parse_diff_categories(buf.getvalue())
        cats = parsed["counts"]
        allowed = _expected_categories(plan)
        undeclared = []
        # 全类别严格相等比对（期望 0 的类别实测非 0 同样拒绝——R14 P1-1）
        for kind in sorted(set(cats) | set(allowed)):
            got = cats.get(kind, 0)
            want = allowed.get(kind, 0)
            if got != want:
                undeclared.append(f"{kind} {got}（声明 {want}）")
        bad_ops = sorted({op for op in parsed["str_ops"]
                          if op not in plan["expected_resources"]["str_ops"]})
        if bad_ops:
            undeclared.append("STR op 含非声明形态: " + ",".join(bad_ops))
        # 结构段比对（F1：COUNT/VARDETERLINE/ROOM/CODE 行——资源级之外的
        # 直接结构证据，如房间尺寸被改、基线非干净、意外新代码条目）
        undeclared.extend(_check_structure(parsed, plan))
        if undeclared:
            raise _pkg().StorylineError(
                "发现未声明资源/结构变更，拒绝出候选（12 §C3）: "
                + "; ".join(undeclared) + f"（允许: {allowed}）")
    except (_pkg().StorylineError, errors.DeterlineError, FileNotFoundError,
            OSError, RuntimeError) as exc:
        # JSON 错误壳按定义版本（R-1215 P3：v2 计划阶段失败不再挂 v1 壳；
        # defn 未及载入时落 v1——与既有 v1 拒绝形态一致）
        shell = (_pkg().BUILD_SCHEMA_V2
                 if defn is not None and defn.get("_version") == "v2"
                 else _pkg().BUILD_SCHEMA)
        if json_out:
            print(json.dumps({"schema": shell, "error": str(exc)},
                             ensure_ascii=False, indent=2))
        else:
            print(f"✗ storyline-build 拒绝: {exc}", file=sys.stderr)
        return 1
    receipt = {
        "schema": _pkg().BUILD_SCHEMA,
        "patch_id": defn["patch_id"],
        "defn_sha256": defn["_sha256"],
        "tool_version": plan["tool_version"],
        "baseline_sha256": base_sha,
        "target": str(game_file),   # R13 复跑修正：回执绑定游戏文件（防跨文件复用）
        "workspace": workspace,
        "product": str(product),
        "product_sha256": product_sha,
        "declared_diff": cats,
        "declared_str_ops": parsed["str_ops"],
        "declared_structure": parsed["struct"],
        "expected_structure": plan["expected_structure"],
        "expected_resources": plan["expected_resources"],
        "goto": plan.get("goto"),
        "flag": plan["flag"],
        "diagnostics": plan["diagnostics"],
    }
    # 构建回执落盘（apply 的核对依据——12 §C4：计划/构建/提交分别可重跑）
    from . import commands as _commands  # noqa: F401  已由 _pkg() 覆盖
    transactions._write_json_atomic(  # noqa: SLF001 原子写复用
        _pkg().receipt_path(game_file, defn["patch_id"]).with_name("build.json"),
        receipt)
    if json_out:
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
    else:
        print(f"--- storyline-build（{receipt['patch_id']}）候选就绪 ---")
        print(f"  工作区: {workspace}  产物 sha256 {product_sha[:16]}…")
        print(f"  声明差异: {cats}")
        for d in receipt["diagnostics"]:
            print(f"  ℹ️  {d}")
    return 0


def cmd_storyline_apply(save_dir, game_file: Path, defn_path: str,
                        workspace: str, commit: bool = False,
                        json_out: bool = False,
                        value2: str | None = None) -> int:
    """整包应用：幂等/漂移/同 ID 异内容拒绝 → 应用 → 回执。默认预览。

    核对依据 = build.json（构建回执，storyline-build 落盘）；应用后回执
    receipt.json（含 before/after/undo）。三种出口全部在写前裁决：
    已应用 no-op（同 ID 同构建且目标==after）/ 拒绝（漂移、同 ID 异内容、
    无回执）——不靠猜测宣布已应用。"""
    defn_err = None
    try:
        from .. import state
        if commit and state.PREVIEW:
            raise _pkg().StorylineError(
                "--commit 与 --preview 互斥（预览=零动作；正式提交去掉 "
                "--preview）——previews 语义不得被 commit 覆盖")
        _validate_workspace_name(workspace)
        game_file = Path(game_file).resolve()
        if value2:
            # 包 28：合成补丁的 apply 侧用同一对文件复算合成定义/指纹
            defn, _a, _b = _load_composed(defn_path, value2)
        else:
            defn = _pkg().load_definition(Path(defn_path))
        build_rcpt_path = _pkg().receipt_path(game_file, defn["patch_id"]).with_name(
            "build.json")
        apply_rcpt_path = _pkg().receipt_path(game_file, defn["patch_id"])
        base_sha = transactions.fingerprint(game_file)
        current = base_sha
        build_rcpt = None
        if build_rcpt_path.is_file():
            try:
                build_rcpt = json.loads(build_rcpt_path.read_text(encoding="utf-8"))
            except ValueError:
                raise _pkg().StorylineError(
                    f"build.json 不可解析（损坏/被篡改为非对象）: "
                    f"{build_rcpt_path}——重新 storyline-build")
            if not isinstance(build_rcpt, dict):
                raise _pkg().StorylineError(
                    f"build.json 形状不符（应为对象）: {build_rcpt_path}——"
                    "重新 storyline-build")
            # 包 22：元数据版本/关联字段校验（写前拒绝路径）
            _validate_build_receipt_meta(build_rcpt, defn)
        prior = None
        if apply_rcpt_path.is_file():
            prior = json.loads(apply_rcpt_path.read_text(encoding="utf-8"))
        product_sha = _ws_product_sha(game_file, workspace)
        refusals = []
        if build_rcpt is None:
            refusals.append("无构建回执（.deterline/storyline 下无 "
                            f"{defn['patch_id']}/build.json）——先 storyline-build")
            if product_sha is None:
                refusals.append("工作区产物缺失——先 storyline-build")
        elif prior is not None:
            # 已有应用回执：幂等/异内容/漂移三选一（幂等判据 = 回执 defn_sha
            # ——工作区产物是单次消费语义，应用后即不在，不能作幂等依据）
            if current == prior.get("after_sha256"):
                if prior.get("defn_sha256") == defn["_sha256"]:
                    if json_out:
                        print(json.dumps({"schema": _pkg().APPLY_SCHEMA,
                                          "patch_id": defn["patch_id"],
                                          "status": "already-applied",
                                          "commit": commit},
                                         ensure_ascii=False, indent=2))
                    else:
                        print(f"✅ {defn['patch_id']} 已应用（目标 == 回执 after，"
                              "同定义）——幂等 no-op")
                    return 0
                refusals.append(
                    "同 patch_id 不同内容（定义已变更 vs 已应用回执）——"
                    "拒绝叠写（12 §C4）；先 undo 或更换 patch_id")
            elif current != prior.get("baseline_sha256"):
                refusals.append(
                    "目标基线漂移（当前 != 已应用回执 baseline）——拒绝")
            elif prior.get("defn_sha256") != defn["_sha256"]:
                refusals.append(
                    "同 patch_id 不同内容（定义已变更 vs 已应用回执）——"
                    "拒绝叠写；先 undo 或更换 patch_id")
            elif build_rcpt.get("product_sha256") != prior.get("product_sha256"):
                refusals.append(
                    "新构建与已应用回执产物不一致——拒绝叠写")
            elif product_sha is None:
                # v2 收口（包 12 链实测，R-1215 P3 顺序订正：置于漂移/异内容
                # 之后——目标漂移时不得误报"已回基线"）：undo 回基线后再次
                # apply，工作区产物已被单次消费
                refusals.append(
                    "工作区产物缺失（应用为单次消费语义：应用后工作区即不在"
                    "；目标已回基线）——重新 storyline-build")
        else:
            # 无应用回执：目标须等于构建时基线，产物须与构建回执一致，
            # 且构建回执必须对应**当前定义**（R13 P1-2：陈旧构建 + 新定义
            # 曾可上盘且回执 defn_sha 失真——首次 apply 的同 ID 异内容出口）
            #
            # 包 24 失败窗口 ①（提交完成、回执未写完）：目标 == 构建回执
            # product → 已应用可对账——从构建回执 + 当前指纹重建应用回执
            # （无前态备份信息缺失问题：before = baseline_sha，after = 当前的
            # product_sha，二者皆有据）；preview 零动作仅报告。
            if (build_rcpt.get("target") in (None, str(game_file))
                    and build_rcpt.get("defn_sha256") == defn["_sha256"]
                    and current == build_rcpt.get("product_sha256")
                    and current != build_rcpt.get("baseline_sha256")):
                rec = {
                    "schema": _pkg().APPLY_SCHEMA,
                    "patch_id": defn["patch_id"],
                    "defn_sha256": defn["_sha256"],
                    "baseline_sha256": build_rcpt.get("baseline_sha256"),
                    "product_sha256": build_rcpt.get("product_sha256"),
                    "after_sha256": current,
                    "before_sha256": build_rcpt.get("baseline_sha256"),
                    "tool_version": build_rcpt.get("tool_version"),
                    "status": "recovered-unrecorded",
                    "note": "提交完成但应用回执未写完（包 24 窗口①）——"
                            "由构建回执 + 当前指纹对账重建",
                }
                if commit:
                    transactions._write_json_atomic(  # noqa: SLF001 原子写复用
                        apply_rcpt_path, rec)
                if json_out:
                    print(json.dumps(rec, ensure_ascii=False, indent=2))
                else:
                    verb = "已对账并重建回执" if commit else \
                        "preview：检测到已应用未记账（--commit 对账）"
                    print(f"✅ {defn['patch_id']} 已应用（目标 == 构建产物）"
                          f"——{verb}")
                return 0
            if build_rcpt.get("target") not in (None, str(game_file)):
                refusals.append(
                    f"构建回执属于其他游戏文件（target={build_rcpt.get('target')}"
                    f" ≠ {game_file}）——回执按文件隔离后旧件失效，重建")
            if build_rcpt.get("defn_sha256") != defn["_sha256"]:
                refusals.append(
                    "构建回执与当前定义不符（build.json 的 defn_sha ≠ 本次"
                    "定义）——定义变更后必须先 storyline-build 重建")
            if current != build_rcpt.get("baseline_sha256"):
                refusals.append(
                    "目标基线漂移（当前 != 构建回执 baseline）——拒绝")
            if build_rcpt.get("product_sha256") != product_sha:
                refusals.append(
                    "工作区产物与构建回执不符（回执 "
                    f"{str(build_rcpt.get('product_sha256'))[:12]}… vs 现工作区 "
                    f"{str(product_sha)[:12]}…）——重建后重试")
            # R13 P1-5：有名工作区必须有 manifest（source 校验的载体）——
            # manifest 缺失 = 校验链塌缩为"未签名 JSON"，拒绝重建
            manifest = (game_file.parent / ".deterline" / game_file.name /
                        workspace / (game_file.name + ".json"))
            if product_sha is not None and not manifest.is_file():
                refusals.append(
                    f"工作区 manifest 缺失: {manifest}——来源校验不可用，"
                    "拒绝（重建须换新工作区名或删除残留后重 build）")
        if refusals:
            if json_out:
                print(json.dumps({"schema": _pkg().APPLY_SCHEMA, "patch_id": defn["patch_id"],
                                  "refusals": refusals, "commit": commit},
                                 ensure_ascii=False, indent=2))
            else:
                for r in refusals:
                    print(f"✗ 拒绝: {r}", file=sys.stderr)
            return 1
        if not commit:
            if json_out:
                print(json.dumps({"schema": _pkg().APPLY_SCHEMA, "patch_id": defn["patch_id"],
                                  "status": "preview", "commit": False,
                                  "product_sha256": product_sha,
                                  "baseline": base_sha},
                                 ensure_ascii=False, indent=2))
            else:
                print("预览完成——--commit 执行整包应用（事务层 EditPlan，含备份）")
            return 0
        # 执行：整包应用（EditPlan：暂存 + 回滚副本 + journal）——
        # 工作区经 state.WORKSPACE（CLI 全局 --workspace / 测试直设）
        from .. import state
        from ..cmds import save_cmds as _sc
        if state.WORKSPACE != workspace:
            state.WORKSPACE = workspace
        state.PREVIEW = False   # apply 层的 --commit 已裁决；内层禁再预览
        _sc.cmd_sandbox_restore(game_file)
        after_sha = transactions.fingerprint(game_file)
        receipt = {
            "schema": _pkg().APPLY_SCHEMA,
            "patch_id": defn["patch_id"],
            "defn_sha256": defn["_sha256"],
            "before_sha256": (prior.get("before_sha256") if prior
                              else build_rcpt.get("baseline_sha256")),
            "baseline_sha256": base_sha,
            "after_sha256": after_sha,
            "product_sha256": build_rcpt.get("product_sha256"),
            "workspace": workspace,
            "flag_id": defn.get("flag_id"),
            "evidence": "sandbox（B5/R2 实机证据待窗口）",
            "undo": f"undo --file data_win --value data_win --dir \"{game_file}\"",
        }
        rp = _pkg().receipt_path(game_file, defn["patch_id"])
        transactions._write_json_atomic(rp, receipt)  # noqa: SLF001 原子写复用
        if json_out:
            print(json.dumps(receipt, ensure_ascii=False, indent=2))
        else:
            print(f"✅ {defn['patch_id']} 已应用：{base_sha[:12]}… → {after_sha[:12]}…")
            print(f"   回执: {rp}")
            print(f"   撤销: {receipt['undo']}")
        return 0
    except (_pkg().StorylineError, errors.DeterlineError, FileNotFoundError,
            OSError, RuntimeError, ValueError) as exc:
        if json_out:
            print(json.dumps({"schema": _pkg().APPLY_SCHEMA,
                              "error": str(exc), "defn_error": defn_err},
                             ensure_ascii=False, indent=2))
        else:
            print(f"✗ storyline-apply 拒绝: {exc}", file=sys.stderr)
        return 1


def _find_restore_backup(game_file: Path, before_sha: str) -> Path | None:
    """包 25：按前态指纹解析恢复备份（.bak / .bak.<ts>，最新优先）。

    备份只认指纹匹配（回执登记的本次前态）——不按"最新备份"猜测，
    防叠加补丁场景下撤销错代。
    """
    cands: list[Path] = []
    plain = game_file.with_suffix(game_file.suffix + ".bak")
    if plain.is_file():
        cands.append(plain)
    cands.extend(sorted(game_file.parent.glob(game_file.name + ".bak.*"),
                        key=lambda x: x.name, reverse=True))
    for p in cands:
        if transactions.fingerprint(p) == before_sha:
            return p
    return None


def cmd_storyline_undo(game_file: Path, defn_path: str,
                       json_out: bool = False,
                       value2: str | None = None) -> int:
    """包 25：v2 补丁前态撤销入口（按应用回执 + 既有备份机制）。

    拒绝链（全部保留目标与回执）：无应用回执 / 目标被修改（当前既非
    after 也非 before）/ 备份缺席（无指纹 == before 的备份）。
    可识别出口：已撤销（回执 status=undone 或当前 == before）→ no-op；
    正例 → 恢复回 before 并原子更新回执（status=undone + undo_after）。
    """
    try:
        game_file = Path(game_file).resolve()
        if value2:
            defn, _a, _b = _load_composed(defn_path, value2)
        else:
            defn = _pkg().load_definition(Path(defn_path))
        rcpt_path = _pkg().receipt_path(game_file, defn["patch_id"])
        if not rcpt_path.is_file():
            raise _pkg().StorylineError(
                f"无应用回执（{rcpt_path} 不存在）——无可撤销记录；"
                "拒绝按猜测恢复")
        rcpt = json.loads(rcpt_path.read_text(encoding="utf-8"))
        if not isinstance(rcpt, dict):
            raise _pkg().StorylineError(
                f"应用回执形状不符（应为对象）: {rcpt_path}")
        before = rcpt.get("before_sha256")
        after = rcpt.get("after_sha256") or rcpt.get("product_sha256")
        current = transactions.fingerprint(game_file)
        if rcpt.get("status") == "undone" or current == before:
            if json_out:
                print(json.dumps({"schema": _pkg().APPLY_SCHEMA,
                                  "patch_id": defn["patch_id"],
                                  "status": "already-undone"},
                                 ensure_ascii=False, indent=2))
            else:
                print(f"✅ {defn['patch_id']} 已撤销（目标 == 前态）——"
                      "幂等 no-op")
            return 0
        refusals = []
        if current != after:
            refusals.append(
                f"目标被修改（当前 {str(current)[:12]}… 既非回执 after "
                f"{str(after)[:12]}… 也非 before）——拒绝撤销，目标与回执"
                "保留；人工核查后再处置")
        if not before:
            refusals.append("回执缺 before_sha256——无法定位前态，拒绝")
        backup = _find_restore_backup(game_file, before) if before else None
        if backup is None:
            refusals.append(
                f"备份缺席（无指纹 == before {str(before)[:12]}… 的 "
                ".bak/.bak.<ts>）——拒绝，回执保留；重新应用或沿用通用 "
                "undo 前先人工核查")
        if refusals:
            if json_out:
                print(json.dumps({"schema": _pkg().APPLY_SCHEMA,
                                  "patch_id": defn["patch_id"],
                                  "error": "; ".join(refusals)},
                                 ensure_ascii=False, indent=2))
            else:
                for r in refusals:
                    print(f"✗ 拒绝: {r}", file=sys.stderr)
            return 1
        transactions.write_one(game_file, backup)
        restored = transactions.fingerprint(game_file)
        rcpt["status"] = "undone"
        rcpt["undo_after_sha256"] = restored
        rcpt["undo_backup"] = str(backup)
        transactions._write_json_atomic(rcpt_path, rcpt)  # noqa: SLF001
        if json_out:
            print(json.dumps({"schema": _pkg().APPLY_SCHEMA,
                              "patch_id": defn["patch_id"],
                              "status": "undone",
                              "before_sha256": before,
                              "undo_after_sha256": restored,
                              "backup": str(backup)},
                             ensure_ascii=False, indent=2))
        else:
            print(f"✅ {defn['patch_id']} 已撤销：{str(after)[:12]}… → "
                  f"{str(restored)[:12]}…（备份 {backup.name}）")
            print(f"   回执已更新: {rcpt_path}")
        return 0
    except (_pkg().StorylineError, errors.DeterlineError, FileNotFoundError,
            OSError, ValueError) as exc:
        if json_out:
            print(json.dumps({"schema": _pkg().APPLY_SCHEMA,
                              "error": str(exc)},
                             ensure_ascii=False, indent=2))
        else:
            print(f"✗ storyline-undo 拒绝: {exc}", file=sys.stderr)
        return 1


def _ws_product_sha(game_file: Path, workspace: str):
    product = (game_file.parent / ".deterline" / game_file.name /
               workspace / game_file.name)
    return transactions.fingerprint(product) if product.is_file() else None
