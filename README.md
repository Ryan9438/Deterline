# undertale-save-editor

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> ⚠️ 非官方粉丝作品 · Fan-made project.  
> Not affiliated with Toby Fox or Fangamer. UNDERTALE is © Toby Fox.

《传说之下》(UNDERTALE) 存档修改器。可以修改 `undertale.ini` 和 `file0` 中的角色属性、物品、BOSS 状态、路线标志等。

## 功能

- 修改 LOVE、HP、ATK、DEF、GOLD、EXP、Kills
- 物品栏编辑（8 格 + 手机选项 + 武器 + 护甲）
- BOSS/遭遇战状态编辑（14 个 BOSS）
- 按区域击杀数（遗迹/雪镇/瀑布/热域）
- 中文房间名称支持（244 个已命名房间）
- 屠杀线标志一键重置
- 真和平路线旗标设置
- Omega Flowey / 系统信息文件创建
- 装备武器/护甲时自动同步 AT/DF
- 每次修改前自动创建 `.bak` 备份
- Undo: `python run.py --action undo --value ini|file0` 从备份恢复

## 快速开始

```bash
# 查看当前 LOVE
python run.py --action get --key Love

# 修改 LOVE 为 20
python run.py --action set --key LOVE --value 20

# 查看完整存档状态
python run.py --action list --file file0

# 装备真刀（自动同步攻击力）
python run.py --action set --key WEAPON --value 51 --file file0

# 重置屠杀线标志
python run.py --action reset-flags
```

> 所有命令也支持 `python scripts/modify_save.py` 直接调用，参数完全一致。

完整用法见 [SKILL.md](SKILL.md)。

## 系统兼容性

| 平台 | 支持 | 说明 |
|---|---|---|
| macOS | ✅ | 自动识别 `~/Library/Application Support/com.tobyfox.undertale/` |
| Windows | ✅ | 自动识别 `%LOCALAPPDATA%\UNDERTALE\` |
| Linux | ⚠️ 手动 | 需用 `--dir` 参数指定存档路径 |

## Agent 兼容性

| 平台 | 支持 | 说明 |
|---|---|---|
| OpenCode | ✅ | Agent Skill 原生支持，自动发现 |
| Codex | ✅ | 兼容 Agent Skill 标准 |
| Claude Code | ✅ | 兼容 `.claude/skills/` 目录结构 |
| Cursor | ✅ | 兼容 `.agents/skills/` 目录结构 |
| 终端直接运行 | ✅ | 无需 Agent，`python run.py` 直接使用 |

### 一键安装到 Agent

```bash
python install.py
# 或
python run.py --install
```

脚本自动检测 OpenCode / Claude Code / Cursor / Codex 并安装。

也支持手动复制：

```bash
# OpenCode
cp -r undertale-save-editor ~/.config/opencode/skills/
# Claude Code
cp -r undertale-save-editor ~/.claude/skills/
# Cursor
cp -r undertale-save-editor ~/.agents/skills/
```

作为 Skill 安装后，Agent 会自动发现并调用，你也可以在终端直接使用 `python run.py`。

## 系统要求

- **Python 3.10+**（没有的话去 [python.org](https://python.org) 下载安装）
- UNDERTALE 至少运行过一次（产生存档文件）

> **Windows 用户**：安装 Python 时请勾选 **"Add Python to PATH"**，否则终端无法识别 `python` 命令。

## 典型用法示例

```bash
# 角色属性
python run.py --action get --key LOVE
python run.py --action set --key HP --value 50 --file file0

# 金钱
python run.py --action get --key GOLD --file file0
python run.py --action set --key GOLD --value 9999 --file file0

# 传送（支持中文房间名）
python run.py --action set --key Room --value "安黛因竞技场"
python run.py --action get --key Room

# 物品
python run.py --action set --key WEAPON --value 50 --file file0  # 磨损的刀
python run.py --action set --key INV1 --value 11 --file file0    # 奶油肉桂派

# BOSS 状态
python run.py --action set --key TORIEL --value 5 --file file0   # 已宽恕
python run.py --action set --key PAPYRUS --value 1 --file file0  # 已击杀

# 搜索
python run.py --action find --value 42 --file file0

# 路线
python run.py --action reset-flags
```

## 文件结构

```
undertale-save-editor/
├── Install.app/        ← macOS 双击一键安装
├── install.bat         ← Windows 双击一键安装
├── install.py          ← 跨平台安装脚本
├── run.py              ← 快捷入口（python run.py --action ...）
├── SKILL.md            ← Agent Skill 完整文档
├── COMMANDS.md         ← 常用指令速查
├── README.md
├── LICENSE             ← MIT
├── .gitignore
└── scripts/
    ├── modify_save.py  ← 核心脚本
    ├── rooms.json      ← 244 个房间名映射
    └── rooms_reverse.json
```

## 注意事项

- 修改前会自动备份文件为 `*.bak`，改坏了可从备份恢复
- file0 字段位置因存档进度而异，不确定位置时用 `find` 搜索
- LOVE、Kills、Room 同时存在于 INI 和 file0，建议两边同步修改

## License

MIT
