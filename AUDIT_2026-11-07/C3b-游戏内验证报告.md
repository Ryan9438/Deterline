# C3b 中文字体注入 —— 实施与游戏内验证报告

- 日期：2026-11-07
- 状态：【2026-11-08 更新】**中文已在游戏内实机渲染成功（B4，见 §九）**——页内重排全栈打通（表替换/像素换/码点/typer31 排版分项实证）。前史：11-07 曾判"被 Mac runner 深层机制阻塞"，经 B3/B4 分解证明阻塞根因是臂位越界（房间仅 320×480）与守卫恒真，约束③④已按一手证据修正。
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

## 九、B3/B4（2026-11-08）：变量分解 + 完整中文栈——**中文实机渲染成功**

离线精读 writer 全事件 + control_* 脚本后，B3 五臂单变量分解、B4 整合，两轮 boot（加 b3c/b3b 修正重跑）全部落定。

### 布局数学定论（obj_base_writer 全事件 + SCR_TEXTTYPE/TEXTSETUP 精读）
1. **writer 逐字推进 = `spacing`（SCR_TEXTSETUP argument8，per-typer 固定常数）**。glyph 的 Shift/Offset 只影响单字绘制定位，**不影响步进**（Draw_0 只画单字符后 `letterx += spacing`）。图集的 Shift=12 约定与此无关。
2. 各 typer 的 spacing：typer3(fnt_curs)=10、typer5(fnt_maintext)=8、typer2(fnt_plain)=9、typer1(fnt_main)=16、**typer31(fnt_maintext)=12 且 writingxend=9999（不自动折行）——12px CJK 的最佳 typer**。
3. ja 语言分支的逐字修正（全宽/半宽/ASCII 间隙）与 SCR_TEXTTYPE 的字体转换块都只在 `global.language=="ja"` 时生效。
4. **writer 文字是视口锚定的**：obj_dialoguer.Create 里 `xx=view_xview[view_current]`，writer 生成于 `(xx+68, yy-5)`，facechange 在 Create 即置 1。带着框走位 → 头像/文字"漂浮" = 引擎原配行为（正常对话镜头不动所以看不见）。"空框=文字离屏"假说否决。
5. typer3 的设计性怪相：writingy=writer.y（框上缘外）+ spacing10 对 MNC 宽字形 → **B2 T-CTRL 的"叠字+画出框外"是 typer 设计，非 bug**。

### 输入系统（control_update 反编译，框管理协议的依据）
`control_*` = `global.control_state/pressed[0..2]`：**槽0 = Z/Enter**（writer Step_0 轮询 → halt 翻页/`/%%` 销毁）、**槽1 = X/Shift**（dialoguer 补完 stringpos/跳过）、**槽2 = C/Ctrl**。gamepad/joystick 并入同槽。
**关框协议：X（瞬补完）→ Z（翻页/销毁）**；半径内关框即重触发（同帧多臂时低 instance id 先赢）→"走中带关"。writer 卡死框（halt 态 Z 无效）偶发，房间切换强制清场。

### 三项历史更正（B1/B2 结论重写）
1. **B1/B2 的 scr_setfont "无条件映射"从未注入**：守卫串 `newfont = fnt_ja_main;` 在基线 scr_setfont 的 ja 分支里本就存在（守卫恒真）→ b1_assert 的 A_SETFONT 检查恒真、形同虚设。**B2 C-ARM 实际走的是原版 fnt_maintext**。判重必须用"基线不存在的单行插入形态 + 计数"（⚠️ 注释标记经反编译即失，只宜作代码可读性标注，不作守卫）。
2. **room_ruins1 实际 320×480**（UT 坐标系 = 屏幕一半，view 320×240 ×2 缩放）：B2/B3 初版臂位 (320,·)/(480,·) 在墙外/房外，**物理上不可触发**。B2 的"N-ARM 结果未记录"、B3 初 boot 三臂沉默、B2 C-ARM"空框"（实为别的臂残影）均此根因。**一切臂位必须在离线 assert 里核对 x<320。**
3. B2 "T-CTRL 渲染✓但叠字" = typer3 设计（见上）；"C-ARM 空" = 臂位越界从未触发。B2 的观察记录全部被 B3/B4 重解释。

