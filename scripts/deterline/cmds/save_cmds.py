"""存档管理命令域（O2 步 4：从 modify_save.py 1:1 平移）。

undo / list-backups / reset-flags / reset-all / create-system-info /
experiment-*。跨模块一律模块属性形式：errors./paths./inifile./file0.
（运行时查找，保 mock 与旗标写入可见——研讨会2/01 风险 #1 铁律）。
"""

import hashlib
import json
import os
import random
import sys
import time
from pathlib import Path

from .. import errors, file0, inifile, paths, state, transactions

# ============================================================
# Undo: restore from .bak
# ============================================================

GAME_BACKUP_KEYS = {"data_win", "game", "game.ios"}
SYSINFO_KEYS = {"962": "system_information_962", "963": "system_information_963"}


def _backup_target(save_dir: Path | None, key: str, dir_override: str | None) -> Path:
    if key in GAME_BACKUP_KEYS:
        return paths.find_game_data_file(dir_override)
    filenames = {"ini": "undertale.ini", "file0": "file0", **SYSINFO_KEYS}
    if key not in filenames:
        raise errors.ValidationError(f"未知文件: '{key}'")
    directory = save_dir if save_dir is not None else paths.find_save_dir(dir_override)
    return directory / filenames[key]


def cmd_undo(save_dir: Path | None, target: str, backup_ts: str | None = None,
             dir_override: str | None = None) -> None:
    key = target.lower()
    orig = _backup_target(save_dir, key, dir_override)
    if backup_ts and backup_ts != "bak":
        backup_ts = backup_ts.removeprefix("bak.")
        if not backup_ts or Path(backup_ts).name != backup_ts or "\\" in backup_ts:
            raise errors.ValidationError("无效的备份标签")
        bak = orig.with_suffix(orig.suffix + f".bak.{backup_ts}")
    else:
        bak = orig.with_suffix(orig.suffix + ".bak")

    if not bak.exists():
        print(f"没有找到备份文件: {bak}", file=sys.stderr)
        print("可用备份:")
        for b in paths.list_backups(orig):
            print(f"  {b['label']}  ({b['time']}, {b['size']} bytes)")
        return

    transactions.write_one(orig, bak)
    label = f"{key} ({bak.name})" if key in GAME_BACKUP_KEYS else key
    print(f"✓ {label} 已从备份恢复: {bak} → {orig}")


def cmd_list_backups(save_dir: Path | None, target: str,
                     dir_override: str | None = None) -> None:
    orig = _backup_target(save_dir, target.lower(), dir_override)
    backups = paths.list_backups(orig)
    if not backups:
        print(f"没有找到 '{target}' 的备份文件")
        return
    print(f"{'标签':<40} {'时间':<20} {'大小'}")
    print("-" * 80)
    for b in backups:
        tag = b["label"].removeprefix(orig.name + ".")
        print(f"{tag:<40} {b['time']:<20} {b['size']} bytes")


# ============================================================
# Convenience: reset genocide flags
# ============================================================

def cmd_reset_flags(save_dir: Path) -> None:
    path = save_dir / "undertale.ini"
    baselines = {path: transactions.fingerprint(path)}
    cp = inifile._read_ini(path)
    changes = []

    if cp.has_section("Flowey"):
        for key in cp.options("Flowey"):
            old = cp.get("Flowey", key)
            cp.set("Flowey", key, inifile.format_ini_value("0"))
            changes.append(f"[Flowey] {key}: {inifile.parse_ini_value(old)} → 0")

    if cp.has_option("General", "Kills"):
        old = cp.get("General", "Kills")
        cp.set("General", "Kills", inifile.format_ini_value("0"))
        changes.append(f"[General] Kills: {inifile.parse_ini_value(old)} → 0")

    new_fun = random.randint(1, 99)
    if cp.has_option("General", "fun"):
        old = cp.get("General", "fun")
        cp.set("General", "fun", inifile.format_ini_value(str(new_fun)))
        changes.append(f"[General] fun: {inifile.parse_ini_value(old)} → {new_fun}")

    edits = {path: inifile._serialize_ini(cp)} if changes else {}
    f0 = save_dir / "file0"
    old_kills = 0
    if f0.exists():
        baselines[f0] = transactions.fingerprint(f0)
        name, nums = file0._parse_file0(f0)
        if len(nums) > 10 and nums[10] != 0:
            old_kills = nums[10]
            nums[10] = 0
            edits[f0] = file0._serialize_file0(name, nums)
    transactions.write_many(edits, baselines=baselines)
    if changes:
        print("INI 已重置以下屠杀线标志:")
        for change in changes:
            print(f"  • {change}")
    else:
        print("INI: 未发现需要重置的标志。")
    if old_kills:
        print(f"  • file0 Kills: {old_kills} → 0 (已同步)")


