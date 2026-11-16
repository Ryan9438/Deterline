#!/usr/bin/env python3
"""recovery_stress（12 计划 A2）：可重放的恢复故障验证工具——独立进程强杀 +
确定性窗口注入 + 结构化证据（JSONL）。只作用于**本工具创建的临时根**，
opt-in 显式确认；不做真实数据执行（12 §A3：真实历史清理由用户逐次决定）。

方法论（承接 03 §2.2 "SIGKILL 216 实验" 与 12 §A2）：
- 窗口不靠时序竞态，靠子进程在真实代码路径上 hook 注入：
  journal 状态写（pending/committing）、暂存计数（staged）、目标 os.replace
  （after_replace1 / after_replace_all）。命中即 os.kill(SIGKILL)
  （Windows = TerminateProcess，07 §3 条3 的 CI 级覆盖）。
- 每个场景硬编码 oracle（合法终态迁移表）：杀点 → scan 分类 → 合格出口
  （恢复到有证据的前态/后态，或明确拒绝 + 证据保全 + 文档化手工顺序）。
- "无 journal 的不明部分写入算失败"（12 §A2）：任何目标内容偏离前态而
  scan 无 run-journal 记录 → violation。
- 全树哈希对拍：收口后除 {目标合法终态, .bak 备份产物} 外任何文件
  变化/残留 → violation；journal 目录不得残留记录文件。
- 记录带 transactions.py 源 sha——内部重构后旧证据可追溯、hook 失配可发现。

关键实测语义（冒烟轮发现，oracle 依据）：
- journal 的 **pending 记录 staged=None**——staged/rollback 路径要到
  committing 态写才入记录。杀在暂存循环中 = 磁盘上有孤儿 .new 副本但
  记录不知情 → 唯一合法出口 = clean（记录 + 孤儿清扫收口，s9）。
- 杀在 committing 态写后 = 副本已入记录 → apply complete 可继续（s2）。

场景（v1，oracle 见 run_scenario / _expect_final）：
  s1        1 目标  杀在 pending 记录后        → not-started → 双向拒绝（副本缺/非 after）→ clean
  s2        2 目标  杀在 committing 态写后     → not-started → rollback 拒绝 → complete 执行 → clean
  s3        1 目标  杀在 committing 态写后     → not-started → clean（.bak 产物白名单）
  s5a/s5b   2 目标  杀在第 1 次替换后（中断）  → 双向拒绝（证据保全）→ 手工回滚/手工完成 → clean
  s6a/s6b   1 目标  杀在全部替换后             → done-confirm → rollback 执行（回前态）/ 直接 clean（后态有据，目标留 NEW）
  s7a       2 目标（t1 不存在）杀在第 1 次替换后 → [after,not-created] 双拒 → 手工完成 → clean
  s7b       2 目标（t1 不存在）杀在 committing 态写后 → apply complete（not-created v1 blocked）→ interrupted → 手工完成 → clean
  s8        2 目标  阶段A 杀 committing 态写后 + 阶段B apply 中杀 → 混合双拒 → 手工完成 → clean
  s9        2 目标  杀在暂存循环中（journal 仍 staged=None）→ not-started + 孤儿 .new ×4 → clean 连记录带孤儿收口
  s10       1 目标  杀在 journal 原子写内（mkstemp 已落、replace 未行）→ 无记录 + .journal.*.new 残留 → 人工查看后删除（clean 不代删）
  p1_prune  prune/purge 可逆性与 manifest 一致性（journal 保护 + 真删出口；无强杀）

CI：tests/test_recovery_stress.py 跑 s1+s2+s5a+p1（Windows 仅 s1/p1——多窗口
TerminateProcess 语义按 07 §3 条3 保守逐级验证）；全量/随机批次 = 本地 opt-in。

退出码：0=全部场景 verdict pass；1=存在 fail；2=参数/门禁拒绝。
"""

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
TOOL_PATH = Path(__file__).resolve()

STRESS_SCHEMA = "deterline.recovery-stress/v1"
SEED_DEFAULT = 20261116
# R11 P1-1：Windows 无 signal.SIGKILL 常量（Availability: Unix）——
# os.kill(pid, 9) 在 Windows 走 TerminateProcess(9)，与 killed 判定 (-9, 9) 吻合
_SIGKILL = getattr(signal, "SIGKILL", 9)
# R12 P3-2：证据级 caveat（12 §A2 原文）随证据携带
EVIDENCE_SCOPE = ("process-kill-only：证据仅覆盖所测进程中断，"
                  "不能替代断电或文件系统耐久性声明")


