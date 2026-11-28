"""存档投影测试（16 号计划包 17）。

映射依据（flag[i] ↔ file0[29+i]，i∈[0,511]）钉死 + 512+ 不可投影拒绝
+ 持久区占用表 + **两份独立合成存档副本往返逐项比较（未知字段保留）**
+ 分支投影一致性（QuestMachine flag 机器 → 投影 → 读回 → 回访资格）。

合成夹具全程在 tempfile（零真实存档接触）；v1 预留 flag 合同通过。
"""

import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import modify_save as ms  # noqa: E402,F401  （初始化 deterline 包路径）
from deterline import errors  # noqa: E402
from deterline.storyline import (  # noqa: E402
    StorylineError, _read_definition_v2)
from deterline.storyline import projection  # noqa: E402
from deterline.storyline.projection import (  # noqa: E402
    apply_flag_writes, check_flag_occupancy, flag_slot, project_state,
    read_flag, read_state)
from deterline.storyline.state import QuestMachine  # noqa: E402
from tests.test_storyline_states import FLAG_V2, MAIN_V2, _defn  # noqa: E402


def _fixture_save(dir_path: Path, variant: int) -> None:
    """合成完整存档（file0 548 数值 + undertale.ini 含未知段/未知键）。

    variant 控制逐项基值——两份副本值不同（独立性），逐项比较口径为
    「除投影槽位外逐项相等」而非「与某模板相等」。
    """
    # file0：名字行 + 548 数值行（含已知字段布局 + 大量"未知字段"值）
    name = f"Char{variant}"
    nums = [0] * projection.FILE0_NUMBER_COUNT
    nums[0] = variant + 1          # lv
    nums[1] = 16 + variant * 4     # maxhp
    nums[9] = 100 * variant        # gold
    nums[10] = variant             # kills
    for i in range(11, 27):
        nums[i] = i * variant      # item/phone（未知组合形态）
    nums[27], nums[28] = 1, 2      # weapon/armor
    for i in range(29, 541):       # flag 区（含大量游戏旗标 + 未知占用）
        nums[i] = (i * 7 + variant) % 100
    nums[541] = 8 + variant        # plot
    nums[542], nums[543], nums[544] = 0, variant, 2   # menuchoice
    nums[545] = 3                  # currentsong
    nums[546] = 46 + variant       # currentroom
    nums[547] = 1000 + variant     # time
    (dir_path / "file0").write_bytes(
        projection.file0._serialize_file0(name, nums))
    # undertale.ini：已知段 + 未知段未知键（保留性口径）
    (dir_path / "undertale.ini").write_text(
        "[General]\r\n"
        f"fun={10 + variant}\r\n"
        "Kills=0\r\n"
        f"Love={variant + 1}\r\n"
        "[Flowey]\r\n"
        "k1=0\r\n"
        f"meta{variant}=v{variant}\r\n"
        "[UnknownSection]\r\n"
        f"unknown_key_{variant}=unknown_value_{variant}\r\n",
        encoding="utf-8", newline="")


class TestFlagSlotMapping(unittest.TestCase):
    """映射依据钉死：29+flag 仅对持久区 [500,511] 合法。"""

    def test_slot_mapping_bounds(self):
        self.assertEqual(flag_slot(500), 529)
        self.assertEqual(flag_slot(511), 540)

    def test_flag_512_and_above_rejected(self):
        # 包 17 关键发现：flag≥512 不入存档且映射越位（踩 plot 等）
        for fid in (512, 520, 999):
            with self.assertRaises(errors.ValidationError) as cm:
                flag_slot(fid)
            self.assertIn("不可投影", str(cm.exception))

    def test_outside_declared_zone_rejected(self):
        for fid in (0, 499, 1000):
            with self.assertRaises(errors.ValidationError):
                flag_slot(fid)

    def test_type_guard(self):
        for bad in ("512", None, True):
            with self.assertRaises(errors.ValidationError):
                flag_slot(bad)

    def test_occupancy_census(self):
        # 持久区全占用（普查：500-512 全部被引用）
        for fid in range(500, 513):
            occ = check_flag_occupancy(fid)
            self.assertTrue(occ, f"flag {fid} 应有占用记录")
        self.assertIn("SCR_GAMESTART(清零)", check_flag_occupancy(512))
        # 空带无引用
        self.assertEqual(check_flag_occupancy(520), [])
        self.assertEqual(check_flag_occupancy(999), [])


