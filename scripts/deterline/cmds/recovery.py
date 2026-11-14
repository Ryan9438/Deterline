"""恢复域命令（03 §2.2c + 06 §4 执行入口）：未完结运行记录的只读扫描、
恢复执行（recovery-apply）与清理（recovery-clean）。

recovery-scan：扫描 game 旁 / 存档目录旁两处 `.deterline/journal/*.json`
（transactions 落盘的运行记录），按目标当前内容 vs 记录的 before/after 哈希
分类中断窗口，输出可预览的恢复动作（精确到 cp 命令）；孤儿暂存文件
（`.{name}.*.new` 且无记录引用）单独列出。零写盘、零 UTMT、零恢复执行。

recovery-apply（06 §4，值守场次入口）：按 scan 分类执行恢复。--direction
rollback|complete 显式择向（rollback=放弃本次，目标 ← 回滚副本；complete=
继续本次，目标 ← 暂存副本）；混合分类整批拒绝；not-created 目标 v1 列为
blocked 跳过。journal 复用方案 A：不新建/不删除运行记录——apply 以原
journal 自身为运行记录，逐目标校验当前 sha ∈ {before, after} 后 os.replace，
全程在盘——apply 中段 SIGKILL → scan 重分类 → apply 可重入；完成后记录
自然重分类为 not-started/done-confirm（recovery-clean 清理）。

recovery-clean（06 §4）：对每条记录**现场重分类**（绝不信任存量 state 字段）；
仅重分类 ∈ {not-started, done-confirm} 且 state ∈ JOURNAL_STATES 可清
（journal 文件 + 其引用的 staged/rollback 副本）；suspicious / interrupted /
aborted-partial / corrupt / unknown-state 一律拒绝并打印指引；孤儿 .new 按
resolve 归一非引用判定删除。清理 manifest 只进 stdout/--json，不写入
journal 目录。

退出码：无未完结项 0；发现/拒绝 1；两侧定位均失败 2
（对齐 backup-index：自动化可区分"干净"与"没扫到"）。
"""

import json
import sys
from pathlib import Path

from .. import paths, transactions

STAGED_SUFFIX = ".new"


def _classify_target(entry: dict) -> str:
    """单目标状态：before（未替换）/ after（已替换）/ not-created（新文件
    未落）/ missing（原文件消失）/ external（均不匹配=外部改动）。"""
    raw = entry.get("path")
    if not raw:
        return "external"
    path = Path(raw)
    before = entry.get("before")
    after = entry.get("after")
    if not path.exists():
        return "not-created" if before is None else "missing"
    current = transactions.fingerprint(path)
    if after is not None and current == after:
        return "after"
    if before is not None and current == before:
        return "before"
    return "external"


def _plan_level(state: str, classes: list[str]) -> str:
    """中断窗口分类 → 展示级：not-started / done-confirm / interrupted /
    suspicious。（aborted-* 由记录状态直达对应建议。）"""
    if any(c in ("external", "missing") for c in classes):
        return "suspicious"
    if all(c == "after" for c in classes):
        return "done-confirm"
    if all(c in ("before", "not-created") for c in classes):
        return "not-started"
    return "interrupted"


def _fmt_sha(sha: str | None) -> str:
    return f"{sha[:12]}…" if isinstance(sha, str) and sha else "<无>"


