"""O2-step0 哨兵与警戒线（研讨会2/01 §2.2 步0 + §三.1/#3）。

三项：
1. --help 全量输出 golden（modify_save.py + run.py）——保护 argparse 迁移逐字节不变（A2）。
2. __file__ 迁移检查项警戒线——登记当前 4 处相对路径（rooms.json ×2、tools ×2），
   拆包搬运改变集合时强制显式更新（风险 #3：迁移后偶发 NotFoundError）。
3. 哨兵演练——patch ms._run_utmt 为 raise 哨兵后调用真实命令，确认调用路径
   经模块属性被拦截、零真实 UTMT 子进程（风险 #1 的提前冒烟；拆包后 from-import
   绑定陷阱将使本演练失败——这正是它的设计目的）。
"""

import os
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "tests"))

from _o2_patch import dual_patch_utmt  # O2 步 3：双路径 patch

import modify_save as ms

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"


def _run_help(script: str) -> str:
    import subprocess
    # COLUMNS 固定：argparse HelpFormatter 是 terminal-size aware（复核席 P1-3：
    # 导出过 COLUMNS 的机器上输出重排，A2 逐字节断言会假失败）
    r = subprocess.run([sys.executable, str(REPO / script), "--help"],
                       capture_output=True, text=True, cwd=str(REPO),
                       env={**os.environ, "COLUMNS": "80"})
    if r.returncode != 0:
        raise RuntimeError(f"{script} --help 退出码 {r.returncode}: {r.stderr[-300:]}")
    return r.stdout


class TestHelpGolden(unittest.TestCase):
    def _check(self, name: str, script: str):
        out = _run_help(script)
        golden = GOLDEN_DIR / f"{name}.txt"
        if os.environ.get("GOLDEN_UPDATE") == "1":
            golden.write_text(out, encoding="utf-8")
            return
        if not golden.exists():
            raise AssertionError(
                f"golden 缺失: {golden}（跑 GOLDEN_UPDATE=1 python3 -m unittest tests.test_o2_step0）")
        self.assertEqual(out, golden.read_text(encoding="utf-8"),
                         f"{script} --help 输出与 golden 不一致（argparse 迁移漂移；"
                         f"有意变更则 GOLDEN_UPDATE=1 重录）")

    def test_help_modify_save(self):
        self._check("help_modify_save", "scripts/modify_save.py")

    def test_help_run(self):
        self._check("help_run", "run.py")


class TestFileMigrationChecklist(unittest.TestCase):
    """风险 #3：__file__ 相对路径在拆包后层级 +1 全部指向错误路径。

    本警戒线登记当前全部 __file__ 使用点（按内容匹配，不按行号——搬运自由，
    集合变化必须显式更新 EXPECTED 并归因）。扫描范围 = modify_save.py +
    deterline/**/*.py（O2 步 2 起与 shape lint 同款发现式收集）。

    归因记录：
    - O2 步 1 复核 P1-1：包引导自举 sys.path 一处（modify_save.py）。
    - O2 步 2：rooms.json 两处（加载/写入）随 rooms_data.py 迁入包内，按方案
      风险 #3 缓解统一为包根解析 parents[1]，并合并为单点 _rooms_json_path()
      （原两处重复字面量 → 一处）。
    - O2 步 9：cjk tools 两处随 cmds/cjk.py 迁入；初版误写 parents[2]（=scripts/），
      A3 post 轮实测捕获（图集工具 can't open file），修正为 parents[3]=仓库根——
      方案风险 #3"验收必须实际触发该路径"的直接兑现。
    """

    EXPECTED = [
        # (描述, 代码片段)
        ("包引导自举（O2 步 1 复核 P1-1：-I/-P/-m 调用形态保持）",
         'str(Path(__file__).resolve().parent)'),
        ("rooms.json 路径单点（rooms_data.py，O2 步 2 包根解析）",
         'parents[1] / "rooms.json"'),
        ("cjk 图集工具路径（cmds/cjk.py，包根解析 parents[3]=仓库根，步 9 引入/A3 修正）",
         'parents[3] / "tools" / "font_cjk_atlas.py"'),
        ("cjk 合成工具路径（cmds/cjk.py，包根解析 parents[3]=仓库根，步 9 引入/A3 修正）",
         'parents[3] / "tools" / "font_emb20_compose.py"'),
        ("cjk-check 默认字形表（cmds/cjk.py，包根解析 parents[3]=仓库根 build/）",
         'parents[3] / "build" / "font_cjk" / "glyphs.json"'),
    ]

    def test_file_usage_set_matches_checklist(self):
        files = [(REPO / "scripts" / "modify_save.py")]
        pkg = REPO / "scripts" / "deterline"
        if pkg.is_dir():
            files.extend(sorted(pkg.glob("**/*.py")))
        found = []
        for f in files:
            if not f.exists() or "__pycache__" in f.parts:
                continue
            for l in f.read_text(encoding="utf-8").split("\n"):
                if "__file__" in l:
                    found.append(f"{f.relative_to(REPO)}: {l.strip()}")
        # 每个登记项必须能在源码中找到对应 __file__ 行
        remaining = list(found)
        for desc, frag in self.EXPECTED:
            hit = next((l for l in remaining if frag in l), None)
            self.assertIsNotNone(
                hit, f"登记项缺失: {desc}（片段 {frag!r}）——迁移检查表过期，请更新 EXPECTED")
            remaining.remove(hit)
        self.assertEqual(
            remaining, [],
            f"存在未登记的 __file__ 使用点（拆包风险 #3）：{remaining}——"
            f"请加入 TestFileMigrationChecklist.EXPECTED 并标注迁移归属")

    def test_room_size_checklist_note(self):
        # 房间尺寸事实（room_ruins1=320×480）已由 B3 实证并写入报告 §九；
        # 拆包时 rooms_data/room 域的尺寸校验必须引用同一事实
        report = (REPO / "AUDIT_2026-11-07" / "C3b-游戏内验证报告.md").read_text(encoding="utf-8")
        self.assertIn("320×480", report, "报告丢失房间尺寸定论——迁移参照失效")


