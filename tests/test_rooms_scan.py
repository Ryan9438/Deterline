"""3.1 房间统一扫描首切片（2026-11-13）：解析/分类/JSON 结构（零 UTMT）。

真实 UTMT 扫描的基线断言（336 房/undynefinal B1/tundra B2/lastruins A）
在 gated 集成用例——设 DETERLINE_RUN_UTMT_INTEGRATION=1 运行。
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "tests"))

from deterline import errors  # noqa: E402
from deterline.cmds import room as room_mod  # noqa: E402


def _rs_line(name="room_a", size="640x480", inst=3, tiles=10,
             bgen="bg_wall", objs="obj_cactus"):
    from urllib.parse import quote
    return ("RS|" + quote(name) + "|" + size + f"|inst={inst}"
            f"|tiles={tiles}|bgen={quote(bgen)}|objs={quote(objs)}")


class TestParseRoomsScan(unittest.TestCase):
    def test_basic_fields_parsed(self):
        rooms = room_mod._parse_rooms_scan(_rs_line())
        self.assertEqual(set(rooms), {"room_a"})
        obs = rooms["room_a"]
        self.assertEqual(obs["size"], "640x480")
        self.assertEqual(obs["instances"], 3)
        self.assertEqual(obs["tiles"], 10)
        self.assertEqual(obs["bg_enabled"], ["bg_wall"])
        self.assertEqual(obs["objects"], ["obj_cactus"])

    def test_uri_escaped_name_roundtrip(self):
        rooms = room_mod._parse_rooms_scan(_rs_line(name="room|pipe\nline"))
        self.assertIn("room|pipe\nline", rooms)

    def test_multi_bg_and_dedup_objects(self):
        rooms = room_mod._parse_rooms_scan(
            _rs_line(bgen="bg_a,bg_b", objs="obj_x,obj_x,obj_y"))
        self.assertEqual(rooms["room_a"]["bg_enabled"], ["bg_a", "bg_b"])
        self.assertEqual(rooms["room_a"]["objects"], ["obj_x", "obj_y"])

    def test_malformed_line_raises(self):
        with self.assertRaisesRegex(RuntimeError, "解析失败"):
            room_mod._parse_rooms_scan("RS|only|three")


class TestClassifyRoom(unittest.TestCase):
    def test_b1_data_driven_bg(self):
        obs = {"bg_enabled": ["bg_water"], "objects": ["obj_cactus"],
               "tiles": 0, "instances": 1}
        label, reason = room_mod._classify_room(obs)
        self.assertEqual(label, "B1")
        self.assertIn("数据驱动", reason)

    def test_b2_backgrounder_objects(self):
        obs = {"bg_enabled": [], "objects": ["obj_backgrounder_3"],
               "tiles": 5, "instances": 2}
        label, _ = room_mod._classify_room(obs)
        self.assertEqual(label, "B2")

    def test_a_pure_tile(self):
        obs = {"bg_enabled": [], "objects": ["obj_solid"],
               "tiles": 30, "instances": 1}
        label, reason = room_mod._classify_room(obs)
        self.assertEqual(label, "A")
        self.assertIn("纯 Tile", reason)

    def test_d_candidate_two_enabled_layers(self):
        obs = {"bg_enabled": ["bg_far", "bg_near"], "objects": [],
               "tiles": 0, "instances": 0}
        label, reason = room_mod._classify_room(obs)
        self.assertEqual(label, "D-candidate")
        self.assertIn("人工复核", reason)

    def test_uncategorized_recorded(self):
        obs = {"bg_enabled": [], "objects": [], "tiles": 0, "instances": 0}
        label, reason = room_mod._classify_room(obs)
        self.assertEqual(label, "uncategorized")
        self.assertIn("待人工归类", reason)


class TestScanRoomsData(unittest.TestCase):
    """编排层：canned dump → 结构/schema/分类落位（零 UTMT）。"""

    def _scan(self, dump_lines, game_bytes=b"FAKE-GAME"):
        with tempfile.TemporaryDirectory() as directory:
            game = Path(directory) / "game.ios"
            game.write_bytes(game_bytes)
            with mock.patch.object(room_mod.utmt, "_run_utmt",
                                   return_value="\n".join(dump_lines)):
                data = room_mod.scan_rooms_data(game)
        return data

    def test_schema_source_hashes_and_classification(self):
        import hashlib
        source_md5 = hashlib.md5(b"FAKE-GAME").hexdigest()
        data = self._scan([_rs_line("room_a", bgen="bg_w"),
                           _rs_line("room_b", tiles=0, bgen="",
                                    objs="obj_backgrounder_1")])
        self.assertEqual(data["schema"], "deterline.rooms-scan/v1")
        self.assertEqual(data["source_md5"], source_md5)
        self.assertEqual(data["room_count"], 2)
        self.assertEqual(data["rooms"]["room_a"]["classification"], "B1")
        self.assertEqual(data["rooms"]["room_b"]["classification"], "B2")

    def test_source_sha256_tracks_content(self):
        data = self._scan([_rs_line()], game_bytes=b"DIFFERENT")
        import hashlib
        self.assertEqual(data["source_sha256"],
                         hashlib.sha256(b"DIFFERENT").hexdigest())


@unittest.skipUnless(
    os.environ.get("DETERLINE_RUN_UTMT_INTEGRATION") == "1",
    "真实 UTMT 扫描需本机 CLI + 基线 game.ios（RESCAN_PLAN §七 基线断言）")
class TestRoomsScanRealBaseline(unittest.TestCase):
    """RESCAN_PLAN §七 五条中的三条自动化（336/B1/B2/A 采样）。"""

    def test_baseline_counts_and_divergences(self):
        """RESCAN_PLAN §七 基线核对（2026-11-13 实测口径）：
        336 房 ✓ / tundra_town=B2 ✓；water_undynefinal 与 lastruins_corridor
        的旧标签（B1/A）与启发式（≥2 启用层 → D-candidate）**存在分歧**——
        按 03 §3.1"人工例外带依据"如实进 D-candidate 复核清单，不强行贴旧标。"""
        game = REPO / "game.ios"
        if not game.is_file():
            self.skipTest("仓库无基线 game.ios")
        data = room_mod.scan_rooms_data(game, timeout=300)
        self.assertEqual(data["room_count"], 336, "RESCAN_PLAN §七：336 房间")
        self.assertEqual(data["source_md5"], "fc049850856dea4ef1427bbf5653fc47")
        by = {n: o["classification"] for n, o in data["rooms"].items()}
        self.assertEqual(by.get("room_tundra_town"), "B2",
                         "RESCAN_PLAN §七：tundra_town = B2（backgrounder 对象驱动）")
        for divergent in ("room_water_undynefinal", "room_lastruins_corridor"):
            self.assertEqual(by.get(divergent), "D-candidate",
                             f"{divergent}：启发式与 RESCAN_PLAN 旧标签分歧——"
                             "D-candidate 人工复核（分歧登记见 09 §5）")


if __name__ == "__main__":
    unittest.main()
