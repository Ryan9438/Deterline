"""O1a/O1b 文档漂移 lint：版本一致性 + 失实模式黑名单 + 生成区块一致性。

背景：两轮审计共勘误 97+ 条，其中相当一部分是"同一事实多处手工陈述"
（版本号 3 种、行数/计数漂移）。本测试把最易漂移的模式固化为断言。
O1b 落地后增加：commands.json（SSOT）↔ 三份文档生成区块 ↔ argparse choices
三方的同步校验（机制见 tools/gen_docs.py）。
"""

import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROOT = REPO.parent
sys.path.insert(0, str(REPO / "tools"))

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


class TestGeneratedDocs(unittest.TestCase):
    """O1b：commands.json（SSOT）→ gen_docs.py → 三份文档 的同步校验。"""

    def test_generated_tables_in_sync(self):
        """三份文档的生成区块必须与 commands.json 渲染结果逐字节一致。"""
        import gen_docs
        problems = gen_docs.check()
        self.assertEqual(problems, [],
                         "文档命令表漂移——改了 commands.json 就运行 "
                         "python3 tools/gen_docs.py；不要手改生成区块")

    def test_commands_json_covers_argparse(self):
        """新增/删除 --action 必须同步 commands.json（否则本测试失败）。"""
        import gen_docs
        problems = gen_docs.validate_json(gen_docs.load_data())
        self.assertEqual(problems, [])

    def test_generated_region_is_byte_identical_across_docs(self):
        """三份文档嵌入的生成区块逐字节相同（O1 验收标准）。"""
        import gen_docs
        blocks = []
        for path in gen_docs.TARGETS:
            found = gen_docs.BLOCK_RE.findall(path.read_text(encoding="utf-8"))
            self.assertEqual(len(found), 1, f"{path.name}: 生成区块应恰有 1 个")
            blocks.append(found[0])
        self.assertEqual(blocks[0], blocks[1])
        self.assertEqual(blocks[1], blocks[2])

    def test_version_in_commands_json_matches_code(self):
        """commands.json 的 version 字段也是受管版本声明之一。"""
        import gen_docs
        ver = re.search(r'__version__ = "([^"]+)"',
                        (REPO / "scripts" / "modify_save.py").read_text(encoding="utf-8")
                        ).group(1)
        self.assertEqual(gen_docs.load_data()["version"], ver,
                         "commands.json version 与 modify_save.py __version__ 不一致")


if __name__ == "__main__":
    unittest.main()