### B3 五臂矩阵（单变量分解；b3c 修正位 boot + 前序 boot 数据）
| 臂 | typer | 变量 | 结果 | 判定 |
|---|---|---|---|---|
| D-CTRL | 3 | 全原版对照 | teal 叠字（5 次 boot 稳定复现）| harness 活 ✓ |
| A-SWP | 5 | emb19 maintext 区品红重染 | **品红干净 ASCII**（Flowey 对话/六柱房 Toriel 对话同证）| **V3 页内像素换触达字体渲染 ✓** |
| E-KANA | 31 | 同上重染 + 假名消息 | **品红假名 あいうえお 完整、无叠字** | **V4 码点路径 ✓（>0x3041 码点直达字体查找）+ typer31 排版 ✓** |
| B-TBL | 30 | fnt_ja_main@原TPI+共享表(4064+canary=4065) | 稀疏白碎片（查得到字形、采到原页错位像素）| **V1 glyph 表替换+查找链路 ✓** |
| C-NPG | 68 | fnt_ja_plain@**新 256² 页**+maintext 原表 | **空框（X 补完仍空）** | **约束④ 单次复测成立**（与 R1-R4 方向一致；4096² 按同机制推定 NO-GO）——B2 Arm-N 因臂位越界从未触发，不构成重复观测 |

附：Pillow RGBA `getbbox()` 由 alpha 通道驱动，RGB 变化 alpha 不变时漏检——font_emb20_compose.py verify() 已改 numpy 全通道差；B2 的 emb20_page_new.png 经全通道复核真实无越界（102 万像素全在象限+金丝雀内）。

### B4 完整中文栈 = **成功**
栈：emb20 象限换页（页身份不变）→ fnt_ja_maintext.Texture 重指向 TPI#6543(1024²象限) + 共享表 4064 字形 → scr_setfont 单行映射 `if (newfont == fnt_maintext) { newfont = fnt_ja_maintext; }`（B4_MAP 标记守卫）→ preload 无条件 prefetch → 触发臂 typer31 @(220,330) face3 msc0 无空格消息。
**实机结果：`* B4中文测试ABC` 清晰渲染（N=1，单 boot 观察）**——中文四字 Fusion Pixel 12px、间距均匀无叠字、与 ASCII 混排正常、sans 头像正常。fonts=20 硬约束未破（b4_inject 自身不新增字体资产；实际 boot 文件另含 B3 残留的 1 页 1 TPI，见上节谱系披露）。

### B4 boot 谱系披露
B4 的实际 boot 文件 = b3c.ios（含 B3 五臂与新增页残留）+ b4_inject + `/tmp/b4_fix.csx`（把 B3 旧 E-KANA 113928 挪至不可达点 (320,400) 以隔离 B4-MAIN；该步骤脚本未随 b4_inject 入库）。故 b4f.ios 同时含 B3_MAP/B4_MAP、新页 Texture26、canary 表（4065）等 B3 残留；复核席逐项排除后确认 B4-MAIN 的渲染路径不受残留影响，结论稳健。纯净化复现：以 game.ios 基线直接跑 b4_inject（其守卫与臂位自成一体）。

### 语言探针（一手证据，约束③修正）
D-CTRL 触发块双路径写 `zcode_lang_probe.txt` 成功回收：`lang=[en] locale=[zh_CN] oslang=[zh] osregion=[CN]`。
- **os_get_language() 在本机返回 "zh"（旧结论"Mac 移植不返回 zh"错误）**；`global.language="en"` 是游戏自身对非 en/ja 语言的回退。
- 实践结论不变：ja 分支永不触发。**备选路线（未验证）**：mod 主动设 `global.language="ja"` 可激活游戏原生 ja 管线（字体转换+spacing×13/8 等）。

### 遗留/下一步
1. **S6 集成（READY）**：cmd_cjk_font 管线收尾——typer 选择器（默认 31）、折行 util（排版卫生项，writingxend 语义已知）、文档（commands.json SSOT + gen_docs）、把手写触发块形态生成器化。
2. 开放项：CJK↔ASCII 混排的 ja 式间隙（language="ja" 才有）；canary UV 钳位未判定（无品红出现，未深究）；writer 卡死框根因（偶发，房间切换可清）。
3. 实验资产：build/cjk_verify/{b3_inject,b3b_move,b4_inject}.csx + dump_writer_events/control_update 等 dump；本 boot 全程 CUA 截图存于会话记录。
