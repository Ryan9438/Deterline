"""Golden CSX snapshot tests (V4).

Every command that generates a CSX script is pinned to a recorded golden file
(tests/golden/<name>.csx).  If a change to CSX generation is INTENTIONAL,
regenerate with:

    GOLDEN_UPDATE=1 python3 -m unittest tests.test_golden_csx -v

and mention the change in the commit message (双轨机制：区分"意外漂移"与"有意演进"，
见 AUDIT_2026-11-07/01-ROADMAP 验收原则).
"""

import os
import shutil
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _o2_patch import dual_patch_utmt  # O2 步 3：双路径 patch（ms 裸名 + 包内模块属性）

import modify_save as ms

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"


def _capture(fn, *args, **kwargs):
    """Patch _run_utmt to record every generated CSX; returns (list_of_csx, fn_result)."""
    captured = []

    def fake_run(csx_code, game_file, save=True):
        captured.append(csx_code)
        return "VERIFY_NSID:bad=0 fixed=0\nVERIFY_INSTANCES:bad=0 zero=0 dup=0 null=0 nonexist=0 fixed=0"

    with dual_patch_utmt(side_effect=fake_run):
        result = fn(*args, **kwargs)
    return captured, result


def _golden_path(name: str) -> Path:
    return GOLDEN_DIR / f"{name}.csx"


def _canonical_tmp(text: str) -> str:
    """平台无关化（CI 修正）：/tmp 在 macOS resolve 成 /private/tmp、Linux
    保持 /tmp、Windows 是 C:\\tmp\\——bg 资产 CSX 内嵌 resolve 后的真实路径，
    golden 只钉占位符。归一化**只作用于占位符后的分隔符**——绝不全局替换
    反斜杠：审核席 A P1-1（GOLDEN_UPDATE 写回曾把 CSX 内 "\\r\\n" 转义序列
    损坏成 "/r/n"，3 枚 fresh-base golden 因此带伤入库）。"""
    real = str(Path("/tmp/golden_test").resolve())
    real_win = real.replace("/", "\\")
    text = (text.replace(real, "<GOLDEN_TMP>")
                .replace(real_win, "<GOLDEN_TMP>")
                .replace("/tmp/golden_test", "<GOLDEN_TMP>"))
    return text.replace("<GOLDEN_TMP>\\", "<GOLDEN_TMP>/")


def _check_golden(testcase, name: str, captured):
    text = "\n=== CALL ===\n".join(captured)
    path = _golden_path(name)
    if os.environ.get("GOLDEN_UPDATE") == "1":
        GOLDEN_DIR.mkdir(exist_ok=True)
        path.write_text(_canonical_tmp(text), encoding="utf-8")
    testcase.assertTrue(
        path.exists(), f"golden 缺失: {path}（跑 GOLDEN_UPDATE=1 生成）")
    expected = path.read_text(encoding="utf-8")
    testcase.assertEqual(_canonical_tmp(expected), _canonical_tmp(text),
                         f"CSX 与 golden 不一致: {name}（有意变更则 GOLDEN_UPDATE=1 重录）")


class TestGoldenStrg(unittest.TestCase):
    def test_strg_set(self):
        cap, _ = _capture(ms.cmd_strg_set, Path("/tmp/golden_test/game.ios"), "11432", "* New text/")
        _check_golden(self, "strg_set", cap)

    def test_strg_add(self):
        cap, _ = _capture(ms.cmd_strg_add, Path("/tmp/golden_test/game.ios"), "* New dialogue/%%")
        _check_golden(self, "strg_add", cap)

    def test_strg_delete(self):
        cap, _ = _capture(ms.cmd_strg_delete, Path("/tmp/golden_test/game.ios"), "64000")
        _check_golden(self, "strg_delete", cap)

    def test_strg_search(self):
        cap, _ = _capture(ms.cmd_strg_search, Path("/tmp/golden_test/game.ios"), "Toriel", 30)
        _check_golden(self, "strg_search", cap)


