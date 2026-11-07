# font_atlas 测试夹具（来源注释）

tests/test_font_atlas.py 用本目录夹具驱动 `tools/font_cjk_atlas.py` 的
`build_atlases` / `build_inpage_atlas`，钉住 glyph 表不变量（RV-B）。
build/ 目录被 .gitignore 排除，故把最小夹具复制入库。生成日期 2026-11-07，
基线 HEAD d74fa63。

## font_cjk_pass1/（原样复制，未做任何修改）

- `fonts.txt`：复制自 `build/font_cjk_pass1/fonts.txt`（cmd_cjk_font pass1 的
  dump，行式 FONT/GLYPH/PAGE/EMBOK 格式，含 fnt_main / fnt_maintext / fnt_plain
  三个源字体的 ASCII 度量）。
- `emb_page.png`：复制自 `build/font_cjk_pass1/emb_page.png`（68KB，源字体
  嵌入纹理页，ASCII 字形像素来源）。

## font_cjk/（合成子集，见下方生成方式）

- `glyphs.json`：build/font_cjk/glyphs.json 的子集 = 全部 95 个 ASCII 条目
  （code 0x20-0x7E，用于钉住"ASCII 不从 build 集取、重复会污染查找"的过滤
  不变量）+ 前 200 个非 ASCII 条目（code > 0x7E，Fusion Pixel 12px）。
  非 ASCII 条目的 x/y 已重映射到 16px 网格（(i%32)*16, (i//32)*16），
  其余字段（code/w/h/offset/advance）保持原值。
- `cjk_page_0.png`：512x512 合成页。生成方式：从真实
  `build/font_cjk/cjk_page_0.png` 把上述 200 个非 ASCII 字形的位图块按
  重映射后的坐标裁剪粘贴（像素即真实 Fusion 字形，仅页内布局压缩），
  其余区域透明。

## 重新生成方式（如需更新子集）

```bash
python3 - <<'PY'
import json
from PIL import Image
src = json.load(open('build/font_cjk/glyphs.json', encoding='utf-8'))
ascii_entries = [g for g in src if g['code'] <= 0x7E]
nonascii = [g for g in src if g['code'] > 0x7E][:200]
for i, g in enumerate(nonascii):
    g['x'] = (i % 32) * 16
    g['y'] = (i // 32) * 16
page_src = Image.open('build/font_cjk/cjk_page_0.png').convert('RGBA')
page = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
for g in nonascii:
    if g['w']:
        t = page_src.crop((g['x'], g['y'], g['x']+g['w'], g['y']+g['h']))
        page.paste(t, (g['x'], g['y']), t)
json.dump(ascii_entries + nonascii,
          open('tests/fixtures/font_atlas/font_cjk/glyphs.json', 'w', encoding='utf-8'),
          ensure_ascii=False)
page.save('tests/fixtures/font_atlas/font_cjk/cjk_page_0.png')
PY
```

注意：重生成会改变夹具字节，从而改变 test_font_atlas 的像素级断言目标
（不变量本身不受影响）。build/ 是产物目录，夹具入库后即与 build/ 解耦。
