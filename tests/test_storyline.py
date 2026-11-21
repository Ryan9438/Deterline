"""storyline 编排层测试（12 计划 C2/C3/C4）。

yaml_min 拒绝面 / 合同封闭字段 / 只读计划（mock UTMT）/ build 声明差异 /
apply 幂等·漂移·同 ID 异内容。全部 tmp 隔离零 UTMT。
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from deterline.storyline import (APPLY_SCHEMA, StorylineError, yaml_min)  # noqa: E402
from deterline.storyline.commands import (  # noqa: E402
    cmd_storyline_apply, cmd_storyline_build, cmd_storyline_plan)
from deterline.storyline import _read_definition  # noqa: E402


GOOD_DEFN = """schema: deterline.storyline/v1
patch_id: det_demo_c2
room: room_golden
npc:
  object: obj_golden_npc
  x: 320
  y: 240
  range: 60
  prompt: "* Go?& &      Yes      No    \\C "
  yes_text: "* Done./%%"
  no_text: "* Later./%%"
  once: true
flag_id: 505
"""


class YamlMinTest(unittest.TestCase):
    def test_happy_path(self):
        doc = yaml_min.parse(GOOD_DEFN.replace("\\C", "\\C"))
        self.assertEqual(doc["patch_id"], "det_demo_c2")
        self.assertEqual(doc["npc"]["x"], 320)
        self.assertTrue(doc["npc"]["once"] is True)

    def test_rejections(self):
        cases = {
            "重复键": "a: 1\na: 2",
            "锚点": "a: &x 1",
            "别名": "a: *x",
            "流式映射": "a: {b: 1}",
            "流式序列": "a: [1]",
            "tab": "\ta: 1",
            "多文档": "---\na: 1",
            "序列内映射": "items:\n  - x: 1",
            "标签": "!x a: 1",
            "顶层裸标量": "plain",
        }
        for why, bad in cases.items():
            with self.assertRaises(yaml_min.YamlMinError, msg=why):
                yaml_min.parse(bad)


class ContractTest(unittest.TestCase):
    def test_good_definition_parses(self):
        doc = _read_definition(GOOD_DEFN)
        self.assertEqual(doc["patch_id"], "det_demo_c2")

    def test_unknown_top_field_rejected(self):
        with self.assertRaises(StorylineError) as ctx:
            _read_definition(GOOD_DEFN + "evil_field: 1\n")
        self.assertIn("未知字段", str(ctx.exception))

    def test_unknown_npc_field_rejected(self):
        bad = GOOD_DEFN.replace("  once: true\n",
                                "  once: true\n  inject: gml\n")
        with self.assertRaises(StorylineError) as ctx:
            _read_definition(bad)
        self.assertIn("npc 未知字段", str(ctx.exception))

    def test_schema_drift_rejected(self):
        with self.assertRaises(StorylineError) as ctx:
            _read_definition(GOOD_DEFN.replace(
                "deterline.storyline/v1", "deterline.storyline/v2"))
        self.assertIn("版本漂移", str(ctx.exception))

    def test_prompt_requires_choice_marker(self):
        bad = GOOD_DEFN.replace("\\C ", "    ")
        with self.assertRaises(StorylineError):
            _read_definition(bad)

    def test_non_ascii_rejected_v1(self):
        bad = GOOD_DEFN.replace("* Go?", "* 东行？")
        with self.assertRaises(StorylineError) as ctx:
            _read_definition(bad)
        self.assertIn("ASCII", str(ctx.exception))

    def test_flag_range_enforced(self):
        bad = GOOD_DEFN.replace("flag_id: 505", "flag_id: 12")
        with self.assertRaises(StorylineError):
            _read_definition(bad)

    def test_branch_text_with_choice_marker_rejected(self):
        bad = GOOD_DEFN.replace('"* Done./%%"', '"* Again\\\\C /%%"')
        with self.assertRaises(StorylineError):
            _read_definition(bad)


def _fake_npc_target(game_file, obj_name):
    return {"obj": obj_name, "native": True,
            "step_code": f"gml_Object_{obj_name}_Step_0",
            "alarm_code": f"gml_Object_{obj_name}_Alarm_0"}


def _fake_idx(game_file, room_name):
    return 42


class PlanTest(unittest.TestCase):
    def test_plan_resolves_with_mocks(self):
        import deterline.storyline as sl
        defn = dict(_read_definition(GOOD_DEFN))
        defn["_sha256"] = "0" * 64
        game = Path("/tmp/fake.ios")
        with mock.patch("deterline.cmds.template_common.idx_room_lookup",
                        side_effect=_fake_idx), \
                mock.patch("deterline.cmds.npc._query_npc_target",
                           side_effect=_fake_npc_target), \
                mock.patch("deterline.storyline._room_match_count",
                           return_value=(1, 0)), \
                mock.patch("deterline.storyline._room_name_by_idx",
                           return_value="room_golden"), \
                mock.patch("deterline.cmds.npc._find_create_code",
                           return_value=None):
            plan = sl.build_plan(defn, game)
        self.assertEqual(plan["room"]["idx"], 42)
        self.assertEqual(plan["room"]["exact_hits"], 1)
        self.assertEqual(plan["room"]["name"], "room_golden")
        self.assertEqual(plan["room"]["requested"], "room_golden")
        self.assertEqual(plan["npc"]["object"], "obj_golden_npc")
        er = plan["expected_resources"]
        self.assertEqual(er["str_total"], 9)
        self.assertEqual(er["code_added"], 1)   # append 路径：仅 Create_0
        self.assertEqual(er["code_changed"], 3)  # textdata + Step_0 追加 + Alarm 守卫
        self.assertEqual(er["code_mode"], "append")
        self.assertEqual(er["code_mode_create"], "create")
        self.assertIsNone(er["code_entry_create"])
        self.assertTrue(er["alarm_guard"])
        self.assertEqual(plan["flag"]["status"], "declared-only")
        # 结构层期望（F1）
        es = plan["expected_structure"]
        self.assertEqual(es["count_deltas"], {
            "STRGCOUNT": 9, "CODECOUNT": 1, "SPRCOUNT": 0, "TEXCOUNT": 0,
            "LASTOBJ": 0, "VARS": 1})
        self.assertEqual(es["var_added"], "deterline_state")
        self.assertEqual(es["room_inst"], {"room_golden": 1})
        self.assertEqual(es["code_added"],
                         ["gml_Object_obj_golden_npc_Create_0"])
        self.assertEqual(es["code_changed"],
                         ["gml_Object_obj_golden_npc_Alarm_0",
                          "gml_Object_obj_golden_npc_Step_0",
                          "gml_Script_textdata_en"])

    def test_plan_create_prepend_branch(self):
        """F2：自有 Create_0 存在但未引用变量 → prepend 式（changed +1）。"""
        import deterline.storyline as sl
        defn = dict(_read_definition(GOOD_DEFN))
        defn["_sha256"] = "0" * 64
        with mock.patch("deterline.cmds.template_common.idx_room_lookup",
                        side_effect=_fake_idx), \
                mock.patch("deterline.cmds.npc._query_npc_target",
                           side_effect=_fake_npc_target), \
                mock.patch("deterline.storyline._room_match_count",
                           return_value=(1, 0)), \
                mock.patch("deterline.storyline._room_name_by_idx",
                           return_value="room_golden"), \
                mock.patch("deterline.cmds.npc._find_create_code",
                           return_value="gml_Object_obj_golden_npc_Create_0"), \
                mock.patch("deterline.cmds.code.decompile_classified",
                           return_value=("ok", ["pushother = 2;"], "")):
            plan = sl.build_plan(defn, Path("/tmp/fake.ios"))
        er = plan["expected_resources"]
        self.assertEqual(er["code_mode_create"], "prepend")
        self.assertEqual(er["code_entry_create"],
                         "gml_Object_obj_golden_npc_Create_0")
        # step 存在(+0 added) + create 已有(+0 added) → added = 0
        self.assertEqual(er["code_added"], 0)
        self.assertEqual(er["code_changed"], 4)  # textdata + append + alarm + prepend
        es = plan["expected_structure"]
        self.assertEqual(es["count_deltas"]["CODECOUNT"], 0)
        self.assertEqual(es["code_added"], [])
        self.assertIn("gml_Object_obj_golden_npc_Create_0", es["code_changed"])
        self.assertTrue(any("前插" in d for d in plan["diagnostics"]))

    def test_plan_create_skip_branch_is_refused_clean_baseline(self):
        """F2：有效 Create_0 已引用 deterline_state → skip 式标定 + 干净基线
        诊断（结构闸门按 va 非空拒绝该形态——v1 单发合同）。"""
        import deterline.storyline as sl
        defn = dict(_read_definition(GOOD_DEFN))
        defn["_sha256"] = "0" * 64
        with mock.patch("deterline.cmds.template_common.idx_room_lookup",
                        side_effect=_fake_idx), \
                mock.patch("deterline.cmds.npc._query_npc_target",
                           side_effect=_fake_npc_target), \
                mock.patch("deterline.storyline._room_match_count",
                           return_value=(1, 0)), \
                mock.patch("deterline.storyline._room_name_by_idx",
                           return_value="room_golden"), \
                mock.patch("deterline.cmds.npc._find_create_code",
                           return_value="gml_Object_obj_golden_npc_Create_0"), \
                mock.patch("deterline.cmds.code.decompile_classified",
                           return_value=("ok", ["deterline_state = 0;"], "")):
            plan = sl.build_plan(defn, Path("/tmp/fake.ios"))
        er = plan["expected_resources"]
        self.assertEqual(er["code_mode_create"], "skip")
        self.assertEqual(er["code_added"], 0)
        self.assertEqual(er["code_changed"], 3)  # textdata + append + alarm
        self.assertTrue(any("非干净" in d or "deterline_state" in d
                            for d in plan["diagnostics"]))

    def test_plan_create_prepend_inherited_diagnostic(self):
        """F2：Create 事件继承自父对象 → 诊断点名改动落在父条目。"""
        import deterline.storyline as sl
        defn = dict(_read_definition(GOOD_DEFN))
        defn["_sha256"] = "0" * 64
        with mock.patch("deterline.cmds.template_common.idx_room_lookup",
                        side_effect=_fake_idx), \
                mock.patch("deterline.cmds.npc._query_npc_target",
                           side_effect=_fake_npc_target), \
                mock.patch("deterline.storyline._room_match_count",
                           return_value=(1, 0)), \
                mock.patch("deterline.storyline._room_name_by_idx",
                           return_value="room_golden"), \
                mock.patch("deterline.cmds.npc._find_create_code",
                           return_value="gml_Object_obj_parent_Create_0"), \
                mock.patch("deterline.cmds.code.decompile_classified",
                           return_value=("ok", ["hp = 3;"], "")):
            plan = sl.build_plan(defn, Path("/tmp/fake.ios"))
        self.assertEqual(plan["expected_resources"]["code_mode_create"],
                         "prepend")
        self.assertEqual(
            plan["expected_resources"]["code_entry_create"],
            "gml_Object_obj_parent_Create_0")
        self.assertTrue(any("继承" in d for d in plan["diagnostics"]))

    def test_plan_create_probe_read_failure_refuses(self):
        """F2：Create 探针读失败 → 拒绝标定（读失败不作空/已初始化假设，B3 口径）。"""
        import deterline.storyline as sl
        defn = dict(_read_definition(GOOD_DEFN))
        defn["_sha256"] = "0" * 64
        with mock.patch("deterline.cmds.template_common.idx_room_lookup",
                        side_effect=_fake_idx), \
                mock.patch("deterline.cmds.npc._query_npc_target",
                           side_effect=_fake_npc_target), \
                mock.patch("deterline.storyline._room_match_count",
                           return_value=(1, 0)), \
                mock.patch("deterline.storyline._room_name_by_idx",
                           return_value="room_golden"), \
                mock.patch("deterline.cmds.npc._find_create_code",
                           return_value="gml_Object_obj_golden_npc_Create_0"), \
                mock.patch("deterline.cmds.code.decompile_classified",
                           return_value=("error", None, "UTMT timeout")):
            with self.assertRaises(Exception) as ctx:
                sl.build_plan(defn, Path("/tmp/fake.ios"))
        self.assertIn("读失败", str(ctx.exception))

    def test_plan_rejects_missing_room(self):
        import deterline.storyline as sl
        defn = dict(_read_definition(GOOD_DEFN))
        defn["_sha256"] = "0" * 64
        with mock.patch("deterline.cmds.template_common.idx_room_lookup",
                        return_value=-1):
            with self.assertRaises(Exception) as ctx:
                sl.build_plan(defn, Path("/tmp/fake.ios"))
        self.assertIn("房间不存在", str(ctx.exception))

    def test_plan_rejects_ambiguous_room(self):
        """R13 P2-3：定义侧房间歧义（exact 1 + 其余子串命中）写前拒绝。"""
        import deterline.storyline as sl
        defn = dict(_read_definition(GOOD_DEFN))
        defn["_sha256"] = "0" * 64
        with mock.patch("deterline.cmds.template_common.idx_room_lookup",
                        return_value=42), \
                mock.patch("deterline.storyline._room_name_by_idx",
                           return_value="room_golden"), \
                mock.patch("deterline.storyline._room_match_count",
                           return_value=(2, 0)):
            with self.assertRaises(Exception) as ctx:
                sl.build_plan(defn, Path("/tmp/fake.ios"))
        self.assertIn("歧义", str(ctx.exception))

    def test_plan_rejects_missing_object(self):
        import deterline.storyline as sl
        defn = dict(_read_definition(GOOD_DEFN))
        defn["_sha256"] = "0" * 64
        with mock.patch("deterline.cmds.template_common.idx_room_lookup",
                        return_value=42), \
                mock.patch("deterline.storyline._room_name_by_idx",
                           return_value="room_golden"), \
                mock.patch("deterline.storyline._room_match_count",
                           return_value=(1, 0)), \
                mock.patch("deterline.cmds.npc._query_npc_target",
                           return_value=None):
            with self.assertRaises(Exception) as ctx:
                sl.build_plan(defn, Path("/tmp/fake.ios"))
        self.assertIn("对象不存在", str(ctx.exception))


class StorylineEndToEnd(unittest.TestCase):
    """build/apply 编排层全流程：域生成器与 O7 打 mock（其行为已由
    golden/C1 实录钉死），**文件面全部真实**（工作区产物/EditPlan/回执）。"""

    # 真实 O7 --detail 形态（R14 P1-1：汇总行全量计数 + STR 明细 op；
    # F1：结构段 COUNT/VARDETERLINE/ROOM/CODE 行同入闸门）——
    # fake 输出必须与 verify.py 实际打印同构，捏造行会让闸门测试失真。
    # 形状对应 fake 目标（append+alarm+create 式）：CODE 新增 1（Create_0）、
    # CODE 变化 3（Alarm_0/Step_0/textdata_en）、VARS +1、目标房 inst +1
    DECLARED_DIFF = ("--- diff-snapshots ---\n"
                     "  A=base\n  B=product\n"
                     "  COUNT CODECOUNT: 1612 → 1613\n"
                     "  COUNT STRGCOUNT: 434 → 443\n"
                     "  COUNT VARS: 4800 → 4801\n"
                     "  VARDETERLINE: [] → ['deterline_state:4321:1']\n"
                     "  ROOM inst room_golden: inst=56 → inst=57\n"
                     "  CODE 新增: gml_Object_obj_golden_npc_Create_0 (instr=2)\n"
                     "  CODE 变化: gml_Object_obj_golden_npc_Alarm_0: instr 12 → 15\n"
                     "  CODE 变化: gml_Object_obj_golden_npc_Step_0: instr 40 → 71\n"
                     "  CODE 变化: gml_Script_textdata_en: instr 320 → 329\n"
                     "--- 资源级差异（--detail） ---\n"
                     "  字符串: 9 处变化（add/change/remove，内容哈希锚定）\n"
                     "  实例: add=1 remove=0 move=0\n"
                     "  代码指纹: changed=3 added=1 removed=0\n"
                     "  字体: changed=0 added=0 removed=0\n"
                     "    STR add len=14 sha=a1\n"
                     "    STR add len=19 sha=c7\n"
                     "    STR add len=11 sha=d7\n"
                     "    INST move id=1 x\n"   # 真实形态：实例明细仅 move 行
                     "    CODEF changed gml_Script_textdata_en\n"
                     "  ⚠️ 资源级差异 5 处\n"
                     "\n⚠️ 共 6 处差异（含资源级）\n")

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="deterline_story_"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.game = self.root / "game.ios"
        self.game.write_bytes(b"BASE-GAME-CONTENT")
        self.defn_path = self.root / "storyline.yaml"
        self.defn_path.write_text(GOOD_DEFN, encoding="utf-8")
        from deterline import state
        state.WORKSPACE = None
        state.PREVIEW = False
        # 状态卫生：E2E 会改 WORKSPACE/PREVIEW——测试后恢复原值，
        # 防止顺序依赖污染后续测试（write_policy/utmt_spine 曾受害）
        for attr in ("WORKSPACE", "PREVIEW"):
            self.addCleanup(setattr, state, attr, getattr(state, attr))
        # plan 解析层 mock（只读解析已由 PlanTest 单独钉）
        self._p1 = mock.patch("deterline.cmds.template_common.idx_room_lookup",
                              return_value=42)
        self._p2 = mock.patch("deterline.cmds.npc._query_npc_target",
                              side_effect=_fake_npc_target)
        self._p1.start()
        self._p2.start()
        self.addCleanup(self._p1.stop)
        self.addCleanup(self._p2.stop)
        self._p5 = mock.patch("deterline.storyline._room_match_count",
                              return_value=(1, 0))
        self._p5.start()
        self.addCleanup(self._p5.stop)
        # F1/F2 新探针：实际房间名 + Create 事件形态（fake 目标 = 无 Create
        # → create 式，与 DECLARED_DIFF 的 CODE 新增 Create_0 一致）
        self._p6 = mock.patch("deterline.storyline._room_name_by_idx",
                              return_value="room_golden")
        self._p7 = mock.patch("deterline.cmds.npc._find_create_code",
                              return_value=None)
        self._p6.start()
        self._p7.start()
        self.addCleanup(self._p6.stop)
        self.addCleanup(self._p7.stop)
        # 域生成器 mock：写真实工作区产物 + **真实形状 manifest**（R13 P1-5：
        # apply 现在要求 manifest 在场——source/source_sha256/history 末条
        # = 产物 sha；确定性派生，不用 hash()，R14 P3-7）
        def fake_choice(game_file, *a, **k):
            import hashlib as _h
            from deterline import sandbox, state as st
            product = sandbox.sandbox_path(game_file)
            product.parent.mkdir(parents=True, exist_ok=True)
            tag = _h.sha256((st.WORKSPACE or "").encode()).hexdigest()[:8]
            data = game_file.read_bytes() + f"\n<patch:{st.WORKSPACE}:{tag}>".encode()
            product.write_bytes(data)
            manifest = {
                "source": str(game_file.resolve()),
                "source_sha256": _h.sha256(game_file.read_bytes()).hexdigest(),
                "history": [{"action": "mock-build",
                             "sha256": _h.sha256(data).hexdigest()}],
            }
            product.with_name(product.name + ".json").write_text(
                json.dumps(manifest), encoding="utf-8")
            print("OK: (mock 域生成器写入工作区)")
        self._p3 = mock.patch("deterline.cmds.npc.cmd_npc_choice",
                              side_effect=fake_choice)
        self._p3.start()
        self.addCleanup(self._p3.stop)
        # O7 mock：输出声明差异形态、记录调用、返回差异数
        self._diff_calls = []

        def fake_diff(file_a, file_b, detail=False, **k):
            self._diff_calls.append((file_a, file_b, detail))
            print(self.DECLARED_DIFF)
            return 5

        self.diff_mock = mock.patch("deterline.cmds.verify.cmd_diff_snapshots",
                                    side_effect=fake_diff)
        self.diff_mock.start()
        self.addCleanup(self.diff_mock.stop)

    def _capture(self, fn, *a, **k):
        import io
        import contextlib
        buf_out, buf_err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            rc = fn(*a, **k)
        return rc, buf_out.getvalue(), buf_err.getvalue()

    def _product(self, ws):
        return (self.root / ".deterline" / "game.ios" / ws / "game.ios")

    def test_build_creates_candidate_with_declared_diff(self):
        rc, out, err = self._capture(
            cmd_storyline_build, self.game, str(self.defn_path), "det_ws")
        self.assertEqual(rc, 0, msg=out + err)
        product = self._product("det_ws")
        self.assertTrue(product.is_file())
        self.assertNotEqual(product.read_bytes(), b"BASE-GAME-CONTENT")
        # O7 mock 收到（基线, 产物）且 detail=True（build 入口 resolve 后路径）
        self.assertEqual(len(self._diff_calls), 1)
        self.assertEqual(self._diff_calls[0][0], self.game.resolve())
        self.assertEqual(self._diff_calls[0][1], product.resolve())
        self.assertTrue(self._diff_calls[0][2])
        # 构建回执落盘（apply 的核对依据）
        build_rcpt = (self.root / ".deterline" / "storyline" /
                      "game.ios" / "det_demo_c2" / "build.json")
        self.assertTrue(build_rcpt.is_file())
        self.assertEqual(json.loads(build_rcpt.read_text(encoding="utf-8"))
                         ["declared_diff"].get("STR total"), 9)
        self.assertEqual(json.loads(build_rcpt.read_text(encoding="utf-8"))
                         ["declared_str_ops"], ["add", "add", "add"])

    def test_build_refuses_undeclared_resource_change(self):
        """C3 验收：未声明资源变更（真实 O7 形态：字体页变更）→ 拒绝出候选。"""
        self.diff_mock.stop()

        def fake_diff(file_a, file_b, detail=False, **k):
            print("--- 资源级差异（--detail） ---")
            print("  字符串: 9 处变化（add/change/remove，内容哈希锚定）")
            print("  实例: add=1 remove=0 move=0")
            print("  代码指纹: changed=3 added=1 removed=0")
            print("  字体: changed=1 added=0 removed=0")   # 未声明：字体页变更
            return 6

        self.diff_mock = mock.patch("deterline.cmds.verify.cmd_diff_snapshots",
                                    side_effect=fake_diff)
        self.diff_mock.start()
        self.addCleanup(self.diff_mock.stop)
        rc, _o, err = self._capture(
            cmd_storyline_build, self.game, str(self.defn_path), "det_ws")
        self.assertEqual(rc, 1)
        self.assertIn("未声明资源/结构变更", err)
        self.assertIn("FONT changed", err)

    # ---- F1：结构段违规拒绝（真实 O7 形态：结构行 + 资源级汇总行同构）----

    def _replace_diff(self, fake_diff):
        self.diff_mock.stop()
        self.diff_mock = mock.patch("deterline.cmds.verify.cmd_diff_snapshots",
                                    side_effect=fake_diff)
        self.diff_mock.start()
        self.addCleanup(self.diff_mock.stop)

    def test_build_refuses_room_structure_change(self):
        """结构段：房间尺寸/tile/背景层变化 → 拒绝（资源级无法间接可见的形态）。"""
        self._replace_diff(lambda a, b, detail=False, **k: print(
            self.DECLARED_DIFF
            + "  ROOM 变化: room_golden: ('320x240', 'inst=57', 'tiles=5', "
              "'bg_x,') → ('640x480', 'inst=57', 'tiles=5', 'bg_x,')"
              "（inst 计数外的分量变化）") or 7)
        rc, _o, err = self._capture(
            cmd_storyline_build, self.game, str(self.defn_path), "det_ws")
        self.assertEqual(rc, 1)
        self.assertIn("ROOM 尺寸/tile/背景层变化: room_golden", err)

    def test_build_refuses_dirty_baseline_vardeterline(self):
        """结构段：基线已含 deterline* 变量 → 干净基线合同拒绝。"""
        self._replace_diff(lambda a, b, detail=False, **k: print(
            self.DECLARED_DIFF.replace(
                "VARDETERLINE: [] → ['deterline_state:4321:1']",
                "VARDETERLINE: ['deterline_state:99:1'] → "
                "['deterline_state:99:2']")) or 6)
        rc, _o, err = self._capture(
            cmd_storyline_build, self.game, str(self.defn_path), "det_ws")
        self.assertEqual(rc, 1)
        self.assertIn("基线已含 deterline* 变量", err)

    def test_build_refuses_nsid_zero_var(self):
        """结构段：新增 deterline_state NameStringID=0 → NSID=0 崩溃根因拒绝。"""
        self._replace_diff(lambda a, b, detail=False, **k: print(
            self.DECLARED_DIFF.replace(
                "VARDETERLINE: [] → ['deterline_state:4321:1']",
                "VARDETERLINE: [] → ['deterline_state:0:1']")) or 6)
        rc, _o, err = self._capture(
            cmd_storyline_build, self.game, str(self.defn_path), "det_ws")
        self.assertEqual(rc, 1)
        self.assertIn("NameStringID=0", err)

    def test_build_refuses_count_delta_mismatch(self):
        """结构段：COUNT 增量与声明不符（STRGCOUNT +10 vs 声明 9）→ 拒绝。"""
        self._replace_diff(lambda a, b, detail=False, **k: print(
            self.DECLARED_DIFF.replace(
                "COUNT STRGCOUNT: 434 → 443", "COUNT STRGCOUNT: 434 → 444")) or 6)
        rc, _o, err = self._capture(
            cmd_storyline_build, self.game, str(self.defn_path), "det_ws")
        self.assertEqual(rc, 1)
        self.assertIn("COUNT STRGCOUNT 变化 10（声明 9）", err)

    def test_build_refuses_undeclared_room_inst(self):
        """结构段：未声明房间的实例数变化 → 拒绝。"""
        self._replace_diff(lambda a, b, detail=False, **k: print(
            self.DECLARED_DIFF
            + "  ROOM inst room_other: inst=3 → inst=4") or 7)
        rc, _o, err = self._capture(
            cmd_storyline_build, self.game, str(self.defn_path), "det_ws")
        self.assertEqual(rc, 1)
        self.assertIn("ROOM inst room_other 变化 1（声明 0）", err)

    def test_build_refuses_extra_code_entry(self):
        """结构段：CODE 新增超出声明（额外代码条目）→ 拒绝。"""
        self._replace_diff(lambda a, b, detail=False, **k: print(
            self.DECLARED_DIFF.replace(
                "CODE 新增: gml_Object_obj_golden_npc_Create_0 (instr=2)",
                "CODE 新增: gml_Object_obj_golden_npc_Create_0 (instr=2)\n"
                "  CODE 新增: gml_Object_obj_evil_twin_Create_0 (instr=5)")) or 7)
        rc, _o, err = self._capture(
            cmd_storyline_build, self.game, str(self.defn_path), "det_ws")
        self.assertEqual(rc, 1)
        self.assertIn("CODE 新增", err)
        self.assertIn("obj_evil_twin", err)

    def test_apply_refuses_preview_and_commit(self):
        """preview×commit 互斥（R5 P2-3 同款）：--preview 语义不得被 commit 覆盖。"""
        from deterline import state
        state.PREVIEW = True
        rc, _o, err = self._capture(
            cmd_storyline_apply, None, self.game, str(self.defn_path),
            "det_ws", commit=True)
        self.assertEqual(rc, 1)
        self.assertIn("互斥", err)
        self.assertEqual(self.game.read_bytes(), b"BASE-GAME-CONTENT",
                         "preview×commit 拒绝后目标不得变化")

    def test_apply_preview_then_commit_and_idempotent(self):
        rc, _o, err = self._capture(
            cmd_storyline_build, self.game, str(self.defn_path), "det_ws")
        self.assertEqual(rc, 0, msg=err)
        built = self._product("det_ws").read_bytes()
        # 预览零动作
        rc, out, _ = self._capture(
            cmd_storyline_apply, None, self.game, str(self.defn_path),
            "det_ws", commit=False)
        self.assertEqual(rc, 0)
        self.assertEqual(self.game.read_bytes(), b"BASE-GAME-CONTENT")
        # commit：整包应用 + 回执
        rc, out, err = self._capture(
            cmd_storyline_apply, None, self.game, str(self.defn_path),
            "det_ws", commit=True)
        self.assertEqual(rc, 0, msg=err)
        self.assertEqual(self.game.read_bytes(), built)
        receipt_path = (self.root / ".deterline" / "storyline" /
                        "game.ios" / "det_demo_c2" / "receipt.json")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(receipt["schema"], APPLY_SCHEMA)
        self.assertEqual(receipt["after_sha256"],
                         __import__("hashlib").sha256(built).hexdigest())
        self.assertEqual(receipt["baseline_sha256"],
                         __import__("hashlib").sha256(
                             b"BASE-GAME-CONTENT").hexdigest())
        # 幂等：再 commit → 已应用 no-op（内容不变；判据 = 回执 defn_sha，
        # 工作区产物单次消费后不在盘上）
        rc, out, err = self._capture(
            cmd_storyline_apply, None, self.game, str(self.defn_path),
            "det_ws", commit=True)
        self.assertEqual(rc, 0)
        self.assertIn("幂等 no-op", out + err)
        self.assertEqual(self.game.read_bytes(), built)

    def test_apply_refuses_without_build_receipt(self):
        rc, _o, err = self._capture(
            cmd_storyline_apply, None, self.game, str(self.defn_path),
            "det_ws", commit=True)
        self.assertEqual(rc, 1)
        self.assertIn("无构建回执", err)
        self.assertEqual(self.game.read_bytes(), b"BASE-GAME-CONTENT")

    def test_apply_refuses_same_id_different_content(self):
        self._capture(cmd_storyline_build, self.game, str(self.defn_path),
                      "det_ws")
        self._capture(cmd_storyline_apply, None, self.game,
                      str(self.defn_path), "det_ws", commit=True)
        applied = self.game.read_bytes()
        # 同 ID 异内容：不同定义 → 不同产物（mock 产物含 defn 差异标记）
        self.defn_path.write_text(
            GOOD_DEFN.replace('"* Done./%%"', '"* Sure thing./%%"'),
            encoding="utf-8")
        rc, _o, err = self._capture(
            cmd_storyline_build, self.game, str(self.defn_path), "det_ws")
        self.assertEqual(rc, 0)
        rc, _o, err = self._capture(
            cmd_storyline_apply, None, self.game, str(self.defn_path),
            "det_ws", commit=True)
        self.assertEqual(rc, 1)
        self.assertIn("不同内容", err)
        self.assertEqual(self.game.read_bytes(), applied,
                         "同 ID 异内容拒绝后目标不得变化")

    def test_apply_refuses_target_drift(self):
        self._capture(cmd_storyline_build, self.game, str(self.defn_path),
                      "det_ws")
        self.game.write_bytes(b"DRIFTED-BY-SOMEONE-ELSE")
        rc, _o, err = self._capture(
            cmd_storyline_apply, None, self.game, str(self.defn_path),
            "det_ws", commit=True)
        self.assertEqual(rc, 1)
        self.assertIn("基线漂移", err)


if __name__ == "__main__":
    unittest.main()
