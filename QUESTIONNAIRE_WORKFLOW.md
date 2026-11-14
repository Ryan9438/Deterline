# Deterline — 问卷工作流模板与实现路径

> 目标：用户无需记忆 CLI 命令，通过交互式问卷完成全部修改操作。
> 每个选项标注了已验证的实现路径（PROJECT_SUMMARY 实验编号 / 功能名称）。

---

## 问卷总入口

```
请问你想修改什么？

  1. 📁 改存档（HP/LOVE/金钱/武器/传送）
  2. 💬 对话（加新对话 / 改已有对话 / 查台词）
  3. 🏗️ 造房间（尺寸/背景/地板）
  4. 🚪 放传送门（双向/单向）
  5. ⚔️ 战斗触发器（位置/敌群）
  6. 🎨 精灵替换（换外观）
  7. 🖼️ 纹理替换（导入图片）
  8. 📋 综合支线（全流程编排）
  9. 🧹 清理/回滚（撤销实验）
```

---

## 2. 💬 对话

> 进入本分类先分流：
> ```
> → 你要做什么？
>    A. 加一条新对话（新 NPC / 新台词）
>    B. 改游戏里已有的某句台词（改对话内容）
>    C. 查某段台词的 key / 位置
> ```
> 选 **A** → 走下方「2A 加对话」；选 **B** → 走「2B 改已有对话」；选 **C** → 用 `search-textdata` 搜索（注意：行序 ≠ 台词顺序，见 SKILL.md「改已有对话标准流程」）。

### 2A. 加对话

### 问卷流程

```
→ 你想改什么？
   1. 属性（HP / LOVE / 金钱 / 击杀数）
   2. 装备（武器 / 护甲）
   3. 传送（跳到指定房间）
   4. 重置（屠杀线 / 全量重置）

→ [选属性] 输入数值：___（⚠️ HP/EXP/GOLD 等属 file0，须 --file file0；ini 模式写它们只会有警告不生效）
→ [选装备] 选择装备：___（列出可选列表）
→ [选传送] 选择目标房间：___（中文名模糊搜索）
→ [确认] 执行
```

⚠️ **Agent 实现指引**：以上为人类可读版本。Agent 在执行时直接调用对应的 CLI 命令映射。例如用户选"改 HP"→ `set --key HP --value N`。如需验证参数正确性，先用 `get --key HP` 读当前值，执行后再 `list` 确认。

### 实现路径

> ⚠️ **权威来源在 file0**（已对照游戏源码 scr_load 核实）：LOVE/HP/AT/DF/EXP/GOLD/Kills/装备都在 file0，游戏运行时读 file0。ini `[General] Love/Kills/Room` 只是镜像副本（游戏不读它定数值）。改核心属性一律用 `--file file0`；用 INI 命令改 Love/Kills/Room 也会自动同步 file0。

| 选项 | CLI 命令 | 实验验证 |
|------|---------|---------|
| 改 HP（=最大生命） | `set --key HP --value N --file file0` | P0 基础存档编辑 ✅ |
| 改 LOVE | `set --key Love --value N --file file0` | P0 ✅（游戏读 file0[0]） |
| 改击杀数 | `set --key Kills --value N --file file0` | P0 ✅（游戏读 file0[10]） |
| 改金钱 | `set --key GOLD --value N --file file0` | P0 ✅ |
| 换武器 | `set --key WEAPON --value N --file file0` | P0 ✅（自动 AT 同步） |
| 传送 | `set --key Room --value "房间名"` | P0 ✅（支持中文名，自动同步 file0；须用唯一名，多匹配报错列出候选） |
| 重置屠杀线 | `reset-flags` | P0 ✅ |
| 全量重置 | `reset-all` | 实验 5/7 ✅ |
| 查看当前 | `list` / `list --file file0` | P0 ✅ |

### 数据来源

- 装备列表：`ITEMS` 字典（modify_save.py，行号随版本漂移，以 grep 为准）
- 武器攻击加成：`WEAPON_AT` 字典
- 护甲防御加成：`ARMOR_DF` 字典
- 房间名：`rooms.json`（244 个中文名）

