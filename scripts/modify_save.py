#!/usr/bin/env python3
"""Deterline — UNDERTALE Save Editor (modify undertale.ini and file0)."""

import argparse
import configparser
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# ============================================================
# Constants
# ============================================================

FLAG_INDEX_MAX = 511
FLAG_CUSTOM_START = 510
FLAG_CUSTOM_END = 511

FACE_CHOICES: dict[int, str] = {
    0: "无头像",
    1: "Toriel", 2: "Flowey", 3: "Sans",
    4: "Papyrus", 5: "Undyne", 6: "Alphys",
    7: "Asgore", 8: "Mettaton", 9: "Asriel",
}

SANS_EMOTIONS: dict[int, str] = {
    0: "普通", 1: "轻笑", 2: "眨眼", 3: "慢眨眼", 4: "无眼",
}

DISTANCE_TRIGGER = 50
QUEST_STATE_INIT = 0

# ============================================================
# Custom Exceptions
# ============================================================

class DeterlineError(Exception):
    """Base exception for all Deterline errors."""

class ValidationError(DeterlineError):
    """Invalid argument or parameter."""

class NotFoundError(DeterlineError):
    """File, room, or object not found."""

# ============================================================
# Sandbox mode
# ============================================================

SANDBOX_ACTIVE = False
SANDBOX_ORIGINAL: Path | None = None

# ============================================================
# Path Detection
# ============================================================

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


def find_game_data_file(override: str | None = None) -> Path:
    """Locate game.ios or data.win (for dialogue editing)."""
    if override:
        p = Path(override).expanduser()
        if p.exists():
            return p
        raise FileNotFoundError(f"游戏数据文件不存在: {override}")
    p = Path("~/Library/Application Support/Steam/steamapps/common/"
             "Undertale/UNDERTALE.app/Contents/Resources/game.ios").expanduser()
    if p.exists():
        return p
    # Also check for data.win in the same directory
    p2 = p.with_name("data.win")
    if p2.exists():
        return p2
    raise FileNotFoundError(
        "未找到 UNDERTALE 游戏数据文件 (game.ios/data.win)。\n"
        "  macOS 默认: ~/Library/Application Support/Steam/.../Resources/game.ios\n"
        "  你也可以用 --dir 手动指定文件路径。"
    )


def backup_file(path: Path) -> None:
    import time
    bak = path.with_suffix(path.suffix + ".bak")
    try:
        shutil.copy2(str(path), str(bak))
    except OSError as e:
        print(f"警告: 备份失败 ({e})", file=sys.stderr)
    ts = time.strftime("%Y%m%d_%H%M%S")
    ts_bak = path.with_suffix(path.suffix + f".bak.{ts}")
    try:
        shutil.copy2(str(path), str(ts_bak))
    except OSError as e:
        print(f"警告: 时间戳备份失败 ({e})", file=sys.stderr)


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


# ============================================================
# UTMT CLI Integration (UndertaleModTool)
# ============================================================

_UTMT_CLI_PATH: str | None = None


def _find_utmt_cli() -> str:
    """Locate UndertaleModCli.dll."""
    global _UTMT_CLI_PATH
    if _UTMT_CLI_PATH:
        return _UTMT_CLI_PATH

    env_path = os.environ.get("UTMT_CLI")
    if env_path and Path(env_path).exists():
        _UTMT_CLI_PATH = env_path
        return env_path

    candidates = [
        Path("UndertaleModCli.dll"),
        Path.home() / "UndertaleModTool" / "UndertaleModCli" / "bin" / "Release" / "net10.0" / "UndertaleModCli.dll",
        Path.home() / "UndertaleModTool" / "UndertaleModCli" / "bin" / "Release" / "net9.0" / "UndertaleModCli.dll",
        Path.home() / "UndertaleModTool" / "UndertaleModCli" / "bin" / "Release" / "net8.0" / "UndertaleModCli.dll",
    ]
    for c in candidates:
        if c.exists():
            _UTMT_CLI_PATH = str(c)
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


def _csx_verbatim_escape(value: str) -> str:
    """Escape a string for embedding as a C# verbatim string literal (@\"...\").

    In verbatim strings, backslash is literal (not escaped).
    Only double-quotes need doubling.
    """
    return value.replace("\"", "\"\"")


def _run_utmt(csx_code: str, game_file: Path, save: bool = True) -> str:
    """Run a C# script via UndertaleModCli and return stdout.

    If save=True, the modified game file is saved back in-place (with backup).
    If save=False, the script runs as read-only (no output file).
    In sandbox mode, operates on game_file.sandbox instead.
    """
    global SANDBOX_ACTIVE, SANDBOX_ORIGINAL
    cli = _find_utmt_cli()

    target = game_file
    if save and SANDBOX_ACTIVE:
        if SANDBOX_ORIGINAL is None:
            SANDBOX_ORIGINAL = game_file
        sandbox_path = game_file.with_suffix(game_file.suffix + ".sandbox")
        if not sandbox_path.exists():
            shutil.copy2(str(game_file), str(sandbox_path))
            print(f"🔒 沙箱模式: 已创建 {sandbox_path.name}", file=sys.stderr)
        target = sandbox_path

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csx", delete=False, encoding="utf-8") as f:
        f.write(csx_code)
        csx_path = f.name

    try:
        cmd = ["dotnet", cli, "load", str(target), "-s", csx_path]
        if save:
            if not SANDBOX_ACTIVE:
                backup_file(target)
            cmd.extend(["-o", str(target)])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(
                f"UTMT CLI 执行失败 (返回码 {result.returncode}):\n{result.stderr}"
            )
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


# ============================================================
# INI Value Helpers
# ============================================================

def format_ini_value(value: str) -> str:
    try:
        num = float(value)
        return f'"{num:.6f}"'
    except ValueError:
        return f'"{value}"'


def parse_ini_value(raw: str) -> str:
    s = raw.strip()
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    try:
        f = float(s)
        return str(int(f)) if f == int(f) else s
    except ValueError:
        return s


# ============================================================
# INI Operations
# ============================================================

KNOWN_KEYS = {
    "Love": "LOVE / 等级 (1-20)",
    "Kills": "击杀数 (屠杀线判定)",
    "Room": "当前房间 ID (支持中文名称)",
    "fun": "趣味值 (影响 Gaster 等隐藏事件)",
    "Name": "玩家名称",
    "Time": "游戏时间 (秒)",
    "Gameover": "死亡次数",
}

ROOMS: dict[str, str] = {}
_ROOMS_LOADED = False


def _load_rooms() -> None:
    global ROOMS, _ROOMS_LOADED
    if _ROOMS_LOADED:
        return
    p = Path(__file__).resolve().parent / "rooms.json"
    try:
        with open(str(p), "r", encoding="utf-8") as f:
            ROOMS = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        ROOMS = {}
    _ROOMS_LOADED = True


def resolve_room(val: str) -> str:
    """Return numeric room ID string given a room number or Chinese name."""
    _load_rooms()
    # already a number
    if val.lstrip("-").isdigit():
        return val
    # exact Chinese name match
    for rid, name in ROOMS.items():
        if name == val:
            return rid
    # partial match — find all matches
    candidates = [(rid, name) for rid, name in ROOMS.items() if val in name]
    if len(candidates) == 1:
        return candidates[0][0]
    if len(candidates) > 1:
        lines = "\n".join(f"  [{rid}] {name}" for rid, name in candidates)
        print(f"匹配到多个房间:\n{lines}\n请使用更精确的名称或直接使用房间 ID。", file=sys.stderr)
        raise NotFoundError(f"匹配到多个房间: {val}")
    print(f"错误: 未找到匹配 '{val}' 的房间", file=sys.stderr)
    raise NotFoundError(f"未找到匹配的房间: {val}")


def format_room(rid: str) -> str:
    """Display room ID with its Chinese name."""
    _load_rooms()
    name = ROOMS.get(rid)
    return f"房间 {rid} — {name}" if name else f"房间 {rid}"


def normalize_key(key: str) -> str:
    upper = key.upper()
    for known in KNOWN_KEYS:
        if known.upper() == upper:
            return known
    return key


class _CasePreservingConfigParser(configparser.ConfigParser):
    """Preserve key case for Undertale's case-sensitive INI parser."""
    def optionxform(self, optionstr: str) -> str:
        return optionstr

    def get(self, section: str, option: str, **kwargs) -> str:
        return super().get(section, self._find_key(section, option), **kwargs)

    def set(self, section: str, option: str, value: str | None = None) -> None:
        super().set(section, self._find_key(section, option), value)

    def has_option(self, section: str, option: str) -> bool:
        return super().has_option(section, self._find_key(section, option))

    def _find_key(self, section: str, option: str) -> str:
        if super().has_option(section, option):
            return option
        for opt in self.options(section):
            if opt.lower() == option.lower():
                return opt
        return option


def _read_ini(path: Path) -> _CasePreservingConfigParser:
    if not path.exists():
        raise FileNotFoundError(f"存档文件不存在: {path}")
    try:
        cp = _CasePreservingConfigParser()
        cp.read(str(path), encoding="utf-8")
        return cp
    except configparser.DuplicateOptionError:
        cp = _CasePreservingConfigParser(strict=False)
        cp.read(str(path), encoding="utf-8")
        print("检测到 INI 重复键 (游戏多周目残留)，自动清理...")
        _write_ini(path, cp)
        print("  ✓ 已清理")
        cp = _CasePreservingConfigParser()
        cp.read(str(path), encoding="utf-8")
        return cp


def _write_ini(path: Path, cp: configparser.ConfigParser) -> None:
    backup_file(path)
    with open(str(path), "w", encoding="utf-8") as f:
        cp.write(f, space_around_delimiters=False)


def cmd_ini_list(save_dir: Path) -> None:
    path = save_dir / "undertale.ini"
    cp = _read_ini(path)
    for section in cp.sections():
        print(f"\n[{section}]")
        for key, value in cp.items(section):
            display = parse_ini_value(value)
            desc = KNOWN_KEYS.get(key, "")
            line = f"  {key} = {display}"
            if desc:
                line += f"  ({desc})"
            if key == "Room":
                _load_rooms()
                name = ROOMS.get(str(display))
                if name:
                    line += f"\n    → {name}"
            print(line)


