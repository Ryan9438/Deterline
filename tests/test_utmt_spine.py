"""UTMT 脊柱函数级覆盖（O2 步 3 硬前置，研讨会2/01 风险 #7 / §2.2 步 3）。

此前 _run_utmt 本体零函数级覆盖（代表2:22 实测盲区）。本文件以 mock
subprocess 的方式覆盖其控制流：CSX ERROR 行检测、空输出拒写、超时、
沙箱跳过 Steam 同步、NO_STEAM_SYNC、AUTO_SNAPSHOT、缓存旗标。

铁的纪律：所有路径绝不真实落写到 Steam——subprocess.run 恒 mock；
copy2 用 wraps 真穿（沙箱创建副本等内部流程照常工作，断言盯 call 目标）；
Steam 常驻路径在本机存在，任何非沙箱用例必须叠加 NO_STEAM_SYNC 或沙箱
旗标 patch（本文件每个用例都已满足其一）。
"""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "tests"))

import modify_save as ms  # noqa: E402
import fixtures_save  # noqa: E402
import deterline.utmt as utmt  # noqa: E402
from deterline import errors, paths, sandbox, state  # noqa: E402
from deterline.cmds import verify as smoke_mod  # noqa: E402
from deterline import paths as det_paths  # noqa: E402
from _o2_patch import dual_patch_utmt  # noqa: E402

STEAM_MARK = "UNDERTALE.app"  # Steam 真实路径的特征段（断言用，不含完整路径）


class SpineTestBase(unittest.TestCase):
    def setUp(self):
        d = tempfile.mkdtemp(prefix="utmt_spine_test_")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        self.game_file = Path(d).resolve() / "game.ios"
        self.game_file.write_bytes(b"FAKE-GAME")
        # copy2 真穿 + 录制 call 目标（沙箱创建副本等内部流程不受影响）
        self.copied = []
        real_copy2 = shutil.copy2  # patch 前捕获真身（side_effect 内引用防递归）

        def _recording_copy2(a, b):
            self.copied.append((str(a), str(b)))
            return real_copy2(a, b)

        p = mock.patch("shutil.copy2", side_effect=_recording_copy2)
        p.start()
        self.addCleanup(p.stop)

    def tearDown(self):
        # _run_utmt 会真实写 state 旗标（V2 自动激活沙箱）——每个用例后强制
        # 复位，防泄漏进其他测试（泄漏曾让 readonly 用例看到沙箱 copy）
        state.SANDBOX_ACTIVE = False
        state.SANDBOX_ORIGINAL = None
        state.COMMIT_ACTIVE = False
        state.NO_STEAM_SYNC = False
        state.AUTO_SNAPSHOT = False

    def _ok_run(self, stdout="OK: done\n", output=b"OUT"):
        def run(cmd, **kwargs):
            if "-o" in cmd:
                Path(cmd[cmd.index("-o") + 1]).write_bytes(output)
            return mock.Mock(returncode=0, stdout=stdout, stderr="")
        return mock.patch.object(utmt.subprocess, "run", side_effect=run)

    def _steam_targets(self):
        return [b for a, b in self.copied if STEAM_MARK in b]


