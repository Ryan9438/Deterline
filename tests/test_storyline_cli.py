"""storyline 三命令命令 CLI 层测试（F3，rc2 前瞻清偿）。

CLI 层断言采用**进程内 cli.main()**（recovery_stress 先例：本机安全扫描
对测试文件 subprocess+sys.executable 形态误报高危并拦截写入——子进程
形态改为进程内 main() 断言，门禁/接线/退出码语义全部复验；OS 进程边界
由 rc2 手工真 CLI 验收链、C1 脚本与 13 实录留痕覆盖）。两层：
- 常开层：无 UTMT 依赖（门禁/拒绝/退出码路径都不触 UTMT）
- 集成层：DETERLINE_RUN_UTMT_INTEGRATION=1 + 本机 UTMT → 真 CLI 全链
  （build → apply 预览 → commit → 幂等 → undo），/tmp 副本 + 显式 --dir，
  零真实数据写入（03 §10 纪律）。
"""

import argparse
import contextlib
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tests"))
sys.path.insert(0, str(REPO / "scripts"))

import modify_save as ms  # noqa: E402,F401  （初始化 deterline 包路径）
from deterline import cli as cli_mod  # noqa: E402
from deterline import state  # noqa: E402
from fixtures_utmt import tmp_game_copy, utmt_available  # noqa: E402

GOOD_DEFN = """schema: deterline.storyline/v1
patch_id: det_cli_test
room: room_ruins1
npc:
  object: obj_npc_marker
  x: 100
  y: 200
  range: 60
  prompt: "* Head east?& &       Yes         No     \\C "
  yes_text: "* You head east./%%"
  no_text: "* Maybe later./%%"
  once: true
flag_id: 505
"""


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _run_cli(*argv: str):
    """进程内 CLI：patch sys.argv → cli.main() → SystemExit 捕获退出码。

    入参为**去前缀形态**（与 run.py 转发一致：此处自动补 --action 旗标）。
    返回 (code, stdout, stderr)。main() 内 parser.error / handler sys.exit
    都以 SystemExit 呈现（argparse 错误码 2、拒绝码 1、成功不抛）。"""
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with mock.patch.object(sys, "argv", ["modify_save.py", "--action", *argv]), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            cli_mod.main()
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
    return code, out.getvalue(), err.getvalue()


_STATE_FLAGS = ("PREVIEW", "WORKSPACE", "SANDBOX_ACTIVE", "SANDBOX_ORIGINAL",
                "COMMIT_ACTIVE", "NO_STEAM_SYNC", "ALLOW_CJK", "AUTO_SNAPSHOT")


def _state_snapshot():
    return {k: getattr(state, k) for k in _STATE_FLAGS}


def _state_restore(snap: dict):
    for k, v in snap.items():
        setattr(state, k, v)


class TestStorylineCliRefusals(unittest.TestCase):
    """常开层：门禁/拒绝/退出码（无 UTMT 依赖——拒绝路径全部发生在任何
    UTMT 往返之前）。"""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="deterline_cli_"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.game = self.root / "game.ios"
        self.game.write_bytes(b"BASE-GAME-CONTENT")
        self.defn = self.root / "storyline.yaml"
        self.defn.write_text(GOOD_DEFN, encoding="utf-8")
        self._snap = _state_snapshot()
        self.addCleanup(_state_restore, self._snap)

    def test_plan_missing_defn_rc1(self):
        """R13 P1-1 退出码保真：拒绝 = rc 1（曾恒 exit 0）。"""
        code, _out, err = _run_cli(
            "storyline-plan", "--file", "data_win",
            "--value", str(self.root / "missing.yaml"),
            "--dir", str(self.game))
        self.assertEqual(code, 1)
        self.assertIn("storyline-plan 拒绝", err)

    def test_plan_json_error_shape(self):
        code, out, _err = _run_cli(
            "storyline-plan", "--file", "data_win",
            "--value", str(self.root / "missing.yaml"),
            "--dir", str(self.game), "--json")
        self.assertEqual(code, 1)
        payload = json.loads(out)
        self.assertEqual(payload["schema"], "deterline.storyline-plan/v1")
        self.assertIn("error", payload)

    def test_build_preview_refused_rc1(self):
        code, _out, err = _run_cli(
            "storyline-build", "--value", str(self.defn),
            "--workspace", "cli_ws", "--dir", str(self.game), "--preview")
        self.assertEqual(code, 1)
        self.assertIn("不支持 --preview", err)

    def test_build_requires_workspace_rc2(self):
        code, _out, err = _run_cli(
            "storyline-build", "--value", str(self.defn),
            "--dir", str(self.game))
        self.assertEqual(code, 2)
        self.assertIn("--workspace", err)

    def test_apply_requires_workspace_rc2(self):
        code, _out, err = _run_cli(
            "storyline-apply", "--value", str(self.defn),
            "--dir", str(self.game), "--commit")
        self.assertEqual(code, 2)
        self.assertIn("--workspace", err)

    def test_apply_sandbox_commit_exclusive_rc2(self):
        """cli 门对 storyline 的 --sandbox 腿仍互斥（R13 P0-1 只豁免
        --workspace 有名腿）。"""
        code, _out, err = _run_cli(
            "storyline-apply", "--value", str(self.defn),
            "--sandbox", "--commit", "--dir", str(self.game))
        self.assertEqual(code, 2)
        self.assertIn("互斥", err)

    def test_apply_preview_commit_exclusive_rc2(self):
        """preview×commit 互斥（R5 P2-3 同款，本批新增）——此前该组合会
        无视 --preview 真写目标。"""
        code, _out, err = _run_cli(
            "storyline-apply", "--value", str(self.defn),
            "--workspace", "cli_ws", "--commit", "--preview",
            "--dir", str(self.game))
        self.assertEqual(code, 2)
        self.assertIn("互斥", err)

    def test_apply_commit_reaches_handler_refuses_no_receipt_rc1(self):
        """P0-1 回归钉（CLI 层）：--workspace×--commit 豁免门生效 → 到达
        handler → 无构建回执拒绝 rc 1（曾因互斥门 CLI 不可达）。"""
        code, _out, err = _run_cli(
            "storyline-apply", "--value", str(self.defn),
            "--workspace", "cli_ws", "--commit", "--dir", str(self.game))
        self.assertEqual(code, 1)
        self.assertIn("无构建回执", err)


