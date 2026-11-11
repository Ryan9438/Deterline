# Changelog

## v2.4.0 — 2026-11-11（写入事务层 + 实验工作区 + 命令注册表）

**性质：架构重构（Codex 协作产出），接口级新增 `--preview` / `--workspace`；命令面与文档 SSOT 不变（86 命令）。已由 ZCode 独立核验（见下）。**

### 架构

- **事务写入层** `deterline/transactions.py`：`EditPlan` 记录目标/基线哈希/拟写入内容；提交时按序取得文件锁、目标旁暂存 + 回滚副本、备份确认后逐文件 `os.replace`；后续替换失败自动回滚已替换文件；大文件流式复制。
- **实验工作区** `deterline/sandbox.py`：默认副本迁移到源文件旁 `.deterline/<文件名>/default/`；`--workspace NAME` 命名隔离；manifest 记录源文件 SHA-256 与每次成功编辑的产物哈希；应用前校验源文件未漂移，过期工作区拒绝应用。旧 `*.sandbox` 在存在时仍优先（兼容路径）。
- **命令注册表** `deterline/command_handlers.py`：取代 85 分支 if/elif 链；`ACTION_CHOICES = COMMANDS`；路由按 `any/data_win/ini/file0` 分键。
- **统一 UTMT 编辑批次** `utmt.GameEdit` + `game_edit()`：多步 UTMT 编辑共享暂存目录、中间产物喂下一步、末步通过后经 EditPlan 一次性提交（含 Steam 目标成组备份提交）；GameMaker FORM 头校验；`submit_file_edit` 允许非 UTMT 文件编辑并入当前批次。
- **`--preview`**：显示拟提交文件与哈希；INI/file0 附行级差异。原 replace-code 的 `--dry-run` 保留。
- **行为规范化**：file0 写入统一标准 CRLF（原实现 newline 转换产生 `\r\r\n`）；`_read_ini` 重复键改只读（取最后一个值，不再自动清理改写）；`backup_file` 先写时间戳归档再更新 latest，`required=True` 失败即取消写入；`find_game_data_file` 改 `is_file()` 判定。

### ZCode 独立核验（2026-11-11 深夜）

- 246/246 单测通过；gen_docs --check / shim 导入 / 版本链一致。
- 真机（tmp 副本 + 真实 UTMT）：`--preview` 零写盘；工作区创建 + manifest + 编辑历史；旧 `.sandbox` 兼容优先；基线漂移拒绝；**cjk-font 五步管线产出的工作区 md5 与 v2.3.3 时代 A3 快照逐字节一致**（行为等价的最强证据）。
- 仓库 game.ios / Steam 副本 / 真实 file0 的 md5 全程未变。

### 输出形态与行为面变化（复核席补记，2026-11-11 交叉审核 A/B）

- 写入回执的"应用:/退路:"两行提示移除（回执主体目标+MD5+范围保留）；`--no-steam-sync` 场景范围标签简化为"真实文件"。
- 备份归档命名 `.bak.{ts}` → `.bak.{ts}_{纳秒}`（防同秒碰撞）；`undo --backup`/list-backups 兼容实测。
- `ini set Love/Kills/Room` 的 file0 回执并入单行（成组提交）；reset-flags 的 file0 同步失败由告警改为硬失败。
- INI 序列化经 StringIO 恒为 LF（Windows 上重写 ini 将从 CRLF 变 LF——归入 Windows 待验证项）；verify-code 在批次内验证的是待提交暂存字节（与最终提交内容自洽）。

### 已知限制（待验证清单）

- file0 新行尾（`\r\n`）未经游戏内读档验证——下一个实机窗口的首要核对项。
- 真实 Steam 写入、进程强杀后的多文件恢复、Windows 文件锁：未验证。
- `--workspace` 与旧 `.sandbox` 共存时旧副本优先（设计取舍；`--workspace default` 可显式走新工作区）。

## v2.3.1 — 2026-11-11（O2 拆包：scripts/modify_save.py → deterline/ 包）

**性质：纯结构重构，行为零变化。** 命令面、参数面、输出文案、退出码、golden CSX 全部不变。

### 拆包（研讨会2/01 十步方案全落地）