# ============================================================
# Full data reset (clean slate for experiments)
# ============================================================

def cmd_reset_all(save_dir: Path) -> None:
    """Reset save data to fresh state: clear bosses, kills, plot, items, equipment.
    Preserves: flag[36] (pacifist memory), flag[510/511] (custom event flags)."""
    path = save_dir / "file0"
    if not path.exists():
        raise errors.NotFoundError(f"file0 不存在: {path}")
    baselines = {path: transactions.fingerprint(path)}
    name, nums = file0._parse_file0(path)
    changes = []

    # Reset LOVE, HP, kills, gold, EXP
    if len(nums) > 0:
        old = nums[0]
        nums[0] = 1
        changes.append(f"LOVE: {old} → 1")
    if len(nums) > 1:
        old = nums[1]
        nums[1] = 20
        changes.append(f"MAXHP: {old} → 20")
    if len(nums) > 2:
        old = nums[2]
        nums[2] = 20
        changes.append(f"MAXEN: {old} → 20")
    if len(nums) > 8:
        old = nums[8]
        nums[8] = 0
        changes.append(f"EXP: {old} → 0")
    if len(nums) > 9:
        old = nums[9]
        nums[9] = 0
        changes.append(f"GOLD: {old} → 0")
    if len(nums) > 10:
        old = nums[10]
        nums[10] = 0
        changes.append(f"KILLS: {old} → 0")

    # Reset items (indices 11-18)
    for i in range(11, 19):
        if i < len(nums) and nums[i] != 0:
            old = nums[i]
            nums[i] = 0
            changes.append(f"INV{i-10}: {old} → 0")

    # Reset equipment (27-28)
    for i in [27, 28]:
        if i < len(nums) and nums[i] != 0:
            old = nums[i]
            nums[i] = 0
            changes.append(f"EQ{i}: {old} → 0")

    # Reset all boss states
    boss_indices = [43, 74, 81, 82, 83, 86, 96, 110, 280, 281, 379, 426, 431, 454]
    for idx in boss_indices:
        if idx < len(nums) and nums[idx] != 0:
            old = nums[idx]
            nums[idx] = 0
            changes.append(f"BOSS[{idx}]: {old} → 0")

    # Reset area kills
    for idx in [230, 231, 232, 233, 234]:
        if idx < len(nums) and nums[idx] != 0:
            old = nums[idx]
            nums[idx] = 0
            changes.append(f"AREA_KILLS[{idx}]: {old} → 0")

    # Reset plot
    if 541 < len(nums) and nums[541] != 0:
        old = nums[541]
        nums[541] = 0
        changes.append(f"PLOT: {old} → 0")

    # Preserve flag[36] (pacifist memory), flag[510] (custom), flag[511] (custom)
    preserve = {36: 1, 510: 0, 511: 0}
    for flag_idx, set_val in preserve.items():
        file0_idx = 29 + flag_idx
        if file0_idx < len(nums):
            old = nums[file0_idx]
            nums[file0_idx] = set_val
            if old != set_val:
                changes.append(f"flag[{flag_idx}]: {old} → {set_val}")

    edits = {path: file0._serialize_file0(name, nums)}
    ini_path = save_dir / "undertale.ini"
    changes_ini = 0
    if ini_path.exists():
        baselines[ini_path] = transactions.fingerprint(ini_path)
        cp = inifile._read_ini(ini_path)
        if cp.has_section("Flowey"):
            for key in cp.options("Flowey"):
                cp.set("Flowey", key, inifile.format_ini_value("0"))
                changes_ini += 1
        for key, value in (("Kills", "0"), ("Love", "1")):
            if cp.has_option("General", key):
                cp.set("General", key, inifile.format_ini_value(value))
                changes_ini += 1
        if changes_ini:
            edits[ini_path] = inifile._serialize_ini(cp)
    transactions.write_many(edits, baselines=baselines)

    print(f"✓ 已重置 {len(changes)} 项 file0 数据:")
    for c in changes:
        print(f"  • {c}")
    if changes_ini:
        print(f"✓ INI 已重置 {changes_ini} 项")
    print("  保留: flag[36]=1 (和平记忆), flag[510/511]=0 (自定义事件)")


