"""file0 存档读写域（O2 步 2：从 modify_save.py L610-1013 1:1 平移）。

GameMaker 纯文本序列化格式；数据表（FILE0_FIELDS..ARMOR_DF、ITEMS）随域整体
平移（_ALL_FILE0_FIELDS 的合并初始化必须与本文件表定义保持同序）。
跨模块一律模块属性形式：errors./paths.（运行时查找）。
"""

import sys
from pathlib import Path

from . import errors, transactions

# ============================================================
# file0 Operations  (GameMaker 纯文本序列化格式)
# ============================================================

# ── 核心角色属性 ──────────────────────────────────────────────
# 索引对应 file0 中去掉首行名字后的 0-based 位置
# 布局已对照游戏源码 scr_saveprocess / scr_load 核实：
#   [0]=global.lv [1]=global.maxhp [2]=global.maxen [3]=global.at
#   [4]=global.wstrength [5]=global.df [6]=global.adef [7]=global.sp
#   [8]=global.xp [9]=global.gold [10]=global.kills
# 注意: file0 不存"当前 HP"，HP 即最大生命值(maxhp)。
FILE0_FIELDS = {
    "LOVE": 0,          # LV / 等级
    "LV": 0,
    "MAXHP": 1,         # 最大生命值 (global.maxhp)
    "HP": 1,            # 别名: 游戏无独立"当前HP"，HP 即最大生命值
    "MAXEN": 2,         # 战斗能量上限 (global.maxen)
    "AT": 3,            # 基础攻击
    "WEAPON_AT": 4,     # 武器攻击加成
    "DF": 5,            # 基础防御
    "ARMOR_DF": 6,      # 护甲防御加成
    "SP": 7,            # 速度
    "EXP": 8,           # 处决点数
    "GOLD": 9,          # 金钱
    "KILLS": 10,        # 总击杀数
}

# HP/AT/DF 由 LV 推导，游戏在升级 (scr_levelup) 与每次进入战斗
# (obj_battlecontroller_Create_0) 时都会用下面公式重算，file0 中的值只是
# 读档瞬间的缓存。想固定这些值必须改游戏脚本，见 `set-derived`。
DERIVED_STAT_FORMULAS: dict[str, str] = {
    "HP": "16 + (global.lv * 4)",
    "MAXHP": "16 + (global.lv * 4)",
    "AT": "8 + (global.lv * 2)",
    "DF": "9 + ceil(global.lv / 4)",
}

DERIVED_STAT_VARS: dict[str, str] = {
    "HP": "maxhp",
    "MAXHP": "maxhp",
    "AT": "at",
    "DF": "df",
}


def derived_stat_value(key: str, lv: int) -> int | None:
    """Return the LV-derived value the game will recompute for HP/AT/DF."""
    upper = key.upper()
    if upper in ("HP", "MAXHP"):
        return 16 + lv * 4
    if upper == "AT":
        return 8 + lv * 2
    if upper == "DF":
        return 9 + (lv + 3) // 4
    return None


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
    transactions.write_one(path, _serialize_file0(name, numbers))


def _serialize_file0(name: str, numbers: list[int]) -> bytes:
    return (name + "\r\n" + "".join(f"{n} \r\n" for n in numbers)).encode("utf-8")


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
    print(f"  LOVE={core.get('LOVE','?')}  MAXHP={core.get('MAXHP','?')}  MAXEN={core.get('MAXEN','?')}  "
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
        raise errors.ValidationError(f"未知字段: '{key}'")

    if not (0 <= idx < len(numbers)):
        raise errors.ValidationError(f"索引 {idx} 越界")

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
        raise errors.ValidationError("搜索值须为整数")

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


def cmd_file0_set(save_dir: Path, key: str, value: str,
                  warn_derived: bool = True, *, submit=None) -> None:
    path = save_dir / "file0"
    baseline = transactions.fingerprint(path)
    name, numbers = _parse_file0(path)

    try:
        val = int(value)
    except ValueError:
        raise errors.ValidationError(f"值须为整数: {value}")

    idx = _resolve_file0_key(key)
    if idx is None:
        raise errors.ValidationError(f"未知字段: '{key}'")

    if not (0 <= idx < len(numbers)):
        raise errors.ValidationError(f"索引 {idx} 越界")

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
    edit = transactions.FileEdit(path.resolve(), _serialize_file0(name, numbers), baseline)
    if submit is None:
        transactions.EditPlan((edit,)).apply()
    else:
        submit(edit)

    # HP/AT/DF 由 LV 推导：读档时先用 file0 值，但进战斗/升级时会被游戏重算覆盖。
    if warn_derived and numbers:
        lv = numbers[0]
        derived = derived_stat_value(upper_key, lv)
        if derived is not None and val != derived:
            print(
                f"⚠️ 注意: {upper_key} 由 LV 推导。读档后菜单会显示你设置的 {val}，"
                f"但进入战斗/升级时游戏会按 {upper_key} = {DERIVED_STAT_FORMULAS[upper_key]}"
                f" 重算（当前 LV={lv} → {derived}），此后 {val} 会被覆盖为 {derived}。",
                file=sys.stderr,
            )
            print(
                f"   如需永久固定为 {val}，请运行: "
                f"set-derived --key {upper_key} --value {val}",
                file=sys.stderr,
            )

    print(f"✓ file0 [{idx}] {key}: {old} → {val}{hint}{auto_msg}")
