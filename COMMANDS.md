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

## 🔒 沙箱模式

```bash
# 在 game.ios.sandbox 副本上操作
python run.py --action spawn-obj --value "room_asrielroom" --key "obj_dummy1" --sandbox --file data_win

# 确认后恢复副本到原文件
python run.py --action sandbox-restore
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
