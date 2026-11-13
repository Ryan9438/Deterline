---
name: deterline
description: "Deterline is an all-in-one modding tool for UNDERTALE (传说之下). Edit save files (HP, LOVE, gold, weapons, armor, room teleport, genocide reset); create and edit rooms with backgrounds, tiles and camera views; replace sprites and textures (export/import PNG, recolor via HSV, duplicate); add custom NPCs with dialogue, portraits, YES/NO choices, quests and battles; edit GML scripts (decompile, replace, append, prepend, create new); manage dialogue text; set up portals between rooms; generate pixel backgrounds. Use when the user wants any UNDERTALE modding task: 改存档, 改属性, 改HP, 换武器, 传送, 传送到某房间, 建房间, 做新场景, 做地图, 换背景, 设置背景, 加背景, 加对话, 改对话, 加NPC, 做支线, 做任务, 放传送门, 开门, 触发战斗, 给物品, 换精灵, 改贴图, 导出图片, 导入图片, 换色, 调色, 复制精灵, 生成背景, 像素背景, 替换纹理, 重置屠杀线. Dialogue text is ASCII-only by default (the stock bitmap font has no CJK glyphs); CJK input is accepted via --allow-cjk but renders blank until the CJK font patch ships."
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
set-derived, derived stat, 固定属性, 锁属性, maxhp, 最大生命,
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
npc, quest, battlegroup, battle, create-battle, quest-init, quest-status, (create-room 已废弃禁用),
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

2.5.0

## 适用平台

- **OpenCode** — Agent Skill 原生支持，自动发现
- **Codex** — 兼容 Agent Skill 标准
- **Claude Code** — 兼容 `.claude/skills/` 目录
- **Cursor** — 兼容 `.agents/skills/` 目录
- **终端/命令行** — `python run.py` 直接使用

## 前提条件

> 注：文档引用的 `AUDIT_2026-11-07/域X`、`01-ROADMAP` 章节号出自本地验证文档库（不随本仓库发布）。

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
    ├── modify_save.py    ← 兼容 shim（纯 re-export；实现已拆入 deterline/）
    ├── deterline/        ← 实现包（O2 拆包，v2.3.1）
    │   ├── cli.py        ← argparse 入口（命令注册表在 command_handlers.py）
    │   ├── errors.py / config.py / state.py / paths.py
    │   │                 ← 叶子层（异常 / 常量表 / 运行旗标单点 / 路径定位）
    │   ├── utmt.py       ← UTMT CLI 脊柱（_run_utmt / 沙箱重定向 / V2 写入策略）
    │   ├── rooms_data.py / inifile.py / file0.py   ← save 层三件
    │   └── cmds/         ← 九命令域：save_cmds / dialogue / code / room /
    │                        npc / door / sprite / verify / cjk
    ├── bg_generator.py   ← 像素背景生成器（PIL，5 种图案）
    ├── rooms.json        ← 244 个房间 ID ↔ 中文名称映射
    └── rooms_reverse.json
