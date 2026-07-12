---
name: undertale-save-editor
description: >
  Use when the user wants to modify UNDERTALE game saves — change LOVE, Kills,
  Room, HP, ATK, DEF, Gold, stats, check or edit undertale.ini or file0,
  reset genocide route flags, or jump to any room. Trigger keywords:
  undertale, save, LOVE, Kills, Room, HP, ATK, DEF, Gold, file0,
  undertale.ini, genocide, flags, reset, item, boss, weapon, armor.
---

# undertale-save-editor

> ⚠️ 非官方粉丝作品 · Fan-made project.  
> Not affiliated with Toby Fox or Fangamer. UNDERTALE is © Toby Fox.

修改《传说之下》(UNDERTALE) 游戏存档的 Agent Skill。支持修改 `undertale.ini` 和 `file0` 中的游戏进度、角色属性、物品、BOSS 状态、路线标志等。

## 技能版本

1.1.0

## 适用平台

- **OpenCode** — Agent Skill 原生支持，自动发现
- **Codex** — 兼容 Agent Skill 标准
- **Claude Code** — 兼容 `.claude/skills/` 目录
- **Cursor** — 兼容 `.agents/skills/` 目录
- **终端/命令行** — 无需 Agent，`python run.py` 直接使用

## 前提条件

