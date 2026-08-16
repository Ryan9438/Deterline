---
name: deterline
description: "Deterline is an all-in-one modding tool for UNDERTALE (传说之下). Edit save files (HP, LOVE, gold, weapons, armor, room teleport, genocide reset); create and edit rooms with backgrounds, tiles and camera views; replace sprites and textures (export/import PNG, recolor via HSV, duplicate); add custom NPCs with dialogue, portraits, YES/NO choices, quests and battles; edit GML scripts (decompile, replace, append, prepend, create new); manage dialogue text; set up portals between rooms; generate pixel backgrounds. Use when the user wants any UNDERTALE modding task: 改存档, 改属性, 改HP, 换武器, 传送, 传送到某房间, 建房间, 做新场景, 做地图, 换背景, 设置背景, 加背景, 加对话, 改对话, 加NPC, 做支线, 做任务, 放传送门, 开门, 触发战斗, 给物品, 换精灵, 改贴图, 导出图片, 导入图片, 换色, 调色, 复制精灵, 生成背景, 像素背景, 替换纹理, 重置屠杀线. Dialogue text must be English/ASCII only (the bitmap font has no Chinese glyphs)."
---

# Deterline

> ⚠️ 非官方粉丝作品 · Fan-made project.
> Not affiliated with Toby Fox or Fangamer. UNDERTALE is © Toby Fox.
> 
> 本软件使用 AGPL-3.0 许可证。

修改《传说之下》(UNDERTALE) 游戏存档 + 游戏数据的全能工具——Deterline。支持存档属性修改、**对话文本自由增删改查**、**GML 脚本反编译与重编译**、**房间布局编辑**、**自定义 NPC 支线**（头像 + 多段对话 + 选择分支 + 战斗 + 物品奖励）。

## 触发词参考（关键词匹配，供 Agent 参考）

```
Deterline, deterline, modify_save, run.py, install.py, bg_generator,
UndertaleModTool, UTMT, game.ios, data.win,
undertale, UNDERTALE, 传说之下,
save, 存档, 存檔, save file, save editor, 修改器,
HP, LOVE, ATK, DEF, GOLD, EXP, Kills, Room, file0, undertale.ini,
weapon, armor, equip, item, boss, 武器, 护甲, 装备, 物品, 金钱, 属性,
genocide, murder, reset, flags, systeminfo, teleport, 传送, 重置, 屠杀,
dialogue, textdata, textentry, STRG, batch-add-textentry,
guided-add-dialogue, 对话, 文本, 文字, 加对话, 改对话,
face, portrait, emotion, facechoice, 头像, 表情,
room, create-room, room-info, room-objects, 房间, 场景, 地图, 建房间,
background, bg, gml-bg, create-bg-asset, tile, remove-tile,
set-room-view, set-room-prop, view, parallax, 背景, 地板, 瓷砖, 视差,
spawn, spawn-obj, remove, remove-obj, 生成, 移除, 放置,
sprite, texture, TXTR, TPAG, SPRT, 精灵, 纹理, 贴图, 图片, 图像,
export, replace, recolor, colorize, duplicate, duplicate-sprite,
export-sprite, export-texture, replace-sprite, replace-texture,
dump-sprites, preview-sprite, colorize-sprite, 导出, 替换, 换色, 复制,
GML, script, code, decompile, decompile-code, 脚本, 代码,
append-code, prepend-code, replace-code, create-script,
find-replace-code, search-vars, search-sctext, search-strings,
npc, quest, battlegroup, battle, create-battle, quest-init, quest-status,
支线, 任务, 战斗, NPC,
door, portal, create-door, list-doors, remove-door, 传送门, 门,
experiment, snapshot, sandbox, backup, undo, 快照, 备份, 恢复, 回滚,
sans, papyrus, toriel, flowey, undyne, alphys, asgore, mettaton, asriel,
dialoguer, OBJ_WRITER, msg, scr, scr_msgup, choice, YES, NO,
global.flag, flag, murderlv, judgement, 审判,
string, add-string, set-string, delete-string, search-strings,
room-list, list-backups, reset-all, auto-snapshot,
sandbox-restore, experiment-snapshot, experiment-list, experiment-restore,
ASCII, ascii, 英文, 中文限制, 字体
```

## 技能版本

2.1.1

## 适用平台

- **OpenCode** — Agent Skill 原生支持，自动发现
- **Codex** — 兼容 Agent Skill 标准
- **Claude Code** — 兼容 `.claude/skills/` 目录
- **Cursor** — 兼容 `.agents/skills/` 目录
- **终端/命令行** — `python run.py` 直接使用

## 前提条件