```

---

## 命令总览

<!-- BEGIN generated:commands (SSOT: scripts/commands.json · python3 tools/gen_docs.py 生成，勿手改) -->
> 全量 89 个命令 · 版本 2.5.0 · 由 `scripts/commands.json` 生成（改命令表 → 改 json → `python3 tools/gen_docs.py`）
> 验证级别（验收总原则，见 AUDIT_2026-11-07/01-ROADMAP §六）：**static** = 反编译/代码审查 · **sandbox** = 沙箱副本注入实测 · **in-game** = 游戏内启动实测

### 📁 存档编辑 — --file ini / --file file0，零依赖立即可用

| 命令 | 功能 | 验证 |
|---|---|---|
| `get --key Love` | 读取 INI 键值（--file file0 读核心属性） | static |
| `set --key Love --value 20 --file file0` | 修改属性。Love/Kills/Room 自动同步 file0；HP/EXP/GOLD 等核心属性必须 --file file0；Room 支持中文房间名（须唯一名） | static |
| `list` | 列出 INI 全部配置（--file file0 列 file0） | static |
| `find --value 42 --file file0` | 在存档中按值搜索（file0 数值搜索） | static |
| `set-derived --key HP --value 50` | 固定由 LV 推导的属性（HP/AT/DF/MAXHP）：写 file0 并改写游戏脚本阻止重算 | sandbox |
| `reset-flags` | 重置屠杀线标记 | static |
| `reset-all` | 全量重置（Boss/物品/击杀/plot），保留自定义 flag | static |
| `create-system-info --value 962` | 创建屠杀线结局标记（962/963） | static |
| `room-list --value "雪镇"` | 搜索/列出房间（支持中文模糊搜索） | static |
| `undo --value data_win` | 从 .bak 恢复最后一次写入（仅一步；--backup 指定时间戳版本） | static |
| `list-backups --value data_win` | 列出所有备份（--value ini\|file0\|data_win） | static |
| `doctor --file data_win` | 聚合体检（全只读零写盘）：rooms.json 健康 / 存档可解析 / 游戏文件 md5 与仓库基线比对 / 备份占盘 / 沙箱残留 / UTMT CLI 与 dotnet 可达 / CJK 字形表状态；退出码 全✓0/有✗1 | static |
| `backup-prune --keep-archives 3` | 保留策略预览（03 §2.4，只读零删除）：占盘统计 + 内容重复分组（sha256）+ 超窗归档清理建议（精确 rm 命令 + 可回收字节）；--keep-archives N 每目标保留最近 N 份；--json 输出 deterline.backup-prune/v1 | static |
| `recovery-scan` | 恢复完整性（03 §2.2c）：只读扫描未完结运行记录（.deterline/journal）与孤儿暂存 → 中断窗口分类 + 可预览恢复指引（--json 输出 deterline.recovery-scan/v1）；零写盘零 UTMT；发现未完结项退出码 1 | static |
| `backup-index --hash` | 恢复资产只读索引（O5 最小切片）：.bak/.snap/.sandbox/.deterline 工作区 → 类型/路径/恢复目标/mtime/大小（--hash 追加 SHA-256；--json 输出 deterline.backup-index/v1）；零写盘零 UTMT | static |

> ⚠️ `set`: HP/maxhp 进战斗会被按 LV 重算——永久固定用 set-derived
> ⚠️ `set`: WEAPON/ARMOR 自动计算 AT/DF
> ⚠️ `set`: HP/EXP/GOLD 等写 ini 会被警告（游戏只认 file0）
> ⚠️ `set-derived`: 永久改写 game.ios、对所有存档生效；恢复用 undo --value data_win
> ⚠️ `room-list`: 模糊名多匹配会报错并列出候选，须用唯一名
> ⚠️ `doctor`: 零 UTMT 子进程——deep 验证仍走 verify-code/smoke-test 独立命令
> ⚠️ `doctor`: 游戏文件 md5 ≠ 基线不一定是问题（实验态）；列出实验工作区数量
> ⚠️ `doctor`: 备份占盘 .bak* 单个约 250MB，长期不用可清（undo/experiment-restore 依赖）
> ⚠️ `backup-prune`: 保留条件：bak-latest / 命名快照 / 工作区副本与 legacy / journal 引用文件（活动恢复记录）/ 每目标最近 --keep-archives 份归档
> ⚠️ `backup-prune`: 内容重复按 sha256 分组（同组保留最新一份；组内超窗部分已入删除集）；归档哈希全量流式计算——13×60MB 约 1-3 秒
> ⚠️ `backup-prune`: 本命令零删除零恢复——是否执行由用户根据预览决定（执行入口下批）
> ⚠️ `backup-prune`: journal 引用的归档被保护跳过并单独计数；双侧定位均失败退出码 2
> ⚠️ `backup-prune`: 归档新旧按文件 mtime 排序（backup_file 保留源 mtime，可能与文件名时间戳分叉；平局按名字字典序）
> ⚠️ `backup-prune`: 执行清理前的前置条件：recovery-scan 无 corrupt-journal（损坏记录的保护可能不完整）
> ⚠️ `recovery-scan`: 扫描 game 旁与存档目录旁两处 .deterline/journal（transactions 每次提交前落盘、成功后删除、SIGKILL 保留）
> ⚠️ `recovery-scan`: 分类：未开始（清理）/ 已全部写入（确认清理）/ 替换中断（逐目标给出回滚或完成的 cp 命令）/ 存在外部修改（人工核对）/ aborted（含 error 字段）
> ⚠️ `recovery-scan`: 孤儿暂存（.{name}.*.new 无记录引用）单独列出；本命令零恢复零清理——执行恢复留待 recovery-apply/clean
> ⚠️ `recovery-scan`: 写命令提交前检测到同名目标未完结记录会拒绝并指引本命令
> ⚠️ `backup-index`: 覆盖 game 旁（game.ios/data.win.bak*、game.ios.snap*、.deterline 工作区、legacy .sandbox）与存档目录（file0/undertale.ini/system_information_962/963 的 bak/snap）
> ⚠️ `backup-index`: 工作区行恢复提示用 --workspace；legacy 行不带参数；所有提示带 --dir 作用域，可直接粘贴执行
> ⚠️ `backup-index`: 工作区行尾附 manifest history 摘要；损坏 manifest 容错（标 manifest损坏 不崩溃）
> ⚠️ `backup-index`: --json：stdout 纯 JSON（schema=deterline.backup-index/v1）；两侧定位均失败退出码 2；orphan 行含 note 字段（向后兼容增量）
> ⚠️ `backup-index`: 恢复入口：undo / experiment-restore / sandbox-restore（本命令零恢复零清理）

### 💬 对话文本编辑 — --file data_win，STRG 与 textdata_en 中央数据库（16457 行 / 158 万字符）

| 命令 | 功能 | 验证 |
|---|---|---|
| `list-strings --limit 30` | 列出 STRG 字符串（--limit/--offset/--hex） | static |
| `get-string --key 500` | 查看指定索引字符串 | static |
| `set-string --key 500 --value "新文本"` | 替换指定索引字符串（无长度限制） | sandbox |
| `add-string --value "* 新对话/%%"` | 新增字符串并返回索引 | sandbox |
| `delete-string --key 64000` | 删除字符串（索引整体重排，引用该索引的代码需自查） | sandbox |
| `replace-string --old "A" --value "B"` | 全局批量替换（--old 旧文本 → --value 新文本） | sandbox |
| `search-strings --value "Toriel"` | 搜索字符串 | static |
| `search-textdata --value "obj_cactus"` | 搜索 textdata_en key（⚠️ 行序 ≠ 台词顺序） | static |
| `add-textentry --key "obj_quest" --value "* Hello!/%%" --face 3` | 新增对话条目（自动去重；--face/--emotion 自动插入 \F\E 控制符） | sandbox |
| `update-textentry --key "obj_quest" --value "* 新文本/%%"` | 替换已存在 key 的文本（幂等） | sandbox |
| `delete-textentry --key "obj_quest"` | 按 key 删除条目 | sandbox |
| `batch-add-textentry --value entries.json` | 从 JSON 文件批量导入（[{"key":"k","text":"t"}]，支持 --face/--emotion） | sandbox |
| `guided-add-dialogue --key "obj_x" --value "* 文本/%%"` | 引导式对话创建（分步打印进度） | static |
| `search-sctext --value "* 你好"` | 在 SCR_TEXT 用例表中搜索文本 | static |
| `cjk-font --value build/font_cjk` | 注入中文字体管线（sandbox 已验证；【2026-11-08】中文已在游戏内实机渲染成功（B4 页内重排全栈），见 AUDIT_2026-11-07/C3b-游戏内验证报告 §九；S6 已集成（cjk-trigger 触发块命令随附）） | sandbox |
| `cjk-trigger --text "* 托丽尔你好，这里是中文测试。" --x 220 --y 330` | 生成并注入单个 CJK 对话触发块（B4 实证全形态：msc/facechoice/faceemotion//%%终止符/msg[1]；默认 typer31 spacing12；--text 文本自动预折行；须先 cjk-font） | sandbox |
| `cjk-check --text "* 托丽尔你好。"` | CJK 字形覆盖预检（C3a-L1）：--text 文本或 --value 文本文件逐字对照 glyphs.json，输出缺失码点与行动建议；退出码 全覆盖0/缺失1/无字形表2。static 级保证——覆盖≠渲染（B4 仅 N=1） | static |

> ⚠️ `replace-string`: 全局替换，先 search-strings 确认影响面
> ⚠️ `cjk-font`: --value 须为 font_cjk_build.py 输出目录（OFL 字体自生成）
> ⚠️ `cjk-font`: 已证实：不能新增字体资产（追加即全局字体失效）；【2026-11-08 探针】os_get_language() 返回 zh，游戏回退 global.language="en"（一手测量，非联合推断）——ja 分支不触发。中文预折行为排版建议（防水平溢出），非防挂起
> ⚠️ `cjk-font`: 完成后自动 verify-code gml_Script_scr_setfont（域F 协议）
> ⚠️ `cjk-trigger`: 依赖 cjk-font 页内栈先行注入（幂等守卫会拒绝）
> ⚠️ `cjk-trigger`: 触发位须在房间 320×480 内且可行走（x>=320 物理不可触发——B2 教训）
> ⚠️ `cjk-trigger`: typer 须在 CJK_TYPER_TABLE（31/5/3/2/68/30，几何经 SCR_TEXTTYPE 反编译核对）
> ⚠️ `cjk-trigger`: 折行按 writer 均匀步距模型（每字符一格）；typer31 无引擎折行故默认预折行宽 202
> ⚠️ `cjk-trigger`: 追加到 --object（默认 obj_cactus）的 Step_1；同一目标对象只能有一个 CJK 触发块
> ⚠️ `cjk-trigger`: 触发半径硬编码 60（B4 实证值，与全局 --range 无关）
> ⚠️ `cjk-check`: 默认字形表 build/font_cjk/glyphs.json（4064 码点 = ASCII + GB2312 一级 + 全角标点 + 假名，full:false）
> ⚠️ `cjk-check`: 缺失二级字 → font_cjk_build --full 重建；表外符号 → 换字符
> ⚠️ `cjk-check`: ASCII 直通判定（<128 恒覆盖——由原生字体承担）

### 📜 脚本编辑 — --file data_win，反编译/重编译 GML（6272 个脚本）

| 命令 | 功能 | 验证 |
|---|---|---|
| `list-codes --limit 10` | 列出脚本名 | static |
| `decompile-code --key "gml_Script_scr_damage"` | 反编译脚本为 GML 源码（--search 过滤行） | static |
| `replace-code --key "gml_Script_x" --value "return 0;"` | 替换整个脚本后重编译（--file-path 从文件读，--show-diff 预览） | sandbox |
| `find-replace-code --key "gml_Object_x" --old "旧" --value "新"` | 源码内搜索替换后重编译（--dry-run 预览匹配数） | sandbox |
| `append-code --key "gml_Object_obj_dummy1_Step_0" --value "// code"` | 追加 GML 到脚本末尾（不改原逻辑） | sandbox |
| `prepend-code --key "gml_Object_obj_dummy1_Step_0" --value "// code"` | 插入 GML 到脚本开头 | sandbox |
| `create-script --key "gml_Script_myfunc" --value "return 0;"` | 创建全新代码条目并自动注册 | sandbox |
| `search-vars --value "global.flag" --limit 30` | 在全部脚本中搜索变量引用 | static |
| `search-code --value "global.flag"` | search-vars 的别名（行为完全一致） | static |

> ⚠️ `replace-code`: 整段替换覆盖原逻辑；操作后用 verify-code 做字节级体检

### 🗺️ 房间布局与背景 — --file data_win；只能改造已有房间（禁止 create-room 新建），选房见 ROOMS_GUIDE.md

| 命令 | 功能 | 验证 |
|---|---|---|
| `room-info --value room_myarea` | 显示房间全部属性 | static |
| `room-objects --value "torielroom"` | 列出房间内全部对象实例（ID/坐标/精灵/事件） | static |
| `spawn-obj --value "room_asrielroom" --key "obj_dummy1" --x 160 --y 120` | 在房间指定坐标生成对象实例（自动分配唯一 InstanceID） | sandbox |
| `remove-obj --value "room_x" --key "obj_dummy1" --all` | 移除实例（--instance 优先；--key 移除第一个匹配；--all 全部） | sandbox |
| `create-room（已禁用，只能改造已有房间）` | ❌ 已废弃：调用即报错。禁止新建房间序号（运行时无法识别，曾导致传送错房遇神烦狗） | static |
| `set-room-bg --value room_x --index 0 --enable true --bg "bg_my"` | 配置房间背景层（对 B1 数据驱动房有效；B2 对象驱动房须用 gml-bg） | in-game |
| `set-room-prop --value room_x --caption "标题"` | 修改房间属性（--width/--height/--speed/--caption/--persistent/--bg-color；不触碰 Views[0]） | sandbox |
| `set-room-view --value room_x --view-w 320 --view-h 240 --port-w 640 --port-h 480 --follow obj_mainchara` | 配置摄像机视图（View 必须 320×240 / port 640×480；640×480 视角跟随失效——S2 大量实验验证） | in-game |
| `remove-tile --value room_x` | 清除房间 Tile（不传 --instance 清全部） | sandbox |
| `list-game-bgs` | 列出全部背景资产 | static |
| `create-bg-asset --value "bg_my" --image "bg.png"` | 将 PNG 注入为新背景资产 | sandbox |
| `gml-bg --value room_x --bg "bg_my" --slot 0 --speedx 0.5` | 注入运行时背景 GML + 视差到 obj_mainchara_Step_0（B2 对象驱动房/兜底手段；B1 用 set-room-bg） | in-game |
| `set-room-solid-bg --value room_x --color 101010` | 房间背景设为纯色（--color 6 位 hex；--layers 选层，--no-runtime 关闭运行时层） | sandbox |
| `room-bg-info --value room_x` | 诊断房间背景渲染类别（A 纯 Tile / B1 数据驱动 / B2 对象驱动） | in-game |

> ⚠️ `spawn-obj`: 新实例重进房间才加载；用 room-objects 查 ID 后 remove-obj
> ⚠️ `set-room-bg`: 必须覆盖所有启用层（高 slot 遮挡低 slot）
> ⚠️ `set-room-bg`: A 类纯 Tile 房 8 层全禁用时无效，须先启用一层
> ⚠️ `set-room-bg`: 2026-11 域D 实测裁决；room-bg-info 诊断房间归属
> ⚠️ `gml-bg`: 域D §八.6/表2.19 悬案：A 类房（room_ruins7A）的 gml-bg 路径建议游戏内复测
> ⚠️ `room-bg-info`: 分类结论经域D 游戏内实验裁决（A/B1/B2 归属）

### 🧍 NPC 交互 / 门 / 战斗 — --file data_win，注入已验证扁平触发形态

| 命令 | 功能 | 验证 |
|---|---|---|
| `npc-dialogue --value "room_torielroom" --key "obj_cactus" --x 170 --y 180 --text-key "obj_cactus_hi" --text "* Hi/%%"` | 一键安全 NPC 对话：加对话条目 + 生成实例 + 注入已验证扁平距离触发块 + 自动 Alarm_0 守卫。默认可重复；--once 触发后 NPC 自毁 | in-game |
| `npc-choice --value "room_water_undynefinal" --key "obj_kitchentable" --x 160 --y 420 --text-key "obj_table_ask" --text "* Let's go?& &         Yes         No      \C " --yes-text-key "obj_table_yes" --yes-text "* Okay!/%%" --no-text-key "obj_table_no" --no-text "* .../%%" --goto "雪镇 - 船夫(妇)" --item 48 --range 160` | 一键 YES/NO 选择 NPC：触发文本（须含 \C，≤3 行）→ 选择框 → YES/NO 分支文本替换。--goto 传送 / --item 给物品；默认单次，--repeat 可重复 | in-game |
| `guard-npc-alarm --key "obj_cactus" --instance 113927` | 给已注入 myinteract 触发、与默认对话重叠的 NPC 补 Alarm_0 守卫（幂等） | sandbox |
| `create-door --value "room_x" --key "room_y" --x 320 --y 240 --spawn-x 160 --spawn-y 120` | 创建传送门（--value 当前房 --key 目标房；--x/--y 位置，--spawn-x/--spawn-y 出生点） | sandbox |
| `list-doors --value "room_x"` | 列出房间内全部 Deterline 门 | static |
| `remove-door --value "room_x" --all` | 移除门（--x/--y 坐标 或 --all 全部） | sandbox |
| `create-pit --value "room_x" --key "room_y" --x 320 --y 240` | 创建坑/陷阱（踩上传送到目标房） | sandbox |
| `create-battle --value "room_x" --key 0 --x 320 --y 240` | 创建战斗触发区（--key = battlegroup 数字 ID；--border 边框样式） | sandbox |
| `handler-extract` | 分析 obj_time_Step_2 自定义逻辑（--apply 应用抽取） | static |

> ⚠️ `npc-dialogue`: 扁平形态 = 15 次游戏内启动实验矩阵实证（AUDIT_2026-11-07/域F）；状态机形态在当前 UTMT 环境是游戏内死代码，禁止手写
> ⚠️ `npc-dialogue`: 不锁移动（v2.3.0 起）；--text 含 \C 会报错并引导改用 npc-choice
> ⚠️ `npc-dialogue`: --range 自定义触发距离（默认 50px）
> ⚠️ `npc-choice`: --text 必须含 \C（≤3 行）；YES/NO 分支文本不得含 \C（自动校验，防止选择框循环重弹）
> ⚠️ `npc-choice`: 默认单次 = 答完后 NPC 自毁；分支文本自动替换 msg[0]
> ⚠️ `npc-choice`: in-game 依据（2026-11 复核标注）：触发块与 npc-dialogue 同为域F 已验证扁平形态（W3 smoke-test 证明游戏内执行）；\C 选择框为原生 obj_choicer 机制；YES/NO 分支替换为 sandbox 反编译验证

### 🎨 精灵 / 对象 / 纹理 — --file data_win，P4 管线

| 命令 | 功能 | 验证 |
|---|---|---|
| `list-sprites --limit 30` | 列出精灵（名称/尺寸/帧数） | static |
| `search-sprite --value "sans"` | 按名称搜索精灵 | static |
| `get-obj --key "obj_sans_actor"` | 查看对象属性（当前精灵/尺寸/可见性/深度/父类/事件数） | static |
| `set-obj-sprite --key "obj_sans_actor" --value "spr_sans_dangerous"` | 切换对象的 Sprite 引用（全局影响该对象所有实例；尺寸一致时碰撞盒无偏移风险） | sandbox |
| `list-textures --limit 10` | 列出嵌入纹理图谱（26 张） | static |
| `export-sprite --key "spr_sans_d" --value "out.png" --frame 0` | 导出精灵帧为 PNG（--frame 指定帧；--value 以 .png 结尾单帧导出，目录则全部帧） | static |
| `replace-sprite --key "spr_sans_d" --value "edit.png" --frame 0` | 替换精灵单帧纹理（合成回图谱对应区域，不影响同图谱其他精灵；PNG 自动 resize） | sandbox |
| `duplicate-sprite --key "spr_a" --value "spr_a_copy"` | 复制精灵为新名（独立编辑不影响原精灵） | sandbox |
| `preview-sprite --key "spr_sans_d"` | 终端 ASCII 预览精灵 | static |
| `colorize-sprite --key "spr_sans_d" --value "spr_sans_d_red" --hue-from "180-260" --hue-to 0` | 复制精灵并按 HSV 范围选择性变色（--hue-from "min-max" --hue-to 角度） | sandbox |
| `export-texture --value "./textures"` | 导出纹理图谱为 PNG（--key 单张；缺省导出全部 26 张） | static |
| `replace-texture --key "Texture 0" --value "tex0.png"` | 替换整个纹理图谱（影响图谱上所有精灵；经 GMImage 自动处理 QOI/BZ2 格式转换） | sandbox |
| `dump-sprites --value "./sprites"` | 批量导出全部 2583 个精灵（UTMT CLI 内置） | static |

> ⚠️ `replace-sprite`: 已验证无损循环：export→replace→export MD5 一致（域C sandbox 字节级）；游戏内目视验证未单独立案
> ⚠️ `replace-texture`: 影响面大，替换前先 export-texture 留底；域C 字节级验证（无损循环），游戏内目视未单独立案

### 🎯 支线任务 flag — global.flag 自定义区（默认 510）

| 命令 | 功能 | 验证 |
|---|---|---|
| `quest-init` | 重置任务 flag 为 0（--flag 默认 510） | static |
| `quest-status` | 查看自定义任务 flag 状态 | static |

### 🔒 验证 / 快照 / 写入安全 — V1/V4/W3/O7 机制与备份恢复

| 命令 | 功能 | 验证 |
|---|---|---|
| `verify-nsid` | 检查损坏变量 NameStringID（读取即崩溃的陷阱；--fix 自动修复） | sandbox |
| `verify-instances` | 检查全房间实例 ID 异常（ID=0/重复/空对象/Nonexistent；--fix 自动分配唯一 ID） | sandbox |
| `verify-code --key "gml_Object_obj_cactus_Step_1"` | 字节级体检指定代码条目：反汇编指纹 + 变量读写普查 + 往返稳定性（WARN/不稳定退出码 1；--asm 输出完整反汇编） | sandbox |
| `smoke-test --value room_torielroom --key obj_cactus` | 游戏内冒烟测试：注入扁平触发块 + 标记文件 → steam 启动 → 断言 → 自动恢复原文件（FAIL 退出码 1；--keys osascript 需辅助功能权限） | in-game |
| `diff-snapshots --key baseline.ios --value after.ios` | 两份 game.ios 结构化差异报告（LastObj/实例/代码条目/字符串计数/自定义变量——实验隔离与泄漏取证） | sandbox |
| `sandbox-restore` | 校验基线并备份后，将实验工作区应用回原文件 | sandbox |
| `md5` | 打印 game.ios MD5（一行校验"是否真的改过"） | static |
| `experiment-snapshot --value "test1"` | 创建命名实验快照（game.ios + file0） | static |
| `experiment-list` | 列出全部实验快照 | static |
| `experiment-restore --value "test1"` | 从命名快照恢复（⚠️ 覆盖 game.ios + file0） | static |

> ⚠️ `verify-code`: V1 收窄版；注入实验后必跑，能区分活/死代码形态的指纹差异
> ⚠️ `smoke-test`: ≈90 秒/次；环境敏感（无人值守开场动画可能卡住）；结束后自动还原并清理
> ⚠️ `smoke-test`: 三段裁决（阶段 1.1）：started/triggered/restored 分判；verdict=unverified 退出码 2（启动失败/按键不可用/非 Steam 目标演练）——报告含 SMOKE_RESULT 机器行
> ⚠️ `smoke-test`: 标记唯一（文件名含 run_id）+ 内容双钥（run/room/inst 字段级精确比对）；编辑目标非 Steam 安装路径时拒绝启动（DETERLINE_SMOKE_ALLOW_NONSTEAM=1 豁免）
> ⚠️ `diff-snapshots`: --key 基线文件，--value 对比文件
> ⚠️ `diff-snapshots`: 阶段 1.3：--detail 输出资源级差异（字符串内容哈希 LCS 锚定 / 实例 add-remove-move / 代码反汇编指纹 / 字体字形+纹理页）；单次遍历同载摘要+明细
> ⚠️ `diff-snapshots`: 阶段 1.4：--expected JSON 声明允许改变的资源范围（strings/code/fonts: any 或名单；instances: {房间: [move,add,remove]} 操作词表）——范围外差异退出码 1
> ⚠️ `diff-snapshots`: 显式 A/B 输入 read-through 直读（工作区选择不会替换任一输入）；--utmt-timeout 默认 300s（--detail 全量反汇编）
<!-- END generated:commands -->

## 关键约束与注意事项（手工维护）

### 存档：file0 vs INI（已对照游戏源码核实）

> ⚠️ **重要（已对照游戏源码 scr_load / scr_saveprocess 核实）**：
> 核心属性 **LOVE/LV、HP(最大生命)、AT、DF、EXP、GOLD、Kills、装备、Boss 状态、flag 都存在 `file0`**，读档瞬间从 file0 读取。
> `undertale.ini` 的 `[General] Name / Love / Time / Kills / Room` **只是存档时写入的镜像副本，游戏不读它定数值**（下次存档会被覆盖）。
> 所以：改 LOVE / Kills / Room 推荐直接用 `--file file0`；用 INI 命令时工具会自动同步 file0（Room/Love/Kills）。
> file0 字段索引（0-based，去首行名字后）：`[0]=LOVE [1]=MAXHP [2]=MAXEN [3]=AT [4]=武器AT [5]=DF [6]=护甲DF [7]=SP [8]=EXP [9]=GOLD [10]=KILLS`。

> ⚠️⚠️ **HP / AT / DF 不是自由属性，而是由 LV 推导的缓存**：
> 游戏在升级（`scr_levelup`）与**每次进入战斗**（`obj_battlecontroller_Create_0`）时都会重算：
> `maxhp = 16 + lv*4`、`at = 8 + lv*2`、`df = 9 + ceil(lv/4)`。
> **读档瞬间**（`scr_load`）是 `maxhp = file0 值`、`hp = maxhp`，所以改完 file0 后菜单会正常显示你设置的值
> （如 LV5 设 50 → 显示 50/50）；重算只在**进战斗/升级**那一刻发生，之后才会变回 LV 推导值。
> 因此只用 `set --key HP` 改 file0，进战斗就会被覆盖（工具会打印警告）。要**永久固定**这些值，必须用
> `set-derived --key HP|AT|DF --value N`（它同时改写 file0 与上述两个脚本）。注意 `set-derived` 会永久改写
> `game.ios`、对**所有存档**生效，可用 `undo --value data_win` 恢复。LV5 对应的原版值为 HP36 / AT18 / DF11。

### 选房规则（强制）

> ⚠️ **强制规则（必须遵守）**：用户要求自定义/新建房间时，**禁止 `create-room` 新建房间序号**（游戏运行时无法识别新增房间）。只能**修改已有房间**。房间选择必须查阅 **`ROOMS_GUIDE.md`**（Deterline 目录下，336 个房间全量分类清单）。
>
> 选房规则：
> 1. 用户要求**加背景/视差** → 必须选 **B 类**（有背景图，可注入 GML 视差）；横长房（W>320）优先，小房（320×240）视角静止看不到视差
> 2. 用户要求**纯地板场景** → 选 **C 类**（纯 Tile 地板）
> 3. 提供候选时列出房间号 + 尺寸 + 中文名，供用户挑选，不得擅自决定
> 4. 用户要求**加背景时**，必须询问：是否要背景视差？视差速度（speedx）多少？（默认 0.3）
> 5. 多层视差参考房：`room_lastruins_corridor`（230，B2 类，7 层多深度视差）。其余 obj_backgrounder_* 房间（tundra/dock/core/castle 等）也有单层视差公式

### 房间背景三类归属（2026-11 审计裁决）

- `set-room-bg` 对**数据驱动（B1）房间有效**——引擎加载时用 ROOM 数据初始化运行时背景数组；但必须覆盖**所有启用层**（高 slot 遮挡低 slot）。
- **对象驱动（B2）房间**（含 `obj_backgrounder_*` 的房）其 Create 会覆盖房间数据，须用 `gml-bg`。
- **纯 Tile（A 类）房** 8 层全禁用时二者均无效，须先 `set-room-bg --enable true` 启用一层。
- 用 `room-bg-info` 查房间归属；View 的 width/height 必须是 320×240（S2 大量实验验证）。

### NPC 注入语义（v2.3.0，扁平形态）

- 修改的是 `game.ios/data.win` 中的房间布局数据，不是存档；新实例在**重新进入房间时加载**，不立即生效（可用 `set --key Room --value 房间ID` 传送触发刷新）
- 生成的实例保留完整的对象行为（碰撞、事件、交互、AI）
- **新增实例必须唯一非 0 的 InstanceID**：多个实例 ID=0 会共享 per-instance 变量表 → Create 事件写入（`phase`、`image_xscale` 等）不生效 → 读 `other.<变量>` 崩溃 + 布局异常（漏口）。ad-hoc CSX 直接 `new UndertaleRoom.GameObject()` 必须设 `InstanceID = Data.GeneralInfo.LastObj++`；工具命令（spawn-obj/npc-dialogue/create-door 等）已自动处理。操作后用 `verify-instances` 检查
- `npc-dialogue` / `npc-choice`（v2.3.0）生成**已验证扁平触发块**（游戏内实测；状态机形态在当前 UTMT 环境下游戏内死代码，禁止手写）；原生 readable 对象额外加 `Alarm_0` 守卫；Create 事件自动初始化 `deterline_state = 0;` 仅为 NSID 兼容保留（触发块不读写）
- **默认触发行为（v2.3.0）**：靠近(<50px，可用 `--range` 调)触发；不锁移动（状态机在当前 UTMT 环境产生死代码，2026-11 审计）；可重复模式下关闭对话后仍在范围内会再次弹出，走出范围即停止；`--once`（npc-choice 默认）触发/答完后 NPC 自毁消失
- `npc-choice` 的 `--text` 必须是含 `\C ` 的 3 行以内选择文本（`"* 提问& &         Yes         No      \C "`）；YES/NO 分支文本**不得含 `\C`**（命令行会自动校验，`npc-dialogue` 遇到 `\C` 文本会报错并引导改用 npc-choice）
- 可用 `--sandbox` 做安全测试，确认无误后 `sandbox-restore` 恢复

### 房间改造工作流（已验证）

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

### 纹理替换工作流与技术细节

```
export-sprite --key "spr_sans_d" --value "sans.png" --frame 0
  → (用 PIL / Photoshop / Aseprite 编辑 PNG)
