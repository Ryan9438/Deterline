# Changelog

## v2.5.4 — 2026-11-14（阶段 3.2 首切片：ROOMS_GUIDE 草稿生成器 + 映射体检）

**性质：03 手册 §7 条 3.2 首切片。375→382 测试（+7）。正式 ROOMS_GUIDE.md 零触碰（重生成须审批——议会裁决）。**

- `tools/gen_rooms_guide.py`：消费 rooms-scan JSON（3.1 分类 SSOT）→ 生成 **`ROOMS_GUIDE.draft.md`**（按 D 候选/B1/B2/A/未归类分节，逐房 idx/中文名/尺寸/实例/Tile/背景/对象/分类理由）。
- **映射体检（03 §3.2）**：rooms.json（id→中文名）与 rooms_reverse.json 双射校验（长度/指向/值集三向）；扫描覆盖统计（登记/未登记 + 未登记名单）。
- rooms-scan 协议扩展：RS 行新增 `idx=<列表序号>`（Room 传送语义的数字 id；映射按 idx 走 rooms.json——扫描名是内部名，rooms.json 值集是中文名，靠 idx 桥接）。
- 稳定性：同一 scan 输入重跑输出逐字节一致（03 §3.2"输出稳定"验收，测试钉住）。
- **真实基线端到端**：336 房 / 映射体检通过（双射 244）/ 登记 244 / 未登记 92（TESTROOM/bullettest 等开发房如实列出）/ 草稿重跑逐字节一致。
- gated 基线测试随 idx 协议更新并复验通过。

## v2.5.3 — 2026-11-13（审核清偿：B2 优先级修正 + CI 红补记 + 协议加固）

**性质：批次 7-9 双席交叉审核清偿。375 测试（+2）。**

### 分类语义修正（审核席 A/B P2）

- **B2 优先级修正**：`_classify_room` 改为**含 obj_backgrounder_* → B2（即使同时有启用层）**——RESCAN_PLAN §三明文（对象 Create_0 覆盖房间数据层）；此前启用层优先与计划相逆。真实基线复测：lastruins_corridor → B2（旧标 A 的分歧随修正消解）、3 个 backgrounder 共存房归 B2、D-candidate 8→5。
- 分类理由携带共存信息（"另有 obj_backgrounder_* 共存——set-room-bg 无效"）；D 阈值启发式自标"无文献背书"（RESCAN_PLAN 对 D 的既有定义是"沿用旧清单"）。

### 诚实记录修正（审核席 B P1/P2）

- **v2.5.1 更正**：本批 CI 红实为 **4 次**（405570e/7b6c756 NameError ×2 + 2df6647/b26f038 cjk 链 ×2），原文记 2 次漏计前两起——同为"编辑后未全量复跑"教训的最强佐证。
- **v2.5.2 后记**：1ec101f 推送 run 43455131996 windows-latest 红（SIGKILL 测试 20s 计时窗口 flake；ubuntu/macos/本地绿，无代码交集）——测试窗口放宽至 60s 修复。

### 协议/工具加固（审核席 B P3）

- rooms-scan 行协议列表分隔符改 `\u001f` 控制字符（资源名内逗号会碰撞出假 D-candidate）；畸形字段缺 `=` 显式 RuntimeError。
- `obj_backgrounder_` 前缀统一带下划线（与 room-bg-info/RESCAN_PLAN 一致）。
- `tools/scan_rooms.py`：--out 可写性预检（先检后扫，不再浪费一次全量 UTMT）；`rooms_scan.json` 入 .gitignore。

### 文档口径修正

- 09 头部刷新（373/v2.5.3/CI 状态如实）；`uncategorized` 描述改"零背景观测"（53 房均有实例观测）；测试 docstring "三条"夸述改为如实口径。

## v2.5.2 — 2026-11-13（阶段 3.1 首切片：rooms-scan 统一扫描）

**性质：03 手册 §7 条 3.1 首切片——库函数 + 工具 + 分类规则；ROOMS_GUIDE 重生成归 3.2（议会裁决：须审批）。373 测试（+12）。**

