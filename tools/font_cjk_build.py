#!/usr/bin/env python3
"""C3b 字形页生成器：把 OFL 像素字体渲染为 UT 字体纹理页 + glyph 元数据。

产出（写入 --out-dir）：
  cjk_page_<n>.png   RGBA 纹理页（白色字形、透明底——UT 字体页惯例）
  glyphs.json        每字形: char/code/page/x/y/w/h/offset_x/offset_y/advance
  meta.json          字体/尺寸/字符集统计（确定性构建，可复现）

字符集（默认）：ASCII 可打印区 + 全角标点符号 + GB2312 一级汉字 3755 字
（--full 追加 GB2312 二级 3008 字）。GB2312 区位迭代生成，不依赖网络。

布局：等宽 CELLxCELL 网格（默认 13x13 = 12px 字形 + 1px 间距），
每页 --page-size（默认 1024）→ 单页容量 6084 字，3755+ASCII 一页放下。

用法：
  python3 tools/font_cjk_build.py --font <path.ttf> --out-dir build/font_cjk
  python3 tools/font_cjk_build.py --font ... --only missing_chars.txt

许可要求：输入字体必须是允许嵌入/再分发的开源许可（项目共识：OFL）。
OFL 许可证文本须随字体文件一并保留（assets/fonts/vendor/）。
"""

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# 全角标点/符号补充（GB2312 区位迭代覆盖不到的常用书写符号在此兜底）
EXTRA_CHARS = (
    "，。！？：；、""''（）《》【】…—～·「」『』※〇"
    "一二三四五六七八九十百千万亿"
)


def build_charset(full: bool) -> list:
    """确定性字符集：ASCII + EXTRA + GB2312 一级（可选二级）。"""
    chars = []
    seen = set()

    def add(ch):
        if ch not in seen:
            seen.add(ch)
            chars.append(ch)

    for cp in range(0x20, 0x7F):          # ASCII 可打印
        add(chr(cp))
    for ch in EXTRA_CHARS:
        add(ch)
    for cp in range(0x3041, 0x3100):      # 平假名+片假名（就地改造 ja 字体时保 kana 渲染）
        try:
            add(chr(cp))
        except ValueError:
            continue
    ranges = [(0xB0, 0xD8)]               # GB2312 一级汉字 3755
    if full:
        ranges.append((0xD8, 0xF8))       # GB2312 二级汉字 3008
    for hb_start, hb_end in ranges:
        for hb in range(hb_start, hb_end):
            for lb in range(0xA1, 0xFF):
                try:
                    add(bytes([hb, lb]).decode("gb2312"))
                except UnicodeDecodeError:
                    continue               # 空位跳过
    return chars


def render_pages(chars: list, font_path: str, px: int, cell: int,
                 page_size: int, only: set = None) -> tuple:
    """渲染字形 → (pages[Image], glyphs[list of dict])。

    字形以"单元格内左上对齐 + 记录 offset"方式排版：
    offset_x/y 是字形位图相对单元格原点(0,0)的绘制偏移，
    advance 取字体给定的等宽前进量（monospaced）。
    """
    font = ImageFont.truetype(font_path, px)
    glyphs = []
    pages = []
    img = None
    draw = None
    col = row = 0
    per_row = page_size // cell

    def new_page():
        nonlocal img, draw, col, row
        img = Image.new("RGBA", (page_size, page_size), (0, 0, 0, 0))
        draw = None
        col = row = 0
        pages.append(img)

    new_page()
    for ch in chars:
        if only is not None and ch not in only:
            continue
        # 度量：getbbox 给出字形在基线坐标系的外接框
        bbox = font.getbbox(ch)
        w = max(0, bbox[2] - bbox[0])
        h = max(0, bbox[3] - bbox[1])
        if w == 0 or h == 0:
            # 空白字形（如全角空格）：仍记录 advance，不占位图
            glyphs.append({"char": ch, "code": ord(ch), "page": len(pages) - 1,
                           "x": 0, "y": 0, "w": 0, "h": 0,
                           "offset_x": 0, "offset_y": 0,
                           "advance": px})
            continue
        if w > cell or h > cell:
            raise ValueError(f"字形 {ch!r} 尺寸 {w}x{h} 超出单元格 {cell}x{cell}——"
                             f"增大 --cell 或减小 --px")
        if col >= per_row:
            col = 0
            row += 1
        if row >= page_size // cell:
            new_page()
        gx, gy = col * cell, row * cell
        # 渲染：把字形位图画到单元格内（bbox 平移到单元格原点）
        d = ImageDraw.Draw(img)
        d.text((gx - bbox[0], gy - bbox[1]), ch, font=font, fill=(255, 255, 255, 255))
        glyphs.append({"char": ch, "code": ord(ch),
                       "page": len(pages) - 1,
                       "x": gx, "y": gy, "w": w, "h": h,
                       "offset_x": bbox[0], "offset_y": bbox[1],
                       "advance": px})
        col += 1
    return pages, glyphs


