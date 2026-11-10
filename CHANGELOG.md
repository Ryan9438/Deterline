# Changelog

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