---

## 2. 💬 加对话

### 问卷流程

```
→ NPC 的标识名（英文 key）：___
   示例: obj_my_npc_001

→ 对话内容（英文，不支持中文）：___
   格式: 每页以 / 结尾，末页以 /%% 结尾
   换行用 &，控制符 \C(选择框) \R(红字)

→ 头像角色：
   0=无 1=Toriel 2=Flowey 3=Sans
   4=Papyrus 5=Undyne 6=Alphys
   7=Asgore 8=Mettaton 9=Asriel

→ 头像表情（Sans）：
   0=普通 1=轻笑 2=眨眼 3=慢眨眼 4=无眼

→ 触发方式（NPC 靠近说话）：
   1. 可重复（默认）：靠近自动说话，关对话后仍在范围内会再弹，走出范围停止
   2. 单次：只触发一次，触发后 NPC 自毁消失（--once）

→ 也添加到 textdata_en 映射表？(Y/n)

→ [确认] 执行
```

> ⚠️ v2.3.0：两种模式都**不锁移动**（状态机在当前 UTMT 环境下产生游戏内死代码，2026-11 审计；恢复锁移动需先解决该字节级问题）。

⚠️ **Agent 推荐使用 `guided-add-dialogue` 命令**替代手拼参数：
```bash
python run.py --action guided-add-dialogue \
  --key "obj_my_npc" --value "* Hello/%%" \
  --face 3 --emotion 1 --file data_win
```
输出结构化反馈（✅/❌），Agent 可逐步骤追踪。

### 实现路径

| 步骤 | CLI 命令 | 实验验证 |
|------|---------|---------|
| 添加文本到 STRG | `add-string --value "..." --file data_win` | 实验 1 ✅ |
| 注册到 textdata_en | `add-textentry --key "K" --value "V" --face N --emotion N --file data_win` | 实验 8 ✅ |
| **引导式添加** | `guided-add-dialogue --key "K" --value "V" --face N --emotion N --file data_win` | 2026-07-28 ✅ |
| **NPC 靠近说话（可重复）** | `npc-dialogue --value "room_xxx" --key "obj_xxx" --x N --y N --text-key "K" --text "* .../%%" --face N --emotion N --file data_win` | 游戏内实测触发 ✅（2026-11，v2.3.0 扁平形态） |
| **NPC 靠近说话（单次）** | `npc-dialogue ... --once --file data_win` | 触发后 NPC 自毁，游戏内实测 ✅（2026-11） |
| **NPC 靠近说话（自定义距离）** | `npc-dialogue ... --range 160 --file data_win` | 触发距离可调（默认 50px）✅ |
| **NPC 带 YES/NO 选择** | `npc-choice --value "room_xxx" --key "obj_xxx" --x N --y N --text-key "K" --text "* ...\C " --yes-text-key "KY" --yes-text "..." --no-text-key "KN" --no-text "..." [--goto 房间] [--item ID] [--range N] [--repeat] --file data_win` | 选择框不循环重弹（msg[0] 自动替换）+ 单次触发默认 ✅ |
| 批量导入 | `batch-add-textentry --value ./dialogues.json --file data_win` | P3 ✅ |
| 搜索已有 | `search-textdata --value "keyword" --file data_win` | 实验 8 ✅ |
| ASCII 校验 | `_validate_ascii_text()` | 2026-07-28 新增 ✅ |

### 对话格式规则（已验证）

| 规则 | 说明 | 来源 |
|------|------|------|
| `* ` 前缀 | 对话必须以 `* ` 开头 | 实验 1 |
| `/` 页分隔 | 中间页以此为结尾 | 实验 1 |
| `/%%` 末页 | 最后一页 | 实验 1 |
| `%%%` 数组终止 | `global.msg[]` 结束符 | 实验 4 |
| `&` 换行 | 同一页内换行 | 安全边界 |
| `\C ` 选择框 | 创建 YES/NO 选择 | 实验 5/7 |
| `\F\E` 控制符 | 由 `--face` `--emotion` 自动插入 | 实验 8 |
| 英文(ASCII) | 不支持中文/日文 | 2026-07-28 底层限制 |