class TestRunUtmtControlFlow(SpineTestBase):
    """_run_utmt 控制流矩阵（subprocess 恒 mock，零真实子进程）。"""

    def test_csx_error_lines_raise_and_skip_write(self):
        """CSX 打印 ScriptMessage("ERROR:...") → 硬失败且不回写真实目标。
        （save=True 经 V2 默认沙箱激活沙箱副本——沙箱存在是设计行为；
        本断言只盯真实目标零触碰。）"""
        with mock.patch.object(state, "SANDBOX_ACTIVE", True), \
             self._ok_run(stdout='ERROR: Sprite not found\n'):
            with self.assertRaisesRegex(RuntimeError, "UTMT 脚本报告错误"):
                utmt._run_utmt("// csx", self.game_file, save=True)
        self.assertEqual(self.game_file.read_bytes(), b"FAKE-GAME",
                         "ERROR 路径不得触碰真实目标文件")

    def test_csx_error_carries_hints(self):
        with mock.patch.object(state, "SANDBOX_ACTIVE", True), \
             self._ok_run(stdout='ERROR: bad\nHINT: 试试 spr_x\n'):
            with self.assertRaisesRegex(RuntimeError, "HINT: 试试 spr_x"):
                utmt._run_utmt("// csx", self.game_file, save=True)

    def test_empty_output_rejected(self):
        """UTMT 输出空文件 → 拒绝保存（防 no-op 覆盖）。"""
        with mock.patch.object(state, "SANDBOX_ACTIVE", True), \
             self._ok_run(stdout="OK\n", output=b""):
            with self.assertRaisesRegex(RuntimeError, "空文件"):
                utmt._run_utmt("// csx", self.game_file, save=True)

    def test_nonzero_returncode_raises(self):
        with mock.patch.object(state, "SANDBOX_ACTIVE", True), \
             mock.patch.object(utmt.subprocess, "run",
                               return_value=mock.Mock(returncode=1,
                                                      stdout="", stderr="boom")):
            with self.assertRaisesRegex(RuntimeError, "UTMT CLI 执行失败"):
                utmt._run_utmt("// csx", self.game_file, save=True)

    def test_timeout_raises(self):
        with mock.patch.object(state, "SANDBOX_ACTIVE", True), \
             mock.patch.object(
                 utmt.subprocess, "run",
                side_effect=subprocess.TimeoutExpired(cmd="dotnet", timeout=120)):
            with self.assertRaisesRegex(RuntimeError, "超时"):
                utmt._run_utmt("// csx", self.game_file, save=True)

    def test_readonly_run_never_writes(self):
        """save=False：不解析写目标、不落盘。"""
        with mock.patch.object(state, "SANDBOX_ACTIVE", False), \
             self._ok_run(stdout="DUMP:\ndata") as run_mock:
            out = utmt._run_utmt("// csx", self.game_file, save=False)
        self.assertIn("DUMP:", out)
        run_mock.assert_called_once()
        cmd = run_mock.call_args[0][0]
        self.assertNotIn("-o", cmd)
        self.assertEqual(self.copied, [], "只读路径零 copy")


