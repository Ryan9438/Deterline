"""恢复域命令（03 §2.2c）：未完结运行记录的只读扫描 + 可预览恢复指引。

recovery-scan：扫描 game 旁 / 存档目录旁两处 `.deterline/journal/*.json`
（transactions 落盘的运行记录），按目标当前内容 vs 记录的 before/after 哈希
分类中断窗口，输出可预览的恢复动作（精确到 cp 命令）；孤儿暂存文件
（`.{name}.*.new` 且无记录引用）单独列出。零写盘、零 UTMT、零恢复执行
——执行恢复/清理留待 recovery-apply/clean（下批）。

退出码：无未完结项 0；发现任何记录/孤儿 1；两侧定位均失败 2
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


def cmd_recovery_scan(save_dir: Path | None, dir_override: str | None = None,
                      json_out: bool = False) -> int:
    """只读扫描：未完结运行记录 + 孤儿暂存 → 分类 + 可预览恢复指引。

    返回 0=无未完结项；1=发现；2=两侧定位均失败。--json 时 stdout 纯 JSON
    （schema deterline.recovery-scan/v1），warnings 进 JSON 不进 stderr。
    """
    warnings: list[str] = []
    findings: list[dict] = []

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
              f"recovery-apply/clean 下批提供） ---")
    return 1 if findings else 0