# ---------------------------------------------------------------- 记录辅助

def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _transactions_sha() -> str:
    return _sha_file(SCRIPTS / "deterline" / "transactions.py") or "unknown"


def _content_for(seed: int, tag: str, n: int = 64) -> bytes:
    """seed 派生的确定性目标内容（场景间互异；不依赖随机源——可重放）。"""
    basis = f"stress|{seed}|{tag}|".encode()
    body = bytes((seed * (i + 3) + index * 7 + len(basis)) % 251
                 for index, i in enumerate(range(n)))
    return basis + body


# ---------------------------------------------------------------- 子进程调用

def _env() -> dict:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"   # cp1252 控制台教训（07 §3 条0）
    return env


def _run_cli(args: list[str], timeout: float = 60.0) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, str(REPO / "run.py"), *args],
        capture_output=True, timeout=timeout, env=_env(),
        encoding="utf-8", errors="replace")
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def _run_child(phase_args: list[str], timeout: float = 60.0) -> tuple[int, bool, str]:
    """子进程：--child 模式在真实代码路径上打点后自杀。killed=信号死亡。"""
    proc = subprocess.run(
        [sys.executable, str(TOOL_PATH), "--child", *phase_args],
        capture_output=True, timeout=timeout, env=_env(),
        encoding="utf-8", errors="replace")
    killed = proc.returncode in (-9, 9)  # POSIX SIGKILL / Windows TerminateProcess(9)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, killed, out


# ---------------------------------------------------------------- 场景定义

TARGET_COUNTS = {"s1": 1, "s3": 1, "s6a": 1, "s6b": 1,
                 "s2": 2, "s5a": 2, "s5b": 2, "s7a": 2, "s7b": 2, "s8": 2,
                 "s9": 2, "s10": 1}
NOT_CREATED = {"s7a": {1}, "s7b": {1}}            # 这些下标的目标在建景时不存在
KILL_PHASES = {                                    # scenario → [(phase, kill_at)]
    "s1": [("commit", "pending")],
    "s2": [("commit", "committing")],
    "s3": [("commit", "committing")],
    "s5a": [("commit", "after_replace1")],
    "s5b": [("commit", "after_replace1")],
    "s6a": [("commit", "after_replace_all")],
    "s6b": [("commit", "after_replace_all")],
    "s7a": [("commit", "after_replace1")],
    "s7b": [("commit", "committing")],
    "s8": [("commit", "committing"), ("apply", "after_replace1")],
    "s9": [("commit", "staged")],
    "s10": [("commit", "journal_tmp")],   # journal 原子写内杀：.journal.*.new 残留、无记录
}
CLOSURE = {   # 中断后的合格出口（12 §A2：恢复到有证据的前态/后态，或拒绝+手工顺序）
    "s1": "clean_direct",
    "s2": "apply_complete",
    "s3": "clean_direct",
    "s5a": "manual_rollback",   # cp rollback→after 目标 → 全 before → clean
    "s5b": "manual_complete",   # cp staged→before 目标 → 全 after → clean
    "s6a": "apply_rollback",
    "s6b": "clean_done_confirm",   # done-confirm：目标合法留在后态，clean 只摘记录
    "s7a": "manual_complete",   # cp staged→not-created 目标 → 全 after → clean
    "s7b": "apply_then_manual_complete",
    "s8": "manual_complete",
    "s9": "clean_direct",       # 唯一合法出口：journal(无副本) + 孤儿 .new 全由 clean 收口
    "s10": "manual_journal_tmp",  # 合格出口：journal-tmp 人工查看后删除（clean 不代删）
}
# 杀后首次 scan 的期望 level（12 §A2：分类错 = oracle 违规）
EXPECT_LEVELS = {
    "s1": ["not-started"], "s2": ["not-started"], "s3": ["not-started"],
    "s5a": ["interrupted"], "s5b": ["interrupted"],
    "s6a": ["done-confirm"], "s6b": ["done-confirm"],
    "s7a": ["interrupted"], "s7b": ["not-started"], "s8": ["interrupted"],
    "s9": ["not-started"], "s10": [],   # 无 run-journal（记录从未落盘）
}
# 混合分类必须双向整批拒绝且 --commit 零执行的场景
MIXED_REFUSE = {"s1", "s5a", "s5b", "s7a", "s8"}
ALL_SCENARIOS = sorted(TARGET_COUNTS)


