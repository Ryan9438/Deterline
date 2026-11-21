# Changelog

## v2.6.0-rc4 — 2026-11-21（G 批次：前瞻清偿第二批 + 真机负路径标定）

**性质：rc3 前瞻/v2.5.11 前瞻六项清偿（G1/G2/G4/G5/G6）+ 真 CLI 负路径标定（G3）+ R2-CJK 实机材料脚本（G7）+ R17/R18 双席清偿（P1×1 + P2×1）。513→517 测试（+4：G1 金丝雀 / G2 复用拒绝改写 / G4 hardlink / R17 P2 符号链接守卫）。候选 tag 递补 v2.6.0-rc4。**

### G1（R15 P3-2）：解析器未知行形金丝雀

- `_parse_diff_categories`：结构段家族前缀（COUNT/VARDETERLINE/ROOM/CODE）+ **2 空格缩进**（verify.py 结构行统一形态）但未被任何已知正则消费的行 → `unclassified` 显式拒绝（"未识别结构行……闸门不猜"）——verify.py 行形漂移/未知差异类别不再静默跳过。4 空格缩进的资源级明细行（STR/CODEF/INST move）不属结构段，不触发。
- 测试：漂移行形（`ROOM 漂移新行形`）→ 拒绝。

### G2（R15 P3-4）：storyline-build 陈旧工作区复用拒绝（含 CLI 路由修正）

- 首版为"同名工作区任何产物即拒"——**真机脚本首跑即误拒**：CLI 全局 `--workspace` 置 `SANDBOX_ACTIVE`（沙箱对所有命令生效的既有设计），plan 探针的读取路由经 `_effective_game_file` **合法预置基线副本**（sha == 基线）。修正为精确判据：仅拒 **sha ≠ 当前基线** 的已补丁产物（链式叠加形态）；基线等价副本照常构建。
- **教训入库**：进程内测试未覆盖 CLI 全局旗标 × 沙箱读取路由的组合——G7 脚本实跑抓出（真 CLI 验收的价值再次自证）。
- 测试：已补丁复用拒绝 + 基线等价副本放行（双分支）。

### G3：真 CLI 负路径标定（脏基线 VARDETERLINE 契约实弹验证）

- /tmp 副本序列：CJK 补丁 commit（30d6673c… 脏基线）→ 第二支线 build → **REAL rc=1**，拒绝消息与设计完全一致：`VARDETERLINE 新增 0 条（声明恰 1 条 deterline_state）` + skip 式常数实弹匹配（CODEF added 0 / changed 2 无违规项——F2 skip 式真机标定顺带完成）。
- **测量纪律教训**：管道后 `echo rc=$?` 读的是 tail 退出码——首次判读误为"闸门放行"，重定向后重测才见真 rc=1。真 CLI 验收一律重定向 + 显式 `$?`（G7 脚本沿用 `set -euo pipefail` 无此问题）。
- 清理回基线 fc049850 + findings 0。

### G4（v2.5.11 前瞻）：hardlink 语义检测

- EditPlan commit 替换循环：目标 `st_nlink > 1` → stderr 警告（不拒绝——拒绝会误伤合法硬链接部署）："os.replace 断链语义：其他链接名将保留旧内容（备份为独立副本不受影响）"。
- 测试：os.link 夹具 → 警告出现 + 断链语义实证（别名保留旧内容）+ 无硬链接零警告回归。

### G5（v2.5.11 前瞻）：recovery_stress 副本证据无静默空洞

- kill 窗口命中 apply 消费段的副本（记录前已不在盘上）此前被静默略过——现显式标记 `<consumed-before-recording>`；记录新增 `journal_referenced_copies` 全集字段。
- 测试：子集运行后逐记录断言"每个 journal 引用副本 ∈ copy_hashes（哈希或消费标记）"+ 至少一条记录携带副本证据；**Windows 子集补 s2**（s1 pending 杀与 p1_prune 均不产副本证据记录——证据下限断言在 Windows CI 会确定性红灯，R18 P1 清偿）。

### 复审清偿（R17 PASS / R18 PASS；双席全项落地）

R17（引擎与安全席）：8 项全 PASS——结构行 16 种行形逐一喂入解析器实测零误触发（✗=U+2717/⚠️=U+26A0 不撞前缀）、G2 判据 None 短路/幂等/TOCTOU 封口全对、G4 警告位置贴 os.replace 且 stderr CLI 直通、G5 断言方向即安全性质、G6 skipTest 语义等价且 release_check 无 skip 计数断言、G7 脚本 rm .bak 防陈旧基线恢复必要、+3/516 算术闭合。**P2×1 已修（本节）**：产品路径符号链接旁路链（/tmp 合成数据实证——ensure_workspace 复用不校验 + _resolve_write_target().resolve() 写穿到链接目标原文件）→ 双守卫：G2 判据 `is_symlink()` 先拒 + `ensure_workspace` 复用分支补 `ensure_not_symlink`（A3 三道防线口径延伸到沙箱入口）+ 测试（尝试制 skip）。

R18（测试与证据诚实性席）：批次声明经独立验证全部属实（516 全绿实跑复现、G3/G7 盘上法证残留逐项对上——含 md5/sha256 双口径对账 30d6673c≡9102378f02e8 同一产物）。P1×1 已修（Windows 子集 s2，见 G5）；P3×5 记录（G1 金丝雀家族成员资格测试注记、G2 放行分支产物断言注记、08 G7 措辞注明脚本在外层 AUDIT 目录、G3 引文含 `: []` 尾巴口径、无 stdout 转录存档——盘上残留+声明互证已充分）。附带发现如实登记：`_check_structure` "基线已含 deterline* 变量"分支真机可达面比 fake 测试显示的窄（未变 VARDETERLINE 行被 verify.py 省略时走"新增 0 条"分支）——fail-closed 不受影响。

### G6（07 §3 条1）：Windows symlink 测试机会主义

- test_boundary_hardening 的 skip 判定从平台静态改为**尝试建链**——有特权/开发者模式的 Windows CI 实跑 symlink 拒绝防线，无权限环境 skipTest 留痕（诚实口径：能跑才跑）。

### G7：R2-CJK 实机窗口材料（C1-支线脚本第三支）

- `c1_branch_cjk.sh`：cjk: true 定义内嵌 → plan → build（字体栈+中文选择 NPC）→ apply 预览/commit → undo → scan——**端到端实跑验证**（9102378f02e8… → undo → fc049850 → findings 0）。实机窗口步骤注释内嵌（05 §5.2 口径：holdSeconds ≥ 0.15 逐格记录）。

### 前瞻登记

- F1 闸门 ROOM/CODE 结构分支的**真机正例**（非 fake）对照样例仍待下次真 CLI 验收链补记（G3 已补负例）；`--journal` 多记录选择器（条件未触发，12 §A3）；CJK 跨定义字形合并（D 批范围）。

## v2.6.0-rc3 — 2026-11-21（rc2 前瞻清偿：结构闸门 + Create_0 三式 + CLI 层测试 + CJK 组合）

**性质：rc2 前瞻登记四项全清偿（F1/F2/F3/F4）+ 新发现 preview×commit 漏洞修复。482→505 测试（+23）。候选 tag 递补 v2.6.0-rc3。真机 /tmp 全链标定两轮（ASCII 回归 + CJK 新增），确定性重建保持逐字节一致。**

### F1（rc2 前瞻）：O7 结构层差异入 storyline 声明闸门

