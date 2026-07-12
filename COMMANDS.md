# 常用指令速查

所有命令都在 `undertale-save-editor` 文件夹内运行。

---

## 查看信息

```bash
# 查看当前 LOVE / 等级
python run.py --action get --key Love

# 查看当前房间
python run.py --action get --key Room

# 查看所有 INI 变量
python run.py --action list

# 查看 file0 完整状态（属性、装备、BOSS）
python run.py --action list --file file0

# 查看 file0 原始数据（前 50 行）
python run.py --action list --file file0

# 搜索某个值在 file0 中的位置
python run.py --action find --value 42 --file file0
```

---

## 修改属性（INI — 推荐优先改这里）

```bash
python run.py --action set --key Love --value 20
python run.py --action set --key Kills --value 0
python run.py --action set --key Room --value 43
python run.py --action set --key fun --value 66
python run.py --action set --key Name --value "Frisk"
python run.py --action set --key Gameover --value 0
```

---

## 修改属性（file0）

```bash
python run.py --action set --key HP --value 50 --file file0
python run.py --action set --key MAXHP --value 99 --file file0
python run.py --action set --key GOLD --value 9999 --file file0
python run.py --action set --key AT --value 10 --file file0
python run.py --action set --key DF --value 10 --file file0
python run.py --action set --key EXP --value 0 --file file0
python run.py --action set --key KILLS --value 0 --file file0
```

---

## 武器 / 护甲（自动同步 AT/DF）

```bash
# 装备真刀（AT+99）
python run.py --action set --key WEAPON --value 52 --file file0

# 装备磨损的刀（AT+15）
python run.py --action set --key WEAPON --value 51 --file file0

# 装备空枪（AT+12）
python run.py --action set --key WEAPON --value 49 --file file0

# 装备心形锁坠（DF+15）
python run.py --action set --key ARMOR --value 50 --file file0

# 装备提米盔甲（DF+20）
python run.py --action set --key ARMOR --value 64 --file file0

# 装备染色围裙（DF+11）
python run.py --action set --key ARMOR --value 46 --file file0

# 装备芭蕾舞鞋（AT+7）
python run.py --action set --key WEAPON --value 25 --file file0
```

> 装备武器/护甲时，WEAPON_AT / ARMOR_DF 自动同步，无需单独设置。

---

## 物品栏

```bash
# 物品 ID 参考：
#   0  = (空)
#   1  = 怪物糖果
#   11 = 奶油肉桂派
#   46 = 染色围裙
#   51 = 磨损的刀
#   52 = 真刀
#   64 = 提米盔甲

python run.py --action set --key INV1 --value 11 --file file0
python run.py --action set --key INV2 --value 1 --file file0
python run.py --action set --key INV3 --value 52 --file file0
```

---

## BOSS / 怪物状态

```bash
# 宽恕托丽尔
python run.py --action set --key TORIEL --value 5 --file file0

# 击杀托丽尔（屠杀线）
python run.py --action set --key TORIEL --value 4 --file file0

# 击杀帕派瑞斯
python run.py --action set --key PAPYRUS --value 1 --file file0

# 击杀安黛因（竞技场）
python run.py --action set --key UNDYNE_2 --value 1 --file file0

# 击杀镁塔顿
python run.py --action set --key METTATON --value 1 --file file0
```

---

## 传送（支持中文房间名）

```bash
# 通过房间 ID
python run.py --action set --key Room --value 43

# 通过中文名称
python run.py --action set --key Room --value "安黛因竞技场"
python run.py --action set --key Room --value "雪镇 - 镇子"
python run.py --action set --key Room --value "王座 房间"

# 搜索房间
python run.py --action room-list --value 遗迹
python run.py --action room-list --value 瀑布
python run.py --action room-list --value 热域
```

---

## 撤销修改

```bash
# 撤销 ini 修改（从 .bak 恢复）
python run.py --action undo --value ini

# 撤销 file0 修改
python run.py --action undo --value file0
```

> 每次修改前自动创建 `.bak` 备份，执行 undo 即可恢复。

---

## 路线相关

```bash
# 重置屠杀线标志（INI + file0 Kills 同步清理）
python run.py --action reset-flags

# 创建"世界已删除"标记（屠杀线结局）
python run.py --action create-system-info --value 962

# 创建"已献出灵魂"标记
python run.py --action create-system-info --value 963
```

---

## 安装到 Agent

```bash
# macOS — 双击 Install.app
# Windows — 双击 install.bat
# 通用 — 终端
python run.py --install
```

---

## 手动指定存档目录

```bash
# macOS
python run.py --action list --dir "~/Library/Application Support/com.tobyfox.undertale"

# Windows
python run.py --action list --dir "C:\Users\你的用户名\AppData\Local\UNDERTALE"
```
