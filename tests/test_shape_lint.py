"""O3a 形态 lint（V4）：静态扫描 modify_save.py 中的 CSX 块，捕获"死代码形态"。

背景（AUDIT_2026-11-07/域F，15 次游戏内启动实验矩阵）：当前 UTMT 环境下，
对话触发 create 一旦被"状态条件"门控（deterline_state / global.flag[...] /
friction / global.interact 读写），整个分支在游戏内静默失效——反编译输出却
完全正确。唯一实证可用形态是纯扁平块：

    if (id == <N> && !instance_exists(obj_dialoguer) && !instance_exists(OBJ_WRITER)
        && !instance_exists(obj_choicer))
    { if (distance_to_object(obj_mainchara) < <range>) { ...创建对话框... } }

本 lint 在源码层强制该不变量，防止未来修复/重构时无意恢复死代码形态。
（v2.3.0 已有 5 个生成器级测试；本文件把约束推广到 modify_save.py 全部 CSX 块。）
"""

import re
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts" / "modify_save.py"

# 触发对话创建的调用（npc 系生成块的标志）
DIALOGUE_CREATE = "instance_create(0, 0, obj_dialoguer)"
# 已验证外层链（允许任意 id 占位符：{instance_id} / {new_id} / 字面量）
VERIFIED_OUTER = re.compile(
    r"if \(id == [^&()]+ && !instance_exists\(obj_dialoguer\) && "
    r"!instance_exists\(OBJ_WRITER\) && !instance_exists\(obj_choicer\)\)")
# 禁止与对话触发共存的状态通道（任一出现即死代码形态）
FORBIDDEN_STATE = [
    "deterline_state",
    "global.flag[",
    "global.interact",
    "friction",
]


def _extract_csx_blocks(source: str):
    """Extract triple-quoted (f-string) CSX blocks with their line numbers."""
    blocks = []
    for m in re.finditer(r"(f?)'''(.*?)'''", source, re.DOTALL):
        text = m.group(2)
        line = source[:m.start()].count("\n") + 1
        blocks.append((line, m.group(1) == "f", text))
    for m in re.finditer(r'(f?)"""(.*?)"""', source, re.DOTALL):
        text = m.group(2)
        line = source[:m.start()].count("\n") + 1
        blocks.append((line, m.group(1) == "f", text))
    return blocks


class TestDialogueTriggerShape(unittest.TestCase):
    def setUp(self):
        self.source = SCRIPTS.read_text(encoding="utf-8")

    def test_dialogue_creates_are_flat_verified_shape(self):
        """任何包含对话创建的 CSX 块都必须是已验证扁平形态，且无状态通道。"""
        checked = 0
        for line, is_f, text in _extract_csx_blocks(self.source):
            if DIALOGUE_CREATE not in text:
                continue
            checked += 1
            # 1) 必须使用已验证外层链
            if not VERIFIED_OUTER.search(text):
                self.fail(
                    f"modify_save.py:{line}: 对话触发块未使用已验证外层链 "
                    f"(id + !instance_exists×3)——这是游戏内死代码形态（域F 矩阵）。\n"
                    f"块内容前 200 字符: {text[:200]!r}")
            # 2) 块内禁止任何状态通道读写
            for forbidden in FORBIDDEN_STATE:
                if forbidden in text:
                    self.fail(
                        f"modify_save.py:{line}: 对话触发块含状态通道 {forbidden!r} ——"
                        f"状态门控/写入在当前 UTMT 环境导致游戏内静默死代码（域F 矩阵）。"
                        f"修复前禁止恢复状态机生成。")
        self.assertGreaterEqual(checked, 2,
                                "应至少扫到 2 个对话触发块（step/choice 生成器）——"
                                "若为 0 说明提取逻辑失效，lint 需要更新")

    def test_source_has_no_state_gated_dialogue_anywhere(self):
        """整文件兜底：deterline_state 与对话创建不得出现在同一行附近（±5 行窗口）。"""
        lines = self.source.split("\n")
        for i, line in enumerate(lines):
            if "instance_create(0, 0, obj_dialoguer)" not in line:
                continue
            window = "\n".join(lines[max(0, i - 5):i + 6])
            for forbidden in FORBIDDEN_STATE:
                # 允许出现在紧邻的注释（说明性文字）里
                code_lines = [l for l in window.split("\n")
                              if not l.strip().startswith("#") and "#" not in l]
                body = "\n".join(code_lines)
                if forbidden in body:
                    self.fail(
                        f"modify_save.py:{i + 1}: 对话创建 ±5 行窗口内出现 {forbidden!r}"
                        f"（代码，非注释）——疑似状态门控回归。")

    def test_no_python_bool_literals_in_csx(self):
        """CSX 块内不得出现 Python 布尔字面量 True/False（GML 是 true/false）。"""
        for line, is_f, text in _extract_csx_blocks(self.source):
            if not is_f:
                continue  # 普通 ''' 字符串多为文档/帮助文本，仅查 f-string 代码块
            if "ScriptMessage" not in text and "Data." not in text and "room." not in text:
                continue  # 非 CSX 的 f-string（如帮助文本）跳过
            stripped = re.sub(r'"[^"]*"', '""', text)  # 排除字符串字面量内的单词
            for bad in ("True", "False"):
                if re.search(rf"[^\w'\"]{bad}[^\w'\"]", stripped):
                    self.fail(
                        f"modify_save.py:{line}: f-string CSX 块含 Python 布尔 {bad!r}"
                        f"（GML 应为 true/false）")


if __name__ == "__main__":
    unittest.main()
