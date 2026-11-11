"""Prepare and commit edits to one or more files."""

import difflib
import hashlib
import os
import shutil
import stat
import tempfile
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path

from . import paths, state

Payload = bytes | Path


def fingerprint(path: Path) -> str | None:
    try:
        with path.open("rb") as stream:
            digest = hashlib.sha256()
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
            return digest.hexdigest()
    except FileNotFoundError:
        return None


@dataclass(frozen=True)
class FileEdit:
    target: Path
    content: Payload
    baseline: str | None
    backup: bool = True

    @classmethod
    def prepare(cls, target: Path, content: Payload, *, backup: bool = True):
        target = target.resolve()
        return cls(target, content, fingerprint(target), backup)


def _stage(target: Path, content: Payload, mode: int | None) -> Path:
    fd, name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".new", dir=target.parent)
    staged = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            if isinstance(content, Path):
                with content.open("rb") as source:
                    shutil.copyfileobj(source, stream, length=1024 * 1024)
            else:
                stream.write(content)
            stream.flush()
            if mode is not None:
                staged.chmod(mode)
            os.fsync(stream.fileno())
        return staged
    except BaseException:
        staged.unlink(missing_ok=True)
        raise


@contextmanager
def _target_lock(target: Path):
    user = os.getuid() if hasattr(os, "getuid") else "user"
    root = Path(tempfile.gettempdir()) / f"deterline-locks-{user}"
    root.mkdir(mode=0o700, exist_ok=True)
    key = hashlib.sha256(os.fsencode(os.path.normcase(target))).hexdigest()
    with (root / key).open("a+b") as stream:
        if os.name == "nt":
            import msvcrt
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        # Closing the descriptor releases the advisory lock on both platforms.
        yield


@dataclass(frozen=True)
class EditPlan:
    edits: tuple[FileEdit, ...]

    def __post_init__(self):
        if len({edit.target for edit in self.edits}) != len(self.edits):
            raise ValueError("修改方案包含重复的文件目标")

    def apply(self) -> None:
        if state.PREVIEW:
            self.preview()
        else:
            self.commit()

    def preview(self) -> None:
        for edit in self.edits:
            self._check_baseline(edit)
            if isinstance(edit.content, bytes):
                after = hashlib.sha256(edit.content).hexdigest()
            else:
                after = fingerprint(edit.content)
            before = edit.baseline or "(新文件)"
            print(f"预览 {edit.target}: {before} → {after}")
            if edit.target.name not in {"file0", "undertale.ini"}:
                continue
            original = edit.target.read_bytes() if edit.baseline else b""
            replacement = edit.content if isinstance(edit.content, bytes) else edit.content.read_bytes()
            diff = difflib.unified_diff(
                original.decode("utf-8", errors="replace").splitlines(),
                replacement.decode("utf-8", errors="replace").splitlines(),
                fromfile="当前", tofile="拟写入", lineterm="",
            )
            for line in diff:
                print(line)

    def commit(self) -> None:
        with ExitStack() as locks:
            for target in sorted(edit.target for edit in self.edits):
                locks.enter_context(_target_lock(target))
            self._commit_locked()

    def _commit_locked(self) -> None:
        staged: dict[Path, Path] = {}
        rollback: dict[Path, Path] = {}
        completed: list[Path] = []
        preserve: set[Path] = set()
        try:
            for edit in self.edits:
                target = edit.target
                self._check_baseline(edit)
                exists = edit.baseline is not None
                mode = stat.S_IMODE(target.stat().st_mode) if exists else None
                staged[target] = _stage(target, edit.content, mode)
                if exists:
                    rollback[target] = _stage(target, target, mode)
                    if fingerprint(rollback[target]) != edit.baseline:
                        raise RuntimeError(f"生成回滚副本时文件已变化: {target}")
            for edit in self.edits:
                self._check_baseline(edit)
                if edit.backup and edit.baseline is not None:
                    paths.backup_file(edit.target, required=True)
            try:
                for edit in self.edits:
                    self._check_baseline(edit)
                    os.replace(staged[edit.target], edit.target)
                    completed.append(edit.target)
            except BaseException as failure:
                recovery_errors = []
                for target in reversed(completed):
                    try:
                        if target in rollback:
                            os.replace(rollback[target], target)
                        else:
                            target.unlink()
                    except OSError as exc:
                        if target in rollback:
                            preserve.add(rollback[target])
                            recovery_errors.append(f"{target}: 恢复副本 {rollback[target]} ({exc})")
                        else:
                            recovery_errors.append(f"{target}: 删除本次新建文件失败 ({exc})")
                if recovery_errors:
                    raise RuntimeError("写入失败且回滚不完整: " + "; ".join(recovery_errors)) from failure
                raise
        finally:
            for temporary in (*staged.values(), *rollback.values()):
                if temporary not in preserve:
                    temporary.unlink(missing_ok=True)

    @staticmethod
    def _check_baseline(edit: FileEdit) -> None:
        if fingerprint(edit.target) != edit.baseline:
            raise RuntimeError(f"文件在准备修改后已变化，已取消写入: {edit.target}")


def write_many(changes: dict[Path, Payload], *, backup: bool = True,
               baselines: dict[Path, str | None] | None = None) -> None:
    baselines = baselines or {}
    edits = []
    for path, data in changes.items():
        if path in baselines:
            edits.append(FileEdit(path.resolve(), data, baselines[path], backup))
        else:
            edits.append(FileEdit.prepare(path, data, backup=backup))
    EditPlan(tuple(edits)).apply()


def write_one(path: Path, data: Payload, *, backup: bool = True) -> None:
    write_many({path: data}, backup=backup)