# ---------------------------------------------------------------- 子进程主体

def child_main(argv: list[str]) -> int:
    """--child：在真实 transactions/recovery 代码路径上装 hook，命中窗口即
    SIGKILL。若窗口未命中（内部重构失配）→ 打印 KILL_NOT_REACHED 退出 3。"""
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--targets", required=True)   # 逗号分隔目标名
    ap.add_argument("--kill-at", required=True)
    ap.add_argument("--phase", required=True)     # commit | apply
    ap.add_argument("--seed", type=int, required=True)
    args = ap.parse_args(argv)

    # R11 P2-1：child 入口同样受门禁——只接受本工具 mkdtemp 前缀的临时根
    root = Path(args.root)
    if not root.name.startswith("deterline_stress_"):
        print("拒绝：--child 只接受本工具自建的 deterline_stress_ 临时根",
              file=sys.stderr)
        return 2

    sys.path.insert(0, str(SCRIPTS))
    from deterline import transactions  # noqa: E402

    names = args.targets.split(",")
    targets = [root / n for n in names]
    seed = args.seed
    old = {i: _content_for(seed, f"old{i}") for i in range(len(targets))}
    new = {i: _content_for(seed, f"new{i}") for i in range(len(targets))}

    replace_targets = {str(t.resolve()) for t in targets}
    # 暂存计数 = 既有目标的 staged+rollback 两份 + not-created 目标仅 staged 一份
    n_stages_expected = sum(2 if t.exists() else 1 for t in targets)
    fired = {"hit": False}

    def _kill() -> None:
        fired["hit"] = True
        sys.stdout.flush()
        sys.stderr.flush()
        os.kill(os.getpid(), _SIGKILL)

    orig_update = transactions.EditPlan._journal_update
    orig_stage = transactions._stage
    orig_replace = os.replace

    def update(self, path, journal_id, created, state_name, *a, **k):
        orig_update(self, path, journal_id, created, state_name, *a, **k)
        if args.kill_at == "pending" and state_name == "pending":
            _kill()
        if args.kill_at == "committing" and state_name == "committing":
            _kill()

    def stage(target, content, mode):
        result = orig_stage(target, content, mode)
        if args.kill_at == "staged":
            stage.calls = getattr(stage, "calls", 0) + 1
            if stage.calls >= n_stages_expected:
                _kill()
        return result

    def replace(src, dst):
        if (args.kill_at == "journal_tmp"
                and Path(dst).suffix == ".json"
                and Path(dst).parent.name == "journal"):
            # journal 原子写窗口：mkstemp 已落（.journal.*.new 残留）、
            # os.replace 未行（正式记录不存在）——R11 P3-1 第三缺口补景
            _kill()
            return orig_replace(src, dst)
        if (args.kill_at in ("after_replace1", "after_replace_all")
                and str(Path(dst).resolve()) in replace_targets):
            orig_replace(src, dst)
            replace.calls = getattr(replace, "calls", 0) + 1
            if args.kill_at == "after_replace1" and replace.calls >= 1:
                _kill()
            if (args.kill_at == "after_replace_all"
                    and replace.calls >= len(replace_targets)):
                _kill()
        return orig_replace(src, dst)

    transactions.EditPlan._journal_update = update
    transactions._stage = stage
    os.replace = replace          # commit 与 apply 的替换路径都在调用点解析
    try:
        if args.phase == "commit":
            edits = []
            for i, t in enumerate(targets):
                edits.append(transactions.FileEdit(
                    t.resolve(), new[i],
                    None if not t.exists() else _sha_bytes(old[i]),
                    backup=True))
            transactions.EditPlan(tuple(edits)).commit()
        else:  # apply：journal 复用方案 A 的执行路径（recovery cmd 本体）
            from deterline.cmds import recovery  # noqa: E402
            recovery.cmd_recovery_apply(
                save_dir=root, dir_override=str(root / "game.ios"),
                direction="complete", commit=True, json_out=False)
        if not fired["hit"]:
            print("KILL_NOT_REACHED", file=sys.stderr)
            return 3
        return 0  # 不可达（SIGKILL 即时）
    finally:
        os.replace = orig_replace
        transactions._stage = orig_stage
        transactions.EditPlan._journal_update = orig_update


