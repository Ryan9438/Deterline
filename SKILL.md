---
name: deterline
description: >
  Modify UNDERTALE game saves — change LOVE, Kills, Room, HP, ATK, DEF, Gold,
  edit undertale.ini or file0, reset genocide route flags, jump to any room,
  modify dialogue text, edit GML code, add custom dialogue events, spawn NPCs,
  create side quests, or inspect game objects.
  Trigger keywords:
  undertale, save, LOVE, Kills, Room, HP, ATK, DEF, Gold, file0,
  undertale.ini, genocide, flags, reset, item, boss, weapon, armor,
  dialogue, GML, script, text, textdata, sans, judgement, room objects,
  spawn, npc, quest, battle, face, portrait, sandbox.
---

# Deterline

> ⚠️ 非官方粉丝作品 · Fan-made project.
> Not affiliated with Toby Fox or Fangamer. UNDERTALE is © Toby Fox.

修改《传说之下》(UNDERTALE) 游戏存档 + 游戏数据的全能工具——Deterline。支持存档属性修改、**对话文本自由增删改查**、**GML 脚本反编译与重编译**、**房间布局编辑**、**自定义 NPC 支线**（头像 + 多段对话 + 选择分支 + 战斗 + 物品奖励）。

## 技能版本

2.0.0

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

### 单独安装组件

```bash
python install.py --skill   # 仅安装 Agent Skill
python install.py --dotnet  # 仅安装 .NET SDK
python install.py --utmt    # 仅编译 UTMT CLI
python install.py --env     # 仅配置环境变量
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
├── README.md
├── LICENSE
├── requirements.txt
├── .gitignore
└── scripts/
    ├── modify_save.py    ← 核心修改脚本
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

注意事项：
- 修改的是 `game.ios/data.win` 中的房间布局数据，不是存档
- 新实例在**重新进入房间时加载**，不立即生效
- 建议操作后用 `set --key Room --value 房间ID` 传送触发刷新
- 用 `room-objects` 查看实例 ID 后再 `remove-obj --instance`
- 生成的实例保留完整的对象行为（碰撞、事件、交互、AI）
- 可用 `--sandbox` 做安全测试，确认无误后 `sandbox-restore` 恢复

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

```gml
// ===== 改写到 NPC 的 Step_0 事件 =====

// 1. 对话结束后重置
if (myinteract == 1 && !instance_exists(OBJ_WRITER) && !instance_exists(obj_choicer))
{
    myinteract = 0;
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

// 3. 距离自动触发（替代 Z 键）
var dist = distance_to_object(obj_mainchara);
if (dist < 50 && myinteract == 0 && !instance_exists(OBJ_WRITER) && !instance_exists(obj_choicer))
{
    // 阶段 0：初次见面
    if (global.flag[510] == 0)
    {
        myinteract = 1;
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
        myinteract = 1;
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
        myinteract = 1;
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
        myinteract = 1;
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

## 已知可靠的交互模式

### ✅ 距离自动触发
```
distance_to_object(obj_mainchara) < 50
```
任意对象的 Step 事件中检测玩家距离。不依赖 Z 键，对话结束后自动重置 `myinteract = 0`。
已验证：`obj_dummy1` 在 `room_asrielroom` 中正常工作。

### ✅ Z 键交互（仅限游戏内置对象）
适用于 `obj_cactus`、`obj_readable_*`、`obj_dummy1` 等。
`scr_interact` 系统自动处理。**自定义对象不能用此方式**，因为碰撞检测写死在玩家对象中。

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
14. 跨平台：macOS/Windows 路径自动识别
15. Skill 通过符号链接安装，工作区修改自动同步到 opencode