- 闸门新增**结构段比对**：COUNT 增量（STRGCOUNT/CODECOUNT/SPRCOUNT/TEXCOUNT/LASTOBJ/VARS）、VARDETERLINE（A/B 双侧列表）、ROOM inst·移除·新增·变化、CODE 新增·移除·变化——资源级汇总行之外的结构漂移（房间尺寸被改、基线非干净、意外代码条目、NSID=0 变量）写前拒绝。
- plan 落 `expected_structure`（全类别严格相等比对）；build 回执记 declared/expected 双侧。
- VARDETERLINE 干净基线合同：A 侧必须无 deterline* 变量；B 侧恰新增一条 `deterline_state`，**NameStringID≠0**（NSID=0 崩溃根因）、Occurrences≥1。
- **真机标定发现**：LASTOBJ 在新建代码条目时 +1（CodeImportGroup/AutoCreateAssets 整体副作用，非逐条目）——首跑该常数缺失被闸门正确拒绝（声明 0 实测 1），修正后全链绿（闸门对未知增量的拒绝行为按设计生效）。

### F2（rc2 前瞻）：Create 事件三式期望分支

- build_plan 新增 Create 探针（`_find_create_code` + `decompile_classified` 三分类）——期望集按实际形态标定，**不再对 obj_npc_marker 形态隐性硬编码**：
  - `create`：无任何 Create 事件 → 新建（CODEF added +1）
  - `prepend`：有效 Create_0 存在但未引用 deterline_state → 前插初始化行（CODEF changed +1；**继承**条目带诊断点名父对象改动）
  - `skip`：已引用变量 → 零改动（干净基线不可达；结构闸门按 VARDETERLINE A 侧非空拒绝）
- 探针读失败拒绝标定（不作空/已初始化假设，B3 三分类口径）。
- plan 改用**实际房间名**（两段式子串回退时与定义名可异——新探针 `_room_name_by_idx`；构建亦以实际名为准，诊断如实注记）。
- 真机验证：obj_cactus（自有 Create_0 无变量）→ added 0 / changed 4（textdata+append+alarm+prepend），build rc=0 过闸门——**该形态此前会被旧常数误拒**（added 1≠2、changed 4≠3）。

### F3（rc2 前瞻）：storyline 三命令 CLI 层测试

- 8 常开测试（无 UTMT 依赖）：plan/build/apply 门禁 rc2、拒绝 rc1（R13 P1-1 退出码保真）、`--sandbox×--commit` 互斥、`--preview×--commit` 互斥（本批新增修复）、P0-1 `--workspace×--commit` CLI 可达性回归钉、`--json` 错误形状。
- 1 集成测试（`DETERLINE_RUN_UTMT_INTEGRATION=1` opt-in）：真 CLI 全链 build→预览→commit→幂等→undo——rc2 手工验证序列固化自动化。
- **形态注记（诚实口径）**：subprocess+sys.executable 测试形态被本机安全扫描误报高危并拦截写入（recovery_stress 同款限制），改进程内 `cli.main()` + SystemExit 捕获——门禁/接线/退出码语义全部复验；OS 进程边界由 rc2 手工真 CLI 验收链、C1 脚本与本批两轮真机标定留痕覆盖。

### 新发现修复：storyline-apply `--preview × --commit` 会真写目标

- F3 测试设计时发现：CLI 只挡 `--sandbox×--commit`，`--preview` 语义可被 `--commit` 覆盖（storyline-apply 不检查 state.PREVIEW 即提交）——R5 P2-3（prune-purge）同款漏洞在 storyline 的复现。修法：handler `parser.error`（rc 2）+ 函数级守卫双层。
- 回归钉：`test_apply_refuses_preview_and_commit` + CLI 层 `test_apply_preview_commit_exclusive_rc2`。

### F4（rc1/C1 前瞻）：CJK×choice 中文组合——合同扩展 + 构建链字体管线

- 合同：顶层 `cjk` 字段（布尔，默认 false）——true 时文本放行非 ASCII，构建链先注入 CJK 字体栈；默认仍全 ASCII。cjk 非布尔拒绝。
- 构建链：`_run_cjk_font_pipeline` = `font_cjk_build --only` **最小字符集**（定义三文本字段唯一字符——确定性字形集）+ `cmd_cjk_font` 五步管线（pass1/pass2 同批写入工作区，不触原文件）。
- **typer 参数**：`_build_npc_choice_block`/`cmd_npc_choice` 增加 `typer`（默认 5 = 原版，既有 golden 零重录）；CJK 组合传 **31**（CJK_TYPER_TABLE，B4 主臂实证）。⚠️ 选择框渲染语义待 **R2-CJK 实机收口**（sandbox 级证据，不升级声明）。
- 闸门：`expected_resources.font_changed`（ASCII 0 一票拒绝 / CJK 1——fnt_ja_maintext 字形表重指+共享表扩容）；expected_structure.code_changed += `scr_setfont`/`scr_preload_textures`（pass2 实际改动面）。
- **真机 /tmp 全链标定**：build 声明差异 STR 9 / INST add 1 / CODEF changed 3（textdata+两字体条目）added 2 / FONT changed 1——与预测常数**完全一致**；apply commit → undo 回基线 fc049850；同定义重建 sha 逐字节一致；recovery-scan findings 0。

### 兼容面与文档

- **505 测试**（口径：rc2 tag `068f7b5` 482 → HEAD；其中 +11 由 5222d06 自报"482→493"，+9 由 c827230，+3 由 3726121——**审阅区间内各提交自报数与总数一致，勿跨条目重复累加**；R16 P2 口径订正）。95 命令不变；FROZEN_EXPORTS 219 不变。
- 覆盖棘轮：**npc-choice 恢复豁免如实记账**（R16 P2：docstring 提及不是覆盖——清洗器扩展剥离注释/docstring 后，npc-choice/colorize-sprite/room-info/create-room 四条按真实状态登记豁免；此前三条靠注释提及假绿计入覆盖）。
- `__file__` 迁移检查表登记 storyline CJK 包根单点（doctor 同款行内标记约定）。
- commands.json storyline-plan 注记更新（cjk 字段），gen_docs 重生成。

### 复审清偿（R15 PASS / R16 PASS；双席全项落地）

R15（引擎与安全席）：8 项审查重点全 PASS——解析正则与 verify.py 全部行形枚举比对无漏看路径、_check_structure 双向严格、F2 三式自洽（skip 式闸门两路必拒）、preview×commit 双层无缝隙、**字体管线批内嵌套链核验（pass1 读基线等价副本 / pass2 链式接力无写丢失 / verify-code 读批内状态恰规避 C4 教训）**、ALLOW_CJK finally 全覆盖、typer 3 处替换点全参数化、版本链 8 载体完整。P2×1 → 已修（runpy 异常面 SystemExit/ImportError → StorylineError 带出缓冲诊断，440c18c）；P3×4 → 登记（literal_eval 已随 P2 顺手加守卫；未知行形金丝雀、rc2 CLI 层非 JSON、陈旧工作区链式叠加靠闸门兜底 → 前瞻）。

R16（测试与证据诚实性席）：核心验收全部实证复跑坐实（505 收集且全绿、干净检出 release_check 全绿、golden 零改动、fake↔verify 在闸门解析面逐行同构、CJK 常数与对象形态自洽、CLI 常开层零 UTMT、证据分级未夸大）。P2×3 → 本批全清偿：①F1 闸门 4 类未钉分支补测试（ROOM 移除/新增、CODE 移除、VARDETERLINE occ=0/畸形/名不匹配/多条新增 + 两段式回退诊断，+8 测试）；②CHANGELOG 计数口径订正（本条目）；③覆盖记账三选一取"清洗器剥离 + 恢复豁免"（见上）。P3×3 → 顺手清偿（fake 明细行逐行同构化——STR 9 条/CODEF changed 3 条/删矛盾 move 行/⚠️ 与尾行计数如实；集成幂等断言改"幂等 no-op"具区分力字样；CJK_DECLARED_DIFF no-op replace 残留清除）。