# ============================================================
# System Information files (屠杀线结局标记)
# ============================================================

def cmd_create_system_info(save_dir: Path, value: str) -> None:
    """Create system_information_962 or system_information_963."""
    if value not in ("962", "963"):
        raise errors.ValidationError("系统信息文件编号必须是 962 或 963")

    fname = f"system_information_{value}"
    path = save_dir / fname
    if path.exists():
        print(f"'{fname}' 已存在。")
        return
    transactions.write_one(path, b"")
    print(f"✓ 已创建 {fname}  ({'世界已删除' if value == '962' else '已向 Chara 献出灵魂'})")


# ============================================================
# Experiment Management (snapshot/restore for isolation)
# ============================================================

def _experiment_game_file() -> Path:
    """experiment-* 的游戏文件定位：显式 DETERLINE_GAME_FILE 优先于 Steam。

    默认定位优先级 1 是 Steam 安装（game 实际加载路径），但实验命令若在
    副本上演练，必须能用 env 明确隔离——否则会命中真实 Steam 目录
    （审核席 D P1-2；与 v2.3.2 事故同型）。
    """
    override = os.environ.get("DETERLINE_GAME_FILE", "")
    if override:
        path = Path(override).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"DETERLINE_GAME_FILE 不存在: {path}")
        return path
    return paths.find_game_data_file()


def cmd_experiment_snapshot(save_dir: Path, tag: str | None = None) -> None:
    """Create a named snapshot of game.ios and file0 for experiment isolation."""
    game_file = _experiment_game_file()
    ts = time.strftime("%Y%m%d_%H%M%S")
    label = tag or f"exp_{ts}"
    _validate_snapshot_tag(label)
    snap_game = game_file.with_name(f"game.ios.snap.{label}")
    f0 = save_dir / "file0"
    ini = save_dir / "undertale.ini"
    edits = {snap_game: game_file}
    for source in (f0, ini):
        if source.is_file():
            edits[source.with_name(f"{source.name}.snap.{label}")] = source
    transactions.write_many(edits)
    print(f"✓ 实验快照已创建: {label}")
    print(f"  game.ios → game.ios.snap.{label}")
    if f0.exists():
        print(f"  file0    → file0.snap.{label}")
    if ini.exists():
        print(f"  ini      → undertale.ini.snap.{label}")


def cmd_experiment_list(save_dir: Path | None = None) -> None:
    """List all experiment snapshots."""
    game_file = _experiment_game_file()
    parent = game_file.parent
    snaps = sorted(parent.glob("game.ios.snap.*"))
    if not snaps:
        print("(没有实验快照)")
        return
    print(f"找到 {len(snaps)} 个实验快照:")
    for p in reversed(snaps):
        label = str(p.name).removeprefix("game.ios.snap.")
        mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.stat().st_mtime))
        size = p.stat().st_size
        # Check if corresponding file0 snapshot exists
        f0_snap = (save_dir or parent) / f"file0.snap.{label}"
        f0_info = " + file0" if f0_snap.exists() else ""
        print(f"  [{label}] {mtime} ({size} bytes){f0_info}")


def _validate_snapshot_tag(tag: str) -> None:
    if not tag or any(char in tag for char in "/\\*?[]"):
        raise errors.ValidationError("快照标签不能包含路径分隔符或通配符")


