# C3b 中文字体注入 —— 实施与游戏内验证报告

- 日期：2026-11-07
- 状态：**管线全部建成（sandbox 验证通过）；游戏内渲染被 Mac runner 深层机制阻塞**——经 15+ 次受控启动实验定位出 3 条硬约束（其中约束②后降级为排版卫生项，见 §三.2 与 §八）与 2 条待验证假设，按域F 教训在烧尽资源前停点。
- 用户游戏已回滚基线：game.ios `fc049850` / file0 `2c9c68d0` / undertale.ini `0e4027d0` ✓

---

## 一、已交付资产（全部入库）

| 资产 | 说明 |
|---|---|
| `tools/font_cjk_build.py` | 字形页生成器：OFL 字体（Fusion Pixel 12px，缝合像素，OFL-1.1）→ 12px 字形页 + glyphs.json。字符集 = ASCII + 全角标点 + 假名(191) + GB2312 一级 3755（`--full` 加二级）。确定性构建。 |
| `tools/font_cjk_atlas.py` | 图集构建器：源字体 ASCII 拷贝（保中英混排）+ CJK 排版 → 2×2048² 图集 + glyph 规格（TPI 相对坐标、按码点排序、advance=2×ASCII 中位）。 |
| `scripts/modify_save.py cmd_cjk_font` | 四步管线命令：pass1 只读 dump → 图集构建 → pass2 注入 → verify-code scr_setfont。已注册 argparse/dispatch/commands.json。 |
| `assets/fonts/vendor/` | Fusion Pixel 字体（gitignore，OFL.txt 随行） |
| 测试 | golden ×2（两段 CSX 钉形）+ 全套 118 通过；drift lint 覆盖 commands.json |
| 侦察 | `C3b侦察-字体/`（10 探针 + 报告）——字段全集、对话字体链、API 可行性 |

## 二、游戏内实验矩阵（全部受控、快照可回滚）

| # | 状态组合 | 结果 |
|---|---|---|
| A0 | 基线 + npc ASCII 触发器 | ✅ "✱ BASELINE TEST 123" 完美渲染 |
| R1 | +新字体×3 +新页×2 +scr_setfont zh +preload zh | ❌ 空框 |
| R2 | R1 + zh→ja 映射 | ❌ 空框 |
| R3 | R2 + 无条件映射 + ASCII 字面量消息 | ❌ 空框 |
| R4 | R3 + scr_setfont 恢复原版（保留资产+preload） | ❌ 空框 |
| BX | 基线 + npc + **仅**纹理/TPI/精灵（无字体无补丁） | ✅ 渲染正常 |
| BY | BX + ja 字体 Texture→新页（对话仍走 fnt_main） | ✅ 渲染正常 |
| PC | 基线 + npc中文 + **就地改造** ja 字体（新 Texture+新 Glyphs）+ zh 分支 + preload zh | ⚠️ 仅 "✱"（ASCII）渲染，CJK 不出 |
| PV | PC + 无条件映射 + 混合消息 | ❌ 全空（含 ASCII） |
| PW | PV + ja 原 glyph 列表 + 新 Texture + 无条件映射 | ❌ 全空 |
| PD | 基线 + npc中文 + 就地改造 + **无条件**映射 + **无条件** prefetch | ⚠️【2026-11-08 更正：当时误判为死循环挂起】真实症状 = face0+无msc 复合幽灵框（writer 读 msg[1]="%%%" 每帧自毁），**游戏正常运行**（用户实测人物可走动）；CUA"窗口停止渲染"为采集假象。消息加空格后仍全空 = face0 文字不可见 |

> ⚠️ **RV-B 复核补注（2026-11-07）**：PC/PV/PW/PD 实验使用的 glyph 表为**修复前的图集产物**
> （ASCII 码点重复 95 个/字体 + CJK 按拼音序未按码点排序 + 无假名）。该变量未受控——
> 若引擎按有序表二分查找字形，"CJK 查不到"可能叠加在约束 4 之上。约束 4 的主因判定
> （新页不加载，PV/PW 连 ASCII 全灭）不受影响（BY 用原 ja 有序 glyph + 新页同样全灭），
> 但**页内重排动工前必须先用修复后工具（ASCII 过滤 + 排序）重建 glyph 表复测**。
> 语言探针：bootv.csx 内嵌了 zcode_lang_probe.txt 写入（working_directory 路径拼接缺陷
> 未落地回收），故"global.language≠zh"为联合推断而非直接测量——复测时用裸文件名探针。
> A0/R1 无专属存档脚本：A0 复现 = 基线 + `npc-dialogue --text "* BASELINE TEST 123/%%" --range 99999 --commit`；R1 复现 = `cjk-font` 全管线（修复前工具）。

## 三、定论（证据充分）