### 前瞻登记

- STORYLINE CJK 的**实机**验收（typer=31 选择框渲染、选项翻页）待 R0–R2 窗口——R2 矩阵增加 CJK×choice 行材料就绪；flag 写入仍禁用（R2 持久语义证据前不改）；`--only` 字形集按定义文本固定（跨定义字形合并/共享未做——多补丁共存属 D 批范围）。
- 解析器未知行形金丝雀（verify.py 未来新增差异行形时显式拒绝而非静默跳过——R15 P3-2）；陈旧同名工作区重建的 ensure_workspace 复用语义（当前靠闸门增量翻倍兜底——R15 P3-4）。
- F1 闸门 ROOM/CODE 结构分支的**真机**（非 fake）对照样例随下次真 CLI 验收链补记。

## v2.6.0-rc2 — 2026-11-21（R13/R14 复审清偿：C 线候选修订）

**性质：R13/R14 双席对 v2.6.0-rc1 的复审清偿（R13 FAIL：P0×1 + P1×5；R14 FAIL：P1×1 + P2×2）。481→482 测试（+2）。候选 tag 递补 v2.6.0-rc2。**

### P0-1（R13）：storyline-apply --commit 经 CLI 不可达——修通

- 根因：cli 全局门 `--workspace × --commit` 互斥 × handler 强制 `--workspace`，合取为空——**rc1 的"CLI 实跑全链"commit 腿实际经进程内调用完成，验收声明失实**（13 实录已订正）。修法：互斥门对 `storyline-apply` 豁免（其语义 = 应用已构建工作区，非 v2 直写；`--sandbox` 无名旗标仍互斥）。
- **诚实重验（全部真 CLI + 真 rc）**：build（候选 35d189a5，10 类声明差异全捕获）→ preview → **commit（CLI 腿，fc049850→5a6f9b66）** → 幂等 no-op → undo → fc049850 → scan findings:0。

### P1 清偿（R13 P1-1/P1-2/P1-3/P1-5 + R14 P1-1）

- **CLI 退出码保真**：三 handler `sys.exit(rc)`——此前拒绝恒 exit 0（脚本层会把拒绝当成功）。
- **首次 apply 的 defn 校验**：build.json.defn_sha ≠ 当前定义 → 拒绝（陈旧构建 + 新定义曾可上盘且回执 defn_sha 失真——同 ID 异内容出口在首次 apply 失效）。
- **alarm_guard 双计修正**：contract 的 code_changed 已含 Alarm 守卫，_expected_categories 不再叠加（曾放行一条未声明 CODEF changed）。
- **manifest 在场强制**：有名工作区 manifest 缺失 → 拒绝（来源校验载体缺失 = 校验链塌缩为未签名 JSON）。
- **声明差异解析器对齐真实 O7 形态**（R14 P1-1 = R13 P1-4 同源）：改吃**汇总行**（verify.py 资源级段全量计数，非 [:10] 截断明细）——10 类别全覆盖（STR total/INST add·remove·move/CODEF changed·added·removed/FONT×3）+ STR 明细 op 校验；全类别**严格相等**比对（期望 0 实测非 0 同拒）。实测：干净构建 10 类与模板常数完全一致；脏构建/未声明字体变更正确拒绝。

### P2 清偿（R13 P2-1/P2-2/P2-3/P2-4 + R14 P2-1/P2-2 同源）

- yaml_min：`a:\n- x` 同缩进序列曾 AttributeError 裸栈逃逸 → 显式拒绝。
- goto 数字越界拒绝（不在 rooms.json 序号内）；**房间歧义写前拒绝**（plan 期只读探针 `_room_match_count`——exact>1 或 exact=0 且子串>1 拒绝；**exact=1 恒唯一**——前缀子集名 room_ruins1 vs room_ruins10 合法，两段式语义确定性胜出）；对象子串首中记诊断（唯一性计数无证据，如实声明）。
- 工作区名白名单（`[a-z0-9][a-z0-9_-]{0,63}`，`../evil` 注入拒绝）；PATCH_ID_RE 改 fullmatch（`$` 换行绕过）。
- 覆盖棘轮：**mock.patch 字符串剥离**（提及不是覆盖——R14 P2-1）；npc-choice 恢复豁免如实记账（口径 95 = 75 已覆盖 + 20 豁免）。
- build.json 形状设防（非对象拒绝）；E2E 产物标记确定性派生（去 hash()）。

### 架构修正（R13 CLI 复跑发现）

- **回执按游戏文件隔离**：`.deterline/storyline/<file>/<patch_id>/`（原目录级共享曾让 /tmp 多个 *.ios 复用同一 build/receipt → 陈旧构建跨文件上盘）；build.json 增 `target` 字段 + apply 校验。
- build 入口 resolve 游戏文件（/tmp vs /private/tmp 两棵元数据树分叉）。

### 文档订正（诚实口径）

- CHANGELOG/13 实录："CLI 实跑全链" commit 腿声明订正（rc1 实为进程内；rc2 修复后真 CLI 重验）；"11/11 拒绝面"实为 10 例；CODEF changed 计数 1-2 → 1-3；storyline-plan 示例补 `--file data_win`；退出码 2 声明删除（无实现路径）。

### 前瞻登记

- O7 结构层差异（COUNT/VARDETERLINE/ROOM 结构行）未入闸门比对（v1 以资源级汇总行为准，结构漂移经 CODEF/INST 间接可见）；storyline 三命令 CLI 层测试（handler 已有 sys.exit，Mimosa 限制下 subprocess 断言另批）；"自有 Create_0 未引用变量 → prepend"形态的期望分支（当前仅 append/create 两式标定）。

## v2.6.0-rc1 — 2026-11-19（12 计划 C 批次 + A4：支线编排层 storyline-plan/build/apply + 新候选版）

**性质：12 号四个月计划 C 线交付 + 新候选版（A4）。95 命令（+3）、462→481 测试（+19）。C1 实录（两分支 sandbox 全绿）+ C4 CLI 实跑（build/preview/commit/幂等/undo 全链）为验收证据。**

### C2：storyline v1 合同（scripts/deterline/storyline/，新包）

- **yaml_min**（安全 YAML 子集解析器，stdlib-only）：块映射/标量序列/引号串/int/bool/null；**显式拒绝**锚点 &、别名 *、标签 !、多文档 ---、流式 {}[]、tab、重复键、序列内映射（11/11 拒绝面测试）；错误带行号。
- **合同**（deterline.storyline/v1）：严格封闭字段集（未知顶层/npc 字段拒绝）、schema 版本漂移拒绝、patch_id 正则、flag 独占区 500-999、prompt 须含 \C 且 ≤3 行、分支文本禁 \C、**v1 全 ASCII**（CJK 组合按 C1 结论另列验收）。
- **flag 语义（诚实口径）**：flag_id 声明保留 + 冲突检查（同 flag 被其他回执占用即冲突）——**模板 v1 不写入**（无实机证据的写入路径按 12 §C2 禁用，记诊断）。

### C3：storyline-build（工作区构建 + 声明差异闸门）