def _collect_findings(save_dir: Path | None, dir_override: str | None):
    """scan / apply / clean 共用的分类 SSOT（06 §4）。

    返回 (findings, warnings, roots, records)：
    - findings：与 recovery-scan --json 同构（run-journal / orphan-staged /
      corrupt-journal；run-journal 项的 level 用展示口径——aborted-* 直达）。
    - records：可解析 run-journal 的现场重分类口径——
      {path, record, state, classes, level_scan, level_pure}；level_pure =
      纯 _plan_level（aborted-clean + 全 before → not-started，供 clean 判定；
      scan 展示口径保持 aborted-* 直达 "aborted"）。
    - roots：扫描根（可能为空列表）。
    """
    warnings: list[str] = []
    findings: list[dict] = []
    records: list[dict] = []

    roots: list[Path] = []
    try:
        roots.append(paths.resolve_game_data_file(dir_override).parent)
    except FileNotFoundError as e:
        warnings.append(f"游戏数据目录未定位: {e}")
    if save_dir is not None:
        # A P3-4：--dir /private/tmp/x 与 file parent /tmp/x 拼写差曾产生
        # 双 root 重复扫描（findings 重复列出）——resolve 归一去重
        if all(save_dir.resolve() != r.resolve() for r in roots):
            roots.append(save_dir)
    else:
        warnings.append("存档目录未定位——存档侧 journal/孤儿不扫描")

    # 工作区层 journal（审核席 A P2-2）：sandbox 写路径的记录落在
    # <game_dir>/.deterline/<file>/<ws>/.deterline/journal——顶层两处看不到，
    # 会造成"提交被拒 → scan 报干净"死胡同。
    journal_roots = transactions.journal_roots_for(roots)

    referenced: set[str] = set()   # resolve 归一（/tmp 与 /private/tmp 同形）
    orphan_dirs: list[Path] = []   # 孤儿暂存扫描目录：roots + 各目标 parent

    def _register_orphan_dir(directory: Path) -> None:
        # A P3-4：拼写差目录以 resolve 归一去重（字面比较曾失效）
        try:
            key = str(directory.resolve())
        except OSError:
            key = str(directory)
        for existing in orphan_dirs:
            try:
                existing_key = str(existing.resolve())
            except OSError:
                existing_key = str(existing)
            if existing_key == key:
                return
        orphan_dirs.append(directory)

    for directory in roots:
        _register_orphan_dir(directory)

    for journal_root in journal_roots:
        for path in sorted(journal_root.glob("*.json")):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                findings.append({
                    "kind": "corrupt-journal", "level": "unfinished",
                    "path": str(path), "error": str(exc)[:120],
                    "actions": ["人工查看后删除（无法解析——无法给出安全恢复指引）"],
                })
                continue
            if (not isinstance(record, dict)
                    or record.get("schema") != transactions.JOURNAL_SCHEMA
                    or not isinstance(record.get("targets"), list)
                    or not record["targets"]):
                findings.append({
                    "kind": "corrupt-journal", "level": "unfinished",
                    "path": str(path), "error": "schema/targets 不符或缺空",
                    "actions": ["人工查看后删除"],
                })
                continue
            state = record.get("state")
            entries = record["targets"]
            classes = [_classify_target(e) if isinstance(e, dict) else "external"
                       for e in entries]
            # A P2-2：目标 parent 一并纳入孤儿扫描——journal 先于暂存落盘
            # （pending 记录 staged=None）时，嵌套工作区旁的残留顶层看不到
            for entry in entries:
                if isinstance(entry, dict) and entry.get("path"):
                    _register_orphan_dir(Path(entry["path"]).parent)
            if state not in transactions.JOURNAL_STATES:
                level = "unknown-state"
            elif state in ("aborted-clean", "aborted-partial"):
                level = "aborted"
            else:
                level = _plan_level(state, classes)
            records.append({
                "path": path, "record": record, "state": state,
                "classes": classes, "level_scan": level,
                "level_pure": _plan_level(state, classes),
            })
            actions: list[str] = []
            # 回滚/完成 cp 指引：interrupted（替换中断）与 aborted-partial
            # （回滚失败、副本保留）两档给出可执行出口（审核席 A P3-1/B P3-4）
            give_cp = (level == "interrupted"
                       or (level == "aborted" and state == "aborted-partial"))
            for entry, cls in zip(entries, classes):
                if not isinstance(entry, dict):
                    continue
                target_path = entry.get("path")
                rollback = entry.get("rollback")
                staged = entry.get("staged")
                if (give_cp and cls == "after" and rollback
                        and Path(rollback).exists()):
                    actions.append(
                        f"回滚该目标: cp \"{rollback}\" \"{target_path}\"")
                if (give_cp and cls == "before" and staged
                        and Path(staged).exists()):
                    actions.append(
                        f"完成该目标: cp \"{staged}\" \"{target_path}\"")
                if rollback:
                    referenced.add(str(Path(rollback).resolve()))
                    _register_orphan_dir(Path(rollback).parent)
                if staged:
                    referenced.add(str(Path(staged).resolve()))
                    _register_orphan_dir(Path(staged).parent)
            if level == "not-started":
                actions.append("目标未被触及——删除该 journal 与 staged 残留即可")
            elif level == "done-confirm":
                actions.append("全部目标已写入（== after）——核对内容后删除该 "
                               "journal 与残留（recovery-clean 下批提供）")
            elif level == "interrupted":
                if actions:
                    actions.append("替换中断——上列 cp 命令二选一：全部回滚=放弃本次，"
                                   "全部完成=继续本次；执行后删除 journal")
                else:
                    # A P3-5：回滚/暂存副本均不存在时"上列 cp"是空指
                    actions.append("替换中断——但回滚/暂存副本均不存在，无 cp 出口；"
                                   "人工核对目标内容后删除 journal")
            elif level == "suspicious":
                actions.append("存在外部修改——人工核对目标内容，勿盲用回滚副本")
            elif level == "aborted":
                actions.append("事务层已按回滚失败/成功归类（error 字段）——"
                               "按 error 处理后删除 journal")
            elif level == "unknown-state":
                actions.append("state 字段不在已知状态机内——人工核对该记录来源")
            findings.append({
                "kind": "run-journal", "level": level,
                "path": str(path), "id": record.get("id"),
                "state": state, "created": record.get("created"),
                "error": record.get("error"),
                "targets": [{
                    "path": e.get("path") if isinstance(e, dict) else None,
                    "class": cls,
                    "before": e.get("before") if isinstance(e, dict) else None,
                    "after": e.get("after") if isinstance(e, dict) else None,
                    "rollback_exists": (bool(e.get("rollback"))
                                        and Path(e["rollback"]).exists()
                                        if isinstance(e, dict) else False),
                    "staged_exists": (bool(e.get("staged"))
                                      and Path(e["staged"]).exists()
                                      if isinstance(e, dict) else False),
                } for e, cls in zip(entries, classes)],
                "actions": actions,
            })

    # 孤儿暂存：.{name}.*.new 且未被任何已解析记录引用（resolve 归一比较，
    # 防 /tmp 与 /private/tmp 拼写差把恢复副本误报成孤儿——审核席 A/B P2-1）
    for directory in orphan_dirs:
        for orphan in sorted(directory.glob(f".*{STAGED_SUFFIX}")):
            if not orphan.is_file() or orphan.name.startswith(".journal."):
                continue
            if str(orphan.resolve()) in referenced:
                continue
            findings.append({
                "kind": "orphan-staged", "level": "unfinished",
                "path": str(orphan),
                "actions": ["无记录引用的暂存残留（目标未被触及）——确认后删除"],
            })
    return findings, warnings, roots, records