- 系统已安装 **Python 3.10+**
  - 没有的话去 [python.org](https://python.org) 下载
  - **Windows 用户**：安装时请勾选 **"Add Python to PATH"**
- UNDERTALE 至少运行过一次（产生存档文件）

## 文件结构

```
undertale-save-editor/
├── run.py                ← 快捷入口（python run.py --action ...）
├── SKILL.md              ← 本技能描述文件
├── README.md
├── LICENSE
├── .gitignore
└── scripts/
    ├── modify_save.py    ← 核心修改脚本
    ├── rooms.json        ← 244 个房间 ID ↔ 中文名称映射
    └── rooms_reverse.json
```

## 参数

| 参数 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `--action` | 是 | — | `get` / `set` / `list` / `find` / `reset-flags` / `room-list` / `create-system-info` |
| `--key` | 视 action 而定 | — | 键名或数字索引 |
| `--value` | set/find/create-system-info 必填 | — | 要设置/搜索的值 |
| `--section` | 否 | `General` | INI 节名（如 `Flowey`、`FFFFF`） |
| `--file` | 否 | `ini` | `ini` 或 `file0` |
| `--dir` | 否 | 自动检测 | 手动指定存档目录路径 |

## 一键安装到 Agent

```bash
# 方式 A: 直接双击 install.py (macOS/Linux 可用)
# 方式 B: 终端运行
python install.py

# 方式 C: 通过 run.py
python run.py --install
```

脚本会自动检测系统中已安装的 Agent 并安装到对应目录。安装后 Agent 即可自动发现此 Skill。

> **风险提示**：macOS/Linux 使用符号链接安装，删除源文件夹后 Skill 会失效。
> 如需重新安装，先删除 Agent 目录下的 `undertale-save-editor` 文件夹再运行。

## 直接下载使用

普通玩家无需 Agent，终端直接运行：

```bash
# 进入文件夹后
python run.py --action get --key Love
python run.py --action set --key HP --value 50 --file file0
python run.py --action list --file file0
```

如果自动检测存档目录失败，手动指定：

```bash
python run.py --action list --dir "C:\Users\用户名\AppData\Local\UNDERTALE"
python run.py --action list --dir "~/Library/Application Support/com.tobyfox.undertale"
```

## 键名映射表

### undertale.ini — [General] 节

| 键名 | 说明 |
|---|---|
| `Love` | LOVE / 等级 (1-20) |
| `Kills` | 击杀数 |
| `Room` | 当前房间 ID（支持中文名称） |
| `fun` | 趣味值（影响 Gaster 等隐藏事件） |
| `Name` | 玩家名称 |
| `Time` | 游戏时间（秒） |
| `Gameover` | 死亡次数 |

### file0 核心属性（索引 0-10）

| 键名 | 索引 | 说明 |
|---|---|---|
| `LOVE` / `LV` | 0 | 等级 |
| `HP` | 1 | 当前 HP |
| `MAXHP` | 2 | 最大 HP |
| `AT` | 3 | 基础攻击 |
| `WEAPON_AT` | 4 | 武器攻击加成 |
| `DF` | 5 | 基础防御 |
| `ARMOR_DF` | 6 | 护甲防御加成 |
| `EXP` | 8 | 处决点数 |
| `GOLD` | 9 | 金钱 |
| `KILLS` | 10 | 总击杀数 |

### file0 物品栏（索引 11-28）

| 键名 | 索引 | 说明 |
|---|---|---|
| `INV1` ~ `INV8` | 11-25 (步长2) | 8 个物品格（物品 ID 见下文） |
| `CELL1` ~ `CELL8` | 12-26 (步长2) | 8 个手机选项 |
| `WEAPON` | 27 | 已装备武器（自动同步 AT） |
| `ARMOR` | 28 | 已装备护甲（自动同步 DF） |

### file0 BOSS 状态

| 键名 | 索引 | 值含义 |
|---|---|---|
| `TRAINING_DUMMY` | 43 | 0=初始 1=击杀 2=对话 3=无聊 |
| `TORIEL` | 74 | 0=初始 4=击杀 5=宽恕 |
| `DOGGO` | 81 | 0=初始 1=击杀 2=宽恕 |
| `DOGAMY` | 82 | 同上 |
| `GREATER_DOG` | 83 | 0=初始 1=击杀 2=宽恕 3=无视 |
| `ICE_CAP` | 86 | 0=初始 2=击杀 |
| `PAPYRUS` | 96 | 0=初始 1=击杀 |
| `SHRYREN` | 110 | 0=初始 1=击杀 |
| `UNDYNE_1` | 280 | 0=初始 1=击杀（瀑布追逐） |
| `MAD_DUMMY` | 281 | 0=初始 1=击杀 |
| `UNDYNE_2` | 379 | 0=初始 1=击杀（竞技场） |
| `MUFFET` | 426 | 0=初始 1=击杀 |
| `ROYAL_GUARDS` | 431 | 0=初始 1=击杀 |
| `METTATON` | 454 | 0=初始 1=击杀 |

### file0 区域击杀数

| 键名 | 索引 | 说明 |
|---|---|---|
| `UNKNOWN_KILLS` | 230 | 未知区域 |
| `RUINS_KILLS` | 231 | 遗迹击杀 |
| `SNOWDIN_KILLS` | 232 | 雪镇击杀 |
| `WATERFALL_KILLS` | 233 | 瀑布击杀 |
| `HOTLAND_KILLS` | 234 | 热域击杀 |

### file0 特殊旗标

| 键名 | 索引 | 说明 |
|---|---|---|
| `FUN` | 34 | 趣味值 |
| `DEFEATED_ASRIEL` | 36 | 1=已击败小羊（真和平） |
| `EXITED_TRUE_LAB` | 522 | 12=已离开真实验室 |
| `PLOT` | 541 | 剧情值 |
| `HAVE_CELL` | 544 | 1=有手机 |
| `LOCATION` / `ROOM` | 546 | 房间 ID |

### 物品 ID 表（常用）

| ID | 名称 | 分类 |
|---|---|---|
| 0 | (空) | — |
| 1 | 怪物糖果 | 恢复 |
| 11 | 奶油肉桂派 | 恢复 |
| 12 | 褪色的缎带 | 护甲 (DF+3) |
| 13 | 玩具刀 | 武器 (AT+3) |
| 14 | 坚韧手套 | 武器 (AT+5) |
| 15 | 兄贵头巾 | 护甲 (DF+7) |
| 25 | 芭蕾舞鞋 | 武器 (AT+7) |
| 45 | 染血的围裙 | 护甲 (DF+7) |
| 46 | 染色围裙 | 护甲 (DF+11) |
| 47 | 烧焦的平底锅 | 武器 (AT+10) |
| 48 | 牛仔帽 | 护甲 (DF+12) |
| 49 | 空枪 | 武器 (AT+12) |
| 50 | 心形锁坠 | 护甲 (DF+15) |
| 51 | 磨损的刀 | 武器 (AT+15) |
| 52 | 真刀 | 武器 (AT+99) |
| 53 | 锁坠 | 护甲 (DF+99) |
| 64 | 提米盔甲 | 护甲 (DF+20) |

## action 说明

### `get` — 读取值

```
python scripts/modify_save.py --action get --key Love
# Love = 4  (LOVE / 等级)

python scripts/modify_save.py --action get --key HP --file file0
# [1] HP = 20

python scripts/modify_save.py --action get --key TORIEL --file file0
# [74] TORIEL = 5  ← TORIEL (已宽恕)
```

### `set` — 修改值

```
python scripts/modify_save.py --action set --key LOVE --value 20
# ✓ [General] Love: 4 → 20

python scripts/modify_save.py --action set --key HP --value 50 --file file0
# ✓ file0 [1] HP: 20 → 50

# 设置武器 (自动同步 AT):
python scripts/modify_save.py --action set --key WEAPON --value 52 --file file0
# ✓ file0 [27] WEAPON: 51 → 52  ← WEAPON (真刀 AT+99) (WEAPON_AT 同步: 15→99)

# 宽恕托丽尔:
python scripts/modify_save.py --action set --key TORIEL --value 5 --file file0
# ✓ file0 [74] TORIEL: 4 → 5  ← TORIEL (已宽恕)

# 修改区域击杀:
set --key RUINS_KILLS --value 20 --file file0
# ✓ file0 [231] RUINS_KILLS: 0 → 20  ← 遗迹击杀
```

### `list` — 列出所有值

```
python scripts/modify_save.py --action list
# [General]
#   Love = 4  (LOVE / 等级)
#   Room = 43  (当前房间 ID)
#     → 遗迹 - 出口
#   ...

python scripts/modify_save.py --action list --file file0
# ═══ 玩家: frisk ═══
# LOVE=4  HP=20/32  AT=3  DF=3  GOLD=0  KILLS=15
# 武器: 真刀 AT+99  护甲: 心形锁坠 DF+15
# 区域击杀: 遗迹=20 雪镇=0 瀑布=0 热域=0
# BOSS: TORIEL=已击杀, PAPYRUS=已宽恕
# ...
```

### `find` — 在 file0 中搜索值

```
python scripts/modify_save.py --action find --value 4 --file file0
# 值 4 出现在以下位置:
#   [0] = 4  ← LOVE
#   [7] = 4
#   ...
```

### `reset-flags` — 清除屠杀线标志

同时清理 INI 和 file0：

```
python scripts/modify_save.py --action reset-flags
# INI 已重置以下屠杀线标志:
#   • [Flowey] met1: 1 → 0
#   • [General] Kills: 15 → 0
#   • [General] fun: 30 → 47
#   • file0 Kills: 15 → 0 (已同步)
```

### `room-list` — 列出/搜索房间

```
python scripts/modify_save.py --action room-list --value 瀑布
# [ 82] 瀑布 - 入口 (瀑布消失的雕像)
# [ 83] 瀑布 - 蘑菇洞
# ...
```

### `create-system-info` — 创建屠杀线结局标记

```
python scripts/modify_save.py --action create-system-info --value 962
# ✓ 已创建 system_information_962 (世界已删除)

python scripts/modify_save.py --action create-system-info --value 963
# ✓ 已创建 system_information_963 (已向 Chara 献出灵魂)
```

## 安全机制

- 每次修改前自动创建 `.bak` 备份
- file0 值严格校验整数，拒绝浮点
- 存档目录不存在时清晰提示
- INI 重复键自动清理

## 注意事项

1. **字段映射已对齐 Undertale 社区研究**，修正了旧版本中 HP/LOVE 映射颠倒的问题
2. **设置 WEAPON/ARMOR 时自动同步 AT/DF**，不需要额外设置
3. **INI 和 file0 同步修改**：LOVE、Kills、Room 同时存在于两文件中
4. **屠杀线重置**：`reset-flags` 同时清理 INI 和 file0
5. **跨平台**：macOS 和 Windows 路径自动识别