- `scripts/modify_save.py`（7779 行单文件）→ **纯兼容 shim（116 行）**：包引导自举 + 全兼容面 re-export + `main` 入口。实现全部迁入 `scripts/deterline/`：
  - 叶子层：`errors.py`（异常）/ `config.py`（常量表）/ `state.py`（7 个运行旗标单点，`state.X` 模块属性读写）/ `paths.py`（路径定位与备份）
  - 脊柱层：`utmt.py`（_run_utmt / 沙箱重定向 / V2 写入策略 / CSX 转义 / 解析 / md5）/ `rooms_data.py` / `inifile.py` / `file0.py`
  - 命令域 `cmds/` 九件：save_cmds / dialogue / code / room / npc / door / sprite / verify / cjk（1:1 平移，**不合并 door/pit/battle 三胞胎**——留给 O3b）
  - `cli.py`：main() 1:1 平移 + `ACTION_CHOICES` 模块级上提（gen_docs import-first 契约）
- 兼容面（A8）：`modify_save` 的 76 个 `ms.*` 名字全部保留（活提取集合 diff 测试锁死）；shim 纯净性 AST 守卫（只许 import/re-export）。

### 护航与验收（A1-A8）

- **A1** 217/217 测试绿（拆包期新增 29：包纪律 AST 警戒线 ×6、UTMT 脊柱函数级 ×16、双前缀/room-list/活绑定等 ×7）；golden 零重录（全程未碰 GOLDEN_UPDATE）。
- **A2** `--help`（裸跑 / `-I` / `-P`，COLUMNS=80）与 golden 逐字节一致——106 处 dispatch 裸名 AST 引导前缀化后仍逐字节不变。
- **A3** 代表命令集 9 项 × 拆包前后双轮（真实 UTMT、独立沙箱）：**8 项字节级 md5 一致**（含 cjk-font 五步管线全链）；sprite_replace 仅 PNG tIME/date:create 元数据 31 字节差异（ImageMagick 重编码时间戳，结构签名 0 差异、像素一致）；create_door 预期失败 parity（原始文件无 door 资产）。**A3 实测捕获 1 处真缺陷**（cjk tools 路径 parents[2] 误写，应为 parents[3]）并当场修复——验收设计兑现。
- **A4** 退出码矩阵不变（成功 0 / 错误 1 / 搜索零匹配 3，测试覆盖）。
- **A5** run.py 子进程转发、install.py symlink、SKILL.md 命令面零变化；唯一文档结构改动 = SKILL.md/README 文件结构图（本文记录）。
- **A6** gen_docs 幂等（二次运行 diff 空）+ choices↔commands.json 双向一致（84 命令）。
- **A7** game.ios 基线 md5 `fc049850…` 全程完好（真实 Steam 副本只读校验多次）。
- **A8** 见上；测试不再经 `ms.*` 引用 4 个旗标（patch 点随域迁 `deterline.state`）。

### 拆包期引入的机制

- `tests/_o2_patch.py` `dual_patch_utmt`：单一 mock 同时挂 `ms._run_utmt` 与 `deterline.utmt._run_utmt`（过渡期双调用路径；from-import 绑定 bug 将令 golden 捕获为空 = 响亮哨兵）。
- AST 警戒线（tests/test_o2_step1.py）：旗标只经 `state.X`；包内相对导入只导模块；shim re-export 活绑定；ROOMS 只经 `rooms_data.ROOMS`（stale-dict 防线，含 asname/星号绕过封堵）；过限定双前缀扫描；shim 纯净性。
- 过渡期从-import 陷阱实测：步 5 曾因过期 mock 静默跑真 `cmd_code_replace`（V2 自动沙箱泄漏，套件 0.4s→13.7s）——重指 patch 点后消除。

### 复核记录

- 步 1-6 每步独立复核席审查（5 轮），全部清偿后合入：步 1 P1 sys.path 自举（-I/-P/-m 形态保持）+ 旗标测试硬化；步 2 ROOMS 前瞻防线；步 3 双挂点必要性负控 + 20024 语料 `_csx_escape` 等义证明 + Steam 写路径安全证明；步 4 未用导入；步 6 **P0 双重前缀**（room-list 运行时必崩，零覆盖漏洞）+ 过限定警戒线 + room-list 冒烟。
- 步 7-10 综合复核（进行中/另轮）。

### 已知过渡期事项