def cmd_experiment_restore(save_dir: Path, tag: str) -> None:
    """Restore game.ios and file0 from a named experiment snapshot."""
    game_file = _experiment_game_file()
    parent = game_file.parent
    _validate_snapshot_tag(tag)
    snap_game = parent / f"game.ios.snap.{tag}"
    if not snap_game.exists():
        # Try fuzzy match
        snaps = sorted(parent.glob(f"game.ios.snap.*{tag}*"))
        if not snaps:
            print(f"错误: 未找到快照 '{tag}'", file=sys.stderr)
            print("用 experiment-list 查看可用快照", file=sys.stderr)
            return
        snap_game = snaps[-1]
        tag = str(snap_game.name).removeprefix("game.ios.snap.")
        print(f"模糊匹配: {tag}")
    edits = {game_file.resolve(): snap_game}
    env_game = os.environ.get("DETERLINE_GAME_FILE", "")
    if env_game and not state.NO_STEAM_SYNC:
        fallback = Path(env_game).expanduser()
        if fallback.is_file():
            edits[fallback.resolve()] = snap_game
    for name in ("file0", "undertale.ini"):
        for directory in dict.fromkeys((save_dir, parent)):
            snapshot = directory / f"{name}.snap.{tag}"
            if snapshot.is_file():
                edits[save_dir / name] = snapshot
                break
    transactions.write_many(edits)
    for target, source in edits.items():
        print(f"✓ 已恢复 {target} ← {source.name}")
    print("完成。请重启游戏。")


# ============================================================
# backup-index（阶段 2.3 最小切片，O5）：恢复资产只读索引
# ============================================================