1. **【硬约束】不能新增字体资产**：Data.Fonts 追加即全局字体查址失效（R1-R4 vs A0/BX；疑 Mac 移植 runner 固定 20 字体表）。新增 EmbeddedTexture/TPI/Sprite 本身无害（BX/BY）。
2. **【2026-11-08 降级：原判"死循环挂起"为误判】** 无空格 CJK 的真实风险是**水平溢出对话框**（writer 按空格断词；SCR_NEWLINE 回扫死循环假说从未实证）。折行建议**保留但降级为排版卫生项**，不再声称"防挂起"。
3. **【硬约束】global.language ≠ "zh"**（PC 的 ✱ 来自 fnt_main 回退反推；Mac 移植 os_get_language 不返回 zh——未直接测量，但 PC/PV 对比已足够定性）。
4. **【未解】字体渲染器不加载新页**：即使无条件 sprite_prefetch（PD/PW/PV），draw_set_font 指向新页的字体渲染全空——sprite 路径的 prefetch 未惠及字体路径（ja 页机制可能依赖 runner 内部表）。这与域F"反编译正确 ≠ 运行时正确"同类，属 runner 黑盒。⚠️【2026-11-08】本条的证据（PD/PW/PV）已被 §八 认定为 face0 污染——约束④待用 face3 修正版重测（B3）。
5. **【未解】glyph 列表替换未被验证可渲染**：PW（原 glyph+新 Texture）与 PV（新 glyph+新 Texture）均因页未加载而无法区分"glyph 替换是否可行"。

## 四、后续路径（按性价比排序）

1. **页内重排（最稳）**：不动纹理页列表——重建 emb#20（ja 页）像素：ja 原 780 glyph 原坐标重贴 + CJK 压缩网格（26×30）填入剩余空间（可容 ~4290 字），ja_main.Texture 不变、Glyphs 全量重写（含 ASCII/kana/CJK）。绕过约束 4。工作量：图集构建器改页内布局 + ja glyph 坐标重写脚本化，约 1 天 + 验证。
2. **4096 页实验**（若 runner 支持大页）：替换 emb#20 为 4096²，容量无忧。一次启动即可证真/伪。
3. **Runner 逆向**：定位 GMS1.4 Mac runner 的字体页加载表（IDA/Ghidra），一次性解明约束 1/4。
4. **替代渲染层**（绕开引擎字体）：对话文本逐字精灵化（对象驱动渲染，完全绕开 UndertaleFont）——工作量大但机制全在自己手里。

## 五、复现与回滚

```bash
# 注入（沙箱）→ 应用 → 验证
python3 tools/font_cjk_build.py --font assets/fonts/vendor/fusion-pixel-12px/fusion-pixel-12px-monospaced-zh_hans.ttf --out-dir build/font_cjk
python3 run.py --action cjk-font --value build/font_cjk --file data_win
# 诊断脚本存档：build/cjk_verify/*.csx（A0~PD 全部可复现）
# 回滚：experiment-restore pre_c3b（快照保留中）
```

---

## 八、B1/B2 系列（2026-11-07 深夜，face0 bug 发现与渲染突破）

用户协同走位 + 逐步二分，**推翻了此前两项"定论"并打通渲染**：

### 新定论（证据充分）
1. **⚠️ 手写触发块两大陷阱**（此前 15+ 次 boot 观察被其污染）：
   - **缺 `global.msc = 0`**：writer 关框后 msc 停留 1+，后续触发读 `msg[1]="%%%"` → writer 每帧自毁 → 永远空框、Z 无效、走路正常（"幽灵框"的真身）。
   - **缺 `global.facechoice`（默认 0）**：facechoice=0 时 writer 的文字渲染整体不可见（B1h/B1k 实证；facechoice=3 立即正常——B1j/B1l 实证）。机理待查（疑 Draw 内 face 分支的坐标计算）。
2. **✅ 文字渲染已打通**：B2 系列（页内图集 + 无条件映射 + face3 修正）里 T-CTRL（fnt_curs 原版）**渲染出了文字**（teal 色）——writer/字体/glyph 查找链路活着。
3. **⚠️ 遗留两问题**：(a) T-CTRL 的字符**叠字**（每字符横向推进异常，字符互相重叠、且画出框外）；(b) C-ARM（fnt_ja_maintext@共享图集）框空。Scale2 已排除（去掉后叠字依旧）。需离线精读 obj_base_writer_Draw_0 的排版数学（myx 推进与 Offset/Shift 语义）后修正图集度量约定。
4. **⚠️ Mac runner 退出（SIGTERM）会回写 game.ios**——pkill 后必须重新 restore 才是干净基线。
5. **约束④（新页不加载）证据被 face0 污染**——PW 实验用的是 face0 臂；新页路线待用 face3 修正版重测（B2 的 Arm-N 机制已备好）。

### B1/B2 实验矩阵速查（CSX 归档于 C3b-实验CSX/）
| boot | 状态 | 结果 |
|---|---|---|
| B1/B1c/B1f | 手写臂（face0+无msc+无/） | 幽灵框（msc+face0 复合） |
| B1h/B1k | 单臂 face0 | 幽灵框（face0） |
| B1j | face3 + scr_gettext 镜像 | ✅ "✱ HELLO B1J" 完美渲染（含头像） |
| B1l | 双臂 face3/face0 | face3 臂渲染✓（Z 推进待查）；face0 臂未观察到 |
| B2/B2c | 页内图集+映射+四臂face3 | T-CTRL 渲染✓但叠字；C-ARM 空；Scale2 已排除 |

### 下一步（离线优先，不烧 boot）
1. 精读 obj_base_writer_Draw_0 的 myx 推进/换行/Offset-Shift 语义 → 修正图集度量 → sandbox → 1 boot 复测四臂。
2. 用 face3 修正版重测 Arm-N（新页）→ 关闭约束④。
3. GO 后按价值派 S6 集成（折行 util + --typer + 文档）。
4. 开放项：B2 各臂消息沿用空格化 CJK（"中 文 测 试"，C3b-实验CSX/b2_inject.csx）——该设计原以防挂起为动机（已降级），现仅余排版理由；无空格 CJK 在 face3 健康条件下的实际渲染/折行行为至今未观察，属开放项。
