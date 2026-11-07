#!/usr/bin/env python3
"""C3b 图集构建器：现有英文字体 ASCII 字形 + CJK 字形 → 新字体图集。

输入：
  --build-dir   font_cjk_build.py 的输出（glyphs.json + cjk_page_*.png，12px）
  --pass1-dir   cmd_cjk_font pass1 的 dump（fonts.txt 行式元数据 + emb<页>.png）
  --out-dir     产出 atlas_page_<n>.png + atlas_glyphs.json + atlas_meta.json

三个新字体（方案 B，AUDIT_2026-11-07/C3b侦察-字体/侦察报告.md §4）：
  fnt_cjk_main     emSize 24（克隆 fnt_main）  CJK=2x 放大  advance=2×ASCII 中位
  fnt_cjk_maintext emSize 12（克隆 fnt_maintext）CJK=1x       advance=2×ASCII 中位
  fnt_cjk_plain    emSize 12（克隆 fnt_plain）  CJK=1x       advance=2×ASCII 中位
ASCII 0x20-0x7E 从源字体像素原样拷贝（kerning 保留），保证中英混排。

行式 pass1 格式（fonts.txt）：
  FONT <name> <emSize> <emsizefloat> <charset> <aa> <lineheight> <ascender>
       <ascenderoffset> <rangestart> <rangeend> <bold> <tpiSX> <tpiSY> <tpiSW> <tpiSH>
  GLYPH <name> <char> <sx> <sy> <sw> <sh> <offset> <shift> <nk> [kchar:kmod ...]
  PAGE <name> <tpiSX> <tpiSY> <tpiSW> <tpiSH> <pagew> <pageh>
  EMBOK
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

from PIL import Image

# 新字体定义：名称 → (源字体, 页分配, CJK 缩放)
FONT_SPECS = [
    # (新名, 源名, page_idx, region_y0, scale)
    ("fnt_cjk_main", "fnt_main", 0, 0, 2),
    ("fnt_cjk_maintext", "fnt_maintext", 1, 0, 1),
    ("fnt_cjk_plain", "fnt_plain", 1, None, 1),  # region_y0 运行时排在 maintext 之后
]
PAGE_SIZE = 2048
ASCII_MIN, ASCII_MAX = 0x20, 0x7E


def parse_pass1(pass1_dir: Path) -> dict:
    fonts = {}
    pages = {}
    for line in (pass1_dir / "fonts.txt").read_text(encoding="utf-8").splitlines():
        p = line.split()
        if not p:
            continue
        if p[0] == "FONT":
            fonts[p[1]] = {"emSize": float(p[2]), "emSizeIsFloat": p[3] == "1",
                           "charset": int(p[4]), "antiAliasing": int(p[5]),
                           "lineHeight": int(p[6]), "ascender": int(p[7]),
                           "ascenderOffset": int(p[8]),
                           "rangeStart": int(p[9]), "rangeEnd": int(p[10]),
                           "bold": p[11] == "1",
                           "tpi": tuple(int(x) for x in p[12:16]),
                           "glyphs": []}
        elif p[0] == "GLYPH":
            nk = int(p[9])
            kern = [tuple(int(v) for v in k.split(":"))
                    for k in p[10:10 + nk]]
            fonts[p[1]]["glyphs"].append({
                "char": int(p[2]), "sx": int(p[3]), "sy": int(p[4]),
                "sw": int(p[5]), "sh": int(p[6]),
                "offset": int(p[7]), "shift": int(p[8]), "kern": kern})
        elif p[0] == "PAGE":
            pages[p[1]] = {"tpi": tuple(int(x) for x in p[2:6]),
                           "w": int(p[6]), "h": int(p[7])}
        elif p[0] == "EMBOK":
            continue
        else:
            raise ValueError(f"pass1 fonts.txt 未知行: {line[:60]}")
    return fonts, pages


def build_atlases(build_dir: Path, pass1_dir: Path, out_dir: Path) -> dict:
    fonts, pages = parse_pass1(pass1_dir)
    cjk = json.loads((build_dir / "glyphs.json").read_text(encoding="utf-8"))
    cjk_pages = {i: Image.open(build_dir / f"cjk_page_{i}.png").convert("RGBA")
                 for i in {g["page"] for g in cjk}}

    n_cjk = sum(1 for g in cjk if g["w"] > 0)  # glyph 元素: [code,x,y,w,h,offset,shift,kern]
    n_ascii = ASCII_MAX - ASCII_MIN + 1
    out = {"pages": [], "fonts": {}}
    page_imgs = [Image.new("RGBA", (PAGE_SIZE, PAGE_SIZE), (0, 0, 0, 0))
                 for _ in range(2)]

    for new_name, src_name, page_idx, region_y0, scale in FONT_SPECS:
        src = fonts[src_name]
        ascii_glyphs = [g for g in src["glyphs"]
                        if ASCII_MIN <= g["char"] <= ASCII_MAX]
        shift_med = int(statistics.median([g["shift"] for g in ascii_glyphs]))
        shift_cjk = shift_med * 2
        max_h = max(g["sh"] for g in ascii_glyphs)
        # 格宽跟字形位图宽走（12px CJK×scale + 4px 余量）；advance(shift) 与格距无关
        cell_w = 12 * scale + 4
        cell_h = max(max_h + 2, 12 * scale + 4)
        cols = PAGE_SIZE // cell_w
        capacity = cols * (PAGE_SIZE // cell_h)
        total = n_ascii + n_cjk
        if total > capacity:
            raise ValueError(f"{new_name}: 容量不足 cell={cell_w}x{cell_h} "
                             f"容量 {capacity} < 需求 {total}")

        y0 = region_y0
        if y0 is None:  # plain：排在 maintext 之后
            prev = out["fonts"]["fnt_cjk_maintext"]
            y0 = prev["region_y0"] + prev["rows"] * cell_h + 16
        if (y0 + ((total + cols - 1) // cols) * cell_h) > PAGE_SIZE:
            raise ValueError(f"{new_name}: 区域越界 y0={y0}")

        emb = Image.open(next(pass1_dir.glob("emb*.png"))).convert("RGBA")
        tpi_x, tpi_y = src["tpi"][0], src["tpi"][1]
        specs = []
        col = row = 0

        def place():
            nonlocal col, row
            if col >= cols:
                col = 0
                row += 1
            gx = col * cell_w
            gy = y0 + row * cell_h
            col += 1
            return gx, gy

        # 1) 拷贝 ASCII（像素 + 度量原样；坐标改写为 TPI 相对——引擎按 TPI
        #    区域内相对坐标取字形，侦察 dump 实证：maintext TPI@768,0 而
        #    glyph 坐标 0..247）
        for g in ascii_glyphs:
            gx, gy = place()
            tile = emb.crop((tpi_x + g["sx"], tpi_y + g["sy"],
                             tpi_x + g["sx"] + g["sw"], tpi_y + g["sy"] + g["sh"]))
            page_imgs[page_idx].paste(tile, (gx, gy), tile)
            specs.append([g["char"], gx, gy - y0, g["sw"], g["sh"],
                          g["offset"], g["shift"], g["kern"]])
        # 2) CJK（12px 位图，main 2x NEAREST）
        for g in cjk:
            if g["w"] == 0:
                specs.append([g["code"], 0, 0, 0, 0, 0, shift_cjk, []])
                continue
            gx, gy = place()
            tile = cjk_pages[g["page"]].crop(
                (g["x"], g["y"], g["x"] + g["w"], g["y"] + g["h"]))
            if scale > 1:
                tile = tile.resize((g["w"] * scale, g["h"] * scale), Image.NEAREST)
            page_imgs[page_idx].paste(tile, (gx, gy), tile)
            specs.append([g["code"], gx, gy - y0, g["w"] * scale, g["h"] * scale,
                          0, shift_cjk, []])

        specs.sort(key=lambda s: s[0])  # 引擎字形查找假定按码点有序（原版字体均有序）

        rows = row + 1
        out["fonts"][new_name] = {
            "page": page_idx, "region_y0": y0, "rows": rows,
            "cell": [cell_w, cell_h], "emSize": src["emSize"],
            "emSizeIsFloat": src["emSizeIsFloat"],
            "charset": src["charset"], "antiAliasing": src["antiAliasing"],
            "lineHeight": src["lineHeight"], "ascender": src["ascender"],
            "ascenderOffset": src["ascenderOffset"],
            "rangeStart": src["rangeStart"], "rangeEnd": 65439,
            "bold": src["bold"], "shift_ascii": shift_med,
            "shift_cjk": shift_cjk, "glyph_count": len(specs),
            "glyphs": specs}

    # 页尺寸记录（第二页实际用到的高度）
    used_b = max(out["fonts"][n]["region_y0"] + out["fonts"][n]["rows"] *
                 out["fonts"][n]["cell"][1]
                 for n in ("fnt_cjk_maintext", "fnt_cjk_plain"))
    for i in range(2):
        page_imgs[i].save(out_dir / f"atlas_page_{i}.png")
    out["pages"] = [PAGE_SIZE, used_b]
    (out_dir / "atlas_glyphs.json").write_text(
        json.dumps(out, ensure_ascii=False), encoding="utf-8")
    (out_dir / "atlas_meta.json").write_text(json.dumps({
        "page_size": PAGE_SIZE,
        "fonts": {n: {k: v for k, v in f.items() if k != "glyphs"}
                  for n, f in out["fonts"].items()},
        "glyph_total": sum(f["glyph_count"] for f in out["fonts"].values()),
        "source": "ASCII 拷贝自源字体（emb 页 dump）；CJK 自 build_dir（OFL Fusion Pixel）",
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--build-dir", required=True)
    ap.add_argument("--pass1-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    result = build_atlases(Path(args.build_dir), Path(args.pass1_dir), out)
    for n, f in result["fonts"].items():
        print(f"{n}: {f['glyph_count']} glyphs cell={f['cell']} "
              f"shift a/c={f['shift_ascii']}/{f['shift_cjk']} "
              f"page{f['page']} y0={f['region_y0']} rows={f['rows']}")
    print(f"pages used: {result['pages']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
