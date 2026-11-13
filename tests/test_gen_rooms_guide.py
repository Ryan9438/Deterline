"""3.2 ROOMS_GUIDE 草稿生成器首切片（2026-11-13）：映射体检 / 渲染 / 稳定性。

全部 tmp 隔离零 UTMT；映射体检直接对照仓库真实 rooms.json 双表。
"""

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "scripts"))

import gen_rooms_guide  # noqa: E402


def _scan_json(rooms: dict, source_md5="fc049850856dea4ef1427bbf5653fc47") -> dict:
    data = {
        "schema": "deterline.rooms-scan/v2",
        "source_md5": source_md5,
        "source_sha256": "x" * 64,
        "captured_at": "2026-11-13T00:00:00",
        "room_count": len(rooms),
        "rooms": rooms,
        "summary": {},
    }
    by_class: dict[str, int] = {}
    for obs in rooms.values():
        c = obs["classification"]
        by_class[c] = by_class.get(c, 0) + 1
    data["summary"]["by_classification"] = by_class
    return data


class TestValidateMapping(unittest.TestCase):
    def setUp(self):
        self.rooms = json.loads((REPO / "scripts" / "rooms.json").read_text(encoding="utf-8"))
        self.reverse = json.loads(
            (REPO / "scripts" / "rooms_reverse.json").read_text(encoding="utf-8"))

    def test_real_mapping_bijection_clean(self):
        self.assertEqual(gen_rooms_guide.validate_mapping(self.rooms, self.reverse),
                         [], "仓库双表必须自洽")

    def test_broken_reverse_detected(self):
        reverse = dict(self.reverse)
        first_name = next(iter(reverse))
        reverse[first_name] = "999999"
        problems = gen_rooms_guide.validate_mapping(self.rooms, reverse)
        self.assertTrue(any("指向不一致" in p for p in problems))

    def test_missing_reverse_entry_detected(self):
        reverse = dict(self.reverse)
        reverse.pop(next(iter(reverse)))
        problems = gen_rooms_guide.validate_mapping(self.rooms, reverse)
        self.assertTrue(any("双射断裂" in p for p in problems)
                        or any("reverse 缺中文名" in p for p in problems))


class TestRenderGuide(unittest.TestCase):
    def setUp(self):
        self.rooms = json.loads((REPO / "scripts" / "rooms.json").read_text(encoding="utf-8"))
        self.reverse = json.loads(
            (REPO / "scripts" / "rooms_reverse.json").read_text(encoding="utf-8"))
        self.fixtures = {
            "room_start": {"idx": 9999, "size": "640x480", "instances": 2,
                           "tiles": 0, "bg_enabled": [], "objects": ["obj_mainchara"],
                           "classification": "uncategorized",
                           "classification_reason": "无背景/backgrounder 观测"},
            "room_ruins1": {"idx": 4, "size": "320x480", "instances": 61,
                            "tiles": 8, "bg_enabled": [], "objects": ["obj_cactus"],
                            "classification": "A",
                            "classification_reason": "纯 Tile"},
            "room_tundra_town": {"idx": 71, "size": "1280x480", "instances": 40,
                                 "tiles": 0, "bg_enabled": [],
                                 "objects": ["obj_backgrounder_tundra"],
                                 "classification": "B2",
                                 "classification_reason": "对象驱动背景"},
        }

    def _render(self, fixtures=None):
        data = _scan_json(fixtures or self.fixtures)
        return gen_rooms_guide.render_guide(data, self.rooms,
                                            gen_rooms_guide.validate_mapping(
                                                self.rooms, self.reverse))

    def test_sections_and_mapping_applied(self):
        out = self._render()
        for header in ("D 候选", "B1 数据驱动", "B2 对象驱动", "A 纯 Tile", "未归类"):
            self.assertIn(header, out)
        self.assertIn("`room_ruins1`", out)
        self.assertIn("遗迹 - 起始点", out, "idx=4 应映射出中文名（rooms.json 按 idx）")
        self.assertIn("id=4", out)
        self.assertIn("id=9999", out)
        self.assertIn("（未登记）", out, "rooms.json 值集中不存在的名应标未登记")
        self.assertIn("理由:", out)

    def test_stable_rerun(self):
        """03 §3.2：同一输入重跑无差异（逐字节）。"""
        self.assertEqual(self._render(), self._render())

    def test_unregistered_count_line(self):
        out = self._render()
        self.assertIn("登记 2 / 未登记 1", out, "idx=9999 不在 rooms.json")


class TestApprovalGate(unittest.TestCase):
    """审核席 A P2-1 / B P1：--out 指向正式 ROOMS_GUIDE.md 一律拒绝
    （大小写变体/resolve 等价形态；同一文件硬链接走 samefile 分支）。"""

    def test_gate_rejects_case_variants(self):
        for name in ("ROOMS_GUIDE.md", "rooms_guide.md", "ROOMS_GUIDE.MD",
                     "./ROOMS_GUIDE.md"):
            out = REPO / name if "/" not in name else REPO / name
            self.assertTrue(gen_rooms_guide._is_forbidden_out(out), name)

    def test_gate_allows_draft(self):
        self.assertFalse(gen_rooms_guide._is_forbidden_out(
            REPO / "ROOMS_GUIDE.draft.md"))


class TestMainEndToEnd(unittest.TestCase):
    """CLI 层：scan JSON → 草稿文件；正式 ROOMS_GUIDE.md 永不被触碰。"""

    def test_end_to_end_writes_draft_only(self):
        import subprocess
        import tempfile
        guide = REPO / "ROOMS_GUIDE.md"
        guide_before = guide.read_text(encoding="utf-8") if guide.exists() else None
        fixtures = {
            "room_ruins1": {"idx": 4, "size": "320x480", "instances": 61,
                            "tiles": 8, "bg_enabled": [], "objects": ["obj_cactus"],
                            "classification": "A",
                            "classification_reason": "纯 Tile"},
        }
        with tempfile.TemporaryDirectory() as directory:
            scan = Path(directory) / "rooms_scan.json"
            scan.write_text(json.dumps(_scan_json(fixtures)), encoding="utf-8")
            out = Path(directory) / "draft.md"
            r = subprocess.run([sys.executable, str(REPO / "tools" / "gen_rooms_guide.py"),
                                "--scan", str(scan), "--out", str(out)],
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            self.assertEqual(r.returncode, 0, r.stderr[-300:])
            draft = out.read_text(encoding="utf-8")
            self.assertIn("ROOMS_GUIDE 草稿", draft)
            self.assertIn("room_ruins1", draft)
            self.assertEqual(r.returncode, 0)
        if guide_before is not None:
            self.assertEqual(guide.read_text(encoding="utf-8"), guide_before,
                             "正式 ROOMS_GUIDE.md 绝不被生成器触碰")


if __name__ == "__main__":
    unittest.main()
