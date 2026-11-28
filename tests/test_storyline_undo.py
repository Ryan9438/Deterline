"""storyline-undo 前态撤销入口测试（16 号计划包 25）。

纯离线（无 UTMT）：临时游戏文件 + 定义 YAML + 应用回执 + 备份夹具。
四臂验收：正例恢复回前态 / 重复撤销 no-op / 目标被修改拒绝（目标与回执
保留）/ 备份缺席拒绝（回执保留）。另测无回执拒绝与"通用 undo 已回前态"
的可识别 no-op。
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import modify_save as ms  # noqa: E402,F401
from deterline import transactions  # noqa: E402
from deterline.storyline.commands import cmd_storyline_undo  # noqa: E402

DEFN_V2 = """schema: deterline.storyline/v2
patch_id: det_undo_t
cjk: false
rooms:
  start: room_ruins1
npcs:
  n1:
    room: start
    object: obj_npc_marker
    x: 100
    y: 200
    prompt: "* Hi./%%"
    once: false
order:
  - npc:n1
"""


class TestStorylineUndo(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="dl25_undo_")
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.game = root / "game.ios"
        self.defn = root / "defn.yaml"
        self.defn.write_text(DEFN_V2, encoding="utf-8")
        self.rcpt_dir = root / ".deterline" / "storyline" / "game.ios" / "det_undo_t"
        self.rcpt_dir.mkdir(parents=True)
        self.rcpt_path = self.rcpt_dir / "receipt.json"

    # —— 夹具 ——
    def _state(self, content: bytes, backup: bytes | None):
        """布置目标/备份/回执。返回 (before_sha, after_sha)。"""
        self.game.write_bytes(content)
        backup_path = self.game.with_suffix(self.game.suffix + ".bak")
        if backup is not None:
            backup_path.write_bytes(backup)
        before = transactions.fingerprint(backup_path) if backup is not None \
            else "0" * 64
        after = transactions.fingerprint(self.game)
        self.rcpt_path.write_text(json.dumps({
            "schema": "deterline.storyline-apply/v1",
            "patch_id": "det_undo_t",
            "defn_sha256": "x", "baseline_sha256": before,
            "before_sha256": before, "after_sha256": after,
            "product_sha256": after, "status": "applied",
        }), encoding="utf-8")
        return before, after

    # —— 四臂 ——
    def test_positive_restore_to_before(self):
        before, _after = self._state(b"PATCHED", backup=b"BASE")
        rc = cmd_storyline_undo(self.game, str(self.defn))
        self.assertEqual(rc, 0)
        self.assertEqual(self.game.read_bytes(), b"BASE")
        rcpt = json.loads(self.rcpt_path.read_text(encoding="utf-8"))
        self.assertEqual(rcpt["status"], "undone")
        self.assertEqual(rcpt["undo_after_sha256"],
                         transactions.fingerprint(self.game))
        self.assertEqual(transactions.fingerprint(self.game), before)

    def test_repeat_undo_noop(self):
        self._state(b"PATCHED", backup=b"BASE")
        self.assertEqual(cmd_storyline_undo(self.game, str(self.defn)), 0)
        rcpt_after = self.rcpt_path.read_text(encoding="utf-8")
        # 重复撤销：可识别 no-op，不再写盘
        self.assertEqual(cmd_storyline_undo(self.game, str(self.defn)), 0)
        self.assertEqual(self.game.read_bytes(), b"BASE")
        rcpt2 = json.loads(self.rcpt_path.read_text(encoding="utf-8"))
        self.assertEqual(rcpt2["status"], "undone")
        self.assertEqual(rcpt2["undo_after_sha256"],
                         json.loads(rcpt_after)["undo_after_sha256"])

    def test_target_modified_refused_kept(self):
        # 目标被第三方修改（既非 after 也非 before）→ 拒绝且目标/回执不动
        self._state(b"PATCHED", backup=b"BASE")
        self.game.write_bytes(b"THIRD-PARTY")
        rcpt_before = self.rcpt_path.read_text(encoding="utf-8")
        rc = cmd_storyline_undo(self.game, str(self.defn))
        self.assertEqual(rc, 1)
        self.assertEqual(self.game.read_bytes(), b"THIRD-PARTY")
        self.assertEqual(self.rcpt_path.read_text(encoding="utf-8"),
                         rcpt_before)

    def test_backup_missing_refused_kept(self):
        self._state(b"PATCHED", backup=b"BASE")
        self.game.with_suffix(self.game.suffix + ".bak").unlink()
        rcpt_before = self.rcpt_path.read_text(encoding="utf-8")
        rc = cmd_storyline_undo(self.game, str(self.defn))
        self.assertEqual(rc, 1)
        self.assertEqual(self.game.read_bytes(), b"PATCHED")
        self.assertEqual(self.rcpt_path.read_text(encoding="utf-8"),
                         rcpt_before)

    # —— 附加臂 ——
    def test_no_receipt_refused(self):
        self.game.write_bytes(b"X")
        rc = cmd_storyline_undo(self.game, str(self.defn))
        self.assertEqual(rc, 1)

    def test_generic_undo_already_before_is_noop(self):
        before, _after = self._state(b"PATCHED", backup=b"BASE")
        # 通用 undo 已把目标恢复到前态（回执未标 undone）
        self.game.write_bytes(b"BASE")
        self.assertEqual(transactions.fingerprint(self.game), before)
        rc = cmd_storyline_undo(self.game, str(self.defn))
        self.assertEqual(rc, 0)   # 当前 == before → 可识别已撤销
        self.assertEqual(self.game.read_bytes(), b"BASE")


if __name__ == "__main__":
    unittest.main()