def cmd_recovery_scan(save_dir: Path | None, dir_override: str | None = None,
                      json_out: bool = False) -> int:
    """只读扫描：未完结运行记录 + 孤儿暂存 → 分类 + 可预览恢复指引。

    退出码：无未完结项 0；发现任何记录/孤儿 1；两侧定位均失败 2。
    --json 时 stdout 纯 JSON（schema deterline.recovery-scan/v1），warnings
    进 JSON 不进 stderr。
    """
    findings, warnings, roots, _records = _collect_findings(save_dir, dir_override)

    if not roots:
        # 两侧定位均失败：什么都没扫到，不能报"干净"（对齐 backup-index）
        if json_out:
            print(json.dumps({
                "schema": "deterline.recovery-scan/v1",
                "roots": [], "findings": [], "warnings": warnings,
            }, ensure_ascii=False, indent=2))
        else:
            for w in warnings:
                print(f"  ⚠️ {w}", file=sys.stderr)
            print("--- 未扫描任何目录（退出码 2） ---")
        return 2

    if json_out:
        print(json.dumps({
            "schema": "deterline.recovery-scan/v1",
            "roots": [str(r) for r in roots],
            "findings": findings,
            "warnings": warnings,
        }, ensure_ascii=False, indent=2))
        return 1 if findings else 0

    for finding in findings:
        if finding["kind"] == "run-journal":
            print(f"⚠️ 未完结运行记录 {finding.get('id')} "
                  f"[{finding.get('state')}] {finding['path']}")
            for target in finding["targets"]:
                rollback_mark = "✓" if target["rollback_exists"] else "✗"
                staged_mark = "✓" if target["staged_exists"] else "✗"
                print(f"   目标 {target['path']}: {target['class']}"
                      f"（rollback {rollback_mark} / staged {staged_mark}）"
                      f" before={_fmt_sha(target['before'])}"
                      f" after={_fmt_sha(target['after'])}")
            if finding.get("error"):
                print(f"   error: {finding['error']}")
        else:
            print(f"⚠️ {finding['kind']}: {finding['path']}")
        for action in finding["actions"]:
            print(f"   → {action}")
    for w in warnings:
        print(f"  ⚠️ {w}", file=sys.stderr)
    if not findings:
        print("✅ 无未完结运行记录与孤儿暂存")
    else:
        print(f"--- 发现 {len(findings)} 项未完结（退出码 1；"
              f"recovery-apply/clean 执行入口见 --help） ---")
    return 1 if findings else 0