class TestGoldenTextdata(unittest.TestCase):
    def test_textdata_add_plain(self):
        cap, _ = _capture(ms.cmd_textdata_add, Path("/tmp/golden_test/game.ios"),
                          "obj_golden_001", "* Hello golden/%%")
        _check_golden(self, "textdata_add_plain", cap)

    def test_textdata_add_with_face(self):
        cap, _ = _capture(ms.cmd_textdata_add, Path("/tmp/golden_test/game.ios"),
                          "obj_golden_002", "* Hi/%%", face=3, emotion=1)
        _check_golden(self, "textdata_add_face", cap)

    def test_textdata_update(self):
        cap, _ = _capture(ms.cmd_textdata_update, Path("/tmp/golden_test/game.ios"),
                          "obj_golden_001", "* Updated text/%%")
        _check_golden(self, "textdata_update", cap)

    def test_textdata_delete(self):
        cap, _ = _capture(ms.cmd_textdata_delete, Path("/tmp/golden_test/game.ios"),
                          "obj_golden_001")
        _check_golden(self, "textdata_delete", cap)

    def test_textdata_search(self):
        cap, _ = _capture(ms.cmd_textdata_search, Path("/tmp/golden_test/game.ios"),
                          "sans", 30)
        _check_golden(self, "textdata_search", cap)


class TestGoldenCode(unittest.TestCase):
    def test_code_replace(self):
        cap, _ = _capture(ms.cmd_code_replace, Path("/tmp/golden_test/game.ios"),
                          "gml_Script_scr_golden", "return 20;")
        _check_golden(self, "code_replace", cap)

    def test_code_append(self):
        cap, _ = _capture(ms.cmd_code_append, Path("/tmp/golden_test/game.ios"),
                          "gml_Object_obj_golden_Step_0", "// appended")
        _check_golden(self, "code_append", cap)

    def test_code_prepend(self):
        cap, _ = _capture(ms.cmd_code_prepend, Path("/tmp/golden_test/game.ios"),
                          "gml_Object_obj_golden_Step_0", "// prepended")
        _check_golden(self, "code_prepend", cap)

    def test_create_script(self):
        cap, _ = _capture(ms.cmd_create_script, Path("/tmp/golden_test/game.ios"),
                          "gml_Script_goldenFunc", "return 0;")
        _check_golden(self, "create_script", cap)

    def test_search_vars(self):
        cap, _ = _capture(ms.cmd_search_vars, Path("/tmp/golden_test/game.ios"),
                          "global.flag", 30)
        _check_golden(self, "search_vars", cap)


class TestGoldenRoom(unittest.TestCase):
    def test_gml_bg(self):
        cap, _ = _capture(ms.cmd_gml_bg, Path("/tmp/golden_test/game.ios"),
                          "room_golden", "bg_golden", slot=0, speedx=0.5)
        _check_golden(self, "gml_bg", cap)

    def test_set_room_bg(self):
        cap, _ = _capture(ms.cmd_set_room_bg, Path("/tmp/golden_test/game.ios"),
                          "room_golden", index=0, enable=True, bg_name="bg_golden")
        _check_golden(self, "set_room_bg", cap)

    def test_set_room_prop_size_only(self):
        """v2.3.0: --width/--height 不得触碰 Views[0]（形态不变量）。"""
        cap, _ = _capture(ms.cmd_set_room_prop, Path("/tmp/golden_test/game.ios"),
                          "room_golden", width=800, height=480)
        _check_golden(self, "set_room_prop_size", cap)
        for csx in cap:
            self.assertNotIn("Views[0]", csx,
                             "set-room-prop 尺寸变更不得触碰 Views[0]（回归 v2.3.0 前的副作用）")

    def test_set_room_prop_caption(self):
        cap, _ = _capture(ms.cmd_set_room_prop, Path("/tmp/golden_test/game.ios"),
                          "room_golden", caption="Golden Room")
        _check_golden(self, "set_room_prop_caption", cap)

    def test_set_room_view(self):
        cap, _ = _capture(ms.cmd_set_room_view, Path("/tmp/golden_test/game.ios"),
                          "room_golden", index=0, enable=True,
                          view_w=320, view_h=240, port_w=640, port_h=480,
                          follow="obj_mainchara")
        _check_golden(self, "set_room_view", cap)

    def test_remove_tile_all(self):
        cap, _ = _capture(ms.cmd_remove_tile, Path("/tmp/golden_test/game.ios"),
                          "room_golden", None)
        _check_golden(self, "remove_tile_all", cap)

    def test_verify_nsid(self):
        cap, _ = _capture(ms.cmd_verify_nsid, Path("/tmp/golden_test/game.ios"), fix=False)
        _check_golden(self, "verify_nsid", cap)

    def test_verify_instances(self):
        cap, _ = _capture(ms.cmd_verify_instances, Path("/tmp/golden_test/game.ios"), fix=False)
        _check_golden(self, "verify_instances", cap)


