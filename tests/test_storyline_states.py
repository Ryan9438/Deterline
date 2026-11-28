"""storyline v2 状态机测试（16 号计划包 16）。

合同层：states 块校验（_validate_states 经 _read_definition_v2 全文路径）。
模拟层：QuestMachine 确定性轨迹（计划验收 = 接受 / 拒绝 / 重进 / 重复尝试
四条轨迹的期望状态与触发顺序 + 可解释错误路径 + 三层持久语义）。
计划层：states 进 v2 计划（mock 探针，进程内）+ 语义指纹重排稳定。

无 UTMT 依赖（探针全 mock 或不触）。
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import modify_save as ms  # noqa: E402,F401  （初始化 deterline 包路径）
import deterline.errors as errors_mod  # noqa: E402
from deterline.storyline import (  # noqa: E402
    StorylineError, _read_definition, _read_definition_v2, build_plan_v2,
    load_definition)
from deterline.storyline.state import QuestMachine  # noqa: E402

MAIN_V2 = """schema: deterline.storyline/v2
patch_id: det_t1
cjk: false
rooms:
  start: room_ruins1
  pickup: room_ruins2
  turn_in: room_ruins4
npcs:
  requester:
    room: start
    object: obj_npc_marker
    x: 100
    y: 200
    prompt: "* Hi& &         Yes         No      \\C "
    yes_text: "* Yes./%%"
    no_text: "* No./%%"
    once: false
  star:
    room: pickup
    object: obj_npc_marker
    x: 160
    y: 150
    prompt: "* Star?& &         Yes         No      \\C "
    yes_text: "* Taken./%%"
    no_text: "* Later./%%"
    once: false
  receiver:
    room: turn_in
    object: obj_npc_marker
    x: 160
    y: 150
    prompt: "* Thanks./%%"
    once: false
doors:
  to_pickup:
    from: start
    to: pickup
    x: 300
    y: 120
    spawn_x: 40
    spawn_y: 120
  to_turn_in:
    from: pickup
    to: turn_in
    x: 300
    y: 120
    spawn_x: 40
    spawn_y: 120
order:
  - npc:requester
  - door:to_pickup
  - npc:star
  - door:to_turn_in
  - npc:receiver
states:
  persistence: session
  initial: not_started
  not_started:
  accepted:
    enter:
      npc: requester
      answer: yes
    require: not_started
  rejected:
    enter:
      npc: requester
      answer: no
    require: not_started
  carrying:
    enter:
      npc: star
      answer: yes
    require: accepted
  delivered:
    enter:
      npc: receiver
    require: carrying