class TestSentinelDrill(unittest.TestCase):
    """风险 #1 提前冒烟：patch ms._run_utmt 为 raise 哨兵，确认零穿透。"""

    def test_cjk_trigger_intercepted_by_sentinel(self):
        # ⚠️ 用临时假数据文件（复核席 P1-2）：真实文件路径在 patch 失效场景下
        # 会让 _run_utmt 真身跑在真文件上；假文件让该失败模式降级为 FileNotFoundError。
        # 且 cmd_cjk_trigger 的 CSX 构建纯内存、_run_utmt 被哨兵替换——零真实目录接触。
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            fake = Path(td) / "game.ios"
            fake.write_bytes(b"fake")
            sentinel_err = "SENTINEL: _run_utmt 不应被直接调用（应经模块属性被本测试拦截）"
            with dual_patch_utmt(side_effect=RuntimeError(sentinel_err)):
                with self.assertRaisesRegex(RuntimeError, "SENTINEL"):
                    ms.cmd_cjk_trigger(fake, "room_ruins1", "obj_cactus",
                                       220, 330, 31, "* 哨兵演练文本")
        # 若上面没有触发哨兵（例如命令路径绕过了模块属性），
        # assertRaisesRegex 会以"未触发 RuntimeError"失败——零穿透即测试失败。

    def test_cjk_font_pass1_intercepted_by_sentinel(self):
        import json as _json
        import tempfile
        sentinel_err = "SENTINEL: pass1 不应直接起 UTMT 子进程"
        with tempfile.TemporaryDirectory() as td:
            # 假 game_file（复核席 P1-2：work_dir 默认 game_file.parent/cjk_work，
            # 真实文件路径会在真游戏目录 mkdir——改临时目录后全程零真实接触）
            fake = Path(td) / "game.ios"
            fake.write_bytes(b"fake")
            # 合规假 build_dir（通过前置校验，让执行路径抵达 _run_utmt）
            bd = Path(td) / "build"
            bd.mkdir()
            (bd / "meta.json").write_text(_json.dumps({"px": 12, "cell": 13}), encoding="utf-8")
            (bd / "glyphs.json").write_text("[]", encoding="utf-8")
            (bd / "cjk_page_0.png").write_bytes(b"png")
            with dual_patch_utmt(side_effect=RuntimeError(sentinel_err)):
                with self.assertRaisesRegex(RuntimeError, "SENTINEL"):
                    ms.cmd_cjk_font(fake, bd, skip_pass1=False)
        # pass2 亦经同一属性（golden 套件 _capture 是同一机制的日常版）


if __name__ == "__main__":
    unittest.main()
