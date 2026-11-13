# Deterline — 常用指令速查

所有命令在 `deterline/` 文件夹内运行。

---

## 安装

选择你的平台，运行一次即可：

| 平台 | 入口 | 说明 |
|------|------|------|
| **macOS** | 双击 `Install.app` | 检测环境 → 没装齐则补全 → 秒装 Agent Skill |
| **Windows** | 双击 `install.bat` | 同上 |
| **Linux** | `bash install.sh` | 同上 |
| **已有 Python** | `python3 install.py` | 同上 |

安装脚本自动安装：Agent Skill + .NET SDK + UndertaleModTool CLI + 环境变量。
所有入口最终都调用同一个 `install.py`。

```bash
python install.py             # 交互式安装（推荐）
python install.py --auto      # 智能模式：体检 → 就绪仅装 Skill，否则自动补全全部
python install.py --all       # 自动安装全部（跳过确认）
python install.py --check     # 只读环境体检（不修改任何文件）
python install.py --update    # 更新/修复（重指向 Skill 链接、重建 UTMT）
python install.py --uninstall # 卸载（删除 Skill 链接与环境变量）
python install.py --skill     # 仅安装 Agent Skill
python install.py --dotnet    # 仅安装 .NET SDK
python install.py --utmt      # 仅编译 UTMT CLI
python install.py --env       # 仅配置环境变量
python install.py --yes       # 配合以上命令自动确认所有提示
```

---

## 命令总表（全量 · 自动生成）

<!-- BEGIN generated:commands (SSOT: scripts/commands.json · python3 tools/gen_docs.py 生成，勿手改) -->
> 全量 89 个命令 · 版本 2.5.2 · 由 `scripts/commands.json` 生成（改命令表 → 改 json → `python3 tools/gen_docs.py`）
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

---

## 📁 存档编辑

```bash
# 查看
python run.py --action get --key Love
python run.py --action get --key Room
python run.py --action list
python run.py --action list --file file0
python run.py --action find --value 42 --file file0

# 修改属性（INI —— Love/Kills/Room 会自动同步 file0，游戏以 file0 为准）
python run.py --action set --key Love --value 20
python run.py --action set --key Kills --value 100
python run.py --action set --key Room --value 43
python run.py --action set --key Room --value "雪镇 - 船夫(妇)"   # 示例用唯一名；模糊名多匹配会报错并列出候选

# 修改属性（file0 —— 核心属性都在这里，推荐直接改 file0）
python run.py --action set --key Love --value 20 --file file0
python run.py --action set --key HP --value 50 --file file0      # 写 maxhp（读档即显示 50；进战斗会被按 LV 重算，见下）
python run.py --action set --key MAXHP --value 50 --file file0
python run.py --action set --key MAXEN --value 50 --file file0
python run.py --action set --key EXP --value 100 --file file0
python run.py --action set --key GOLD --value 9999 --file file0
python run.py --action set --key Kills --value 100 --file file0
python run.py --action set --key WEAPON --value 52 --file file0  # 自动 AT+99
python run.py --action set --key ARMOR --value 53 --file file0   # 自动 DF+99

# 固定由 LV 推导的属性（HP/AT/DF）——写 file0 并改写游戏脚本，防止被重算
# 游戏每次进战斗都会 maxhp=16+lv*4 / at=8+lv*2 / df=9+ceil(lv/4)，
# 只 set file0 会被覆盖；set-derived 才能永久固定（会永久改写 game.ios，对所有存档生效）
python run.py --action set-derived --key HP --value 50
python run.py --action set-derived --key AT --value 99
python run.py --action set-derived --key DF --value 99
# 恢复：python run.py --action undo --value data_win

# 修改 Boss 状态（4=击杀, 5=宽恕）
python run.py --action set --key TORIEL --value 5 --file file0
python run.py --action set --key PAPYRUS --value 1 --file file0

# 区域击杀
python run.py --action set --key RUINS_KILLS --value 20 --file file0

# 屠杀线重置
python run.py --action reset-flags

# 结局标记
python run.py --action create-system-info --value 962
```

---

## 💬 对话文本编辑（`--file data_win`）

需要 UTMT CLI 已安装。**无长度限制。**

```bash
# 查看字符串
python run.py --action list-strings --file data_win --limit 10
python run.py --action get-string --key 11432 --file data_win

# 新增/删除/修改
python run.py --action add-string --value "新对话" --file data_win
python run.py --action delete-string --key 64000 --file data_win
python run.py --action set-string --key 11432 --value "* 新文本/" --file data_win

# 搜索
python run.py --action search-strings --value "Toriel" --file data_win
python run.py --action replace-string --old "Toriel" --value "TORIEL" --file data_win

# 批量导入 (JSON: [{"key": "k", "text": "t"}, ...])
python run.py --action batch-add-textentry --value ./dialogues.json --file data_win

# 带头像的对话（自动插入 \F\E 控制符）
python run.py --action add-textentry --key "obj_test" --value "* hello/%%" --face 3 --emotion 1 --file data_win
```