class TestGoldenGenerators(unittest.TestCase):
    """生成器函数的精确输出快照（npc 触发块是死代码事故区，钉死形态）。"""

    def test_npc_step_block_repeat(self):
        block = ms._build_npc_step_block(113928, "obj_k", 3, 1, True, once=False, range_=50)
        _check_golden(self, "gen_npc_step_repeat", [block])

    def test_npc_step_block_once(self):
        block = ms._build_npc_step_block(113928, "obj_k", 3, 1, True, once=True, range_=50)
        _check_golden(self, "gen_npc_step_once", [block])

    def test_npc_choice_block(self):
        block = ms._build_npc_choice_block(
            113930, "obj_ask", "obj_yes", "obj_no", 3, 1, range_=160,
            goto_room="70", item_id=48, repeat=False)
        _check_golden(self, "gen_npc_choice", [block])

    def test_npc_choice_block_repeat(self):
        block = ms._build_npc_choice_block(
            113930, "obj_ask", "obj_yes", "obj_no", 3, 1, repeat=True)
        _check_golden(self, "gen_npc_choice_repeat", [block])


class TestGoldenCjkFont(unittest.TestCase):
    """C3b：cjk-font 两段 CSX 模板钉形（work_dir 用固定假路径保证字节稳定）。"""

    def test_cjk_pass1_csx(self):
        _check_golden(self, "cjk_pass1",
                      [ms._build_cjk_pass1_csx("/tmp/golden_cjk_work")])

    def test_cjk_pass2_csx(self):
        _check_golden(self, "cjk_pass2",
                      [ms._build_cjk_pass2_csx("/tmp/golden_cjk_work")])

    def test_cjk_trigger_csx(self):
        """S6：触发块生成器钉形（B4 实证全形态；含预折行）。"""
        _check_golden(self, "cjk_trigger",
                      [ms._build_cjk_trigger_csx(
                          "room_ruins1", "obj_cactus", 220, 330, 31,
                          "* 托丽尔你好，这里是中文测试。第二行内容稍微长一些需要折行。")])

    def test_cjk_trigger_two_page_csx(self):
        """阶段 1.5：两页形态钉形（中部 "/%%" 页分隔输入 → msg[0] 裸 "/" 翻页
        （2026-11-14 实机订正）、msg[1] "/%%" 关框、msg[2]="%%%" 收口）。"""
        _check_golden(self, "cjk_trigger_twopage",
                      [ms._build_cjk_trigger_csx(
                          "room_ruins1", "obj_cactus", 220, 330, 31,
                          "* 托丽尔你好，这是中文样例第一页。&CJK 12px + ASCII 123 mixed。"
                          "/%%* 第二页：翻页、头像与退出对话测试。")])


# ============================================================
# D0 清偿日补齐（风险审计派 A3 + 全量实测盘点）：
# 以下写命令此前完全无 golden 快照，搬运/改动 CSX 生成时无文本钉。
# 盘点口径：函数体内直接调 _run_utmt(save=True) 的 cmd_ 入口 + 经委托
# 产生 CSX 但委托接线未钉的写命令（code-find-replace / batch-textdata /
# guided-add-dialogue / set-derived）。create-room 已废弃（调用即报错），
# 只读命令（list/search/decompile/room-info 等）不在补齐范围。
# ============================================================

DEFAULT_UTMT_OUT = (
    "VERIFY_NSID:bad=0 fixed=0\n"
    "VERIFY_INSTANCES:bad=0 zero=0 dup=0 null=0 nonexist=0 fixed=0"
)


def _fake_gml_output(lines):
    """把一组 GML 行包装成 _decompile_to_lines 能解析的 UTMT 输出。"""
    out = [f"GML_LINE:{i}:{ln}" for i, ln in enumerate(lines)]
    out.append(f"GML_COUNT:{len(lines)}")
    return "\n".join(out)