class TestRoundTripTwoCopies(unittest.TestCase):
    """两份独立合成存档副本：投影写入 → 逐项比较（未知字段保留）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="dl17_proj_")
        self.addCleanup(self._tmp.cleanup)
        self.a = Path(self._tmp.name) / "copyA"
        self.b = Path(self._tmp.name) / "copyB"
        self.a.mkdir()
        self.b.mkdir()
        _fixture_save(self.a, variant=1)
        _fixture_save(self.b, variant=2)

    @staticmethod
    def _read_all(save_dir: Path) -> tuple[str, list[int], bytes]:
        f0 = save_dir / "file0"
        name, nums = projection.file0._parse_file0(f0)
        return name, nums, f0.read_bytes()

    def test_projection_changes_exactly_one_slot(self):
        for save_dir in (self.a, self.b):
            name_before, nums_before, ini_before = (
                self._read_all(save_dir)[0], self._read_all(save_dir)[1],
                (save_dir / "undertale.ini").read_bytes())
            diff = apply_flag_writes(save_dir, {511: 3})
            self.assertEqual(diff, {511: (nums_before[540], 3)})
            name_after, nums_after, _ = self._read_all(save_dir)
            # 逐项比较：名字 + 除投影槽位外的全部数值位 + INI 字节
            self.assertEqual(name_after, name_before)
            for i in range(len(nums_before)):
                if i != 540:
                    self.assertEqual(nums_after[i], nums_before[i],
                                     f"槽位 {i} 被意外改动")
            self.assertEqual(nums_after[540], 3)
            self.assertEqual((save_dir / "undertale.ini").read_bytes(),
                             ini_before)

    def test_two_independent_copies_diverge_only_in_slot(self):
        # 两副本基值不同（独立性）；同一投影在两副本各自落位（slot=3），
        # 投影槽之外保持各自的独立基值（互不串写）
        apply_flag_writes(self.a, {511: 3})
        apply_flag_writes(self.b, {511: 3})
        name_a, nums_a, _ = self._read_all(self.a)
        name_b, nums_b, _ = self._read_all(self.b)
        self.assertNotEqual(name_a, name_b)
        self.assertEqual(nums_a[540], 3)   # 29+511
        self.assertEqual(nums_b[540], 3)
        # 独立基值在投影后仍各自保留（抽查 variant 驱动位）
        self.assertNotEqual(nums_a[0], nums_b[0])      # lv
        self.assertNotEqual(nums_a[9], nums_b[9])      # gold
        self.assertNotEqual(nums_a[541], nums_b[541])  # plot
        self.assertNotEqual(nums_a[547], nums_b[547])  # time

    def test_unknown_fields_preserved(self):
        # "未知字段"（已知表之外的数值位 + INI 未知段/键）逐位保留
        _, nums_before, _ = self._read_all(self.a)
        apply_flag_writes(self.a, {505: 77})   # 持久区另一槽（仅演示往返）
        _, nums_after, _ = self._read_all(self.a)
        # 大量"未知"数值位（此处取若干代表位）不变
        for probe_idx in (100, 200, 300, 400, 500, 530, 545, 546, 547):
            self.assertEqual(nums_after[probe_idx], nums_before[probe_idx])
        ini = (self.a / "undertale.ini").read_text(encoding="utf-8")
        self.assertIn("[UnknownSection]", ini)
        self.assertIn("unknown_key_1=unknown_value_1", ini)
        self.assertIn("meta1=v1", ini)

    def test_roundtrip_idempotent_value(self):
        apply_flag_writes(self.a, {511: 3})
        _, nums1, _ = self._read_all(self.a)
        apply_flag_writes(self.a, {511: 3})
        _, nums2, _ = self._read_all(self.a)
        self.assertEqual(nums1, nums2)

    def test_short_file_rejected_without_padding(self):
        # 存档长度不足 → 拒绝（不补零伪造字段）
        short = self.a / "file0"
        name, nums = projection.file0._parse_file0(short)
        short.write_bytes(projection.file0._serialize_file0(
            name, nums[:100]))
        with self.assertRaises(errors.ValidationError) as cm:
            apply_flag_writes(self.a, {511: 3})
        self.assertIn("不补零", str(cm.exception))

    def test_value_domain_guard(self):
        for bad in (-1, 1000, "3", None, True):
            with self.assertRaises(errors.ValidationError):
                apply_flag_writes(self.a, {511: bad})

    def test_read_flag(self):
        apply_flag_writes(self.a, {505: 77})
        self.assertEqual(read_flag(self.a, 505), 77)
        with self.assertRaises(errors.ValidationError):
            read_flag(self.a, 512)  # 不可投影 → 读也拒绝


class TestBranchProjectionConsistency(unittest.TestCase):
    """分支结果与回访资格一致：机器轨迹 → 投影 → 读回 → 回读状态。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="dl17_branch_")
        self.addCleanup(self._tmp.cleanup)
        self.save = Path(self._tmp.name) / "copyA"
        self.save.mkdir()
        _fixture_save(self.save, variant=1)
        self.defn = _defn(FLAG_V2)          # flag_id 511, persistence=flag
        self.defn["_version"] = "v2"

    def test_accept_branch_projection(self):
        m = QuestMachine(self.defn)
        m.trigger("requester", "yes")       # accepted (code 1)
        m.trigger("star", "yes")            # carrying (code 3)
        writes = project_state(self.defn, m.state)
        self.assertEqual(writes, {511: 3})
        apply_flag_writes(self.save, writes)
        self.assertEqual(read_flag(self.save, 511), 3)
        # 读回 → 状态还原 → 回访资格一致（requester 守卫不再满足）
        restored = read_state(self.defn, read_flag(self.save, 511))
        self.assertEqual(restored, "carrying")
        m.load(3)
        self.assertEqual(m.state, "carrying")
        m.trigger("requester", "yes")
        self.assertIn("守卫", m.trace[-1]["diagnostic"])
        self.assertEqual(m.state, "carrying")

    def test_reject_branch_projection(self):
        m = QuestMachine(self.defn)
        m.trigger("requester", "no")        # rejected (code 2)
        writes = project_state(self.defn, m.state)
        self.assertEqual(writes, {511: 2})
        apply_flag_writes(self.save, writes)
        restored = read_state(self.defn, read_flag(self.save, 511))
        self.assertEqual(restored, "rejected")
        # 拒绝线回访资格：重触发无转换（吸收态）
        m.load(2)
        m.trigger("star", "yes")
        self.assertEqual(m.state, "rejected")

    def test_save_load_roundtrip_full_chain(self):
        m = QuestMachine(self.defn)
        m.trigger("requester", "yes")
        rec = m.save()                       # 机器层投影
        apply_flag_writes(self.save, {511: rec["projected_code"]})
        # 模拟读档：从存档旗标重建
        m2 = QuestMachine(self.defn)
        m2.load(read_flag(self.save, 511))
        self.assertEqual(m2.state, "accepted")

    def test_session_machine_has_no_projection(self):
        defn = _defn(MAIN_V2)
        with self.assertRaises(StorylineError) as cm:
            project_state(defn, "accepted")
        self.assertIn("无存档投影", str(cm.exception))


class TestV1ReservedFlagContract(unittest.TestCase):
    """v1 预留 flag 合同通过：declared-only，无投影写路径。"""

    def test_v1_flag_declared_only_no_projection(self):
        from deterline.storyline import _read_definition
        v1 = _read_definition(
            "schema: deterline.storyline/v1\npatch_id: det_t1\n"
            "room: room_ruins1\nnpc:\n  object: obj_npc_marker\n"
            "  x: 100\n  y: 200\n  prompt: \"* Hi& &         Yes         No"
            "      \\C \"\n  yes_text: \"* Yes./%%\"\n"
            "  no_text: \"* No./%%\"\nflag_id: 509\n")
        with self.assertRaises(StorylineError):
            project_state(v1, "whatever")    # v1 无 states——投影拒绝

    def test_v1_persisted_zone_flag_has_occupancy_record(self):
        # v1 样例 flag 509/508 落在占用区——登记事实（declared-only 无写
        # 路径；若未来接线须先换旗标）
        self.assertTrue(check_flag_occupancy(509))
        self.assertTrue(check_flag_occupancy(508))


if __name__ == "__main__":
    unittest.main()
