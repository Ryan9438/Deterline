#!/usr/bin/env python3
"""rooms-scan 工具（阶段 3.1 首切片）：单次只读遍历 → rooms-scan JSON。

用法:
  python3 tools/scan_rooms.py --game /path/to/game.ios --out rooms_scan.json

零写盘于游戏/存档侧；唯一写动作 = --out 指定的 JSON 文件。
分类规则与理由内嵌（A/B1/B2/D-candidate）；D 人工例外在 JSON 里直接改
classification/classification_reason 并保留 original_* 字段（3.2 生成器
消费时以人工字段为准）。
"""

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from deterline.cmds import room  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="房间统一扫描（03 §3.1 首切片）")
    parser.add_argument("--game", required=True, help="游戏数据文件（tmp 副本）")
    parser.add_argument("--out", default="rooms_scan.json", help="输出 JSON 路径")
    parser.add_argument("--timeout", type=int, default=300, help="UTMT 超时秒数")
    args = parser.parse_args()

    game = Path(args.game).expanduser()
    if not game.is_file():
        print(f"错误: 游戏数据文件不存在: {game}", file=sys.stderr)
        return 1
    data = room.scan_rooms_data(game, timeout=args.timeout)

    # 统计摘要
    by_class: dict[str, int] = {}
    for obs in data["rooms"].values():
        by_class[obs["classification"]] = by_class.get(obs["classification"], 0) + 1
    data["summary"] = {"by_classification": by_class}

    out = Path(args.out)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ {data['room_count']} 房间 → {out}")
    for label in sorted(by_class):
        print(f"  {label}: {by_class[label]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
