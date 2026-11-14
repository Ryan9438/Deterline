"""Prepare and commit edits to one or more files."""

import difflib
import hashlib
import json
import os
import shutil
import stat
import tempfile
import time
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path

from . import paths, state

Payload = bytes | Path

# 运行记录（03 §2.2 可恢复 journal）：提交前落盘、成功后删除、SIGKILL 保留。
# 状态机 pending → committing →（成功=删除 | aborted-clean | aborted-partial）。
JOURNAL_SCHEMA = "deterline.run-journal/v1"
JOURNAL_STATES = {"pending", "committing", "aborted-clean", "aborted-partial"}


def journal_dir_for(target: Path) -> Path:
    """运行记录目录：首个目标旁 `.deterline/journal/`（与工作区根同层）。"""
    return target.parent / ".deterline" / "journal"


def journal_roots_for(roots) -> list[Path]:
    """给定扫描根（game 目录/存档目录），枚举全部 journal 目录：
    `<root>/.deterline/journal/` + 工作区层 `<root>/.deterline/*/*/.deterline/
    journal/`（sandbox 写路径的记录落在工作区副本旁，顶层看不到）。
    recovery-scan 与 backup-prune（活动恢复记录保护）共用。"""
    out: list[Path] = []
    for root in roots:
        if root is None:
            continue
        journal_root = Path(root) / ".deterline" / "journal"
        if journal_root not in out:
            out.append(journal_root)
        ws_root = Path(root) / ".deterline"
        if ws_root.is_dir():
            for nested in sorted(ws_root.glob("*/*/.deterline/journal")):
                if nested.is_dir() and nested not in out:
                    out.append(nested)
    return out


def journal_referenced_files(roots) -> set[str]:
    """全部未完结运行记录引用的文件（目标 + staged + 回滚副本），resolve
    归一字符串集合。损坏记录跳过（保护宁缺毋滥——clean 批次再收口）。"""
    protected: set[str] = set()
    for journal_root in journal_roots_for(roots):
        for path in sorted(journal_root.glob("*.json")):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(record, dict):
                continue
            for entry in record.get("targets") or []:
                if not isinstance(entry, dict):
                    continue
                for key in ("path", "staged", "rollback"):
                    raw = entry.get(key)
                    if raw:
                        try:
                            protected.add(str(Path(raw).resolve()))
                        except OSError:
                            protected.add(raw)
    return protected


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _content_sha(content: Payload) -> str | None:
    if isinstance(content, bytes):
        return hashlib.sha256(content).hexdigest()
    return fingerprint(content)


