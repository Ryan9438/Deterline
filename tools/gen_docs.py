#!/usr/bin/env python3
"""O1b 文档生成器：从 scripts/commands.json（SSOT）生成三份文档的命令总表。

机制：节替换（marker 之间整段替换）+ 漂移检查（--check 退出码 1）。
三份文档（SKILL.md / COMMANDS.md / README.md）嵌入**逐字节相同**的生成区块，
因此三份命令表不可能互相漂移；与代码的漂移由 test_docs_lint 校验
（action 集合必须与 modify_save.py --action choices 完全一致）。

用法：
    python3 tools/gen_docs.py           # 重新生成（改 commands.json 之后运行）
    python3 tools/gen_docs.py --check   # 只检查漂移，不写入（CI/lint 用）

手工规则：文档内 marker 区块之间的内容勿手改；要改命令表，改 commands.json。
"""

import argparse
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = ROOT / "scripts" / "commands.json"
SCRIPT = ROOT / "scripts" / "modify_save.py"
TARGETS = [ROOT / "SKILL.md", ROOT / "COMMANDS.md", ROOT / "README.md"]

BEGIN_MARK = "<!-- BEGIN generated:commands (SSOT: scripts/commands.json · python3 tools/gen_docs.py 生成，勿手改) -->"
END_MARK = "<!-- END generated:commands -->"
BLOCK_RE = re.compile(
    re.escape("<!-- BEGIN generated:commands") + r"[^>]*-->.*?" + re.escape(END_MARK),
    re.DOTALL)

VERIFY_ORDER = ["static", "sandbox", "in-game"]
VERIFY_LEGEND = ("验证级别（验收总原则，见 AUDIT_2026-11-07/01-ROADMAP §六）："
                 "**static** = 反编译/代码审查 · "
                 "**sandbox** = 沙箱副本注入实测 · "
                 "**in-game** = 游戏内启动实测")


def load_data() -> dict:
    return json.loads(JSON_PATH.read_text(encoding="utf-8"))


def authoritative_actions() -> list:
    """提取 --action choices（权威命令集合）。

    O2-step0（研讨会2/01 §1.4 地雷 #2）：拆包后优先 import deterline.cli 读
    ACTION_CHOICES（对排版免疫）；单文件期走旧正则（fallback，对 modify_save.py
    的特定排版敏感——拆包完成后可删）。
    """
    pkg_cli = SCRIPT.parent / "deterline" / "cli.py"
    if pkg_cli.exists():
        sp = str(SCRIPT.parent)
        if sp not in sys.path:
            sys.path.insert(0, sp)
        try:
            import deterline.cli as cli_mod
            actions = list(getattr(cli_mod, "ACTION_CHOICES"))
        except (ImportError, AttributeError) as e:
            raise RuntimeError(
                f"import deterline.cli 失败（拆包过渡期 cli 半成品？）: {e!r}——"
                f"请完成 cli.py 的 ACTION_CHOICES 或暂回退正则路径") from e
        if len(set(actions)) != len(actions):
            raise RuntimeError("deterline.cli ACTION_CHOICES 含重复项")
        return actions
    # fallback：单文件期正则提取
    src = SCRIPT.read_text(encoding="utf-8")
    m = re.search(r'choices=\[(.*?)\]\)\n    parser\.add_argument\("--key"', src, re.DOTALL)
    if not m:
        raise RuntimeError("未能在 modify_save.py 中定位 --action choices 块")
    actions = ast.literal_eval("[" + m.group(1) + "]")
    if len(set(actions)) != len(actions):
        raise RuntimeError("modify_save.py choices 含重复项")
    return actions