@unittest.skipUnless(
    os.environ.get("DETERLINE_RUN_UTMT_INTEGRATION") == "1"
    and utmt_available(),
    "集成层需 UTMT CLI + dotnet + 基线文件，且 DETERLINE_RUN_UTMT_INTEGRATION=1")
class TestStorylineCliFullChain(unittest.TestCase):
    """集成层：真 CLI 全链（12 §C4 验收的自动化回归版——rc2 手工验证
    序列固化）。/tmp 副本 + 显式 --dir，零真实数据写入。"""

    @classmethod
    def setUpClass(cls):
        cls.game = tmp_game_copy(cls)
        cls.defn = Path(cls.game.parent) / "storyline.yaml"
        cls.defn.write_text(GOOD_DEFN, encoding="utf-8")
        cls.baseline_sha = _sha256_file(cls.game)
        cls._snap = _state_snapshot()

    @classmethod
    def tearDownClass(cls):
        _state_restore(cls._snap)

    def _sha(self) -> str:
        return _sha256_file(self.game)

    def _product(self) -> Path:
        p = (self.game.parent / ".deterline" / "game.ios" / "cli_e2e"
             / "game.ios")
        self.assertTrue(p.is_file(), f"工作区产物缺失: {p}")
        return p

    def test_full_chain(self):
        # build（真 CLI 层：cli.main → handler → 域生成器 → 闸门 → 回执）
        code, out, err = _run_cli(
            "storyline-build", "--value", str(self.defn),
            "--workspace", "cli_e2e", "--dir", str(self.game))
        self.assertEqual(code, 0, msg=out[-3000:] + err[-2000:])
        built_sha = _sha256_file(self._product())
        # apply 预览（零动作）
        code, _out, err = _run_cli(
            "storyline-apply", "--value", str(self.defn),
            "--workspace", "cli_e2e", "--dir", str(self.game))
        self.assertEqual(code, 0, msg=err[-2000:])
        self.assertEqual(self._sha(), self.baseline_sha)
        # commit（整包应用）
        code, out, err = _run_cli(
            "storyline-apply", "--value", str(self.defn),
            "--workspace", "cli_e2e", "--dir", str(self.game), "--commit")
        self.assertEqual(code, 0, msg=out[-3000:] + err[-2000:])
        self.assertEqual(self._sha(), built_sha)
        # 幂等：再 commit → 已应用 no-op（R16 P3：用具区分力字样断言——
        # "已应用" 全新 apply 亦含，"幂等 no-op" 为幂等分支独有）
        code, out, err = _run_cli(
            "storyline-apply", "--value", str(self.defn),
            "--workspace", "cli_e2e", "--dir", str(self.game), "--commit")
        self.assertEqual(code, 0, msg=err[-2000:])
        self.assertIn("幂等 no-op", out + err)
        self.assertEqual(self._sha(), built_sha)
        # undo → 回基线
        code, _out, err = _run_cli(
            "undo", "--file", "data_win", "--value", "data_win",
            "--dir", str(self.game))
        self.assertEqual(code, 0, msg=err[-2000:])
        self.assertEqual(self._sha(), self.baseline_sha)