replace-sprite --key "spr_sans_d" --value "sans_edit.png" --frame 0 --sandbox
  → 进游戏验证
undo --value data_win  (恢复已提交的游戏数据)
```

- 2583 个精灵共享 26 张纹理图谱（Texture 0~25）；图谱尺寸 512/1024/2048 混合（2026-11 审计实测）
- `replace-sprite` 只替换精灵在纹理图谱上对应 SourceX/Y/Width/Height 的区域，不影响同图谱其他精灵
- 编辑 PNG 会自动 Resize 匹配原尺寸；替换后通过 `GMImage` 自动处理格式转换（QOI/BZ2 等）
- 已验证无损循环：`export-texture → replace-texture → export-texture` MD5 完全一致

### 实验工作区与写入

游戏数据写操作默认使用源文件旁的 `.deterline/<文件名>/default/`。有旧 `*.sandbox` 时，默认继续使用旧副本。指定 `--workspace` 可单独创建和选择工作区，名称允许小写字母、数字、连字符和下划线。

```bash
python run.py --action add-string --value "Test text" --file data_win --workspace test
python run.py --action list-strings --file data_win --workspace test
python run.py --action sandbox-restore --workspace test --preview
python run.py --action sandbox-restore --workspace test
```

应用工作区前会比较原始文件的基线哈希，并备份当前目标。缺少基线记录的旧副本可保留，使用新工作区重做编辑。直接写入请加 `--commit`，如需跳过 Steam 同步请再加 `--no-steam-sync`。`--preview` 显示拟写入目标和哈希，存档文本另有行级差异。原有代码替换 `--dry-run` 仍可查看源码匹配或差异。

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

- 所有对话文本注册在 `gml_Script_textdata_en` 这一个脚本
- 格式：`ds_map_add(global.text_data_en, "key", "文本/%%")`

> ⚠️⚠️ **`search-textdata` 的返回顺序 ≠ 游戏内对话顺序（关键陷阱）**
>
> - textdata 的 key 编号（如 `obj_darksans1_345`）与角色台词顺序**无关**。同一段剧情的 key 可能散落在脚本各处：Sans 雪镇开场里 `obj_darksans1_187`（放屁垫玩笑）数值上排在 `obj_darksans1_345`（第一句 "* Human."）**前面**。
> - `search-textdata` 按**文件行序**输出，**列表里第一行绝不等于"第一句对话"**。严禁凭"先搜到/列表在前"判断台词先后。
> - **台词真正的顺序由场景代码决定**：`global.msg[N] = scr_gettext("key")` 的 N 递增顺序，或对象事件里的调用顺序。要确定"第几句 = 哪个 key"，必须反编译对应场景对象的事件代码查看。
> - 同名台词常有**重复变体**（如 `obj_darksans1_187` 与 `obj_darksans1_210` 都是放屁垫玩笑，`obj_darksans1_345` 与 `obj_darksans1_354` 都是 "Human."）。必须在代码里确认目标事件实际引用的那一个。

#### 改已有对话的标准流程（Agent 必读）

> 用户要求"改某 NPC 的第 N 句对话 / 改某句特定台词"时，**禁止直接按 `search-textdata` 的结果挑一条改**。必须按以下流程定位：

```
1. 定位 key 家族
   search-textdata --value "<key前缀>" --file data_win
   （如 Sans 雪镇开场 = "darksans1"；先搜关键词确认前缀）

