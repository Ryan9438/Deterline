#!/usr/bin/env python3
"""UNDERTALE Save Editor — modify undertale.ini and file0."""

import argparse
import configparser
import json
import os
import random
import shutil
import sys
from pathlib import Path

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


def backup_file(path: Path) -> None:
    bak = path.with_suffix(path.suffix + ".bak")
    try:
        shutil.copy2(str(path), str(bak))
    except OSError as e:
        print(f"警告: 备份失败 ({e})", file=sys.stderr)


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
        sys.exit(1)
    print(f"错误: 未找到匹配 '{val}' 的房间", file=sys.stderr)
    sys.exit(1)


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
        print(f"错误: [{section}] 中未找到 '{key}'", file=sys.stderr)
        sys.exit(1)
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
        print(f"错误: 未知字段 '{key}'。\n已知字段: {known}", file=sys.stderr)
        sys.exit(1)

    if not (0 <= idx < len(numbers)):
        print(f"错误: 索引 {idx} 越界 (0 ~ {len(numbers) - 1})", file=sys.stderr)
        sys.exit(1)

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
        print("错误: 搜索值须为整数", file=sys.stderr)
        sys.exit(1)

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
        print(f"错误: file0 值须为整数, 收到: {value}", file=sys.stderr)
        sys.exit(1)

    idx = _resolve_file0_key(key)
    if idx is None:
        known = ", ".join(sorted(_ALL_FILE0_FIELDS.keys(), key=lambda k: _ALL_FILE0_FIELDS[k]))
        print(f"错误: 未知字段 '{key}'。\n已知字段: {known}", file=sys.stderr)
        sys.exit(1)

    if not (0 <= idx < len(numbers)):
        print(f"错误: 索引 {idx} 越界 (0 ~ {len(numbers) - 1})", file=sys.stderr)
        sys.exit(1)

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

def cmd_undo(save_dir: Path, target: str) -> None:
    files = {
        "ini": save_dir / "undertale.ini",
        "file0": save_dir / "file0",
    }
    key = target.lower()
    if key not in files:
        print(f"错误: 未知文件 '{target}'，可选: ini, file0", file=sys.stderr)
        sys.exit(1)

    orig = files[key]
    bak = orig.with_suffix(orig.suffix + ".bak")
    if not bak.exists():
        print(f"没有找到备份文件: {bak}", file=sys.stderr)
        sys.exit(1)

    shutil.copy2(str(bak), str(orig))
    print(f"✓ {key} 已从备份恢复: {bak} → {orig}")


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
# System Information files (屠杀线结局标记)
# ============================================================

def cmd_create_system_info(save_dir: Path, value: str) -> None:
    """Create system_information_962 or system_information_963."""
    if value not in ("962", "963"):
        print("错误: 系统信息文件编号必须是 962 或 963。\n"
              "  962 = 世界已删除 (屠杀线结局)\n"
              "  963 = 已向 Chara 献出灵魂", file=sys.stderr)
        sys.exit(1)

    fname = f"system_information_{value}"
    path = save_dir / fname
    if path.exists():
        print(f"'{fname}' 已存在。")
        return
    path.touch()
    print(f"✓ 已创建 {fname}  ({'世界已删除' if value == '962' else '已向 Chara 献出灵魂'})")


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
  %(prog)s --action set  --key HP  --value 99 --file file0
  %(prog)s --action get  --key HP  --file file0
  %(prog)s --action list --file file0
  %(prog)s --action set  --key WEAPON --value 51 --file file0   (自动 AT=99)
  %(prog)s --action set  --key TORIEL --value 5 --file file0    (宽恕)
  %(prog)s --action set  --key RUINS_KILLS --value 20 --file file0
  %(prog)s --action create-system-info --value 962
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--action", required=True,
                        choices=["get", "set", "list", "find", "reset-flags",
                                 "room-list", "create-system-info", "undo"])
    parser.add_argument("--key", help="键名或数字索引 (file0 用数字)")
    parser.add_argument("--value", help="要设置/搜索的值 (set/find 操作必需)")
    parser.add_argument("--section", default="General",
                        help="INI 节名 (默认: General)")
    parser.add_argument("--file", choices=["ini", "file0"], default="ini",
                        help="目标文件 (默认: ini)")
    parser.add_argument("--dir", help="手动指定存档目录路径")
    args = parser.parse_args()

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
                parser.error("reset-flags 仅支持 INI 文件")
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
                    parser.error("--value 是必需的 (ini 或 file0)")
                cmd_undo(save_dir, args.value)
            elif args.action == "create-system-info":
                if args.value is None:
                    parser.error("--value 是必需的 (962 或 963)")
                cmd_create_system_info(save_dir, args.value)
            else:
                cmd_reset_flags(save_dir)
    except (FileNotFoundError, ValueError) as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