_APPLY_DIRECTIONS = ("rollback", "complete")


def _copy_sha_ok(copy: Path, expect: str | None) -> tuple[bool, str | None]:
    """副本存在性 + 内容指纹 == 期望（before/after）。"""
    if not copy or not Path(copy).is_file():
        return False, None
    actual = transactions.fingerprint(Path(copy))
    return (expect is not None and actual == expect), actual


def cmd_recovery_apply(save_dir: Path | None, dir_override: str | None = None,
                       direction: str | None = None, commit: bool = False,
                       json_out: bool = False) -> int:
    """按 scan 分类执行恢复（06 §4）：--direction rollback|complete。

    rollback = 放弃本次（目标 ← 回滚副本；须全部目标 == after）；complete =
    继续本次（目标 ← 暂存副本；须全部目标 ∈ {before, not-created}，not-created
    目标 v1 blocked 跳过）。混合分类整批拒绝。journal 复用方案 A：不新建/不
    删除运行记录——中段 SIGKILL → scan 重分类 → apply 可重入；完成后记录自然
    重分类为 not-started/done-confirm（recovery-clean 清理）。
    默认预览零动作；--commit 执行（逐目标 os.replace，副本即被消费）。
    退出码：0=成功/可执行/无未完结记录；1=拒绝（混合/外部改动/副本缺失/
    多记录/无需 apply）；2=两侧定位均失败。--json 输出
    deterline.recovery-apply/v1。
    """
    findings, warnings, roots, records = _collect_findings(save_dir, dir_override)

    if not roots:
        if json_out:
            print(json.dumps({
                "schema": "deterline.recovery-apply/v1",
                "direction": direction, "commit": commit,
                "roots": [], "plan": None, "refusals": [],
                "warnings": warnings,
            }, ensure_ascii=False, indent=2))
        else:
            for w in warnings:
                print(f"  ⚠️ {w}", file=sys.stderr)
            print("--- 未扫描任何目录（退出码 2） ---")
        return 2

    refusals: list[str] = []
    plan: list[dict] = []
    done: list[dict] = []

    if commit and direction not in _APPLY_DIRECTIONS:
        refusals.append("--commit 需要 --direction rollback|complete")

    if not records:
        msg = "✅ 无未完结运行记录——无需 apply"
        if json_out:
            print(json.dumps({
                "schema": "deterline.recovery-apply/v1",
                "direction": direction, "commit": commit,
                "roots": [str(r) for r in roots], "plan": [], "refusals": [],
                "warnings": warnings,
            }, ensure_ascii=False, indent=2))
        else:
            print(msg)
        return 0

    if len(records) > 1:
        refusals.append(
            f"发现 {len(records)} 条可解析运行记录——v1 一次只处理一条"
            "（逐条 recovery-clean 处理已完结项后重试）："
            + "; ".join(str(r["path"]) for r in records))

    rec = records[0]
    level = rec["level_pure"]
    state = rec["state"]
    if not refusals:
        # 注意：不按 level 挡 not-started/done-confirm——pending+全 before
        # 恰是 complete 的目标场景（staging 后、首次替换前窗口）；同质校验 +
        # 副本校验才是裁决者。仅挡真正不可恢复的形态：
        if level == "suspicious":
            refusals.append(
                "存在外部修改（目标既非 before 也非 after）——人工核对，勿盲用副本")
        elif state not in transactions.JOURNAL_STATES:
            refusals.append("state 字段不在已知状态机内——人工核对该记录来源")

    if not refusals:
        classes = rec["classes"]
        entries = rec["record"]["targets"]
        if direction == "complete":
            if any(c not in ("before", "not-created") for c in classes):
                refusals.append(
                    "complete 要求全部目标 ∈ {before, not-created}"
                    f"（实况: {classes}）——混合分类整批拒绝")
        elif direction == "rollback":
            if any(c != "after" for c in classes):
                refusals.append(
                    f"rollback 要求全部目标 == after（实况: {classes}）"
                    "——混合分类整批拒绝")
        # direction=None（纯预览）：不择向，仅展示

    if not refusals and direction is not None:
        entries = rec["record"]["targets"]
        for entry, cls in zip(entries, classes):
            if not isinstance(entry, dict):
                continue
            if direction == "complete":
                if cls == "not-created":
                    plan.append({"path": entry["path"], "class": cls,
                                 "copy": None, "action": "blocked（v1 不处理）",
                                 "copy_sha_ok": None})
                    continue
                copy = entry.get("staged")
                expect = entry.get("after")
                verb = "complete"
            else:
                copy = entry.get("rollback")
                expect = entry.get("before")
                verb = "rollback"
            ok, actual = _copy_sha_ok(copy, expect)
            plan.append({
                "path": entry["path"], "class": cls,
                "copy": copy, "copy_sha_ok": ok,
                "copy_sha": actual,
                "expect": expect,
                "action": (f"{verb}: os.replace(\"{copy}\" → \"{entry['path']}\")"
                           if ok else f"{verb}: 副本缺失/指纹不符——拒绝"),
            })
            if not ok:
                refusals.append(
                    f"副本校验失败: {entry['path']}（copy={copy} 存在="
                    f"{bool(copy) and Path(copy).is_file()}"
                    f" 指纹匹配={ok}）——整批拒绝")

    if commit and refusals:
        # --commit 遇拒绝：绝不部分执行（整批拒绝）
        done = []
    elif commit and direction is not None and not refusals:
        import os
        for item in plan:
            if item["action"].startswith("blocked"):
                item["done"] = False
                continue
            try:
                os.replace(item["copy"], item["path"])
                item["done"] = True
                done.append(item)
            except OSError as exc:
                item["done"] = False
                refusals.append(f"执行失败: {item['path']}（{exc}）"
                                "——已完成目标保留（scan 重分类后可重入）")
                break

    if json_out:
        print(json.dumps({
            "schema": "deterline.recovery-apply/v1",
            "direction": direction, "commit": commit,
            "roots": [str(r) for r in roots],
            "record_path": str(rec["path"]) if records else None,
            "state": state, "classes": rec["classes"],
            "plan": plan, "done": done, "refusals": refusals,
            "warnings": warnings,
        }, ensure_ascii=False, indent=2))
        return 1 if refusals else 0

    print(f"--- recovery-apply（{'执行' if commit and direction else '预览，零动作'}） ---")
    if records:
        print(f"  记录 {rec['path']} [state={state}] 现场分类: {rec['classes']}")
    for item in plan:
        mark = "✓" if item.get("copy_sha_ok") else "✗"
        print(f"  {mark} {item['action']}")
    for r in refusals:
        print(f"  ✗ 拒绝: {r}")
    if done:
        print(f"  已执行 {len(done)} 目标；journal 保留——scan 现应重分类，"
              "recovery-clean 清理")
    elif commit and direction and not refusals:
        print("  （无 actionable 目标）")
    for w in warnings:
        print(f"  ⚠️ {w}", file=sys.stderr)
    if not commit and not refusals and direction is None:
        print("  预览完成——--direction rollback|complete 择向，--commit 执行")
    if not commit and not refusals and direction is not None:
        print("  预览完成——加 --commit 执行")
    return 1 if refusals else 0