- room.py 库层：`_SCAN_ROOMS_CSX`（单次只读遍历：尺寸/实例/Tile/启用背景/对象名集合，Uri 转义行协议）+ `_parse_rooms_scan`（解析层保序去重契约加固）+ `_classify_room`（A/B1/B2/D-candidate 规则 + 分类理由随行）+ `scan_rooms_data`（schema deterline.rooms-scan/v1：源 md5/sha256/时间戳/逐房观测+分类）。
- `tools/scan_rooms.py`：CLI 包装（--game/--out/--timeout；分类统计摘要）。
- **基线核对（RESCAN_PLAN §七，真实 UTMT 实测 2.1s）**：336 房 ✓、source md5 = 基线 ✓、tundra_town=B2 ✓；**分歧如实登记**：room_water_undynefinal / room_lastruins_corridor 按启发式（≥2 启用背景层）入 **D-candidate 人工复核**（旧标 B1/A 不强行复贴）——03 §3.1"人工例外带依据"工作面；uncategorized=53（intro/menu 等零观测房）。
- gated 集成用例（DETERLINE_RUN_UTMT_INTEGRATION=1）钉住上述基线口径。

## v2.5.1 — 2026-11-13（凌晨批次：A8 强化 + dispatch 收编 + cjk-trigger 前置校验 + O3b 前置钉）

**性质：议会三席裁决的凌晨自主批次（文档收口/执行入口另行记录于 06 §4 设计稿，未实现）。344→361 测试。**

### A8 强化（风险席首位）

- **shim 全量导出面冻结**：FROZEN_EXPORTS 215 名逐名锁定（此前 91 名仅为测试引用子集，约 121 名裸奔）；有意变更须改清单并归因。覆盖扫描相应剪裁名册块（FROZEN 不是覆盖——曾使 21 条 ALLOWLIST 被误判陈余）。

### dispatch 收编 + `--dir` 双形态

- `cmd_md5` / `cmd_sandbox_restore` 抽入 cmds/save_cmds.py（01-ROADMAP 既定归属）；handler 委托；**ALLOWLIST 23→20**（两条内联豁免清偿）。
- md5 / sandbox-restore 的 `--dir` 支持"文件或含 game.ios/data.win 的目录"（与 backup-index/recovery-scan 同语义；显式无效不回退 Steam）。

### cjk-trigger 前置字形覆盖校验（风险席切片 A）

- 文本含非 ASCII 且字形表在位时，**表外字符在任何 UTMT 调用/写盘前 ValidationError**（收口"覆盖≠放行"缺口：此前可生成必然渲染空白的触发块）。
- 字形表缺失 → 降级告警照常生成（与 cjk-check 退出码 2 语义分离）；**畸形字形表 fail-closed 并点名文件**（此前 chr(c) ValueError/TypeError 裸栈）。
- ALLOWLIST "verify-code" 移出（preflight 测试引用 cmd_verify_code）。`--glyphs` 现为 cjk-check/cjk-trigger 共用。

### O3b 前置钉 + 域F 回归样本（阶段 3.4）

- door/pit/battle **fresh-base golden ×3**（无既有 Create_0 → BASE 起步路径此前零钉——合并前盲区清障）。
- 外层 `10-域F形态回归样本.md`：11+2 形态准入表；**准入集 = {扁平触发块 + Alarm_0 守卫}**，实测指纹 Step_1 `instr=68 branches=6` roundtrip stable / ASM sha256 `15ea1cb5…`（tmp 副本注入 + V1 采集，方法可复跑）。

### 双席审核清偿（2 轮）

- **golden 写回机制损坏**（P1）：GOLDEN_UPDATE 曾把 CSX 内 `"\r\n"` 转义序列全局替换成 `/r/n`——canonical 归一收窄到占位符路径；3 枚 fresh-base golden 重录、5 枚工作区污染回退；归一化转义序列保护有测试钉。
- cjk-trigger `--glyphs` CLI 传 str 未 Path 化（AttributeError 裸栈，单测全走函数级故未暴露）→ handler Path 化 + 回归钉。
- cjk-check 缺表报错打印实际尝试路径（回归）；测试夹具泄漏钉（backup-index 无存档目录用例现 patch resolve_game_data_file）。