class TestRunUtmtSafety(SpineTestBase):
    """沙箱/Steam 同步/备份/自动快照安全矩阵。"""

    def test_sandbox_skips_steam_sync(self):
        with mock.patch.object(state, "SANDBOX_ACTIVE", True), \
             self._ok_run(stdout="OK\n"), \
             mock.patch.object(paths, "backup_file"):
            utmt._run_utmt("// csx", self.game_file, save=True)
        self.assertEqual(self._steam_targets(), [],
                         "沙箱模式 Steam 不得同步（copy2 录制断言）")
        self.assertEqual(sandbox.sandbox_path(self.game_file).read_bytes(), b"OUT")
        self.assertEqual(self.game_file.read_bytes(), b"FAKE-GAME")

    def test_no_steam_sync_flag_skips_sync(self):
        with mock.patch.object(state, "COMMIT_ACTIVE", True), \
             mock.patch.object(state, "NO_STEAM_SYNC", True), \
             self._ok_run(stdout="OK\n"), \
             mock.patch.object(paths, "backup_file"):
            utmt._run_utmt("// csx", self.game_file, save=True)
        self.assertEqual(self._steam_targets(), [],
                         "COMMIT + NO_STEAM_SYNC 下 Steam 不得同步")
        self.assertEqual(self.game_file.read_bytes(), b"OUT")

    def test_backup_invoked_when_saving_real_file(self):
        with mock.patch.object(state, "COMMIT_ACTIVE", True), \
             mock.patch.object(state, "NO_STEAM_SYNC", True), \
             self._ok_run(stdout="OK\n"), \
             mock.patch.object(paths, "backup_file") as bak:
            utmt._run_utmt("// csx", self.game_file, save=True)
        bak.assert_called_once_with(self.game_file, required=True)

    def test_autosnapshot_creates_timestamped_snap(self):
        with mock.patch.object(state, "COMMIT_ACTIVE", True), \
             mock.patch.object(state, "AUTO_SNAPSHOT", True), \
             mock.patch.object(state, "NO_STEAM_SYNC", True), \
             self._ok_run(stdout="OK\n"), \
             mock.patch.object(paths, "backup_file"):
            utmt._run_utmt("// csx", self.game_file, save=True)
        snaps = list(self.game_file.parent.glob("game.ios.snap.auto_*"))
        self.assertEqual(len(snaps), 1, "AUTO_SNAPSHOT 应产生恰好一个自动快照")

    def test_no_autosnapshot_in_sandbox(self):
        with mock.patch.object(state, "SANDBOX_ACTIVE", True), \
             mock.patch.object(state, "AUTO_SNAPSHOT", True), \
             self._ok_run(stdout="OK\n"), \
             mock.patch.object(paths, "backup_file"):
            utmt._run_utmt("// csx", self.game_file, save=True)
        self.assertEqual(list(self.game_file.parent.glob("game.ios.snap.auto_*")),
                         [], "沙箱内不产生自动快照（父版语义）")

    def test_second_utmt_step_reads_first_step_and_failure_discards_both(self):
        def run(cmd, **kwargs):
            source = Path(cmd[3])
            output = Path(cmd[cmd.index("-o") + 1])
            if source.read_bytes() == b"FAKE-GAME":
                output.write_bytes(b"FIRST-STEP")
                return mock.Mock(returncode=0, stdout="OK", stderr="")
            self.assertEqual(source.read_bytes(), b"FIRST-STEP")
            return mock.Mock(returncode=1, stdout="", stderr="second step failed")

        with mock.patch.object(state, "COMMIT_ACTIVE", True), \
             mock.patch.object(state, "NO_STEAM_SYNC", True), \
             mock.patch.object(utmt.subprocess, "run", side_effect=run):
            with self.assertRaisesRegex(RuntimeError, "second step failed"):
                with utmt.game_edit():
                    utmt._run_utmt("// step 1", self.game_file)
                    utmt._run_utmt("// step 2", self.game_file)
        self.assertEqual(self.game_file.read_bytes(), b"FAKE-GAME")
        self.assertFalse(self.game_file.with_suffix(".ios.bak").exists())

    def test_steam_replace_failure_rolls_back_first_target(self):
        import os

        steam = self.game_file.parent / "steam.ios"
        steam.write_bytes(b"STEAM-ORIGINAL")
        replace = os.replace

        def fail_steam(source, target):
            if target == steam:
                raise PermissionError("mock Steam permission error")
            return replace(source, target)

        with mock.patch.object(state, "COMMIT_ACTIVE", True), \
             mock.patch.object(utmt, "_steam_target", return_value=steam), \
             self._ok_run(), mock.patch.object(os, "replace", side_effect=fail_steam):
            with self.assertRaisesRegex(PermissionError, "mock Steam permission error"):
                utmt._run_utmt("// edit", self.game_file)
        self.assertEqual(self.game_file.read_bytes(), b"FAKE-GAME")
        self.assertEqual(steam.read_bytes(), b"STEAM-ORIGINAL")
        self.assertEqual(steam.with_suffix(".ios.bak").read_bytes(), b"STEAM-ORIGINAL")