- 自管 `game_edit` 上下文——批量提交在上下文**退出**时落盘（data_win 包装内读产物 = 基线副本，**CLI 实测教训入库**）；指纹/O7 比对在提交后进行。
- **声明差异闸门**：O7 --detail 输出按通用类别解析（`<大写资源> <add|changed|del>`——**不设白名单**：解析层漏看 = 假绿，C3 验收自我修正记录）；期望资源集 = 模板常数（干净基线实证标定：STR add 9 / CODEF add 1-2 / CODEF changed 1-2 / INST add 1——随 append/create/native 路径变化）；未声明变更拒绝出候选（实跑验证：脏重建 STR×9 与干净构建 CODEF changed×1 均正确裁决）。
- 构建回执落盘 `build.json`（apply 的核对依据）。

### C4：storyline-apply（整包应用 + 幂等）

- 核对依据分层：build.json（构建回执）→ 应用前裁决 → receipt.json（应用回执：before/after/defn_sha/undo 指引）。
- **三种出口全部写前裁决**：幂等 = 同 patch_id + 目标==after + **同定义 defn_sha**（判据用回执 defn_sha 而非活产物——工作区单次消费后不在盘上）；同 ID 不同内容（定义变更）拒绝叠写；目标漂移拒绝。`--commit` 经 EditPlan 事务层（含备份 journal）；中断交给恢复分类（journal 复用方案 A），不靠猜测宣布已应用。
- **CLI 实跑全链**（/tmp 副本）：build（候选 35d189a5，声明差异 {STR add 9, CODEF changed 1}）→ preview → commit（fc049850→5a6f9b66）→ 幂等 no-op → undo → fc049850 → recovery-scan findings:0。
- `sandbox.remove_workspace` 容错化：`.deterline/` 下新增 storyline/ 兄弟目录时清理链停止（Errno 66 修复）。

### A4：候选版 v2.6.0-rc1

- 版本链 2.6.0-rc1（**预发布后缀支持**：docs-lint/release_check 版本正则扩展 `-rcN`）；95 actions 注册链全量（commands.json → COMMANDS → gen_docs 三文档 → help golden 重录 → FROZEN_EXPORTS 216→219）。
- 分发自检：干净检出 release_check 全绿（见 08 候选版记录）。

### 注册链与纪律

- commands.json 95 条（storyline 组 safety 域）；dispatch coverage 口径 95 = 76 已覆盖 + 19 豁免（**npc-choice 移出豁免**：storyline 编排 mock 级 + C1 真实 UTMT 双证据）；包纪律（跨模块引用一律模块属性/运行时查找——`_pkg()` 模式）11 处违规清偿；write_policy/utmt_spine 顺序依赖污染修复（E2E 状态卫生）。

### 前瞻登记

- storyline flag 写入路径（B5/R2 实机证据后开放）；多 NPC/多房间扩展（D2 触发）；O7 "added" 类别行解析（当前资源级明细对 added 的行形态与 changed 不同——实测 {STR add 9, CODEF changed 1} 与手工计数一致，add 类别由增量计数覆盖）；CJK 支线组合验收（C1 结论）；实机 B5/R0-R2 矩阵。

## v2.5.12 — 2026-11-18（12 计划 B 批次：模板边界——3.5 评审包落地 + O3b 三分类）

**性质：12 号四个月计划 B1/B2/B3 交付（无人值守场次；R11/R12 复审 A 线时同树并行，随 A 线分离提交）。447→462 测试（+15）。**

### B1（原 3.5 首切片）现状行为夹具（tests/test_template_resolution.py，+15）

- 把模板解析语义钉在测试层（对照 11 §2b）：door/pit/battle cur 房与 door/pit target 房 = 两段式（exact `ByName` + `OrdinalIgnoreCase` 子串回退）；`room._spawn_obj_internal`（NPC 对话/选择命令 Step 3 落点）= 两段式房 + 两段式对象 + 双向子串建议；`npc._query_npc_target` = exact → ignoreCase → 子串回退 + 父链；`utmt._room_id_by_name` = **exact-only** + "smoke-test: " 前缀（现状钉——文案修正属单独决策）。
- 覆盖棘轮教训入库：测试 docstring 出现 "npc-dialogue" 字样会被子串判据误判为已覆盖（ALLOWLIST 陈余误报）——措辞避让，判据 AST 化保持前向登记。

### B2 模板公共层（cmds/template_common.py，新）

- `idx_room_lookup`（两段式房间序号预查，自 door.py 1:1 平移——**CSX 字节不变，golden 零重录**）+ `reject_if` 语义化拒绝语法糖 + 解析策略地图 docstring（各模板保留的差异：battle cur 房内联两段式、npc 经 `_spawn_obj_internal`、verify exact-only）。
- door/pit 换点；**battle 前置 ensure_room 延后**（B1 建议默认：全命令 capture 新增 CALL 段不能声称 golden 零重录——battle 三胞胎现状钉在夹具里）。

### B3（O3b）反编译三分类（cmds/code.py）

- `decompile_classified`：("ok", lines, None)（存在且已读，**含空内容**——fresh-base 由模板自裁决）| ("not-found", None, "ERROR: not found")（条目不存在）| ("error", None, detail)（其他 ERROR / GML_COUNT 缺失 / 行序列不全）——**读失败不得当空脚本 fresh-base**（11 §2b：超时/工具错误/协议异常不能作为空脚本继续）。
- `_get_decompiled_code` 兼容面保持（None 折叠 + stderr 副作用不变）；door/pit/battle 三生成器 + list/remove-door 换点：error → `DeterlineError` 拒绝，**零写入 CSX**（钉面：读失败只发 idx 预查 + 读取两次只读调用）。
- golden 零重录证实：fresh-base 夹具应答从空串改为**真实 `ERROR: not found` 形态**（B3 后空应答=协议异常须拒绝）——捕获 CSX 逐字节不变，59 golden 全绿。

### 随批修复（Mimosa medium，A 线登记项）

- sprite.py `cmd_sprite_colorize`：`tempfile.mktemp` TOCTOU → `mkdtemp` 原子创建（finally 清理不变）。

### 前瞻登记

- `_room_id_by_name` smoke 前缀文案（verify.py 消费方，单独决策）；battle ensure_room + 2 枚 golden 有意重录（B1 评审包裁决后）；覆盖判据 AST 化。

## v2.5.11 — 2026-11-17（12 计划 A 批次：可重放恢复验证 + 写入边界收紧）

**性质：12 号四个月计划 A 线交付（无人值守场次，R11/R12 双席复审清偿后入库）。426→447 测试（+21：stress 7 + 边界 14）。**

### A2 可重放恢复验证（tools/recovery_stress.py，新）

