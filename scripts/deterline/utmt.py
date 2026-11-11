"""Run UTMT commands against the source, a workspace or a pending edit."""

import hashlib
import os
import struct
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from . import errors, sandbox, state, transactions

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
    batch = _active_edit.get()
    if batch and batch.output is not None and batch.source == game_file.resolve():
        return batch.output
    if batch and batch.read_workspace and not state.COMMIT_ACTIVE:
        copy = sandbox.sandbox_path(game_file)
        if copy.is_file():
            return copy
    if state.SANDBOX_ACTIVE:
        if state.SANDBOX_ORIGINAL is None:
            state.SANDBOX_ORIGINAL = game_file
        copy = sandbox.sandbox_path(game_file)
        if state.PREVIEW:
            return copy if copy.is_file() else game_file
        return sandbox.ensure_workspace(game_file)
    return game_file


def _resolve_write_target(game_file: Path) -> Path:
    """V2 写入策略统一入口：写操作（无论走 _run_utmt 还是子进程）默认落沙箱
    副本，--commit 才写真实文件。返回实际应写入的路径。"""
    if not state.SANDBOX_ACTIVE and not state.COMMIT_ACTIVE:
        state.SANDBOX_ACTIVE = True
        print("\U0001F7E1 默认沙箱 (v2 写入安全): 本次写入落在实验工作区。", file=sys.stderr)
        print("   确认后可用 sandbox-restore 应用工作区。", file=sys.stderr)
    if state.PREVIEW and state.SANDBOX_ACTIVE:
        return sandbox.sandbox_path(game_file)
    return _effective_game_file(game_file)


def _steam_target(target: Path) -> Path | None:
    steam = Path("~/Library/Application Support/Steam/steamapps/common/"
                 "Undertale/UNDERTALE.app/Contents/Resources/game.ios").expanduser()
    if (not state.SANDBOX_ACTIVE and not state.NO_STEAM_SYNC
            and target.suffix.lower() == steam.suffix.lower()
            and steam.is_file() and steam.resolve() != target.resolve()):
        return steam.resolve()
    return None


def _run_cli(cmd: list[str], timeout: int) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"UTMT CLI 执行超时 ({timeout} 秒)") from exc
    except FileNotFoundError as exc:
        raise FileNotFoundError("未找到 dotnet。请安装 .NET SDK。") from exc
    if result.returncode != 0:
        raise RuntimeError(f"UTMT CLI 执行失败 (返回码 {result.returncode}):\n{result.stderr}")
    messages = _parse_msg(result.stdout)
    failures = [line for line in messages if line.startswith("ERROR:")]
    if failures:
        hints = [line for line in messages if line.startswith(("HINT:", "WARN:"))]
        raise RuntimeError("UTMT 脚本报告错误: " + "\n".join(failures + hints))
    if result.stderr.strip():
        print(f"[UTMT stderr] {result.stderr.strip()}", file=sys.stderr)
    return result.stdout


class GameEdit:
    def __init__(self, directory: Path, action: str, read_workspace: bool):
        self.directory = directory
        self.action = action
        self.read_workspace = read_workspace
        self.output: Path | None = None
        self.source: Path | None = None
        self.baselines: dict[Path, str | None] = {}
        self.save_edits: list[transactions.FileEdit] = []

    def run(self, game_file: Path, command, timeout: int) -> str:
        if self.source is None:
            self.source = game_file.resolve()
            self.target = _resolve_write_target(game_file).resolve()
            steam = _steam_target(self.target)
            targets = (self.target, steam) if steam else (self.target,)
            self.baselines = {path: transactions.fingerprint(path) for path in targets}
            self.input = self.target if self.target.is_file() else game_file
            self.before = _md5_file(self.input)
        elif self.source != game_file.resolve():
            raise RuntimeError("一次游戏数据修改只能使用一个源文件")
        original = self.output or self.input
        name = "next.ios" if self.output == self.directory / "output.ios" else "output.ios"
        output = self.directory / name
        output.unlink(missing_ok=True)
        stdout = _run_cli(command(original, output), timeout)
        if not output.is_file() or not output.stat().st_size:
            raise RuntimeError("UTMT CLI 输出了空文件或未生成文件，保存已取消")
        with original.open("rb") as previous, output.open("rb") as result:
            if previous.read(4) == b"FORM":
                header = result.read(8)
                if len(header) != 8:
                    raise RuntimeError("UTMT 输出的 GameMaker FORM 文件头不完整")
                kind, size = struct.unpack("<4sI", header)
                if kind != b"FORM" or size + 8 != output.stat().st_size:
                    raise RuntimeError("UTMT 输出的 GameMaker FORM 文件头与文件长度不符")
        self.output = output
        return stdout

    def commit(self) -> None:
        edits = list(self.save_edits)
        if self.output is not None:
            edits.extend(transactions.FileEdit(path, self.output, baseline,
                                               backup=not state.SANDBOX_ACTIVE)
                         for path, baseline in self.baselines.items())
            if state.SANDBOX_ACTIVE:
                record = sandbox.record_edit(self.target, self.output, self.action)
                if record is not None:
                    edits.append(record)
            if state.AUTO_SNAPSHOT and not state.SANDBOX_ACTIVE:
                ts = time.strftime("%Y%m%d_%H%M%S")
                snapshot = self.target.with_name(f"game.ios.snap.auto_{ts}_{time.time_ns()}")
                edits.insert(0, transactions.FileEdit.prepare(snapshot, self.target, backup=False))
        transactions.EditPlan(tuple(edits)).apply()
        if self.output is not None and not state.PREVIEW:
            scope = "仅沙箱副本" if state.SANDBOX_ACTIVE else "真实文件"
            if len(self.baselines) > 1:
                scope += " + Steam 同步"
            print(f"📝 写入回执: {self.target}")
            print(f"   MD5: {self.before[:12]}… → {_md5_file(self.target)[:12]}… | 范围: {scope}")


