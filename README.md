# Deterline

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)

> ⚠️ 非官方粉丝作品 · Fan-made project.  
> Not affiliated with Toby Fox or Fangamer. UNDERTALE is © Toby Fox.
>
> ⚠️ 本软件使用 AGPL-3.0 许可证。禁止任何形式的商业倒卖。
> 未经作者书面授权，不得发布修改版本或衍生作品。

《传说之下》(UNDERTALE) **全能修改器**——Deterline。支持存档属性编辑、**对话文本自由增删改查**、**GML 脚本反编译与重编译**、**房间布局编辑**、**自定义 NPC 支线**（头像 + 多段对话 + 选择分支 + 战斗 + 物品奖励）。

## 功能

### 📁 存档编辑
- 修改 LOVE、HP、ATK、DEF、GOLD、EXP、Kills、Room
- 物品栏编辑（8 格 + 武器 + 护甲，换武器自动同步 AT/DF）
- BOSS 状态编辑（14 个 BOSS）+ 区域击杀数
- 中文房间名支持（244 个已命名房间）
- 屠杀线标志一键重置、真和平路线旗标设置
- Omega Flowey / 系统信息文件创建

### 💬 对话编辑（需 UTMT CLI）
- 对话字符串自由**新增/删除/修改**（无长度限制）
- 按内容搜索/批量替换
- 所有文本的中央数据库（`textdata_en`，16457 行 GML）管理

### 📜 脚本编辑（需 UTMT CLI）
- **反编译** 6272 个游戏脚本为可读 GML 源码
- **修改后重新编译**回字节码
- **追加/前置代码**不覆盖原有逻辑（`append-code` / `prepend-code`）
- 创建全新脚本并自动注册
- 跨所有脚本搜索变量引用（`search-vars`）
- 源码搜索替换（`find-replace-code`，已修复转义问题）

### 🏗️ 房间布局编辑（需 UTMT CLI）
- 在任意房间生成任意对象实例（`spawn-obj`，保留完整 AI/碰撞/交互）
- 按实例 ID 或对象类型移除（`remove-obj` / `remove-obj --all`）
- 查看房间内全部对象及其事件（`room-objects`）

### 🎭 头像/对话系统（需 UTMT CLI）
- 9 个内置角色头像（`facechoice=1-9`：Toriel/Sans/Papyrus/Undyne/...）
- 对话文本控制符完整支持（`\F`头像 `\E`表情 `\C`选择 `\T`速度 `\R\G\B`颜色）
- 批量导入对话（`batch-add-textentry` from JSON）
- 添加对话时可选自动插入头像控制符（`add-textentry --face 3 --emotion 1`）

### 🤖 自定义 NPC 支线（需 UTMT CLI）
- **距离自动触发对话**（`distance_to_object`，无需 Z 键）
- **多阶段状态机**（`flag[510]`，0→1→2→...）
- **YES/NO 选择分支** + 2 帧窗口截获机制
- **物品奖励**（`scr_itemget`）+ **战斗触发**（`battlegroup`）
- **任务管理**（`quest-init` / `quest-status`）
- 完整三段式 NPC 模板见 [SKILL.md](SKILL.md)

## 快速开始

### 安装

选择你的平台，运行一次即可：

| 平台 | 入口 | 说明 |
|------|------|------|
| **macOS** | 双击 `Install.app` | 检测环境 → 没装齐则补全 → 秒装 Agent Skill |
| **Windows** | 双击 `install.bat` | 同上 |
| **Linux** | `bash install.sh` | 同上 |
| **已有 Python** | `python3 install.py` | 同上 |

所有入口最终都调用同一个 `install.py`，安装脚本会自动处理：
- Agent Skill 安装（符号链接）
- .NET SDK 检测与安装
- UndertaleModTool CLI 克隆与编译
- `UTMT_CLI` 环境变量配置

### 快速上手

安装完成后：

```bash
# 存档编辑（零依赖，立即可用）
python run.py --action get --key Love
python run.py --action set --key HP --value 50 --file file0
python run.py --action set --key Room --value "托丽尔的家"

# 对话编辑（需 UTMT CLI）
python run.py --action add-textentry --key "obj_quest" --value "* Hello!/%%" --face 3 --file data_win

# 脚本编辑（需 UTMT CLI）
python run.py --action list-codes --file data_win --limit 5
python run.py --action append-code --key "gml_Object_obj_dummy1_Step_0" --value "// custom code" --file data_win

# 房间布局编辑（需 UTMT CLI）
python run.py --action spawn-obj --value "room_asrielroom" --key "obj_dummy1" --x 160 --y 120 --file data_win

# 任务管理
python run.py --action quest-status
python run.py --action quest-init
```