### 诚实记录

- 本批 9 个提交中 2 次推送 CI 红（test_cjk_wrap 脚本链损伤期 NameError；根因与修复见 07 §3.0 同族——**教训：凌晨脚本链编辑后必须全量复跑再推**）。
- 前向记录：door/pit/battle 对"反编译失败"与"条目不存在"同为 fresh-base 分支（O3b 合并时须区分 ERROR 语义，见 10 §4）。

## v2.5.0-rc1 — 2026-11-13（阶段 2 出口：恢复/平台/发布流程补齐）

**性质：03 手册阶段 2 全部交付（2.1–2.6）的候选版；新增 `backup-prune`（v2.4.4）与 `tools/release_check.py`；CI 三平台矩阵；发布记录见外层 AUDIT_2026-11-07/08-候选版发布记录.md。**

### 阶段 2.5 平台矩阵（本版）

- CI 从单 ubuntu 扩为 **ubuntu/windows/macos 三 OS 矩阵**（fail-fast: false）：344 单测 + gen_docs --check + --help golden + `install.py --check` 安装入口（只读）+ diff 卫生。**Windows 侧 msvcrt 锁分支与路径语义首次真实执行**（03 §2.5 挂账项转 ci-static ✓）。
- 外层新增 `07-平台矩阵与验证级别.md`：能力 × 平台 × 验证级别全表；明确挂账（Windows UTMT 集成/Windows smoke/TerminateProcess 实验/行尾游戏读回）。

### 阶段 2.6 候选版（本版）

- `tools/release_check.py`：工作树提交态 / 版本链单点 / gen_docs / help golden / 命令注册表↔commands.json / 分发关键文件 / install --check 入口 / 全量单测——候选版门槛命令化。
- 外层 `08-候选版发布记录.md`：Git 标识、验证范围、已知限制、工作区迁移说明、CLI 兼容说明、回退方法。
- tag `v2.5.0-rc1` → **rc2**（三平台 CI 首夜实证修掉 Windows 平台差异：fsync 只读句柄 Errno 9 / cp1252 打印与解码 / golden 反斜杠 / 夹具泄漏钉——详见 07 §3.0；run 43336290168 三平台全绿）。

### 阶段出口核对（03 §6）

常用写入与恢复有可重放证据（journal + recovery-scan + SIGKILL 216 实验 0 违例）✓；自动检查不依赖真实存档 ✓；候选版对每个平台和功能列出实际验证级别（07 矩阵）✓；真实 Steam 或 Windows 验证单独挂账 ✓。

## v2.4.4 — 2026-11-13（阶段 2.4：保留策略预览 backup-prune）

**性质：03 手册 §6 阶段 2.4 最小切片；新增 `backup-prune` 命令（89 命令）；只读零删除。**

- `backup-prune`（只读零删除）：占盘统计 / sha256 内容重复分组 / 超窗归档清理建议（精确 rm 命令 + 可回收字节 + undo 失效提示）；`--keep-archives N`（默认 3，<1 拒绝）；`--json`（deterline.backup-prune/v1）；退出码 0/2。
- 保留条件：bak-latest / 命名快照 / 工作区副本与 legacy / journal 引用文件（活动恢复记录，v2.4.3 journal 保护）/ 每目标最近 N 份归档（system_information_962/963 归档同受窗口管理）。
- 损坏 journal → 显式警告（保护可能不完整；执行清理的前置条件 = recovery-scan 无 corrupt）。
- 重构：backup-index 抽出共用扫描层 `_collect_backup_entries`（prune/index 同源；审核席 A 逐字节 diff 等价）+ transactions `journal_roots_for` / `journal_referenced_files` 公共助手（recovery 同源）。
- 双席交叉审核清偿：`--dir "None"` 提示回归（save_dir=None 时省略 dir 键 + 防御性判值）、`--keep-archives 0` 静默吞参数、kept_shas 死代码与 bak-latest 白哈希、重复组可回收口径（只计删除集）、exit-2 JSON 键统一、rm 行 shell 特殊字符防护、夹具死分支、sanity 断言改 assertLess。
- 真实数据预演（B 席只读）：59 项 / 1194 MB，唯一建议项与保留项及在用 game.ios 三者 md5 相同（删除零信息损失）；0.21s 完成；零写入。
- 344/344 测试绿（+8）；zero-deletion 断言钉死（预览后目录快照逐字节一致）。

