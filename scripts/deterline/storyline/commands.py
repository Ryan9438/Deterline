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
import sys
from pathlib import Path

from .. import errors, transactions


def _pkg():
    """运行时取本包模块（跨模块引用一律运行时属性查找——包纪律）。
    commands 由 __init__ 导入，此处 _sys.modules[__package__] 在运行期
    已完成初始化。"""
    import sys as _sys
    return _sys.modules[__package__]


def cmd_storyline_plan(game_file: Path, defn_path: str, json_out: bool = False) -> int:
    """只读计划：定义 → 计划 JSON（零写盘）。"""
    try:
        defn = _pkg().load_definition(Path(defn_path))
        plan = _pkg().build_plan(defn, game_file)
    except (_pkg().StorylineError, errors.DeterlineError, FileNotFoundError,
            OSError) as exc:
        if json_out:
            print(json.dumps({"schema": _pkg().PLAN_SCHEMA, "error": str(exc)},
                             ensure_ascii=False, indent=2))
        else:
            print(f"✗ storyline-plan 拒绝: {exc}", file=sys.stderr)
        return 1
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
            except (ValueError, SyntaxError, MemoryError):
                # R15 P3-1：畸形 repr（理论形态——var 名含 "] → " 等）→
                # 显式畸形标记，闸门按不可解析拒绝（fail-closed 非裸栈）
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
    return {"counts": counts, "str_ops": str_ops, "struct": struct}


def _check_structure(parsed: dict, plan: dict) -> list[str]:
    """结构段比对（F1）：解析出的结构差异 vs plan.expected_structure——
    全类别严格相等（含期望为空而实测非空的形态）。返回未声明清单（空=过）。"""
    st = parsed["struct"]
    exp = plan["expected_structure"]
    out: list[str] = []
    for k in sorted(set(st["count_deltas"]) | set(exp["count_deltas"])):
        got = st["count_deltas"].get(k, 0)
        want = exp["count_deltas"].get(k, 0)
        if got != want:
            out.append(f"COUNT {k} 变化 {got}（声明 {want}）")
    va, vb = st["vardeterline"] if st["vardeterline"] is not None else ([], [])
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


def _run_cjk_font_pipeline(game_file: Path, defn: dict) -> None:
    """F4 中文组合：字形页预处理 + 五步字体管线（pass1/pass2 经外层
    game_edit 批量写入当前工作区）。字符集 = 定义三文本字段的全部唯一
    字符（最小集，确定性：同定义 → 同字形集 → 同产物）。

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
    npc = defn["npc"]
    chars = sorted({ch for ch in (npc["prompt"] + npc["yes_text"]
                                  + npc["no_text"]) if ch not in "\r\n\t"})
    with _tmp.TemporaryDirectory(prefix="deterline_cjk_") as td:
        chars_file = _Path(td) / "chars.txt"
        chars_file.write_text("".join(chars), encoding="utf-8")
        build_dir = _Path(td) / "font_build"
        work_dir = _Path(td) / "cjk_work"
        tool_ns = _runpy.run_path(str(tool), run_name="deterline_font_build")
        out, err = _io.StringIO(), _io.StringIO()
        try:
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


def cmd_storyline_build(game_file: Path, defn_path: str, workspace: str,
                        json_out: bool = False) -> int:
    """构建：plan → 工作区构建 → O7 差异核验 → 构建回执（仅写工作区）。
    `--preview` 不支持——构建即写工作区（EditPlan 预览不落盘会使产物
    缺失，语义冲突，R13 P3）。"""
    try:
        from .. import state
        if state.PREVIEW:
            raise _pkg().StorylineError(
                "storyline-build 不支持 --preview（构建即写工作区；预览用 "
                "storyline-plan 或 build 后的 storyline-apply 预览）")
        _validate_workspace_name(workspace)
        game_file = Path(game_file).resolve()
        defn = _pkg().load_definition(Path(defn_path))
        plan = _pkg().build_plan(defn, game_file)
        base_sha = transactions.fingerprint(game_file)
        if base_sha is None:
            raise errors.NotFoundError(f"基线文件不存在: {game_file}")
        # 域生成器构建（写入有名工作区，不触原文件）——自管 game_edit 上下文：
        # 批量提交在上下文**退出**时落盘（data_win 包装内读产物 = 基线副本，
        # C4 CLI 实测教训），指纹/O7 比对必须在其后
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
                    _run_cjk_font_pipeline(game_file, defn)
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
        if json_out:
            print(json.dumps({"schema": _pkg().BUILD_SCHEMA, "error": str(exc)},
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
                        json_out: bool = False) -> int:
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
        else:
            # 无应用回执：目标须等于构建时基线，产物须与构建回执一致，
            # 且构建回执必须对应**当前定义**（R13 P1-2：陈旧构建 + 新定义
            # 曾可上盘且回执 defn_sha 失真——首次 apply 的同 ID 异内容出口）
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


def _ws_product_sha(game_file: Path, workspace: str):
    product = (game_file.parent / ".deterline" / game_file.name /
               workspace / game_file.name)
    return transactions.fingerprint(product) if product.is_file() else None