2. 确认场景顺序（关键步骤，决定"第几句"）
   search-vars --value "<key前缀>" --file data_win
   → 找到真正引用这些 key 的对象事件代码（如 gml_Object_obj_darksans1_Step_0）
   decompile-code --key "<该对象事件>" --file data_win
   → 看 global.msg[0]/[1]/[2] = scr_gettext("key") 的先后 → 确定第 N 句对应哪个 key

3. 核对旧文本
   search-textdata --value "<确定的key>" --file data_win
   → 确认该 key 的当前文本与用户描述一致（防止选到重复变体）

4. 修改
   方案 A（推荐）：update-textentry --key "<key>" --value "<新文本>" --file data_win
   方案 B（无该命令时）：find-replace-code --key "gml_Script_textdata_en"
     --old "<旧文本片段>" --value "<新文本片段>" --file data_win

5. 验证
   search-textdata --value "<key>" --file data_win 确认已更新
```

**已核实示例：Sans 雪镇开场（`obj_darksans1` 家族）**

| 游戏顺序 | key | 文本 |
|---|---|---|
| 第 1 句 | `obj_darksans1_345` | `* Human./` |
| 第 2 句 | `obj_darksans1_346` | `* Don't you know how&  to greet a new pal?/` |
| 第 3 句 | `obj_darksans1_347` | `* Turn around and shake&  my hand./%%` |
| 放屁垫玩笑 | `obj_darksans1_187`（变体 `_210`） | `* heheh... the old whoopee&  cushion in the hand&  trick./` |