def _capture_stateful(fn, *args, replies=None, **kwargs):
    """_capture 变体：fake_run 按 CSX 内嵌探针应答只读请求（IDX 查询 /
    GML 反编译 / NPC_TARGET 查询 / 房间尺寸 / 资源存在性 / 启用层），
    使复合写命令能走完完整流程；每次 _run_utmt 调用（含只读）都记入
    captured —— 与既有 golden 语义一致（钉住全部生成 CSX）。"""
    captured = []
    table = list((replies or {}).items())

    def fake_run(csx_code, game_file, save=True):
        captured.append(csx_code)
        for probe, response in table:
            if probe in csx_code:
                return response
        return DEFAULT_UTMT_OUT

    with dual_patch_utmt(side_effect=fake_run):
        result = fn(*args, **kwargs)
    return captured, result


def _ensure_golden_png(name: str) -> Path:
    """在固定路径 /tmp/golden_test/ 下准备一张小 PNG（内容不影响 golden，
    golden 只钉路径字符串；固定路径保证 expanduser().resolve() 后字节稳定）。"""
    d = Path("/tmp/golden_test")
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    if not p.exists():
        from PIL import Image
        Image.new("RGBA", (4, 4), (255, 0, 0, 255)).save(p)
    return p


# 反编译桩：door 三胞胎共用形态（分支坐标与 golden 测试写入的不同，
# 避免触发"已有门"分支）。PIT/BATTLE 同构，各用自身形态。
DOOR_GML_STUB = [
    '/// obj_deterline_door — Create event',
    'var _rn = room_get_name(room);',
    'if (_rn == "room_seed" && x == 100 && y == 100) {',
    '    target_room = 70;',
    '    spawn_x = 10;',
    '    spawn_y = 20;',
    '    exit;',
    '}',
    'target_room = -1;',
    'spawn_x = 0;',
    'spawn_y = 0;',
]
PIT_GML_STUB = [
    '/// obj_deterline_pit — Create event',
    'var _rn = room_get_name(room);',
    'if (_rn == "room_seed" && x == 100 && y == 100) {',
    '    target_room = 70;',
    '    spawn_x = 10;',
    '    spawn_y = 20;',
    '    exit;',
    '}',
    'target_room = -1;',
    'spawn_x = 0;',
    'spawn_y = 0;',
]
# remove-door 专用：必须包含与测试参数匹配的 room_golden 分支，否则
# removed_count=0 会在生成写 CSX 之前提前返回（两个房间分支 → --all 移除 2 处）。
REMOVE_DOOR_GML_STUB = [
    '/// obj_deterline_door — Create event',
    'var _rn = room_get_name(room);',
    'if (_rn == "room_golden" && x == 320 && y == 240) {',
    '    target_room = 70;',
    '    spawn_x = 100;',
    '    spawn_y = 200;',
    '    exit;',
    '}',
    'if (_rn == "room_golden" && x == 500 && y == 100) {',
    '    target_room = 71;',
    '    spawn_x = 100;',
    '    spawn_y = 200;',
    '    exit;',
    '}',
    'target_room = -1;',
    'spawn_x = 0;',
    'spawn_y = 0;',
]
BATTLE_GML_STUB = [
    '/// obj_deterline_battle — Create event',
    'var _rn = room_get_name(room);',
    'if (_rn == "room_seed" && x == 100 && y == 100) {',
    '    battlegroup_id = 3;',
    '    border = 1;',
    '    exit;',
    '}',
    'battlegroup_id = -1;',
    'border = 0;',
]
STEP_GML_STUB = [
    'if (visible) {',
    '    myinteract = 1;',
    '}',
]
HANDLER_GML_STUB = [
    'if (global.choice != -1) {',
    '    msg[0] = "resumed";',
    '}',
    'exit;',
]
FINDREPLACE_GML_STUB = [
    'if (global.maxhp == 16 + (global.lv * 4)) {',
    '    global.maxhp = 16 + (global.lv * 4);',
    '}',
]
DERIVED_GML_STUB = [
    'global.maxhp = 16 + (global.lv * 4);',
    'if (global.lv > 18) {',
    '    global.maxhp = 16 + (global.lv * 4);',
    '}',
]


class TestGoldenStrgReplace(unittest.TestCase):
    def test_strg_replace(self):
        cap, _ = _capture(ms.cmd_strg_replace, Path("/tmp/golden_test/game.ios"),
                          "* Old line/%%", "* New line/%%")
        _check_golden(self, "strg_replace", cap)


