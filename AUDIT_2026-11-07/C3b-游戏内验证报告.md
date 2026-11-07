# C3b 中文字体注入 —— 实施与游戏内验证报告

- 日期：2026-11-07
- 状态：**管线全部建成（sandbox 验证通过）；游戏内渲染被 Mac runner 深层机制阻塞**——经 15+ 次受控启动实验定位出 3 条硬约束与 2 条待验证假设，按域F 教训在烧尽资源前停点。
- 用户游戏已回滚基线：game.ios `fc049850` / file0 `2c9c68d0` / undertale.ini `0e4027d0` ✓

---

## 一、已交付资产（全部入库）

| 资产 | 说明 |
|---|---|
| `tools/font_cjk_build.py` | 字形页生成器：OFL 字体（Fusion Pixel 12px，缝合像素，OFL-1.1）→ 12px 字形页 + glyphs.json。字符集 = ASCII + 全角标点 + 假名(190) + GB2312 一级 3755（`--full` 加二级）。确定性构建。 |
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
| PD | 基线 + npc中文 + 就地改造 + **无条件**映射 + **无条件** prefetch | 💥 进房瞬间死循环挂起（无空格中文触发 writer 换行死循环）；消息加空格后不挂但仍全空 |

## 三、定论（证据充分）

1. **【硬约束】不能新增字体资产**：Data.Fonts 追加即全局字体查址失效（R1-R4 vs A0/BX；疑 Mac 移植 runner 固定 20 字体表）。新增 EmbeddedTexture/TPI/Sprite 本身无害（BX/BY）。
2. **【硬约束】中文字符串必须预折行（空格分隔）**：无空格 CJK 长句让 obj_base_writer 换行逻辑死循环（PD 挂起；侦察预警 #4 升级为 crash 级）。
3. **【硬约束】global.language ≠ "zh"**（PC 的 ✱ 来自 fnt_main 回退反推；Mac 移植 os_get_language 不返回 zh——未直接测量，但 PC/PV 对比已足够定性）。
4. **【未解】字体渲染器不加载新页**：即使无条件 sprite_prefetch（PD/PW/PV），draw_set_font 指向新页的字体渲染全空——sprite 路径的 prefetch 未惠及字体路径（ja 页机制可能依赖 runner 内部表）。这与域F"反编译正确 ≠ 运行时正确"同类，属 runner 黑盒。
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
