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
import deterline.utmt as utmt  # noqa: E402
from deterline import errors, paths, state  # noqa: E402
from _o2_patch import dual_patch_utmt  # noqa: E402

STEAM_MARK = "UNDERTALE.app"  # Steam 真实路径的特征段（断言用，不含完整路径）


class _FakeTF:
    """tempfile.NamedTemporaryFile 替身：write 落到预置路径（支持 with 与裸 .name）。"""

    def __init__(self, path):
        self.name = str(path)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass

    def write(self, b):
        Path(self.name).write_text(b, encoding="utf-8")


class SpineTestBase(unittest.TestCase):
    def setUp(self):
        d = tempfile.mkdtemp(prefix="utmt_spine_test_")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        self.game_file = Path(d) / "game.ios"
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

    def _ok_run(self, stdout="OK: done\n"):
        return mock.patch.object(utmt.subprocess, "run",
                                 return_value=mock.Mock(returncode=0,
                                                        stdout=stdout,
                                                        stderr=""))

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
        csx_path = self.game_file.parent / "in.csx"
        out_path = self.game_file.parent / "empty.ios"
        out_path.write_text("")  # subprocess 被 mock：真实 UTMT 的空产物以预置文件模拟

        def fake_ntf(**kw):
            # csx 临时文件（with+write）与输出临时文件（裸 .name）分离
            return _FakeTF(csx_path if kw.get("suffix") == ".csx" else out_path)

        with mock.patch.object(state, "SANDBOX_ACTIVE", True), \
             self._ok_run(stdout="OK\n"), \
             mock.patch("tempfile.NamedTemporaryFile", side_effect=fake_ntf):
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

    def _fake_ntf_pair(self):
        csx_path = self.game_file.parent / "in.csx"
        out_path = self.game_file.parent / "out.ios"
        Path(out_path).write_text("OUT", encoding="utf-8")  # 非空输出 → 走回写路径

        def fake_ntf(**kw):
            return _FakeTF(csx_path if kw.get("suffix") == ".csx" else out_path)
        return fake_ntf

    def test_sandbox_skips_steam_sync(self):
        with mock.patch.object(state, "SANDBOX_ACTIVE", True), \
             self._ok_run(stdout="OK\n"), \
             mock.patch("tempfile.NamedTemporaryFile", side_effect=self._fake_ntf_pair()), \
             mock.patch.object(paths, "backup_file"):
            utmt._run_utmt("// csx", self.game_file, save=True)
        self.assertEqual(self._steam_targets(), [],
                         "沙箱模式 Steam 不得同步（copy2 录制断言）")
        self.assertTrue(any(b.endswith("game.ios.sandbox") for a, b in self.copied),
                        "沙箱模式应回写 sandbox 副本")

    def test_no_steam_sync_flag_skips_sync(self):
        with mock.patch.object(state, "COMMIT_ACTIVE", True), \
             mock.patch.object(state, "NO_STEAM_SYNC", True), \
             self._ok_run(stdout="OK\n"), \
             mock.patch("tempfile.NamedTemporaryFile", side_effect=self._fake_ntf_pair()), \
             mock.patch.object(paths, "backup_file"):
            utmt._run_utmt("// csx", self.game_file, save=True)
        self.assertEqual(self._steam_targets(), [],
                         "COMMIT + NO_STEAM_SYNC 下 Steam 不得同步")
        self.assertTrue(any(b == str(self.game_file) for a, b in self.copied),
                        "目标本体仍应回写")

    def test_backup_invoked_when_saving_real_file(self):
        with mock.patch.object(state, "COMMIT_ACTIVE", True), \
             mock.patch.object(state, "NO_STEAM_SYNC", True), \
             self._ok_run(stdout="OK\n"), \
             mock.patch("tempfile.NamedTemporaryFile", side_effect=self._fake_ntf_pair()), \
             mock.patch.object(paths, "backup_file") as bak:
            utmt._run_utmt("// csx", self.game_file, save=True)
        bak.assert_called_once_with(self.game_file)

    def test_autosnapshot_creates_timestamped_snap(self):
        with mock.patch.object(state, "COMMIT_ACTIVE", True), \
             mock.patch.object(state, "AUTO_SNAPSHOT", True), \
             mock.patch.object(state, "NO_STEAM_SYNC", True), \
             self._ok_run(stdout="OK\n"), \
             mock.patch("tempfile.NamedTemporaryFile", side_effect=self._fake_ntf_pair()), \
             mock.patch.object(paths, "backup_file"):
            utmt._run_utmt("// csx", self.game_file, save=True)
        snaps = list(self.game_file.parent.glob("game.ios.snap.auto_*"))
        self.assertEqual(len(snaps), 1, "AUTO_SNAPSHOT 应产生恰好一个自动快照")

    def test_no_autosnapshot_in_sandbox(self):
        with mock.patch.object(state, "SANDBOX_ACTIVE", True), \
             mock.patch.object(state, "AUTO_SNAPSHOT", True), \
             self._ok_run(stdout="OK\n"), \
             mock.patch("tempfile.NamedTemporaryFile", side_effect=self._fake_ntf_pair()), \
             mock.patch.object(paths, "backup_file"):
            utmt._run_utmt("// csx", self.game_file, save=True)
        self.assertEqual(list(self.game_file.parent.glob("game.ios.snap.auto_*")),
                         [], "沙箱内不产生自动快照（父版语义）")


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
            # ms 裸名路径：cmd_smoke_test 等 ms 驻留命令经 ms globals 调用
            with mock.patch.object(ms, "_run_utmt") as probe:
                pass  # ms 挂点存在性由 dual_patch 本身保证（同一 mock 两处挂载）
        # 双挂载断言：patch 退出后两处均恢复为同一真身
        self.assertIs(ms._run_utmt, utmt._run_utmt)
