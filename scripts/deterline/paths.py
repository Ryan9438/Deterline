"""存档目录 / 游戏数据文件定位 + 备份（O2 步 1：从 modify_save.py L94-196 1:1 平移）。

本模块无旗标依赖（backup_file 不读 AUTO_SNAPSHOT——自动快照判定在 _run_utmt）。
跨模块引用一律模块属性形式：`paths.find_game_data_file(...)`。
"""

import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

MACOS_PATHS = [
    "~/Library/Application Support/com.tobyfox.undertale",
    "~/Library/Application Support/UNDERTALE",
]

WINDOWS_PATH = "%LOCALAPPDATA%/UNDERTALE"


def find_save_dir(override: str | None = None) -> Path:
    if override:
        p = Path(override).expanduser()
        if p.is_dir():
            return p
        raise FileNotFoundError(f"存档目录不存在: {override}")

    for p_str in MACOS_PATHS:
        p = Path(p_str).expanduser()
        if p.is_dir():
            return p

    win_path = os.path.expandvars(WINDOWS_PATH)
    if win_path != WINDOWS_PATH:
        p = Path(win_path)
        if p.is_dir():
            return p

    raise FileNotFoundError(
        "未找到 UNDERTALE 存档目录。使用 --dir 手动指定。\n"
        "  macOS: ~/Library/Application Support/com.tobyfox.undertale/\n"
        "  Windows: %LOCALAPPDATA%\\UNDERTALE\\"
    )


def steam_game_file() -> Path | None:
    """Steam 安装的 game.ios（启动器实际加载的文件）；不存在时 None。

    阶段 1.1：smoke-test 用它做"编辑目标 = 启动器加载路径"一致性判定。
    """
    p = Path("~/Library/Application Support/Steam/steamapps/common/"
             "Undertale/UNDERTALE.app/Contents/Resources/game.ios").expanduser()
    return p if p.is_file() else None


def find_game_data_file(override: str | None = None) -> Path:
    """Locate game.ios or data.win (for dialogue editing)."""
    if override:
        p = Path(override).expanduser()
        if p.is_file():
            return p
        raise FileNotFoundError(f"游戏数据文件不存在: {override}")
    # Priority 1: Steam app bundle (game reads from here on Steam launch)
    steam = steam_game_file()
    if steam is not None:
        return steam
    # Priority 2: data.win in Steam bundle（steam_game_file()=None 时仍按固定
    # 布局探测 data.win——复核席 B P1-1：对 None 调 with_name 会 AttributeError，
    # 且会打断 DETERLINE_GAME_FILE 安全隔离回退）
    p2 = (Path("~/Library/Application Support/Steam/steamapps/common/"
               "Undertale/UNDERTALE.app/Contents/Resources").expanduser()
          / "data.win")
    if p2.is_file():
        return p2
    # Priority 3: configurable fallback via DETERLINE_GAME_FILE env var
    env_path = os.environ.get("DETERLINE_GAME_FILE", "")
    if env_path:
        p3 = Path(env_path).expanduser()
        if p3.is_file():
            return p3
    raise FileNotFoundError(
        "未找到 UNDERTALE 游戏数据文件 (game.ios/data.win)。\n"
        "  macOS 默认: ~/Library/Application Support/Steam/.../Resources/game.ios\n"
        "  你也可以用 --dir 手动指定文件路径。"
    )


def backup_file(path: Path, *, required: bool = False) -> None:
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    latest = path.with_suffix(path.suffix + ".bak")
    archive = path.with_suffix(path.suffix + f".bak.{timestamp}_{time.time_ns()}")
    for backup in (archive, latest):
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".new", delete=False) as stream:
                temporary = Path(stream.name)
            shutil.copy2(path, temporary)
            with temporary.open("rb") as stream:
                os.fsync(stream.fileno())
            os.replace(temporary, backup)
        except OSError as exc:
            if required:
                raise OSError(f"备份失败，已取消写入: {backup}: {exc}") from exc
            print(f"警告: 备份失败 ({exc})", file=sys.stderr)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def list_backups(path: Path) -> list[dict[str, str]]:
    """List all backup files for a given path, sorted newest first."""
    import time
    pattern = f"{path.name}.bak*"
    backups = []
    for p in sorted(path.parent.glob(pattern), key=lambda x: x.stat().st_mtime, reverse=True):
        size = p.stat().st_size
        mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.stat().st_mtime))
        label = p.name
        ts_part = label.removeprefix(f"{path.name}.bak")
        if ts_part.startswith("."):
            ts_part = ts_part[1:]
        backups.append({
            "path": str(p),
            "label": label,
            "time": mtime,
            "size": size,
            "timestamp": ts_part,
        })
    return backups