- **独立进程强杀 + 确定性窗口注入**：窗口不靠时序竞态，子进程在真实 transactions/recovery 代码路径上 hook 打点（journal 状态写 pending/committing、暂存计数 staged、目标 os.replace after_replace1/after_replace_all、**journal 原子写内** journal_tmp——R11 P3-1 第三缺口补景），命中即 SIGKILL（Windows `os.kill(pid,9)`=TerminateProcess，`_SIGKILL=getattr(signal,"SIGKILL",9)`——R11 P1-1）。
- **12 场景 oracle 矩阵**（s1–s10 + p1_prune，全部本机实测 12/12 pass）：每场景硬编码合法终态迁移表；混合分类双向整批拒绝 + `--commit` 零执行断言；手工收口 = scan 逐条 cp 指引的程序化复刻；"无 journal 的不明部分写入算失败"（12 §A2）硬编码为 violation。
- **关键实测语义入库**（冒烟轮发现）：journal 的 **pending 记录 staged=None**——staged/rollback 路径要到 committing 态写才入记录；杀在暂存循环中 = 孤儿 `.new` 副本但记录不知情，唯一合法出口 = clean 连记录带孤儿收口（s9）。
- **证据**：JSONL（run-header 带 seed/transactions_sha/evidence_scope="process-kill-only"——R12 P3-2；record 带 child rc/killed、scan levels、copy_hashes——R11 P3-1 副本半边、final_hashes、violations、verdict）；`--batches N` 随机批次扩展（R12 P3-1）；场景级 try/except 不炸整轮（R11 P3-3）。
- **门禁**：`--confirm-synthetic` 必填 + 临时根 mkdtemp 自建；`--child` 子入口同样受门禁（只接受 `deterline_stress_` 前缀根——R11 P2-1）。
- CI 子集 s1+s2+s5a+p1（Windows s1+p1——多窗口 TerminateProcess 保守逐级验证，07 §3 条3 更新）；全量/批次 = 本地 opt-in。

### A3 写入边界收紧

- **符号链接三道防线**（12 §A3）：`ensure_not_symlink` 公共助手——`FileEdit.prepare`（resolve **之前**判定）、`write_many` baselines 直传分支（**R11 P1-2 实证绕过修复**：ini alias 曾静默写穿）、提交期紧贴 os.replace 重验（R11 P2-2 TOCTOU）；`file0.py` 直构路径同样过防线。回归钉 ×3。
- **journal 原子写残留单列**（`.journal.*.new`）：recovery-scan 新 kind `journal-tmp`——只列出不自动清理（内容可能是未落盘快照，宁缺毋滥）；扫描域 = journal_roots 本体（根级按旧契约忽略——旧钉面语义保持）。
- **kept_counts 语义订正**（B P3-4 收口）：bak-archive 与 system-info（R11 P2-3/R12 P2-1 孪生）均改 kept = 未进删除集现存数——与"保留最近 N 份"承诺可对账。
- **边界测试 14 项**（tests/test_boundary_hardening.py）：符号链接拒绝/零副作用、journal-tmp 列出且 clean 保留、kept_counts 对账、跨目录 journal 四钉（CHANGELOG v2.5.7 A P2-3 口径锚定——R12 P3-3）、相对路径 resolve/journal 落点、`..` 逃逸负形钉 + CLI 无回退钉（R12 P3-6）。
- **SKILL 退出码契约 + 锁作用域 + 分层允许根 + hardlink 局限登记**（B P3-6 收口 + R11 P3-2/R12 P3-5）。
- 并发回归沿用既有 `test_concurrent_commits_single_winner`（进程级竞争钉面随 A2 stress 的独立子进程覆盖补强）。

### 复审清偿（R11 FAIL→清偿 / R12 PASS；双席全项落地）

R11：P1-1 Windows SIGKILL 常量缺失（CI 必红）→ 一行修复；P1-2 symlink 主写路径绕过（实证探针）→ 三道防线重构 + 回归钉；P2-1 child 绕门禁 → 前缀校验；P2-2 TOCTOU → replace 循环重验；P2-3 sysinfo 口径 → 同步扣减；P3 ×3 → 全落地。R12：P1 双批次并发污染（过程性）→ A/B 线分离提交解决；P2 与 R11 重复；P3 ×7 → 全落地（含 07 §3 Windows 挂账更新：SIGKILL s1 已进 CI 级、symlink Windows 回归挂账）。

### 前瞻登记

- stress 副本哈希仅记录存续副本（apply 消费后即失）；hardlink 语义检测；`--journal` 多记录选择器（条件未触发，符合 12 §A3）；Windows symlink 回归（07 §3 条1）。

## v2.5.10 — 2026-11-14（深夜：prune-purge 入口 + 样例升级 in-game 级）

**性质：值守场次交付收尾。** v2.5.9 修复后的样例（文本 ≤3 行重录）实机六项复验**全过 → 判级升级 in-game**（05 §5.3）；purge 真删除入口交付（06 §4 执行链最后一环）。**425 测试（+5）。**

### prune-purge（新命令 91→92，06 §4 执行链最后一环）

- `prune-purge`：清空 `.deterline/pruned/<ts>/` 批次（backup-prune --commit 的最终出口）——默认预览（批次/条目/字节），`--commit` 真删除（不可逆）；**每批次硬校验 manifest.json**（缺失/损坏/schema 不符拒绝并保留——可追溯性保护）；`--preview × --commit` handler 层互斥（R5 P2-3 同款）；--json 输出 deterline.pruned-purge/v1。
- 注册链：commands.json 92 → COMMANDS/cli → gen_docs；shim 收编 cmd_prune_purge（FROZEN_EXPORTS 215→216）；tests/test_recovery_exec.py +5（预览/逐批删除+损坏保留/空 no-op/json schema/互斥）。
- 至此 06 §4 执行链完整：recovery-scan（分类）→ recovery-apply（恢复）→ recovery-clean（清理）→ backup-prune --commit（可逆移除）→ prune-purge（真删除）——破坏性逐级上升、全部默认预览 + --commit 显式激活 + 值守场次逐次确认。

### 样例升级 in-game 级（05 §5.3）

- 样例 v2：页 1 文本缩短至 3 行（`* 托丽尔你好，这是中文样例。&CJK 12px + ASCII 123 mixed。`）+ 修复后生成器（非末页裸 `/`）——实机六项复验全过（帧证据齐），判级 **sandbox → in-game**。
- 观察项：贴身站上仙人掌会同时触发原版观察文本（双框并显）——原版行为共存。

## v2.5.9 — 2026-11-14（深夜：cjk-trigger 两页翻页修复——Boot-1 实验矩阵实锤根因）

**性质：1.6 实机缺陷定位（W1 静态分析 + Boot-1 三点对照实验矩阵，实机判读 Computer-Use 代检）→ 一行修复 + golden 重录。420 测试（two-page 断言更新）。外层 05 §5.2 已收口记录；R7/R8 双席复审通过（P3 笔误随本版订正）。**

### 根因（W1 §1/H1，Boot-1 A/B/C 全过实证）

- **obj_base_writer 原版页推进语义**（dump 逐字节实证，打补丁件 = 原版）：非末页条目以**裸 "/"** 结尾（Draw 扫到 `/` 且 nextch≠`%` → halt=1 → Z 翻页 `mystring[stringno++]`）；末页以 "/%%" 结尾（nextch=="%" → halt=2 → Z 关框销毁）；终结条目 "%%%"。原版三实例（SCR_TEXT case1 / obj_undyne1_old / obj_bara04）全同构。writer/dialoguer/SCR_TEXTTYPE/SCR_TEXTSETUP 在 cjk-font 补丁后与原版**逐字节一致**——"CJK 补丁改写推进分支"不存在，typer31 为原版合法 typer。
- **生成器缺陷**（cjk.py 消息表组装）：非末页也发 "/%%" → 页 1 成为终止页 → halt=2 → Z 关框（范围内 refire 把"关框"伪装成"卡死"）→ **页 2 结构性不可达**——与 CJK 栈无关。
- **输入伪影（前瞻登记）**：合成点按可落在 30fps 帧间隙（control_check_pressed 帧沿检测）——Computer-Use 实验按键须 holdSeconds ≥0.15；真人自然长按不受影响。

### 修复