_active_edit: ContextVar[GameEdit | None] = ContextVar("deterline_game_edit", default=None)


@contextmanager
def game_edit(action: str = "UTMT", *, read_workspace: bool = False):
    existing = _active_edit.get()
    if existing is not None:
        yield existing
        return
    with tempfile.TemporaryDirectory(prefix="deterline-utmt-") as directory:
        batch = GameEdit(Path(directory), action, read_workspace)
        token = _active_edit.set(batch)
        try:
            yield batch
            batch.commit()
        finally:
            _active_edit.reset(token)


def _run_game_write(game_file: Path, command, timeout: int = 120) -> str:
    with game_edit() as batch:
        return batch.run(game_file, command, timeout)


def submit_file_edit(edit: transactions.FileEdit) -> None:
    batch = _active_edit.get()
    if batch is None:
        transactions.EditPlan((edit,)).apply()
    else:
        batch.save_edits.append(edit)


def _run_utmt(csx_code: str, game_file: Path, save: bool = True) -> str:
    """Run a generated CSX script and commit its output through the editor."""
    cli = _find_utmt_cli()
    with tempfile.TemporaryDirectory(prefix="deterline-csx-") as directory:
        script = Path(directory) / "edit.csx"
        script.write_text(csx_code, encoding="utf-8")
        if save:
            return _run_game_write(
                game_file,
                lambda target, output: ["dotnet", cli, "load", str(target),
                                        "-s", str(script), "-o", str(output)],
            )
        target = _effective_game_file(game_file)
        return _run_cli(["dotnet", cli, "load", str(target), "-s", str(script)], 120)


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

def _instances_check_snippet() -> str:
    """Return a C# snippet that audits the in-scope `room` for invalid instance IDs.

    Appended to the CSX of room-write commands (spawn/door/pit/battle) so that any
    operation adding instances reports ID=0 / duplicate-ID problems immediately,
    without an extra UTMT round-trip.  Only reports — never mutates.  The `room`
    variable must be non-null at the point of insertion.
    """
    return r'''
// --- instance ID audit (experiment 19: ID=0/duplicate breaks per-instance vars) ---
int _chkZero = 0;
int _chkDup = 0;
var _chkSeen = new System.Collections.Generic.HashSet<uint>();
foreach (var _chkG in room.GameObjects)
{
    if (_chkG.ObjectDefinition == null) continue;
    if (_chkG.InstanceID == 0) { _chkZero++; }
    else if (!_chkSeen.Add(_chkG.InstanceID)) { _chkDup++; }
}
if (_chkZero > 0 || _chkDup > 0)
{
    ScriptMessage("WARN_INSTANCES:zero=" + _chkZero + " dup=" + _chkDup + " (room=" + room.Name.Content + ")");
    ScriptMessage("  提示: 实例 ID=0/重复会使 per-instance 变量表冲突(Create 写入不生效 → 崩溃/漏口)。");
    ScriptMessage("  请运行: --action verify-instances --fix --file data_win");
}
'''


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