# ---------------------------------------------------------------- 场景执行

def _build_scenario_root(seed: int, scenario: str) -> tuple[Path, dict, dict]:
    root = Path(tempfile.mkdtemp(prefix="deterline_stress_"))
    (root / "game.ios").write_bytes(b"STRESS-GAME")   # --dir 定位锚（零 UTMT）
    old, new = {}, {}
    for i in range(TARGET_COUNTS[scenario]):
        old[i] = _content_for(seed, f"old{i}")
        new[i] = _content_for(seed, f"new{i}")
        if i not in NOT_CREATED.get(scenario, set()):
            (root / f"t{i}.bin").write_bytes(old[i])
    return root, old, new


def _tree_map(root: Path) -> dict:
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(root))] = _sha_file(p) or "unreadable"
    return out


def _tree_violations(root: Path, before: dict, after: dict,
                     targets: list) -> list:
    """除目标终态与 .bak 备份产物外，任何新增/变化/消失都算违规。"""
    tset = {str(t) for t in targets}
    violations = []
    for rel, sha in before.items():
        if str(root / rel) in tset:
            continue  # 目标单独按 oracle 判
        if rel not in after:
            violations.append(f"文件消失: {rel}")
        elif after[rel] != sha:
            violations.append(f"文件被改: {rel}")
    for rel in after:
        if rel not in before and str(root / rel) in tset:
            continue  # not-created 目标被合法建成——终态由 oracle 判
        if rel not in before and not any(
                Path(rel).name.startswith(t.name + ".bak") for t in targets):
            # R11 P3-3：白名单收紧为目标名+.bak 前缀（防任意 *.bak 名放行）
            violations.append(f"计划外新文件: {rel}")
    return violations


def _scan(root: Path):
    rc, out, _ = _run_cli(["--action", "recovery-scan", "--dir", str(root), "--json"])
    try:
        return rc, json.loads(out)
    except ValueError:
        return rc, {"findings": [], "warnings": [f"scan 输出不可解析: {out[:200]}"]}


def _journal_of(scan_json: dict):
    for f in scan_json.get("findings", []):
        if f.get("kind") == "run-journal":
            return f
    return None


def _apply(root: Path, direction: str, commit: bool):
    args = ["--action", "recovery-apply", "--dir", str(root), "--json",
            "--direction", direction]
    if commit:
        args.append("--commit")
    rc, out, _ = _run_cli(args)
    try:
        return rc, json.loads(out)
    except ValueError:
        return rc, {"refusals": [f"输出不可解析: {out[:200]}"]}


def _clean(root: Path, commit: bool):
    args = ["--action", "recovery-clean", "--dir", str(root), "--json"]
    if commit:
        args.append("--commit")
    rc, out, _ = _run_cli(args)
    try:
        return rc, json.loads(out)
    except ValueError:
        return rc, {"refused": [{"guidance": "输出不可解析"}]}


def _manual_closure(root: Path, journal: dict, policy: str, steps: list) -> list:
    """scan 逐条 cp 指引的程序化复刻（shutil.copyfile + 指纹预验）。
    manual_rollback：after 目标 ← rollback；manual_complete：
    before/not-created 目标 ← staged。返回违规列表。"""
    rec = json.loads(Path(journal["path"]).read_text(encoding="utf-8"))
    violations = []
    for i, entry in enumerate(rec.get("targets", [])):
        path = Path(entry["path"])
        current = _sha_file(path)
        is_after = bool(entry.get("after")) and current == entry.get("after")
        if policy == "manual_rollback" and is_after:
            copy, expect = entry.get("rollback"), entry.get("before")
        elif policy == "manual_complete" and not is_after:
            copy, expect = entry.get("staged"), entry.get("after")
        else:
            continue
        if not copy or not Path(copy).is_file() or _sha_file(Path(copy)) != expect:
            violations.append(f"手工收口副本不可用: {path}（copy={copy}）")
            continue
        shutil.copyfile(copy, path)
        if _sha_file(path) != expect:
            violations.append(f"手工收口后指纹不符: {path}")
        steps.append({"step": f"manual_cp[{i}]",
                      "action": f"cp {copy} -> {path}", "rc": 0})
    return violations