## v2.4.3 — 2026-11-13（阶段 2.2：恢复完整性——可恢复运行记录 + recovery-scan）

**性质：03 手册 §6 阶段 2.2 交付；新增 `recovery-scan` 命令（88 命令）；无破坏性接口变化。**

### 2.2a 故障矩阵（7f64ac7）

- 五类故障全部有可复现测试：备份失败 / 后续替换失败（含回滚不完整保留恢复副本）/ 基线漂移 ×3 / 双进程竞争（真并发恰一胜者 + flock 移除变异敏感化）/ 工作区产物与清单不匹配（副本 sha ≠ 清单末条 → 拒绝应用，interlock 入 check_baseline）。
- 畸形 manifest 容错：history 为 dict/int/None、副本丢失、空 sha 一律不逃逸（跳过或明确报错）。

### 2.2b 可恢复运行记录（journal）

- 每次多文件提交前在首个目标旁 `.deterline/journal/<id>.json` 落盘（mkstemp+fsync+os.replace 原子写）：预期目标 / before-after sha256 / staged 与回滚副本路径 / 状态机 pending→committing→(删除 | aborted-clean | aborted-partial)。
- 成功后整目录摘除；失败路径 aborted-* 保留（含 error 聚合）；**SIGKILL 保留——216 次随机 kill + 3 个确定性窗口实验 0 违例**（目标内容恒 ∈ {before, after}，journal 全部可解析）。
- 提交前检测同名目标未完结运行记录 → 拒绝并指引 recovery-scan（03"再次运行能识别"）。
- 已知局限：跨目录混合提交崩溃后，只动另一目录的新提交看不到该记录（06 §4 登记；scan 三处兜底）。

### 2.2c recovery-scan（新命令）

- 只读扫描未完结记录 + 孤儿暂存 → 中断窗口分类（未开始 / 已全部写入 / 替换中断 / 存在外部修改 / aborted / 损坏 / 未知 state）+ 可预览恢复指引（interrupted 与 aborted-partial 档逐目标给出回滚或完成的 cp 命令）。
- `--json`（deterline.recovery-scan/v1）；退出码 0/1/2（2=双侧定位失败，对齐 backup-index）；工作区层 journal（sandbox 默认写路径）一并扫描；孤儿判定 resolve 归一（/tmp vs /private/tmp 不误报恢复副本）。
- 零写盘零 UTMT 零恢复执行——recovery-apply/clean（执行恢复/清理）留待下批。

### 测试与文档

- 336/336 绿（+28）；双席交叉审核 2 轮全清偿（orphan symlink 误报、工作区层 scan 盲区、pending 先落盘不变量测试、content sha 缓存等）。
- 06-写入路径盘点 §1 补 journal 写入位点 #15、§4 风险表更新；help golden 重录（--json/--dir 文案）。

## v2.4.2 — 2026-11-12（并发审核修复：smoke 安全面 + backup-index 可用性 + 文档诚实性）

**性质：对 v2.4.1/024e698 的独立交叉审核（4 席并发）修复批次；无新功能面。**

### smoke-test（审核席 A）