- `_md5_file` 等 ms re-export 为导入时绑定（无 patch 消费者，方案接受；步 10 后 ms 侧无实现）。
- `saved_to_temp` 死赋值（1:1 保留，父文件同）；`cmd_file0_get/set` 的 `known` 死赋值（1:1 保留，拆包后单独清理）。

## v2.3.2 — 2026-11-11（cjk-check 字形覆盖预检 + 冷路径覆盖棘轮）

### 新命令：`cjk-check`（C3a-L1 收口，价值席裁决落地）

- 逐字对照 glyphs.json 判定文本字形覆盖；缺失清单带 U+ 码点与行动建议（GB2312 二级 → `--full` 重建；表外 → 换字符）。
- 退出码：全覆盖 0 / 缺失 1 / 无字形表 2（指引先跑 cjk-font 或 `--glyphs` 指定）。
- 诚实边界：static 级保证——覆盖≠渲染（B4 仅 N=1 实证、canary UV 钳位未判定）。
- 默认字形表 `build/font_cjk/glyphs.json`（4064 码点，full:false）；`--glyphs` 可指定。

### 防线：dispatch 覆盖棘轮（风险席裁决落地）

- `tests/test_dispatch_coverage.py`：commands.json ↔ ACTION_CHOICES ↔ dispatch 分支三方一致 + 零覆盖必须 ⊆ 带理由 ALLOWLIST（当前空，84→85 命令全冒烟覆盖）——room-list P0 一类的接线 bug 从此在 import 时爆红。
- 十条原零覆盖 save 域命令补冒烟（含 experiment 快照/列表/恢复全链 roundtrip）。

### 真 bug 修复（冒烟捕获）

- `cmd_reset_all`：undertale.ini 缺失时 `changes_ini` 未定义即引用（UnboundLocalError）——`changes_ini = []` 提至 try 前。

### 事故记录（如实披露）

- experiment 冒烟初版以 `DETERLINE_GAME_FILE` env 隔离，但 `find_game_data_file` 优先级 1（Steam 路径，本机存在）胜过优先级 3 env → 冒烟实际打真实 Steam 目录，**覆盖了两枚 Nov-8 旧同名快照**（`game.ios.snap.dbg` / `game.ios.snap.a3smoke`，内容替换为当前 game 内容，原状态不可恢复）；真实 `game.ios` 本体内容零变化（自拷贝，md5 `fc049850` 全程）。已改 patch `paths.find_game_data_file` 隔离并加"套件前后 Steam 目录 mtime 扫描 = NONE"证明。
- 4 处死赋值清除（`saved_to_temp` ×2、`known` ×2，均为写而不读）。

## v2.3.3 — 2026-11-11（doctor 聚合体检）

### 新命令：`doctor`（风险席路线图 B1 项，O2 后收编条件兑现）

- 全只读零写盘零 UTMT 子进程：rooms.json 健康 / 存档可解析 / 游戏文件 md5 与仓库基线比对 / 备份占盘盘点 / 沙箱残留提醒 / UTMT CLI + dotnet 可达 / CJK 字形表状态。
- 退出码：全 ✓ 0 / 有 ✗ 1；`--dir` 定位失败降级为 ✗ 行不崩溃。
- rooms.json 路径复用 rooms_data 单点（不新增模块路径位点）；仓库根经 `_ROOT` 单点。
- 首次实机体检（真实用户数据，只读）：正确检出真实沙箱残留与 13 个 .bak 占盘 315MB。

### 其余

- `--text`/`--value` 互斥校验（cjk-check）；覆盖棘轮 ALLOWLIST 24 条带理由（2 条内联型）；死导入清除。
- 236/236 测试绿；fresh-archive 自包含复验通过。

## v2.4.1 — 2026-11-12（阶段 0/1：中文样例复现链 + W3/O7 加固 + O5 索引）

**性质：按外层 AUDIT_2026-11-07/02-下一步推进建议.md 与 03 手册的阶段 0/1 交付。样例状态：sandbox（实机验收待窗口，预案见 05 记录 §5）。**

### 阶段 0（接手基线）

- Codex 架构重构独立核验后检查点入库（v2.4.0，0eb0ef5）。
- `tests/fixtures_save.py` / `fixtures_utmt.py`：共享夹具（标准库存档夹具、UTMT 集成夹具 + tmp 副本）。
- 外层交付文档：04-接手基线与环境清单.md（0.2 复跑 / 0.3 清单 / 0.4 验证状态矩阵）。