def _expect_final(old: dict, new: dict, scenario: str) -> dict:
    """oracle：合格出口决定的唯一合法终态。
    clean_direct/apply_rollback/manual_rollback → 全部回到前态 OLD
    （not-created 目标保持 absent——本矩阵中该组合不存在，防御性标注）；
    clean_done_confirm/apply_complete/manual_complete/apply_then_manual_complete
    → 全部 NEW（done-confirm 的后态有记录证据确认，clean 不回写目标）。"""
    policy = CLOSURE[scenario]
    not_created = NOT_CREATED.get(scenario, set())
    back = policy in ("clean_direct", "apply_rollback", "manual_rollback",
                      "manual_journal_tmp")
    expect = {}
    for i in range(TARGET_COUNTS[scenario]):
        name = f"t{i}.bin"
        if back:
            expect[name] = "(absent)" if i in not_created else _sha_bytes(old[i])
        else:
            expect[name] = _sha_bytes(new[i])
    return expect


def run_scenario(scenario: str, seed: int) -> dict:
    record: dict = {"schema": STRESS_SCHEMA, "scenario": scenario, "seed": seed,
                    "window": KILL_PHASES.get(scenario),
                    "closure": CLOSURE.get(scenario),
                    "transactions_sha": _transactions_sha(),
                    "platform": sys.platform, "python": sys.version.split()[0],
                    "child": [], "steps": [], "violations": [], "verdict": "fail"}

    if scenario == "p1_prune":
        return _run_prune_scenario(seed, record)

    root, old, new = _build_scenario_root(seed, scenario)
    try:
        targets = [root / f"t{i}.bin" for i in range(TARGET_COUNTS[scenario])]
        tree_before = _tree_map(root)

        # 1) 子进程强杀（真实代码路径 + 确定性窗口）
        names = ",".join(t.name for t in targets)
        for phase, kill_at in KILL_PHASES[scenario]:
            rc, killed, out = _run_child(["--root", str(root), "--targets", names,
                                          "--kill-at", kill_at, "--phase", phase,
                                          "--seed", str(seed)])
            record["child"].append({"phase": phase, "kill_at": kill_at,
                                    "returncode": rc, "killed": killed})
            if not killed:
                record["violations"].append(
                    "子进程窗口未命中（phase=%s kill_at=%s rc=%s）tail=%s"
                    % (phase, kill_at, rc, out[-200:]))

        # 2) 杀后扫描：分类必须与 oracle 对上；偏离前态必须有 journal
        rc, scan1 = _scan(root)
        journal = _journal_of(scan1)
        levels = [f.get("level") for f in scan1.get("findings", [])
                  if f.get("kind") == "run-journal"]
        record["steps"].append({"step": "scan_after_kill", "rc": rc,
                                "levels": levels})
        replaced_any = any(t.exists() and _sha_file(t) != _sha_bytes(old[i])
                           for i, t in enumerate(targets))
        if replaced_any and journal is None:
            # 12 §A2：无 journal 的不明部分写入算失败
            record["violations"].append("目标已偏离前态但无 run-journal——不明写入")
        # R11 P3-1 副本半边：记录 journal 引用的 staged/rollback 副本哈希
        if journal is not None:
            try:
                rec = json.loads(Path(journal["path"]).read_text(encoding="utf-8"))
                copy_hashes = {}
                for entry in rec.get("targets", []):
                    for key in ("staged", "rollback"):
                        copy = entry.get(key) if isinstance(entry, dict) else None
                        if copy and Path(copy).is_file():
                            copy_hashes[copy] = _sha_file(Path(copy))
                if copy_hashes:
                    record["copy_hashes"] = copy_hashes
            except (OSError, ValueError):
                pass
        if levels != EXPECT_LEVELS[scenario]:
            record["violations"].append(
                "scan 分类不符: %s != 期望 %s" % (levels, EXPECT_LEVELS[scenario]))

        # 3) 拒绝面（12 §A2：明确拒绝 + 证据保全）与执行面（按政策）
        policy = CLOSURE[scenario]
        if scenario in MIXED_REFUSE:
            for direction in ("rollback", "complete"):
                rc_a, apply_json = _apply(root, direction, commit=False)
                refused = bool(apply_json.get("refusals"))
                record["steps"].append({"step": f"apply_refusal[{direction}]",
                                        "rc": rc_a, "refused": refused})
                if not refused:
                    record["violations"].append(
                        f"混合分类未被拒绝（{direction}）——应整批拒绝")
                rc_c, _apply_json = _apply(root, direction, commit=True)
                record["steps"].append({
                    "step": f"apply_commit_refused[{direction}]", "rc": rc_c})
                if rc_c != 1:
                    record["violations"].append(
                        f"--commit 混合分类应拒绝（rc={rc_c}, {direction}）")
        if policy == "apply_complete":
            rc_a, apply_json = _apply(root, "rollback", commit=False)
            if not apply_json.get("refusals"):
                record["violations"].append("not-started 状态 rollback 未拒绝")
            record["steps"].append({"step": "apply_rollback_refused", "rc": rc_a})
            rc_x, apply_json = _apply(root, "complete", commit=True)
            record["steps"].append({"step": "apply_complete_commit", "rc": rc_x,
                                    "done": len(apply_json.get("done", []))})
            if rc_x != 0 or not apply_json.get("done"):
                record["violations"].append("apply complete 执行失败")
        elif policy == "apply_rollback":
            rc_x, apply_json = _apply(root, "rollback", commit=True)
            record["steps"].append({"step": "apply_rollback_commit", "rc": rc_x,
                                    "done": len(apply_json.get("done", []))})
            if rc_x != 0 or not apply_json.get("done"):
                record["violations"].append("apply rollback 执行失败")
        elif policy == "apply_then_manual_complete":
            # s7b：apply complete 执行（not-created 目标 blocked，v1 口径）
            rc_x, apply_json = _apply(root, "complete", commit=True)
            record["steps"].append({"step": "apply_complete_commit", "rc": rc_x,
                                    "done": len(apply_json.get("done", [])),
                                    "refusals": apply_json.get("refusals")})
            if rc_x != 0 or not apply_json.get("done"):
                record["violations"].append("apply complete 执行失败")

        # s7b 特有：apply complete 对 not-created 目标 blocked（v1 不处理）→
        # 记录重分类为 interrupted（诚实登记，不猜测宣布已应用）
        if scenario == "s7b":
            rc, scan2 = _scan(root)
            levels2 = [f.get("level") for f in scan2.get("findings", [])
                       if f.get("kind") == "run-journal"]
            record["steps"].append({"step": "scan_after_apply", "rc": rc,
                                    "levels": levels2})
            if levels2 != ["interrupted"]:
                record["violations"].append(
                    f"apply 后重分类不符: {levels2} != ['interrupted']")

        # 4) 手工收口（12 §A2 文档化顺序的程序化复刻）
        if scenario == "s10":
            # journal-tmp：clean 不代删（宁缺毋滥）——人工查看后删除是
            # 文档化出口；目标从未被替换，终态 = 前态
            jtmp = [f for f in scan1.get("findings", [])
                    if f.get("kind") == "journal-tmp"]
            if not jtmp:
                record["violations"].append("s10 未报告 journal-tmp 残留")
            for f in jtmp:
                Path(f["path"]).unlink(missing_ok=True)
            record["steps"].append({"step": "manual_journal_tmp_delete",
                                    "count": len(jtmp), "rc": 0})
        if policy in ("manual_rollback", "manual_complete",
                      "apply_then_manual_complete"):
            rc, scan_now = _scan(root)
            journal = _journal_of(scan_now)
            if journal is None:
                record["violations"].append("手工收口时 journal 消失")
            else:
                record["violations"].extend(_manual_closure(
                    root, journal,
                    "manual_complete" if policy == "apply_then_manual_complete"
                    else policy,
                    record["steps"]))

        # 5) 清理 + 终验
        rc_c, clean_json = _clean(root, commit=True)
        record["steps"].append({"step": "clean_commit", "rc": rc_c})
        if rc_c != 0:
            record["violations"].append(
                f"clean 未全清（rc={rc_c}）: {clean_json.get('refused')}")
        rc, scan_end = _scan(root)
        if scan_end.get("findings"):
            record["violations"].append("收尾扫描仍有 findings")
        if any(root.glob(".*.new")):
            record["violations"].append("根目录残留暂存 .new 文件")
        journal_dir = root / ".deterline" / "journal"
        if journal_dir.exists() and any(journal_dir.glob("*.json")):
            record["violations"].append("journal 目录残留记录文件")
        # s9 特有：孤儿清扫必须报告过（证据保全面）
        if scenario == "s9" and not any(
                f.get("kind") == "orphan-staged"
                for f in scan1.get("findings", [])):
            record["violations"].append("s9 未报告孤儿暂存（清扫证据缺失）")

        # 6) 终态 oracle + 全树对拍
        expect = _expect_final(old, new, scenario)
        for t in targets:
            actual = "(absent)" if not t.exists() else _sha_file(t)
            if actual != expect[t.name]:
                record["violations"].append(
                    f"终态不符: {t.name} {actual} != {expect[t.name]}")
        record["violations"].extend(
            _tree_violations(root, tree_before, _tree_map(root), targets))
        record["final_hashes"] = {t.name: ("(absent)" if not t.exists()
                                           else _sha_file(t)) for t in targets}
        record["verdict"] = "pass" if not record["violations"] else "fail"
        return record
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _run_prune_scenario(seed: int, record: dict) -> dict:
    """p1：可逆 prune 的批次/manifest 一致性 + journal 保护 + purge 真删出口。
    无强杀（prune/purge 的中断语义在 07 §3 条3 同一挂账下，v1 不注入）。"""
    root = Path(tempfile.mkdtemp(prefix="deterline_stress_p1_"))
    try:
        game = root / "game.ios"
        game.write_bytes(b"STRESS-GAME")
        archives = []
        for k in range(4):   # 4 份时间戳归档（keep_archives=2）
            arch = root / f"game.ios.bak.2026110{k}_000000_{k}"
            arch.write_bytes(_content_for(seed, f"arch{k}"))
            archives.append(arch)
        # journal 保护：引用第 0 份归档为 rollback 副本 → 永不进入删除集
        journal_dir = root / ".deterline" / "journal"
        journal_dir.mkdir(parents=True)
        (journal_dir / "protect_probe.json").write_text(json.dumps({
            "schema": "deterline.run-journal/v1", "id": "protect_probe",
            "state": "pending", "pid": 0, "created": "2026-01-01T00:00:00",
            "updated": "2026-01-01T00:00:00",
            "targets": [{"path": str(game), "before": None, "after": None,
                         "staged": None, "rollback": str(archives[0]),
                         "backup": False}],
        }, ensure_ascii=False), encoding="utf-8")

        rc, out, _ = _run_cli(["--action", "backup-prune", "--dir", str(root),
                               "--json", "--commit", "--keep-archives", "2"])
        record["steps"].append({"step": "prune_commit", "rc": rc})
        try:
            prune_json = json.loads(out)
        except ValueError:
            record["violations"].append("prune 输出不可解析")
            prune_json = {}
        if rc != 0:
            record["violations"].append(f"prune --commit rc={rc}")
        committed = prune_json.get("commit") or {}   # JSON 块名 = commit（v2.5.8 口径）
        moved = committed.get("moved") or []
        manifest_path = committed.get("manifest")
        if not moved or not manifest_path:
            record["violations"].append("prune 未产出 moved/manifest")
        # oracle：最旧两份中第 0 份受保护 → 恰移动第 1 份
        if moved and len(moved) == 1:
            if Path(moved[0]["original_path"]).name != archives[1].name:
                record["violations"].append(
                    "删除集不符: %s != %s" % (moved[0]["original_path"],
                                             archives[1].name))
        elif moved:
            record["violations"].append(f"删除集数量不符: {len(moved)} != 1")
        if not archives[0].exists():
            record["violations"].append("journal 引用文件被移动——保护失效")
        # manifest 一致性：schema + 每条 moved 的指纹与盘上实际文件一致
        if manifest_path and Path(manifest_path).is_file():
            manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
            if manifest.get("schema") != "deterline.pruned-manifest/v1":
                record["violations"].append("manifest schema 不符")
            for entry in manifest.get("entries", []):
                dest = Path(entry["moved_to"])
                if not dest.is_file():
                    record["violations"].append(f"manifest 目标缺失: {dest}")
                elif _sha_file(dest) != entry.get("sha256"):
                    record["violations"].append(f"manifest 指纹不符: {dest}")
                if Path(entry["original_path"]).exists():
                    record["violations"].append(f"原文件仍在: {entry['original_path']}")
                if Path(entry["original_path"]).name == archives[0].name:
                    record["violations"].append("受保护归档进入 manifest")
        else:
            record["violations"].append("manifest 文件缺失")
        # prune-purge：批次整体消失（真删出口）
        rc_p, out_p, _ = _run_cli(["--action", "prune-purge", "--dir", str(root),
                                   "--json", "--commit"])
        record["steps"].append({"step": "purge_commit", "rc": rc_p})
        if rc_p != 0:
            record["violations"].append(f"purge rc={rc_p}: {out_p[-200:]}")
        pruned_root = root / ".deterline" / "pruned"
        if pruned_root.exists() and any(pruned_root.iterdir()):
            record["violations"].append("purge 后批次残留")
        record["verdict"] = "pass" if not record["violations"] else "fail"
        return record
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------- 入口