- CLI 默认坐标修复：handler 改用 `--x/--y` 的原始 None 判定，`room_torielroom` 默认 160/150 不再被全局 320/240 覆盖（文档默认调用不再必然超时 FAIL）。
- 演练隔离：非 Steam 目标（未启动）时，file0/ini 复制到临时目录后全部改写落临时目录，真实存档零接触；真实启动仍需真实存档目录。
- 恢复闭环：pkill 后 8s 未退升级 SIGKILL 再等 2s；进程仍存活则 `restored=fail`（保留快照），不再报告 restored=ok。
- 标记三字段真正生效：`_launch_and_poll` 传入 `room_name`，room 不符必判负。
- 清理面按 `game_file.name` 构造（data.win/改名副本不再泄漏归档）；稳定名 `.bak` 运行前内容保存/结束后还原。
- 未启动的演练不再无条件 pkill 用户的 Mac_Runner。
- **external 模式超时归 UNVERIFIED(2)**：未发键时无法区分“人未操作”与“触发未执行”（02 手册“前台输入不可用 → 未能验证”）；需要确定性 FAIL 判据时用 `--keys osascript`。

### backup-index（审核席 C）

- `--json` 接线：handler 传 `json_out`；JSON 模式不再混入文本行，stdout 纯 JSON；新增 CLI 级纯度测试。
- 工作区行提示改 `sandbox-restore --workspace <ws>`（024e698 回退修复）；legacy 行不带参数；所有提示附 `--dir` 作用域。
- legacy `.sandbox` 无 manifest 也可恢复（`sandbox-restore` 仅在工作区有 manifest 时做来源漂移校验）。
- `--dir` 指向目录时自动探测其中 `game.ios/data.win`，双侧可同时索引。
- 命名快照扫描固定 `game.ios.snap.*`（Windows 一致）；save 侧孤儿快照标 `orphan-snapshot`，不再给死命令。
- system-info 改为索引 962/963 的 `.bak/.bak.<ts>`（此前只列活文件，无可执行恢复入口）。
- `.bak` glob 精确到 `game_file.name.bak*`，过滤目录与空 tag；两侧定位均失败退出码 2；JSON 行键齐全（缺失值为 null）。
- **显式 `--dir` 无效时不再回退默认 Steam 定位**（否则会把真实安装当成索引对象）；目录输入自动探测 `game.ios/data.win`。
- experiment-* 的游戏侧支持 `DETERLINE_GAME_FILE` 显式隔离（优先于 Steam 默认）。

### diff-snapshots（审核席 B）

- **`--detail` 无 `--expected` 时资源级差异计入退出码**（P1-1）：等指令数改代码/原地改台词不再假绿；成功行改为分述“结构 0 差异 / 资源级 0 差异”。
- 空声明（`[]`/`{}`）不再整类豁免 COUNT（P2-1）；仅声明 `move` 不得豁免房间实例计数变化（P2-2）；实例按多重集比较，精确重复项不再被 set 折叠。
- 行协议转义：CSX 名称字段经 `Uri.EscapeDataString` 编码，含 `|`/换行/非 ASCII 的代码名不再破坏解析（P2-4）。
- `--expected` 形状校验（顶层对象/键白名单/instances 操作枚举），错形状干净报错（P3-1）。
- 显式 A/B 输入不再要求默认游戏文件存在（P2-3，CLI 定位失败仅对 diff-snapshots 放行）。

### 测试与文档

- `tests/test_dispatch_coverage.py` 的 `__main__` 守卫移到文件末尾（直跑 12 → 30 测试）。
- FLAGS 警戒线纳入 `WORKSPACE/PREVIEW`（不进 shim，避免 stale 快照）。
- 05 记录补齐 `layer1_expected.json`/`empty.json` 内容与路径变量；§5 实机命令改为可执行路径（删除无效的 `--workspace --commit` 组合，明确跨源工作区会被拒绝）；06 标注 as-of 快照并补 `sandbox.ensure_workspace` 直写位点。
- 308/308 测试绿（+17）；真实 UTMT dump 复验转义协议（336 rooms / 64017 strings / 13927 inst）；gen_docs/help golden 重新生成；导入卫生清理。

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
