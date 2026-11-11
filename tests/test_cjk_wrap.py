"""C3b S6：cjk_wrap_text / 触发块生成器单测。

折行模型 = writer 均匀步距（Draw_0 逐字符 letterx += spacing），一格=一字符。
触发块 = B4 实证全形态（缺一即幽灵框/空框，AUDIT §八/§九）。
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import modify_save as ms


class TestCjkWrapText(unittest.TestCase):
    def test_short_text_unchanged(self):
        self.assertEqual(ms.cjk_wrap_text("短文本", 16), "短文本")

    def test_empty_and_zero_limit(self):
        self.assertEqual(ms.cjk_wrap_text("", 10), "")
        self.assertEqual(ms.cjk_wrap_text("任意", 0), "任意")

    def test_cjk_breaks_anywhere(self):
        out = ms.cjk_wrap_text("一二三四五六七八九十十一十二十三", 10)
        lines = out.split("&")
        self.assertEqual([len(x) for x in lines], [10, 6])

    def test_ascii_words_kept_intact(self):
        out = ms.cjk_wrap_text("你好 hello world 再见", 7)
        lines = out.split("&")
        self.assertTrue(any("hello" in l for l in lines))
        self.assertTrue(any("world" in l for l in lines))

    def test_spaces_at_break_dropped(self):
        out = ms.cjk_wrap_text("aaaa bb cc dddd", 4)
        lines = out.split("&")
        for line in lines:
            self.assertFalse(line.startswith(" "))
            self.assertFalse(line.endswith(" "))

    def test_existing_ampersand_resets_counter(self):
        out = ms.cjk_wrap_text("aaaaaaaaaa&bb", 10)
        # 第一段正好 10 不加断，第二段独立计数
        self.assertEqual(out, "aaaaaaaaaa&bb")

    def test_ascii_cell_accounting(self):
        # 空格占格：行内 "bb cc" = 5 格 ≤ 6；再放不下 "dddd" 才断
        out = ms.cjk_wrap_text("aaaa bb cc dddd", 6)
        self.assertEqual(out, "aaaa&bb cc&dddd")

    def test_long_ascii_word_hard_split(self):
        out = ms.cjk_wrap_text("abcdefghijklmn", 5)
        self.assertEqual(out, "abcde&fghij&klmn")

    def test_no_leading_trailing_space_per_line(self):
        out = ms.cjk_wrap_text("中文 文本 带有 空格 的 折行 测试 用例 很长", 6)
        for line in out.split("&"):
            self.assertEqual(line, line.strip(" "))


class TestCjkTriggerBuilder(unittest.TestCase):
    def test_full_form_block(self):
        csx = ms._build_cjk_trigger_csx("room_ruins1", "obj_cactus", 220, 330, 31,
                                        "* 托丽尔你好，这里是中文测试。")
        # B4 实证全形态：缺一即幽灵框/空框
        self.assertIn("global.msc = 0;", csx)
        self.assertIn("global.typer = 31;", csx)
        self.assertIn("global.facechoice = 3;", csx)
        self.assertIn("global.faceemotion = 0;", csx)
        self.assertIn("/%%", csx)                      # msg[0] 终止符
        self.assertIn('\\"%%%\\"', csx)                # msg[1] = "%%%"
        self.assertIn("!instance_exists(obj_dialoguer)", csx)
        self.assertIn("!instance_exists(OBJ_WRITER)", csx)
        self.assertIn("!instance_exists(obj_choicer)", csx)
        self.assertIn("distance_to_object(obj_mainchara) < 60", csx)
        self.assertIn("inst.X = 220; inst.Y = 330;", csx)
        self.assertIn("CJK_TRIGGER", csx)              # 标记 + 幂等
        self.assertIn("fnt_ja_maintext", csx)          # 依赖 CJK 栈守卫

    def test_wraps_long_text_with_typer31_default_width(self):
        long_text = "*" + "好" * 40
        csx = ms._build_cjk_trigger_csx("room_ruins1", "obj_cactus", 220, 330, 31, long_text)
        # 202//12 = 16 格/行 → 消息里应有 & 断行
        self.assertIn("&", csx)

    def test_appends_page_terminator_once(self):
        csx = ms._build_cjk_trigger_csx("room_ruins1", "obj_cactus", 220, 330, 31, "你好/%%")
        self.assertEqual(csx.count("你好/%%"), 1)      # 不重复追加 /%%

    def test_position_hard_validation(self):
        with self.assertRaisesRegex(RuntimeError, "320"):
            ms._build_cjk_trigger_csx("room_ruins1", "obj_cactus", 480, 240, 31, "x")
        with self.assertRaisesRegex(RuntimeError, "320"):
            ms._build_cjk_trigger_csx("room_ruins1", "obj_cactus", -5, 240, 31, "x")
        with self.assertRaisesRegex(RuntimeError, "480"):
            ms._build_cjk_trigger_csx("room_ruins1", "obj_cactus", 100, 480, 31, "x")

    def test_escape_layers(self):
        # P1：GML 层 + C# 层嵌套转义——C# 反转义得 GML 转义形态，GML 反转义得原文
        for raw in ('plain', 'say "hi"', 'back\\slash', 'mix\"\\end'):
            gml = ms._gml_escape(raw)
            csx = ms._csx_escape(gml)
            gml_back = csx.replace("\\\\", "\x00").replace('\\"', '"').replace("\x00", "\\")
            self.assertEqual(gml_back, gml, f"GML 层还原失败: {raw!r}")
        # 反斜杠 1→2（旧实现的 2→4/1 穿透 bug 钉形）
        self.assertEqual(ms._gml_escape('a\\b'), 'a\\\\b')
        self.assertEqual(ms._gml_escape('a"b'), 'a\\"b')

    def test_writer_special_chars_rejected(self):
        for bad in ("50%off", "and/or"):
            with self.assertRaisesRegex(RuntimeError, "writer 专用字符"):
                ms._build_cjk_trigger_csx("room_ruins1", "obj_cactus", 100, 100, 31, bad, wrap=False)

    def test_terminator_not_split_by_wrap(self):
        csx = ms._build_cjk_trigger_csx("room_ruins1", "obj_cactus", 100, 100, 31,
                                        "abcd/%%", wrap=True, width_room_px=12)
        self.assertNotIn("/&", csx.split("msg[0]")[1])   # 终止符不被折行劈开
        self.assertNotIn("&%%", csx.split("msg[0]")[1])

    def test_unknown_typer_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "typer"):
            ms._build_cjk_trigger_csx("room_ruins1", "obj_cactus", 100, 100, 7, "x")

    def test_empty_text_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "text 为空"):
            ms._build_cjk_trigger_csx("room_ruins1", "obj_cactus", 100, 100, 31, "  ")


if __name__ == "__main__":
    unittest.main()


class TestTwoPageTrigger(unittest.TestCase):
    """阶段 1.5：cjk-trigger 两页扩展的校验矩阵。"""

    def test_two_page_msg_table_shape(self):
        csx = ms._build_cjk_trigger_csx("room_ruins1", "obj_cactus", 220, 330,
                                        31, "* 第一页/%%* 第二页", wrap=False)
        # CSX 内 GML 字符串带反斜杠转义（\"）——与 B4 形态一致
        self.assertIn('global.msg[0] = \\"* 第一页/%%\\";', csx)
        self.assertIn('global.msg[1] = \\"* 第二页/%%\\";', csx)
        self.assertIn('global.msg[2] = \\"%%%\\";', csx)
        self.assertNotIn("global.msg[3]", csx)

    def test_single_page_shape_unchanged(self):
        csx = ms._build_cjk_trigger_csx("room_ruins1", "obj_cactus", 220, 330,
                                        31, "* 单页", wrap=False)
        self.assertIn('global.msg[0] = \\"* 单页/%%\\";', csx)
        self.assertIn('global.msg[1] = \\"%%%\\";', csx)
        self.assertNotIn("global.msg[2]", csx)

    def test_three_pages_rejected(self):
        with self.assertRaises(RuntimeError):
            ms._build_cjk_trigger_csx("room_ruins1", "obj_cactus", 220, 330,
                                      31, "* 一/%%* 二/%%* 三", wrap=False)

    def test_two_page_wrap_independent(self):
        csx = ms._build_cjk_trigger_csx(
            "room_ruins1", "obj_cactus", 220, 330, 31,
            "* 第一页内容比较长需要折行处理测试/%%* 第二页也要折行", wrap=True)
        self.assertIn("global.msg[0]", csx)
        self.assertIn("global.msg[1]", csx)
        # 折行独立性：页1 的 & 硬换行不得渗入页2（每页独立折行）
        import re as _re
        m0 = _re.search(r'global\.msg\[0\] = \\"([^"]*)\\"', csx)
        m1 = _re.search(r'global\.msg\[1\] = \\"([^"]*)\\"', csx)
        self.assertIsNotNone(m0)
        self.assertIsNotNone(m1)
        self.assertIn("&", m0.group(1), "页1 长文本折行应产生 & 硬换行")
        self.assertNotIn("&", m1.group(1), "页2 短文本不应有硬换行（独立性）")