def validate_json(data: dict) -> list:
    """结构性校验；返回问题列表（空 = 通过）。"""
    problems = []
    try:
        actions = authoritative_actions()
    except RuntimeError as e:
        return [f"authoritative: {e}"]
    cmds = data.get("commands", [])
    json_actions = [c.get("action") for c in cmds]

    dupes = sorted({a for a in json_actions if json_actions.count(a) > 1})
    if dupes:
        problems.append(f"commands.json 重复条目: {dupes}")
    missing = sorted(set(actions) - set(json_actions))
    extra = sorted(set(json_actions) - set(actions))
    if missing:
        problems.append(f"argparse 有而 commands.json 缺: {missing}")
    if extra:
        problems.append(f"commands.json 有而 argparse 无: {extra}")

    group_ids = [g["id"] for g in data.get("groups", [])]
    if len(set(group_ids)) != len(group_ids):
        problems.append(f"groups id 重复: {group_ids}")
    for c in cmds:
        a = c.get("action", "?")
        if c.get("group") not in group_ids:
            problems.append(f"{a}: group {c.get('group')!r} 不在 groups 中")
        if c.get("verify") not in VERIFY_ORDER:
            problems.append(f"{a}: verify {c.get('verify')!r} 非法（{VERIFY_ORDER}）")
        ex = c.get("example", "")
        if not ex.startswith(a):
            problems.append(f"{a}: example 必须以 action 名开头，现为 {ex[:40]!r}")
        if not c.get("summary"):
            problems.append(f"{a}: 缺 summary")
        for k in ("action", "group", "verify", "summary", "example"):
            if k not in c:
                problems.append(f"{a}: 缺字段 {k}")
    return problems


def render_inner(data: dict) -> str:
    """渲染 marker 之间的内容（不含 marker 本身）。无时间戳——逐字节可复现。"""
    groups = {g["id"]: g for g in data["groups"]}
    by_group = {gid: [] for gid in groups}
    for c in data["commands"]:
        by_group[c["group"]].append(c)

    out = [
        f"> 全量 {len(data['commands'])} 个命令 · 版本 {data['version']} · "
        f"由 `scripts/commands.json` 生成（改命令表 → 改 json → `python3 tools/gen_docs.py`）",
        f"> {VERIFY_LEGEND}",
        "",
    ]
    for g in data["groups"]:
        members = by_group[g["id"]]
        out.append(f"### {g['icon']} {g['title']} — {g['desc']}")
        out.append("")
        out.append("| 命令 | 功能 | 验证 |")
        out.append("|---|---|---|")
        for c in members:
            summary = c["summary"].replace("|", "\\|")
            example = c["example"].replace("|", "\\|")
            out.append(f"| `{example}` | {summary} | {c['verify']} |")
        noted = [c for c in members if c.get("notes")]
        if noted:
            out.append("")
            for c in noted:
                for note in c["notes"]:
                    note = note.replace("|", "\\|")
                    out.append(f"> ⚠️ `{c['action']}`: {note}")
        out.append("")
    # 去掉末尾多余空行（保留一个换行结尾）
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out) + "\n"


def render_block(data: dict) -> str:
    return f"{BEGIN_MARK}\n{render_inner(data)}{END_MARK}"


def check() -> list:
    """检查三份文档的生成区块；返回漂移列表（空 = 全部同步）。"""
    problems = []
    data = load_data()
    problems.extend(validate_json(data))
    expected = render_block(data)
    for path in TARGETS:
        if not path.exists():
            problems.append(f"{path.name}: 文件缺失")
            continue
        text = path.read_text(encoding="utf-8")
        found = BLOCK_RE.findall(text)
        if len(found) != 1:
            problems.append(
                f"{path.name}: 应有且仅有 1 个生成区块，实为 {len(found)}"
                f"（添加 {BEGIN_MARK[:40]}…/{END_MARK} 标记对）")
            continue
        if found[0] != expected:
            problems.append(
                f"{path.name}: 生成区块与 commands.json 不一致"
                f"（运行 python3 tools/gen_docs.py 同步）")
    return problems


def apply_changes():
    """就地替换全部目标文档的生成区块；返回 (改动的文件名列表, 校验问题列表)。"""
    data = load_data()
    problems = validate_json(data)
    if problems:
        return [], problems
    block = render_block(data)
    changed = []
    for path in TARGETS:
        text = path.read_text(encoding="utf-8")
        new_text, n = BLOCK_RE.subn(lambda _m: block, text)
        if n != 1:
            raise RuntimeError(
                f"{path.name}: 应有且仅有 1 个生成区块，实为 {n}（先手工加标记对）")
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            changed.append(path.name)
    return changed, []


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="只检查漂移，不写入")
    args = ap.parse_args()
    if args.check:
        problems = check()
        if problems:
            print("漂移检查失败：")
            for p in problems:
                print(f"  - {p}")
            return 1
        print(f"OK：{len(TARGETS)} 份文档命令表与 commands.json 逐字节一致")
        return 0
    changed, problems = apply_changes()
    if problems:
        print("commands.json 校验失败：")
        for p in problems:
            print(f"  - {p}")
        return 1
    if changed:
        print("已更新: " + ", ".join(changed))
    else:
        print("无变化（三份文档已是最新）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