---

## 📜 脚本编辑（`--file data_win`）

```bash
# 列出/反编译
python run.py --action list-codes --file data_win --limit 10
python run.py --action decompile-code --key "gml_Script_scr_sansface" --file data_win

# 替换/搜索替换
python run.py --action replace-code --key "gml_Script_scr_murderlv" --value "return 20;" --file data_win
python run.py --action find-replace-code --key "gml_Object_obj_dummy1_Step_0" --old "旧文本" --value "新文本" --file data_win

# 追加/前置代码（无需完全替换，不破坏原有逻辑）
python run.py --action append-code --key "gml_Object_obj_dummy1_Step_0" --value "if (global.flag[510]==99) instance_destroy();" --file data_win
python run.py --action append-code --key "gml_Object_obj_dummy1_Step_0" --value "./append.gml" --file-path --file data_win
python run.py --action prepend-code --key "gml_Object_obj_dummy1_Step_0" --value "// init code" --file data_win

# 创建新脚本
python run.py --action create-script --key "gml_Script_myFunc" --value "return 0;" --file data_win
```

---

## 🗺️ 文本数据表（`--file data_win`）

```bash
# 搜索对话 key
python run.py --action search-textdata --value "sans" --file data_win

# 新增/删除对话条目
python run.py --action add-textentry --key "obj_mynpc_001" --value "* Hello from Deterline!/%%" --file data_win
python run.py --action delete-textentry --key "obj_test_entry" --file data_win
```

---

## 🔍 搜索（`--file data_win`）

```bash
# 在所有脚本中搜索变量
python run.py --action search-vars --value "global.flag" --file data_win

# 查看房间内的对象
python run.py --action room-objects --value "torielroom" --file data_win
```

### 🧭 检索引导（先定位再动手）

| 用户说的 | 该查什么 | 不该查什么 |
|---|---|---|
| 对话框 / 文本框（含边框） | `obj_dialoguer`（边框 = `obj_dialoguer_Draw_0` 的 `draw_set_color`+`draw_rectangle`） | ❌ `spr_border` |
| 战斗盒 / 弹幕盒边框 | `spr_border` / `spr_emptyborder` 纹理、`obj_lborder`/`obj_rborder`/`obj_uborder`/`obj_dborder` | ❌ `obj_dialoguer` |
| 对话文本内容 | `search-textdata` + 场景事件反编译确认顺序 | ❌ 凭搜索行序判断台词先后 |

> ⚠️ `spr_border` 与对话框**无关**；对话框边框是程序化绘制，不能靠换纹理修改。

---

## 🏗️ 房间布局编辑（`--file data_win`）

```bash
# 在房间中添加对象实例
python run.py --action spawn-obj --value "room_torielroom" --key "obj_sans_actor" --x 320 --y 240   # obj_sans 不存在 --file data_win

# 从房间移除对象实例（按类型，仅移除第一个匹配）
python run.py --action remove-obj --value "room_torielroom" --key "obj_sans_actor" --file data_win

# 移除所有匹配的实例
python run.py --action remove-obj --value "room_torielroom" --key "obj_sans_actor" --all --file data_win

# 按实例 ID 移除
python run.py --action remove-obj --value "room_torielroom" --instance 100085 --file data_win

# 一键安全 NPC 对话（已验证扁平距离触发块 + Alarm_0 守卫；Create 事件初始化 deterline_state 仅为 NSID 兼容）
# 默认：可重复触发（关对话后仍在范围内会再弹，走出范围停止）；v2.3.0 不锁移动
python run.py --action npc-dialogue --value "room_torielroom" --key "obj_cactus" --x 170 --y 180 --text-key "obj_cactus_hi" --text "* Hi/%%" --file data_win

# 单次触发 NPC 对话（触发后 NPC 自毁消失，永久只看一次）
python run.py --action npc-dialogue --value "room_asrielroom" --key "obj_dummy1" --x 170 --y 180 --text-key "obj_dummy_hi" --text "* Hi/%%" --once --file data_win

# 自定义触发距离（默认 50px）
python run.py --action npc-dialogue --value "room_water_undynefinal" --key "obj_kitchentable" --x 160 --y 420 --text-key "obj_table_hi" --text "* Hi/%%" --range 160 --file data_win

# 一键安全 YES/NO 选择 NPC（npc-choice）：
# - 触发文本必须含 \C（≤3行），YES/NO 分支文本不得含 \C（自动校验，防止选择框循环重弹）
# - 默认单次触发；--repeat 可重复；--goto 传送（支持中文房间名）；--item 给物品
python run.py --action npc-choice --value "room_water_undynefinal" --key "obj_kitchentable" --x 160 --y 420 --text-key "obj_table_ask" --text "* Let's go?& &         Yes         No      \C " --yes-text-key "obj_table_yes" --yes-text "* Okay!/%%" --no-text-key "obj_table_no" --no-text "* .../%%" --goto "雪镇 - 船夫(妇)" --item 48 --range 160 --file data_win

# 给已注入过 myinteract 触发、与默认对话重叠的 NPC 补 Alarm_0 守卫（幂等）
python run.py --action guard-npc-alarm --key "obj_cactus" --instance 113927 --file data_win

# 检查损坏变量 NameStringID（读取会崩溃的陷阱），--fix 自动修复
python run.py --action verify-nsid --file data_win
python run.py --action verify-nsid --fix --file data_win

# 检查全房间实例 ID 异常（ID=0/重复会破坏 per-instance 变量表 → 崩溃+布局异常），--fix 自动分配唯一 ID
python run.py --action verify-instances --file data_win
python run.py --action verify-instances --fix --file data_win
```

