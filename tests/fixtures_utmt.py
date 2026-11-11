"""UTMT 集成夹具（阶段 0.3）：tmp 游戏副本 + CLI 定位 + 跳过守卫。

用法（测试内）：
    from fixtures_utmt import utmt_available, tmp_game_copy, UTMT_CLI

    @unittest.skipUnless(utmt_available(), "需要本机 UTMT CLI 构建")
    def test_something_with_real_utmt(self):
        game = tmp_game_copy(self)      # 注册 addCleanup，返回 tmp 副本路径
        ...                             # 显式 --dir/--game-file 传副本路径

纪律（03 手册 §10）：
- 测试副本一律放独立目录，显式传路径；绝不写真实 Steam 目录或真实存档目录。
- find_game_data_file 优先级 1 是现存 Steam 安装——集成测试不要依赖 env 兜底，
  直接 patch paths.find_game_data_file 或显式传路径。
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

UTMT_CLI_CANDIDATES = [
    os.environ.get("UTMT_CLI", ""),
    str(Path.home() / "UndertaleModTool" / "UndertaleModCli" / "bin"
        / "Release" / "net10.0" / "UndertaleModCli.dll"),
    str(Path.home() / "UndertaleModTool" / "UndertaleModCli" / "bin"
        / "Release" / "net9.0" / "UndertaleModCli.dll"),
]


def find_utmt_cli() -> str | None:
    for cand in UTMT_CLI_CANDIDATES:
        if cand and Path(cand).is_file():
            return cand
    return None


def dotnet_available() -> bool:
    import shutil
    return shutil.which("dotnet") is not None


def utmt_available() -> bool:
    """真实 UTMT 集成测试的跳过守卫（CLI + dotnet + 基线游戏文件齐备）。"""
    return (find_utmt_cli() is not None and dotnet_available()
            and (REPO / "game.ios").is_file())


def utmt_cli() -> str:
    cli = find_utmt_cli()
    if cli is None:
        raise RuntimeError("UTMT CLI 不可用——skipUnless(utmt_available()) 应已拦截")
    return cli


def tmp_game_copy(testcase) -> Path:
    """把仓库基线 game.ios 复制到独立 tmp 目录（注册 addCleanup）。

    testcase 可为 TestCase 实例/类（cls.addCleanup 亦可）。返回副本路径；
    调用方显式传给 --dir / game_file 参数。
    """
    d = Path(tempfile.mkdtemp(prefix="deterline_utmt_fixture_"))
    if isinstance(testcase, type):
        testcase.addClassCleanup(shutil.rmtree, d, ignore_errors=True)  # 类级
    else:
        testcase.addCleanup(shutil.rmtree, d, ignore_errors=True)
    game = d / "game.ios"
    shutil.copy2(REPO / "game.ios", game)
    return game