### 2B. 改已有对话

> ⚠️ **关键**：textdata 的 key 编号 ≠ 台词顺序，`search-textdata` 列表第一行 ≠ 第一句。确定"第几句"必须反编译场景代码。完整步骤见 **SKILL.md「改已有对话的标准流程」**。

### 问卷流程

```
→ 谁在说话 / 哪个场景：___（如 Sans 雪镇开场、Toriel 遗迹、审判长廊…）
→ 改第几句（1 = 第一句）：___
→ 目标句当前文本（让 Agent 核对定位，防止选到重复变体）：___
   示例: "Human."  "Don't you know how to greet a new pal?"
→ 新文本（英文 ASCII，保留 * 前缀与 / 结尾格式）：___
   （不改头像/表情，除非用户明确要求）

→ [确认] Agent 按标准流程定位 key 并修改
```

### Agent 定位步骤（必须按序执行，禁止跳步）

```
1. search-textdata --value "<key前缀>" --file data_win
   → 确认 key 家族（如 Sans 开场 = "darksans1"）
2. search-vars --value "<key前缀>" --file data_win
   → 找到引用这些 key 的对象事件（如 gml_Object_obj_darksans1_Step_0）
3. decompile-code --key "<该事件>" --file data_win --old "scr_gettext"
   → 看 global.msg[N] = scr_gettext("key") 顺序 → 第 N 句 = 哪个 key
4. search-textdata --value "<确定的key>" --file data_win
   → 核对旧文本与用户描述一致（防重复变体）
5. update-textentry --key "<key>" --value "<新文本>" --file data_win
   （无此命令时用 find-replace-code 改 gml_Script_textdata_en 对应行）
6. search-textdata --value "<key>" --file data_win → 验证
```

### 实现路径

| 步骤 | CLI 命令 | 说明 |
|------|---------|------|
| 找 key 家族 | `search-textdata --value "darksans1" --file data_win` | ⚠️ 行序非台词顺序 |
| 找场景代码 | `search-vars --value "darksans1" --file data_win` | 定位 `gml_Object_..._Step_0` |
| 看台词顺序 | `decompile-code --key "gml_Object_..._Step_0" --old "scr_gettext" --file data_win` | msg[0]=第 1 句 |
| 核对旧文本 | `search-textdata --value "obj_xxx_NNN" --file data_win` | 防重复变体 |
| **改已有条目** | `update-textentry --key "obj_xxx_NNN" --value "* 新文本/" --file data_win` | 新命令，幂等替换 |
| 改（无新命令时） | `find-replace-code --key "gml_Script_textdata_en" --old "旧文本" --value "新文本" --file data_win` | 源码级替换后重编译 |
| 验证 | `search-textdata --value "obj_xxx_NNN" --file data_win` | 确认已更新 |

**已核实示例：Sans 雪镇开场第一句** → key `obj_darksans1_345`（`* Human./`），引用代码 `gml_Object_obj_darksans1_Step_0:20`（`msg[0] = scr_gettext("obj_darksans1_345")`）。

---

## 3. 🏗️ 造房间（改造已有房间）

> ⚠️ **强制规则：禁止新建房间序号**（`create-room` 已废弃）。
> 游戏运行时**无法识别新增房间**，`create-room` 创建的房间会因找不到而传送进错房间、遇神烦狗。
> 因此"造房间"= **选择游戏里已有的房间进行改造**。选房必须查阅 **`ROOMS_GUIDE.md`**（336 个房间全量分类清单）。

### 问卷流程