class TestGoldenRoomObj(unittest.TestCase):
    """remove_obj 三分支（按实例 / 按名首个 / --all）与 spawn_obj。"""

    def test_remove_obj_by_name(self):
        cap, _ = _capture(ms.cmd_remove_obj, Path("/tmp/golden_test/game.ios"),
                          "room_golden", "obj_golden_npc")
        _check_golden(self, "remove_obj_by_name", cap)

    def test_remove_obj_all(self):
        cap, _ = _capture(ms.cmd_remove_obj, Path("/tmp/golden_test/game.ios"),
                          "room_golden", "obj_golden_npc", remove_all=True)
        _check_golden(self, "remove_obj_all", cap)

    def test_remove_obj_instance(self):
        cap, _ = _capture(ms.cmd_remove_obj, Path("/tmp/golden_test/game.ios"),
                          "room_golden", "obj_golden_npc", instance_id=113928)
        _check_golden(self, "remove_obj_instance", cap)

    def test_spawn_obj(self):
        cap, _ = _capture(ms.cmd_spawn_obj, Path("/tmp/golden_test/game.ios"),
                          "room_golden", "obj_golden_npc", 320, 240)
        _check_golden(self, "spawn_obj", cap)


class TestGoldenNpcGuard(unittest.TestCase):
    """guard-npc-alarm：NPC_TARGET 只读查询 + Alarm_0 守卫 +（可选）Step 状态机改写。"""

    NPC_REPLY = ("NPC_TARGET:RESULT:obj_golden_npc:1:"
                 "gml_Object_obj_golden_npc_Step_0:"
                 "gml_Object_obj_golden_npc_Alarm_0")

    def test_guard_npc_alarm_only(self):
        cap, _ = _capture_stateful(
            ms.cmd_guard_npc_alarm, Path("/tmp/golden_test/game.ios"),
            "obj_golden_npc", 113928,
            replies={"NPC_TARGET:RESULT": self.NPC_REPLY})
        _check_golden(self, "guard_npc_alarm", cap)

    def test_guard_npc_alarm_step_machine(self):
        cap, _ = _capture_stateful(
            ms.cmd_guard_npc_alarm, Path("/tmp/golden_test/game.ios"),
            "obj_golden_npc", 113928, text_key="obj_golden_003",
            replies={"NPC_TARGET:RESULT": self.NPC_REPLY,
                     'ScriptMessage("GML_LINE:': _fake_gml_output(STEP_GML_STUB)})
        _check_golden(self, "guard_npc_alarm_step", cap)


