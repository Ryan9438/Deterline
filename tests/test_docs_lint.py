"""O1a 文档漂移 lint（MVP）：版本一致性 + 已知失实模式黑名单。

背景：两轮审计共勘误 97+ 条，其中相当一部分是"同一事实多处手工陈述"
（版本号 3 种、行数/计数漂移）。本测试把最易漂移的模式固化为断言；
O1b（commands.json 生成机制）落地后，本文件再扩展为生成一致性校验。
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROOT = REPO.parent

# 已被审计裁决为失实、不允许在任何现行文档中复现的模式
STALE_PATTERNS = [
    (r"4100\+ 行", "modify_save.py 行数已 6800+"),
    (r"150 个触发词", "触发词实测约 210"),
    (r"唯一自带背景视差", "tundra/dock/core/castle 亦有单层视差（2026-11 裁决）"),
    (r"约 200MB", "game.ios 实测 60MB"),
]


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


class TestVersionConsistency(unittest.TestCase):
    def test_all_versions_match_modify_save(self):
        ver = re.search(r'__version__ = "([^"]+)"',
                        _read(REPO / "scripts" / "modify_save.py")).group(1)
        for rel, pat in [
            ("run.py", r'__version__ = "([^"]+)"'),
            ("install.py", r'__version__ = "([^"]+)"'),
            ("scripts/bg_generator.py", r'__version__ = "([^"]+)"'),
            ("SKILL.md", r"## 技能版本\n\n([0-9.]+)"),
            ("README.md", r"SKILL\.md\s+← Agent Skill 完整文档（v?([0-9.]+)）"),
        ]:
            m = re.search(pat, _read(REPO / rel))
            self.assertIsNotNone(m, f"{rel} 未找到版本声明")
            self.assertEqual(m.group(1), ver,
                             f"{rel} 版本 {m.group(1)} != {ver}（版本必须单点统一）")
        ps = _read(ROOT / "PROJECT_SUMMARY.md")
        m = re.search(r"SKILL\.md\s+← Agent Skill 完整文档（v?([0-9.]+)）", ps)
        if m:
            self.assertEqual(m.group(1), ver, "PROJECT_SUMMARY 版本漂移")


class TestStalePatterns(unittest.TestCase):
    def test_no_stale_claims(self):
        files = [REPO / f for f in
                 ["SKILL.md", "COMMANDS.md", "README.md",
                  "QUESTIONNAIRE_WORKFLOW.md", "ROOMS_GUIDE.md"]]
        files += [ROOT / f for f in
                  ["PROJECT_SUMMARY.md", "ROOM_DESIGN.md",
                   "ROOMS_GUIDE_RESCAN_PLAN.md", "ChatBox适配计划.md"]]
        for pat, why in STALE_PATTERNS:
            for f in files:
                text = _read(f)
                for m in re.finditer(pat, text):
                    # 允许"勘误引用"形态：同一行内出现 修正/有误/~~/旧 字样
                    line = text[:m.start()].count("\n") + 1
                    line_text = text.split("\n")[line - 1]
                    if not re.search(r"修正|有误|~~|旧|审计|已废弃|实测", line_text):
                        self.fail(f"{f.name}:{line}: 失实模式 {pat!r} 复现（{why}）\n"
                                  f"  行: {line_text.strip()[:90]}")


if __name__ == "__main__":
    unittest.main()
