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

退出码：0=成功/已应用；1=拒绝（合同/解析/差异/漂移/冲突）；2=定位失败。
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
    """从 O7 --detail 文本提取粗粒度差异类别（kind→计数）。

    通用解析：`<大写资源类别> <add|changed|del> …` 形态的行（STR add /
    CODEF changed / TEX changed / INST add …）——**不设类别白名单**：
    未知类别必须被看见并进入声明比对（C3 验收：未声明变更 = 拒绝，
    解析层漏看 = 假绿）。非差异行（表头/路径/统计）不匹配形态即忽略。"""
    cats: dict[str, int] = {}
    for line in diff_output.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[0].isupper() \
                and parts[1] in ("add", "changed", "del"):
            kind = f"{parts[0]} {parts[1]}"
            cats[kind] = cats.get(kind, 0) + 1
    return cats


def _expected_categories(plan: dict) -> dict:
    """计划期望 → 允许的 O7 类别集合（模板常数标定，见 contract）。"""
    er = plan["expected_resources"]
    allowed = {"STR add": er["str_adds"], "CODEF add": er["code_adds"],
               "CODEF changed": er["code_changed"],
               "INST add": er["inst_adds"]}
    if er.get("alarm_guard"):
        allowed["CODEF changed"] += 1   # Alarm_0 守卫追加
    return allowed


def cmd_storyline_build(game_file: Path, defn_path: str, workspace: str,
                        json_out: bool = False) -> int:
    """构建：plan → 工作区构建 → O7 差异核验 → 构建回执（仅写工作区）。"""
    try:
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
        state.WORKSPACE = workspace
        state.SANDBOX_ACTIVE = True   # 写入定向到工作区产物（构建不触原文件）
        try:
            with utmt.game_edit("storyline-build", read_workspace=False):
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
                    repeat=not npc.get("once", True))
        finally:
            state.WORKSPACE, state.SANDBOX_ACTIVE = old_ws, old_sbx
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
        cats = _parse_diff_categories(buf.getvalue())
        allowed = _expected_categories(plan)
        undeclared = []
        for kind, count in cats.items():
            if kind not in allowed:
                undeclared.append(f"{kind}×{count}")
            elif count > allowed[kind]:
                undeclared.append(f"{kind}×{count}（声明 {allowed[kind]}）")
        if undeclared:
            raise _pkg().StorylineError(
                "发现未声明资源变更，拒绝出候选（12 §C3）: "
                + "; ".join(undeclared) + f"（允许类别: {allowed}）")
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
        "workspace": workspace,
        "product": str(product),
        "product_sha256": product_sha,
        "declared_diff": cats,
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
        defn = _pkg().load_definition(Path(defn_path))
        build_rcpt_path = _pkg().receipt_path(game_file, defn["patch_id"]).with_name(
            "build.json")
        apply_rcpt_path = _pkg().receipt_path(game_file, defn["patch_id"])
        base_sha = transactions.fingerprint(game_file)
        current = base_sha
        build_rcpt = None
        if build_rcpt_path.is_file():
            build_rcpt = json.loads(build_rcpt_path.read_text(encoding="utf-8"))
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
            # 无应用回执：目标须等于构建时基线，产物须与构建回执一致
            if current != build_rcpt.get("baseline_sha256"):
                refusals.append(
                    "目标基线漂移（当前 != 构建回执 baseline）——拒绝")
            if build_rcpt.get("product_sha256") != product_sha:
                refusals.append(
                    "工作区产物与构建回执不符（回执 "
                    f"{str(build_rcpt.get('product_sha256'))[:12]}… vs 现工作区 "
                    f"{str(product_sha)[:12]}…）——重建后重试")
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