- cjk.py 消息表组装：**非末页裸 "/" 结尾、末页 "/%%"、终结 "%%%"**（单页形态不变——本就是末页语义，B4 实机已证）；golden cjk_trigger_twopage.csx 重录（diff 恰一行 = W1 预测）；test_cjk_wrap two-page 形态断言更新（含订正注释）。页内容仍拒绝 "/" "%"（writer 语义）；输入语法 `页1/%%页2` 不变。
- **Boot-1 矩阵（room_ruins1 同房三实例一次 boot）**：A=裸 `/`+中文最简 **✓ 翻页**（「第二页」帧证据）；B=裸 `/`+原文 4 行溢出 **✓ 翻页**（H3 溢出排除——纯显示层）；C=裸 `/`+纯 ASCII **✓ 翻页**（CJK 栈排除）。范围内 refire 重打 = 伴生现象（走出范围判读隔离）。
- golden 附带：sprite_replace_all/frame 占位符规范化随重录携带（比对语义不变，归因本提交）。

## v2.5.8 — 2026-11-14（夜间值守场次：06 §4 执行入口 + ROOMS_GUIDE 审批重生成）

**性质：值守场次交付（用户在场）。1.6 实机核对已执行（渲染栈 ✓/两页触发 ✗，外层 05 §5.1）。393→415 测试（+22）。**

### recovery-apply / recovery-clean（06 §4 执行入口，新命令 89→91）

- **recovery-apply**：`--direction rollback|complete` 显式择向（rollback=放弃本次，须全部目标==after；complete=继续本次，须全部 ∈{before,not-created}）；混合分类整批拒绝；副本指纹校验（staged==after / rollback==before）失败整批拒绝；**journal 复用方案 A**——不删不建运行记录，中段 SIGKILL → scan 重分类 → 可重入；完成后记录自然重分类为 not-started/done-confirm（clean 收尾）。默认预览零动作，--commit 逐目标 os.replace（副本即被消费）。
- **recovery-clean**：**现场重分类（绝不信任存量 state）**——state=committing 但实况 mixed 的记录照样拒绝；可清 = state∈状态机 且纯重分类 ∈{not-started, done-confirm}（aborted-clean+全 before 归 not-started 可清——06 §4 拒绝清单不含它）；**逐条执行**（拒绝项不影响其他可清项，退出码 1 提示）；孤儿 .new 一并清理；清理 manifest 只进 stdout/--json，不写 journal 目录。
- 实设修正：初版"无需 apply"门（not-started/done-confirm 一律拒）误挡 pending+全 before 的 complete 场景（=staging 后、首次替换前的合法继续窗口）——删除该门，裁决权交同质校验+副本校验；done-confirm+rollback=放弃本次为合法出口。
- 分类 SSOT 重构：`_collect_findings`（scan/apply/clean 共用；records 携带 level_scan/level_pure 双口径）——**scan --json 输出逐字节不变**（8 场景双版本对拍 0 字节差；人读尾行交叉引用有意更新）。

### 复审清偿（R5/R6，双席变异实证）