def cmd_ini_get(save_dir: Path, section: str, key: str) -> None:
    path = save_dir / "undertale.ini"
    cp = _read_ini(path)
    key = normalize_key(key)
    try:
        raw = cp.get(section, key)
    except (configparser.NoSectionError, configparser.NoOptionError):
        raise NotFoundError(f"[{section}] 中未找到 '{key}'")
    display = parse_ini_value(raw)
    desc = KNOWN_KEYS.get(key, "")
    line = f"{key} = {display}"
    if desc:
        line += f"  ({desc})"
    if key == "Room":
        _load_rooms()
        name = ROOMS.get(str(display))
        if name:
            line += f"\n  → {name}"
    print(line)


def cmd_ini_set(save_dir: Path, section: str, key: str, value: str) -> None:
    path = save_dir / "undertale.ini"
    cp = _read_ini(path)
    key = normalize_key(key)

    if not cp.has_section(section):
        cp.add_section(section)

    # Room 支持中文名称
    actual = resolve_room(value) if key == "Room" else value

    formatted = format_ini_value(actual)
    old_raw = cp.get(section, key, fallback=None)
    old_display = parse_ini_value(old_raw) if old_raw else "(不存在)"

    cp.set(section, key, formatted)
    _write_ini(path, cp)

    new_display = parse_ini_value(formatted)
    msg = f"✓ [{section}] {key}: {old_display} → {new_display}"
    if key == "Room":
        _load_rooms()
        name = ROOMS.get(new_display)
        if name:
            msg += f"  ({name})"
        cmd_file0_set(save_dir, "LOCATION", actual)
    print(msg)


# ============================================================
# file0 Operations  (GameMaker 纯文本序列化格式)
# ============================================================

# ── 核心角色属性 ──────────────────────────────────────────────
# 索引对应 file0 中去掉首行名字后的 0-based 位置
# 数据来源: Flowey's Time Machine research/savefile.md
FILE0_FIELDS = {
    "LOVE": 0,          # LV / 等级
    "LV": 0,
    "HP": 1,            # 当前生命值
    "MAXHP": 2,         # 最大生命值
    "AT": 3,            # 基础攻击
    "WEAPON_AT": 4,     # 武器攻击加成
    "DF": 5,            # 基础防御
    "ARMOR_DF": 6,      # 护甲防御加成
    "EXP": 8,           # 处决点数
    "GOLD": 9,          # 金钱
    "KILLS": 10,        # 总击杀数
}

# ── 物品栏 (8 格 + 手机 + 装备) ─────────────────────────────
INVENTORY_FIELDS = {
    "INV1": 11, "CELL1": 12,
    "INV2": 13, "CELL2": 14,
    "INV3": 15, "CELL3": 16,
    "INV4": 17, "CELL4": 18,
    "INV5": 19, "CELL5": 20,
    "INV6": 21, "CELL6": 22,
    "INV7": 23, "CELL7": 24,
    "INV8": 25, "CELL8": 26,
    "WEAPON": 27,       # 已装备武器
    "ARMOR": 28,         # 已装备护甲
}

# ── BOSS / 怪物状态 ──────────────────────────────────────────
BOSS_FIELDS = {
    "TRAINING_DUMMY": 43,   # 0=初始 1=击杀 2=对话过 3=无聊
    "TORIEL": 74,           # 0=初始 3=? 4=击杀 5=宽恕
    "DOGGO": 81,            # 0=初始 1=击杀 2=宽恕
    "DOGAMY": 82,           # 0=初始 1=击杀 2=宽恕
    "GREATER_DOG": 83,      # 0=初始 1=击杀 2=宽恕 3=无视
    "ICE_CAP": 86,          # 0=初始 2=击杀
    "PAPYRUS": 96,          # 0=初始 1=击杀
    "SHRYREN": 110,         # 0=初始 1=击杀 2=?
    "UNDYNE_1": 280,        # 0=初始 1=击杀 (瀑布追逐)
    "MAD_DUMMY": 281,       # 0=初始 1=击杀
    "UNDYNE_2": 379,        # 0=初始 1=击杀 (竞技场)
    "MUFFET": 426,          # 0=初始 1=击杀
    "ROYAL_GUARDS": 431,    # 0=初始 1=击杀
    "METTATON": 454,        # 0=初始 1=击杀
}

BOSS_STATE_DESC: dict[str, dict[int, str]] = {
    "TORIEL": {0: "初始", 4: "已击杀", 5: "已宽恕"},
    "PAPYRUS": {0: "初始", 1: "已击杀"},
    "UNDYNE_1": {0: "初始", 1: "已击杀"},
    "UNDYNE_2": {0: "初始", 1: "已击杀"},
    "TRAINING_DUMMY": {0: "初始", 1: "已击杀", 2: "已对话", 3: "无聊"},
    "DOGGO": {0: "初始", 1: "已击杀", 2: "已宽恕"},
    "DOGAMY": {0: "初始", 1: "已击杀", 2: "已宽恕"},
    "GREATER_DOG": {0: "初始", 1: "已击杀", 2: "已宽恕", 3: "已无视"},
    "MUFFET": {0: "初始", 1: "已击杀"},
    "METTATON": {0: "初始", 1: "已击杀"},
    "MAD_DUMMY": {0: "初始", 1: "已击杀"},
    "ROYAL_GUARDS": {0: "初始", 1: "已击杀"},
}

# ── 区域击杀数 ───────────────────────────────────────────────
AREA_KILLS_FIELDS = {
    "UNKNOWN_KILLS": 230,
    "RUINS_KILLS": 231,
    "SNOWDIN_KILLS": 232,
    "WATERFALL_KILLS": 233,
    "HOTLAND_KILLS": 234,
}

# ── 特殊旗标 ─────────────────────────────────────────────────
FLAG_FIELDS = {
    "FUN": 34,              # FUN 值 (特殊事件)
    "DEFEATED_ASRIEL": 36,  # 1=已击败小羊 (真和平)
    "EXITED_TRUE_LAB": 522, # 12=已离开真实验室
    "PLOT": 541,            # 剧情值
    "HAVE_CELL": 544,       # 1=有手机
    "LOCATION": 546,        # 房间 ID
    "ROOM": 546,
}

# 合并所有已知字段做快速查找
_ALL_FILE0_FIELDS: dict[str, int] = {}
for _d in [FILE0_FIELDS, INVENTORY_FIELDS, BOSS_FIELDS, AREA_KILLS_FIELDS, FLAG_FIELDS]:
    _ALL_FILE0_FIELDS.update(_d)

# ── 物品系统 ──────────────────────────────────────────────────
ITEMS: dict[int, str] = {
    0: "(空)", 1: "怪物糖果", 2: "Croquet Roll", 3: "树枝",
    4: "绷带", 5: "石头糖果", 6: "南瓜圈", 7: "蜘蛛甜甜圈",
    8: "洋葱(?)", 9: "幽灵果实", 10: "蜘蛛汽水", 11: "奶油肉桂派",
    12: "褪色的缎带", 13: "玩具刀", 14: "坚韧手套", 15: "兄贵头巾",
    16: "雪人块", 17: "好棒冰", 18: "Puppydough 冰淇淋", 19: "情侣棒冰",
    20: "单身狗棒冰", 21: "兔肉桂包", 22: "提米薄片", 23: "遗弃的蛋派",
    24: "老旧的芭蕾舞裙", 25: "芭蕾舞鞋", 26: "击分卡", 27: "神烦狗",
    28: "狗狗沙拉", 29: "狗剩 (1)", 30: "狗剩 (2)", 31: "狗剩 (3)",
    32: "狗剩 (4)", 33: "狗剩 (5)", 34: "狗剩 (6)",
    35: "太空人食物", 36: "方便面", 37: "热狗...?", 38: "热猫",
    39: "魅力汉堡", 40: "海茶", 41: "新星菲特", 42: "传说英雄",
     43: "破损的眼镜", 44: "破损的笔记",
    45: "染血的围裙",
    46: "染色围裙",
    47: "烧焦的平底锅",
    48: "牛仔帽",
    49: "空枪", 50: "心形锁坠", 51: "磨损的刀",
    52: "真刀", 53: "锁坠", 54: "糟糕的回忆", 55: "最终梦想",
    56: "Undyne 的信", 57: "Undyne 的信 EX", 58: "薯片",
    59: "垃圾食品", 60: "神秘钥匙", 61: "脸型牛排", 62: "Hush Puppy",
    63: "蜗牛派",
     64: "提米盔甲",
     65: "Dream Fragment",
}

WEAPON_AT: dict[int, int] = {
    3: 0,   # 树枝
    13: 3,  # 玩具刀
    14: 5,  # 坚韧手套
    25: 7,  # 芭蕾舞鞋
    47: 10, # 烧焦的平底锅
    49: 12, # 空枪
    51: 15, # 磨损的刀
    52: 99, # 真刀
}

ARMOR_DF: dict[int, int] = {
    4: 0,   # 绷带
    12: 3,  # 褪色的缎带
    15: 7,  # 兄贵头巾
    43: 5,  # 破损的眼镜
    45: 7,  # 染血的围裙
    46: 11, # 染色围裙
    48: 12, # 牛仔帽
    50: 15, # 心形锁坠
    53: 99, # 锁坠
    64: 20, # 提米盔甲
}


def _file0_field_name(idx: int) -> str:
    """Return the human-readable name for a file0 index, if known."""
    for name, i in _ALL_FILE0_FIELDS.items():
        if i == idx:
            return name
    return ""