def cmd_recovery_clean(save_dir: Path | None, dir_override: str | None = None,
                       commit: bool = False, json_out: bool = False) -> int:
    """清理已完结运行记录与孤儿暂存（06 §4）：现场重分类，绝不信任存量 state。

    可清 = state ∈ JOURNAL_STATES 且纯重分类 ∈ {not-started, done-confirm}
    （journal 文件 + 其引用的 staged/rollback 副本）；suspicious / interrupted /
    aborted-partial / corrupt / unknown-state 一律拒绝并打印指引（拒绝不影响
    其他可清项执行）。孤儿 .new（resolve 归一非引用）一并清理。
    默认预览零动作；--commit 执行。清理 manifest 只进 stdout/--json，
    不得写入 journal 目录。
    退出码：0=无可清项或全部已清；1=存在拒绝项（指引已打印）；2=两侧定位均失败。
    --json 输出 deterline.recovery-clean/v1。
    """
    findings, warnings, roots, records = _collect_findings(save_dir, dir_override)

    if not roots:
        if json_out:
            print(json.dumps({
                "schema": "deterline.recovery-clean/v1",
                "commit": commit, "roots": [], "cleanable": [],
                "refused": [], "orphans": [], "deleted": [],
                "warnings": warnings,
            }, ensure_ascii=False, indent=2))
        else:
            for w in warnings:
                print(f"  ⚠️ {w}", file=sys.stderr)
            print("--- 未扫描任何目录（退出码 2） ---")
        return 2

    cleanable: list[dict] = []
    refused: list[dict] = []
    for rec in records:
        if (rec["state"] in transactions.JOURNAL_STATES
                and rec["level_pure"] in ("not-started", "done-confirm")):
            cleanable.append(rec)
        else:
            refused.append({
                "path": str(rec["path"]), "state": rec["state"],
                "level": rec["level_pure"],
                "guidance": (
                    "recovery-apply 处理（--direction 择向）"
                    if rec["level_pure"] in ("interrupted", "aborted")
                    else "存在外部修改——人工核对目标内容"
                    if rec["level_pure"] == "suspicious"
                    else "state 不在已知状态机——人工核对"),
            })
    corrupt = [f for f in findings if f["kind"] == "corrupt-journal"]
    for f in corrupt:
        refused.append({"path": f["path"], "state": None,
                        "level": "corrupt-journal",
                        "guidance": "人工查看后删除（无法解析）"})

    # 孤儿：findings 中的 orphan-staged 项（其"非引用"判定已按**全部**现存
    # 记录算好——含将被 clean 的记录；commit 时它们随记录一起消失，判定仍成立）
    orphans = [f for f in findings if f["kind"] == "orphan-staged"]

    deleted: list[str] = []
    if commit:
        # 逐条执行（06 §4）：拒绝项不影响其他可清项——拒绝只驱动退出码
        for rec in cleanable:
            try:
                rec["path"].unlink()
                deleted.append(str(rec["path"]))
            except OSError as exc:
                warnings.append(f"journal 删除失败: {rec['path']}（{exc}）")
            for key in ("staged", "rollback"):
                for entry in rec["record"].get("targets", []):
                    copy = entry.get(key) if isinstance(entry, dict) else None
                    if copy and Path(copy).is_file():
                        try:
                            Path(copy).unlink()
                            deleted.append(str(copy))
                        except OSError as exc:
                            warnings.append(f"副本删除失败: {copy}（{exc}）")
            journal_dir = rec["path"].parent
            transactions._rmdir_if_empty(journal_dir)  # noqa: SLF001 同包私有复用
        for f in orphans:
            opath = Path(f["path"])
            try:
                opath.unlink()
                deleted.append(str(opath))
            except OSError as exc:
                warnings.append(f"孤儿删除失败: {f['path']}（{exc}）")

    if json_out:
        print(json.dumps({
            "schema": "deterline.recovery-clean/v1",
            "commit": commit,
            "roots": [str(r) for r in roots],
            "cleanable": [{"path": str(r["path"]), "state": r["state"],
                           "level": r["level_pure"]} for r in cleanable],
            "refused": refused,
            "orphans": [f["path"] for f in orphans],
            "deleted": deleted,
            "warnings": warnings,
        }, ensure_ascii=False, indent=2))
        return 1 if refused else 0

    print(f"--- recovery-clean（{'执行' if commit else '预览，零动作'}） ---")
    for rec in cleanable:
        copies = sum(1 for e in rec["record"].get("targets", [])
                     if isinstance(e, dict)
                     for k in ("staged", "rollback")
                     if e.get(k) and Path(e[k]).is_file())
        print(f"  可清: {rec['path']} [state={rec['state']}] "
              f"（现场重分类 {rec['level_pure']}；副本 {copies} 个）")
    for f in orphans:
        print(f"  可清孤儿: {f['path']}")
    for r in refused:
        print(f"  ✗ 拒绝: {r['path']} [state={r['state']}] {r['level']} → {r['guidance']}")
    if commit:
        if deleted:
            print(f"  已删除 {len(deleted)} 项（journal/副本/孤儿——manifest 见上列）")
        elif not cleanable and not orphans:
            print("  ✅ 无可清项")
    else:
        if cleanable or orphans:
            print("  预览完成——加 --commit 执行")
        else:
            print("  ✅ 无可清项")
    for w in warnings:
        print(f"  ⚠️ {w}", file=sys.stderr)
    return 1 if refused else 0
