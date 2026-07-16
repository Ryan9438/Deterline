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

---

## 📁 存档编辑

```bash
# 查看
python run.py --action get --key Love
python run.py --action get --key Room
python run.py --action list
python run.py --action list --file file0
python run.py --action find --value 42 --file file0

# 修改属性（INI）
python run.py --action set --key Love --value 20
python run.py --action set --key Kills --value 100
python run.py --action set --key Room --value 43
python run.py --action set --key Room --value "托丽尔的家"

# 修改 file0
python run.py --action set --key HP --value 50 --file file0
python run.py --action set --key WEAPON --value 52 --file file0    # 自动 AT+99
python run.py --action set --key ARMOR --value 53 --file file0     # 自动 DF+99
python run.py --action set --key GOLD --value 9999 --file file0

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
python run.py --action add-textentry --key "obj_mynpc_001" --value "* 你好/" --file data_win
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

---

## 🏗️ 房间布局编辑（`--file data_win`）

```bash
# 在房间中添加对象实例
python run.py --action spawn-obj --value "room_torielroom" --key "obj_sans" --x 320 --y 240 --file data_win

# 从房间移除对象实例（按类型，仅移除第一个匹配）
python run.py --action remove-obj --value "room_torielroom" --key "obj_sans" --file data_win

# 移除所有匹配的实例
python run.py --action remove-obj --value "room_torielroom" --key "obj_sans" --all --file data_win

# 按实例 ID 移除
python run.py --action remove-obj --value "room_torielroom" --instance 100085 --file data_win
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
```

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