def _file0_field_hint(numbers: list[int], idx: int) -> str:
    """Return a display hint like '<- HP (4)' for a known field."""
    name = _file0_field_name(idx)
    if not name:
        return ""
    val = numbers[idx] if idx < len(numbers) else "?"
    if name in INVENTORY_FIELDS and name.startswith("INV"):
        item_name = ITEMS.get(val, f"未知({val})")
        return f"  ← {name} ({item_name})"
    if name in INVENTORY_FIELDS and name.startswith("CELL"):
        cell_names = {0: "(空)", 201: "打招呼", 202: "帮助解密", 203: "关于你自己",
                      204: "叫她\"妈妈\"", 205: "调情", 206: "托丽尔的手机",
                      210: "帕派瑞斯的手机", 220: "空间箱子 A", 221: "空间箱子 B"}
        label = cell_names.get(val, f"未知({val})")
        return f"  ← {name} ({label})"
    if name == "WEAPON":
        item_name = ITEMS.get(val, f"未知({val})")
        at = WEAPON_AT.get(val)
        return f"  ← {name} ({item_name})" + (f" AT+{at}" if at else "")
    if name == "ARMOR":
        item_name = ITEMS.get(val, f"未知({val})")
        df = ARMOR_DF.get(val)
        return f"  ← {name} ({item_name})" + (f" DF+{df}" if df else "")
    if name in BOSS_FIELDS:
        desc = BOSS_STATE_DESC.get(name, {}).get(val, f"状态 {val}")
        return f"  ← {name} ({desc})"
    if name in AREA_KILLS_FIELDS:
        area_labels = {"UNKNOWN_KILLS": "未知", "RUINS_KILLS": "遗迹",
                        "SNOWDIN_KILLS": "雪镇", "WATERFALL_KILLS": "瀑布",
                        "HOTLAND_KILLS": "热域"}
        area = area_labels.get(name, name)
        return f"  ← {area}击杀"
    return f"  ← {name}"


# ── 文件解析 ─────────────────────────────────────────────────

def _parse_file0(path: Path) -> tuple[str, list[int]]:
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    with open(str(path), "r", encoding="utf-8", newline="") as f:
        lines = f.readlines()
    if not lines:
        raise ValueError("file0 为空")

    name = lines[0].rstrip("\r\n")
    numbers = []
    for line in lines[1:]:
        stripped = line.strip()
        if stripped:
            numbers.append(int(stripped))
    return name, numbers


def _write_file0(path: Path, name: str, numbers: list[int]) -> None:
    backup_file(path)
    with open(str(path), "w", encoding="utf-8", newline="\r\n") as f:
        f.write(name + "\r\n")
        for n in numbers:
            f.write(f"{n} \r\n")


def _resolve_file0_key(key: str) -> int | None:
    """Convert a field name or index string to a file0 index."""
    upper = key.upper()
    if upper in _ALL_FILE0_FIELDS:
        return _ALL_FILE0_FIELDS[upper]
    try:
        return int(key)
    except ValueError:
        return None


# ── 命令实现 ─────────────────────────────────────────────────

def cmd_file0_list(save_dir: Path) -> None:
    path = save_dir / "file0"
    name, numbers = _parse_file0(path)

    print(f"═══ 玩家: {name} ═══")
    print(f"变量总数: {len(numbers)}")

    # 核心属性概览
    core = {k: numbers[v] for k, v in FILE0_FIELDS.items() if v < len(numbers)}
    print(f"  LOVE={core.get('LOVE','?')}  HP={core.get('HP','?')}/{core.get('MAXHP','?')}  "
          f"AT={core.get('AT','?')}  DF={core.get('DF','?')}  "
          f"GOLD={core.get('GOLD','?')}  KILLS={core.get('KILLS','?')}")

    # 装备
    if 27 < len(numbers):
        w = ITEMS.get(numbers[27], f"未知({numbers[27]})")
        a = ITEMS.get(numbers[28], f"未知({numbers[28]})")
        print(f"  武器: {w}  护甲: {a}")

    # 区域击杀
    if len(numbers) > 234:
        print(f"  区域击杀: 遗迹={numbers[231]} 雪镇={numbers[232]} "
              f"瀑布={numbers[233]} 热域={numbers[234]}")

    # BOSS 状态摘要
    boss_line = []
    for name_f, idx in BOSS_FIELDS.items():
        if idx < len(numbers) and numbers[idx] != 0:
            desc = BOSS_STATE_DESC.get(name_f, {}).get(numbers[idx], f"?{numbers[idx]}")
            boss_line.append(f"{name_f}={desc}")
    if boss_line:
        print(f"  BOSS: {', '.join(boss_line)}")

    print(f"\n--- 原始数据 (前 50) ---")
    for i, n in enumerate(numbers[:50]):
        hint = _file0_field_hint(numbers, i)
        print(f"  [{i:3d}] {n}{hint}")
    if len(numbers) > 50:
        print(f"  ... (剩余 {len(numbers) - 50} 个)")
    print("\n提示: 用字段名访问, 如 --key HP; 或用索引, 如 --key 0")


def cmd_file0_get(save_dir: Path, key: str) -> None:
    path = save_dir / "file0"
    _, numbers = _parse_file0(path)

    idx = _resolve_file0_key(key)
    if idx is None:
        known = ", ".join(sorted(_ALL_FILE0_FIELDS.keys(), key=lambda k: _ALL_FILE0_FIELDS[k]))
        raise ValidationError(f"未知字段: '{key}'")

    if not (0 <= idx < len(numbers)):
        raise ValidationError(f"索引 {idx} 越界")

    val = numbers[idx]
    hint = _file0_field_hint(numbers, idx)
    line = f"[{idx}] {val}{hint}" if hint else f"[{idx}] = {val}"
    print(line)


def cmd_file0_find(save_dir: Path, value: str) -> None:
    path = save_dir / "file0"
    _, numbers = _parse_file0(path)

    try:
        target = int(value)
    except ValueError:
        raise ValidationError("搜索值须为整数")

    matches = [(i, n) for i, n in enumerate(numbers) if n == target]
    if not matches:
        print(f"未找到值为 {target} 的变量。")
        return

    print(f"值 {target} 出现在以下位置:")
    for idx, val in matches[:20]:
        hint = _file0_field_hint(numbers, idx)
        print(f"  [{idx}] = {val}{hint}")
    if len(matches) > 20:
        print(f"  ... (共 {len(matches)} 处, 仅显示前 20)")


def cmd_file0_set(save_dir: Path, key: str, value: str) -> None:
    path = save_dir / "file0"
    name, numbers = _parse_file0(path)

    try:
        val = int(value)
    except ValueError:
        raise ValidationError(f"值须为整数: {value}")

    idx = _resolve_file0_key(key)
    if idx is None:
        known = ", ".join(sorted(_ALL_FILE0_FIELDS.keys(), key=lambda k: _ALL_FILE0_FIELDS[k]))
        raise ValidationError(f"未知字段: '{key}'")

    if not (0 <= idx < len(numbers)):
        raise ValidationError(f"索引 {idx} 越界")

    old = numbers[idx]

    # 自动计算 AT/DF: 设置武器/护甲时同步更新加成值
    auto_msg = ""
    upper_key = key.upper()
    if upper_key == "WEAPON":
        at = WEAPON_AT.get(val)
        if at is not None and 4 < len(numbers):
            old_at = numbers[4]
            numbers[4] = at
            auto_msg = f" (WEAPON_AT 同步: {old_at}→{at})"
    elif upper_key == "ARMOR":
        df = ARMOR_DF.get(val)
        if df is not None and 6 < len(numbers):
            old_df = numbers[6]
            numbers[6] = df
            auto_msg = f" (ARMOR_DF 同步: {old_df}→{df})"

    numbers[idx] = val
    hint = _file0_field_hint(numbers, idx)
    _write_file0(path, name, numbers)
    print(f"✓ file0 [{idx}] {key}: {old} → {val}{hint}{auto_msg}")


# ============================================================
# Undo: restore from .bak
# ============================================================

def cmd_undo(save_dir: Path, target: str, backup_ts: str | None = None) -> None:
    files: dict[str, Path] = {
        "ini": save_dir / "undertale.ini",
        "file0": save_dir / "file0",
    }
    key = target.lower()
    if key in ("data_win", "game", "game.ios"):
        try:
            game_file = find_game_data_file()
        except FileNotFoundError as e:
            raise NotFoundError(str(e))
        orig = game_file
    elif key in files:
        orig = files[key]
    else:
        raise ValidationError(f"未知文件: '{target}'")

    if backup_ts:
        bak = orig.with_suffix(orig.suffix + f".bak.{backup_ts}")
    else:
        bak = orig.with_suffix(orig.suffix + ".bak")

    if not bak.exists():
        print(f"没有找到备份文件: {bak}", file=sys.stderr)
        print("可用备份:")
        for b in list_backups(orig):
            print(f"  {b['label']}  ({b['time']}, {b['size']} bytes)")
        return

    shutil.copy2(str(bak), str(orig))
    label = f"{key} ({bak.name})" if key in ("data_win", "game", "game.ios") else key
    print(f"✓ {label} 已从备份恢复: {bak} → {orig}")