class TestSpineHelpers(SpineTestBase):
    def test_find_utmt_cli_env_and_cache(self):
        fake_cli = self.game_file.parent / "UndertaleModCli.dll"
        fake_cli.write_text("fake")
        with mock.patch.object(state, "_UTMT_CLI_PATH", None), \
             mock.patch.dict("os.environ", {"UTMT_CLI": str(fake_cli)}):
            self.assertEqual(utmt._find_utmt_cli(), str(fake_cli))
            self.assertEqual(state._UTMT_CLI_PATH, str(fake_cli), "解析结果应写缓存旗标")

    def test_parse_msg_filters_noise(self):
        out = ("Trying to load file: 'x'\n[MESSAGE]: IDX:42\nIDX:42\n\n"
               "HINT: 试试 spr_x\n")
        self.assertEqual(utmt._parse_msg(out), ["IDX:42", "HINT: 试试 spr_x"])

    def test_validate_ascii_allow_cjk_gate(self):
        with self.assertRaisesRegex(errors.ValidationError, "非 ASCII"):
            utmt._validate_ascii_text("中文", "文本")
        with mock.patch.object(state, "ALLOW_CJK", True):
            utmt._validate_ascii_text("中文", "文本")  # 不抛
        utmt._validate_ascii_text("ascii ok", "文本")

    def test_room_id_by_name_parses_and_raises(self):
        with dual_patch_utmt(return_value="ROOM_ID:42\n") as m:
            self.assertEqual(utmt._room_id_by_name(self.game_file, "room_x"), "42")
            m.assert_called_once()
        with dual_patch_utmt(return_value=""):
            with self.assertRaisesRegex(errors.NotFoundError, "房间未找到"):
                utmt._room_id_by_name(self.game_file, "room_missing")

    def test_dual_patch_intercepts_both_paths(self):
        """步 3 哨兵演练：ms 裸名路径与 utmt 模块属性路径都能被同一 mock 拦截。"""
        sentinel = "SENTINEL"
        with dual_patch_utmt(side_effect=RuntimeError(sentinel)):
            with self.assertRaisesRegex(RuntimeError, sentinel):
                utmt._run_utmt("// x", self.game_file, save=False)  # 包内路径
            # ms 路径演练（步 3 复核 P3-2：死 probe 换真触发；迁移全程有效——
            # ms 挂点即 shim re-export 绑定，patch 直接改写该命名空间条目）
            with self.assertRaisesRegex(RuntimeError, sentinel):
                ms._run_utmt("// x", self.game_file, save=False)
        # 双挂载断言：patch 退出后两处均恢复为同一真身
        self.assertIs(ms._run_utmt, utmt._run_utmt)


class _FakeClock:
    """假钟：sleep 只推进时钟；time() 返回当前假时刻。

    编排层测试会真跑 cmd_smoke_test 的 strftime（run_id 生成）——strftime
    代理到真实 time 模块（确定性足够）。
    """

    def __init__(self):
        self.now = 0.0

    def sleep(self, seconds):
        self.now += seconds  # 每次轮询推进 2s（与真实节奏一致）

    def time(self):
        return self.now

    def strftime(self, fmt):
        import time as _real
        return _real.strftime(fmt)


class _FakeSp:
    """模拟启动器：按 argv[0] 分派 open/pgrep/osascript/pkill。"""

    def __init__(self, case, *, pgrep_ok_after=None, osascript_rc=0):
        self.case = case
        self.pgrep_ok_after = pgrep_ok_after  # None=永不命中；N=第 N 次 sleep 后命中
        self.osascript_rc = osascript_rc
        self.open_calls = 0
        self.pgrep_calls = 0
        self.osascript_calls = 0

    def run(self, cmd, **kwargs):
        name = cmd[0]
        if name == "open":
            self.open_calls += 1
            return unittest.mock.Mock(returncode=0)
        if name == "pgrep":
            self.pgrep_calls += 1
            ok = (self.pgrep_ok_after is not None
                  and self.case.clock.now >= self.pgrep_ok_after)
            return unittest.mock.Mock(returncode=0 if ok else 1)
        if name == "osascript":
            self.osascript_calls += 1
            return unittest.mock.Mock(returncode=self.osascript_rc)
        if name == "pkill":
            return unittest.mock.Mock(returncode=0)
        return unittest.mock.Mock(returncode=0)