| 组件 | 要求 | 安装方式 |
|---|---|---|
| **Python 3.10+** | 必选 | [python.org](https://python.org) |
| **.NET 10 SDK** | `data_win` 命令必选 | 安装脚本自动安装 |
| **UndertaleModTool CLI** | `data_win` 命令必选 | `python install.py --utmt` 一键完成 |

### 一键安装

选择你的平台，运行一次即可：

| 平台 | 入口 | 说明 |
|------|------|------|
| **macOS** | 双击 `Install.app` | 检测环境 → 没装齐则补全 → 秒装 Agent Skill |
| **Windows** | 双击 `install.bat` | 同上 |
| **Linux** | `bash install.sh` | 同上 |
| **已有 Python** | `python3 install.py` | 同上 |

安装脚本自动处理：
1. Agent Skill 安装（符号链接到 agent 配置目录）
2. .NET SDK 检测与安装（对话/脚本编辑需要）
3. UndertaleModTool CLI 克隆与编译
4. `UTMT_CLI` 环境变量配置

所有平台入口最终都调用同一个 `install.py`：

```bash
python install.py             # 交互式安装（推荐）
python install.py --auto      # 智能模式：体检 → 就绪仅装 Skill，否则自动补全全部
python install.py --all       # 自动安装全部（跳过确认）
python install.py --check     # 只读环境体检（不修改任何文件）
python install.py --update    # 更新/修复（重指向 Skill 链接、重建 UTMT）
python install.py --uninstall # 卸载（删除 Skill 链接与环境变量）
```

### 单独安装组件

```bash
python install.py --skill   # 仅安装 Agent Skill
python install.py --dotnet  # 仅安装 .NET SDK
python install.py --utmt    # 仅编译 UTMT CLI
python install.py --env     # 仅配置环境变量
python install.py --yes     # 配合以上命令自动确认所有提示
```

## 文件结构

```
deterline/
├── run.py                ← 快捷入口（python run.py --action ...）
├── install.py            ← 一键安装脚本
├── install.sh            ← Linux 安装入口
├── install.bat           ← Windows 安装入口
├── Install.app/          ← macOS 安装入口
├── SKILL.md              ← 技能描述文件（本文档）
├── COMMANDS.md           ← 常用指令速查
├── QUESTIONNAIRE_WORKFLOW.md ← 问卷工作流（Agent 必读）
├── README.md
├── LICENSE
├── requirements.txt
├── .gitignore
└── scripts/
    ├── modify_save.py    ← 核心修改脚本（房间编辑、GML 注入）
    ├── bg_generator.py   ← 像素背景生成器（PIL，5 种图案）
    ├── rooms.json        ← 244 个房间 ID ↔ 中文名称映射
    └── rooms_reverse.json
```

---

## 命令总览

### 📁 存档编辑（`--file ini` / `--file file0`）

| 命令 | 功能 |
|---|---|
| `get --key Love` | 读取 INI 键值 |
| `set --key Love --value 20` | 修改 INI（`Room` 自动同步 file0） |
| `set --key Room --value "托丽尔的家"` | 支持中文房间名 |
| `list` | 列出 INI 全部配置 |
| `find --value 4 --file file0` | 在 file0 中搜索数值 |
| `set --key HP --value 50 --file file0` | 修改 file0 属性 |
| `set --key WEAPON --value 52 --file file0` | 换武器（自动计算 AT） |
| `set --key TORIEL --value 5 --file file0` | 修改 Boss 状态 |
| `room-list --value "雪镇"` | 搜索/列出房间 |
| `room-list` | 列出全部房间 |
| `reset-flags` | 重置屠杀线标记 |
| `reset-all` | **全量重置**（BOSS、物品、击杀、plot），保留自定义 flag |
| `create-system-info --value 962` | 创建屠杀线结局标记 |
| `undo --value ini` / `file0` / `data_win` | 从 `.bak` 恢复 |
| `undo --value data_win --backup 20240714_193500` | 恢复到指定时间戳版本 |
| `list-backups --value data_win` | 列出所有备份 |

### 💬 对话文本编辑（`--file data_win`）

通过 UTMT CLI 编辑游戏字符串表（STRG），**无长度限制**。

| 命令 | 功能 |
|---|---|
| `list-strings --limit 30` | 列出字符串 |
| `get-string --key 500` | 查看指定字符串 |
| `set-string --key 500 --value "新文本"` | 替换（无长度限制） |
| `add-string --value "新对话"` | **新增字符串，返回索引** |
| `delete-string --key 50000` | **删除字符串** |
| `search-strings --value "Toriel"` | 搜索 |
| `replace-string --old "A" --value "B"` | 批量替换 |

### 📜 脚本编辑（`--file data_win`）

将游戏 GML 字节码反编译为可读源码，修改后重新编译。**支持 6272 个游戏脚本。**

| 命令 | 功能 |
|---|---|
| `list-codes --limit 10` | 列出脚本名 |
| `decompile-code --key "gml_Script_xxx"` | 反编译为 GML 源码 |
| `replace-code --key "脚本名" --value "GML"` | **替换整个脚本后重编译** |
| `replace-code --key "脚本名" --value "file.gml" --file-path` | 从文件加载 GML |
| `find-replace-code --key "脚本" --old "旧" --value "新"` | **源码搜索替换后重编译** |
| `create-script --key "gml_Script_xxx" --value "GML"` | **创建全新脚本，自动注册** |

### 🗺️ 文本数据表（`--file data_win`）

管理 `global.text_data_en` 映射表——**游戏所有文本的中央数据库（16457 行 GML，158 万字符）。**

| 命令 | 功能 |
|---|---|
| `search-textdata --value "sans"` | 搜索 textdata key |
| `add-textentry --key "obj_xxx" --value "文本/"` | **新增对话条目（自动去重）** |
| `delete-textentry --key "obj_xxx"` | 按 key 删除条目 |

### 🔍 跨脚本搜索（`--file data_win`）

| 命令 | 功能 |
|---|---|
| `search-vars --value "global.flag"` | **在所有 6272 个脚本中搜索变量引用** |
| `room-objects --value "torielroom"` | **列出房间内的全部对象实例** |

### 🏗️ 房间布局编辑（`--file data_win`）

在任意房间生成或移除游戏对象实例，不限于原本就在该房间的对象。

| 命令 | 功能 |
|---|---|
| `spawn-obj --value "room_asrielroom" --key "obj_dummy1" --x 160 --y 120` | 在房间指定坐标生成对象 |
| `remove-obj --value "room_asrielroom" --instance 113930` | 按实例 ID 移除 |
| `remove-obj --value "room_asrielroom" --key "obj_dummy1"` | 按对象类型移除第一个 |
| `remove-obj --value "room_asrielroom" --key "obj_dummy1" --all` | 移除该类型全部实例 |
| `npc-dialogue --value "room_torielroom" --key "obj_cactus" --x 170 --y 180 --text-key "obj_cactus_hi" --text "* Hi/%%"` | **一键安全 NPC 对话**：加对话 + 生成实例 + 注入 `deterline_state` 距离触发 + 自动守卫 Alarm_0。默认 = **对话期间锁移动 + 走开后可再次触发** |
| `npc-dialogue --value "room_asrielroom" --key "obj_dummy1" --x 170 --y 180 --text-key "obj_dummy_hi" --text "* Hi/%%" --once` | **单次触发**：对话期间锁移动（`global.interact=1`），结束后解锁且**不再触发**（永久只一次） |
| `guard-npc-alarm --key "obj_cactus" --instance 113927` | 给已有冲突 NPC 补 `Alarm_0` 守卫（幂等） |
| `verify-nsid` | 检查损坏变量 NameStringID（读取会崩溃的陷阱）；`--fix` 自动修复 |

注意事项：
- 修改的是 `game.ios/data.win` 中的房间布局数据，不是存档
- 新实例在**重新进入房间时加载**，不立即生效
- 建议操作后用 `set --key Room --value 房间ID` 传送触发刷新
- 用 `room-objects` 查看实例 ID 后再 `remove-obj --instance`
- 生成的实例保留完整的对象行为（碰撞、事件、交互、AI）
- `npc-dialogue` 一律用 `deterline_state` 状态机（普通对象与原生 readable 对象都安全），原生 readable 对象额外加 `Alarm_0` 守卫（自动在 Create 事件初始化 `deterline_state = 0;`，防止 NSID 损坏崩溃）
- **默认触发行为**：靠近(<50px)触发，对话期间**锁移动**（`global.interact=1`，头像/文字不会与文本框错位），按 Z 关闭后**不会立即重触发**，需**走开(>60px) 再靠近**才能再次触发。需要"只看一次"用 `--once`
- 可用 `--sandbox` 做安全测试，确认无误后 `sandbox-restore` 恢复

### 🎨 精灵/对象编辑（`--file data_win`）— P4-1

浏览和修改游戏对象的 Sprite 引用，用已有精灵更换 NPC 动作。

| 命令 | 功能 |
|------|------|
| `list-sprites --limit 30` | 列出所有精灵（名称、尺寸、帧数、类型） |
| `search-sprite --value "sans"` | 按名称搜索精灵 |
| `get-obj --key "obj_sans_actor"` | 查看对象属性：当前精灵、尺寸、可见性、深度、父类、事件数 |
| `set-obj-sprite --key "obj_sans_actor" --value "spr_sans_dangerous"` | **切换对象的 Sprite 引用**（用已有精灵换动作，全局影响所有实例） |

**注意事项**：
- `set-obj-sprite` 修改对象定义，影响该对象的所有实例（全局）
- 精灵尺寸一致（如 25x32 ↔ 25x32）时碰撞盒无偏移风险
- 用 `search-sprite` 和 `get-obj` 先确认可用精灵和目标对象
- 建议用 `--sandbox` 测试

### 🏗️ 房间编辑（P4-2）

创建、查看和修改游戏房间。**关键约束：View 必须 320×240（port 640×480，2x 缩放）**。设成 640×480 会导致视角跟随失效。

| 命令 | 功能 |
|------|------|
| `create-room --value "room_myarea" --width 640 --height 480` | 创建新房间（View 自动 320×240） |
| `room-info --value room_myarea` | 显示房间全部属性 |
| `set-room-prop --value room_myarea --caption "标题"` | 修改房间属性（可选 `--width`/`--height`/`--speed`） |
| `set-room-view --view-w 320 --view-h 240 --port-w 640 --port-h 480 --follow obj_mainchara` | 配置摄像机 |
| `room-objects --value "torielroom"` | 列出房间内的对象 + 事件 |
| `spawn-obj --value "room_xxx" --key "obj_dummy1" --x 160 --y 120` | 在房间生成对象 |
| `remove-obj --value "room_xxx" --key "obj_solidtall" --all` | 移除指定类型的全部对象 |
| `remove-tile --value room_xxx` | 清除房间全部 Tile |
| `gml-bg --value room_xxx --bg "bg_asset" --slot 0 --speedx 0.5` | **注入运行时背景 GML + 视差**（替代 set-room-bg） |
| `bg_generator.py` | PIL 像素背景生成（独立脚本，5 种图案） |
| `create-bg-asset --value "bg_my" --image "bg.png"` | 将 PNG 注入为游戏背景资产 |
| `list-game-bgs` | 列出所有可用背景资产 |

**房间改造工作流（已验证）**：
```
1. remove-obj --all + remove-tile 清空房间
2. set-room-prop --width 640 --height 480     ← 房间 > View 才有滚动空间
3. set-room-view --view-w 320 --view-h 240    ← View=320×240！不可用 640×480
    --port-w 640 --port-h 480
    --follow obj_mainchara
4. spawn-obj 主角 + 碰撞墙
5. 直接 CSX 铺设 Tile 地面
6. gml-bg 注入运行时背景 + 视差
7. set --key Room "房间ID" → 进入验证
```

**注意事项**：
- `set-room-bg` 修改 ROOM 数据但 Undertale 运行时忽略背景设置，请用 `gml-bg`
- View 的 width/height 必须是 320×240（经过 S2 大量实验验证）
- `remove-tile` 不传 `--instance` 时清除所有 Tile
- `gml-bg` 将代码注入 `obj_mainchara_Step_0`，代码每帧执行设置背景和视差

### 🖼️ 纹理替换（`--file data_win`）— P4-1-1

导出精灵纹理为 PNG → 编辑 → 替换回游戏，实现**自定义美术内容**。

| 命令 | 功能 |
|------|------|
| `list-textures --limit 10` | 列出 26 张嵌入纹理图谱（名称、尺寸） |
| `export-sprite --key "spr_sans_d" --value "out.png" --frame 0` | 导出精灵单帧为 PNG |
| `export-sprite --key "spr_sans_d" --value "out_dir/"` | 导出精灵全部帧到目录 |
| `replace-sprite --key "spr_sans_d" --value "edit.png" --frame 0` | **替换精灵单帧纹理**（合成回纹理图谱对应区域） |
| `export-texture --key "Texture 0" --value "out_dir/"` | 导出单个纹理图谱为 PNG |
| `export-texture --value "out_dir/"` | 导出全部 26 个纹理图谱到目录 |
| `replace-texture --key "Texture 0" --value "tex.png"` | **替换整个纹理图谱**（影响该图谱上所有精灵） |
| `dump-sprites --value "out_dir/"` | 批量导出全部 2583 个精灵（UTMT CLI 内置） |

**纹理替换工作流**：
```
export-sprite --key "spr_sans_d" --value "sans.png" --frame 0
  → (用 PIL / Photoshop / Aseprite 编辑 PNG)
replace-sprite --key "spr_sans_d" --value "sans_edit.png" --frame 0 --sandbox
  → 进游戏验证
sandbox-restore  (不满意就恢复)
```

**技术细节**：
- 2583 个精灵共享 26 张纹理图谱（Texture 0~25）
- 每张纹理图谱 1024x1024 ~ 2048x2048 像素
- `replace-sprite` 只替换精灵在纹理图谱上对应 SourceX/Y/Width/Height 的区域，不影响同图谱其他精灵
- 编辑 PNG 会自动 Resize 匹配原尺寸
- 替换后通过 `GMImage` 自动处理格式转换（QOI/BZ2 等）
- 已验证无损循环：`export-texture → replace-texture → export-texture` MD5 完全一致

---

### 🔒 沙箱模式

在不修改原 `game.ios` 的情况下测试修改：

```bash
# 在副本上操作
python run.py --action spawn-obj --value "room_asrielroom" --key "obj_dummy1" --sandbox --file data_win

# 确认效果后，恢复副本到原文件
python run.py --action sandbox-restore
```

沙箱自动创建 `game.ios.sandbox` 作为工作副本，所有操作只影响副本。

---

## 关键架构发现

### 对话系统

```
textdata_en (ds_map, 16457 行 GML)
  ↓
scr_gettext("obj_npc_key")    ← NPC 事件代码
  ↓
global.msg[0] = "对话文本/"
  ↓
instance_create(0, 0, obj_dialoguer)  →  OBJ_WRITER 渲染
```

- 所有对话文本集中在 `gml_Script_textdata_en` 这一个脚本
- 格式：`ds_map_add(global.text_data_en, "key", "文本/%%")`

### 完整文本控制符表

| 控制符 | 作用 | 示例 |
|--------|------|------|
| `* ` | 对话前缀（**必需**，否则不渲染） | `"* 文字/"` |
| `/` | 翻页标记（中间页以此结尾） | `"* 第一页/* 第二页/%%"` |
| `/%%` | 末页标记 | `"* 最后一页/%%"` |
| `%%%` | msg 数组结束符（代码中用，非对话文本内容） | `global.msg[N] = "%%%"` |
| `&` | 换行 | `"* 第一行&* 第二行/"` |
| `^N` | 暂停 N 帧（N 是数字，`^120` = 暂停 2 秒） | `"* 停一下^120 再继续/"` |
| `\C ` | 在行尾创建 YES/NO 选择框（**后面必须带空格**） | `"* 确认？&  Yes No\C "` |
| `\R` | 红色文字 | |
| `\W` | 白色文字（默认） | |
| `\X` | 左侧白色文字（用于角色名） | `"\XI am\BTORIEL\X,.../"` |
| `\G` | 绿色文字 | |
| `\Y` | 黄色文字 | |
| `\B` | 蓝色文字 | |
| `\O` | 橙色文字 | |
| `\L` | 浅蓝色文字 | |
| `\P` | 粉色文字 | |
| `\F` + 数字 | **切换头像角色**（1-9） | `"\F3"` = Sans 脸 |
| `\E` + 数字 | **切换表情**（角色相关） | `"\E1"` = Sans 轻笑 |
| `\T` + 字符 | 切换打字速度 | `"\T0"`=标准, `"\Ts"`=慢, `"\TF"`=快 |
| `\M` + 数字 | 设置 `global.flag[20]` | `"\M1"` = flag[20]=1 |
| `\*` | 绘制按键图标（键盘提示） | |

### 头像/肖像系统

对话显示角色头像由 `global.facechoice` 和 `global.faceemotion` 控制。
`obj_dialoguer` 自动创建和销毁头像对象，无需手动清理。

**可用头像（内置 1-9 号槽，直接使用，稳定可靠）：**

| facechoice | 角色 | 设置方式 |
|-----------|------|---------|
| 0 | 无头像（仅文字） | `global.facechoice = 0` |
| 1 | Toriel | `global.facechoice = 1` |
| 2 | Flowey | `global.facechoice = 2` |
| **3** | **Sans ✅ 最稳定** | `global.facechoice = 3` |
| 4 | Papyrus | `global.facechoice = 4` |
| 5 | Undyne | `global.facechoice = 5` |
| 6 | Alphys | `global.facechoice = 6` |
| 7 | Asgore | `global.facechoice = 7` |
| 8 | Mettaton | `global.facechoice = 8` |
| 9 | Asriel | `global.facechoice = 9` |

**Sans 表情表（`faceemotion`）：**

| 值 | 表情 | 代码示例 |
|----|------|---------|
| 0 | 普通（默认） | `global.faceemotion = 0` |
| 1 | 轻笑 | `"\E1* 呵呵呵/"` |
| 2 | 眨眼 | `"\E2* wink/"` |
| 3 | 慢眨眼 | |
| 4 | 无眼（严肃/恐怖） | |

**在对话文本中切换头像与表情：**

```
"\F3\E1* 嘿，你好呀。/ \E0* 今天天气不错。/%%"
→ 第1页：Sans脸 + 轻笑 → 第2页：Sans脸 + 普通
```

设置 `facechoice` 和 `faceemotion` 后，dialoguer 自动在正确位置创建头像。
表情在渲染到 `\E` 字符时即时切换。

**重要：不要在对话文本外部创建自定义 face 对象（如 `obj_face_dummy`）。**
头像清理依赖 dialoguer 的 `with (obj_face)` 机制，自定义对象需要继承
`obj_face → obj_torface` 且管理复杂。**直接使用内置的 1-9 号头像。**

### 屠杀线判定（scr_murderlv）

```
global.flag[202] >= 20  →  遗迹清理完成 (mrd=1)
  + global.flag[45] == 4  →  Toriel 击杀 (mrd=2)
  + global.flag[52] == 1  →  (mrd=3)
  + ...  →  mrd=16  →  Sans 战
```

- `global.flag[]` 数组大小 = 512（索引 0-511，超出即崩溃）
- 修改 `scr_murderlv` 可直接控制路线判定（`replace-code`）

### 视角系统（P4-2 关键发现）

**View 必须 320×240（port 640×480，2x 缩放）**。这是 Undertale 所有房间的标准。设成 640×480 会导致：
- 房间 ≤ View → 引擎钳位 `view_xview` 到 0，视角看似"不跟随"
- 房间 > View → 画面缩放比异常（2x 变成 1x），人物变小

视角跟随由 GMS1 引擎自动处理，只需确保 `Views[0].ObjectId = obj_mainchara`（`create-room` / `set-room-view` 默认设置）。不需要手写 GML 代码控制视角。

### NPC 动画系统（实验 13/14 发现）

**对象动画控制链**：
```
Create_0: dsprite = spr_sans_d; rsprite = spr_sans_r; lsprite = spr_sans_l;
          image_speed = 0.334; fun = 0;
  ↓
Step_0:   scr_depth(...);
          if (fun == 0) {
            myinteract = 0;
            if (speed == 0) { image_index = 0; image_speed = 0; }
            if (speed > 0) { image_speed = 0.2; }
          }
  ↓
scr_npcdir(n):  如果 myinteract == 0 → sprite_index = dsprite/rsprite/lsprite/usprite (行走)
                如果 myinteract == (1+n) → sprite_index = dtsprite/rtsprite/ltsprite/utsprite (静止交互)
```

**安全 NPC 改造手法**（append-code / prepend-code 不覆盖原逻辑）：
```
Step 头部 prepend:  hspeed/方向控制          ← 不影响原 Step 的动画判断
Step 尾部 append:   sprite_index/fun 覆盖    ← 覆盖 scr_npcdir 的结果
Create 尾部 append:  初始化自定义变量         ← 不干扰原 Create 逻辑
```

**方向精灵命名约定**（4 帧 = 行走动画，1-2 帧 = 静止）：
| 命名 | 含义 |
|------|------|
| `spr_char_d` | 朝下（面向镜头）4 帧 |
| `spr_char_u` | 朝上（背向镜头）4 帧 |
| `spr_char_r` | 朝右 4 帧 |
| `spr_char_l` | 朝左 4 帧 |
| `spr_char_dt` / `ut` / `rt` / `lt` | 静止帧（1-2 帧） |
| 后缀 `_dark` / `_stark` | 黑暗区域变体 |

**巡逻 NPC 实现要素**（已验证：Sans 在地下室走廊左右行走）：
- `hspeed` = GameMaker 内置水平速度，自动每帧 `x += hspeed`
- 设 `hspeed ≠ 0` 后 `speed > 0` → 原 Step 自动启动 `image_speed = 0.2`
- 方向精灵切换：手动 `sprite_index = rsprite` / `lsprite`
- 边界检测 + 反转 hspeed + 切换方向精灵 → 完整的巡逻行为

### 纹理系统架构（P4-1-1 发现）

**三层结构**：
```
EmbeddedTexture (TXTR)   — 26 张，实际的图像数据（PNG/QOI）
  ↓
TexturePageItem (TPAG)   — 6550 个，定义精灵在纹理图谱上的裁剪区域
  ↓
Sprite (SPRT)            — 2583 个，逻辑精灵，每帧指向一个 TexturePageItem
```

**关键属性**（TexturePageItem）：
- `SourceX/Y/Width/Height`：精灵在纹理图谱上的像素区域
- `TargetX/Y/Width/Height`：精灵在渲染包围盒中的位置
- `BoundingWidth/Height`：精灵的渲染包围盒尺寸
- `TexturePage`：引用所属的 EmbeddedTexture

**替换单精灵纹理原理**（`replace-sprite`）：
1. 找目标 Sprite → 获取帧的 TextureEntry → TexturePageItem
2. 用 Magick.NET 将编辑 PNG 合成回纹理图谱的 `(SourceX, SourceY)` 位置
3. 更新 EmbeddedTexture 的图像数据
4. 同图谱上其他精灵不受影响（不同 SourceX/Y 区域）

### 自定义 NPC 完整工作流

推荐方法：用 `spawn-obj` 生成 NPC + `replace-code` 改写 Step 事件 + 距离自动触发。
无需改 Create 事件、不依赖玩家输入系统、不涉及复杂碰撞检测。

#### 步骤

```
1. spawn-obj   → 在目标房间放置 NPC
2. add-textentry → 添加对话到 textdata_en
3. replace-code → 改写 NPC 的 Step 事件（距离触发 + 状态机）
4. 进入游戏测试
```

#### 已知可用的 Hook 房间

| 中文名 | 内部名 | 房间 ID | 推荐生成对象 |
|--------|--------|---------|-------------|
| **你的房间（Frisk 卧室）** | `room_asrielroom` | 36 | `obj_dummy1` ✅ 已验证 |
| 托丽尔的房间 | `room_torielroom` | 35 | `obj_readable_room3` / `obj_cactus` |
| 审判长廊 | `room_sanscorridor` | 231 | `obj_backgrounder_pillar` |
| 遗迹（木偶房） | `room_ruins4` | 9 | `obj_dummy1` |
| 厨房 | `room_kitchen` | 37 | 任意可交互对象 |

#### 完整模板（三段支线 NPC）

以下代码实现：自动对话 → 求助选择 → 奖励/拒绝 三段式支线。

> ⚠️ **重要：不要用 `myinteract` 做距离触发状态变量。**
> 如果目标对象继承 `obj_readablesolid`/`obj_interactable`（如 `obj_cactus`、`obj_readable_*`），
> 其父类 `Step_0` 监视 `myinteract == 1` → 调度 `alarm[0]` → 弹默认对话，会与你的对话重叠成两个对话框。
> 用**每实例变量 `deterline_state`**，或用 `npc-dialogue` 命令自动生成。

> ⚠️⚠️ **`deterline_state` 必须先在 Create 事件中初始化！**
> 它**不是**"未赋值自动为 0"。新变量若只在 Step 中被引用，一旦 Step 被覆盖为不含它的代码，
> 其 `NameStringID` 会损坏为 0，游戏读取该变量时**直接崩溃**（UTMT 的引用链陷阱）。
> `npc-dialogue` / `guard-npc-alarm` 会自动在对象 Create 事件写入 `deterline_state = 0;`。
> 手工注入时必须自己做这步（或在 Create_0 末尾 `append-code` 加 `deterline_state = 0;`）。
> 可用 `verify-nsid` 检查 / `--fix` 修复损坏变量。

```gml
// ===== 改写到 NPC 的 Step_0 事件 =====
// 前置条件：对象 Create 事件必须含 `deterline_state = 0;`（否则读取崩溃）

// 1. 对话结束后重置
if (deterline_state == 1 && !instance_exists(OBJ_WRITER) && !instance_exists(obj_choicer))
{
    deterline_state = 0;
}

// 2. 处理 \C 选择结果（2 帧窗口截获）
if (global.choice != -1 && global.flag[510] == 2)
{
    if (global.choice == 0)
    {
        global.flag[510] = 3;  // YES 路线
        global.msc = -1;        // 阻止 SCR_TEXT 覆盖
        global.typer = 5;
        global.facechoice = 3;  // Sans 头像
        global.faceemotion = 1; // 开心
        global.msg[0] = scr_gettext("obj_quest_yes");
        global.msg[1] = "%%%";
        script_execute(scr_itemget, 48);  // 给物品
    }
    else
    {
        global.flag[510] = 4;  // NO 路线
        global.msc = -1;
        global.typer = 5;
        global.facechoice = 3;
        global.faceemotion = 0;
        global.msg[0] = scr_gettext("obj_quest_no");
        global.msg[1] = "%%%";
    }
    global.choice = -1;
}

// 3. 距离自动触发（替代 Z 键）——用 deterline_state，不用 myinteract！
var dist = distance_to_object(obj_mainchara);
if (dist >= 60)
{
    deterline_state = 0;   // 走远重置，可重复触发
}
if (dist < 50 && deterline_state == 0 && !instance_exists(OBJ_WRITER) && !instance_exists(obj_choicer))
{
    // 阶段 0：初次见面
    if (global.flag[510] == 0)
    {
        deterline_state = 1;
        global.flag[510] = 1;
        global.msc = 0;        // SCR_TEXT(0) = no-op
        global.typer = 5;
        global.facechoice = 3;
        global.faceemotion = 0;
        global.msg[0] = scr_gettext("obj_intro_01");
        global.msg[1] = scr_gettext("obj_intro_02");
        global.msg[2] = "%%%";
        instance_create(0, 0, obj_dialoguer);
    }
    // 阶段 1：求助（含 \C 选择）
    else if (global.flag[510] == 1)
    {
        deterline_state = 1;
        global.flag[510] = 2;
        global.msc = 0;
        global.typer = 5;
        global.facechoice = 3;
        global.faceemotion = 0;
        global.msg[0] = scr_gettext("obj_ask_01");
        global.msg[1] = scr_gettext("obj_ask_choice");  // 含 \C
        global.msg[2] = "%%%";
        instance_create(0, 0, obj_dialoguer);
    }
    // 阶段 2：YES 后续
    else if (global.flag[510] == 3)
    {
        deterline_state = 1;
        global.flag[510] = 5;  // 标记完成
        global.msc = 0;
        global.typer = 5;
        global.facechoice = 3;
        global.faceemotion = 1;
        global.msg[0] = scr_gettext("obj_quest_complete");
        global.msg[1] = "%%%";
        instance_create(0, 0, obj_dialoguer);
    }
    // 阶段 2：NO 后续
    else if (global.flag[510] == 4)
    {
        deterline_state = 1;
        global.flag[510] = 5;
        global.msc = 0;
        global.typer = 5;
        global.facechoice = 3;
        global.faceemotion = 0;
        global.msg[0] = scr_gettext("obj_quest_reject");
        global.msg[1] = "%%%";
        instance_create(0, 0, obj_dialoguer);
    }
}

// 4. 保持深度正确
script_execute(scr_depth);
```

**原生 readable 对象额外必做**：如果对象继承 `obj_readablesolid`/`obj_interactable`，还要在它的 `Alarm_0` 事件**头部**加守卫，阻止默认对话弹出：

```gml
if (id == <实例ID>)
{
    exit;
}
```

`guard-npc-alarm` 命令可自动完成这两步（守卫 + 改写 Step 为 flag 状态机）。

#### \C 选择机制的 2 帧窗口

`\C ` 在文本中创建 YES/NO 选择框。玩家选择后 `obj_choicer` 的 alarm 会在 2 帧后调用 `scr_msgup`，自增 `global.msc` 并执行 `SCR_TEXT`，可能覆盖已设置的 `global.msg[]`。

**关键点：**
- `global.msc = -1`：`scr_msgup` 自增到 0 → `SCR_TEXT(0)` 是空操作 → `msg[]` 不被覆盖
- 替换后的 `msg[0]` **不含 `\C`**，不会再次弹出选择
- `global.choice = 0` = 左选项（YES），`1` = 右选项（NO）
- 物品给予：`script_execute(scr_itemget, 物品ID)`

**对话框高度限制：**
- 含 `\C` 的选择文本总行数 ≤ **3 行**（含选项行）
- 格式：`"* 提问& &    选项1    选项2      \C "`（3 行：提问 + 空行 + 选项）

---

## 实验验证记录

### 实验 13：厨房旋转 Papyrus（P4-1 精灵替换）
- `spawn-obj` 在厨房生成 `obj_papyrus_room` → `set-obj-sprite` 为 `spr_papyrus_spin`
- 需在 Step 末尾 `append-code` 设 `fun=1` 解除 `image_index` 锁定，覆盖 `scr_npcdir` 的方向设置
- **教训**：坐标避免与已有对象（`obj_bigpie`）重叠；须了解目标对象的 Step 事件逻辑

### 实验 14：地下室 Sans 巡逻（P4-1 动画 NPC）
- `spawn-obj` + `prepend-code` 实现自主移动
- 利用原对象已预设的 `rsprite/lsprite` 和 `image_speed` 自动控制
- 设 `hspeed` 后原 Step 的 `if (speed > 0) image_speed = 0.2` 自动工作

### 实验 15：新实例变量 NSID 陷阱（崩溃根因）
- 现象：`npc-dialogue` 注入 `deterline_state` 状态机后，再次覆盖 Step 代码，游戏**读取即崩**
- 根因：新变量 `deterline_state` 只在 Step 中被引用 → Step 被覆盖为不含它的代码 → `Occurrences=0` → UTMT 序列化时 `NameStringID=0` → 之后任何引用都崩（写入不崩，读取崩）
- 决定性复现：创建含变量的脚本(NSID 正确) → 覆盖为不含变量的空代码(occ=0, NSID=0) → 再引用(NSID 仍=0)
- **修复**：在 Create 事件初始化 `deterline_state = 0;`（变量永远被引用，NSID 不再损坏）；或 `verify-nsid --fix` 把 NameStringID 重置为正确 STRG 索引
- 教训：**新实例变量必须先在 Create 事件初始化**；注入后跑 `verify-nsid` 验证

### 实验 A：Sans 走路变红（纹理替换管线验证）
- `export-sprite` → PIL 红蓝通道互换 → `replace-sprite`
- 确认精灵 frame 0/2 共享同纹理区域（SourceX/Y 相同）
- 结果：Sans 走路时红 X 闪烁（帧 0/2 有红 X，帧 1/3 无）

### 实验 B：对话框心形变青（UI 元素替换验证）
- `export-sprite` → PIL 全像素改色 → `replace-sprite`（帧 0 和帧 1）
- 跨纹理图谱（Texture 2）操作成功
- 结果：对话文本继续指示从红色心变为青色心

### 实验 C：纹理图谱无损循环验证
- `export-texture` → `replace-texture`（同一文件）→ `export-texture`
- 导出→回写→重导出 MD5 完全一致
- **结论**：`replace-texture` 无损，可安全用于纹理图谱级替换

---

## 原生 readable 对象（交互冲突注意）

下列对象**继承 `obj_readablesolid` / `obj_interactable`**，自带原生 Z 键/触碰交互系统：

| 对象 | 默认对话 |
|------|---------|
| `obj_cactus` | `obj_cactus_55` / `obj_cactus_58`（"Ah, the cactus..."） |
| `obj_readable_*` 系列 | 各自 `Alarm_0` 默认文本 |
| `obj_dummy1` 等 | 父链含 `obj_interactable` |

**原生交互链**（父类 `obj_readablesolid_Step_0`）：
```
玩家 Z 键/触碰 → scr_interact → myinteract = 1
  → 父类 Step_0 检测 myinteract == 1 → alarm[0] = 1 → Alarm_0 → 弹默认对话
```

**冲突根因**：在 Step 事件里设 `myinteract = 1` 做距离触发，会同时被父类 Step_0 捕获 → 默认对话 + 你的对话两个对话框重叠。

**正确做法（二选一）**：
1. 用 `npc-dialogue` 命令（自动用 `deterline_state` 状态机 + `Alarm_0` 加 `if (id == N) exit;` 守卫）
2. 手工：Step 用 `deterline_state`/`flag[510]` 状态机（不要碰 `myinteract`）+ `Alarm_0` 头部加 `if (id == <实例ID>) exit;`

**如何识别**：`get-obj --key obj_xxx` 会显示完整父链并打印警告；`spawn-obj` 生成这类对象时也会提示。

---

## 已知可靠的交互模式

### ✅ 距离自动触发
```
distance_to_object(obj_mainchara) < 50
```
任意对象的 Step 事件中检测玩家距离。不依赖 Z 键，对话结束后自动重置。
已验证：`obj_dummy1` 在 `room_asrielroom` 中正常工作。

> ⚠️ **用每实例变量 `deterline_state`（或 `global.flag[510]`）做状态，不要用 `myinteract`。**
> 若对象继承 `obj_readablesolid`/`obj_interactable`，设 `myinteract = 1` 会触发父类默认对话造成重叠。
> 用 `npc-dialogue` 命令可自动生成安全代码。
> **⚠️ `deterline_state` 必须先在 Create 事件初始化（`deterline_state = 0;`），否则变量未被注册时读取会崩溃。**

### ✅ Z 键交互（仅限游戏内置对象）
适用于 `obj_cactus`、`obj_readable_*`、`obj_dummy1` 等。
`scr_interact` 系统自动处理。**自定义对象不能用此方式**，因为碰撞检测写死在玩家对象中。
这些内置对象自带 `Alarm_0` 默认对话 —— 若要注入自定义对话，必须给 `Alarm_0` 头部加 `if (id == <实例ID>) exit;` 守卫（`guard-npc-alarm` 命令可自动完成）。

### ✅ 物品给予
```gml
script_execute(scr_itemget, 物品ID);
```
物品 ID 见 `modify_save.py` 的 `ITEMS` 字典。

### ✅ 游戏重启
```gml
ini_write_real(...);       // 写 INI
ossafe_savedata_save();    // 保存存档
game_restart();            // 重启游戏
```

### ❌ control_check_pressed
在非 `obj_mainchara` 对象中无效。

### ❌ 自定义 face 对象
添加新的头像插槽（如 `facechoice=10`）涉及父类继承 `obj_face→obj_torface` 和对话框清理逻辑，不稳定。**勿用，直接使用内置 1-9 号头像。**

---

## 保留 flag（自定义事件专用）

为避免与游戏主线 flag 冲突，以下两个 flag 索引被保留供自定义事件使用：

| flag 索引 | file0 索引 | 用途 |
|---|---|---|
| `global.flag[510]` | 539 | 自定义事件状态机（0=未触发, 1=已触发, 10+=阶段） |
| `global.flag[511]` | 540 | 备用（\C 选择、定时器等） |

**请勿在自定义事件中使用其他 flag 索引。**

---

## 安全机制

| 机制 | 说明 |
|---|---|
| `.bak.{时间戳}` 备份 | 每次修改前创建时间戳备份，可 `list-backups` 查看 |
| `add-textentry` 幂等 | 自动检测 key 是否已存在，防止重复 |
| `global.flag` 越界警告 | 索引超出 0-511 时打印警告 |
| `add-textentry` 格式校验 | 自动检查对话是否以 `/`、`%%` 或 `\C` 结尾 |
| `backup_file` + `undo` | 两步回滚机制：`.bak`（最新）+ `.bak.{ts}`（历史） |
| WEAPON/ARMOR 自动 AT/DF | 设置装备时自动同步加成值 |
| `undo --value data_win` | 恢复 `game.ios` 到修改前状态（用 `.bak.时间戳` 可恢复到指定版本） |
| `remove-obj --instance ID` | 精确移除单个实例，不影响其他对象 |
| **沙箱模式** `--sandbox` | 在 `game.ios.sandbox` 副本上操作，原文件不受影响。用 `sandbox-restore` 恢复 |
| **`verify-nsid` 变量体检** | 检查损坏的变量 NameStringID（读取会崩溃的陷阱），`--fix` 自动修复 |
| **变量自动初始化** | `npc-dialogue`/`guard-npc-alarm` 自动在 Create 事件写 `deterline_state = 0;`，防止新变量 NSID 损坏崩溃 |
| **精灵搜索推荐** `search-sprite` | 找不到精灵时自动推荐相似名称 |
| **对象搜索推荐** `get-obj` | 找不到对象时自动推荐相似名称 |
| **多匹配提示** | 名称模糊匹配时打印 `(found N matches, using: ...)` |
| **`replace-sprite` 自动 Resize** | 编辑 PNG 自动缩放匹配源精灵尺寸 |
| **`filename` 起名建议** | 文件名不合预期时自动修正 |

## 注意事项

1. **UndertaleModTool 必须预先编译**，`UTMT_CLI` 环境变量必须设置
2. `replace-code` 会覆盖整个脚本——先用 `list-backups` 确认有备份
3. `global.flag[]` 索引范围 0-511，**不要使用 512+**，游戏会崩溃
4. 自定义事件仅使用保留 flag **510** 和 **511**，避免与主线剧情冲突
5. 对话文本必须包含 `* ` 前缀，否则引擎不渲染
6. 中间页以 `/` 结尾，末页以 `/%%` 结尾
7. **英文版 Undertale 不支持中文字符**。添加的对话文本必须使用英文（ASCII），中文字符不渲染（显示为空白 `*`）
8. `spawn-obj` 修改的是 `game.ios`/`data.win` 的房间布局数据，**不是存档**。新实例在重新进入房间时加载
9. `spawn-obj` 生成的实例保留原始对象的完整行为（AI、碰撞、交互），可能包含战斗触发等逻辑。建议先 `room-objects` 确认对象行为
10. `\C` 的选择文本总行数（含选项）≤ 3 行，超过会导致选项溢出对话框
11. `global.msc = 0`：`SCR_TEXT(0)` 是空操作，不会覆盖 `global.msg[]`
12. `global.msc = -1`：`scr_msgup` 自增到 0，2 帧窗口截获 `\C` 选择
13. 使用头像时 `facechoice` 设为内置角色（1-9），**不要自定义 face 对象**
14. **房间 View 必须 320×240（port 640×480）**。设成 640×480 会导致视角跟随失效，2x 缩放异常。`create-room` 自动使用此设置
15. `set-room-bg` 修改 ROOM chunk 数据，但 Undertale 运行时会忽略背景设置（改完进游戏看不到变化）。请用 `gml-bg` 注入运行时背景
16. `gml-bg` 将代码注入 `obj_mainchara_Step_0`，每帧执行设置背景和视差。一次注入永久生效，直到代码被清除
17. 跨平台：macOS/Windows 路径自动识别
18. Skill 通过符号链接安装，工作区修改自动同步到 OpenCode
19. `set-obj-sprite` 修改对象定义，影响所有实例。如需实例级只改一个 NPC，用 GML `sprite_index` 运行时赋值
20. `replace-sprite` 修改纹理图谱对应区域，帧 0 和帧 2 可能共享同纹理区域（SourceX/Y 相同）
21. `replace-texture` 替换整个纹理图谱，影响该图谱上所有精灵。确认无误再操作
22. 纹理编辑后 PNG 会自动 Resize 匹配原精灵尺寸，但建议保持原尺寸编辑以保真
23. 英文版 Undertale 的字体精灵不包含中文字形，替换文字纹理无法解决中文显示问题
24. **新实例变量必须先初始化**：注入用到新变量（如 `deterline_state`）的代码前，务必在对象 Create 事件写 `变量 = 0;`。否则变量未被正确注册（NameStringID=0）时读取会崩溃。用 `npc-dialogue`/`guard-npc-alarm` 会自动处理；`verify-nsid --fix` 可修复已损坏变量
25. `npc-dialogue` 默认与 `--once` **都锁移动**：对话期间 `global.interact=1`，头像/文字不会与文本框错位；按 Z 关闭后默认需**走开(>60px) 才可再次触发**，`--once` 则**永久只触发一次**。不要用 `myinteract` 手写距离触发（会在对话结束瞬间立即重触发 + 不锁移动导致错位）

## 工作流（Agent 必读）

在每次执行修改操作前，必须先打开 `QUESTIONNAIRE_WORKFLOW.md`，按照其中的决策树向用户逐步收集参数。禁止凭猜测执行操作。

### 标准流程

```
用户请求 → Agent 打开 QUESTIONNAIRE_WORKFLOW.md
         → 匹配入口分类（1-9）
         → 按问卷逐项向用户提问
         → 用户提供参数
         → 映射到 CLI 命令
         → 确认汇总 → 执行
         → 如果失败，用 `experiment-restore` 回滚
```

### 必须遵循的规则

1. **不要跳过问卷步骤**。即使用户说"随便"或"你决定"，也必须至少问一遍所有参数，用户可以给默认值但必须确认
2. **每个参数问清楚再继续**。比如加对话时必须问：key、文本内容（英文）、头像角色、头像表情
3. **遇到模糊指令时使用问卷纠偏**。例如用户说"加个对话" → 问卷强制补问 key/内容/头像
4. **所有文本必须是纯 ASCII**。检查无中文字符后再执行
5. **先快照再执行**。任何写操作前先 `experiment-snapshot`
6. **执行后验证**。用对应的 `list-*` / `room-objects` / `decompile-code` 命令验证结果