引用代码：`gml_Object_obj_darksans1_Step_0`（`msg[0]=scr_gettext("obj_darksans1_345")` 为第一句）。

### ⚠️ 对话框边框 ≠ spr_border（目标歧义陷阱）

"对话框边框"和"战斗弹幕盒边框"名字高度相似，但**实现链路完全无关**。改错目标会得到"边框没变化"的假成功。

| 用户说的 | 实际实现 | 修改入口 |
|---|---|---|
| 对话框/文本框边框 | `gml_Object_obj_dialoguer_Draw_0` 内 `draw_set_color(c_white)` + `draw_rectangle` **程序化绘制**（上/下两种位置各一处） | `find-replace-code --key "gml_Object_obj_dialoguer_Draw_0" --old ... --value ...` |
| 战斗弹幕盒边框 | `spr_border`(5×5) / `spr_emptyborder`(165×165) 纹理 + `obj_lborder`/`obj_rborder`/`obj_uborder`/`obj_dborder` 四对象 | `replace-sprite --key "spr_border" --value ...` |

- `obj_lborder` 等四对象均引用 `spr_border`，被 `obj_battlecontroller`、战斗实体（`obj_dummymonster`/`obj_fakefroggit`）、约会场景（`obj_papdate`/`obj_adate`）引用（2026-11 审计：obj_fakeheart 实测 0 处引用，已从名单移除）——**与对话框无关**。
- 检索引导：**"对话框/文本框" → 查 `obj_dialoguer`；"战斗盒/弹幕盒" → 查 `spr_border`**。
- ⚠️ 改 `spr_border` **不会**影响对话框边框；改 `obj_dialoguer_Draw_0` 也不会影响战斗盒边框。