class TestSmokeVerdict(unittest.TestCase):
    """阶段 1.1/1.2：W3 三段裁决负例（mock 启动器 + 假钟，全部离线毫秒级）。"""

    RUN_ID = "20261112_000000_123"

    def setUp(self):
        self.save_dir = fixtures_save.make_save_dir()
        self.addCleanup(shutil.rmtree, str(self.save_dir), ignore_errors=True)
        self.clock = _FakeClock()
        self.sp = _FakeSp(self, pgrep_ok_after=2.0)
        p1 = mock.patch.object(smoke_mod, "time", self.clock)
        p2 = mock.patch.object(smoke_mod, "_sp", self.sp)
        p1.start(); p2.start()
        self.addCleanup(p1.stop); self.addCleanup(p2.stop)

    def _poll(self, *, new_id="7", marker_body=None, launch_allowed=True,
              keys="external", timeout=10.0):
        marker_name = f"zcode_smoke_{self.RUN_ID}.txt"
        marker = self.save_dir / marker_name
        if marker_body is not None:
            marker.write_text(marker_body, encoding="utf-8")
        return smoke_mod._launch_and_poll(
            self.save_dir, timeout, keys, self.RUN_ID, new_id, marker_name,
            launch_allowed=launch_allowed,
            game_exe_running=lambda: self.sp.pgrep_ok_after is not None)

    def _marker_body(self, run_id=RUN_ID, inst="7"):
        return f"SMOKE_OK|run={run_id}|room=room_torielroom|inst={inst}"

    def test_correct_marker_passes(self):
        started, triggered, content, keys_ok, _ = self._poll(
            marker_body=self._marker_body())
        self.assertEqual((started, triggered), ("ok", "ok"))
        self.assertIn(f"run={self.RUN_ID}", content)

    def test_planted_marker_wrong_run_rejected(self):
        """旧标记/伪造正文（同文件名但 run 字段不符）→ 触发判据不接受。"""
        started, triggered, content, _, _ = self._poll(
            marker_body=self._marker_body(run_id="OLD_RUN"))
        self.assertEqual((started, triggered), ("ok", "fail"))
        self.assertIn("run=OLD_RUN", content)

    def test_non_smoke_prefix_rejected(self):
        started, triggered, _, _, _ = self._poll(
            marker_body="gammaruined everything")
        self.assertEqual(triggered, "fail")

    def test_wrong_instance_rejected(self):
        started, triggered, _, _, _ = self._poll(
            marker_body=self._marker_body(inst="999"))
        self.assertEqual((started, triggered), ("ok", "fail"))

    def test_unreadable_marker_degrades_to_fail(self):
        """复核席 3：读取失败不得当作通过（旧实现 exists 即 pass 的洞）。"""
        marker = self.save_dir / f"zcode_smoke_{self.RUN_ID}.txt"
        marker.write_text(self._marker_body(), encoding="utf-8")
        marker.chmod(0o200)  # 写-only：read_text → PermissionError
        self.addCleanup(lambda: marker.chmod(0o644) if marker.exists() else None)
        started, triggered, content, _, _ = self._poll()
        self.assertEqual((started, triggered), ("ok", "fail"))
        self.assertIn("unreadable", content)

    def test_launcher_never_sees_game_unverified(self):
        """pgrep 全程未命中（启动失败/秒退）→ started=fail → UNVERIFIED 而非 FAIL。"""
        self.sp.pgrep_ok_after = None
        started, triggered, _, _, _ = self._poll()
        self.assertEqual((started, triggered), ("fail", "fail"))
        v = smoke_mod.SmokeVerdict(started, triggered, "ok")
        self.assertEqual(v.verdict, "unverified")

    def test_keys_unavailable_unverified(self):
        """osascript 全部失败（辅助功能权限缺失）→ UNVERIFIED 而非 FAIL。"""
        self.sp.osascript_rc = 1
        started, triggered, _, keys_ok, _ = self._poll(keys="osascript")
        self.assertFalse(keys_ok)
        v = smoke_mod.SmokeVerdict(started, triggered, "ok", keys_ok=keys_ok)
        self.assertEqual(v.verdict, "unverified")

    def test_restore_failure_is_fail_not_unverified(self):
        """恢复校验失败是真失败（round-trip 前裁决属性回归）。"""
        v = smoke_mod.SmokeVerdict("ok", "ok", "fail")
        self.assertEqual(v.verdict, "fail")

    def test_launch_path_gate_rejects_tmp_copy(self):
        allowed, reason = smoke_mod._check_launch_path(self.save_dir / "game.ios")
        self.assertFalse(allowed)
        self.assertIn("Steam", reason)

    def test_launch_path_gate_accepts_steam_install(self):
        steam = paths.steam_game_file()
        if steam is None:
            self.skipTest("本机无 Steam 安装")
        allowed, reason = smoke_mod._check_launch_path(steam)
        self.assertTrue(allowed)
        self.assertEqual(reason, "")

    def test_launch_refused_skips_open(self):
        self.sp.pgrep_ok_after = 2.0
        started, triggered, _, _, elapsed = self._poll(launch_allowed=False)
        self.assertEqual((started, triggered, elapsed), ("skipped", "skipped", 0.0))
        self.assertEqual(self.sp.open_calls, 0, "拒绝启动时不得调用 open steam://run")

    def test_nonsteaming_escape_env_documented(self):
        """DETERLINE_SMOKE_ALLOW_NONSTEAM=1 的豁免开关在 cmd_smoke_test 中读取。"""
        import inspect
        src = inspect.getsource(smoke_mod.cmd_smoke_test)
        self.assertIn("DETERLINE_SMOKE_ALLOW_NONSTEAM", src)


