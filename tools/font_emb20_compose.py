#!/usr/bin/env python3
"""C3b S1（研讨会2 价值派 A1）：emb#20 象限合成器——页内重排的页位图产物。

只改动 (0,1024)-(1023,2047) 象限（ja_main 的 TPI 区域 → 共享 12px 图集）与
金丝雀标记块 (1536,1408)-(1552,1424)（16px 对齐，glyph 采样取其左上 12×12），其余像素逐字节不动——这是"页身份不变、
约束④不在作用路径上"方案的页侧保证，并有 --verify 的像素 diff 自证。

用法：
  python3 tools/font_emb20_compose.py --emb20 <emb20_page.png> \
      --atlas <font_atlas_inpage.png> --out <emb20_page_new.png> [--verify]
"""

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

QUADRANT = (0, 1024, 1024, 2048)          # ja_main TPI 区域（左上角在页 (0,1024)）
CANARY_RECT = (1536, 1408, 1552, 1424)    # 表外码位 glyph 的采样落点（16px 对齐便于块校验）
CANARY_PIXEL = (255, 0, 255, 255)         # 品红——若引擎渲染 canary 字符则目视/像素可判


def compose(emb20_path: Path, atlas_path: Path, out_path: Path) -> dict:
    base = Image.open(emb20_path).convert("RGBA")
    atlas = Image.open(atlas_path).convert("RGBA")
    if atlas.size != (1024, 1024):
        raise ValueError(f"atlas 应为 1024²，实为 {atlas.size}")
    before = base.copy()
    base.paste(atlas, (QUADRANT[0], QUADRANT[1]))
    # 金丝雀标记块：表外 glyph 采样落点画成品红实块
    for y in range(CANARY_RECT[1], CANARY_RECT[3]):
        for x in range(CANARY_RECT[0], CANARY_RECT[2]):
            base.putpixel((x, y), CANARY_PIXEL)
    base.save(out_path)
    return {"before": before, "after": base}


def verify(before: Image.Image, after: Image.Image) -> tuple:
    """返回 (越界 16px 块列表, 全通道 diff bbox)。空列表 = 仅象限+金丝雀变化。

    ⚠️ 必须用全通道差（Pillow 的 RGBA getbbox() 由 alpha 通道驱动，
    RGB 变化而 alpha 相同的像素会被漏检——2026-11-08 B3 复核发现）。
    """
    a = np.asarray(before.convert("RGBA"), dtype=np.int16)
    b = np.asarray(after.convert("RGBA"), dtype=np.int16)
    d = np.abs(a - b).sum(axis=2)
    ys, xs = np.nonzero(d)
    bbox_all = None
    if len(xs):
        bbox_all = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    allowed = [QUADRANT, CANARY_RECT]
    problems = []
    # 逐 16px 块扫描：任何含变化的块必须完全落在允许区内
    bs = 16
    for by in range(0, after.height, bs):
        for bx in range(0, after.width, bs):
            block = d[by:by + bs, bx:bx + bs]
            if not block.any():
                continue
            ok = any(bx >= r[0] and by >= r[1] and bx + bs <= r[2] and by + bs <= r[3]
                     for r in allowed)
            if not ok:
                problems.append((bx, by))
    return problems, bbox_all


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--emb20", required=True)
    ap.add_argument("--atlas", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--verify", action="store_true", help="生成后自证像素 diff 范围")
    args = ap.parse_args()
    r = compose(Path(args.emb20), Path(args.atlas), Path(args.out))
    print(f"compose OK: {args.out}")
    if args.verify:
        problems, bbox = verify(r["before"], r["after"])
        if problems:
            print(f"FAIL: {len(problems)} 个 16px 块越界变化，首个 {problems[0]}")
            return 1
        print(f"verify OK: 变化仅限象限 {QUADRANT} 与金丝雀块 {CANARY_RECT}（总 bbox {bbox}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