完整命令列表见 [COMMANDS.md](COMMANDS.md)，Agent Skill 文档见 [SKILL.md](SKILL.md)。

## 系统要求

| 组件 | 存档编辑 | 对话/脚本编辑 |
|---|---|---|
| **Python 3.10+** | ✅ 必需 | ✅ 必需 |
| **.NET 10 SDK** | ❌ 不需要 | ✅ 必需（安装脚本自动处理） |
| **UndertaleModTool CLI** | ❌ 不需要 | ✅ 必需（安装脚本自动处理） |

### 一键安装

```bash
# 交互式安装（推荐）
python install.py

# 或快速自动安装（跳过确认）
python install.py --all
```

安装脚本会自动：
1. 安装 Deterline Skill 到已检测到的 Agent（OpenCode / Claude Code / Cursor / Codex）
2. 检测并安装 .NET SDK（如未安装）
3. 克隆并编译 UndertaleModTool CLI
4. 配置 `UTMT_CLI` 环境变量

**macOS 用户**也可双击 `Install.app` 启动安装。

### 单独安装组件

```bash
python install.py --skill   # 仅安装 Agent Skill
python install.py --dotnet  # 仅安装 .NET SDK
python install.py --utmt    # 仅编译 UTMT CLI
python install.py --env     # 仅配置环境变量
```

## 系统兼容性

| 平台 | 支持 | 说明 |
|---|---|---|
| macOS | ✅ | 自动识别存档路径 |
| Windows | ✅ | 自动识别 `%LOCALAPPDATA%\UNDERTALE\` |
| Linux | ⚠️ 手动 | 需 `--dir` 参数指定路径 |

## Agent 兼容性

| 平台 | 支持 |
|---|---|
| OpenCode | ✅ Agent Skill 原生支持，自动发现 |
| Codex | ✅ 兼容 Agent Skill 标准 |
| Claude Code | ✅ 兼容 `.claude/skills/` |
| Cursor | ✅ 兼容 `.agents/skills/` |
| 终端直接运行 | ✅ `python run.py` |

### 一键安装到 Agent

```bash
python install.py
```

或双击 `Install.app`（macOS）。

Skill 通过符号链接安装，工作区修改自动同步。

## 文件结构

```
deterline/
├── run.py              ← 快捷入口
├── SKILL.md            ← Agent Skill 完整文档（2.0.0）
├── COMMANDS.md         ← 常用指令速查
├── README.md
├── scripts/
│   ├── modify_save.py  ← 核心脚本（存档 + 对话 + 代码编辑）
│   └── rooms.json      ← 244 个房间名映射
```

## 注意事项

- 修改 `game.ios` 前自动创建时间戳备份（`.bak.YYYYMMDD_HHMMSS`）
- `global.flag[]` 索引范围 0-511，超出会崩溃。自定义事件仅用 `flag[510]` 和 `flag[511]`
- 对话文本格式：`* ` 前缀必需、`/` 翻页、`/%%` 末页、`&` 换行、`^N` 暂停
- 英文版不支持中文，中文字符显示为空白 `*`
- `spawn-obj` 修改的是 `game.ios` 的房间布局数据，不是存档。新实例在重新进入房间时加载
- `replace-code` 会覆盖整个脚本；`append-code` / `prepend-code` 不覆盖原逻辑
- LOVE、Kills、Room 同时存在于 INI 和 file0，`set --key Room` 自动同步
- `facechoice` 范围 0-9（0=无头像, 1=Toriel, 2=Flowey, 3=Sans, ...），**不要用 10+**
- **`--sandbox` 模式**：在 `game.ios.sandbox` 副本上操作，原文件不受影响。确认后用 `sandbox-restore` 恢复
- **安装 UTMT CLI 后**才能使用 `--file data_win` 相关命令

## License

[GNU Affero General Public License v3.0](LICENSE)

> 本软件为粉丝项目，与 Toby Fox 或 Fangamer 无关。
> UNDERTALE 是 Toby Fox 的注册商标。
>
> 禁止任何形式的商业倒卖。未经作者书面授权，不得发布修改版本或衍生作品。
