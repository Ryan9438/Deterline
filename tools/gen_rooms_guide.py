#!/usr/bin/env python3
"""ROOMS_GUIDE 草稿生成器（阶段 3.2 首切片，2026-11-13）。

输入：rooms-scan JSON（tools/scan_rooms.py 产出，分类 SSOT）+ rooms.json
映射。输出：**草稿** `ROOMS_GUIDE.draft.md`（绝不覆盖正式 ROOMS_GUIDE.md
——重生成须审批，03 §3.2 / 议会裁决）。同一输入重跑输出逐字节稳定。

附带映射体检（03 §3.2）：rooms.json ID/中文名双射、rooms_reverse.json
一致性、扫描房名覆盖率（未登记名单列出）。
"""

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SECTION_ORDER = ["D-candidate", "B1", "B2", "A", "uncategorized"]
SECTION_TITLES = {
    "D-candidate": "D 候选（多层视差启发式——人工复核带依据）",
    "B1": "B1 数据驱动背景（启用层含 BackgroundDefinition）",
    "B2": "B2 对象驱动背景（obj_backgrounder_* 实例）",
    "A": "A 纯 Tile",
    "uncategorized": "未归类（零背景观测——人工归类）",
}


def validate_mapping(rooms: dict, reverse: dict) -> list[str]:
    """rooms.json（id→中文名）与 rooms_reverse.json（中文名→id）双向体检。"""
    problems = []
    if len(rooms) != len(reverse):
        problems.append(f"双射断裂：rooms.json {len(rooms)} 条 vs reverse {len(reverse)} 条"
                        "（存在同名异 ID 或漏登记）")
    for rid, name in rooms.items():
        back = reverse.get(name)
        if back is None:
            problems.append(f"reverse 缺中文名: id={rid} name={name}")
        elif str(back) != str(rid):
            problems.append(f"reverse 指向不一致: id={rid} name={name} → reverse={back}")
    for name, rid in reverse.items():
        if name not in rooms.values():
            problems.append(f"reverse 中文名不在 rooms.json 值集: {name} → {rid}")
    return problems


def render_guide(data: dict, rooms: dict, problems: list[str]) -> str:
    lines = [
        "# ROOMS_GUIDE 草稿（自动生成——重生成须审批，勿直接覆盖正式文档）",
        "",
        f"- schema: {data['schema']}",
        f"- 源文件 md5: `{data['source_md5']}`",
        f"- 采集时间: {data['captured_at']}",
        f"- 房间总数: {data['room_count']}",
        f"- 分类统计: " + "、".join(
            f"{k}={v}" for k, v in sorted(
                data.get("summary", {}).get("by_classification", {}).items())),
        "",
        "## 映射体检（03 §3.2）",
        "",
    ]
    if problems:
        lines.append(f"⚠️ {len(problems)} 项问题：")
        lines.extend(f"- {p}" for p in problems)
    else:
        lines.append(f"✓ rooms.json ({len(rooms)} 条) 与 reverse 双射一致")
    lines.append("")

    scan_names = set(data["rooms"])
    unregistered = sorted(n for n, o in data["rooms"].items()
                          if str(o.get("idx")) not in rooms)
    registered = scan_names - set(unregistered)
    lines.append(f"扫描房名覆盖：登记 {len(registered)} / 未登记 {len(unregistered)}"
                 "（未登记房以“（未登记）”标注，登记走 rooms.json）")
    if unregistered:
        lines.append("")
        lines.append("未登记名单（前 20）：")
        lines.extend(f"- {n}" for n in unregistered[:20])
    lines.append("")

    for section in SECTION_ORDER:
        members = sorted(n for n, o in data["rooms"].items()
                         if o["classification"] == section)
        lines.append(f"## {SECTION_TITLES[section]}（{len(members)}）")
        lines.append("")
        if not members:
            lines.append("（无）")
            lines.append("")
            continue
        for name in members:
            obs = data["rooms"][name]
            rid_key = str(obs.get("idx"))
            if rid_key in rooms:
                cn, rid = rooms[rid_key], f" id={rid_key}"
            else:
                cn, rid = "（未登记）", f" id={rid_key}"
            bgs = "、".join(obs["bg_enabled"]) or "—"
            objs = "、".join(obs["objects"][:6]) or "—"
            more = f"（共 {len(obs['objects'])} 种对象）" if len(obs["objects"]) > 6 else ""
            lines.append(
                f"- `{name}`{rid} — {cn} | {obs['size']} | 实例 {obs['instances']}"
                f" | Tile {obs['tiles']} | 启用背景: {bgs} | 对象: {objs}{more}")
            lines.append(f"  - 理由: {obs['classification_reason']}")
        lines.append("")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="ROOMS_GUIDE 草稿生成（03 §3.2 首切片）")
    parser.add_argument("--scan", default="rooms_scan.json",
                        help="rooms-scan JSON（tools/scan_rooms.py 产出）")
    parser.add_argument("--out", default="ROOMS_GUIDE.draft.md",
                        help="草稿输出路径（默认不覆盖正式文档）")
    args = parser.parse_args()

    scan_path = Path(args.scan)
    if not scan_path.is_file():
        print(f"错误: scan JSON 不存在: {scan_path}", file=sys.stderr)
        return 1
    data = json.loads(scan_path.read_text(encoding="utf-8"))
    rooms = json.loads((REPO / "scripts" / "rooms.json").read_text(encoding="utf-8"))
    reverse = json.loads((REPO / "scripts" / "rooms_reverse.json").read_text(encoding="utf-8"))

    problems = validate_mapping(rooms, reverse)
    text = render_guide(data, rooms, problems)
    Path(args.out).write_text(text, encoding="utf-8")
    print(f"✓ 草稿 → {args.out}（{data['room_count']} 房；映射体检 "
          f"{'⚠️ ' + str(len(problems)) + ' 项' if problems else '通过'}）")
    print("  重生成须审批——本命令不触碰正式 ROOMS_GUIDE.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