class TestSmokeOrchestrator(unittest.TestCase):
    """审核席 B P0-1 回归：cmd_smoke_test 编排层贯通测试（全 mock、零真实
    UTMT/零真实路径）——接缝级测试绿灯下 P0 NameError 曾静默存活。"""

    def _run_orchestrator(self):
        import contextlib as _ctxlib
        import io as _io
        save_dir = fixtures_save.make_save_dir()
        self.addCleanup(shutil.rmtree, str(save_dir), ignore_errors=True)
        game = save_dir / "game.ios"
        game.write_bytes(b"FAKE-ORCHESTRATOR")
        before = {q.name: q.stat().st_mtime_ns for q in save_dir.iterdir()}
        buf = _io.StringIO()
        # 全 mock：注入缝（6 个领域函数）+ game_edit + Steam 定位 + 启动器 + 假钟
        with mock.patch.object(smoke_mod.utmt, "game_edit",
                               side_effect=lambda *a, **k: _ctxlib.nullcontext()), \
             mock.patch.object(smoke_mod.dialogue, "cmd_textdata_add"), \
             mock.patch.object(smoke_mod.room, "_spawn_obj_internal",
                               return_value=1234), \
             mock.patch.object(smoke_mod.npc, "_query_npc_target",
                               return_value={"step_code": "", "native": False,
                                             "alarm_code": None, "obj": "obj_cactus"}), \
             mock.patch.object(smoke_mod.code, "_append_to_code"), \
             mock.patch.object(smoke_mod.code, "cmd_create_script"), \
             mock.patch.object(smoke_mod.utmt, "_room_id_by_name", return_value="31"), \
             mock.patch.object(smoke_mod.inifile, "cmd_ini_set"), \
             mock.patch.object(det_paths, "steam_game_file", return_value=None), \
             mock.patch.object(smoke_mod, "_sp", _FakeSp(self)), \
             mock.patch.object(smoke_mod, "time", _FakeClock()):
            with _ctxlib.redirect_stdout(buf):
                res = ms.cmd_smoke_test(game, save_dir)
        return before, save_dir, buf.getvalue(), res

    def test_orchestrator_reaches_smoke_result_without_nameerror(self):
        """P0-1 回归钉：finally 的 marker.unlink NameError 曾使每次真实调用
        崩溃、SMOKE_RESULT 永不打印、快照泄漏。"""
        before, save_dir, out, res = self._run_orchestrator()
        self.assertIn("SMOKE_RESULT:", out, "三段裁决机器行必须到达（P0-1 曾被 finally NameError 掐断）")
        self.assertIn("verdict=unverified", out)
        self.assertIn("started=skipped", out)
        self.assertEqual(res.verdict, "unverified")
        self.assertEqual(res.started, "skipped")
        self.assertEqual(res.restored, "ok", "演练模式的恢复必须成功")
        # 零残留（演练模式下快照已回滚、无 .bak 泄漏）
        after = {q.name: q.stat().st_mtime_ns for q in save_dir.iterdir()}
        new_names = set(after) - set(before)
        self.assertEqual(new_names, set(),
                         f"演练模式不得残留文件: {new_names}")

    def test_orchestrator_reason_populated(self):
        """审核席 A P2-1：reason 必须进入 SMOKE_RESULT（机器契约）。"""
        _, _, out, res = self._run_orchestrator()
        line = next(l for l in out.splitlines() if l.startswith("   SMOKE_RESULT:"))
        self.assertIn("reason=", line)
        self.assertIn("演练模式", line)