### 完整文本控制符表

| 控制符 | 作用 | 示例 |
|--------|------|------|
| `* ` | 对话前缀（**强惯例**——引擎实际渲染任意文本，但全游戏对话均带此前缀；缺失会导致样式不一致） | `"* 文字/"` |
| `/` | 翻页标记（中间页以此结尾） | `"* 第一页/* 第二页/%%"` |
| `/%%` | 末页标记 | `"* 最后一页/%%"` |
| `%%%` | msg 数组结束符（代码中用，非对话文本内容） | `global.msg[N] = "%%%"` |
| `&` | 换行 | `"* 第一行&* 第二行/"` |
| `^N` | 暂停 N×10 帧（N 仅**单个数字** 1-9，`^1`=10 帧≈0.17 秒，`^9`=90 帧=1.5 秒；两位数如 `^120` 会变成 10 帧暂停 + 字面渲染 "20"） | `"* 停一下^9 再继续/"` |
| `\C ` | 在行尾创建 YES/NO 选择框（带尾随空格是全游戏惯例，引擎不检查空格；**真雷**：`\C` 后跟 `/` 会把选择等待 halt=5 覆盖成翻页 halt=1，破坏选择框） | `"* 确认？&  Yes No\C "` |
| `\R` | 红色文字 | |
| `\W` | 白色文字（默认） | |
| `\X` | 黑色文字（mycolor=0=c_black；白气泡上的默认黑字；全游戏 0 处用于"左侧白字"——旧描述有误） | `"\XI am\BTORIEL\X,.../"` |
| `\G` | 绿色文字 | |
| `\Y` | 黄色文字 | |
| `\B` | 蓝色文字 | |
| `\O` | 橙色文字 | |
| `\L` | 浅蓝色文字 | |
| `\P` | 粉色文字（另有大写表缺漏的小写 `\p` = 粉色变体） | |
| `\F` + 数字 | **切换头像角色**（1-9） | `"\F3"` = Sans 脸 |
| `\E` + 数字 | **切换表情**（角色相关） | `"\E1"` = Sans 轻笑 |
| `\T` + 字符 | 按角色首字母切换**打字机样式**（非速度）：`"\T0"`=标准, `"\Ts"`=Sans 字体标准速度, `"\TF"`=Flowey 邪恶样式（更慢+抖动） | `"\Ts* hey./"` |
| `\M` + 数字 | 设置 `global.flag[20]` | `"\M1"` = flag[20]=1 |
| `\*` | 绘制按键图标——PC/macOS 上被 `scr_replace_buttons_pc` 预替换为字面 "[Z]" 文本，精灵图标仅主机路径 | |

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
"\F3\E1* hey, buddy./ \E0* nice weather today./%%"
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

视角跟随由 GMS1 引擎自动处理，只需确保 `Views[0].ObjectId = obj_mainchara`（`set-room-view` 需**显式** `--follow obj_mainchara`，无默认值）。不需要手写 GML 代码控制视角。

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
EmbeddedTexture (TXTR)   — 26 张，实际的图像数据（PNG/QOI），512×512 ~ 2048×2048
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

> 🚨 **v2.3.0 警示（2026-11 游戏内 13 次启动实测）**：下方手写状态机模板在当前
> UndertaleModCli 0.9.1.2 环境下**游戏内静默死代码**（触发分支从未执行）——凡"状态条件
> 门控 create"的写法（deterline_state/flag[510]/内建变量，外层或嵌套）全部失效；唯一
> 游戏内实证可用的形态是 `npc-dialogue` v2.3.0 生成的**纯扁平触发块**（无状态读写）。
> 此模板保留仅作历史参考，**禁止照抄**；修复前请用 `npc-dialogue` 命令。

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