```
→ 房间内部名（从 ROOMS_GUIDE.md 选已有房间，禁止新造）：room_xxx
→ 选房规则：
   1. 要背景/视差 → 选 B1（数据驱动背景；横长可滚动 W>320 最佳）或 B2（对象驱动背景）
   2. 要纯 Tile 地板 → 选 A
   ※ 提供候选时列出房间号 + 尺寸 + 中文名，让用户挑选
→ 尺寸：宽 ___ 高 ___ (默认 640x480)
→ 标题（中文/英文）：___
→ 背景色（hex）：___ (默认 000000)
→ 房间类型：
   1. 普通 Tile 房间（遗迹风格，纯色底 + Tile 地面）
   2. 视差背景房间（雪镇风格，有背景图）
   ※ 类型 2 需要先创建背景资源

→ [选类型2] 背景图：
   a) 用内置生成器（渐变/条纹/棋盘/点阵/星空）
   b) 导入外部 PNG

→ 地板类型：
   a) 无
   b) 棋盘格（内置生成器）
   c) 自定义 Tile（需准备 PNG）

→ [确认] 执行
```

### 实现路径（改造已有房间，已验证）

| 步骤 | CLI 命令 | 实验验证 |
|------|---------|---------|
| 选择已有房间 | 查 `ROOMS_GUIDE.md`（禁止 `create-room` 新建） | ✅ |
| 清空房间 | `remove-obj --value room_xxx --key <obj> --all` + `remove-tile --value room_xxx` | 实验 D ✅ |
| 设置房间尺寸 | `set-room-prop --value room_xxx --width W --height H --caption "名称" --file data_win`（房间 > View 才有滚动空间） | P4-2 ✅ |
| 设置视角 | `set-room-view --value room_xxx --index 0 --view-w 320 --view-h 240 --port-w 640 --port-h 480 --follow obj_mainchara --file data_win` | P4-2 ✅（View=320 关键） |
| 生成背景图 | `bg_generator.py --pattern gradient --colors "#R,#G,#B" --output bg.png` | P4-2 ✅ |
| 生成棋盘 | `bg_generator.py --pattern checkerboard --colors "#A,#B" --tile-size 32 --output floor.png` | P4-2 ✅ |
| 创建背景资源 | `create-bg-asset --value "bg_xxx" --image "bg.png" --file data_win` | P4-2 ✅ |
| 注入运行时背景 | `gml-bg --value room_xxx --bg "bg_xxx" --slot 0 --speedx 0.15 --speedy 0 --file data_win` | P4-2 ✅ |
| 放置主角+碰撞 | `spawn-obj --value room_xxx --key obj_mainchara --x X --y Y` + 碰撞墙 | ✅ |
| 铺设 Tile 地面 | CSX 直接操作 `room.Tiles`（直接改已有房间的 Tile） | 实验 D ✅ |
| 进入房间验证 | `set --key Room "<房间ID>"`（必须用 game.ios 中已存在的房间） | ✅ |

### ⚠️ 已知限制

- **禁止 `create-room`**：新建房间序号游戏运行时无法识别，会导致传送进错房间遇神烦狗
- **Tile 房间背景不可用**：`gml-bg` 在 A 类 Tile 房间（8 层背景全 disabled）无效，渲染器跳过背景绘制。需先 `set-room-bg --enable true` 启用某层使其变 B1 类，再注入 `gml-bg`
- **背景房间需要 backgrounder 对象**：需手动 `spawn-obj` 放置背景控制器
- **View 必须 320×240**：port 640×480，2x 缩放。View=640×480 破坏视角跟随
- **`set --key Room` 只能填 game.ios 中已存在的房间号**：写入不存在的房间会触发运行时错误（神烦狗）

---

## 4. 🚪 放传送门

### 问卷流程

```
→ 当前房间（放置门的位置）：___
→ X 坐标：___ Y 坐标：___
→ 目标房间（传送到哪里）：___
→ 目标出生点 X：___ Y：___
→ 是否双向（对面也放一个返回门）？(Y/n)

→ [确认] 执行
```

### 实现路径