---

## 🗄️ 房间列表

```bash
python run.py --action room-list
python run.py --action room-list --value "瀑布"
```

---

## ⏪ 备份与恢复

```bash
# 查看备份
python run.py --action list-backups --value data_win
python run.py --action list-backups --value ini
python run.py --action list-backups --value file0

# 恢复
python run.py --action undo --value data_win
python run.py --action undo --value data_win --backup 20240714_193500
python run.py --action undo --value file0
# ⚠️ undo 只回退"最后一次写入"（.bak）。若连续改了多个字段，需用时间戳备份回到更早状态：
python run.py --action list-backups --value file0
python run.py --action undo --value file0 --backup 20240714_193500
# data_win 的 undo/list-backups 支持 --dir 指定游戏数据文件
python run.py --action list-backups --value data_win --dir "path/to/game.ios"
```

### 改动自检（防止"零操作虚假成功"）

```bash
# 打印 game.ios 的 MD5（报告里原样贴出即可一行校验"是否真的改过"）
python run.py --action md5
```

- **搜索类命令零匹配时以退出码 3 结束**（`search-sprite` / `search-strings` /
  `search-textdata` / `search-vars` / `search-sctext`）：未找到即为失败，**禁止编造名称或结果**。
- **UTMT 脚本报 `ERROR:` 时以退出码 1 结束**，且**不会写回 game.ios**（避免"报错被吞后虚报成功"）。

---

## 🔒 沙箱模式与写入安全（v2.3.0+）

```bash
# 默认：data_win 写操作自动隔离到沙箱副本（打印写入回执：MD5 前后 + 退路）
python run.py --action spawn-obj --value "room_asrielroom" --key "obj_dummy1" --file data_win

# 确认后二选一：
python run.py --action sandbox-restore            # 应用沙箱到原文件
python run.py --action spawn-obj ... --commit     # 直写真实文件（含 Steam 同步）
python run.py --action spawn-obj ... --commit --no-steam-sync  # 直写但不同步 Steam

# 代码条目字节级体检（反汇编指纹 + 变量读写普查 + 往返稳定性）
python run.py --action verify-code --key "gml_Object_obj_cactus_Create_0" --file data_win

# 游戏内冒烟测试（注入+启动+断言+自动恢复；验证级别 in-game）
python run.py --action smoke-test --value room_torielroom --key obj_cactus --x 160 --y 150 --file data_win
```

---

## 💾 安装到 Agent

```bash
python install.py --skill
```

或运行完整安装（含 .NET + UTMT）：`python install.py`

```bash
python run.py --install
```

---

## 🎯 支线任务管理

```bash
# 重置任务状态（flag[510] = 0）
python run.py --action quest-init

# 查看自定义 flag 状态
python run.py --action quest-status

# 重置指定 flag
python run.py --action quest-init --flag 511
```

---

## 手动指定路径

```bash
# macOS 存档
python run.py --action list --dir "~/Library/Application Support/com.tobyfox.undertale"
# Windows 存档
python run.py --action list --dir "C:\Users\用户名\AppData\Local\UNDERTALE"
# 指定游戏数据文件
python run.py --action list-strings --file data_win --dir "path/to/game.ios"
```

> **关于中文字符**：英文版 Undertale 的字体不含中文字形。添加自定义对话时请使用英文（ASCII），中文不会渲染。
>
