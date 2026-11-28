# samples/zhi_x · 纸星回信与组合样例（16 号计划包 31–35）

原创三房间支线样例 + 最小修改练习 + 组合对照。全部定义是原创文本；
游戏数据（game.ios）由作者自备，仓库不携带任何游戏资产。

## 样例清单

| 文件 | 说明 |
|---|---|
| `defn_v2_main.yaml` | 「纸星回信」主样例：三房间（room_ruins1/2/4）双分支（接受/拒绝）、4 单向门（含回访反向门）、3 NPC（两处选择）、states 状态机（session 级；delivered 声明 code 4 = `--flag-write` 候选写入值）、flag 520（513–999 空带运行时载体） |
| `defn_v2_min.yaml` | 单房 ASCII 冒烟样例（复制起步用；无 states/flag） |
| `defn_v2_notice.yaml` | 「告示」组合样例：与主样例同基线独立补丁（同房不同坐标；无门无 flag），演示 shared-script（obj_npc_marker 共享事件脚本）经同一合成构建合并 |

v1 样例在 `../c1-cjk/`（ASCII/CJK 两腿；本目录只含 v2）。

## 起步（一条链）

```bash
storyline-start --dir /path/to/game.ios            # 环境诊断 + 路由（只读）
cp samples/zhi_x/defn_v2_min.yaml my_story.yaml    # 复制最小样例
# 编辑 my_story.yaml（patch_id 必须换成你自己的；文本/坐标/房间按需）
storyline-plan  --value my_story.yaml --dir /path/to/game.ios
storyline-build --value my_story.yaml --workspace my_ws --dir /path/to/game.ios
storyline-apply --value my_story.yaml --workspace my_ws --dir /path/to/game.ios --commit
storyline-undo  --value my_story.yaml --dir /path/to/game.ios   # 前态撤销
```

组合两份定义：

```bash
storyline-compose --value a.yaml --value2 b.yaml --dir /path/to/game.ios   # 冲突表+合成计划
storyline-build   --value a.yaml --value2 b.yaml --workspace combo_ws --dir /path/to/game.ios
```

## 最小修改练习（每步预期可观察差异）

基线 = 主样例计划（语义指纹 `4fe848ae…`，7 op）。三例均在真实基线副本上实测：

1. **替换文本**：把 requester 的 prompt 里"回信"改成"急信"。
   预期：`storyline-plan --json` 的 `semantic_sha256` 变化（实测 `151dd9b0…`），
   `ops` 执行序不变。构建产物差异 = STR 内容变化（O7 strings 里的一处 change）。
2. **换入同类房间**：把 `rooms.pickup: room_ruins2` 改成 `room_ruins3`。
   预期：plan 的 `rooms.pickup.name` 变为 `room_ruins3`（实测通过，该房存在），
   指纹变（实测 `b7c1c96f…`）；门坐标仍须落在新房间界内（越界会写出前拒绝并
   指出 `doors.<id>` 字段）。
3. **改顺序**：把 order 末两条门对调。
   预期：执行序最后两项互换（实测 `back_to_start → back_to_pickup`），指纹变
   （`252f4008…`）——order 是语义（执行序），不是排版。

每个练习的验证链：`storyline-plan`（只读差异）→ 满意后 `storyline-build` →
`storyline-apply --commit` → 不满意 `storyline-undo`。

## 常见失败与修正

| 症状 | 修正 |
|---|---|
| `YAML 第 N 行: 重复键 'x'` | 同层删掉重复字段（YAML 层带行号） |
| `未知字段: ['x']（允许: [...]）` | 字段名拼写；对照允许集 |
| `rooms.<别名> 房间不存在` | 用 `storyline-plan` 前先确认房间里名（`room-info` 可查） |
| `坐标越界 … 不在 rooms.<别名> WxH 界内` | 按提示字段（`npcs.<id>`/`doors.<id>`）改坐标 |
| `未找到 UndertaleModCli.dll` | `export UTMT_CLI=/path/to/UndertaleModCli.dll`；CJK 构建另需 Pillow+numpy（ASCII 可起步） |
| `基线非干净，v2 拒绝` | 目标已含 deterline 补丁：先 `storyline-undo`/换干净副本；两补丁请用 `--value2` 合成 |

## 文件与目录

- 计划/回执：`<游戏目录>/.deterline/storyline/<游戏文件名>/<patch_id>/`
  （`build.json` 构建回执、`receipt.json` 应用/撤销回执）。
- 构建工作区：`<游戏目录>/.deterline/<游戏文件名>/<workspace>/`（单次消费：
  应用后即不在，撤销后需重新构建）。
- 证据分级：计划/构建/应用/撤销均为本地可复现（UTMT 副本级）；渲染/按键/
  真实存读档需游戏前台窗口（16 §7 待验）。`--flag-write`/`--view-track` 为
  默认禁用的候选能力，产物形态待实机复验。