| 步骤 | CLI 命令 | 实验验证 |
|------|---------|---------|
| 创建单向门 | `create-door --value "cur_room" --key "target_room" --x N --y N --spawn-x N --spawn-y N --file data_win` | 实验 A ✅ |
| 自动注册目标房间 | 自动调用 `_update_rooms_json()` | 实验 B ✅ |
| 列出房间门 | `list-doors --value room_xxx --file data_win` | 实验 B ✅ |
| 按坐标移除 | `remove-door --value room_xxx --x N --y N --file data_win` | 实验 B ✅ |
| 全部移除 | `remove-door --value room_xxx --all --file data_win` | 实验 B ✅ |

### 核心技术细节

- **触发方式**：`point_distance(x, y, obj_mainchara.x, obj_mainchara.y) < 80`（半径 80px）
- **标识方式**：`Create_0` 中按 `(room_get_name(room), x, y)` 坐标匹配分支
- **精灵**：`spr_cactus`（仙人掌，37×49，可见标记）
- **多门共存**：每新增一个门在 `Create_0` 追加一条 `if (_rn == "room" && x == N && y == N)` 分支
- **出生点定位**：Step 事件设 `global.deterline_pending_x/y`，目标房间的门 `Create_0` 读取并定位玩家

---

## 5. ⚔️ 战斗触发器

### 问卷流程

```
→ 放置房间：___
→ X 坐标：___ Y 坐标：___
→ 敌群（battlegroup ID）：___
   常用（2026-11 审计修正，反编译 scr_battlegroup 核对）：
    1 = 3xFroggit（遗迹）
    2 = Dummy（练习战）
    3 = fakefroggit（遗迹）
    5 = Whimsun（遗迹）
    7/8/10/11 = Moldsmal（通用）
    40 = Aaron
    43 = Woshua
    45 = Mad Dummy
    47 = Undyne 战
→ 战斗边框样式（默认 0）：___

→ [确认] 执行
```

### 实现路径

| 步骤 | CLI 命令 | 实验验证 |
|------|---------|---------|
| 创建战斗 | `create-battle --value "room_xxx" --key BG_ID --x N --y N --border N --file data_win` | 方向 B ✅ |
| 精灵 | `spr_markerB`（20×20，B 标记） | 方向 B ✅ |
| 触发 | `place_meeting(x, y, obj_mainchara)` + `global.interact == 0` | 方向 B ✅ |

### battlegroup 数据来源

`scr_battlegroup` 脚本（1649 行）包含了全部敌群定义。通过 `decompile-code --key gml_Script_scr_battlegroup` 查看完整列表。

---

## 6. 🎨 精灵替换

### 问卷流程

```
→ 要修改的对象：obj_xxx（如 obj_sans_actor）
→ 新精灵：spr_xxx（如 spr_sans_dangerous）
   用 search-sprite 搜索可用精灵
→ 需要同时替换纹理吗？(y/N)
   → [是] 替换精灵纹理：
      - 导出当前精灵：export-sprite
      - 编辑 PNG
      - 替换回纹理图谱：replace-sprite

→ [确认] 执行
```

### 实现路径

| 步骤 | CLI 命令 | 实验验证 |
|------|---------|---------|
| 搜索精灵 | `search-sprite --value "keyword" --file data_win` | P4-1 POC ✅ |
| 查看对象 | `get-obj --key obj_xxx --file data_win` | P4-1 POC ✅ |
| 切换精灵 | `set-obj-sprite --key obj_xxx --value spr_xxx --file data_win` | 实验 13 ✅ |
| 追加代码（适配逻辑） | `append-code --key gml_Object_obj_xxx_Step_0 --value "GML" --file data_win` | 实验 13/14 ✅ |
| 预览精灵 | `preview-sprite --key spr_xxx --file data_win` | P4-1-1 ✅ |
| 导出精灵 | `export-sprite --key spr_xxx --value out.png --frame 0 --file data_win` | P4-1-1 ✅ |
| 替换精灵纹理 | `replace-sprite --key spr_xxx --value edit.png --frame 0 --file data_win` | 实验 A/B ✅ |
| 复制精灵 | `duplicate-sprite --key spr_src --value spr_dst --file data_win` | P4-1-1 ✅ |
| 一键换色 | `colorize-sprite --key spr_src --value spr_dst --hue-from "180-260" --hue-to 0 --file data_win` | P4-1-1 ✅ |

