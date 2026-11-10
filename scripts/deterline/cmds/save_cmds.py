"""存档管理命令域（O2 步 4：从 modify_save.py 1:1 平移）。

undo / list-backups / reset-flags / reset-all / create-system-info /
experiment-*。跨模块一律模块属性形式：errors./paths./inifile./file0.
（运行时查找，保 mock 与旗标写入可见——研讨会2/01 风险 #1 铁律）。
"""

import os
import random
import shutil
import sys
import tempfile
import time
from pathlib import Path

from .. import errors, file0, inifile, paths

# ============================================================
# Undo: restore from .bak
# ============================================================

def cmd_undo(save_dir: Path, target: str, backup_ts: str | None = None,
             dir_override: str | None = None) -> None:
    files: dict[str, Path] = {
        "ini": save_dir / "undertale.ini",
        "file0": save_dir / "file0",
    }
    key = target.lower()
    if key in ("data_win", "game", "game.ios"):
        try:
            game_file = paths.find_game_data_file(dir_override)
        except FileNotFoundError as e:
            raise errors.NotFoundError(str(e))
        orig = game_file
    elif key in files:
        orig = files[key]
    else:
        raise errors.ValidationError(f"未知文件: '{target}'")

    if backup_ts:
        bak = orig.with_suffix(orig.suffix + f".bak.{backup_ts}")
    else:
        bak = orig.with_suffix(orig.suffix + ".bak")

    if not bak.exists():
        print(f"没有找到备份文件: {bak}", file=sys.stderr)
        print("可用备份:")
        for b in paths.list_backups(orig):
            print(f"  {b['label']}  ({b['time']}, {b['size']} bytes)")
        return

    shutil.copy2(str(bak), str(orig))
    label = f"{key} ({bak.name})" if key in ("data_win", "game", "game.ios") else key
    print(f"✓ {label} 已从备份恢复: {bak} → {orig}")


def cmd_list_backups(save_dir: Path, target: str,
                     dir_override: str | None = None) -> None:
    files: dict[str, Path] = {
        "ini": save_dir / "undertale.ini",
        "file0": save_dir / "file0",
    }
    key = target.lower()
    if key in ("data_win", "game", "game.ios"):
        try:
            game_file = paths.find_game_data_file(dir_override)
        except FileNotFoundError as e:
            raise errors.NotFoundError(str(e))
        orig = game_file
    elif key in files:
        orig = files[key]
    else:
        raise errors.ValidationError(f"未知文件: '{target}'")

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

    if changes:
        inifile._write_ini(path, cp)
        print("INI 已重置以下屠杀线标志:")
        for c in changes:
            print(f"  • {c}")
    else:
        print("INI: 未发现需要重置的标志。")

    # 同时清理 file0 中的 Kills
    try:
        f0 = save_dir / "file0"
        if f0.exists():
            name, nums = file0._parse_file0(f0)
            if len(nums) > 10 and nums[10] != 0:
                old_k = nums[10]
                nums[10] = 0
                file0._write_file0(f0, name, nums)
                print(f"  • file0 Kills: {old_k} → 0 (已同步)")
            else:
                print("file0 Kills 已经是 0。")
    except Exception as e:
        print(f"file0 同步失败: {e}", file=sys.stderr)


# ============================================================
# Full data reset (clean slate for experiments)
# ============================================================

def cmd_reset_all(save_dir: Path) -> None:
    """Reset save data to fresh state: clear bosses, kills, plot, items, equipment.
    Preserves: flag[36] (pacifist memory), flag[510/511] (custom event flags)."""
    path = save_dir / "file0"
    if not path.exists():
        raise errors.NotFoundError(f"file0 不存在: {path}")
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

    file0._write_file0(path, name, nums)

    # Update INI
    try:
        ini_path = save_dir / "undertale.ini"
        cp = inifile._read_ini(ini_path)
        changes_ini = []
        if cp.has_section("Flowey"):
            for key in cp.options("Flowey"):
                cp.set("Flowey", key, inifile.format_ini_value("0"))
                changes_ini.append(f"[Flowey] {key} → 0")
        if cp.has_option("General", "Kills"):
            old = cp.get("General", "Kills")
            cp.set("General", "Kills", inifile.format_ini_value("0"))
            changes_ini.append(f"[General] Kills → {inifile.parse_ini_value(old)}")
        if cp.has_option("General", "Love"):
            old = cp.get("General", "Love")
            cp.set("General", "Love", inifile.format_ini_value("1"))
            changes_ini.append(f"[General] Love → {inifile.parse_ini_value(old)}")
        if changes_ini:
            inifile._write_ini(ini_path, cp)
    except Exception:
        pass

    print(f"✓ 已重置 {len(changes)} 项 file0 数据:")
    for c in changes:
        print(f"  • {c}")
    if changes_ini:
        print(f"✓ INI 已重置 {len(changes_ini)} 项")
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
    path.touch()
    print(f"✓ 已创建 {fname}  ({'世界已删除' if value == '962' else '已向 Chara 献出灵魂'})")