def cmd_list_backups(save_dir: Path, target: str) -> None:
    files: dict[str, Path] = {
        "ini": save_dir / "undertale.ini",
        "file0": save_dir / "file0",
    }
    key = target.lower()
    if key in ("data_win", "game", "game.ios"):
        try:
            game_file = find_game_data_file()
        except FileNotFoundError as e:
            raise NotFoundError(str(e))
        orig = game_file
    elif key in files:
        orig = files[key]
    else:
        raise ValidationError(f"未知文件: '{target}'")

    backups = list_backups(orig)
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
    cp = _read_ini(path)
    changes = []

    if cp.has_section("Flowey"):
        for key in cp.options("Flowey"):
            old = cp.get("Flowey", key)
            cp.set("Flowey", key, format_ini_value("0"))
            changes.append(f"[Flowey] {key}: {parse_ini_value(old)} → 0")

    if cp.has_option("General", "Kills"):
        old = cp.get("General", "Kills")
        cp.set("General", "Kills", format_ini_value("0"))
        changes.append(f"[General] Kills: {parse_ini_value(old)} → 0")

    new_fun = random.randint(1, 99)
    if cp.has_option("General", "fun"):
        old = cp.get("General", "fun")
        cp.set("General", "fun", format_ini_value(str(new_fun)))
        changes.append(f"[General] fun: {parse_ini_value(old)} → {new_fun}")

    if changes:
        _write_ini(path, cp)
        print("INI 已重置以下屠杀线标志:")
        for c in changes:
            print(f"  • {c}")
    else:
        print("INI: 未发现需要重置的标志。")

    # 同时清理 file0 中的 Kills
    try:
        f0 = save_dir / "file0"
        if f0.exists():
            name, nums = _parse_file0(f0)
            if len(nums) > 10 and nums[10] != 0:
                old_k = nums[10]
                nums[10] = 0
                _write_file0(f0, name, nums)
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
        raise NotFoundError(f"file0 不存在: {path}")
    name, nums = _parse_file0(path)
    changes = []

    # Reset LOVE, HP, kills, gold, EXP
    if len(nums) > 0:
        old = nums[0]
        nums[0] = 1
        changes.append(f"LOVE: {old} → 1")
    if len(nums) > 1:
        old = nums[1]
        nums[1] = 20
        changes.append(f"HP: {old} → 20")
    if len(nums) > 2:
        old = nums[2]
        nums[2] = 20
        changes.append(f"MAXHP: {old} → 20")
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

    _write_file0(path, name, nums)

    # Update INI
    try:
        ini_path = save_dir / "undertale.ini"
        cp = _read_ini(ini_path)
        changes_ini = []
        if cp.has_section("Flowey"):
            for key in cp.options("Flowey"):
                cp.set("Flowey", key, format_ini_value("0"))
                changes_ini.append(f"[Flowey] {key} → 0")
        if cp.has_option("General", "Kills"):
            old = cp.get("General", "Kills")
            cp.set("General", "Kills", format_ini_value("0"))
            changes_ini.append(f"[General] Kills → {parse_ini_value(old)}")
        if cp.has_option("General", "Love"):
            old = cp.get("General", "Love")
            cp.set("General", "Love", format_ini_value("1"))
            changes_ini.append(f"[General] Love → {parse_ini_value(old)}")
        if changes_ini:
            _write_ini(ini_path, cp)
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
        raise ValidationError("系统信息文件编号必须是 962 或 963")

    fname = f"system_information_{value}"
    path = save_dir / fname
    if path.exists():
        print(f"'{fname}' 已存在。")
        return
    path.touch()
    print(f"✓ 已创建 {fname}  ({'世界已删除' if value == '962' else '已向 Chara 献出灵魂'})")


# ============================================================
# Dialogue Editor Commands (game.ios / data.win) — UTMT CLI
# ============================================================

def cmd_strg_list(game_file: Path, limit: int, offset: int, hex_mode: bool) -> None:
    if offset == 0:
        csx = 'ScriptMessage("COUNT:" + Data.Strings.Count);'
        out = _run_utmt(csx, game_file, save=False)
        for line in _parse_msg(out):
            if line.startswith("COUNT:"):
                print(f"Total strings: {line.split(':', 1)[1]}")
                break
        print(f"{'Index':>6} | Content")
        print("-" * 80)

    if limit > 0:
        csx = f'''
for (int i = {offset}; i < Math.Min(Data.Strings.Count, {offset + limit}); i++) {{
    ScriptMessage("[" + i + "] " + Data.Strings[i].Content);
}}
'''
        out = _run_utmt(csx, game_file, save=False)
        for line in _parse_msg(out):
            print(line)


def cmd_strg_get(game_file: Path, key: int) -> None:
    csx = f'ScriptMessage("[" + {key} + "] " + Data.Strings[{key}].Content);'
    out = _run_utmt(csx, game_file, save=False)
    for line in _parse_msg(out):
        print(line)


def cmd_strg_set(game_file: Path, key: int, value: str) -> None:
    esc = _csx_escape(value)
    csx = f'''
var old = Data.Strings[{key}].Content;
Data.Strings[{key}].Content = "{esc}";
ScriptMessage("[{key}] " + old + " → " + Data.Strings[{key}].Content);
'''
    out = _run_utmt(csx, game_file, save=True)
    for line in _parse_msg(out):
        print(line)


def cmd_strg_add(game_file: Path, value: str) -> None:
    esc = _csx_escape(value)
    csx = f'''
var s = Data.Strings.MakeString("{esc}");
var idx = Data.Strings.IndexOf(s);
ScriptMessage("NEW_INDEX:" + idx);
ScriptMessage("Content: " + Data.Strings[idx].Content);
'''
    out = _run_utmt(csx, game_file, save=True)
    for line in _parse_msg(out):
        print(line)


def cmd_strg_delete(game_file: Path, key: int) -> None:
    csx = f'''
var old = Data.Strings[{key}].Content;
Data.Strings.RemoveAt({key});
ScriptMessage("Deleted [" + {key} + "]: " + old);
'''
    out = _run_utmt(csx, game_file, save=True)
    for line in _parse_msg(out):
        print(line)


def cmd_strg_replace(game_file: Path, old: str, new_val: str) -> None:
    oe = _csx_escape(old)
    ne = _csx_escape(new_val)
    csx = f'''
int count = 0;
for (int i = 0; i < Data.Strings.Count; i++) {{
    if (Data.Strings[i].Content == "{oe}") {{
        Data.Strings[i].Content = "{ne}";
        ScriptMessage("Replaced [" + i + "]: " + "{oe}" + " → " + "{ne}");
        count++;
    }}
}}
ScriptMessage("DONE:" + count + " replacements");
'''
    out = _run_utmt(csx, game_file, save=True)
    for line in _parse_msg(out):
        if line.startswith("DONE:"):
            n = line.split(":", 1)[1].split()[0]
            print(f"已替换 {n} 处")
        else:
            print(line)


def cmd_strg_search(game_file: Path, query: str, limit: int) -> None:
    esc = _csx_escape(query)
    csx = f'''
int found = 0;
for (int i = 0; i < Data.Strings.Count && found < {limit}; i++) {{
    if (Data.Strings[i].Content.IndexOf("{esc}", StringComparison.OrdinalIgnoreCase) >= 0) {{
        ScriptMessage("[" + i + "] " + Data.Strings[i].Content);
        found++;
    }}
}}
ScriptMessage("FOUND:" + found);
'''
    out = _run_utmt(csx, game_file, save=False)
    printed = 0
    for line in _parse_msg(out):
        if line.startswith("FOUND:"):
            total = int(line.split(":", 1)[1])
            label = f" (仅显示前 {limit} 个)" if total > limit else ""
            print(f"找到 {total} 个匹配 '{query}'{label}")
        else:
            print(line)
            printed += 1


# ============================================================
# Code Editor Commands (game.ios / data.win) — UTMT CLI
# ============================================================

def cmd_code_list(game_file: Path, limit: int, offset: int) -> None:
    csx = f'''
ScriptMessage("COUNT:" + Data.Code.Count);
for (int i = {offset}; i < Math.Min(Data.Code.Count, {offset + limit}); i++) {{
    ScriptMessage("[" + i + "] " + Data.Code[i].Name.Content);
}}
'''
    out = _run_utmt(csx, game_file, save=False)
    for line in _parse_msg(out):
        if line.startswith("COUNT:"):
            print(f"Total code entries: {line.split(':', 1)[1]}")
            print(f"{'Index':>6} | Code Name")
            print("-" * 80)
        else:
            print(line)


def cmd_code_decompile(game_file: Path, code_name: str, limit: int = 0, search: str = "") -> None:
    esc = _csx_escape(code_name)
    esc_search = _csx_escape(search)
    filter_lines = "" if not search else f'''
    ScriptMessage("SEARCH:" + "{esc_search}");
    for (int i = 0; i < lines.Length && found < {limit}; i++) {{
        if (lines[i].IndexOf("{esc_search}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            ScriptMessage("  [" + i + "] " + lines[i]);
            found++;
        }}
    }}
    if (found == 0) ScriptMessage("  (no matches)");
    return;
'''
    csx = f'''
var code = Data.Code.ByName("{esc}");
if (code == null) {{
    ScriptMessage("ERROR: Code entry not found: {esc}");
    return;
}}
if (code.ParentEntry != null) {{
    ScriptMessage("SKIP: child entry of " + code.ParentEntry.Name.Content + ", decompile parent instead");
    return;
}}
try {{
    string gml = GetDecompiledText(code);
    var lines = gml.Split(new[] {{ "\\r\\n", "\\r", "\\n" }}, StringSplitOptions.None);
    int total = lines.Length;
    int max = {limit};
    if (max <= 0) max = total;
    int found = 0;
    {filter_lines}
    if (max <= 0) max = total;
    ScriptMessage("LINES:" + total + ":" + (max < total ? max.ToString() : total.ToString()));
    int end = Math.Min(max, total);
    for (int i = 0; i < end; i++) {{
        ScriptMessage(lines[i]);
    }}
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    out = _run_utmt(csx, game_file, save=False)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("SKIP:"):
            print(line, file=sys.stderr)
        elif line.startswith("LINES:"):
            parts = line.split(":")
            total = parts[1]
            shown = parts[2] if len(parts) > 2 else total
            label = f" (仅显示前 {shown} 行)" if int(shown) < int(total) else ""
            print(f"--- 共 {total} 行{label} ---")
        else:
            print(line)


def cmd_code_replace(game_file: Path, code_name: str, value: str, value_is_file: bool = False) -> None:
    """Replace an entire code entry with new GML content.

    value can be:
    - GML source code directly (value_is_file=False)
    - Path to a .gml file (value_is_file=True)
    """
    esc = _csx_escape(code_name)
    gml = _csx_escape(value)

    if value_is_file:
        p = Path(value)
        if not p.exists():
            raise NotFoundError(f"文件不存在: {value}")
        gml = p.read_text(encoding="utf-8")
        esc_gml = _csx_verbatim_escape(gml)
        csx = f'''