### 关键技术约束（已验证）

- 目标对象的 Step 事件可能每帧覆盖 `sprite_index`（如 `scr_npcdir`），需用 `append-code` / `prepend-code` 在适当时机覆盖
- `spr_cactus`（37×49）是最常用的可见标记精灵
- 精灵帧 0 和帧 2 可能共享同一纹理区域（`SourceX/Y` 相同），替换一次影响两帧

---

## 7. 🖼️ 纹理替换（导入图片）

### 问卷流程

```
→ 操作类型：
   1. 替换整张纹理图谱（export-texture → 编辑 → replace-texture）
   2. 替换单个精灵纹理（export-sprite → 编辑 → replace-sprite）
   3. 创建新背景资源（从 PNG 导入）

→ [选1/2] 要修改的精灵/纹理名：___
→ [选1/2] 编辑后的 PNG 路径：___
→ [选3] PNG 路径：___ 背景名字：___

→ [确认] 执行
```

### 实现路径

| 步骤 | CLI 命令 | 实验验证 |
|------|---------|---------|
| 列出纹理 | `list-textures --limit 30 --file data_win` | P4-1-1 ✅ |
| 导出纹理图谱 | `export-texture --key "Texture 0" --value out_dir/ --file data_win` | 实验 C ✅ |
| 替换纹理图谱 | `replace-texture --key "Texture 0" --value tex.png --file data_win` | 实验 C ✅（MD5 无损验证） |
| 导出精灵帧 | `export-sprite --key spr_xxx --value out.png --frame 0 --file data_win` | 实验 A/B ✅ |
| 替换精灵帧 | `replace-sprite --key spr_xxx --value edit.png --frame 0 --file data_win` | 实验 A ✅ |
| 批量导出精灵 | `dump-sprites --value out_dir/ --file data_win` | P4-1-1 ✅ |
| 创建背景资产 | `create-bg-asset --value "bg_xxx" --image bg.png --file data_win` | P4-2 ✅ |
| 生成像素背景 | `bg_generator.py --pattern gradient --colors "#A,#B" --output bg.png` | P4-2 ✅ |
| 终端预览 | `preview-sprite --key spr_xxx --file data_win` | P4-1-1 ✅ |

---

## 8. 📋 综合支线（全流程编排）

### 问卷流程（分步）

```
→ 支线名称：___

Step 1/6 — 创建场景
  → 房间名：room_xxx
  → 尺寸：宽 ___ 高 ___
  → 背景色：___

Step 2/6 — 添加 NPC 对话
  → NPC key：obj_xxx_001
  → 对话内容：___
  → 头像角色：___ 表情：___

Step 3/6 — 放传送门
  → 从当前房间传送到支线房间
  → 出生点坐标：( ___ , ___ )

Step 4/6 — 放置战斗（可选）
  → 敌群 ID：___
  → 位置：( ___ , ___ )

Step 5/6 — 添加奖励（可选）
  → 物品 ID：___
  → 给哪个 NPC 交互触发：___

Step 6/6 — 确认总览 → 执行
```

### 已实现的完整支线参考

详见 PROJECT_SUMMARY 实验 4-14。以下是最完整的支线模板：

| 阶段 | 功能 | 实现方式 |
|------|------|---------|
| 对话 | `add-textentry` 注册多段对话 | `scr_gettext("key")` 读取 |
| NPC | `npc-dialogue` 一键生成（推荐）| 加对话 + spawn + 已验证扁平距离触发块 + 自动守卫 Alarm_0 |
| NPC（手动） | `spawn-obj` + `append-code` 注入距离触发 | Step 事件 `point_distance`（⚠️ 手写状态机形态在当前 UTMT 环境游戏内死代码——用 `npc-dialogue` 生成的扁平形态；原生 readable 对象须 `Alarm_0` 守卫） |
| 传送 | `create-door` 双向门 | `room_goto` + `global.deterline_pending_*` 出生点 |
| 战斗 | `create-battle` | `global.battlegroup` + `obj_battleblcon` |
| 条件 | `global.flag[510/511]` 状态机 | `quest-init/status` |
| 奖励 | `scr_itemget(item_id)` 或 CLI `set --key INV --value ID` | 实验 B ✅ |