"""

# flag 持久化夹具：全状态 code（0-4 唯一），flag_id 511（持久区上限——
# 包 17：scr_saveprocess 只持久化 flag[0..511]）
FLAG_V2 = MAIN_V2.replace(
    "persistence: session", "persistence: flag").replace(
    "patch_id: det_t1", "patch_id: det_t1\nflag_id: 511").replace(
    "  not_started:\n", "  not_started:\n    code: 0\n").replace(
    "      answer: yes\n    require: not_started\n",
    "      answer: yes\n    require: not_started\n    code: 1\n", 1).replace(
    "      answer: no\n    require: not_started\n",
    "      answer: no\n    require: not_started\n    code: 2\n", 1).replace(
    "      answer: yes\n    require: accepted\n",
    "      answer: yes\n    require: accepted\n    code: 3\n", 1).replace(
    "      npc: receiver\n    require: carrying\n",
    "      npc: receiver\n    require: carrying\n    code: 4\n", 1)

STAR_ONCE_TRUE = MAIN_V2.replace(
    'no_text: "* Later./%%"\n    once: false',
    'no_text: "* Later./%%"\n    once: true')


def _defn(text: str = MAIN_V2) -> dict:
    return _read_definition_v2(text)


class TestStatesContract(unittest.TestCase):
    """states 块合同（fail-closed，错误指向字段）。"""

    def test_valid_machine_normalized(self):
        st = _defn()["states"]
        self.assertEqual(st["persistence"], "session")
        self.assertEqual(st["initial"], "not_started")
        self.assertEqual(st["map"]["accepted"]["enter"],
                         {"npc": "requester", "answer": "yes"})
        self.assertEqual(st["map"]["delivered"]["enter"], {"npc": "receiver"})
        self.assertEqual(st["map"]["not_started"], {})
        self.assertEqual(set(st["map"]), {
            "not_started", "accepted", "rejected", "carrying", "delivered"})

    def test_states_absent_ok(self):
        text = MAIN_V2.rsplit("states:", 1)[0]
        st = _defn(text)
        self.assertNotIn("states", st)

    def test_initial_required(self):
        text = MAIN_V2.replace("  initial: not_started\n", "")
        with self.assertRaises(StorylineError) as cm:
            _defn(text)
        self.assertIn("initial 必填", str(cm.exception))

    def test_initial_unknown_ref(self):
        text = MAIN_V2.replace("initial: not_started", "initial: nowhere")
        with self.assertRaises(StorylineError) as cm:
            _defn(text)
        self.assertIn("引用未声明状态", str(cm.exception))

    def test_initial_spec_must_be_empty(self):
        text = MAIN_V2.replace(
            "  not_started:\n",
            "  not_started:\n    enter:\n      npc: receiver\n")
        with self.assertRaises(StorylineError) as cm:
            _defn(text)
        self.assertIn("初始态是入口", str(cm.exception))

    def test_noninitial_bare_key_rejected(self):
        text = MAIN_V2.replace(
            "  carrying:\n    enter:\n      npc: star\n      answer: yes\n"
            "    require: accepted\n", "  carrying:\n")
        with self.assertRaises(StorylineError) as cm:
            _defn(text)
        self.assertIn("规格不能为空", str(cm.exception))

    def test_enter_unknown_npc(self):
        text = MAIN_V2.replace("      npc: requester", "      npc: ghost", 1)
        with self.assertRaises(StorylineError) as cm:
            _defn(text)
        self.assertIn("enter.npc", str(cm.exception))

    def test_choice_npc_answer_required_and_validated(self):
        bad_missing = MAIN_V2.replace(
            "      npc: requester\n      answer: yes",
            "      npc: requester", 1)
        with self.assertRaises(StorylineError) as cm:
            _defn(bad_missing)
        self.assertIn("answer 必须是", str(cm.exception))
        bad_value = MAIN_V2.replace(
            "      answer: yes", "      answer: maybe", 1)
        with self.assertRaises(StorylineError) as cm:
            _defn(bad_value)
        self.assertIn("answer 必须是", str(cm.exception))

    def test_talk_npc_answer_forbidden(self):
        text = MAIN_V2.replace(
            "      npc: receiver\n    require: carrying",
            "      npc: receiver\n      answer: yes\n    require: carrying")
        with self.assertRaises(StorylineError) as cm:
            _defn(text)
        self.assertIn("answer 不得出现", str(cm.exception))

    def test_require_unknown_and_self(self):
        bad = MAIN_V2.replace("    require: carrying", "    require: nowhere")
        with self.assertRaises(StorylineError) as cm:
            _defn(bad)
        self.assertIn("require 必须引用已声明状态", str(cm.exception))
        self_ok = MAIN_V2.replace(
            "    require: carrying", "    require: delivered")
        with self.assertRaises(StorylineError) as cm:
            _defn(self_ok)
        self.assertIn("不得自指", str(cm.exception))

    def test_require_without_enter_rejected(self):
        text = MAIN_V2.replace(
            "  rejected:\n    enter:\n      npc: requester\n"
            "      answer: no\n    require: not_started\n",
            "  rejected:\n    require: not_started\n")
        with self.assertRaises(StorylineError) as cm:
            _defn(text)
        self.assertIn("require 必须与 enter 同现", str(cm.exception))

    def test_unknown_state_field(self):
        text = MAIN_V2.replace("    require: carrying",
                               "    require: carrying\n    once: true")
        with self.assertRaises(StorylineError) as cm:
            _defn(text)
        self.assertIn("未知字段", str(cm.exception))

    def test_bad_state_identifier(self):
        text = MAIN_V2.replace("  rejected:", '  "9l":')
        with self.assertRaises(StorylineError) as cm:
            _defn(text)
        self.assertIn("标识符", str(cm.exception))

    def test_ambiguity_unguarded_in_multi(self):
        text = MAIN_V2.replace(
            "  carrying:\n    enter:\n      npc: star\n      answer: yes\n"
            "    require: accepted\n",
            "  carrying:\n    enter:\n      npc: star\n      answer: yes\n"
            "    require: accepted\n"
            "  carrying2:\n    enter:\n      npc: star\n      answer: yes\n")
        with self.assertRaises(StorylineError) as cm:
            _defn(text)
        self.assertIn("分派歧义", str(cm.exception))

    def test_ambiguity_colliding_guards(self):
        text = MAIN_V2.replace(
            "  carrying:\n    enter:\n      npc: star\n      answer: yes\n"
            "    require: accepted\n",
            "  carrying:\n    enter:\n      npc: star\n      answer: yes\n"
            "    require: accepted\n"
            "  carrying2:\n    enter:\n      npc: star\n      answer: yes\n"
            "    require: accepted\n")
        with self.assertRaises(StorylineError) as cm:
            _defn(text)
        self.assertIn("守卫相撞", str(cm.exception))

    def test_disjoint_guards_same_trigger_ok(self):
        # 同触发键按当前态路由：accepted→carrying，rejected→carrying_alt
        text = MAIN_V2.replace(
            "  carrying:\n    enter:\n      npc: star\n      answer: yes\n"
            "    require: accepted\n",
            "  carrying:\n    enter:\n      npc: star\n      answer: yes\n"
            "    require: accepted\n"
            "  carrying_alt:\n    enter:\n      npc: star\n      answer: yes\n"
            "    require: rejected\n")
        st = _defn(text)["states"]
        self.assertIn("carrying_alt", st["map"])

    def test_flag_persistence_requires_flag_id(self):
        text = FLAG_V2.replace("flag_id: 511\n", "")
        with self.assertRaises(StorylineError) as cm:
            _defn(text)
        # FLAG_V2 全状态带 code → 统一 code 检查先行（同槽位缺口）
        self.assertIn("需要顶层 flag_id", str(cm.exception))

    def test_flag_persistence_requires_persisted_range(self):
        # 包 17：flag≥512 不入存档（scr_saveprocess 上界）——持久化承诺
        # 必须落在 500-511；512 本身还被游戏代码占用
        for fid in (512, 520, 999):
            text = FLAG_V2.replace("flag_id: 511", f"flag_id: {fid}")
            with self.assertRaises(StorylineError) as cm:
                _defn(text)
            self.assertIn("500-511", str(cm.exception))

    def test_flag_persistence_requires_full_codes(self):
        text = FLAG_V2.replace("    code: 3\n", "")
        with self.assertRaises(StorylineError) as cm:
            _defn(text)
        self.assertIn("缺失", str(cm.exception))
        self.assertIn("carrying", str(cm.exception))

    def test_flag_persistence_unique_codes(self):
        text = FLAG_V2.replace("    code: 3\n", "    code: 1\n")
        with self.assertRaises(StorylineError) as cm:
            _defn(text)
        self.assertIn("code 重复", str(cm.exception))

    def test_code_range_and_session_rules(self):
        bad_range = FLAG_V2.replace("    code: 3\n", "    code: 1000\n")
        with self.assertRaises(StorylineError) as cm:
            _defn(bad_range)
        self.assertIn("0-999", str(cm.exception))
        # 包 18：session+code 需要顶层 flag_id（载体槽）；MAIN_V2 无 flag_id
        with self.assertRaises(StorylineError) as cm:
            _defn(MAIN_V2.replace("    require: carrying",
                                  "    require: carrying\n    code: 1"))
        self.assertIn("需要顶层 flag_id", str(cm.exception))

    def test_session_partial_codes_valid_with_flag(self):
        # 包 18：session + flag_id + 局部 code = 运行时载体编码（合法）
        text = MAIN_V2.replace(
            "patch_id: det_t1", "patch_id: det_t1\nflag_id: 520").replace(
            "    require: carrying", "    require: carrying\n    code: 4")
        st = _defn(text)["states"]
        self.assertEqual(st["map"]["delivered"]["code"], 4)
        self.assertEqual(st["persistence"], "session")

    def test_session_duplicate_codes_rejected(self):
        text = MAIN_V2.replace(
            "patch_id: det_t1", "patch_id: det_t1\nflag_id: 520").replace(
            "    require: carrying", "    require: carrying\n    code: 4").replace(
            "      answer: yes\n    require: not_started\n",
            "      answer: yes\n    require: not_started\n    code: 4\n", 1)
        with self.assertRaises(StorylineError) as cm:
            _defn(text)
        self.assertIn("code 重复", str(cm.exception))

    def test_flag_machine_parses(self):
        st = _defn(FLAG_V2)["states"]
        self.assertEqual(st["persistence"], "flag")
        self.assertEqual({s: m["code"] for s, m in st["map"].items()},
                         {"not_started": 0, "accepted": 1, "rejected": 2,
                          "carrying": 3, "delivered": 4})


class TestQuestMachineTrajectories(unittest.TestCase):
    """四条标准轨迹 + 错误路径 + 三层持久语义（确定性、可重放）。"""

    def test_accept_trajectory(self):
        m = QuestMachine(_defn())
        self.assertEqual(m.state, "not_started")
        m.trigger("requester", "yes")
        self.assertEqual(m.state, "accepted")
        m.trigger("star", "yes")
        self.assertEqual(m.state, "carrying")
        m.trigger("receiver")
        self.assertEqual(m.state, "delivered")
        # 轨迹逐步可重放（触发顺序入 trace）
        self.assertEqual(
            [(r["event"], r["from"], r["to"]) for r in m.trace],
            [("trigger", "not_started", "accepted"),
             ("trigger", "accepted", "carrying"),
             ("trigger", "carrying", "delivered")])

    def test_reject_trajectory_absorbing(self):
        m = QuestMachine(_defn())
        m.trigger("requester", "no")
        self.assertEqual(m.state, "rejected")
        # 拒绝线收束：再答 yes/no 均不改变状态（守卫未满足 → 可解释）
        m.trigger("requester", "yes")
        self.assertEqual(m.state, "rejected")
        self.assertIn("守卫", m.trace[-1]["diagnostic"])
        m.trigger("requester", "no")
        self.assertEqual(m.state, "rejected")

    def test_out_of_order_error_paths(self):
        m = QuestMachine(_defn())
        # 未接受取星 / 未携带递交：守卫未满足，原地不动
        m.trigger("star", "yes")
        self.assertEqual(m.state, "not_started")
        self.assertIn("守卫", m.trace[-1]["diagnostic"])
        m.trigger("receiver")
        self.assertEqual(m.state, "not_started")
        # 未声明分支：star 的 no 无状态 enter → 无转换（与守卫拒绝分述）
        m.trigger("requester", "yes")
        m.trigger("star", "no")
        self.assertEqual(m.state, "accepted")
        self.assertIn("无任何状态声明", m.trace[-1]["diagnostic"])

    def test_reenter_keeps_session_state_and_rearms(self):
        m = QuestMachine(_defn(STAR_ONCE_TRUE))
        m.trigger("requester", "yes")
        self.assertEqual(m.state, "accepted")
        # once=true 星星：触发后自毁
        m.trigger("star", "yes")
        self.assertEqual(m.state, "carrying")
        self.assertIn("实例自毁", m.trace[-1].get("note", ""))
        m.trigger("star", "yes")
        self.assertEqual(m.state, "carrying")
        self.assertIn("实例已自毁", m.trace[-1]["diagnostic"])
        # 重进房间：实例重臂（once 重新可用），会话态保持
        m.reenter("pickup")
        self.assertEqual(m.state, "carrying")
        self.assertTrue(m.alive["star"])
        # 已在 carrying：重取星 = 守卫拒绝（重复输入路径）
        m.trigger("star", "yes")
        self.assertEqual(m.state, "carrying")
        self.assertIn("守卫", m.trace[-1]["diagnostic"])

    def test_repeat_attempt_guarded(self):
        m = QuestMachine(_defn())
        m.trigger("requester", "yes")
        m.trigger("requester", "yes")
        self.assertEqual(m.state, "accepted")
        self.assertIn("守卫", m.trace[-1]["diagnostic"])
        m.trigger("receiver")
        self.assertEqual(m.state, "accepted")  # 未携带递交：守卫拒绝，原地不动
        m.trigger("star", "yes")
        m.trigger("receiver")
        m.trigger("receiver")
        self.assertEqual(m.state, "delivered")
        self.assertIn("守卫", m.trace[-1]["diagnostic"])

    def test_routed_same_trigger_by_current_state(self):
        text = MAIN_V2.replace(
            "  carrying:\n    enter:\n      npc: star\n      answer: yes\n"
            "    require: accepted\n",
            "  carrying:\n    enter:\n      npc: star\n      answer: yes\n"
            "    require: accepted\n"
            "  carrying_alt:\n    enter:\n      npc: star\n      answer: yes\n"
            "    require: rejected\n")
        m = QuestMachine(_defn(text))
        m.trigger("requester", "yes")
        m.trigger("star", "yes")
        self.assertEqual(m.state, "carrying")
        m2 = QuestMachine(_defn(text))
        m2.trigger("requester", "no")
        m2.trigger("star", "yes")
        self.assertEqual(m2.state, "carrying_alt")

    def test_session_save_load_resets(self):
        m = QuestMachine(_defn())
        m.trigger("requester", "yes")
        rec = m.save()
        self.assertIsNone(rec["projected_code"])
        self.assertIn("无存档投影", rec["diagnostic"])
        rec = m.load()
        self.assertEqual(m.state, "not_started")
        self.assertIn("随读档丢失", rec["diagnostic"])

    def test_flag_save_load_roundtrip(self):
        m = QuestMachine(_defn(FLAG_V2))
        m.trigger("requester", "yes")
        m.trigger("star", "yes")
        rec = m.save()
        self.assertEqual(rec["projected_code"], 3)
        rec = m.load(3)
        self.assertEqual(m.state, "carrying")
        self.assertIsNone(rec.get("diagnostic"))
        # 未知旗标值（占用漂移/外部写入）→ fail-safe 回 initial + 诊断
        rec = m.load(999)
        self.assertEqual(m.state, "not_started")
        self.assertIn("fail-safe", rec["diagnostic"])
        # save→load 无参：读上次投影
        m.trigger("requester", "no")
        self.assertEqual(m.state, "rejected")
        m.save()
        m.load()
        self.assertEqual(m.state, "rejected")

    def test_load_without_save_rejected(self):
        m = QuestMachine(_defn(FLAG_V2))
        with self.assertRaises(StorylineError):
            m.load()

    def test_machine_requires_states_block(self):
        with self.assertRaises(StorylineError):
            QuestMachine(_defn(MAIN_V2.rsplit("states:", 1)[0]))

    def test_trigger_callform_failclosed(self):
        m = QuestMachine(_defn())
        with self.assertRaises(StorylineError):
            m.trigger("ghost")
        with self.assertRaises(StorylineError):
            m.trigger("requester")            # 选择 npc 缺 answer
        with self.assertRaises(StorylineError):
            m.trigger("receiver", "yes")      # 纯对话 npc 带 answer

    def test_render_trace_readable(self):
        m = QuestMachine(_defn())
        m.trigger("requester", "yes")
        m.trigger("star", "no")
        text = m.render_trace()
        self.assertIn("#01 trigger npc=requester answer=yes: "
                      "not_started → accepted", text)
        self.assertIn("⚠", text)  # 诊断行


class TestStatesPlanIntegration(unittest.TestCase):
    """states 进 v2 计划（mock 探针）+ 语义指纹重排稳定/内容变更。"""

    PROBES = {"room_ruins1": 6, "room_ruins2": 7, "room_ruins4": 9}

    def _plan(self, text: str) -> dict:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "d.yaml"
            p.write_text(text, encoding="utf-8")
            defn = load_definition(p)
            game_file = Path(td) / "game.ios"
            with \
                mock.patch("deterline.cmds.template_common.idx_room_lookup",
                           side_effect=lambda gf, name:
                               self.PROBES.get(name, -1)), \
                mock.patch("deterline.storyline._room_name_by_idx",
                           side_effect=lambda gf, idx: next(
                               (k for k, v in self.PROBES.items()
                                if v == idx), None)), \
                mock.patch("deterline.storyline._room_match_count",
                           return_value=(1, 0)), \
                mock.patch("deterline.storyline._room_size_by_idx",
                           side_effect=lambda gf, idx: {
                               6: (320, 480), 7: (320, 240),
                               9: (320, 240)}.get(idx)), \
                mock.patch("deterline.cmds.npc._query_npc_target",
                           return_value={"obj": "obj_npc_marker",
                                         "native": False,
                                         "step_code": None,
                                         "alarm_code": None}), \
                mock.patch("deterline.cmds.npc._find_create_code",
                           return_value=None):
                return build_plan_v2(defn, game_file)

    def test_states_in_plan_canonical(self):
        plan = self._plan(MAIN_V2)
        st = plan["states"]
        self.assertEqual(st["persistence"], "session")
        self.assertEqual(st["initial"], "not_started")
        # canonical 按 id 排序（声明序不进语义）
        self.assertEqual([s["id"] for s in st["declared"]],
                         ["accepted", "carrying", "delivered",
                          "not_started", "rejected"])
        self.assertNotIn("flag_encoding", st)

    def test_states_flag_encoding_in_plan(self):
        plan = self._plan(FLAG_V2)
        enc = plan["states"]["flag_encoding"]
        self.assertEqual(enc["flag_id"], 511)
        self.assertEqual(enc["codes"]["delivered"], 4)
        self.assertEqual(enc["scope"], "save（包 17 投影）")

    def test_states_flag_encoding_runtime_scope_session(self):
        # 包 18：session + 局部 code → flag_encoding 标 runtime-carrier
        text = MAIN_V2.replace(
            "patch_id: det_t1", "patch_id: det_t1\nflag_id: 520").replace(
            "    require: carrying", "    require: carrying\n    code: 4")
        plan = self._plan(text)
        enc = plan["states"]["flag_encoding"]
        self.assertEqual(enc["flag_id"], 520)
        self.assertEqual(enc["codes"], {"delivered": 4})
        self.assertIn("runtime-carrier", enc["scope"])

    def test_unreachable_state_diagnosed(self):
        # accepted 的守卫指向 delivered（delivered 又依赖 carrying→accepted
        # 环）→ accepted/carrying/delivered 从 initial 不可达 → 诊断
        text = MAIN_V2.replace(
            "  accepted:\n    enter:\n      npc: requester\n"
            "      answer: yes\n    require: not_started\n",
            "  accepted:\n    enter:\n      npc: requester\n"
            "      answer: yes\n    require: delivered\n")
        plan = self._plan(text)
        joined = "\n".join(plan["diagnostics"])
        self.assertIn("不可达的状态", joined)
        self.assertIn("accepted", joined)

    def test_fingerprint_stable_across_states_reorder(self):
        head, states = MAIN_V2.rsplit("states:", 1)
        lines = [l for l in states.splitlines() if l.strip()]
        # accepted/rejected 块整体对调（内容逐字不变，声明序变化）
        acc = "\n".join(lines[3:8])    # accepted 块
        rej = "\n".join(lines[8:13])   # rejected 块
        self.assertIn("accepted:", acc)
        self.assertIn("rejected:", rej)
        swapped = "states:\n" + "\n".join(lines[:3]) + "\n" + rej + "\n" \
            + acc + "\n" + "\n".join(lines[13:]) + "\n"
        p1 = self._plan(MAIN_V2)
        p2 = self._plan(head + swapped)
        self.assertEqual(p1["semantic_sha256"], p2["semantic_sha256"])

    def test_fingerprint_changes_with_states_content(self):
        p1 = self._plan(MAIN_V2)
        p2 = self._plan(MAIN_V2.replace("require: accepted",
                                        "require: not_started"))
        self.assertNotEqual(p1["semantic_sha256"], p2["semantic_sha256"])


class TestV1Unaffected(unittest.TestCase):
    """v1 合同不受 states 扩展影响（未知字段照旧拒绝）。"""

    def test_v1_rejects_states_field(self):
        v1 = """schema: deterline.storyline/v1
patch_id: det_t1
room: room_ruins1
npc:
  object: obj_npc_marker
  x: 100
  y: 200
  prompt: "* Hi/%%"
flag_id: 512
states:
  initial: s1
"""
        with self.assertRaises(errors_mod.DeterlineError) as cm:
            _read_definition(v1)
        self.assertIn("未知字段", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