def compose_pages(existing_png: Path, existing_rect: tuple, out_png: Path,
                  glyphs_in: Path, glyphs_out: Path, canvas: int, cell: int,
                  px: int, origin: tuple):
    """C3b extend 模式的页复合：现有字体页 + 新 CJK 字形 → 大画布。

    existing_rect = (x, y, w, h)：现有字形在页内的占用区域（由侦察/CSX pass1
    dump 得出）；新字形从其下方第一格行开始排（origin 覆盖起始格坐标）。
    产出：复合 PNG + 坐标已换算为画布绝对位置的 glyphs json。
    """
    img = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    old = Image.open(existing_png).convert("RGBA")
    img.paste(old, (0, 0), old)

    glyphs = json.loads(glyphs_in.read_text(encoding="utf-8"))
    per_row = canvas // cell
    ex, ey, ew, eh = existing_rect
    start_row = (origin[1] if origin else ey + eh) // cell
    col = origin[0] // cell if origin else 0
    row = start_row
    src_cache = {}
    for g in glyphs:
        if g["w"] == 0:
            g["x"], g["y"] = 0, 0
            continue
        if col >= per_row:
            col = 0
            row += 1
        if (row + 1) * cell > canvas:
            raise ValueError("画布放不下全部新字形——增大 --compose-canvas 或减小字符集")
        # 新页内字形重新按单元格排布：把源页里该格的像素块搬到目标格
        pkey = g["page"]
        if pkey not in src_cache:
            src_cache[pkey] = Image.open(
                glyphs_in.parent / f"cjk_page_{pkey}.png").convert("RGBA")
        src = src_cache[pkey]
        tile = src.crop((g["x"], g["y"], g["x"] + g["w"], g["y"] + g["h"]))
        gx, gy = col * cell, row * cell
        img.paste(tile, (gx, gy), tile)
        g["page"] = 0                     # 复合后全部位于单一画布
        g["x"], g["y"] = gx, gy
        col += 1
    img.save(out_png)
    glyphs_out.write_text(json.dumps(glyphs, ensure_ascii=False, indent=1),
                          encoding="utf-8")
    n = sum(1 for g in glyphs if g["w"] > 0)
    print(f"compose OK: 现有页 {existing_png.name} + {n} 个 CJK 字形 → {out_png}"
          f"（占用行 {start_row}..{row}）")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--font", required=True, help="TTF/OTF 路径（须为 OFL 等可嵌入许可）")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--px", type=int, default=12, help="字形像素尺寸（默认 12）")
    ap.add_argument("--cell", type=int, default=13, help="单元格边长（默认 px+1）")
    ap.add_argument("--page-size", type=int, default=1024)
    ap.add_argument("--full", action="store_true", help="追加 GB2312 二级汉字（共 ~6800 字）")
    ap.add_argument("--only", help="只渲染给定文件中的字符（每行一个或直接一串文本）")
    ap.add_argument("--compose-existing", help="compose 模式：现有字体页 PNG（CSX pass1 dump）")
    ap.add_argument("--compose-rect", help="compose 模式：现有字形占用区 x,y,w,h")
    ap.add_argument("--compose-canvas", type=int, default=1024, help="compose 画布边长")
    ap.add_argument("--compose-origin", help="compose 新字形起始格 x,y（默认占用区下方）")
    args = ap.parse_args()

    if args.compose_existing:
        rect = tuple(int(v) for v in args.compose_rect.split(","))
        origin = tuple(int(v) for v in args.compose_origin.split(",")) \
            if args.compose_origin else None
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        compose_pages(Path(args.compose_existing), rect,
                      out_dir / "cjk_composed.png",
                      out_dir / "glyphs.json", out_dir / "glyphs_composed.json",
                      args.compose_canvas, args.cell, args.px, origin)
        return 0

    chars = build_charset(args.full)
    only = None
    if args.only:
        text = Path(args.only).read_text(encoding="utf-8")
        only = set(text) - {"\n", "\r"}

    pages, glyphs = render_pages(chars, args.font, args.px, args.cell,
                                 args.page_size, only)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for i, page in enumerate(pages):
        page.save(out / f"cjk_page_{i}.png")
    (out / "glyphs.json").write_text(
        json.dumps(glyphs, ensure_ascii=False, indent=1), encoding="utf-8")
    meta = {
        "font": str(Path(args.font).resolve()),
        "px": args.px, "cell": args.cell, "page_size": args.page_size,
        "charset_size": len(chars), "glyph_count": len(glyphs),
        "pages": len(pages), "full": args.full,
        "license_note": "input font must be embeddable (project policy: OFL)",
    }
    (out / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"OK: {len(glyphs)} glyphs → {len(pages)} 页({args.page_size}px) → {out}")
    print(f"    字符集 {len(chars)}（full={args.full}），已渲染位图 "
          f"{sum(1 for g in glyphs if g['w'] > 0)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