class TestO7DetailDiff(unittest.TestCase):
    """阶段 1.3/1.4：资源级差异的解析/对比/范围判定（单层，假签名零 UTMT）。"""

    def _sig(self, strings, instances, codefp, fonts):
        return {"rooms": {}, "code": {}, "counts": {}, "vardeterline": [],
                "strings": strings, "instances": instances,
                "codefp": codefp, "fonts": fonts}

    def test_string_change_detected(self):
        """02 验收：原地改台词（同 index 改内容）必须检出。"""
        a = self._sig([(10, "aaa"), (12, "bbb")], [], {}, {})
        b = self._sig([(10, "aaa"), (12, "zzz")], [], {}, {})
        rd = smoke_mod._diff_detail_resources(a, b)
        self.assertEqual(len(rd["strings"]), 1)
        self.assertEqual(rd["strings"][0][0], "change")
        self.assertEqual(rd["strings"][0][1][1], "zzz")

    def test_string_insert_no_mass_false_alarm(self):
        """插入一条字符串不产生 16000 级误报（LCS 锚定）。"""
        a = self._sig([(10, f"h{i}") for i in range(50)], [], {}, {})
        b = self._sig([(10, "NEW") ] + [(10, f"h{i}") for i in range(50)], [], {}, {})
        rd = smoke_mod._diff_detail_resources(a, b)
        self.assertEqual(len(rd["strings"]), 1)
        self.assertEqual(rd["strings"][0][0], "add")

    def test_instance_move_detected_as_move(self):
        """02 验收：移动现有实例（id 不变坐标变）→ move 而非 add/remove。"""
        a = self._sig([], [("room_ruins1", 113928, "obj_cactus", 220, 330)], {}, {})
        b = self._sig([], [("room_ruins1", 113928, "obj_cactus", 300, 330)], {}, {})
        rd = smoke_mod._diff_detail_resources(a, b)
        self.assertEqual(len(rd["instances"]["moved"]), 1)
        self.assertEqual(rd["instances"]["moved"][0][1], 113928)
        self.assertEqual(rd["instances"]["added"], [])

    def test_equal_instruction_count_code_change_detected(self):
        """02 验收：同指令数改代码（指纹必变）必须检出。"""
        a = self._sig([], [], {"gml_Script_x": (3, "digest-old")}, {})
        b = self._sig([], [], {"gml_Script_x": (3, "digest-new")}, {})
        rd = smoke_mod._diff_detail_resources(a, b)
        self.assertEqual(rd["code"]["changed"], ["gml_Script_x"])

    def test_font_glyph_remap_detected(self):
        """字形数不变但重映射（digest 变）也检出。"""
        a = self._sig([], [], {}, {"fnt_main": (4064, 3, "g-digest-a")})
        b = self._sig([], [], {}, {"fnt_main": (4064, 3, "g-digest-b")})
        rd = smoke_mod._diff_detail_resources(a, b)
        self.assertEqual(rd["fonts"]["changed"], ["fnt_main"])

    def test_expected_scope_pass_and_violation(self):
        a = self._sig([(10, "old")], [("room_ruins1", 1, "obj_cactus", 1, 1)],
                      {"gml_Script_x": (1, "d1")}, {})
        b = self._sig([(10, "new")], [("room_ruins1", 1, "obj_cactus", 9, 1)],
                      {"gml_Script_x": (1, "d1"),
                       "gml_Script_rogue": (1, "d2")}, {})
        rd = smoke_mod._diff_detail_resources(a, b)
        in_scope = {"strings": "any",
                    "instances": {"room_ruins1": ["move"]},
                    "code": "any"}
        self.assertEqual(smoke_mod._evaluate_expected(rd, in_scope), [],
                         "声明 any 后全部差异应在范围内")
        out = smoke_mod._evaluate_expected(rd, {"strings": "any",
                                             "instances": {"room_ruins1": ["move"]},
                                             "code": ["gml_Script_x"]})
        self.assertTrue(any("rogue" in v for v in out),
                        "范围外新增 code 条目必须报计划外差异")