- **R5 P2-1** prune corrupt 口径与 scan 对齐（schema/targets 结构破损同算损坏——曾只查 JSON 解析，结构破损绕过硬前置）；**R5 P2-2** clean 在存在 corrupt-journal 时跳过孤儿清扫（corrupt 记录资产"宁缺毋滥"，处置后二次 clean）；**R5 P2-3** --preview × --commit 三 handler 互斥（parser.error）；**R5 P2-4/R6 P2-1** backup-prune SSOT 条目随 --commit 行为更新（summary/notes/gen_docs 重生成）。
- **R6 P2-2 两处"应红不红"钉面补齐**：副本**存在但指纹不符**用例（M2b 曾全绿）；pruned/**可逆移动本体**断言（moved_to 文件存在，M8 move→unlink 曾全绿）；另补 commit+拒绝零执行、corrupt×孤儿跳过、--preview 互斥三用例。
- P3 批：clean 删除失败计入退出码 + stderr 列出；拒绝指引不再死胡同（interrupted/aborted → scan cp 指引而非 apply）；scan not-started/done-confirm/aborted 动作文案随 apply/clean 交付更新；apply 执行失败文案改指 scan cp（mixed 后 apply 恒拒）；pruned ts 含微秒（同秒双次不覆盖 manifest）；apply notes 增 not-created 死角标注；CHANGELOG "committed 块"→`commit` 块；SKILL/QUESTIONNAIRE 旧 A/B/C/D 分类口径随 ROOMS_GUIDE 重生成更新；test_dispatch 头部 89→91。

### backup-prune --commit（06 §4）

- 现场重算删除集（绝不信任历史预览）+ 硬前置"无损坏运行记录"（journal 保护可能不完整时拒绝）+ 空删除集 no-op；**可逆设计**：移入 `<game_dir>/.deterline/pruned/<ts>/` + manifest（deterline.pruned-manifest/v1：原路径+sha256+undo key+reason）而非 unlink；journal 引用文件保护照常生效；undo 失效提示随行打印；purge（真删除）另立显式入口（值守场次）。
- --json：commit 模式 = deterline.backup-prune/v1 + `committed` 块（executed/refused/moved/failures/manifest）。

### 交付配套

- 新增 tests/test_recovery_exec.py（22 测试：apply 10 / clean 6 / prune commit 5 / json schema；离线 tmp 矩阵——journal 复用方案 A 的"完成后 scan 重分类"双向断言、clean 现场重分类反证、prune 保护跳过与损坏拒绝）。
- 注册链：commands.json 89→91（save 组）→ COMMANDS/cli.ACTION_CHOICES → gen_docs 三文档再生；cli 新增 `--direction`；--help golden GOLDEN_UPDATE 重录。
- **cli 帮助三处滞后清偿（B P3-5 前瞻项）**：--dir 双形态命令清单补全（+md5/doctor/backup-prune/apply/clean）、--text 补 npc-choice、--value 口径放宽；--json/--commit 帮助同步。
- SKILL 恢复链章节：scan 分类处置表改指 apply/clean 入口 + apply/clean/prune 纪律段（journal 复用方案 A、现场重分类、可逆 pruned）。
- **ROOMS_GUIDE.md 审批重生成**（用户 2026-11-14 批准，09 §3）：2026-08-16 旧版（376 行 A/B/C/D 旧分类）→ rooms-scan v2 重生成（723 行，A=237/B1=30/B2=11/D-candidate=5/unc=53，336 房，双射体检通过）；正文 = 生成器输出逐字节（重生成 diff 仅头部+采集时间戳，/tmp/rg_regen 复验）；**审批闸门保持绝对**（--out 指向正式文件仍一律拒绝，无 bypass flag）。

### 1.6 实机核对（已执行，详见外层 05 §5.1；本版无游戏侧代码改动）

- 渲染栈本体实机成立（sans 头像/混排/&硬换行/重复触发/file0 CRLF 读档 ✓）+ **两页触发 Z 翻页实机失效 ✗**（S6 首曝——沙箱字节级验证盲区实证，writer 机制静态分析 + 对照实验矩阵进行中）；样例判级如实回落 sandbox。

### 前瞻登记（更新）

- purge 入口（pruned/ 真删除，值守）、apply 多记录 `--journal` 选择器、跨目录闸门收口、kill_chaos 入库、**两页触发修复**（W1 静态分析 → 实机对照矩阵 → 修复+golden 重录）、prune system-info 哈希、覆盖判据 AST 化、CI action 升级。

## v2.5.7 — 2026-11-14（上午全量复审：四席并发审 02/03 全部成果 → 清偿）

**性质：四席并发复审（B 命令层 / C 测试与 CI / D 文档审批件 / A 架构事务层）两轮清偿，经 R1/R2 + R3/R4 两轮双席复审——0 P1，10 P2 全清偿 + P3 择要。386→393 测试（+7 测试方法；回归钉面 8——B P2-1 等值钉内嵌既有用例）。**

### 第一轮清偿（P2 ×6：B/C/D 席）

- **backup-prune duplicate_groups.reclaimable_bytes 恒 0**（B P2-1）：deletion_paths 在同组删除集构建**之前**快照——统计改在删除集成型后做第二遍；reclaimable 恰等于删除行字节，journal 保护跳过不计；test_duplicate_group_reported 补等值回归钉。
- **backup-index/prune --json stderr 泄漏**（B P2-2）：适配器 find_save_dir 失败无条件 print(stderr)——与 recovery-scan/doctor 同型：原因并入 payload warnings（save_dir_error 参数）；TestAdapterJsonStderrPurity 回归钉 ×2（stderr==""）。
- **backup-prune 人读模式 warnings 不可见**（B P2-3）：损坏 journal 前置信号人读分支无输出——补 stderr warnings 循环（对照 backup-index / prune 早退分支同款）。
- **doctor 非 dict 形态 rooms.json 报 ✓ 0 条**（B P2-4）：bool(raw) 对非空 list 为真——判定改 `isinstance(raw, dict) and bool(raw)`，detail 区分"非映射形态/空/缺失"；回归钉 ×1。
- **棘轮冻结名册截断字面量静默失效**（C P2-2）：`split("FROZEN_EXPORTS = [")` 落空时静默返回全文 → 215 个冻结名把 20 条 ALLOWLIST 误判"已覆盖"——旧失败模式经变异实证为**误导性红**（陈余爆红诱导误清偿 → 假绿面；R2 P3-1 措辞订正）——partition + 未截断显式 AssertionError。
- **test_dispatch_coverage.py `__main__` 主块在 TestDoctorJson 之前**（C P2-1）：直跑恒缺 doctor --json 2 例（45 vs 47）——主块移至 EOF（直跑 45→50，与 discover 对齐）。

### 第二轮清偿（A 席架构/事务层 + R1/R2 复审残项）

- **backup-prune 同秒 mtime 保留方向反转**（A P2-1）：mtime_epoch 整秒截断 + 稳定排序在同秒批量备份场景"留最旧删最新"（违反 COMMANDS.md"保留最近 N 份"承诺；journal 保护计数随窗口错位）——排序改纳秒级 mtime（stat 现取，不进 JSON 面）+ 路径名次级键，stat 失败回退极大值（宁可不删，R3 观察）；同秒夹具回归钉。
- **recovery-scan 孤儿暂存漏扫目标 parent**（A P2-2）：注释承诺"roots + 各目标 parent"但实现只加 roots——journal 先于暂存落盘（pending 记录 staged=None）时嵌套工作区旁残留永不报告；目标 parent 纳入 orphan_dirs（`_register_orphan_dir` resolve 归一去重，顺带修 A P3-4 双 root 重复扫描）；嵌套孤儿回归钉。
- **跨目录混合提交闸门豁口**（A P2-3）：journal 只落首目标旁，崩溃后仅动另一侧目标的再提交不被拒——完整收口需记录回查清单/上下文 roots（挂值守批次），本轮先把局限提升到 SKILL 恢复链章节（补偿控制：recovery-scan 双 roots 报 suspicious）。
- **"216 实验"可重放性声明过强**（A P2-4）：CHANGELOG/SKILL/外层 06/07/03 五文件六处措辞收敛为"216 一次性运行未入库 + 确定性窗口 1 窗口有入库回归测试"（A 席独立复刻实验 8/8 断言通过——方法学成立、结论可复现，问题仅在证据面）。
- journal 目录 fsync（A P3-2 掉电加固，Windows 无此语义静默跳过）；interrupted 无副本时指引文案分支（A P3-5）；errors.py docstring 注记（A P3-6）；roots 拼写差 resolve 去重（A P3-4）。
- 复审残项：直跑==discover 测试数钉（R2 P3-2，防 `__main__` 位置回归）；prune 损坏 journal 人读可见性钉（R2 P3-3）；外层"五项"残留 ×4 对齐六项（R2 P3-4：03/05/07/08）；save_cmds prune warnings 注释的行号引用改位置描述（R2 P3-5——删号式修复，diff 中无行号可检索）；CHANGELOG 棘轮条目措辞订正（R2 P3-1）。

### 清偿（P3 择要）

- verify-code 零 ROUNDTRIP 行：stderr 显式 WARN 留痕（假绿面；退出契约保守不变）（B P3-2）。
- smoke-test external 观测到内容不符标记：留痕区分"触发器已执行过（陈旧/伪造标记）"与人未操作（B P3-3）。
- release_check check_git_clean 收紧：删 "?? .github" 历史白名单（tests.yml 已入库）（C P3-4）。
- 数字漂移订正：FROZEN 213→215（compat_surface 注释）、water_undynefinal "3 启用层"→"2 启用层"（实测 bg_waterfalltex/bg_undynecrag）、棘轮头 84/84→89/20 口径、doctor inifile._read_ini 注释订正（现行实现已零写盘，旧注释失实）（B P3-7/P3-8、C P3-1）。

### 外层文档修复（D 席，随本版落）

- 11 设计稿：§3 残留 `code.py:140-150` → `:97-124`（与 §2.3 自我修正对齐，D P2-1）；door.py:108-111 → :112-114（D P3-1）；"09 §5.4" → "09 §5 条 5"（D P3-5）。
- 09 §1：实机"五项"→"六项"（05 §5 六条清单为权威，D P3-6）；03 手册 1.2 注记"12 条负例"精确为"含 2 阳性对照"（D P3-7）。
- CHANGELOG v2.4.1：backup-index 引入提交 92a2393 → 19d59f1（92a2393 为同轮审核修复，D P3-2）；rc1 段补 CI 前史（1216993/3d9cfc5，D P3-4）。

### 前瞻登记（未清偿）

- prune hash_kinds 补 system-info + kept_counts 语义名不符实（B P3-4）；cli help 三处滞后（--dir/--text/--value，需 --help golden 重录）（B P3-5=A P3-8）；异常退出码契约文档化（B P3-6）；覆盖判据子串提及 → AST 级（C P3-2）；CI checkout@v4/setup-python@v5 Node 20 弃用告警升级（C P3-5）；CHANGELOG v2.3.x 段序倒排归位（D P3-3，纯排版）。
- **A 席架构残项**：kill_chaos 随机杀脚本入库（A P2-4 彻底解）、伪造相对路径记录闸门加固（A P3-1）、`.journal.*.new` 残留单列（A P3-3）、RuntimeError 收编 DeterlineError（A P3-6 实作面）、跨进程竞争字面测试（A P3-10）、跨目录闸门完整收口（A P2-3）、prune keep_path 语义角落（R1 观察 a）——均挂值守/O3b 批次。

## v2.5.6 — 2026-11-14（终轮清偿：firmlink 闸门 + 生成器健壮化 + 批次 12/13 收口）

**性质：终轮双席清偿（0 P0/P1；4 P2 → 3 清偿 + 1 设计稿修订）。375→386 测试。外层新增 11-阶段3设计稿.md 与 ROOMS_GUIDE.draft.md 审批件（336 房留痕）。**

### 闸门（P2-1 清偿 + 加固）

- rooms-scan 协议列表分隔符改 `\u001f`、畸形字段显式 RuntimeError（曾逗号碰撞出假 D-candidate / IndexError 裸栈）；inst/tiles int 解析对齐干净报错。
- **ROOMS_GUIDE 审批闸门三重判定**：resolve 字面 + 大小写折叠（macOS 卷不敏感绕过实测后修）+ samefile（硬链接别名）+ **父目录同 inode + 文件名 casefold**（firmlink 缺失态绕过——B 席 /tmp 同构证明，正式文件缺失时旧闸门完全失效）。
- 生成器：未知/非字符串分类兜底节（不丢房）+ 分类统计现算 + 行净化 + JSON 损坏/OSError 干净报错 + schema v2 条件式警告；`.gitignore` 补 `ROOMS_GUIDE.draft.md`（须审批的草稿不入库）。

### 批次 12（补记）

- doctor `--dir` 目录双形态（resolve_game_data_file，与 md5/undo/backup-index 同语义）；SKILL/commands.json 启动次数口径统一为域F 原文（11 次启动/8 受控变体；13/15 漂移清除）。

### doctor --json（v2.5.5 主特性延续）

- `deterline.doctor/v1`：save_dir/items{label,ok,detail}/fails；人读输出零扰动（git archive 对照）；fails 计数自纠（曾只在人读分支计数，双回归钉）；JSON 存档定位失败原因进 items[0].detail（人读双打印同步消除）。
- `--dir` 存档目录为文件时的报错措辞区分（paths.py，低危口径项）。

### CI 状态（如实）

- 198fe5b/387b74a：ubuntu ✓ windows ✓ **macos ✗（infra："job not acquired by Runner"，容量约束，非测试失败）**——首见，随 runner 容量波动。
- 历史红已按 v2.5.3/v2.5.5 补记口径全数登记（4+1 次）。

### 外层交付

- `11-阶段3设计稿.md`：3.3 收口记录（RESCAN_PLAN §七 自动化对照）+ 3.5 实施方案（**经终轮修订**：两段式房名语义二选一、语义拒绝三条改待实验/实况纠偏/口径对调）+ 前向记录。
- `ROOMS_GUIDE.draft.md`：336 房审批件留痕（重放逐字节复现，仅采集时间差）。

## v2.5.5 — 2026-11-14（凌晨收口：批次 10/11 清偿 + doctor --json）

**性质：双席交叉审核 2 轮清偿（批次 10 修复 + doctor --json）。382→386 测试（+4：闸门 2 + doctor JSON 2）。**

### 批次 10 清偿（审核席 A/B）

- **审批闸门三重判定**（P1/P2-2）：`--out` 指向正式 ROOMS_GUIDE.md 一律拒绝——resolve 字面 + **大小写折叠**（macOS 卷不敏感绕过，已实测覆盖正式文档后修复）+ **samefile**（硬链接别名）；回归钉 2 条。
- **未知/非字符串分类兜底**（P2-1/P2）：未知标签落"其他（人工标签 …）"节（不丢房）；**非字符串标签归一 uncategorized**（null/bool/数字曾静默消失）；分类统计由 rooms 现算（stale summary 不再矛盾）；混合类型排序键 str 化（曾 TypeError 裸栈）；统计键过 _sanitize。
- **rooms-scan schema 升 v2**（idx 字段入协议）；生成器对 v1 旧稿条件式警告（带 idx=v1 旧稿措辞如实）；JSON 损坏/缺观测字段干净报错（曾裸 traceback）；房行/理由/头部 _sanitize 净化（防 markdown 行裂/注入）。
- scan_rooms.py docstring 如实化（original_* 字段从未实现——改为兜底节/现算口径）；room.py 分节注释 v1→v2、inst/tiles int 解析对齐干净报错。
- CHANGELOG v2.5.4 定性修正：未登记 92 房 = 旧指南**无中文注**集合（含开发房与 room_battle/room_tundra_sanshouse 等真实房间），非"等开发房"。

### doctor --json（v2.5.5 主特性，风险席填缝批）

- `doctor --json`：stdout 纯 JSON（schema **deterline.doctor/v1**：save_dir/items{label,ok,detail}/fails）；人读输出逐字节零扰动（git archive 对照实测）；退出码语义不变（任一 ✗ → 1）。
- **fails 计数自纠**：JSON 分支曾不计数（恒 0）——上移至统一入口，双回归钉（变异实验：移回旧位两用例必红）。
- JSON 模式存档目录定位失败原因进 `items[0].detail`（此前 stderr 行蒸发、JSON 无原因）。
- `--json` help 文案、commands.json doctor 条目同步。

### 诚实记录

- 6c52cba 推送 CI 红（windows cp1252：test_gen_rooms_guide e2e 的 subprocess 无 encoding + fixture 残留 v1 触发 stderr ⚠️——本版双修）；v2.5.1 记录更正为 4 次红（见 v2.5.3）。
- 前向：doctor --dir 目录双形态（md5/undo 已接 resolve，doctor 未接）——归表驱动 dispatch 后续；SKILL"启动次数 11/13/15"三口径漂移未清（历史文本，挂文档复核）。

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

- CI 从单 ubuntu 扩为 **ubuntu/windows/macos 三 OS 矩阵**（fail-fast: false）：344 单测 + gen_docs --check + --help golden + `install.py --check` 安装入口（只读）+ diff 卫生。**Windows 侧 msvcrt 锁分支与路径语义首次真实执行**（03 §2.5 挂账项转 ci-static ✓）。（CI 前史补记 D P3-4：1216993 单 ubuntu 最小工作流、3d9cfc5 平台中立 golden 路径，v2.4.x 期间落库）
- 外层新增 `07-平台矩阵与验证级别.md`：能力 × 平台 × 验证级别全表；明确挂账（Windows UTMT 集成/Windows smoke/TerminateProcess 实验/行尾游戏读回）。

### 阶段 2.6 候选版（本版）

- `tools/release_check.py`：工作树提交态 / 版本链单点 / gen_docs / help golden / 命令注册表↔commands.json / 分发关键文件 / install --check 入口 / 全量单测——候选版门槛命令化。
- 外层 `08-候选版发布记录.md`：Git 标识、验证范围、已知限制、工作区迁移说明、CLI 兼容说明、回退方法。
- tag `v2.5.0-rc1` → **rc2**（三平台 CI 首夜实证修掉 Windows 平台差异：fsync 只读句柄 Errno 9 / cp1252 打印与解码 / golden 反斜杠 / 夹具泄漏钉——详见 07 §3.0；run 43336290168 三平台全绿）。

### 阶段出口核对（03 §6）

常用写入与恢复有可重放证据（journal + recovery-scan + SIGKILL 确定性窗口回归测试入库；216 随机杀实验为一次性运行未入库，A P2-4 措辞收敛）✓；自动检查不依赖真实存档 ✓；候选版对每个平台和功能列出实际验证级别（07 矩阵）✓；真实 Steam 或 Windows 验证单独挂账 ✓。

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
- 成功后整目录摘除；失败路径 aborted-* 保留（含 error 聚合）；**SIGKILL 保留——216 次随机 kill + 3 个确定性窗口实验 0 违例**（目标内容恒 ∈ {before, after}，journal 全部可解析；A P2-4 补注：216 为一次性运行、采样脚本未入库——确定性窗口中 1 窗口有入库回归测试，A 席独立复刻 8/8 通过）。
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

### 新命令：`backup-index`（阶段 2.3 O5 最小切片，19d59f1；92a2393 为同轮审核修复——D P3-2 引用订正）

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
