"""Named game data workspaces with a recorded source baseline."""

import json
import os
import re
import shutil
import tempfile
from pathlib import Path

from . import state, transactions


def workspace_name(name: str) -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", name):
        raise ValueError("工作区名须为 1–64 个小写字母、数字、下划线或连字符，首位须为字母或数字")
    return name


def sandbox_path(game_file: Path) -> Path:
    game_file = game_file.resolve()
    legacy = game_file.with_suffix(game_file.suffix + ".sandbox")
    if state.WORKSPACE is None and legacy.is_file():
        return legacy
    name = state.WORKSPACE or "default"
    return game_file.parent / ".deterline" / game_file.name / name / game_file.name


def _manifest(copy: Path) -> Path:
    return copy.with_name(copy.name + ".json")


def ensure_workspace(game_file: Path) -> Path:
    copy = sandbox_path(game_file)
    if copy.is_file():
        return copy
    root = copy.parent.parent
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".creating-", dir=root) as directory:
        pending = Path(directory) / "workspace"
        pending.mkdir()
        artifact = pending / copy.name
        shutil.copy2(game_file, artifact)
        baseline = transactions.fingerprint(artifact)
        if transactions.fingerprint(game_file) != baseline:
            raise RuntimeError("创建工作区时原始游戏文件已变化，请重试")
        _manifest(artifact).write_text(
            json.dumps({"source_sha256": baseline, "source": str(game_file.resolve())}),
            encoding="utf-8",
        )
        try:
            os.rename(pending, copy.parent)
        except OSError:
            if not copy.is_file():
                raise
    return copy


def check_baseline(game_file: Path, copy: Path) -> str:
    manifest = _manifest(copy)
    try:
        record = json.loads(manifest.read_text(encoding="utf-8"))
        expected = record["source_sha256"]
    except FileNotFoundError as exc:
        raise RuntimeError("沙箱缺少基线记录，请保留旧副本并用 --workspace 创建新工作区。") from exc
    except (ValueError, KeyError, TypeError) as exc:
        raise RuntimeError(f"工作区基线记录损坏: {manifest}") from exc
    if record.get("source", str(game_file.resolve())) != str(game_file.resolve()):
        raise RuntimeError("工作区记录指向其他游戏文件")
    if not isinstance(expected, str) or transactions.fingerprint(game_file) != expected:
        raise RuntimeError("真实游戏文件在创建沙箱后已变化，已拒绝覆盖；请创建新工作区。")
    return expected


def record_edit(copy: Path, artifact: Path, action: str) -> transactions.FileEdit | None:
    manifest = _manifest(copy)
    if not manifest.is_file():
        return None
    baseline = transactions.fingerprint(manifest)
    record = json.loads(manifest.read_text(encoding="utf-8"))
    history = record.setdefault("history", [])
    history.append({"action": action, "sha256": transactions.fingerprint(artifact)})
    data = json.dumps(record, ensure_ascii=False, indent=2).encode("utf-8")
    return transactions.FileEdit(manifest, data, baseline, backup=False)


def remove_workspace(copy: Path) -> None:
    copy.unlink()
    _manifest(copy).unlink(missing_ok=True)
    if copy.parent.parent.parent.name == ".deterline":
        copy.parent.rmdir()  # <文件名>/default 工作区层
        # 清理空目录链（审核席 B P2-1：唯一工作区移除后 .deterline/<名>/ 与
        # .deterline/ 会残留）；rmdir 仅在空目录时成功，非空即保留
        file_layer = copy.parent.parent
        file_layer.rmdir()
        file_layer.parent.rmdir()