class TestTyperWiring(unittest.TestCase):
    """I1：--typer 全链接线（R21 P2 实机窗口教训）。

    cjk_w3 实机修正链经 npc-choice CLI 构建，handler 静默丢弃 args.typer →
    cmd_npc_choice 回默认 5，r3ok.ios 全文 typer=5（字体栈在而 31 不在）。
    修复：全局 --typer 默认改 None（原默认 31 只归 cjk-trigger），npc-choice
    handler None→5 / 显式值原样转发；cjk-trigger handler None→31。全部无 UTMT
    依赖：parser 默认（COMMANDS 打桩短路 dispatch 与文件解析）+ handler 转发
    （下沉函数 mock）+ 白名单拒绝（校验先于任何文件访问，纯函数路径）。"""

    def test_parser_default_typer_none(self):
        seen = {}
        with mock.patch.dict(cli_mod.command_handlers.COMMANDS,
                             {"npc-choice": {"any": lambda a, p, g: seen.setdefault("args", a)}}):
            code, _out, err = _run_cli(
                "npc-choice", "--value", "parser_default", "--key", "obj_npc_marker",
                "--text-key", "500", "--text", "* T& &      Yes      No     \\C ")
        self.assertEqual(code, 0, msg=err[-2000:])
        self.assertIsNone(seen["args"].typer)

    def test_npc_choice_handler_resolves_default_5(self):
        from deterline import command_handlers as ch
        rec = {}

        def fake_cmd(*a, **kw):
            rec.update(kw)

        args = argparse.Namespace(
            value="room_ruins1", key="obj_npc_marker", x=100, y=200,
            text_key="500", text="* T& &      Yes      No     \\C ",
            yes_text_key=None, yes_text=None,
            no_text_key="501", no_text="* N./%%",
            face=0, emotion=0, range=50, goto=None, item=None,
            repeat=False, typer=None)
        with mock.patch.object(ch.npc, "cmd_npc_choice", fake_cmd):
            ch._npc_choice_data_win(args, mock.Mock(), Path("/fake/t5.ios"))
        self.assertEqual(rec.get("typer"), 5)

    def test_npc_choice_handler_forwards_explicit_31(self):
        from deterline import command_handlers as ch
        rec = {}

        def fake_cmd(*a, **kw):
            rec.update(kw)

        args = argparse.Namespace(
            value="room_ruins1", key="obj_npc_marker", x=100, y=200,
            text_key="500", text="* T& &      Yes      No     \\C ",
            yes_text_key=None, yes_text=None,
            no_text_key="501", no_text="* N./%%",
            face=0, emotion=0, range=50, goto=None, item=None,
            repeat=False, typer=31)
        with mock.patch.object(ch.npc, "cmd_npc_choice", fake_cmd):
            ch._npc_choice_data_win(args, mock.Mock(), Path("/fake/t31.ios"))
        self.assertEqual(rec.get("typer"), 31)

    def test_cjk_trigger_handler_falls_back_31(self):
        from deterline import command_handlers as ch
        rec = {}

        def fake_trigger(*a, **kw):
            rec["typer"] = a[5]   # (game_file, room, obj, x, y, typer, text, ...)
            return True

        args = argparse.Namespace(
            text="* 中文", room="room_ruins1", object="obj_cactus",
            x_raw=None, y_raw=None, typer=None, no_wrap=False,
            width=None, glyphs=None)
        with mock.patch.object(ch.cjk, "cmd_cjk_trigger", fake_trigger):
            ch._cjk_trigger_data_win(args, mock.Mock(), Path("/fake/tcjk.ios"))
        self.assertEqual(rec["typer"], 31)

    def test_npc_choice_typer_whitelist_rejects_unproven(self):
        from deterline import errors
        from deterline.cmds import npc as npc_mod
        with self.assertRaises(errors.ValidationError) as cm:
            npc_mod.cmd_npc_choice(
                Path("/tmp/none.ios"), "room_ruins1", "obj_npc_marker", 100, 200,
                "500", "* T& &      Yes      No     \\C ",
                no_key="501", no_text="* N./%%", typer=7)
        self.assertIn("无渲染证据", str(cm.exception))

    def test_npc_choice_typer5_cjk_refused(self):
        """I3 防护：typer=5（spacing 8px）+ 非 ASCII = 实证重叠缺陷组合，fail-closed。"""
        from deterline import errors, state
        from deterline.cmds import npc as npc_mod
        with mock.patch.object(state, "ALLOW_CJK", True), \
                self.assertRaises(errors.ValidationError) as cm:
            npc_mod.cmd_npc_choice(
                Path("/tmp/none.ios"), "room_ruins1", "obj_npc_marker", 100, 200,
                "500", "* 往东走吗？& &      是      否     \\C ",
                no_key="501", no_text="* 还是算了。/%%", typer=5)
        self.assertIn("--typer 31", str(cm.exception))