def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(str(path), "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _manifest_summary(copy: Path) -> tuple[str, int | None]:
    """容错读取工作区 manifest（索引对损坏 manifest 不崩——区别于
    check_baseline 的拒绝路径）。返回 (status, history_count|None)。"""
    manifest = copy.with_name(copy.name + ".json")
    try:
        record = json.loads(manifest.read_text(encoding="utf-8"))
        return "ok", len(record.get("history", []))
    except FileNotFoundError:
        return "无manifest", None
    except Exception as e:  # noqa: BLE001 — 索引容错
        return f"损坏({type(e).__name__})", None


def _collect_backup_entries(save_dir: Path | None, dir_override: str | None = None,
                            with_hash: bool = False,
                            hash_kinds: set[str] | None = None):
    """backup-index / backup-prune 共用的只读扫描层（O5/2.4 SSOT）。

    返回 (entries, warnings, game_dir)。entry 与 backup-index --json 行同构：
    kind/path/restore/mtime_*/size_bytes/sha256/manifest?/note?。
    hash_kinds 非空时仅对命中 kind 计算内容哈希（prune 只需 bak 行，
    避免 60MB 级工作区/快照无谓全量读）。
    """
    warnings: list[str] = []
    entries: list[dict] = []
    game_dir: Path | None = None

    def add(kind: str, path: Path, restore: dict | None = None,
            manifest_status: str | None = None,
            manifest_history: int | None = None,
            note: str = "") -> None:
        entry = {"kind": kind, "path": str(path), "restore": restore,
                 "mtime_epoch": None, "mtime_iso": None, "size_bytes": None,
                 "sha256": None}
        try:
            st = path.stat()
            entry["mtime_epoch"] = int(st.st_mtime)
            entry["mtime_iso"] = time.strftime(
                "%Y-%m-%dT%H:%M:%S", time.localtime(st.st_mtime))
            entry["size_bytes"] = st.st_size
            if with_hash and (hash_kinds is None or kind in hash_kinds):
                entry["sha256"] = _sha256_file(path)
        except OSError as exc:
            entry["error"] = str(exc)
        if manifest_status is not None:
            entry["manifest"] = {"status": manifest_status,
                                 "history": manifest_history}
        if note:
            entry["note"] = note
        entries.append(entry)

    try:
        game_file = paths.resolve_game_data_file(dir_override)
        game_dir = game_file.parent
        undo_key = {".ios": "game.ios", ".win": "data_win"}.get(
            game_file.suffix.lower(), game_file.name)
        bak_prefix = game_file.name + ".bak."
        for p in sorted(game_dir.glob(f"{game_file.name}.bak*")):
            if not p.is_file():
                continue
            if p.name == game_file.name + ".bak":
                add("bak-latest", p, {"cmd": "undo", "value": undo_key,
                                      "dir": str(game_file)})
            elif p.name.startswith(bak_prefix) and p.name[len(bak_prefix):]:
                add("bak-archive", p, {"cmd": "undo", "value": undo_key,
                                       "backup": p.name[len(bak_prefix):],
                                       "dir": str(game_file)})
        # cmd_experiment_snapshot 固定写 game.ios.snap.*（Windows 亦然）
        snap_prefix = "game.ios.snap."
        for p in sorted(game_dir.glob(f"{snap_prefix}*")):
            if not p.is_file():
                continue
            tag = p.name[len(snap_prefix):]
            if tag:
                restore = {"cmd": "experiment-restore", "value": tag}
                if save_dir is not None:
                    restore["dir"] = str(save_dir)
                add("named-snapshot", p, restore)
        legacy = game_dir / (game_file.name + ".sandbox")
        if legacy.is_file():
            add("workspace-legacy", legacy,
                {"cmd": "sandbox-restore", "dir": str(game_file)})
        ws_root = game_dir / ".deterline" / game_file.name
        if ws_root.is_dir():
            for copy in sorted(ws_root.glob(f"*/{game_file.name}")):
                if not copy.is_file():
                    continue
                ws_name = copy.parent.name
                m_status, m_hist = _manifest_summary(copy)
                add("workspace-copy", copy,
                    {"cmd": "sandbox-restore", "workspace": ws_name,
                     "dir": str(game_file)},
                    manifest_status=m_status, manifest_history=m_hist)
    except FileNotFoundError as e:
        warnings.append(f"游戏数据目录未定位: {e}")

    if save_dir is not None:
        for sysname in ("system_information_962", "system_information_963"):
            key = sysname.split("_")[-1]
            bak_prefix = sysname + ".bak."
            for p in sorted(save_dir.glob(f"{sysname}.bak*")):
                if not p.is_file():
                    continue
                if p.name == sysname + ".bak":
                    add("system-info", p, {"cmd": "undo", "value": key,
                                           "dir": str(save_dir)})
                elif p.name.startswith(bak_prefix) and p.name[len(bak_prefix):]:
                    add("system-info", p, {"cmd": "undo", "value": key,
                                           "backup": p.name[len(bak_prefix):],
                                           "dir": str(save_dir)})
        for base, key in (("file0", "file0"), ("undertale.ini", "ini")):
            bak_prefix = base + ".bak."
            for p in sorted(save_dir.glob(f"{base}.bak*")):
                if not p.is_file():
                    continue
                if p.name == base + ".bak":
                    add("bak-latest", p, {"cmd": "undo", "value": key,
                                          "dir": str(save_dir)})
                elif p.name.startswith(bak_prefix) and p.name[len(bak_prefix):]:
                    add("bak-archive", p, {"cmd": "undo", "value": key,
                                           "backup": p.name[len(bak_prefix):],
                                           "dir": str(save_dir)})
            snap_prefix = base + ".snap."
            for p in sorted(save_dir.glob(f"{snap_prefix}*")):
                if not p.is_file():
                    continue
                tag = p.name[len(snap_prefix):]
                if not tag:
                    continue
                game_snap = (game_dir / f"game.ios.snap.{tag}"
                             if game_dir is not None else None)
                if game_snap is not None and game_snap.is_file():
                    add("named-snapshot", p, {
                        "cmd": "experiment-restore", "value": tag,
                        "dir": str(save_dir)})
                else:
                    add("orphan-snapshot", p, None,
                        note=f"（孤儿：缺 game.ios.snap.{tag}，不可单独恢复）")
    else:
        warnings.append("存档目录未定位——undo/list-backups 需 --dir")
    return entries, warnings, game_dir


def _entry_restore_hint(entry: dict) -> str:
    restore = entry.get("restore")
    if restore is None:
        return "—（不可单独恢复）"
    hint = restore["cmd"]
    for key in ("value", "workspace"):
        if key in restore:
            hint += f" --{key} {restore[key]}"
            break
    if "backup" in restore:
        hint += " --backup " + restore["backup"]
    if restore.get("dir"):
        hint += f' --dir "{restore["dir"]}"'
    return hint


def cmd_backup_index(save_dir: Path | None, dir_override: str | None = None,
                     with_hash: bool = False, json_out: bool = False) -> int:
    """只读索引：备份/命名快照/工作区副本 → 类型/路径/恢复目标/mtime/大小。

    零写盘、零 UTMT、零清理（O5 保留策略的前置证据面）。
    --hash 追加每项 SHA-256（大文件逐项流式）。
    定位失败降级为提示行，不崩溃（doctor 先例）。
    返回 0=至少一侧定位成功；2=两侧均失败（自动化可区分"空索引"与"路径错"）。
    """
    entries, warnings, game_dir = _collect_backup_entries(
        save_dir, dir_override, with_hash=with_hash)
    if json_out:
        print(json.dumps({
            "schema": "deterline.backup-index/v1",
            "game_dir": str(game_dir) if game_dir is not None else None,
            "save_dir": str(save_dir) if save_dir is not None else None,
            "entries": entries,
            "warnings": warnings,
        }, ensure_ascii=False, indent=2))
    else:
        for entry in entries:
            manifest = entry.get("manifest")
            manifest_note = ""
            if manifest is not None:
                manifest_note = f" | {manifest['status']}"
                if manifest["history"] is not None:
                    manifest_note += f"={manifest['history']}"
            mtime = entry["mtime_iso"] or "?"
            size = (entry["size_bytes"] or 0) / 1e6
            line = (f"{entry['kind']}\t{entry['path']}\t"
                    f"→ {_entry_restore_hint(entry)}\t"
                    f"{mtime}\t{size:.1f}MB{manifest_note}"
                    f"{entry.get('note', '')}")
            if entry.get("sha256"):
                line += f"\tsha256={entry['sha256']}"
            print(line)
        for w in warnings:
            print(f"  ⚠️ {w}", file=sys.stderr)
        print("--- 索引完成 ---")
    return 0 if (game_dir is not None or save_dir is not None) else 2


def cmd_backup_prune(save_dir: Path | None, dir_override: str | None = None,
                     keep_archives: int = 3, json_out: bool = False) -> int:
    """保留策略预览（03 §2.4，**只读零删除**）：重复内容/占盘统计 + 清理建议。

    建议集 = 主文件（game.ios/data.win/file0/undertale.ini 及
    system_information_962/963）的 .bak.<ts> 时间戳归档中超出
    --keep-archives 窗口的部分；bak-latest / 命名快照 / 工作区副本
    （含 legacy）/ journal 引用文件一律保留。重复内容按 sha256 分组统计（同组建议保留最新一份——超窗部分
    已被删除集覆盖）。是否执行清理由用户根据预览决定（执行入口下批）。
    返回 0=预览完成；2=两侧定位均失败。
    """
    entries, warnings, game_dir = _collect_backup_entries(
        save_dir, dir_override, with_hash=True,
        hash_kinds={"bak-archive"})
    if game_dir is None and save_dir is None:
        if json_out:
            print(json.dumps({
                "schema": "deterline.backup-prune/v1",
                "keep_archives": keep_archives,
                "stats": {}, "duplicate_groups": [], "deletions": [],
                "kept_counts": {}, "journal_protected_skipped": 0,
                "warnings": warnings,
            }, ensure_ascii=False, indent=2))
        else:
            for w in warnings:
                print(f"  ⚠️ {w}", file=sys.stderr)
            print("--- 未扫描任何目录（退出码 2） ---")
        return 2

    # 活动恢复记录保护：journal 引用的文件永不进入建议集
    roots = [r for r in (game_dir, save_dir) if r is not None]
    protected = transactions.journal_referenced_files(roots)
    # 损坏 journal = 保护可能不完整（B P3-3）：预览阶段给出显式信号
    corrupt_count = 0
    for journal_root in transactions.journal_roots_for(roots):
        for path in sorted(journal_root.glob("*.json")):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(record, dict):
                    corrupt_count += 1
            except (OSError, ValueError):
                corrupt_count += 1
    if corrupt_count:
        warnings.append(
            f"发现 {corrupt_count} 个损坏/不可解析运行记录——journal 保护可能"
            "不完整；先运行 recovery-scan 处理再做清理决定")

    stats: dict[str, dict] = {}
    total_bytes = 0
    for entry in entries:
        kind = entry["kind"]
        bucket = stats.setdefault(kind, {"count": 0, "bytes": 0})
        bucket["count"] += 1
        bucket["bytes"] += entry.get("size_bytes") or 0
        total_bytes += entry.get("size_bytes") or 0

    # 归档按目标键分组（undo key + 作用域目录）
    groups: dict[tuple, list[dict]] = {}
    latest_rows: dict[tuple, dict] = {}
    for entry in entries:
        restore = entry.get("restore") or {}
        if entry["kind"] == "bak-archive" or (
                entry["kind"] == "system-info" and "backup" in restore):
            key = (restore.get("value"), restore.get("dir"))
            groups.setdefault(key, []).append(entry)
        elif entry["kind"] == "bak-latest":
            key = (restore.get("value"), restore.get("dir"))
            latest_rows[key] = entry

    deletions: list[dict] = []
    duplicate_groups: list[dict] = []
    protected_skipped = 0
    for key, rows in sorted(groups.items(), key=lambda kv: str(kv[0])):
        rows = sorted(rows, key=lambda e: e.get("mtime_epoch") or 0,
                      reverse=True)
        # 内容重复统计（同组 sha 相同，保留最新一份）
        by_sha: dict[str, list[dict]] = {}
        for row in rows:
            sha = row.get("sha256")
            if sha:
                by_sha.setdefault(sha, []).append(row)
        for sha, same in by_sha.items():
            if len(same) > 1:
                deletion_paths = {d["path"] for d in deletions}
                duplicate_groups.append({
                    "key": key[0], "sha256": sha[:16] + "…",
                    "count": len(same),
                    # 只计真正进入删除集的份数（A P3-2：窗口内重复不虚报）
                    "reclaimable_bytes": sum(r.get("size_bytes") or 0
                                             for r in same[1:]
                                             if r["path"] in deletion_paths),
                    "keep_path": same[0]["path"],
                })
        for index, row in enumerate(rows):
            if index < max(int(keep_archives), 1):
                continue
            if str(Path(row["path"]).resolve()) in protected:
                protected_skipped += 1
                continue
            deletions.append({
                "path": row["path"], "key": key[0], "dir": key[1],
                "backup_ts": (row.get("restore") or {}).get("backup"),
                "size_bytes": row.get("size_bytes") or 0,
                "sha256": row.get("sha256"),
                "reason": (f"超出 --keep-archives {keep_archives} 窗口"
                           f"（第 {index + 1} 新）"),
            })

    kept_counts = {}
    for kind in ("bak-latest", "named-snapshot", "workspace-copy",
                 "workspace-legacy", "orphan-snapshot", "system-info"):
        if kind in stats:
            kept_counts[kind] = stats[kind]["count"]

    reclaimable = sum(d["size_bytes"] for d in deletions)
    if json_out:
        print(json.dumps({
            "schema": "deterline.backup-prune/v1",
            "keep_archives": keep_archives,
            "stats": {"total_items": len(entries),
                      "total_bytes": total_bytes,
                      "by_kind": stats},
            "duplicate_groups": duplicate_groups,
            "deletions": deletions,
            "kept_counts": kept_counts,
            "journal_protected_skipped": protected_skipped,
            "warnings": warnings,
        }, ensure_ascii=False, indent=2))
        return 0

    print(f"--- backup-prune（只读预览，零删除） ---")
    print(f"  统计: {len(entries)} 项 / {total_bytes / 1e6:.0f} MB")
    for kind, bucket in sorted(stats.items()):
        print(f"    {kind}: {bucket['count']} 项 / "
              f"{bucket['bytes'] / 1e6:.0f} MB")
    if duplicate_groups:
        print(f"  重复内容: {len(duplicate_groups)} 组"
              f"（组内 sha 相同；超窗部分已入删除集）")
        for group in duplicate_groups[:10]:
            print(f"    {group['key']} sha={group['sha256']}"
                  f" ×{group['count']} 保留最新 {group['keep_path']}"
                  f"（可回收 {group['reclaimable_bytes'] / 1e6:.0f} MB）")
    if deletions:
        print(f"  建议删除 {len(deletions)} 项，可回收 "
              f"{reclaimable / 1e6:.0f} MB（保留条件：bak-latest / 命名快照 / "
              f"工作区 / journal 引用 / 每目标最近 {keep_archives} 份归档）:")
        for d in deletions:
            target_text = d["path"]
            if any(ch in target_text for ch in ('"', "'", "$", "`")):
                print(f"    （路径含 shell 特殊字符，请手动处理）{target_text}")
            else:
                print(f'    rm "{target_text}"')
            print(f"      {d['reason']} | {d['size_bytes'] / 1e6:.0f}MB"
                  f" sha={_fmt_short_sha(d['sha256'])}"
                  f" | undo --value {d['key']} --backup {d['backup_ts']} "
                  f"将随之失效")
    else:
        print("  无超窗归档——无可清理建议")
    if protected_skipped:
        print(f"  journal 保护跳过 {protected_skipped} 项（活动恢复记录引用）")
    print("--- 预览完成（是否执行由用户决定；执行入口下批） ---")
    return 0


def _fmt_short_sha(sha: str | None) -> str:
    return f"{sha[:12]}…" if sha else "<未计算>"