class TestGoldenBgAsset(unittest.TestCase):
    """create-bg-asset 与 set-room-solid-bg 组合（create + 层分配 + 运行时覆盖）。"""

    def test_create_bg_asset(self):
        png = _ensure_golden_png("bg_golden.png")
        cap, _ = _capture(ms.cmd_create_bg_asset, Path("/tmp/golden_test/game.ios"),
                          "bg_golden", str(png))
        _check_golden(self, "create_bg_asset", cap)

    def test_set_room_solid_bg(self):
        """固定 mkstemp 路径保证 CSX 内嵌 PNG 路径字节稳定。"""
        fixed_png = _ensure_golden_png("det_solid_fixed.png")
        fd = os.open(fixed_png, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        # 注意: cmd_set_room_solid_bg 内部会 os.close(fd)——这里不再重复关闭。
        with mock.patch("tempfile.mkstemp", return_value=(fd, str(fixed_png))):
            cap, _ = _capture_stateful(
                ms.cmd_set_room_solid_bg, Path("/tmp/golden_test/game.ios"),
                "room_golden", "0000FF",
                replies={
                    'ScriptMessage("SIZE:': "SIZE:640:480",
                    'ScriptMessage("EXISTS:': "EXISTS:false",
                    'ScriptMessage("ENABLED:': "",
                })
        _check_golden(self, "set_room_solid_bg", cap)


class TestGoldenDoorPitBattle(unittest.TestCase):
    """door/pit/battle 三胞胎 + remove-door 两分支（按坐标 / --all）。"""

    def test_create_door(self):
        cap, _ = _capture_stateful(
            ms.cmd_create_door, Path("/tmp/golden_test/game.ios"),
            "room_golden", "room_golden_b", 320, 240, 100, 200,
            replies={'ScriptMessage("IDX:': "IDX:70",
                     'ScriptMessage("GML_LINE:': _fake_gml_output(DOOR_GML_STUB)})
        _check_golden(self, "create_door", cap)

    def test_create_pit(self):
        cap, _ = _capture_stateful(
            ms.cmd_create_pit, Path("/tmp/golden_test/game.ios"),
            "room_golden", "room_golden_b", 320, 240, 100, 200,
            replies={'ScriptMessage("IDX:': "IDX:70",
                     'ScriptMessage("GML_LINE:': _fake_gml_output(PIT_GML_STUB)})
        _check_golden(self, "create_pit", cap)

    def test_create_battle(self):
        cap, _ = _capture_stateful(
            ms.cmd_create_battle, Path("/tmp/golden_test/game.ios"),
            "room_golden", battlegroup_id=3, border=1, x=320, y=240,
            replies={'ScriptMessage("GML_LINE:': _fake_gml_output(BATTLE_GML_STUB)})
        _check_golden(self, "create_battle", cap)

    def test_remove_door_coords(self):
        cap, _ = _capture_stateful(
            ms.cmd_remove_door, Path("/tmp/golden_test/game.ios"),
            "room_golden", 320, 240,
            replies={'ScriptMessage("GML_LINE:': _fake_gml_output(REMOVE_DOOR_GML_STUB)})
        _check_golden(self, "remove_door_coords", cap)

    def test_create_door_fresh_base(self):
        """O3b 前置钉（风险席 2026-11-13）：无既有 Create_0 → 从 BASE 起步
        路径此前零 golden——空反编译应答走 fresh-base 分支，BASE 常量直录。"""
        cap, _ = _capture_stateful(
            ms.cmd_create_door, Path("/tmp/golden_test/game.ios"),
            "room_golden", "room_golden_b", 320, 240, 100, 200,
            replies={'ScriptMessage("IDX:': "IDX:70",
                     'ScriptMessage("GML_LINE:': ""})
        _check_golden(self, "create_door_fresh_base", cap)

    def test_create_pit_fresh_base(self):
        cap, _ = _capture_stateful(
            ms.cmd_create_pit, Path("/tmp/golden_test/game.ios"),
            "room_golden", "room_golden_b", 320, 240, 100, 200,
            replies={'ScriptMessage("IDX:': "IDX:70",
                     'ScriptMessage("GML_LINE:': ""})
        _check_golden(self, "create_pit_fresh_base", cap)

    def test_create_battle_fresh_base(self):
        cap, _ = _capture_stateful(
            ms.cmd_create_battle, Path("/tmp/golden_test/game.ios"),
            "room_golden", battlegroup_id=3, border=1, x=320, y=240,
            replies={'ScriptMessage("GML_LINE:': ""})
        _check_golden(self, "create_battle_fresh_base", cap)

    def test_remove_door_all(self):
        cap, _ = _capture_stateful(
            ms.cmd_remove_door, Path("/tmp/golden_test/game.ios"),
            "room_golden", None, None, remove_all=True,
            replies={'ScriptMessage("GML_LINE:': _fake_gml_output(REMOVE_DOOR_GML_STUB)})
        _check_golden(self, "remove_door_all", cap)


class TestGoldenSpriteEdit(unittest.TestCase):
    """obj-set-sprite / sprite-replace（单帧 / --all-frames）/ sprite-duplicate。"""

    def test_obj_set_sprite(self):
        cap, _ = _capture(ms.cmd_obj_set_sprite, Path("/tmp/golden_test/game.ios"),
                          "obj_golden_npc", "spr_golden")
        _check_golden(self, "obj_set_sprite", cap)

    def test_sprite_replace_frame(self):
        cap, _ = _capture(ms.cmd_sprite_replace, Path("/tmp/golden_test/game.ios"),
                          "spr_golden", "/tmp/golden_test/spr_golden.png", frame=0)
        _check_golden(self, "sprite_replace_frame", cap)

    def test_sprite_replace_all_frames(self):
        cap, _ = _capture(ms.cmd_sprite_replace, Path("/tmp/golden_test/game.ios"),
                          "spr_golden", "/tmp/golden_test/spr_golden.png",
                          all_frames=True)
        _check_golden(self, "sprite_replace_all", cap)

    def test_sprite_duplicate(self):
        cap, _ = _capture(ms.cmd_sprite_duplicate, Path("/tmp/golden_test/game.ios"),
                          "spr_golden", "spr_golden_copy")
        _check_golden(self, "sprite_duplicate", cap)


class TestGoldenHandlerExtract(unittest.TestCase):
    """handler-extract --apply：反编译读 + 提取写（--apply 才有写 CSX）。"""

    def test_handler_extract_apply(self):
        cap, _ = _capture_stateful(
            ms.cmd_handler_extract, Path("/tmp/golden_test/game.ios"), True,
            replies={'ScriptMessage("GML_LINE:': _fake_gml_output(HANDLER_GML_STUB)})
        _check_golden(self, "handler_extract_apply", cap)


class TestGoldenDelegatingWrites(unittest.TestCase):
    """委托型写命令：CSX 文本与被委托命令同形，但委托接线（参数映射）未钉。

    - code-find-replace → replace-code（file 模式）：钉 old→new 的 Python 侧替换
    - batch-textdata → N × add-textentry：钉 JSON→CSX 批量展开
    - guided-add-dialogue → add-textentry：钉四步校验后的委托
    - set-derived → file0-set + 两个目标脚本的 stat 赋值改写
    """

    def test_code_find_replace(self):
        cap, _ = _capture_stateful(
            ms.cmd_code_find_replace, Path("/tmp/golden_test/game.ios"),
            "gml_Script_golden", "16 + (global.lv * 4)", "50",
            replies={'ScriptMessage("GML_LINE:': _fake_gml_output(FINDREPLACE_GML_STUB)})
        _check_golden(self, "code_find_replace", cap)

    def test_batch_textdata(self):
        import json as _json
        import tempfile
        d = tempfile.mkdtemp(prefix="golden_batch_")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        jp = Path(d) / "batch.json"
        jp.write_text(_json.dumps([
            {"key": "obj_golden_b1", "text": "* Batch one/%%"},
            {"key": "obj_golden_b2", "text": "* Batch two/%%", "face": 3, "emotion": 1},
        ], ensure_ascii=False), encoding="utf-8")
        cap, _ = _capture(ms.cmd_batch_textdata, Path("/tmp/golden_test/game.ios"),
                          str(jp))
        _check_golden(self, "batch_textdata", cap)

    def test_guided_add_dialogue(self):
        cap, _ = _capture(ms.cmd_guided_add_dialogue, Path("/tmp/golden_test/game.ios"),
                          "obj_golden_003", "* Guided hello/%%", face=3, emotion=1)
        _check_golden(self, "guided_add_dialogue", cap)

    def test_set_derived(self):
        import tempfile
        d = tempfile.mkdtemp(prefix="golden_derived_")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        f0 = Path(d) / "file0"
        f0.write_text("Golden\r\n" + "".join(f"{i} \r\n" for i in range(1, 31)),
                      encoding="ascii")
        cap, _ = _capture_stateful(
            ms.cmd_set_derived, Path(d), Path("/tmp/golden_test/game.ios"),
            "HP", "50",
            replies={'ScriptMessage("GML_LINE:': _fake_gml_output(DERIVED_GML_STUB)})
        _check_golden(self, "set_derived", cap)

class TestCanonicalTmp(unittest.TestCase):
    """P1-1 回归钉：归一化只动占位符路径，绝不碰转义序列。"""

    def test_preserves_escape_sequences(self):
        t = r'var lines = gml.Split(new[] { "\r\n", "\r", "\n" });'
        self.assertEqual(_canonical_tmp(t), t)

    def test_windows_path_normalized_to_placeholder(self):
        # Windows 形态从当前平台 resolve 派生（反斜杠变体），钉住 real_win 分支
        real = str(Path('/tmp/golden_test').resolve())
        real_win = real.replace('/', chr(92))
        t = f'var p = "{real_win}{chr(92)}bg.png";'
        self.assertEqual(_canonical_tmp(t), 'var p = "<GOLDEN_TMP>/bg.png";')
    def test_posix_resolved_path_normalized(self):
        real = str(Path("/tmp/golden_test").resolve())
        t = f'var p = "{real}/bg.png";'
        self.assertEqual(_canonical_tmp(t), 'var p = "<GOLDEN_TMP>/bg.png";')


if __name__ == "__main__":
    unittest.main()
