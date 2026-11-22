# c1-cjk —— 中文支线样例（准备 / 验收 / 撤销 三阶段拆解）

定义驱动的中文 npc-choice 样例（`deterline.storyline/v1`，typer=31 +
CJK 字体栈注入），替代旧单脚本形态 `C1-支线脚本/c1_branch_cjk.sh`
（该形态打印实机提示后**立即自动撤销**、用固定 /tmp 路径、硬编码
`python3`——三处都已在本目录拆解，见 14 手册 §1）。

## 三阶段模型（时点语义）

| 阶段 | 命令 | 做什么 | 写什么 |
|---|---|---|---|
| 1 准备 | `prepare.sh [--out DIR]` | 独立运行目录 + 基线副本 + 只读计划 + 工作区构建 + 应用预览 + **显式 `--no-steam-sync` 整包应用** | 仅运行目录（副本/回执/工作区/指纹） |
| 2 验收 | `verify.sh <运行目录>` | 指纹链核对 + O7 结构化差异 + recovery-scan；打印实机清单（材料，不执行） | 只读 + 验收产物落运行目录 |
| 3 撤销 | `undo.sh <运行目录>` | `.bak → game.ios` + md5 对账基线 + recovery-scan | 仅运行目录 |

**应用发生在 prepare 内、撤销只在操作者显式运行 undo.sh 时发生。**
两阶段之间，已应用副本长期保留在运行目录，可跨会话交接——不再出现
"提示打印完产物即被撤销" 的旧形态问题。每次运行强制全新目录（已存在
即拒），构建指纹与交接信息在 `run.json`。

## 前置条件

1. **Python ≥ 3.10**（`X | None` 模块级注解；3.9 导入期即 TypeError）。
   脚本自动按 `DL_PYTHON` → python3.14/3.13/3.12/3.11/python3 顺序探测。
   本机已知卡点：系统 `python3` = 3.9.6 不可用。
2. **Pillow + numpy**（CJK 字形页生成 + emb20 象限合成，requirements.txt；
   numpy 原未登记，2026-11-22 本样例实跑发现后补录）。PEP 668 环境直接
   `pip install` 会被拒，先建 venv：
   ```bash
   python3.11 -m venv ~/.venvs/dl-c1
   ~/.venvs/dl-c1/bin/pip install pillow numpy
   DL_PYTHON=~/.venvs/dl-c1/bin/python samples/c1-cjk/prepare.sh
   ```
3. **dotnet + UndertaleModCli**（data_win 全链路 CSX 探针）。`UTMT_CLI`
   未设时脚本探测 `~/UndertaleModTool/…/Release/net{10,9,8}.0/`；
   dotnet 不在 PATH 时自动补 `/opt/homebrew/bin`（LaunchAgent 最小 PATH
   的本机卡点）。
4. **vendor 字体**（不入库，.gitignore 口径）：
   `assets/fonts/vendor/fusion-pixel-12px/fusion-pixel-12px-monospaced-zh_hans.ttf`
   md5 `0349f9f173558216daa5a9579537da8a`（fusion-pixel 12px，OFL 许可）。
   来源：官方发布 zip 或既有本地检出复制，md5 不符即拒。
5. **干净基线**：检出 `game.ios` md5 必须 = `fc049850856dea4ef1427bbf5653fc47`
   （rc6），否则拒跑（样例钉在该基线上）。

## 快速上手

```bash
cd <检出根>
DL_PYTHON=~/.venvs/dl-c1/bin/python samples/c1-cjk/prepare.sh   # 全新运行目录（缺省 /tmp 下，--out 可指定）；缺省探测已得 ≥3.10 且 Pillow/numpy 就绪时可省 DL_PYTHON 前缀（见前置条件 1/2）
samples/c1-cjk/verify.sh <运行目录>       # 本地沙箱级验收
samples/c1-cjk/undo.sh  <运行目录>        # 显式撤销回基线
```

## 运行目录布局（交接信息）

```
<run>/
  run.json            ← 机器可读交接：指纹链/阶段时间线/环境（python·dotnet·UTMT）
  defn_cjk.yaml       ← 本样例定义副本（patch_id det_c1_cjk，flag 508 declared-only）
  game.ios            ← 基线副本（应用后 = 已应用产物；undo 后 = 回基线）
  game.ios.bak        ← 撤销点（prepare 的 EditPlan 备份；undo 后 = 已应用产物）
  game.ios.bak.<时间戳>  ← apply / undo 时对**当时的 game.ios** 的滚动留档
                         （apply 留档应用前值=基线；undo 留档撤销前值=已应用产物）
  plan.json           ← 只读计划（期望资源/结构集）
  build.out.json      ← 构建回执（产物 sha256 / 声明差异 / defn_sha256）
  apply_preview.json / apply_commit.json   ← 应用回执（before/after 指纹）
  .deterline/         ← 工作区 c1_cjk 与 storyline 回执（工具层自管）
  verify_diff.txt / verify_recovery.json / undo_recovery.json
```

`run.json.status`: `prepared`（已应用，等验收/撤销）→ `undone`（已回基线）。
prepare 失败会留 `FAILED` 标记，现场不清理。

**undo 是单次语义**：撤销本身会滚动 `.bak`（撤销后 `.bak` = 已应用产物），
重复运行 undo.sh 会因基线指纹闸门拒绝——这是 fail-closed 设计；要重建
材料请对全新运行目录重跑 prepare.sh。

## 实机窗口（仅用户值守；脚本零触真实数据）

本样例的一切写入只发生在**运行目录副本**内；真实 Steam 目录与存档由
操作者在授权窗口手工处理（03 §10），步骤：

1. 真实安装前备份（含 `UNDERTALE.app/Contents/Resources/game.ios` 哈希留档）；
2. 将运行目录中**已应用副本**安装到游戏数据位（或按 05 记录的安装路径）；
3. `steam://run/391540` → room_ruins1 触发点（obj_npc_marker @ (100,200)
   半径 60），按 05 §5.2 / 15-SOP 口径逐格记录：首屏中文（typer=31）、
   选项行、是·否两支、once 自毁、重进、存读档持久语义，holdSeconds ≥ 0.15；
4. 恢复真实安装备份 + 哈希核对（fc049850856dea4ef1427bbf5653fc47）。

渲染语义在窗口记录前一律是 sandbox 级证据，不得升格为实机级。

## 支持边界

- macOS bash（`md5 -q` / `shasum`）；Windows 游戏侧为等待条件。
- flag_id 508 仅声明（模板 v1 不写入——无实机证据的写入路径禁用）。
- 构建差异声明闸门（O7）由工具链强制：未声明资源/结构变更直接拒绝出候选。