var code = Data.Code.ByName("{esc}");
if (code == null) {{
    ScriptMessage("ERROR: Code entry not found: {esc}");
    return;
}}
if (code.ParentEntry != null) {{
    ScriptMessage("SKIP: child entry, replace parent instead");
    return;
}}
try {{
    CodeImportGroup importGroup = new(Data)
    {{
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueueReplace(code, @"{esc_gml}");
    importGroup.Import();
    ScriptMessage("OK: Replaced " + "{esc}");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    else:
        csx = f'''
var code = Data.Code.ByName("{esc}");
if (code == null) {{
    ScriptMessage("ERROR: Code entry not found: {esc}");
    return;
}}
if (code.ParentEntry != null) {{
    ScriptMessage("SKIP: child entry, replace parent instead");
    return;
}}
try {{
    CodeImportGroup importGroup = new(Data)
    {{
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueueReplace(code, "{gml}");
    importGroup.Import();
    ScriptMessage("OK: Replaced " + "{esc}");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    out = _run_utmt(csx, game_file, save=True)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("SKIP:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)
        else:
            print(line)


def cmd_code_find_replace(game_file: Path, code_name: str, old: str, new_val: str) -> None:
    """Find and replace text within a decompiled code entry, then recompile.

    Uses Python-side string replacement (not QueueFindReplace) to avoid
    CSX escaping issues. Writes modified GML to a temp file.
    """
    esc = _csx_escape(code_name)
    # Decompile in C#, send back as tagged lines
    dump_csx = f'''
var code = Data.Code.ByName("{esc}");
if (code == null) {{
    ScriptMessage("ERROR: Code entry not found: {esc}");
    return;
}}
if (code.ParentEntry != null) {{
    ScriptMessage("SKIP: child entry, use parent instead");
    return;
}}
try {{
    string gml = GetDecompiledText(code);
    var lines = gml.Split(new[] {{ "\\r\\n", "\\r", "\\n" }}, StringSplitOptions.None);
    for (int i = 0; i < lines.Length; i++) {{
        ScriptMessage("GML_LINE:" + i + ":" + lines[i]);
    }}
    ScriptMessage("GML_COUNT:" + lines.Length);
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    out = _run_utmt(dump_csx, game_file, save=False)
    lines = _parse_msg(out)
    
    errors = [l for l in lines if l.startswith("ERROR:") or l.startswith("SKIP:")]
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return
    
    # Reconstruct GML from tagged lines
    count_line = next((l for l in lines if l.startswith("GML_COUNT:")), None)
    if count_line is None:
        raise RuntimeError("无法获取反编译结果")
    
    total = int(count_line.split(":")[1])
    gml_lines = []
    for i in range(total):
        tag = f"GML_LINE:{i}:"
        for l in lines:
            if l.startswith(tag):
                gml_lines.append(l[len(tag):])
                break
    
    gml = "\n".join(gml_lines)
    
    # Do the replacement
    replaced_count = gml.count(old)
    if replaced_count == 0:
        raise NotFoundError(f"未找到匹配: '{old}'")
    
    new_gml = gml.replace(old, new_val)
    
    # Write to temp file and use replace-code
    with tempfile.NamedTemporaryFile(mode='w', suffix='.gml', delete=False, encoding='utf-8') as f:
        f.write(new_gml)
        temp_path = f.name
    
    try:
        # Use the file-path mode of replace-code
        cmd_code_replace(game_file, code_name, temp_path, value_is_file=True)
        print(f"已替换 {replaced_count} 处")
    finally:
        Path(temp_path).unlink(missing_ok=True)


def cmd_code_append(game_file: Path, code_name: str, value: str) -> None:
    """Append GML code to the end of an existing code entry."""
    esc = _csx_escape(code_name)
    verb = _csx_verbatim_escape(value)
    csx = f'''
var code = Data.Code.ByName("{esc}");
if (code == null) {{
    ScriptMessage("ERROR: Code entry not found: {esc}");
    return;
}}
if (code.ParentEntry != null) {{
    ScriptMessage("SKIP: child entry, use parent instead");
    return;
}}
try {{
    CodeImportGroup importGroup = new(Data)
    {{
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueueAppend(code, @"{verb}");
    importGroup.Import();
    ScriptMessage("OK: Appended to " + "{esc}");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    out = _run_utmt(csx, game_file, save=True)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("SKIP:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)
        else:
            print(line)


def cmd_code_prepend(game_file: Path, code_name: str, value: str) -> None:
    """Prepend GML code to the beginning of an existing code entry."""
    esc = _csx_escape(code_name)
    verb = _csx_verbatim_escape(value)
    csx = f'''
var code = Data.Code.ByName("{esc}");
if (code == null) {{
    ScriptMessage("ERROR: Code entry not found: {esc}");
    return;
}}
if (code.ParentEntry != null) {{
    ScriptMessage("SKIP: child entry, use parent instead");
    return;
}}
try {{
    CodeImportGroup importGroup = new(Data)
    {{
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueuePrepend(code, @"{verb}");
    importGroup.Import();
    ScriptMessage("OK: Prepended to " + "{esc}");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    out = _run_utmt(csx, game_file, save=True)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("SKIP:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)
        else:
            print(line)


# ============================================================
# Text Data Commands (global.text_data_en map)
# ============================================================

def cmd_textdata_search(game_file: Path, query: str, limit: int) -> None:
    """Search for keys in the textdata_en map."""
    esc = _csx_escape(query)
    csx = f'''
try {{
    string gml = GetDecompiledText(Data.Code.ByName("gml_Script_textdata_en"));
    var lines = gml.Split(new[] {{ "\\r\\n", "\\r", "\\n" }}, StringSplitOptions.None);
    int found = 0;
    for (int i = 0; i < lines.Length && found < {limit}; i++) {{
        if (lines[i].IndexOf("{esc}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            ScriptMessage(lines[i]);
            found++;
        }}
    }}
    if (found == 0) {{
        ScriptMessage("(no matches)");
    }}
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    out = _run_utmt(csx, game_file, save=False)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        else:
            print(line)


def _validate_facechoice(face: int) -> None:
    if face not in FACE_CHOICES:
        choices = ", ".join(f"{k}={v}" for k, v in FACE_CHOICES.items())
        print(f"警告: facechoice={face} 超出有效范围 (0-9)", file=sys.stderr)
        print(f"  可用: {choices}", file=sys.stderr)


def _inject_face_control(value: str, face: int, emotion: int) -> str:
    """Prepend \\F{face}\\E{emotion} control codes to dialogue text."""
    if face < 0 or face > 9:
        return value
    if face == 0:
        return value  # no face
    return f"\\F{face}\\E{emotion}{value}"


def cmd_textdata_add(game_file: Path, key: str, value: str,
                     face: int = 0, emotion: int = 0) -> None:
    """Add a new key-value pair to the textdata_en map.

    This modifies gml_Script_textdata_en to append a new ds_map_add line.
    The value is also added to the STRG table.
    """
    _validate_facechoice(face)
    value = _inject_face_control(value, face, emotion)

    # Validate dialogue format
    if not any(value.rstrip("\n\r ").endswith(s) for s in ["/", "/%%", "%%%", "\\C ", "\\C", "/%"]):
        print("警告: 对话文本应使用标准格式结尾", file=sys.stderr)
        print("  中间页: 以 / 结尾", file=sys.stderr)
        print("  末页: 以 /%% 结尾", file=sys.stderr)
        print("  选择: 以 \\C 结尾", file=sys.stderr)

    esc_key = _csx_escape(key)
    esc_val = _csx_escape(value)

    # First add the value string to STRG table
    strg_csx = f'''
var s = Data.Strings.MakeString("{esc_val}");
ScriptMessage("STRG_INDEX:" + Data.Strings.IndexOf(s));
'''
    out = _run_utmt(strg_csx, game_file, save=True)
    strg_idx = None
    for line in _parse_msg(out):
        if line.startswith("STRG_INDEX:"):
            strg_idx = line.split(":", 1)[1]

    if strg_idx is None:
        raise RuntimeError("无法获取 STRG 索引")

    v_key = _csx_verbatim_escape(key)
    v_val = _csx_verbatim_escape(value)
    code_csx = f'''
try {{
    string gml = GetDecompiledText(Data.Code.ByName("gml_Script_textdata_en"));
    if (gml.IndexOf(@"ds_map_add(global.text_data_en, ""{v_key}"", ") >= 0) {{
        ScriptMessage("WARN: Key '" + "{esc_key}" + "' already exists, skipping (use delete-textentry first)");
        return;
    }}
    gml = gml.TrimEnd() + "\\r\\n" + @"ds_map_add(global.text_data_en, ""{v_key}"", ""{v_val}"");";

    CodeImportGroup importGroup = new(Data)
    {{
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueueReplace(Data.Code.ByName("gml_Script_textdata_en"), gml);
    importGroup.Import();
    ScriptMessage("OK: Added textdata entry '" + "{esc_key}" + "' (STRG idx " + "{strg_idx}" + ")");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    out = _run_utmt(code_csx, game_file, save=True)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)


def cmd_textdata_delete(game_file: Path, key: str) -> None:
    """Delete a key-value pair from the textdata_en map.

    This searches for ds_map_add(global.text_data_en, "key", ...) and removes the line.
    """
    v_key = _csx_verbatim_escape(key)
    esc_key = _csx_escape(key)
    csx = f'''
try {{
    string gml = GetDecompiledText(Data.Code.ByName("gml_Script_textdata_en"));
    string search = @"ds_map_add(global.text_data_en, ""{v_key}"", ";
    var lines = gml.Split(new[] {{ "\\r\\n", "\\r", "\\n" }}, StringSplitOptions.None);
    System.Text.StringBuilder sb = new System.Text.StringBuilder();
    int removed = 0;
    for (int i = 0; i < lines.Length; i++) {{
        if (lines[i].TrimStart().StartsWith(search)) {{
            removed++;
        }} else {{
            if (sb.Length > 0) sb.Append("\\r\\n");
            sb.Append(lines[i]);
        }}
    }}
    if (removed == 0) {{
        ScriptMessage("ERROR: No entry found for key '{esc_key}'");
        return;
    }}
    string newGml = sb.ToString();
    CodeImportGroup importGroup = new(Data)
    {{
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueueReplace(Data.Code.ByName("gml_Script_textdata_en"), newGml);
    importGroup.Import();
    ScriptMessage("OK: Removed " + removed + " entry(s) for '" + "{esc_key}" + "'");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    out = _run_utmt(csx, game_file, save=True)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)


# ============================================================
# Variable Search (search for variable usage across all code)
# ============================================================

def cmd_search_vars(game_file: Path, query: str, limit: int) -> None:
    """Search for a variable name across all decompiled code entries."""
    esc = _csx_escape(query)
    csx = f'''
int found = 0;
int totalCodes = Data.Code.Count;
ScriptMessage("SCANNING:" + totalCodes);
for (int ci = 0; ci < totalCodes && found < {limit}; ci++) {{
    try {{
        string gml = GetDecompiledText(Data.Code[ci]);
        if (gml.IndexOf("{esc}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            string name = Data.Code[ci].Name.Content;
            // Extract first matching line
            var lines = gml.Split(new[] {{ "\\r\\n", "\\r", "\\n" }}, StringSplitOptions.None);
            for (int li = 0; li < lines.Length; li++) {{
                if (lines[li].IndexOf("{esc}", StringComparison.OrdinalIgnoreCase) >= 0) {{
                    ScriptMessage("[" + ci + "] " + name + ": " + lines[li].Trim());
                    break;
                }}
            }}
            found++;
        }}
    }} catch {{ }}
}}
if (found == 0) {{
    ScriptMessage("(no matches)");
}}
'''
    out = _run_utmt(csx, game_file, save=False)
    for line in _parse_msg(out):
        if line.startswith("SCANNING:"):
            total = line.split(":", 1)[1]
            print(f"Scanning {total} code entries...")
        elif line.startswith("(no"):
            print(line)
        else:
            print(line)


# ============================================================
# Script Management (create new code entries)
# ============================================================

def cmd_create_script(game_file: Path, code_name: str, value: str, value_is_file: bool = False) -> None:
    """Create a new code entry (script) with given GML content.

    If the name follows the convention gml_Object_{name}_{event}_{subtype},
    the script is automatically linked to the object's event.
    Use gml_Script_{name} for new reusable scripts.
    """
    esc_name = _csx_escape(code_name)
    gml_source = value

    if value_is_file:
        p = Path(value)
        if not p.exists():
            raise NotFoundError(f"文件不存在: {value}")
        gml_source = p.read_text(encoding="utf-8")

    # Check if the code entry already exists
    check_csx = f'''
var existing = Data.Code.ByName("{esc_name}");
if (existing != null) {{
    ScriptMessage("EXISTS:" + existing.Name.Content);
}} else {{
    ScriptMessage("NOT_EXISTS");
}}
'''
    out = _run_utmt(check_csx, game_file, save=False)
    for line in _parse_msg(out):
        if line.startswith("EXISTS:"):
            print(f"警告: 代码 '{code_name}' 已存在，将覆盖", file=sys.stderr)

    esc_gml = _csx_verbatim_escape(gml_source)
    csx = f'''
try {{
    CodeImportGroup importGroup = new(Data)
    {{
        AutoCreateAssets = true,
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueueReplace("{esc_name}", @"{esc_gml}");
    importGroup.Import();
    ScriptMessage("OK: Created/replaced " + "{esc_name}");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    out = _run_utmt(csx, game_file, save=True)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)


# ============================================================
# Room Object Inspector (list objects in a specific room)
# ============================================================

def cmd_room_objects(game_file: Path, room_name: str) -> None:
    """List all object instances in a room by its internal name."""
    esc = _csx_escape(room_name)
    csx = f'''
bool found = false;
for (int r = 0; r < Data.Rooms.Count; r++) {{
    var room = Data.Rooms[r];
    if (room.Name.Content.IndexOf("{esc}", StringComparison.OrdinalIgnoreCase) >= 0) {{
        found = true;
        ScriptMessage("Room[" + r + "]: " + room.Name.Content);
        foreach (var go in room.GameObjects) {{
            string objName = go.ObjectDefinition?.Name?.Content ?? "(unknown)";
            ScriptMessage("  [" + go.InstanceID + "] " + objName + " at (" + go.X + "," + go.Y + ")");
            // Show code events for this object
            string objDefName = "gml_Object_" + objName + "_";
            bool hasAny = false;
            foreach (var code in Data.Code) {{
                string cname = code.Name.Content;
                if (cname.StartsWith(objDefName)) {{
                    if (!hasAny) {{ ScriptMessage("    Events:"); hasAny = true; }}
                    string evt = cname.Substring(objDefName.Length);
                    ScriptMessage("      " + evt);
                }}
            }}
        }}
    }}
}}
if (!found) {{
    ScriptMessage("(no matching room found)");
}}
'''
    out = _run_utmt(csx, game_file, save=False)
    for line in _parse_msg(out):
        print(line)


# ============================================================
# Room Object Spawn/Remove (room layout editing)
# ============================================================

def cmd_spawn_obj(game_file: Path, room_name: str, obj_name: str, x: int, y: int) -> None:
    """Spawn an object instance in a room at given coordinates."""
    esc_room = _csx_escape(room_name)
    esc_obj = _csx_escape(obj_name)
    csx = f'''
var room = Data.Rooms.ByName("{esc_room}");
if (room == null) {{
    for (int r = 0; r < Data.Rooms.Count; r++) {{
        if (Data.Rooms[r].Name.Content.IndexOf("{esc_room}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            room = Data.Rooms[r];
            break;
        }}
    }}
}}
if (room == null) {{
    ScriptMessage("ERROR: Room not found: {esc_room}");
    // Suggest similar rooms
    string suggest = "";
    int found = 0;
    for (int r = 0; r < Data.Rooms.Count && found < 5; r++) {{
        string rn = Data.Rooms[r].Name.Content;
        if (rn.IndexOf("{esc_room}", StringComparison.OrdinalIgnoreCase) >= 0 ||
            "{esc_room}".IndexOf(rn, StringComparison.OrdinalIgnoreCase) >= 0) {{
            suggest += (found > 0 ? ", " : "") + rn;
            found++;
        }}
    }}
    if (found > 0) ScriptMessage("HINT: Did you mean: " + suggest);
    return;
}}
var objDef = Data.GameObjects.ByName("{esc_obj}");
if (objDef == null) {{
    for (int o = 0; o < Data.GameObjects.Count; o++) {{
        if (Data.GameObjects[o].Name.Content.IndexOf("{esc_obj}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            objDef = Data.GameObjects[o];
            break;
        }}
    }}
}}
if (objDef == null) {{
    ScriptMessage("ERROR: Object not found: {esc_obj}");
    // Suggest similar objects
    string suggest = "";
    int found = 0;
    for (int o = 0; o < Data.GameObjects.Count && found < 5; o++) {{
        string on = Data.GameObjects[o].Name.Content;
        if (on.IndexOf("{esc_obj}", StringComparison.OrdinalIgnoreCase) >= 0 ||
            "{esc_obj}".IndexOf(on, StringComparison.OrdinalIgnoreCase) >= 0) {{
            suggest += (found > 0 ? ", " : "") + on;
            found++;
        }}
    }}
    if (found > 0) ScriptMessage("HINT: Did you mean: " + suggest);
    return;
}}
uint newId = Data.GeneralInfo.LastObj++;
room.GameObjects.Add(new UndertaleRoom.GameObject() {{
    InstanceID = newId,
    ObjectDefinition = objDef,
    X = {x},
    Y = {y}
}});
string objName = objDef.Name?.Content ?? "(unknown)";
string rName = room.Name?.Content ?? "(unknown)";
ScriptMessage("OK: Spawned [" + newId + "] " + objName + " in " + rName + " at ({x}, {y})");
'''
    out = _run_utmt(csx, game_file, save=True)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("HINT:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)
        else:
            print(line)


def cmd_remove_obj(game_file: Path, room_name: str, obj_name: str,
                   instance_id: int | None = None, remove_all: bool = False) -> None:
    """Remove an object instance from a room.

    If instance_id is given, remove that specific instance.
    Otherwise, remove by object name (first match unless --all).
    """
    if instance_id is not None:
        esc_room = _csx_escape(room_name)
        csx = f'''
var room = Data.Rooms.ByName("{esc_room}");
if (room == null) {{
    for (int r = 0; r < Data.Rooms.Count; r++) {{
        if (Data.Rooms[r].Name.Content.IndexOf("{esc_room}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            room = Data.Rooms[r];
            break;
        }}
    }}
}}
if (room == null) {{
    ScriptMessage("ERROR: Room not found: {esc_room}");
    return;
}}
var target = room.GameObjects.ByInstanceID({instance_id});
if (target == null) {{
    ScriptMessage("ERROR: Instance [{instance_id}] not found in " + (room.Name?.Content ?? "(unknown)"));
    return;
}}
string objName = target.ObjectDefinition?.Name?.Content ?? "(unknown)";
room.GameObjects.Remove(target);
ScriptMessage("OK: Removed [" + {instance_id} + "] " + objName + " from " + (room.Name?.Content ?? "(unknown)"));
'''
    else:
        esc_room = _csx_escape(room_name)
        esc_obj = _csx_escape(obj_name)
        remove_all_flag = "true" if remove_all else "false"
        csx = f'''
var room = Data.Rooms.ByName("{esc_room}");
if (room == null) {{
    for (int r = 0; r < Data.Rooms.Count; r++) {{
        if (Data.Rooms[r].Name.Content.IndexOf("{esc_room}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            room = Data.Rooms[r];
            break;
        }}
    }}
}}
if (room == null) {{
    ScriptMessage("ERROR: Room not found: {esc_room}");
    return;
}}
var objDef = Data.GameObjects.ByName("{esc_obj}");
if (objDef == null) {{
    for (int o = 0; o < Data.GameObjects.Count; o++) {{
        if (Data.GameObjects[o].Name.Content.IndexOf("{esc_obj}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            objDef = Data.GameObjects[o];
            break;
        }}
    }}
}}
if (objDef == null) {{
    ScriptMessage("ERROR: Object not found: {esc_obj}");
    return;
}}
int removed = 0;
bool removeAll = {remove_all_flag};
if (removeAll) {{
    for (int i = room.GameObjects.Count - 1; i >= 0; i--) {{
        if (room.GameObjects[i].ObjectDefinition == objDef) {{
            room.GameObjects.RemoveAt(i);
            removed++;
        }}
    }}
}} else {{
    for (int i = 0; i < room.GameObjects.Count; i++) {{
        if (room.GameObjects[i].ObjectDefinition == objDef) {{
            room.GameObjects.RemoveAt(i);
            removed++;
            break;
        }}
    }}
}}
string objName = objDef.Name?.Content ?? "(unknown)";
string rName = room.Name?.Content ?? "(unknown)";
ScriptMessage("OK: Removed " + removed + " instance(s) of " + objName + " from " + rName);
'''
    out = _run_utmt(csx, game_file, save=True)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)
        else:
            print(line)


# ============================================================
# SCR_TEXT Case Viewer (search for text cases in SCR_TEXT)
# ============================================================

def cmd_search_sctext(game_file: Path, query: str, limit: int) -> None:
    """Search for cases in SCR_TEXT that contain a given text."""
    esc = _csx_escape(query)
    csx = f'''
try {{
    string gml = GetDecompiledText(Data.Code.ByName("gml_Script_SCR_TEXT"));
    var lines = gml.Split(new[] {{ "\\r\\n", "\\r", "\\n" }}, StringSplitOptions.None);
    int found = 0;
    string curCase = "";
    for (int i = 0; i < lines.Length && found < {limit}; i++) {{
        string trimmed = lines[i].Trim();
        if (trimmed.StartsWith("case ")) curCase = trimmed;
        if (trimmed.IndexOf("{esc}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            ScriptMessage("--- [" + curCase + "] ---");
            int ctxStart = Math.Max(0, i - 2);
            int ctxEnd = Math.Min(lines.Length - 1, i + 2);
            for (int j = ctxStart; j <= ctxEnd; j++) {{
                ScriptMessage("  " + lines[j]);
            }}
            found++;
        }}
    }}
    if (found == 0) ScriptMessage("(no matches)");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    out = _run_utmt(csx, game_file, save=False)
    for line in _parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        else:
            print(line)


# ============================================================
# Quest Management Commands
# ============================================================

def cmd_quest_init(save_dir: Path, flag_idx: int = FLAG_CUSTOM_START) -> None:
    """Reset a quest flag to initial state (0)."""
    if not (0 <= flag_idx <= FLAG_INDEX_MAX):
        raise ValidationError(f"flag 索引 {flag_idx} 超出范围")
    f0 = save_dir / "file0"
    if not f0.exists():
        raise NotFoundError(f"file0 不存在: {f0}")
    name, nums = _parse_file0(f0)
    file0_idx = 29 + flag_idx
    if file0_idx >= len(nums):
        raise ValidationError(f"flag[{flag_idx}] 越界")
    old = nums[file0_idx]
    nums[file0_idx] = 0
    _write_file0(f0, name, nums)
    print(f"✓ flag[{flag_idx}]: {old} → 0 (已重置为初始状态)")


def cmd_quest_status(save_dir: Path) -> None:
    """Show status of custom quest flags."""
    f0 = save_dir / "file0"
    if not f0.exists():
        raise NotFoundError(f"file0 不存在: {f0}")
    _, nums = _parse_file0(f0)
    for flag_idx in (FLAG_CUSTOM_START, FLAG_CUSTOM_END):
        file0_idx = 29 + flag_idx
        val = nums[file0_idx] if file0_idx < len(nums) else "?"
        label = f"flag[{flag_idx}]"
        desc = ""
        if flag_idx == FLAG_CUSTOM_START:
            desc = " (自定义状态机: 0=未开始, 1+=阶段)"
        elif flag_idx == FLAG_CUSTOM_END:
            desc = " (备用)"
        print(f"  {label} = {val}{desc}")
    # Try to find nearby unused flags
    unused = []
    for fi in range(0, FLAG_INDEX_MAX + 1):
        idx = 29 + fi
        if idx < len(nums) and nums[idx] == 0:
            unused.append(fi)
    print(f"  空闲 flag 索引: {len(unused)} 个 (0-{FLAG_INDEX_MAX})")
    if unused:
        print(f"  例: {unused[:10]}{'...' if len(unused) > 10 else ''}")


# ============================================================
# Batch Textdata Import
# ============================================================

def cmd_batch_textdata(game_file: Path, json_path: str,
                        face: int = 0, emotion: int = 0) -> None:
    """Batch import dialogue entries from a JSON file.

    JSON format: [{"key": "...", "text": "..."}, ...]
    """
    p = Path(json_path)
    if not p.exists():
        raise NotFoundError(f"文件不存在: {json_path}")
    try:
        with open(str(p), "r", encoding="utf-8") as f:
            entries = json.load(f)
    except (json.JSONDecodeError, Exception) as e:
        raise ValidationError(f"JSON 解析失败: {e}")
    
    if not isinstance(entries, list):
        raise ValidationError("JSON 必须是数组格式")
    
    for entry in entries:
        key = entry.get("key", "")
        text = entry.get("text", "")
        entry_face = entry.get("face", face)
        entry_emotion = entry.get("emotion", emotion)
        if not key or not text:
            print(f"跳过无效条目: {entry}", file=sys.stderr)
            continue
        _validate_facechoice(entry_face)
        text = _inject_face_control(text, entry_face, entry_emotion)
        print(f"  → {key}...", end="", flush=True)
        cmd_textdata_add(game_file, key, text, face=0, emotion=0)
        print()

    print(f"✓ 批量导入完成: {len(entries)} 条")


# ============================================================
# Main
# ============================================================

def cmd_room_list(args_filter: str = "") -> None:
    _load_rooms()
    items = sorted(ROOMS.items(), key=lambda x: int(x[0]))
    for rid, name in items:
        if args_filter:
            if args_filter.lower() in name.lower():
                pass
            elif args_filter == rid or (args_filter.isdigit() and int(args_filter) == int(rid)):
                pass
            else:
                continue
        print(f"  [{rid:>3}] {name}")


def main():
    parser = argparse.ArgumentParser(
        description="UNDERTALE Save Editor — 修改 undertale.ini / file0",
        epilog="""
示例:
  %(prog)s --action get  --key Love
  %(prog)s --action set  --key LOVE --value 20
  %(prog)s --action set  --key Kills --value 0
  %(prog)s --action set  --key Room --value 31
  %(prog)s --action set  --key Room --value "安黛因竞技场"
  %(prog)s --action list
  %(prog)s --action room-list
  %(prog)s --action room-list --value 瀑布
  %(prog)s --action reset-flags
  %(prog)s --action reset-all   # 全量重置（BOSS、物品、击杀、plot），保留自定义 flag
  %(prog)s --action set  --key HP  --value 99 --file file0
  %(prog)s --action get  --key HP  --file file0
  %(prog)s --action list --file file0
  %(prog)s --action set  --key WEAPON --value 51 --file file0   (自动 AT=99)
  %(prog)s --action set  --key TORIEL --value 5 --file file0    (宽恕)
  %(prog)s --action set  --key RUINS_KILLS --value 20 --file file0
  %(prog)s --action create-system-info --value 962
  
  # Dialogue editing (game.ios / data.win) — via UndertaleModTool
  %(prog)s --action list-strings --file data_win --limit 10
  %(prog)s --action get-string --key 500 --file data_win
  %(prog)s --action set-string --key 500 --value "Hello" --file data_win
  %(prog)s --action add-string --value "新对话内容" --file data_win
  %(prog)s --action delete-string --key 50000 --file data_win
  %(prog)s --action search-strings --value "Toriel" --file data_win
  %(prog)s --action replace-string --old "Toriel" --value "TORIEL" --file data_win
  
  # Code editing (game.ios / data.win) — via UndertaleModTool
  %(prog)s --action list-codes --file data_win --limit 10
  %(prog)s --action decompile-code --key "gml_Object_obj_dialoguer_Create_0" --file data_win
  %(prog)s --action replace-code --key "gml_Script_test" --value "return 0;" --file data_win
  %(prog)s --action replace-code --key "gml_Script_test" --value "./mycode.gml" --file-path --file data_win
  %(prog)s --action find-replace-code --key "gml_Object_obj_dialoguer_Step_0" --old "old_code" --value "new_code" --file data_win
  
  # Text data editing (game.ios / data.win) — via UndertaleModTool
  %(prog)s --action search-textdata --value "darksans1" --file data_win
  %(prog)s --action add-textentry --key "obj_myevent_001" --value "我的新对话/" --file data_win
  %(prog)s --action delete-textentry --key "obj_test_entry" --file data_win
  
  # Variable/code search
  %(prog)s --action search-vars --value "global.flag" --file data_win
  %(prog)s --action create-script --key "gml_Script_myFunc" --value "return 0;" --file data_win
  
  # Room inspection
  %(prog)s --action room-objects --value "torielroom" --file data_win

  # Room layout editing
  %(prog)s --action spawn-obj --value "room_asrielroom" --key "obj_dummy1" --x 160 --y 120 --file data_win
  %(prog)s --action remove-obj --value "room_asrielroom" --instance 113930 --file data_win
  %(prog)s --action remove-obj --value "room_asrielroom" --key "obj_dummy1" --all --file data_win

  # Code append/prepend (新增，无需完全替换)
  %(prog)s --action append-code --key "gml_Object_obj_dummy1_Step_0" --value "if (global.flag[510]==99) instance_destroy();" --file data_win
  %(prog)s --action prepend-code --key "gml_Object_obj_dummy1_Step_0" --value "// custom code here" --file data_win

  # Batch import dialogues from JSON
  %(prog)s --action batch-add-textentry --value "./dialogues.json" --face 3 --file data_win

  # Quest management
  %(prog)s --action quest-init
  %(prog)s --action quest-init --flag 511
  %(prog)s --action quest-status

  # SCR_TEXT case search
  %(prog)s --action search-sctext --value "Toriel" --file data_win
  
  # Backups
  %(prog)s --action list-backups --value data_win
  %(prog)s --action undo --value data_win --backup 20240714_193500
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--action", required=True,
                        choices=["get", "set", "list", "find", "reset-flags", "reset-all",
                                 "room-list", "create-system-info", "undo",
                                 "list-backups",
                                 "list-strings", "get-string", "set-string",
                                 "add-string", "delete-string",
                                 "replace-string", "search-strings",
                                 "list-codes", "decompile-code",
                                 "replace-code", "find-replace-code",
                                 "append-code", "prepend-code",
                                 "search-textdata", "add-textentry", "delete-textentry",
                                 "batch-add-textentry",
                                 "search-vars", "create-script",
                                 "room-objects", "search-sctext",
                                  "spawn-obj", "remove-obj",
                                  "quest-init", "quest-status",
                                  "sandbox-restore"])
    parser.add_argument("--key", help="键名或数字索引 (file0 用数字)")
    parser.add_argument("--value", help="要设置/搜索的值 (set/find 操作必需)")
    parser.add_argument("--old", help="replace-string 的旧文本")
    parser.add_argument("--section", default="General",
                        help="INI 节名 (默认: General)")
    parser.add_argument("--file", choices=["ini", "file0", "data_win"], default="ini",
                        help="目标文件 (默认: ini)")
    parser.add_argument("--dir", help="手动指定存档目录或游戏数据文件路径")
    parser.add_argument("--limit", type=int, default=30,
                        help="最大显示条数 (默认: 30)")
    parser.add_argument("--offset", type=int, default=0,
                        help="起始偏移 (list-strings 用)")
    parser.add_argument("--hex", action="store_true",
                        help="显示十六进制 (list-strings 用)")
    parser.add_argument("--file-path", action="store_true",
                        help="--value 是文件路径而非内联内容 (replace-code 用)")
    parser.add_argument("--backup", type=str, default=None,
                        help="备份时间戳 (undo 恢复到指定版本, list-backups 可查看)")
    parser.add_argument("--x", type=int, default=320,
                        help="X 坐标 (spawn-obj 用, 默认: 320)")
    parser.add_argument("--y", type=int, default=240,
                        help="Y 坐标 (spawn-obj 用, 默认: 240)")
    parser.add_argument("--all", action="store_true",
                        help="移除所有匹配实例 (remove-obj 用)")
    parser.add_argument("--instance", type=int, default=None,
                        help="实例 ID (remove-obj 用, 优先级高于 --key 匹配)")
    parser.add_argument("--face", type=int, default=0,
                        help="头像角色 (0=无, 1=Toriel, 2=Flowey, 3=Sans, 4=Papyrus, 5=Undyne, 6=Alphys, 7=Asgore, 8=Mettaton, 9=Asriel)")
    parser.add_argument("--emotion", type=int, default=0,
                        help="头像表情 (Sans: 0=普通, 1=轻笑, 2=眨眼, 3=慢眨眼, 4=无眼)")
    parser.add_argument("--flag", type=int, default=None,
                        help="flag 索引 (quest-init 用, 默认 510)")
    parser.add_argument("--sandbox", action="store_true",
                        help="沙箱模式: 在 game.ios.sandbox 副本上操作，不修改原文件")
    args = parser.parse_args()

    # Activate sandbox mode
    if args.sandbox:
        global SANDBOX_ACTIVE
        SANDBOX_ACTIVE = True

    # Handle sandbox-restore before file-type checks
    if args.action == "sandbox-restore":
        try:
            game_file = find_game_data_file(args.dir)
            sandbox_path = game_file.with_suffix(game_file.suffix + ".sandbox")
            if not sandbox_path.exists():
                print(f"错误: 沙箱备份不存在: {sandbox_path}", file=sys.stderr)
                sys.exit(1)
            shutil.copy2(str(sandbox_path), str(game_file))
            sandbox_path.unlink()
            print(f"✓ 沙箱备份已恢复: {sandbox_path.name} → {game_file.name}")
        except FileNotFoundError as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # ── Dialogue editor actions (data_win) ────────────────
    if args.file == "data_win":
        try:
            game_file = find_game_data_file(args.dir)
        except FileNotFoundError as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)

        if SANDBOX_ACTIVE:
            sandbox_path = game_file.with_suffix(game_file.suffix + ".sandbox")
            print(f"🔒 沙箱模式: 所有操作作用于 {sandbox_path.name}", file=sys.stderr)

        try:
            if args.action == "list-strings":
                cmd_strg_list(game_file, args.limit, args.offset, args.hex)
            elif args.action == "get-string":
                if args.key is None:
                    parser.error("--key 是必需的 (字符串索引)")
                cmd_strg_get(game_file, int(args.key))
            elif args.action == "set-string":
                if args.key is None or args.value is None:
                    parser.error("--key 和 --value 是必需的")
                cmd_strg_set(game_file, int(args.key), args.value)
            elif args.action == "add-string":
                if args.value is None:
                    parser.error("--value 是必需的 (新对话文本)")
                cmd_strg_add(game_file, args.value)
            elif args.action == "delete-string":
                if args.key is None:
                    parser.error("--key 是必需的 (要删除的索引)")
                cmd_strg_delete(game_file, int(args.key))
            elif args.action == "replace-string":
                if args.old is None or args.value is None:
                    parser.error("--old 和 --value 是必需的")
                cmd_strg_replace(game_file, args.old, args.value)
            elif args.action == "search-strings":
                if args.value is None:
                    parser.error("--value 是必需的 (搜索关键词)")
                cmd_strg_search(game_file, args.value, args.limit)
            elif args.action == "list-codes":
                cmd_code_list(game_file, args.limit, args.offset)
            elif args.action == "decompile-code":
                if args.key is None:
                    parser.error("--key 是必需的 (代码名称)")
                cmd_code_decompile(game_file, args.key, args.limit, search=args.old or "")
            elif args.action == "replace-code":
                if args.key is None or args.value is None:
                    parser.error("--key 和 --value 是必需的 (代码名称 + GML 源码或文件路径)")
                cmd_code_replace(game_file, args.key, args.value, value_is_file=args.file_path)
            elif args.action == "find-replace-code":
                if args.key is None or args.old is None or args.value is None:
                    parser.error("--key, --old 和 --value 是必需的")
                cmd_code_find_replace(game_file, args.key, args.old, args.value)
            elif args.action == "search-textdata":
                if args.value is None:
                    parser.error("--value 是必需的 (搜索关键词)")
                cmd_textdata_search(game_file, args.value, args.limit)
            elif args.action == "add-textentry":
                if args.key is None or args.value is None:
                    parser.error("--key 和 --value 是必需的")
                cmd_textdata_add(game_file, args.key, args.value,
                                 face=args.face, emotion=args.emotion)
            elif args.action == "delete-textentry":
                if args.key is None:
                    parser.error("--key 是必需的 (要删除的 textdata key)")
                cmd_textdata_delete(game_file, args.key)
            elif args.action == "search-vars":
                if args.value is None:
                    parser.error("--value 是必需的 (变量名)")
                cmd_search_vars(game_file, args.value, args.limit)
            elif args.action == "room-objects":
                if args.value is None:
                    parser.error("--value 是必需的 (房间内部名，如 torielroom)")
                cmd_room_objects(game_file, args.value)
            elif args.action == "create-script":
                if args.key is None or args.value is None:
                    parser.error("--key 和 --value 是必需的 (代码名 + GML 源码或文件路径)")
                cmd_create_script(game_file, args.key, args.value, value_is_file=args.file_path)
            elif args.action == "search-sctext":
                if args.value is None:
                    parser.error("--value 是必需的 (搜索关键词)")
                cmd_search_sctext(game_file, args.value, args.limit)
            elif args.action == "spawn-obj":
                if args.value is None or args.key is None:
                    parser.error("--value (房间名) 和 --key (对象名) 是必需的")
                cmd_spawn_obj(game_file, args.value, args.key, args.x, args.y)
            elif args.action == "remove-obj":
                if args.value is None:
                    parser.error("--value 是必需的 (房间名)")
                if args.instance is None and args.key is None:
                    parser.error("--instance (实例 ID) 或 --key (对象名) 是必需的")
                cmd_remove_obj(game_file, args.value, args.key or "",
                               instance_id=args.instance, remove_all=args.all)
            elif args.action == "append-code":
                if args.key is None or args.value is None:
                    parser.error("--key (代码名) 和 --value (GML) 是必需的")
                cmd_code_append(game_file, args.key, args.value)
            elif args.action == "prepend-code":
                if args.key is None or args.value is None:
                    parser.error("--key (代码名) 和 --value (GML) 是必需的")
                cmd_code_prepend(game_file, args.key, args.value)
            elif args.action == "batch-add-textentry":
                if args.value is None:
                    parser.error("--value 是必需的 (JSON 文件路径)")
                cmd_batch_textdata(game_file, args.value,
                                   face=args.face, emotion=args.emotion)
            else:
                parser.error(f"'{args.action}' 不支持 data_win 文件")
        except (FileNotFoundError, ValueError, IndexError, RuntimeError, DeterlineError) as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # ── Save editor actions (ini / file0) ────────────────
    try:
        save_dir = find_save_dir(args.dir)
    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        if args.file == "file0":
            if args.action == "list":
                cmd_file0_list(save_dir)
            elif args.action == "find":
                if args.value is None:
                    parser.error("--value 是必需的 (搜索目标值)")
                cmd_file0_find(save_dir, args.value)
            elif args.action == "get":
                if not args.key:
                    parser.error("--key 是必需的")
                cmd_file0_get(save_dir, args.key)
            elif args.action == "set":
                if not args.key or args.value is None:
                    parser.error("--key 和 --value 是必需的")
                cmd_file0_set(save_dir, args.key, args.value)
            else:
                parser.error(f"'{args.action}' 仅支持 INI 文件")
        else:
            if args.action == "list":
                cmd_ini_list(save_dir)
            elif args.action == "room-list":
                cmd_room_list(args.value or "")
            elif args.action == "get":
                if not args.key:
                    parser.error("--key 是必需的")
                cmd_ini_get(save_dir, args.section, args.key)
            elif args.action == "set":
                if not args.key or args.value is None:
                    parser.error("--key 和 --value 是必需的")
                cmd_ini_set(save_dir, args.section, args.key, args.value)
            elif args.action == "find":
                print("find 仅支持 file0 (在 INI 中用 get 或 list)", file=sys.stderr)
                sys.exit(1)
            elif args.action == "undo":
                if not args.value:
                    parser.error("--value 是必需的 (ini, file0, 或 data_win)")
                cmd_undo(save_dir, args.value, backup_ts=args.backup)
            elif args.action == "list-backups":
                if not args.value:
                    parser.error("--value 是必需的 (ini, file0, 或 data_win)")
                cmd_list_backups(save_dir, args.value)
            elif args.action == "create-system-info":
                if args.value is None:
                    parser.error("--value 是必需的 (962 或 963)")
                cmd_create_system_info(save_dir, args.value)
            elif args.action == "quest-init":
                flag_idx = args.flag if args.flag is not None else FLAG_CUSTOM_START
                cmd_quest_init(save_dir, flag_idx)
            elif args.action == "quest-status":
                cmd_quest_status(save_dir)
            elif args.action == "reset-all":
                cmd_reset_all(save_dir)
            else:
                cmd_reset_flags(save_dir)
    except (FileNotFoundError, ValueError, DeterlineError) as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
