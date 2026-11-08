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

    def test_unknown_typer_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "typer"):
            ms._build_cjk_trigger_csx("room_ruins1", "obj_cactus", 100, 100, 7, "x")

    def test_empty_text_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "text 为空"):
            ms._build_cjk_trigger_csx("room_ruins1", "obj_cactus", 100, 100, 31, "  ")


if __name__ == "__main__":
    unittest.main()
