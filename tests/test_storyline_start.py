"""storyline-start 起步路由测试（16 号计划包 31）。

fatal 臂（UTMT_CLI 缺失 → exit 1 + actionable next）/ 齐备臂（exit 0 +
ready）/ JSON 形状。环境探针全 mock（无 UTMT 依赖）。
"""

import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import modify_save as ms  # noqa: E402,F401
from deterline.storyline.commands import cmd_storyline_start  # noqa: E402


def _run(**patches) -> tuple[int, dict]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), \
         mock.patch("deterline.utmt._find_utmt_cli",
                    **patches.get("utmt", {"return_value": "/fake/UTMT.dll"})), \
         mock.patch("deterline.paths.find_game_data_file",
                    **patches.get("game",
                                  {"return_value": Path("/tmp/game.ios")})):
        rc = cmd_storyline_start(None, json_out=True)
    return rc, json.loads(buf.getvalue())


class TestStorylineStart(unittest.TestCase):

    def test_ready_route(self):
        rc, out = _run()
        self.assertEqual(rc, 0)
        self.assertTrue(out["ready"])
        self.assertEqual(out["schema"], "deterline.storyline-start/v1")
        labels = [c["label"] for c in out["checks"]]
        self.assertIn("UTMT_CLI", labels)
        self.assertEqual(len(out["route"]), 7)
        self.assertTrue(any("storyline-plan" in s for s in out["route"]))
        self.assertTrue(any("storyline-undo" in s for s in out["route"]))

    def test_missing_utmt_fatal_actionable(self):
        rc, out = _run(utmt={"side_effect": FileNotFoundError("未找到 UTMT_CLI")})
        self.assertEqual(rc, 1)
        self.assertFalse(out["ready"])
        self.assertIn("UTMT_CLI 导出", out["next"])
        utmt_check = next(c for c in out["checks"]
                          if c["label"] == "UTMT_CLI")
        self.assertFalse(utmt_check["ok"])
        self.assertTrue(utmt_check["fatal"])

    def test_missing_game_not_fatal(self):
        rc, out = _run(game={"side_effect": FileNotFoundError("无游戏文件")})
        self.assertEqual(rc, 0)  # 基线缺失不阻断（可 later --dir 指定）
        game_check = next(c for c in out["checks"]
                          if c["label"] == "基线游戏文件")
        self.assertFalse(game_check["ok"])
        self.assertFalse(game_check["fatal"])


if __name__ == "__main__":
    unittest.main()