def _fsync_dir(path: Path) -> None:
    """目录 fsync（A P3-2 掉电加固）：让 journal 目录项落盘，避免掉电后
    journal 丢失而 staged 残留退化为"无记录孤儿"。Windows 无目录 fsync
    语义（os.open 目录即 OSError）——静默跳过；SIGKILL 语义不受影响。"""
    try:
        fd = os.open(str(path), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _write_json_atomic(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".journal.", suffix=".new", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(record, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        _fsync_dir(path.parent)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _rmdir_if_empty(path: Path) -> None:
    try:
        path.rmdir()
    except OSError:
        pass


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

    def _refuse_unfinished_journals(self, own_targets: set[Path]) -> None:
        """再次运行识别未完结操作（03 §2.2）：同名目标存在未完结运行记录时
        拒绝提交，指引 recovery-scan。
        已知局限：运行记录落在该次提交首个目标的目录旁——跨目录混合提交
        （如 game+ini）崩溃后，只动 ini 的新提交看不到那份记录；recovery-scan
        会同时扫描 game/save 两侧目录兜底。"""
        own_paths = {str(Path(t).resolve()) for t in own_targets}
        roots = []
        for target in own_targets:
            root = journal_dir_for(target)
            if root not in roots:
                roots.append(root)
        for journal_root in roots:
            for path in sorted(journal_root.glob("*.json")):
                try:
                    record = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue  # 损坏记录交给 recovery-scan 报告，不在提交路径阻塞
                if not isinstance(record, dict) or record.get("schema") != JOURNAL_SCHEMA:
                    continue
                if record.get("state") not in JOURNAL_STATES:
                    continue
                targets = record.get("targets") or []
                overlap = any(
                    isinstance(t, dict) and t.get("path")
                    and str(Path(t["path"]).resolve()) in own_paths
                    for t in targets)
                if overlap:
                    raise RuntimeError(
                        f"检测到未完结的运行记录: {path}"
                        f"（state={record.get('state')}）——先运行 recovery-scan "
                        "查看可预览的恢复方式并处理，再重试本次写入")

    def _journal_record(self, journal_id: str, created: str, state: str,
                        staged: dict, rollback: dict, content_shas: dict,
                        error: str | None = None) -> dict:
        record = {
            "schema": JOURNAL_SCHEMA,
            "id": journal_id,
            "state": state,
            "pid": os.getpid(),
            "created": created,
            "updated": _now_iso(),
            "targets": [{
                "path": str(edit.target),
                "before": edit.baseline,
                "after": content_shas.get(edit.target),
                "staged": (str(staged[edit.target])
                           if edit.target in staged else None),
                "rollback": (str(rollback[edit.target])
                             if edit.target in rollback else None),
                "backup": edit.backup,
            } for edit in self.edits],
        }
        if error:
            record["error"] = error
        return record

    def _journal_update(self, path: Path, journal_id: str, created: str,
                        state: str, staged: dict, rollback: dict,
                        content_shas: dict, error: str | None = None) -> None:
        _write_json_atomic(path, self._journal_record(
            journal_id, created, state, staged, rollback, content_shas, error))

    def _commit_locked(self) -> None:
        staged: dict[Path, Path] = {}
        rollback: dict[Path, Path] = {}
        completed: list[Path] = []
        preserve: set[Path] = set()
        journal_path: Path | None = None
        journal_id = (f"{time.strftime('%Y%m%d_%H%M%S')}"
                      f"_{os.getpid()}_{os.urandom(3).hex()}")
        created = _now_iso()
        if not self.edits:
            return  # 空方案（如 set-derived 无实际改动）：无目标即无记录
        # 一次计算内容哈希，pending/committing/aborted-* 共享（B P3-7：
        # Path 载荷 250MB 级时避免每次 update 全量重哈希）
        content_shas = {edit.target: _content_sha(edit.content)
                        for edit in self.edits}
        try:
            self._refuse_unfinished_journals({e.target for e in self.edits})
            journal_path = (journal_dir_for(self.edits[0].target)
                            / f"{journal_id}.json")
            self._journal_update(journal_path, journal_id, created, "pending",
                                 staged, rollback, content_shas)
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
            except BaseException as failure:
                # 暂存/备份阶段失败：目标零替换，回滚语义已由 finally 完成
                # （staged/rollback 暂存删除）——记录 aborted-clean 供 scan 归类
                self._journal_update(journal_path, journal_id, created,
                                     "aborted-clean", staged, rollback,
                                     content_shas, error=str(failure))
                raise
            self._journal_update(journal_path, journal_id, created,
                                 "committing", staged, rollback, content_shas)
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
                journal_state = ("aborted-partial" if recovery_errors
                                 else "aborted-clean")
                self._journal_update(journal_path, journal_id, created,
                                     journal_state, staged, rollback,
                                     content_shas,
                                     error="; ".join(recovery_errors)
                                     or str(failure))
                if recovery_errors:
                    raise RuntimeError("写入失败且回滚不完整: " + "; ".join(recovery_errors)) from failure
                raise
        finally:
            for temporary in (*staged.values(), *rollback.values()):
                if temporary not in preserve:
                    temporary.unlink(missing_ok=True)
        # 全部目标替换成功：记录使命完成（删除前记录已在盘上——SIGKILL 窗口
        # 只会留下"已全部写入"的记录，scan 据此给确认清理指引）
        if journal_path is not None:
            journal_path.unlink(missing_ok=True)
            _rmdir_if_empty(journal_path.parent)
            _rmdir_if_empty(journal_path.parent.parent)  # .deterline 空则摘除

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