### 阶段 1.1/1.2：W3 冒烟三段裁决（68f9a8c）

- `SmokeVerdict(started/triggered/restored)`：三段分别判定，PASS=三者皆 ok；启动失败/按键不可用/非 Steam 目标 → **UNVERIFIED(2)**（与真 FAIL(1) 区分）；报告含 SMOKE_RESULT 机器行。
- 唯一标记（文件名含 run_id）+ 内容双钥（run/room/inst 字段级精确比对）；多候选探测删除（无内容校验的假 PASS 洞）。
- 编辑目标 ≠ Steam 启动器加载路径 → 拒绝启动（DETERLINE_SMOKE_ALLOW_NONSTEAM=1 豁免）；pkill 后轮询进程真正消失再恢复（SIGTERM 回写竞态）。
- 12 条离线负例（mock 启动器 + 假钟，毫秒级）。

### 阶段 1.3/1.4：O7 资源级差异（0e10ace + 2aac783）

- diff-snapshots 单次遍历同载摘要+明细：STR 内容哈希（LCS 锚定防 16k 位移误报）/ 实例 add-remove-move / CODEF 反汇编指纹（等指令数改代码必检出）/ FONT 字形+纹理页。
- `--detail` / `--expected`（范围声明，范围外差异退出码 1）/ `--utmt-timeout` 300s。
- 显式 A/B 输入 read-through 直读（工作区选择不得替换任一输入；消除 ensure_workspace 250MB 只读副作用）。
- **1.5 实测发现的语义缺口**（结构投影不受 --expected 管辖 → 层1 恒 exit 1）已修复（ab2174d，议会 A 裁决最小切片：声明条目指令数投影 + 声明房间实例计数投影豁免；size/tiles/bg 与未声明条目仍计违规；双向钉测试）。样例层1 场景复验退出码 0。

### 阶段 1.5：中文样例双副本字节级复现（9936c66 + 1.5a）

- **cjk-trigger 两页扩展**：text 至多一个中部 `/%%` 页分隔 → msg[0]=页1/%%、msg[1]=页2/%%、msg[2]="%%%"（B4 消息表两页推广）；三页拒绝；逐页校验/折行；单页 golden 字节不变。
- 样例：room_ruins1 / obj_cactus @220,330 / typer31 / sans 头像 / 两页中英混排。
- 双副本两轮构建：工作区 sha256 **字节级一致**（4903050a…）；cjk-font 中间产物 md5 与 v2.3.3 时代 A3 快照同值（跨架构等价性）。
- 层1（基线 vs 构建，声明范围）：资源级 0 违规；结构层 4 处差异 = 声明操作的结构投影（缺口已修）。
- 撤销核验：覆盖回基线后 md5 复原。复现步骤全录于外层 05-中文样例复现记录.md。

### 新命令：`backup-index`（阶段 2.3 O5 最小切片，92a2393）

- 恢复资产只读索引：bak-latest/bak-archive/named-snapshot/workspace-copy/workspace-legacy 五类 → 路径/恢复目标/mtime/大小（--hash 追加 SHA-256）。
- 恢复提示与 undo/experiment-restore 的 key/tag 语义精确对齐（首轮 33/59 提示不可用被审核席 B 实测抓出后全部修正）。
- manifest 损坏容错；定位失败降级；零写盘零 UTMT。

### 真 bug 修复（各轮交叉审核捕获）

- cmd_smoke_test finally 引用已删除变量（每次真实运行 NameError——编排层零覆盖下静默）。
- find_game_data_file 的 data.win 回退链在无 Steam 安装时 AttributeError。
- cmd_reset_all ini 缺失 UnboundLocalError；doctor rooms.json 检查恒 ✗（`import json as _json` 函数内遮蔽）。
- diff-snapshots 范围外差异退出码 0（契约未接线）。
- 4 处死赋值/死导入清除。

### 已知限制（移交后续）

- file0 新行尾（CRLF）未经游戏内读档验证（实机窗口首要核对项）。
- 结构层投影豁免的 CODE 移除不对称（保守方向仅假红）；单块 >2 页未支持。
- 真实 Steam 写入、进程强杀恢复、Windows 锁：未验证（03 手册 2.2/2.5）。