`guard-npc-alarm` 命令可自动完成守卫步骤；⚠️ v2.3.0：不再提供"改写 Step 为状态机"（状态机形态游戏内死代码，2026-11 审计）——触发代码请用 `npc-dialogue` 生成的扁平块。

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

#### 已验证模板：YES/NO 选择 + 传送 + 给物品（单次触发）

> 此模板来自竞技场桌子实验（v2.1.1 实测通过）：桌子靠近弹 "Let's go?"，
> YES → 传送到雪镇码头，NO → 显示 "..." 后结束，**不再追问**。
> 用 `npc-choice` 命令可一键生成，无需手写。

前置条件（`npc-choice` 自动完成）：
1. 文本条目（textdata_en）：
   - `obj_ask` = `"* Let's go?& &         Yes         No      \C "`（含 `\C`，≤3 行）
   - `obj_yes` = `"* Okay!/%%"`（**不含 `\C`**）
   - `obj_no`  = `"* .../%%"`（**不含 `\C`**）
2. 对象 Create 事件含 `deterline_state = 0;`
3. 原生 readable 对象在 `Alarm_0` 头部加 `if (id == N) exit;` 守卫

> 🚨 **v2.3.0 警示**：同上——此"已验证模板"（v2.1.1 竞技场实验）在 2026-11 复测中
> 属于游戏内死代码形态（状态机门控）；单次语义请改用 `npc-choice`（答完自毁）。

```gml
// ===== 改写到 NPC 的 Step 事件（或 Step_1）=====
if (id == <实例ID>)
{
    // 1. 对话结束后标记完成（单次触发：0→1→2，永不再触发）
    if (deterline_state == 1 && !instance_exists(OBJ_WRITER) && !instance_exists(obj_choicer))
    {
        deterline_state = 2;
        global.interact = 0;
    }

    // 2. 处理 \C 选择结果（2 帧窗口截获；必须替换 msg[0] 为不含 \C 的文本！）
    if (global.choice != -1 && deterline_state == 1)
    {
        if (global.choice == 0)  // YES
        {
            global.choice = -1;
            global.msc = -1;       // 阻止 scr_msgup 覆盖 msg[]
            global.interact = 0;
            global.typer = 5;
            global.facechoice = 0; // 头像角色（0=无）
            global.faceemotion = 0;
            global.msg[0] = scr_gettext("obj_yes");   // 不含 \C！
            global.msg[1] = "%%%";
            script_execute(scr_itemget, 48);          // 可选：给物品
            room_goto(room_tundra_dock);              // 可选：传送（房间常量/ID 均可）
        }
        else                        // NO
        {
            global.choice = -1;
            global.msc = -1;
            global.typer = 5;
            global.facechoice = 0;
            global.faceemotion = 0;
            global.msg[0] = scr_gettext("obj_no");    // 不含 \C！
            global.msg[1] = "%%%";
        }
    }

    // 3. 距离触发（默认 <50px；可用 --range 调）
    if (deterline_state == 0 && !instance_exists(OBJ_WRITER) && !instance_exists(obj_choicer))
    {
        var dist = distance_to_object(obj_mainchara);
        if (dist < 160)   // 竞技场实测 160px（门线前触发）
        {
            deterline_state = 1;
            global.interact = 1;    // 锁移动，防头像/文字错位
            global.msc = 0;         // SCR_TEXT(0) = no-op
            global.typer = 5;
            global.facechoice = 0;
            global.faceemotion = 0;
            global.msg[0] = scr_gettext("obj_ask");
            global.msg[1] = "%%%";
            instance_create(0, 0, obj_dialoguer);
        }
    }
}
```

**为什么 NO 不会循环追问（本次实验的坑）：**
选 NO 后 `obj_choicer` 的 alarm 在 2 帧后调 `scr_msgup`，它会把 `global.msg[]`
重新复制进对话框渲染。若此时 `msg[0]` 还是带 `\C` 的选择文本 → 选择框再次弹出 → 无限循环。
**修复：分支处理必须把 `msg[0]` 换成不含 `\C` 的文本。**（`npc-choice` 自动生成此代码，
`add-textentry` 遇到 `\C` 文本也会打印警告。）

**🚨 以下"可重复触发变体"已废弃（v2.3.0 起，勿手写）**：这个 `deterline_state` 状态机
变体在当前 UTMT 环境是游戏内死代码（2026-11 审计，见 AUDIT_2026-11-07/域F），仅作历史
记录保留。现行的可重复触发 = `npc-dialogue`/`npc-choice --repeat` 生成的**无状态扁平块**
（关闭对话后仍在 `--range` 内会再弹，走出范围即停）：

```gml
// ❌ 废弃形态（游戏内死代码——deterline_state 门控）：
if (deterline_state == 2 && distance_to_object(obj_mainchara) >= 60)
{
    deterline_state = 0;
}
```

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

### 实验 16：房间实例 InstanceID=0 陷阱（崩溃 + 布局异常根因）
- 现象：条纹实验室（room_tundra_dangerbridge）靠近天花板/底部 solid 即崩（`other.phase` 未设置 @ Collision_822），且底部 x=160 处 100px 漏口可穿出房间
- 根因：ad-hoc CSX 用 `new UndertaleRoom.GameObject() { ObjectDefinition=..., X=..., Y=... }` 未设 `InstanceID` → 37 个实例全部 ID=0 → GM 按实例 ID 管理 per-instance 变量表 → 全部实例共用一个变量槽 → Create 事件写入的 `phase`/`image_xscale` 未落到碰撞实例 → 读 `other.phase` 崩溃 + solid 未撑开成 400px（漏口）
- 排查链：反汇编确认 `other.phase`（100467）→ 当前文件 Create 事件与干净原版逐字节一致 → 全备份都有正确 wiring → 对照原版排除 scale 覆盖 → 唯一异常 = 37 实例 ID 全 0（全游戏唯一 ID=0 的房间）
- **修复**：给 37 实例分配唯一 ID（`Data.GeneralInfo.LastObj++`）并同步 `LastObj`，实测恢复正常
- 工具防护：`verify-instances` 命令全房间体检 + `--fix` 自动修；spawn-obj/npc-dialogue/create-door/create-pit/create-battle 保存时自动告警 ID 异常；`room-info`/`room-objects` 对 ID=0/重复实例标 `⚠️`
- 教训：**新增房间实例必须设唯一非 0 的 InstanceID**；排查"Create 事件正确却不生效"先查实例 ID；ad-hoc CSX 禁止裸 `new GameObject()` 不设 ID

### 实验 A：Sans 走路变红（纹理替换管线验证）
- `export-sprite` → PIL 红蓝通道互换 → `replace-sprite`
- 确认精灵 frame 0/2 共享同纹理区域（SourceX/Y 相同）
- 结果：Sans 走路时红 X 闪烁（帧 0/2 有红 X，帧 1/3 无）

### 实验 B：对话框心形变青（UI 元素替换验证）
- `export-sprite` → PIL 全像素改色 → `replace-sprite`（帧 0 和帧 1）
- 跨纹理图谱（Texture 2）操作成功
- 结果：对话文本继续指示从红色心变为青色心
- ⚠️ **边界**：本实验改的是对话文本里的"心形图标 Sprite"，**不是对话框边框**。对话框边框由 `obj_dialoguer_Draw_0` 程序化绘制，改 `spr_border` 不会影响它（见「对话框边框 ≠ spr_border」）。

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
1. 用 `npc-dialogue` 命令（v2.3.0：生成游戏内已验证扁平触发块 + `Alarm_0` 加 `if (id == N) exit;` 守卫；状态机形态已废弃——游戏内死代码）
2. 手工（⚠️ 状态机形态游戏内死代码，勿照此写——只允许 npc-dialogue 生成的扁平形态；守卫部分仍有效）：`Alarm_0` 头部加 `if (id == <实例ID>) exit;`

