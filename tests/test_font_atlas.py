"""Glyph 表不变量测试（D0 清偿日 A4，RV-B 回归钉）。

tools/font_cjk_atlas.py 的 RV-B 修复（排序/去重/ASCII 来源）此前没有任何测试
钉住——"页内重排动工前必须先用修复后工具重建 glyph 表复测"的前提是"修复后"
可证明。本文件把不变量钉成断言：

  a) 每个字体 glyph 列表严格按码点升序
  b) 无重复码点
  c) ASCII 全部来自源字体（pass1 dump，shift/offset/kern 一致 + 像素一致），
     非 ASCII 全部来自 build 集（fixture glyphs.json），build 集的 ASCII 条目
     不得进入输出（防污染）；shift_cjk == 2 * shift_ascii
  d) 容量公式成立：cols*rows >= glyph 需求，且区域不越界
  e) plain 字体 region_y0 == maintext 末行 + 16

夹具见 tests/fixtures/font_atlas/README.md（来源与再生成方式）。
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "font_atlas"
BUILD_DIR = FIXTURES / "font_cjk"
PASS1_DIR = FIXTURES / "font_cjk_pass1"

import font_cjk_atlas
from font_cjk_atlas import (ASCII_MAX, ASCII_MIN, PAGE_SIZE, build_atlases,
                            parse_pass1)

# build_inpage_atlas 属价值派 S0 在途工作（本文件 commit 时可能尚未入库）；
# 缺席时跳过而非报错，保证本 commit 自洽——函数入库后测试自动激活。
HAS_INPAGE = hasattr(font_cjk_atlas, "build_inpage_atlas")


class FontAtlasInvariantTest(unittest.TestCase):
    """build_atlases 双页图集输出不变量。"""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="font_atlas_test_"))
        cls.result = build_atlases(BUILD_DIR, PASS1_DIR, cls.tmp)
        cls.fonts_pass1, cls.pages_pass1 = parse_pass1(PASS1_DIR)
        cls.build_glyphs = json.loads(
            (BUILD_DIR / "glyphs.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _codes(self, font_name):
        return [g[0] for g in self.result["fonts"][font_name]["glyphs"]]

    # ── a/b: 排序 + 去重 ──
    def test_glyphs_sorted_by_codepoint(self):
        for name, font in self.result["fonts"].items():
            codes = [g[0] for g in font["glyphs"]]
            self.assertEqual(codes, sorted(codes),
                             f"{name}: glyph 表未按码点升序（引擎查找假定有序）")

    def test_glyphs_no_duplicate_codepoint(self):
        for name, font in self.result["fonts"].items():
            codes = [g[0] for g in font["glyphs"]]
            self.assertEqual(len(codes), len(set(codes)),
                             f"{name}: glyph 表存在重复码点")

    # ── c: ASCII 来源 = 源字体；非 ASCII 来源 = build 集 ──
    def test_ascii_from_source_font_metrics(self):
        for new_name, src_name, _page, _y0, _scale in [
                ("fnt_cjk_main", "fnt_main", 0, 0, 2),
                ("fnt_cjk_maintext", "fnt_maintext", 1, 0, 1),
                ("fnt_cjk_plain", "fnt_plain", 1, None, 1)]:
            src_ascii = {g["char"]: g for g in self.fonts_pass1[src_name]["glyphs"]
                         if ASCII_MIN <= g["char"] <= ASCII_MAX}
            out_ascii = {g[0]: g for g in self.result["fonts"][new_name]["glyphs"]
                         if g[0] <= ASCII_MAX}
            self.assertEqual(set(out_ascii), set(src_ascii),
                             f"{new_name}: ASCII 码集应恰为源字体 0x20-0x7E")
            for code, g in out_ascii.items():
                s = src_ascii[code]
                # spec: [code, gx, gy_rel, sw, sh, offset, shift, kern]
                self.assertEqual(g[3], s["sw"], f"{new_name} U+{code:02X}: sw 不一致")
                self.assertEqual(g[4], s["sh"], f"{new_name} U+{code:02X}: sh 不一致")
                self.assertEqual(g[5], s["offset"], f"{new_name} U+{code:02X}: offset 不一致")
                self.assertEqual(g[6], s["shift"], f"{new_name} U+{code:02X}: shift 与 pass1 不一致")
                self.assertEqual(g[7], s["kern"], f"{new_name} U+{code:02X}: kern 不一致")

    def test_ascii_pixels_copied_from_source_page(self):
        """ASCII 像素等于源字体 emb 页 TPI 区域内的裁剪（paste 掩码语义）：
        源 alpha=0 的像素输出必须同样透明；源 alpha!=0 的像素输出逐位相等。"""
        try:
            from PIL import Image
            emb = Image.open(PASS1_DIR / "emb_page.png").convert("RGBA")
        except ImportError:
            self.skipTest("PIL 不可用")
        checked = 0
        for new_name, src_name, page_idx, region_y0, _scale in [
                ("fnt_cjk_main", "fnt_main", 0, 0, 2),
                ("fnt_cjk_maintext", "fnt_maintext", 1, 0, 1),
                ("fnt_cjk_plain", "fnt_plain", 1, None, 1)]:
            font = self.result["fonts"][new_name]
            y0 = font["region_y0"]
            page_img = Image.open(self.tmp / f"atlas_page_{font['page']}.png").convert("RGBA")
            src_ascii = {g["char"]: g for g in self.fonts_pass1[src_name]["glyphs"]
                         if ASCII_MIN <= g["char"] <= ASCII_MAX}
            tpi_x, tpi_y = self.fonts_pass1[src_name]["tpi"][:2]
            for g in font["glyphs"]:
                if g[0] > ASCII_MAX:
                    continue
                s = src_ascii[g[0]]
                out_tile = page_img.crop((g[1], y0 + g[2],
                                          g[1] + g[3], y0 + g[2] + g[4]))
                src_tile = emb.crop((tpi_x + s["sx"], tpi_y + s["sy"],
                                     tpi_x + s["sx"] + s["sw"],
                                     tpi_y + s["sy"] + s["sh"]))
                ob, sb = out_tile.tobytes(), src_tile.tobytes()
                for px in range(0, len(ob), 4):
                    sa = sb[px + 3]
                    if sa == 0:
                        self.assertEqual(ob[px + 3], 0,
                                         f"{new_name} U+{g[0]:02X}: 透明源像素被污染")
                    else:
                        self.assertEqual(ob[px:px + 4], sb[px:px + 4],
                                         f"{new_name} U+{g[0]:02X}: ASCII 像素与源字体不一致")
                checked += 1
        self.assertGreater(checked, 0)

    def test_nonascii_from_build_set_complete_and_exclusive(self):
        for name, font in self.result["fonts"].items():
            out_nonascii = {g[0] for g in font["glyphs"] if g[0] > ASCII_MAX}
            build_nonascii = {g["code"] for g in self.build_glyphs
                              if g["code"] > ASCII_MAX}
            self.assertEqual(out_nonascii, build_nonascii,
                             f"{name}: 非 ASCII 码集应恰为 build 集（无缺失/无混入）")
            # build 集的 ASCII 条目必须被过滤——重复会污染按码点查找。
            # 度量级证明在 test_ascii_from_source_font_metrics：输出 ASCII 的
            # offset/shift/kern 与源字体一致，而 build 集 ASCII 条目的度量不同。
            src_ascii = {g["char"] for g in
                         self.fonts_pass1["fnt_main"]["glyphs"]
                         if ASCII_MIN <= g["char"] <= ASCII_MAX}
            out_ascii = {g[0] for g in font["glyphs"] if g[0] <= ASCII_MAX}
            self.assertEqual(out_ascii, src_ascii,
                             f"{name}: ASCII 码集应恰为源字体码集（build 集 ASCII 未混入）")

    def test_shift_cjk_is_double_shift_ascii(self):
        for name, font in self.result["fonts"].items():
            self.assertEqual(font["shift_cjk"], font["shift_ascii"] * 2,
                             f"{name}: CJK advance 应为 ASCII 中位 shift 的 2 倍")
            nonascii = [g for g in font["glyphs"] if g[0] > ASCII_MAX]
            self.assertTrue(all(g[6] == font["shift_cjk"] for g in nonascii),
                            f"{name}: 非 ASCII glyph 的 shift 不一致")

    # ── d: 容量公式 ──
    def test_capacity_formula(self):
        for name, font in self.result["fonts"].items():
            cell_w, cell_h = font["cell"]
            cols = PAGE_SIZE // cell_w
            capacity = cols * (PAGE_SIZE // cell_h)
            self.assertGreaterEqual(capacity, font["glyph_count"],
                                    f"{name}: 容量不足 {capacity} < {font['glyph_count']}")
            # 区域不越界：y0 + 实用行数 * cell_h <= PAGE_SIZE
            used = font["region_y0"] + font["rows"] * cell_h
            self.assertLessEqual(used, PAGE_SIZE,
                                 f"{name}: 区域越界 y0+rows*cell_h={used}")

    # ── e: plain 排在 maintext 之后 ──
    def test_plain_region_y0_follows_maintext(self):
        fonts = self.result["fonts"]
        mt = fonts["fnt_cjk_maintext"]
        pl = fonts["fnt_cjk_plain"]
        expected = mt["region_y0"] + mt["rows"] * mt["cell"][1] + 16
        self.assertEqual(pl["region_y0"], expected,
                         "plain 字体 y0 应为 maintext 末行 + 16（页内布局不变量）")
        self.assertEqual(pl["page"], mt["page"],
                         "plain 与 maintext 应同页（第二页）")


@unittest.skipUnless(HAS_INPAGE, "build_inpage_atlas 尚未入库（价值派 S0 在途）")
class FontAtlasInPageTest(unittest.TestCase):
    """build_inpage_atlas（RV-B 修复目标）的共享不变量。"""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="font_inpage_test_"))
        cls.result = font_cjk_atlas.build_inpage_atlas(
            BUILD_DIR, PASS1_DIR, cls.tmp)
        cls.fonts_pass1, _ = parse_pass1(PASS1_DIR)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_inpage_sorted_and_unique(self):
        codes = [g[0] for g in self.result["glyphs"]]
        self.assertEqual(codes, sorted(codes), "in-page glyph 表未按码点升序")
        self.assertEqual(len(codes), len(set(codes)), "in-page glyph 表有重复码点")

    def test_inpage_ascii_metrics_from_maintext(self):
        src_ascii = {g["char"]: g for g in self.fonts_pass1["fnt_maintext"]["glyphs"]
                     if ASCII_MIN <= g["char"] <= ASCII_MAX}
        out_ascii = [g for g in self.result["glyphs"] if g[0] <= ASCII_MAX]
        self.assertEqual(len(out_ascii), len(src_ascii))
        for g in out_ascii:
            s = src_ascii[g[0]]
            # spec: [code, x, y, w, h, offset, shift, kern]
            self.assertEqual(g[5], s["offset"])
            self.assertEqual(g[6], s["shift"], "in-page ASCII shift 与 pass1 不一致")

    def test_inpage_capacity_recorded(self):
        self.assertGreaterEqual(self.result["capacity"], self.result["glyph_count"])
        self.assertEqual(self.result["glyph_count"], 295)


if __name__ == "__main__":
    unittest.main()