# ============================================================
# Experiment Management (snapshot/restore for isolation)
# ============================================================

def cmd_experiment_snapshot(save_dir: Path, tag: str | None = None) -> None:
    """Create a named snapshot of game.ios and file0 for experiment isolation."""
    game_file = paths.find_game_data_file()
    ts = time.strftime("%Y%m%d_%H%M%S")
    label = tag or f"exp_{ts}"
    # Snapshot game.ios
    snap_game = game_file.with_name(f"game.ios.snap.{label}")
    shutil.copy2(str(game_file), str(snap_game))
    # Snapshot file0
    f0 = save_dir / "file0"
    if f0.exists():
        snap_f0 = save_dir / f"file0.snap.{label}"
        shutil.copy2(str(f0), str(snap_f0))
    # Snapshot ini
    ini = save_dir / "undertale.ini"
    if ini.exists():
        snap_ini = save_dir / f"undertale.ini.snap.{label}"
        shutil.copy2(str(ini), str(snap_ini))
    print(f"✓ 实验快照已创建: {label}")
    print(f"  game.ios → game.ios.snap.{label}")
    if f0.exists():
        print(f"  file0    → file0.snap.{label}")
    if ini.exists():
        print(f"  ini      → undertale.ini.snap.{label}")


def cmd_experiment_list(save_dir: Path | None = None) -> None:
    """List all experiment snapshots."""
    game_file = paths.find_game_data_file()
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
        f0_snap = parent / f"file0.snap.{label}"
        f0_info = " + file0" if f0_snap.exists() else ""
        print(f"  [{label}] {mtime} ({size} bytes){f0_info}")


def cmd_experiment_restore(save_dir: Path, tag: str) -> None:
    """Restore game.ios and file0 from a named experiment snapshot."""
    game_file = paths.find_game_data_file()
    parent = game_file.parent
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
    # Restore game.ios (use temp file to bypass .app bundle protection)
    import tempfile as _tf
    _tmp = _tf.NamedTemporaryFile(suffix=".ios", delete=False).name
    shutil.copy2(str(snap_game), _tmp)
    shutil.copy2(_tmp, str(game_file))
    # Sync to configurable fallback copy if it exists (DETERLINE_GAME_FILE)
    env_game = os.environ.get("DETERLINE_GAME_FILE", "")
    if env_game:
        desktop_game = Path(env_game).expanduser()
        if desktop_game.exists() and str(desktop_game.resolve()) != str(game_file.resolve()):
            shutil.copy2(_tmp, str(desktop_game))
    os.unlink(_tmp)
    print(f"✓ 已恢复 game.ios ← game.ios.snap.{tag}")
    # Restore file0 if exists
    f0 = save_dir / "file0"
    snap_f0 = parent / f"file0.snap.{tag}"
    if snap_f0.exists() and f0.exists():
        shutil.copy2(str(snap_f0), str(f0))
        print(f"✓ 已恢复 file0 ← file0.snap.{tag}")
    # Restore ini if exists
    ini = save_dir / "undertale.ini"
    snap_ini = parent / f"undertale.ini.snap.{tag}"
    if snap_ini.exists() and ini.exists():
        shutil.copy2(str(snap_ini), str(ini))
        print(f"✓ 已恢复 undertale.ini ← undertale.ini.snap.{tag}")
    print("完成。请重启游戏。")