**如何识别**：`get-obj --key obj_xxx` 会显示完整父链并打印警告；`spawn-obj` 生成这类对象时也会提示。

---

## 已知可靠的交互模式

### ✅ 距离自动触发
```
distance_to_object(obj_mainchara) < 50
```
任意对象的 Step 事件中检测玩家距离。不依赖 Z 键。（⚠️ v2.3.0："对话结束后自动重置"需状态机实现，而状态机形态在当前 UTMT 环境游戏内死代码——纯扁平块会在关对话后、仍在范围内时立即重弹，走出范围停止）
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

> ⚠️ 2026-11 审计注：flag[510] 并非绝对无冲突——原版 `obj_asriel_overworldanim_Step_0`（真和平线结尾）会写 `flag[510] = 1`。正常流程影响极小，但做持久状态机时请在设计中容忍该场景（flag[511] 未见原版写入，更安全）。

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
| **写入默认沙箱** | 写命令默认落在实验工作区并打印回执；`--commit` 直写；`--no-steam-sync` 抑制 Steam 同步 |
| **`verify-nsid` 变量体检** | 检查损坏的变量 NameStringID（读取会崩溃的陷阱），`--fix` 自动修复 |
| **变量自动初始化** | `npc-dialogue`/`guard-npc-alarm` 自动在 Create 事件写 `deterline_state = 0;`，防止新变量 NSID 损坏崩溃 |
| **精灵搜索** `search-sprite` | 零匹配以退出码 3 结束（推荐逻辑仅 get-obj/spawn-obj 有） |
| **对象搜索推荐** `get-obj` | 找不到对象时自动推荐相似名称 |
| **多匹配提示** | 名称模糊匹配时打印 `(found N matches, using: ...)` |
| **`replace-sprite` 自动 Resize** | 编辑 PNG 自动缩放匹配源精灵尺寸 |
| **`filename` 起名建议** | 文件名不合预期时自动修正 |
| **`md5` 自检** | `--action md5` 打印 game.ios 的 MD5，可在报告中一行校验"是否真的改过" |
| **搜索零匹配非零退出** | 搜索类命令无匹配时以退出码 3 结束并告警——禁止把"没找到"当作成功 |
| **UTMT `ERROR:` 传播退出码** | CSX 脚本报错时以退出码 1 结束，且**不写回 game.ios**（防止"报错被吞后虚报成功"） |

## 注意事项

1. **UndertaleModTool 必须预先编译**，`UTMT_CLI` 环境变量必须设置
2. `replace-code` 会覆盖整个脚本——先用 `list-backups` 确认有备份
3. `global.flag[]` 索引范围 0-511，**不要使用 512+**，游戏会崩溃
4. 自定义事件仅使用保留 flag **510** 和 **511**，避免与主线剧情冲突
5. 对话文本请包含 `* ` 前缀（全游戏惯例；引擎技术上渲染任意文本，但缺前缀样式不一致）
6. 中间页以 `/` 结尾，末页以 `/%%` 结尾
7. **英文版 Undertale 不支持中文字符**。添加的对话文本必须使用英文（ASCII），中文字符不渲染（显示为空白 `*`）
8. `spawn-obj` 修改的是 `game.ios`/`data.win` 的房间布局数据，**不是存档**。新实例在重新进入房间时加载
9. `spawn-obj` 生成的实例保留原始对象的完整行为（AI、碰撞、交互），可能包含战斗触发等逻辑。建议先 `room-objects` 确认对象行为
10. `\C` 的选择文本总行数（含选项）≤ 3 行，超过会导致选项溢出对话框
11. `global.msc = 0`：`SCR_TEXT(0)` 是空操作，不会覆盖 `global.msg[]`
12. `global.msc = -1`：`scr_msgup` 自增到 0，2 帧窗口截获 `\C` 选择
13. 使用头像时 `facechoice` 设为内置角色（1-9），**不要自定义 face 对象**
14. **房间 View 必须 320×240（port 640×480）**。设成 640×480 会导致视角跟随失效，2x 缩放异常（10 个战斗/约会/结尾房为 640×480 例外）。`set-room-view` 按此设置
15. `set-room-bg` 对数据驱动（B1）房间有效，但须覆盖所有启用层；对象驱动（B2）房用 `gml-bg`；纯 Tile（A 类）房需先启用一层。用 `room-bg-info` 诊断（2026-11 审计修正，旧"一律被忽略"结论有误）
16. `gml-bg` 将代码注入 `obj_mainchara_Step_0`，每帧执行设置背景和视差。一次注入永久生效，直到代码被清除
17. 跨平台：macOS/Windows 路径自动识别
17a. **写入安全（v2.3.0）**：data_win 写命令默认沙箱 + 写入回执；`--commit` 直写；`--no-steam-sync` 抑制 Steam 同步
17b. **`verify-code`**：代码条目字节级体检（反汇编指纹 + 变量读写普查 + 反编译↔重编译往返稳定性判定）
17c. **`smoke-test`**：游戏内冒烟测试（注入触发块+标记文件 → 启动游戏 → 断言 → 自动恢复；验证级别 in-game）
18. Skill 通过符号链接安装，工作区修改自动同步到 OpenCode
19. `set-obj-sprite` 修改对象定义，影响所有实例。如需实例级只改一个 NPC，用 GML `sprite_index` 运行时赋值
20. `replace-sprite` 修改纹理图谱对应区域，帧 0 和帧 2 可能共享同纹理区域（SourceX/Y 相同）
21. `replace-texture` 替换整个纹理图谱，影响该图谱上所有精灵。确认无误再操作
22. 纹理编辑后 PNG 会自动 Resize 匹配原精灵尺寸，但建议保持原尺寸编辑以保真
23. 英文版 Undertale 的字体精灵不包含中文字形，替换文字纹理无法解决中文显示问题
24. **新实例变量必须先初始化**：注入用到新变量（如 `deterline_state`）的代码前，务必在对象 Create 事件写 `变量 = 0;`。否则变量未被正确注册（NameStringID=0）时读取会崩溃。用 `npc-dialogue`/`npc-choice`/`guard-npc-alarm` 会自动处理；`verify-nsid --fix` 可修复已损坏变量
25. `npc-dialogue`（v2.3.0）：已验证扁平触发块，不锁移动；默认可重复（关对话后仍在范围内会再弹），`--once` 触发后 NPC 自毁。⚠️ 状态机形态（deterline_state/flag[510]/内建变量门控 create）在当前 UTMT 环境全部游戏内死代码——修复前禁止恢复状态机生成（见 AUDIT_2026-11-07/域F 实验矩阵）
26. `npc-choice` 的触发文本必须含 `\C `（且 ≤3 行含选项行），YES/NO 分支文本不得含 `\C`（否则选择框循环重弹）；`--goto` 支持中文房间名/ID，`--item` 用 `ITEMS` 字典 ID（0-65）。默认**单次触发**，`--repeat` 切可重复
27. `append-code`/`prepend-code` 支持 `--file-path` 从文件加载 GML（与 `replace-code`/`create-script` 一致）

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
