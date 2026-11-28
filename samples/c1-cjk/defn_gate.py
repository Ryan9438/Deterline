"""样例定义闸门（16 号计划包 04）——与引擎**同源**解析。

单一来源 = deterline.storyline._read_definition（yaml_min 解析 + v1 合同校验：
重复键/未知字段/类型/patch_id 正则全部 fail-closed 带行号）。
样例脚本不再自行文本截取（sed/grep 分岔废除，包 04）。

用法: defn_gate.py <定义文件路径>
输出（stdout）: JSON {"patch_id": ..., "cjk": ...}
失败（stderr）: ✗ [c1-cjk] 引擎错误原样（指向字段/行号），exit 1。
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from deterline.storyline import StorylineError, _read_definition  # noqa: E402


def main(argv: list) -> int:
    if len(argv) != 1:
        print("用法: defn_gate.py <定义文件>", file=sys.stderr)
        return 2
    try:
        text = Path(argv[0]).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"✗ [c1-cjk] 定义读取失败: {exc}", file=sys.stderr)
        return 1
    try:
        doc = _read_definition(text)
    except StorylineError as exc:
        print(f"✗ [c1-cjk] 定义不合合同（引擎裁决）: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:  # yaml_min.YamlMinError 等
        print(f"✗ [c1-cjk] 定义解析失败（引擎裁决）: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"patch_id": doc["patch_id"],
                      "cjk": bool(doc.get("cjk", False))},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
