"""UTMT CLI 脊柱（O2 步 3：从 modify_save.py 1:1 平移）。

_run_utmt / 沙箱重定向 / V2 写入策略 / CSX 转义 / 输出解析 / md5 —— 全部命令
域共享的脊柱。跨模块一律模块属性形式：state./errors./paths.（运行时查找，
保 mock 与旗标写入可见）。shutil 在 _run_utmt 内保留函数内导入（1:1）。
"""

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from . import errors, paths, state

def _md5_file(path: Path) -> str:
    """MD5 of a file (streamed) — used by write receipts."""
    h = hashlib.md5()
    with open(str(path), "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

# ============================================================
# UTMT CLI Integration (UndertaleModTool)
# （_UTMT_CLI_PATH 缓存旗标已迁 deterline/state.py，O2 步 1）
# ============================================================

def _find_utmt_cli() -> str:
    """Locate UndertaleModCli.dll."""
    if state._UTMT_CLI_PATH:
        return state._UTMT_CLI_PATH

    env_path = os.environ.get("UTMT_CLI")
    if env_path and Path(env_path).exists():
        state._UTMT_CLI_PATH = env_path
        return env_path

    candidates = [
        Path("UndertaleModCli.dll"),
        Path.home() / "UndertaleModTool" / "UndertaleModCli" / "bin" / "Release" / "net10.0" / "UndertaleModCli.dll",
        Path.home() / "UndertaleModTool" / "UndertaleModCli" / "bin" / "Release" / "net9.0" / "UndertaleModCli.dll",
        Path.home() / "UndertaleModTool" / "UndertaleModCli" / "bin" / "Release" / "net8.0" / "UndertaleModCli.dll",
    ]
    for c in candidates:
        if c.exists():
            state._UTMT_CLI_PATH = str(c)
            return str(c)

    raise FileNotFoundError(
        "未找到 UndertaleModCli.dll。\n"
        "请设置环境变量 UTMT_CLI 指向它，或将其放在运行目录下。\n"
        "下载: https://github.com/UnderminersTeam/UndertaleModTool\n"
        "编译: dotnet build -c Release"
    )


def _csx_escape(value: str) -> str:
    """Escape a string for embedding as a C# string literal ("...")."""
    return (value
        .replace("\\", "\\\\")
        .replace("\"", "\\\"")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t"))


def validate_flag_index(idx: int) -> None:
    """Warn if a global.flag index is outside the valid range (0-511)."""
    if not (0 <= idx <= 511):
        print(f"警告: global.flag[{idx}] 超出有效范围 (0-511)，游戏可能崩溃", file=sys.stderr)


def _validate_ascii_text(text: str, label: str = "文本") -> None:
    """校验对话文本字符集。默认拒绝非 ASCII（英文版位图字体无 CJK glyph，显示空白）。

    --allow-cjk（C3a）放行非 ASCII 并打印行动指南：需先完成中文字体注入（C3b，
    使用 OFL 开源像素字体自生成 glyph）否则对应字符显示为空白。
    """
    non_ascii = [(i, ch) for i, ch in enumerate(text) if ord(ch) > 127]
    if not non_ascii:
        return
    ctx_start = max(0, non_ascii[0][0] - 10)
    ctx_end = min(len(text), non_ascii[0][0] + 10)
    ctx = text[ctx_start:ctx_end]
    chars = " ".join(f"{ch}(U+{ord(ch):04X})" for _, ch in non_ascii[:8])
    if state.ALLOW_CJK:
        print(f"⚠️ {label} 含 {len(non_ascii)} 个非 ASCII 字符: {chars}", file=sys.stderr)
        print("   若游戏已注入中文字体（cjk-font 页内重排栈），这些字符可正常显示；", file=sys.stderr)
        print("   对话触发块请用 cjk-trigger（自动全形态+预折行）。", file=sys.stderr)
        return
    raise errors.ValidationError(
        f"{label} 含有非 ASCII 字符（位置 {non_ascii[0][0]}）: ...{ctx}...\n"
        f"Undertale 英文版位图字体没有中文字形，这些字符（{chars}）将显示为空白。\n"
        f"行动指南:\n"
        f"  1. 改用英文 (ASCII) 文本；或\n"
        f"  2. 加 --allow-cjk 强行写入（需先 cjk-font 注入中文字体栈，否则显示空白）；或\n"
        f"  3. 对话触发块直接用 cjk-trigger --text（自动全形态+预折行）。"
    )


def _csx_verbatim_escape(value: str) -> str:
    """Escape a string for embedding as a C# verbatim string literal (@\"...\").

    In verbatim strings, backslash is literal (not escaped).
    Only double-quotes need doubling.
    """
    return value.replace("\"", "\"\"")


def _effective_game_file(game_file: Path) -> Path:
    """Return the sandbox copy when --sandbox is active, else the original.

    沙箱对**所有**命令生效（含只读）——否则导出/反编译等读取操作会看到原文件、
    看不到沙箱里刚写入的内容（曾导致 colorize-sprite --sandbox 必然失败）。
    """
    if state.SANDBOX_ACTIVE:
        if state.SANDBOX_ORIGINAL is None:
            state.SANDBOX_ORIGINAL = game_file
        sandbox_path = game_file.with_suffix(game_file.suffix + ".sandbox")
        if not sandbox_path.exists():
            shutil.copy2(str(game_file), str(sandbox_path))
            print(f"🔒 沙箱模式: 已创建 {sandbox_path.name}", file=sys.stderr)
        return sandbox_path
    return game_file


def _resolve_write_target(game_file: Path) -> Path:
    """V2 写入策略统一入口：写操作（无论走 _run_utmt 还是子进程）默认落沙箱
    副本，--commit 才写真实文件。返回实际应写入的路径。"""
    if not state.SANDBOX_ACTIVE and not state.COMMIT_ACTIVE:
        state.SANDBOX_ACTIVE = True
        print("\U0001F7E1 默认沙箱 (v2 写入安全): 本次写入仅落在 *.sandbox 副本，真实文件未动。", file=sys.stderr)
        print("   确认无误后: 加 --commit 直写真实文件(+Steam 同步)，或 sandbox-restore 应用沙箱。", file=sys.stderr)
    return _effective_game_file(game_file)


def _run_utmt(csx_code: str, game_file: Path, save: bool = True) -> str:
    """Run a C# script via UndertaleModCli and return stdout.

    If save=True, the modified game file is saved back in-place (with backup).
    If save=False, the script runs as read-only (no output file).
    In sandbox mode, operates on game_file.sandbox instead.
    """
    cli = _find_utmt_cli()

    if save and state.AUTO_SNAPSHOT and not state.SANDBOX_ACTIVE:
        ts = time.strftime("%Y%m%d_%H%M%S")
        snap_path = game_file.with_name(f"game.ios.snap.auto_{ts}")
        shutil.copy2(str(game_file), str(snap_path))
        print(f"📸 自动快照: {snap_path.name}", file=sys.stderr)

    # ── V2 写入默认安全：写操作走统一策略入口（默认沙箱，--commit 直写）──
    if save:
        target = _resolve_write_target(game_file)
    else:
        target = _effective_game_file(game_file) if state.SANDBOX_ACTIVE else game_file

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csx", delete=False, encoding="utf-8") as f:
        f.write(csx_code)
        csx_path = f.name

    try:
        if save and not state.SANDBOX_ACTIVE:
            paths.backup_file(target)

        # Save to temp file first (workaround: .app bundle prevents direct File.Move)
        saved_to_temp = False
        _before_write = _md5_file(target) if save else ""
        temp_output = None
        if save:
            import tempfile as _tf
            temp_output = _tf.NamedTemporaryFile(suffix=".ios", delete=False).name
            cmd = ["dotnet", cli, "load", str(target), "-s", csx_path, "-o", temp_output]
        else:
            cmd = ["dotnet", cli, "load", str(target), "-s", csx_path]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            if temp_output and os.path.exists(temp_output):
                os.unlink(temp_output)
            raise RuntimeError(
                f"UTMT CLI 执行失败 (返回码 {result.returncode}):\n{result.stderr}"
            )

        # A CSX script can print ScriptMessage("ERROR: ...") and `return` without
        # setting a non-zero exit code. Treat that as a hard failure and DO NOT write
        # the (unchanged/partial) output back — prevents no-op rewrites and
        # "zero-operation fabricated success" reports.
        csx_errs = [l for l in _parse_msg(result.stdout) if l.startswith("ERROR:")]
        if csx_errs:
            if temp_output and os.path.exists(temp_output):
                os.unlink(temp_output)
            msg = "UTMT 脚本报告错误: " + "; ".join(csx_errs)
            # HINT（相似名称推荐等）与 ERROR 同批输出时随异常带上，
            # 否则会被异常传播吞掉、永远到不了用户。
            hints = [l for l in _parse_msg(result.stdout)
                     if l.startswith("HINT:") or l.startswith("WARN:")]
            if hints:
                msg += "\n" + "\n".join(hints)
            raise RuntimeError(msg)

        # Copy temp output to target (bypass .app bundle File.Move issue)
        if save and temp_output and os.path.exists(temp_output):
            if os.path.getsize(temp_output) == 0:
                os.unlink(temp_output)
                raise RuntimeError("UTMT CLI 输出了空文件，保存已取消")
            import shutil as _shutil
            _shutil.copy2(temp_output, str(target))
            # Also sync to Steam app bundle (game reads from there on Steam launch).
            # Never sync in sandbox mode — the sandbox copy must not leak into the real file.
            steam_path = Path("~/Library/Application Support/Steam/steamapps/common/"
                             "Undertale/UNDERTALE.app/Contents/Resources/game.ios").expanduser()
            steam_synced = False
            if (not state.SANDBOX_ACTIVE and steam_path.exists()
                    and str(steam_path.resolve()) != str(Path(target).resolve())):
                if state.NO_STEAM_SYNC:
                    print("\U0001F6D1 --no-steam-sync: 已跳过 Steam 同步（真实文件已更新，Steam 内需手动同步）", file=sys.stderr)
                else:
                    _shutil.copy2(temp_output, str(steam_path))
                    steam_synced = True
            os.unlink(temp_output)
            saved_to_temp = True
            # ── 写入回执：影响文件 + MD5 前后 + 退路（信任机制，研讨会共识）──
            try:
                _after = _md5_file(Path(target))
            except OSError:
                _after = "?"
            if state.SANDBOX_ACTIVE:
                _scope = "仅沙箱副本"
            elif steam_synced:
                _scope = "真实文件 + Steam 同步"
            elif state.NO_STEAM_SYNC:
                _scope = "真实文件（--no-steam-sync，未同步 Steam）"
            else:
                _scope = "真实文件（目标即 Steam 路径，无需同步）"
            print(f"\U0001F4DD 写入回执: {target}")
            print(f"   MD5: {_before_write[:12]}… → {_after[:12]}… | 范围: {_scope}")
            if state.SANDBOX_ACTIVE:
                print("   应用: --commit 直写 或 sandbox-restore；放弃: 直接删除 *.sandbox")
            else:
                print("   退路: undo --value data_win / list-backups / experiment-restore")

        if result.stderr.strip():
            print(f"[UTMT stderr] {result.stderr.strip()}", file=sys.stderr)
        return result.stdout
    except subprocess.TimeoutExpired:
        raise RuntimeError("UTMT CLI 执行超时 (120 秒)")
    except FileNotFoundError:
        raise FileNotFoundError(
            "未找到 dotnet。请安装 .NET SDK:\n"
            "  brew install dotnet\n"
            "  或 https://dotnet.microsoft.com/download"
        )
    finally:
        Path(csx_path).unlink(missing_ok=True)


def _bool_or_none(s: str | None) -> bool | None:
    if s is None:
        return None
    return s.lower() in ("true", "1", "yes", "y")


def _parse_msg(output: str) -> list[str]:
    """Extract relevant lines from UTMT's ScriptMessage output."""
    lines = []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("Trying to load"):
            continue
        if stripped.startswith("[MESSAGE]:"):
            continue
        lines.append(stripped)
    return lines


# Exit code used when a search returns zero matches (distinct from generic error 1).
NO_MATCH_EXIT_CODE = 3


def _fail_if_no_match(lines: list[str], kind: str, query: str) -> None:
    """Exit non-zero with a loud warning when a search returns zero matches.

    Guards against "zero-operation fabricated success": a search that finds
    nothing must not be silently treated as a successful step. The agent must
    report the failure instead of inventing names/results.
    """
    if any(l.startswith("(no") for l in lines):
        print(f"警告: {kind} 无匹配: '{query}'", file=sys.stderr)
        print("      未找到目标——禁止编造名称或结果；请如实报告失败。", file=sys.stderr)
        sys.exit(NO_MATCH_EXIT_CODE)

def _room_id_by_name(game_file: Path, room_name: str) -> str:
    """按内部名解析房间数字 ID（resolve_room 只认数字/中文名，不认内部名）。"""
    esc = _csx_escape(room_name)
    csx = f"""
for (int i = 0; i < Data.Rooms.Count; i++) {{
    if (Data.Rooms[i].Name.Content == "{esc}") {{ ScriptMessage("ROOM_ID:" + i); break; }}
}}
"""
    out = _run_utmt(csx, game_file, save=False)
    for line in _parse_msg(out):
        if line.startswith("ROOM_ID:"):
            return line[len("ROOM_ID:"):]
    raise errors.NotFoundError(f"smoke-test: 房间未找到: {room_name}")