def main(argv: list) -> int:
    ap = argparse.ArgumentParser(
        description="恢复故障可重放验证（12 计划 A2）——只作用于工具自建临时根")
    ap.add_argument("--out", default=None, help="JSONL 证据输出目录（默认 tmp 下新建）")
    ap.add_argument("--seed", type=int, default=SEED_DEFAULT)
    ap.add_argument("--batches", type=int, default=1,
                    help="随机批次扩展（12 §A2）：以 seed+i 派生重复全场景 N 轮")
    ap.add_argument("--scenarios", default=",".join(ALL_SCENARIOS + ["p1_prune"]),
                    help="逗号分隔场景 id（默认全部）")
    ap.add_argument("--confirm-synthetic", action="store_true",
                    help="显式确认：仅合成临时根，不含真实数据（必填门禁）")
    args = ap.parse_args(argv)

    if not args.confirm_synthetic:
        print("拒绝执行：本工具做进程强杀实验，仅作用于自建临时根。\n"
              "确认不含真实数据请加 --confirm-synthetic。", file=sys.stderr)
        return 2

    scenarios = [s.strip() for s in args.scenarios.split(",") if s.strip()]
    valid = set(ALL_SCENARIOS) | {"p1_prune"}
    unknown = [s for s in scenarios if s not in valid]
    if unknown:
        print(f"未知场景: {unknown}（可选 {sorted(valid)}）", file=sys.stderr)
        return 2

    out_dir = Path(args.out) if args.out else Path(
        tempfile.mkdtemp(prefix="deterline_stress_out_"))
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl = out_dir / f"stress_{time.strftime('%Y%m%d_%H%M%S')}_{args.seed}.jsonl"

    header = {
        "schema": STRESS_SCHEMA, "kind": "run-header",
        "seed": args.seed, "scenarios": scenarios,
        "batches": args.batches,
        "evidence_scope": EVIDENCE_SCOPE,   # R12 P3-2：证据级 caveat 随证据携带
        "transactions_sha": _transactions_sha(),
        "platform": sys.platform, "python": sys.version.split()[0],
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    records = [header]
    for batch in range(max(int(args.batches), 1)):
        batch_seed = args.seed + batch
        for scenario in scenarios:
            try:
                record = run_scenario(scenario, batch_seed)
            except Exception as exc:  # R11 P3-3：场景级失败不炸整轮
                record = {"schema": STRESS_SCHEMA, "scenario": scenario,
                          "seed": batch_seed, "verdict": "error",
                          "violations": [f"场景执行异常: {exc!r}"],
                          "window": KILL_PHASES.get(scenario),
                          "closure": CLOSURE.get(scenario),
                          "child": [], "steps": [],
                          "transactions_sha": _transactions_sha()}
            record["batch"] = batch
            records.append(record)
            print(f"  [{batch}] {scenario}: {record['verdict']}"
                  + ("" if record["verdict"] == "pass"
                     else f" — {record['violations'][:3]}"))
    jsonl.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
        encoding="utf-8")
    fails = [r for r in records[1:] if r.get("verdict") != "pass"]
    print(f"=== recovery-stress：{len(scenarios) - len(fails)}/{len(scenarios)} pass；"
          f"证据 {jsonl} ===")
    return 1 if fails else 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--child" in argv:   # 子进程模式：先于主解析分发（--seed 等同名参数不冲突）
        sys.exit(child_main([a for a in argv if a != "--child"]))
    sys.exit(main(argv))
