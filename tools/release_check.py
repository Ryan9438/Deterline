#!/usr/bin/env python3
"""候选版发布自检（03 §2.6）：干净检出核对 + 版本链 + 测试 + 文档一致性。

用法:
  python3 tools/release_check.py            # 全量自检（单测 + 全部核对）
  python3 tools/release_check.py --skip-tests  # 快检（版本链/文档/分发/入口）

退出码 0=全部通过；1=有失败项。全程只读（install.py --check 本身只读）。
"""

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

VERSION_FILES = [
    ("run.py", '__version__ = "([^"]+)"'),
    ("install.py", '__version__ = "([^"]+)"'),
    ("scripts/bg_generator.py", '__version__ = "([^"]+)"'),
    ("scripts/modify_save.py", '__version__ = "([^"]+)"'),
    ("scripts/deterline/__init__.py", '__version__ = "([^"]+)"'),
    ("scripts/commands.json", '"version": "([^"]+)"'),
    ("SKILL.md", r"## 技能版本\n\n([0-9.]+)"),
    ("README.md", r"Agent Skill 完整文档（v?([0-9.]+)）"),
]

DISTRIBUTION_FILES = [
    "run.py", "install.py", "README.md", "SKILL.md", "COMMANDS.md",
    "scripts/commands.json", "scripts/modify_save.py", "tools/gen_docs.py",
    "scripts/deterline/cli.py", "scripts/deterline/cmds/recovery.py",
    "tests/golden/help_run.txt", "tests/golden/help_modify_save.txt",
]


def _run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO), **kw)


def check_version_chain(failures):
    import re
    versions = {}
    for rel, pattern in VERSION_FILES:
        text = (REPO / rel).read_text(encoding="utf-8")
        m = re.search(pattern, text)
        if not m:
            failures.append(f"{rel}: 未找到版本声明（pattern {pattern}）")
            continue
        versions[rel] = m.group(1)
    distinct = set(versions.values())
    if len(distinct) != 1:
        failures.append("版本链不一致: " + "; ".join(
            f"{k}={v}" for k, v in versions.items()))
    else:
        print(f"  ✓ 版本链单点一致: {distinct.pop()}")


def check_generated_docs(failures):
    r = _run([sys.executable, "tools/gen_docs.py", "--check"])
    if r.returncode != 0:
        failures.append(f"gen_docs --check 失败: {r.stdout[-200:]}{r.stderr[-200:]}")
    else:
        print("  ✓ 文档生成与 commands.json 逐字节一致")


def check_help_goldens(failures):
    import os
    for script, golden in (("run.py", "help_run.txt"),
                           ("scripts/modify_save.py", "help_modify_save.txt")):
        r = _run([sys.executable, script, "--help"],
                 env={**os.environ, "COLUMNS": "80"})
        expected = (REPO / "tests" / "golden" / golden).read_text(encoding="utf-8")
        if r.returncode != 0:
            failures.append(f"{script} --help 退出码 {r.returncode}")
        elif r.stdout != expected:
            failures.append(f"{script} --help 与 golden 不一致: {golden}")
        else:
            print(f"  ✓ --help golden 逐字节一致: {golden}")


def check_distribution(failures):
    import json
    commands = json.loads((REPO / "scripts" / "commands.json").read_text(encoding="utf-8"))
    actions = [c["action"] for c in commands["commands"]]
    handlers_src = (REPO / "scripts" / "deterline" / "command_handlers.py").read_text(encoding="utf-8")
    missing = [a for a in actions if f'"{a}"' not in handlers_src]
    if missing:
        failures.append(f"commands.json 的 {len(missing)} 个 action 在注册表缺失: {missing[:5]}")
    else:
        print(f"  ✓ 命令注册表覆盖全部 {len(actions)} 个 action")
    for rel in DISTRIBUTION_FILES:
        if not (REPO / rel).exists():
            failures.append(f"分发内容缺失: {rel}")
    if not failures or not any(f.startswith("分发内容缺失") for f in failures):
        print(f"  ✓ 分发关键文件齐全（{len(DISTRIBUTION_FILES)} 项抽检）")


def check_install_entry(failures):
    r = _run([sys.executable, "install.py", "--check"])
    # fresh/CI 环境无 .NET/UTMT → rc=1 属预期（入口可运行即达标）
    if r.returncode not in (0, 1):
        failures.append(f"install.py --check 异常退出码 {r.returncode}: {r.stderr[-200:]}")
    else:
        print(f"  ✓ install.py --check 入口可运行（rc={r.returncode}；"
              + ("环境齐备" if r.returncode == 0 else "部分组件缺失属 CI/fresh 预期") + ")")


def check_tests(failures):
    r = _run([sys.executable, "-m", "unittest", "discover", "-s", "tests"])
    tail = (r.stdout + r.stderr).strip().splitlines()
    summary = next((l for l in reversed(tail) if l.startswith("Ran ")), "?")
    if r.returncode != 0:
        failures.append(f"全量单测失败（{summary}）")
    else:
        print(f"  ✓ {summary}（skipped 为 opt-in 集成）")


def check_git_clean(failures):
    r = _run(["git", "status", "--porcelain"])
    dirty = [l for l in r.stdout.splitlines() if l.strip() and not l.startswith("?? .github")]
    if dirty:
        failures.append(f"工作树不干净（候选版必须提交态）: {dirty[:3]}")
    else:
        print("  ✓ 工作树干净（提交态）")


def main():
    parser = argparse.ArgumentParser(description="候选版发布自检（03 §2.6）")
    parser.add_argument("--skip-tests", action="store_true",
                        help="跳过全量单测（快检）")
    args = parser.parse_args()

    print(f"--- release_check（{REPO.name}） ---")
    failures = []
    check_git_clean(failures)
    check_version_chain(failures)
    check_generated_docs(failures)
    check_help_goldens(failures)
    check_distribution(failures)
    check_install_entry(failures)
    if not args.skip_tests:
        check_tests(failures)
    if failures:
        print(f"--- {len(failures)} 项失败: ")
        for f in failures:
            print(f"  ✗ {f}")
        return 1
    print("--- 发布自检全部通过 ✓ ---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
