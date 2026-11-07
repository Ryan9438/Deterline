# C3b 侦察：字体资产清单（fonts_dump）

> 数据来源：`p1_fonts_dump.csx` 输出（p1_output.log）+ `fonts_dump.json`（1.9MB，含全部 20 个字体的完整 glyph 数组）。
> 运行命令：`dotnet ~/UndertaleModTool/UndertaleModCli/bin/Release/net10.0/UndertaleModCli.dll load game.ios -s p1_fonts_dump.csx`（只读，无 -o）。

## 1. 全部字体（20 个）

**重要修正：本数据文件（Mac 版 Undertale 移植基座，game.ios）中不存在 `fnt_marsneedcunnilingus`。**
英文字体为 10 个 + 日文字体 10 个。对话主字体的对应物见下表（displayName 保留原名）。

| 字体名 | displayName | glyphs | range | emSize | 纹理区域 (TPI# / emb# / src) | 用途（由 p2 扫描确认） |
|---|---|---|---|---|---|---|
| fnt_wingdings | Wingdings | 96 | 32-127 | 12 | #6530 / emb18 / 2,262 256x128 | SCR_TEXTTYPE(wingdings 类型) |
| **fnt_main** | 8bitoperator JVE | **269** | 32-12540 | 24 | #6531 / emb19 / 0,0 256x1024 | **对话主字体（typer 0 默认）**+ 战斗等 27 处 |
| **fnt_maintext** | 8bitoperator JVE | **269** | 32-12540 | 12 | #6532 / emb19 / 768,0 256x256 | **对话主字体（NPC/剧情）**，55 处引用 |
| fnt_small | Crypt of Tomorrow | 96 | 32-127 | 6 | #6533 / emb18 / 262,262 128x64 | 标题/菜单 |
| fnt_plain | DotumChe | 269 | 32-12540 | 12 | #6534 / emb19 / 768,256 256x256 | 对话（plain 类 typer） |
| fnt_plainbig | DotumChe | 96 | 32-127 | 48 | #6535 / emb19 / 256,0 512x512 | 大号 plain |
| fnt_dmg | Hachicro | 96 | 32-127 | 24 | #6536 / emb18 / 0,2 512x256 | 伤害数字 |
| fnt_curs | **Mars Needs Cunnilingus** | 96 | 32-127 | 18 | #6537 / emb18 / 2,394 256x128 | 菜单光标/名单（原名所出） |
| fnt_comicsans | Comic Sans MS | 96 | 32-127 | 10 | #6538 / emb19 / 256,512 256x128 | comicsans 对话 |
| fnt_papyrus | Papyrus | 96 | 32-127 | 8 | #6539 / emb19 / 512,512 128x128 | papyrus 对话 |
| fnt_ja_comicsans | HappyRuikaKyohkan-07 | 780 | 32-65439 | 12 | #6540 / emb20 / 1024,512 512x512 | 日语 comicsans |
| fnt_ja_comicsans_big | 同上 | 780 | 32-65439 | 24 | #6541 / emb20 / 0,0 1024x1024 | 日语 comicsans 大 |
| fnt_ja_curs | JF Dot Shinonome Gothic 16 | 268 | 32-12540 | 13 | #6542 / emb20 / 1536,1024 512x256 | 日语光标 |
| fnt_ja_main | JF Dot Shinonome Gothic 14 | 780 | 32-65439 | 22 | #6543 / emb20 / 0,1024 1024x1024 | 日语 main |
| fnt_ja_maintext | 同上 | 780 | 32-65439 | 11 | #6544 / emb20 / 1536,512 512x512 | 日语 maintext |
| fnt_ja_papyrus | Tanuki Permanent Marker | 780 | 32-65439 | 18 | #6545 / emb20 / 1024,0 1024x512 | 日语 papyrus |
| fnt_ja_papyrus_btl | 同上 | 780 | 32-65439 | 13 | #6546 / emb20 / 1024,1024 512x512 | 日语 papyrus 战斗 |
| fnt_ja_plain | FTT-UDKakugoC80 M | 780 | 32-65439 | 12 | #6547 / emb20 / 1024,1536 512x512 | 日语 plain |
| fnt_ja_plainbig | FTT-UD角ゴC80 M | 3 | 32-12397 | 56 | #6548 / emb20 / 1536,1280 256x128 | 日语 plainbig |
| fnt_ja_plainsmall | FTT-UD角ゴC80 M | 181 | 32-12540 | 9 | #6549 / emb20 / 1792,1280 256x128 | 日语 plainsmall |

所有字体：charset=1（ANSI/默认），bold/italic 见 JSON，`ScaleX=ScaleY=1`，`LineHeight=0, Ascender=0`（引擎用 EmSize/字形 Offset 渲染）。反别名：英文字体 aa=0，部分 ja 字体 aa=1。

## 2. Glyph 结构样本（前 10 个）

### fnt_main（对话主字体候选，269 glyphs = 95 ASCII + 173 假名 + 1 DEL）
```
U+0020 ' ' src=198,122 6x32   off=0 shift=6
U+0021 '!'  src=188,122 8x26  off=2 shift=12
U+0022 '"'  src=220,122 10x16 off=0 shift=12
U+0023 '#'  src=104,2  14x26  off=0 shift=16
U+0024 '$'  src=184,2  12x30  off=0 shift=14
U+0025 '%'  src=88,2   14x26  off=0 shift=16
U+0026 '&'  src=136,2  14x26  off=0 shift=16
U+0027 '''  src=14,156 4x16  off=0 shift=6
U+0028 '('  src=178,122 8x26  off=0 shift=10
U+0029 ')'  src=158,122 8x26  off=0 shift=10
```
glyph 源坐标是**页绝对坐标**（落在该字体 TPI 区域 0,0+256x1024 内）。

### fnt_maintext（对话主字体候选 2，269 glyphs）
```
U+0020 ' ' src=79,81 3x16  off=0 shift=3
U+0021 '!'  src=73,81 4x13 off=1 shift=6
U+0022 '"'  src=92,81 5x8  off=0 shift=6
U+0023 '#'  src=60,2  7x13 off=0 shift=8
U+0024 '$'  src=105,2 6x15 off=0 shift=7
...
```

### fnt_ja_main CJK glyph 样本（证明引擎支持非 ASCII 大码点 glyph）
```
U+4E00 一  src=600,244 28x36 off=0 shift=28
U+4E03 七  src=632,244 28x36 off=0 shift=28
U+4E09 三  src=664,244 28x36 off=0 shift=28
U+4E0A 上  src=696,244 28x36 off=0 shift=28
U+4E0B 下  src=728,244 28x36 off=0 shift=28
U+4E0D 不  src=760,244 28x36 off=0 shift=28
```

## 3. GlyphInfo 字段全集（本 UTMT 0.9.1.2 / UndertaleModLib）

任务简报中的旧版字段名（TexturePage/GlyphInfo/EmittedSize/DisplayHeight/OffsetX/Shifting/TextureItem）**在本构建中均已不存在**，实际为：

```
UndertaleFont:
  Name, DisplayName (UndertaleString)
  Bold, Italic (bool)
  RangeStart (ushort), RangeEnd (uint)
  Charset, AntiAliasing (byte)
  EmSize (float), EmSizeIsFloat (bool)
  LineHeight (uint), Ascender (uint), AscenderOffset (int)
  ScaleX, ScaleY (float), SDFSpread (uint)
  Glyphs (UndertalePointerList<Glyph>)
  Texture (UndertaleTexturePageItem)      ← 旧名 TexturePage
  ProjectName/ProjectAssetType/ProjectExportable（UTMT 工程辅助字段）

UndertaleFont.Glyph（嵌套类，旧名 GlyphInfo）:
  Character (ushort)
  SourceX, SourceY, SourceWidth, SourceHeight (ushort)   ← 旧名 SourceW/H
  Offset (short), Shift (short)                          ← 旧名 Shifting
  UnknownAlwaysZero (short)
  Kerning (UndertaleSimpleListShort<GlyphKerning>)
  ※ 无 TextureItem 字段（GMS1 风格：每字体一个 Texture，glyph 无独立纹理项）

UndertaleFont.Glyph.GlyphKerning:
  Character (short), ShiftModifier (short)

UndertaleTexturePageItem:
  Name (UndertaleString，如 "PageItem 6531")
  SourceX, SourceY, SourceWidth, SourceHeight (ushort)   ← 在 emb 纹理中的区域
  TargetX, TargetY, TargetWidth, TargetHeight (ushort)
  BoundingWidth, BoundingHeight (ushort)
  TexturePage (UndertaleEmbeddedTexture)                 ← 指向所属页

UndertaleEmbeddedTexture:
  Name ("Texture 19"), IndexInGroup (int)
  TextureWidth/TextureHeight (int，未加载时为 0！真实尺寸在 TextureData)
  TextureData (TexData { Width, Height, FormatBZ2, FormatQOI, Image: GMImage })
  Scaled, GeneratedMips (uint), TextureExternal (bool), TextureLoaded (bool)
  TextureInfo (UndertaleTextureGroupInfo，本文件全部为 null)
```

## 4. 字体纹理页占用（8px 网格估算，p3b）

| 页 | 尺寸 | TPI 数 | 占用率 | 最大空闲矩形 |
|---|---|---|---|---|
| emb#18（小字体页） | 512x1024 | 63 | 49% | 496x480 @ (16,544) |
| **emb#19（英文字体页）** | 1024x1024 | 11 | 67% | **768x384 @ (256,640)** |
| **emb#20（日文字体页）** | 2048x2048 | 11 | 92% | **512x632 @ (1536,1416)** |

全文件 26 页，尺寸上限观测：最大 **2048x2048**（emb#14/20/23/25）。
emb#20 上有 `spr_fonts_ja_preload`（2x2 精灵，TPI#5785）——Mac 移植用精灵触发字体页预加载。

## 5. 各字体码点覆盖（由 fonts_dump.json 统计）

| 字体组 | ASCII | 假名 | CJK 汉字/全角 | 其他标点 |
|---|---|---|---|---|
| 英文 96-glyph 组（wingdings/small/plainbig/dmg/curs/comicsans/papyrus） | 95 | 0 | 0 | 1 (DEL) |
| 英文 269-glyph 组（main/maintext/plain） | 95 | 173 | 0 | 1 (DEL) |
| **fnt_ja_* 780-glyph 组**（6 个） | 95 | 173 | **488** | 24（‘’—“”…※ 等） |
| fnt_ja_curs (268) | 95 | 173 | 0 | 0 |
| fnt_ja_plainsmall (181) | 1 | 178 | 0 | 2 |

fnt_ja_main 已含 671 个 CJK 区 glyph：全假名 + 488 个日文汉字（新字体形，如 並/伝）+ 中文标点（，。「」等）。
完整清单见 `fnt_ja_main_cjk清单.txt`。**此集合远不够简体中文**（GB2312 一级 3755 字），且缺简体特有字形（如 习/东/语）。

原始数据：`fonts_dump.json`（每字体全部 glyph 的码点/坐标/宽高/offset/shift）。