---

## 9. 🧹 清理 / 回滚

### 问卷流程

```
→ 操作类型：
   1. 查看可用快照
   2. 回滚到指定快照
   3. 查看备份
   4. 撤销到最近备份

→ [选1] 输出快照列表
→ [选2] 选择快照名称：___
→ [选3/4] 选择文件类型：ini / file0 / data_win

→ [确认] 执行
```

### 实现路径

| 步骤 | CLI 命令 | 实验验证 |
|------|---------|---------|
| 创建快照 | `experiment-snapshot --value "名称"` | P4-1-1 ✅ |
| 列出快照 | `experiment-list` | P4-1-1 ✅ |
| 恢复快照 | `experiment-restore --value "名称"` | P4-1-1 ✅（已修复 .app bundle bug） |
| 查看备份 | `list-backups --value data_win` | 实验 8 ✅ |
| 撤销 | `undo --value data_win` | 实验 8 ✅ |
| 撤销到指定版本 | `undo --value data_win --backup 时间戳` | 实验 8 ✅ |

---

## 附录：各问卷选项的 CLI 命令汇总

```
# 存档（核心属性在 file0，游戏读 file0）
get --key Love
set --key Love --value 20 --file file0
set --key Kills --value 100 --file file0
set --key WEAPON --value 52 --file file0
room-list --value "瀑布"
set --key Room --value "雪镇 - 船夫(妇)"     # 自动同步 file0（须唯一名）
reset-flags

# 对话
add-string --value "text" --file data_win
add-textentry --key "K" --value "V" --face 3 --emotion 0 --file data_win
update-textentry --key "K" --value "新文本" --file data_win   # 改已有台词
search-textdata --value "keyword" --file data_win
batch-add-textentry --value ./file.json --file data_win

# 房间（只改已有房间，禁止 create-room 新建）
set-room-view --value room_tundra_town --index 0 --view-w 320 --view-h 240 --file data_win
gml-bg --value room_tundra_town --bg bg_xxx --slot 0 --speedx 0.15 --file data_win
create-bg-asset --value bg_xxx --image bg.png --file data_win

# 传送门
create-door --value cur_room --key target_room --x 160 --y 120 --spawn-x 320 --spawn-y 240 --file data_win
list-doors --value room_xxx --file data_win
remove-door --value room_xxx --x 160 --y 120 --file data_win

# NPC 对话（安全，自动处理原生 readable 冲突）
npc-dialogue --value room_xxx --key obj_cactus --x 170 --y 180 --text-key "obj_cactus_hi" --text "* Hi/%%" --file data_win
guard-npc-alarm --key obj_cactus --instance 113927 --file data_win

# NPC 带 YES/NO 选择（默认单次触发；分支文本自动替换 msg[0]，不循环重弹）
npc-choice --value room_water_undynefinal --key obj_kitchentable --x 160 --y 420 --text-key "obj_table_ask" --text "* Let's go?& &         Yes         No      \C " --yes-text-key "obj_table_yes" --yes-text "* Okay!/%%" --no-text-key "obj_table_no" --no-text "* .../%%" --goto "雪镇 - 船夫(妇)" --item 48 --range 160 --file data_win

# 战斗
create-battle --value room_xxx --key 40 --x 200 --y 120 --file data_win

# 精灵纹理
list-sprites --limit 30 --file data_win
set-obj-sprite --key obj_xxx --value spr_xxx --file data_win
export-sprite --key spr_xxx --value out.png --frame 0 --file data_win
replace-sprite --key spr_xxx --value edit.png --frame 0 --file data_win
colorize-sprite --key spr_src --value spr_dst --hue-from "180-260" --hue-to 0 --file data_win

# 快照
experiment-snapshot --value "my_exp"
experiment-list
experiment-restore --value "my_exp"
```
