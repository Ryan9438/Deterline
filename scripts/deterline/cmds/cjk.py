"""CJK 中文字体注入域（O2 步 9：从 modify_save.py 1:1 平移，方案修订 2 cjk 项）。

CJK_TYPER_TABLE + pass1/pass2 CSX 模板（raw 三引号原样）+ cmd_cjk_font 五步管线 +
折行 util + 触发块生成器/cmd（B4 实证栈）。

模块路径修正（方案风险 #3 缓解）：tools/ 引用由原 `parent.parent`（单文件期
scripts/ 直下）改为包根解析 `parents[2]`（scripts/deterline/cmds/cjk.py →
scripts/）——已登记 tests/test_o2_step0.py::TestFileMigrationChecklist。

本域自带 _gml_escape/_csx_escape 定义（1:1 平移，域内裸调用绑定本地版——
与父版"cjk 块后定义覆盖全局"的有效语义一致；utmt 版与 cjk 版 _csx_escape
五 replace 语义等同，步 3 复核 20024 语料证明）。
跨模块一律模块属性形式：utmt./verify./errors.
"""

import subprocess
import sys
from pathlib import Path

from .. import errors, utmt
from . import verify

# typer → (spacing, writingxend)；spacing = writer 逐字推进常数（SCR_TEXTSETUP arg8）。
# 只收录经 B3/B4 实证或 SCR_TEXTTYPE 反编译核对过几何的 typer。
CJK_TYPER_TABLE = {
    31: (12, 9999),   # fnt_maintext, x+20 起步，无自动折行（B4 主臂实证）
    5: (8, 290),      # fnt_maintext, 标准对话（引擎按 writingxend 自动折行）
    3: (10, 100),     # fnt_curs, writingy 在框上缘外（设计性）
    2: (9, 190),      # fnt_plain
    68: (9, 500),     # fnt_plain, c_white
    30: (20, 9999),   # fnt_main, 大间距无折行
}


# pass1（只读）：dump 源字体行式元数据 + 共享纹理页 PNG 到 work_dir
_CJK_PASS1_CSX = r'''// C3b pass1 (READ-ONLY): dump source fonts metadata + shared texture page
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
string dumpDir = @"__WORKDIR__";
string[] srcNames = { "fnt_main", "fnt_maintext", "fnt_plain" };
try {
    // 幂等守卫（S6 页内栈）：ja_maintext 被共享表替换过（glyph 数 >1000）即已注入
    var jaTextChk = Data.Fonts.FirstOrDefault(f => f.Name != null && f.Name.Content == "fnt_ja_maintext");
    if (jaTextChk != null && jaTextChk.Glyphs.Count > 1000) {
        ScriptMessage("ERROR: CJK 页内栈已注入（fnt_ja_maintext glyph=" + jaTextChk.Glyphs.Count + "）——先 experiment-restore/undo 回滚");
        return;
    }
    var sb = new System.Text.StringBuilder();
    UndertaleEmbeddedTexture page = null;
    foreach (string nm in srcNames) {
        var f = Data.Fonts.FirstOrDefault(x => x.Name != null && x.Name.Content == nm);
        if (f == null || f.Texture == null) { ScriptMessage("ERROR: font not found: " + nm); return; }
        var tpi = f.Texture;
        var emb = tpi.TexturePage;
        if (emb == null || emb.TextureData == null) { ScriptMessage("ERROR: no texture page for " + nm); return; }
        if (page == null) { page = emb; }
        else if (page != emb) { ScriptMessage("ERROR: 源字体不在同一纹理页（MVP 仅支持共享页布局）"); return; }
        sb.AppendLine("PAGE " + nm + " " + tpi.SourceX + " " + tpi.SourceY + " " + tpi.SourceWidth + " " + tpi.SourceHeight
                      + " " + emb.TextureData.Width + " " + emb.TextureData.Height);
        sb.AppendLine("FONT " + nm + " " + f.EmSize + " " + (f.EmSizeIsFloat ? 1 : 0) + " " + f.Charset + " "
                      + f.AntiAliasing + " " + f.LineHeight + " " + f.Ascender + " " + f.AscenderOffset + " "
                      + f.RangeStart + " " + f.RangeEnd + " " + (f.Bold ? 1 : 0) + " "
                      + tpi.SourceX + " " + tpi.SourceY + " " + tpi.SourceWidth + " " + tpi.SourceHeight);
        foreach (var g in f.Glyphs) {
            string kern = "";
            foreach (var k in g.Kerning) kern += " " + k.Character + ":" + k.ShiftModifier;
            sb.AppendLine("GLYPH " + nm + " " + g.Character + " " + g.SourceX + " " + g.SourceY + " "
                          + g.SourceWidth + " " + g.SourceHeight + " " + g.Offset + " " + g.Shift + " "
                          + g.Kerning.Count + kern);
        }
    }
    File.WriteAllText(Path.Combine(dumpDir, "fonts.txt"), sb.ToString());
    using (var fs = File.Create(Path.Combine(dumpDir, "emb_page.png"))) {
        page.TextureData.Image.SavePng(fs);
    }
    // S6：另 dump emb20（ja 字体共享页）——页内重排换页（font_emb20_compose）的底图
    var tex20 = Data.EmbeddedTextures.FirstOrDefault(t => t.Name != null && t.Name.Content == "Texture 20");
    if (tex20 == null || tex20.TextureData == null) { ScriptMessage("ERROR: Texture 20 not found"); return; }
    using (var fs = File.Create(Path.Combine(dumpDir, "emb20_page.png"))) {
        tex20.TextureData.Image.SavePng(fs);
    }
    ScriptMessage("CJK_PASS1_OK fonts=" + srcNames.Length + " page=" + page.TextureData.Width + "x" + page.TextureData.Height
                  + " emb20=" + tex20.TextureData.Width + "x" + tex20.TextureData.Height);
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.GetType().Name + ": " + ex.Message);
}'''


# pass2（写入）：新 EmbeddedTexture×2 + TexturePageItem×3 + UndertaleFont×3
#              + scr_setfont 加 zh 分支（方案 B 唯一代码改动点）
_CJK_PASS2_CSX = r'''// C3b S6 pass2 (WRITE): 中文页内重排栈（B4 实证形态，AUDIT 报告 §九）
//   emb20 象限换页（页身份不变）+ fnt_ja_maintext 重指向 TPI#6543 + 共享表 4064 字形
//   + scr_setfont 单行映射（槽位判重）+ preload 无条件 prefetch
//   ⚠️ 守卫不能 Contains "newfont = fnt_ja_maintext;"（基线 ja 分支本就含，恒真陷阱）
using System;
using System.IO;
using System.Linq;
using UndertaleModLib.Util;   // GMImage.FromPng(byte[], bool verifyHeader)
string workDir = @"__WORKDIR__";
try {
    // ── 0) 幂等守卫（计数式：基线 ja 分支含 1 处 fnt_ja_maintext 映射）──
    var sfChk = GetDecompiledText("gml_Script_scr_setfont");
    int nMap = sfChk.Split(new[]{"newfont = fnt_ja_maintext;"}, StringSplitOptions.None).Length - 1;
    if (nMap > 1) { ScriptMessage("ERROR: CJK 映射已存在（n=" + nMap + "）——先回滚"); return; }
    var jaText = Data.Fonts.FirstOrDefault(f => f.Name != null && f.Name.Content == "fnt_ja_maintext");
    if (jaText == null) { ScriptMessage("ERROR: fnt_ja_maintext not found"); return; }
    if (jaText.Glyphs.Count > 1000) { ScriptMessage("ERROR: 共享表已注入（glyph=" + jaText.Glyphs.Count + "）"); return; }

    // ── 1) emb20 象限换页（页身份不变；换页底图已由 font_emb20_compose 离线合成并 --verify）──
    byte[] png20 = File.ReadAllBytes(Path.Combine(workDir, "emb20_page_new.png"));
    var img20 = GMImage.FromPng(png20, false);
    var tex20 = Data.EmbeddedTextures.FirstOrDefault(t => t.Name != null && t.Name.Content == "Texture 20");
    if (tex20 == null || tex20.TextureData == null || tex20.TextureData.Width != 2048) {
        ScriptMessage("ERROR: Texture 20 缺失或尺寸异常"); return;
    }
    tex20.TextureData.Image = img20;

    // ── 2) fnt_ja_maintext：TPI 重指向 #6543（(0,1024) 1024² 象限）+ 共享表 ──
    var tpi = Data.TexturePageItems.FirstOrDefault(t => t.SourceX == 0 && t.SourceY == 1024
                    && t.SourceWidth == 1024 && t.SourceHeight == 1024 && t.TexturePage == tex20);
    if (tpi == null) { ScriptMessage("ERROR: TPI#6543 not found"); return; }
    jaText.Texture = tpi;
    var spec = System.Text.Json.JsonDocument.Parse(
        File.ReadAllText(Path.Combine(workDir, "glyphs_inpage.json"))).RootElement;
    jaText.Glyphs.Clear();
    int n = 0;
    foreach (var ge in spec.GetProperty("glyphs").EnumerateArray()) {
        var g = new UndertaleFont.Glyph();
        g.Character = (ushort)ge[0].GetInt32();
        g.SourceX = (ushort)ge[1].GetInt32();
        g.SourceY = (ushort)ge[2].GetInt32();
        g.SourceWidth = (ushort)ge[3].GetInt32();
        g.SourceHeight = (ushort)ge[4].GetInt32();
        g.Offset = (short)ge[5].GetInt32();
        g.Shift = (short)ge[6].GetInt32();
        g.UnknownAlwaysZero = 0;
        jaText.Glyphs.Add(g);
        n++;
    }
    // 排序/去重不变量（RV-B）：引擎字形查找假定按码点有序
    var codes = jaText.Glyphs.Select(x => (int)x.Character).ToList();
    if (!codes.SequenceEqual(codes.OrderBy(c => c)) || codes.Distinct().Count() != codes.Count) {
        ScriptMessage("ERROR: glyph 表排序/去重不变量破坏"); return;
    }

    // ── 3) scr_setfont 单行映射（唯一代码改动点；计数判重见守卫）──
    var sf = Data.Code.ByName("gml_Script_scr_setfont");
    string sgml = GetDecompiledText("gml_Script_scr_setfont");
    int anchor = sgml.IndexOf("draw_set_font(newfont);");
    if (anchor < 0) { ScriptMessage("ERROR: setfont anchor missing"); return; }
    sgml = sgml.Insert(anchor, "// CJK_MAP\nif (newfont == fnt_maintext) { newfont = fnt_ja_maintext; }\n");
    var ig1 = new CodeImportGroup(Data) { MainThreadAction = MainThreadAction };
    ig1.QueueReplace(sf, sgml);
    ig1.Import();

    // ── 4) preload 无条件 prefetch（既有页）──
    var pc = Data.Code.ByName("gml_Script_scr_preload_textures");
    string pgml = GetDecompiledText("gml_Script_scr_preload_textures");
    int pcAnchor = pgml.IndexOf("sprite_prefetch(spr_maincharad);");
    if (pcAnchor < 0) { ScriptMessage("ERROR: preload anchor missing"); return; }
    int nPre = pgml.Split(new[]{"sprite_prefetch(spr_fonts_ja_preload);"}, StringSplitOptions.None).Length - 1;
    if (nPre > 1 || pgml.Contains("// CJK_UNCOND")) { ScriptMessage("ERROR: preload 已有无条件分支（n=" + nPre + "）"); return; }
    pgml = pgml.Insert(pcAnchor, "sprite_prefetch(spr_fonts_ja_preload); // CJK_UNCOND\n");
    var ig2 = new CodeImportGroup(Data) { MainThreadAction = MainThreadAction };
    ig2.QueueReplace(pc, pgml);
    ig2.Import();

    ScriptMessage("CJK_PASS2_OK glyphs=" + n + " tpi=(0,1024) setfont_map=1 preload_uncond=1");
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.GetType().Name + ": " + ex.Message);
}''' 


def _build_cjk_pass1_csx(work_dir: str) -> str:
    """pass1 CSX（work_dir 占位替换；纯函数，供 golden 钉形）。"""
    return _CJK_PASS1_CSX.replace("__WORKDIR__", work_dir)


def _build_cjk_pass2_csx(work_dir: str) -> str:
    """pass2 CSX（work_dir 占位替换；纯函数，供 golden 钉形）。"""
    return _CJK_PASS2_CSX.replace("__WORKDIR__", work_dir)


def cmd_cjk_font(game_file: Path, build_dir: Path,
                 work_dir: Path = None, skip_pass1: bool = False) -> bool:
    """C3b S6：中文页内重排注入（B4 实证栈，AUDIT 报告 §九）。五步管线：

    1. pass1（只读 CSX）：dump 源字体元数据 + emb19 页 + emb20 页 PNG → work_dir
    2. tools/font_cjk_atlas.py --mode in-page：ASCII 拷贝 + CJK 排版 → 1024² 共享图集
    3. tools/font_emb20_compose.py --verify：emb20 象限合成（页身份不变；像素 diff 自证）
    4. pass2（写 CSX，默认沙箱）：emb20 换页 + fnt_ja_maintext@TPI6543 共享表 4064 字形
       + scr_setfont 单行映射（计数守卫）+ preload 无条件 prefetch
    5. verify-code gml_Script_scr_setfont（域F 教训：代码改动必须字节级体检）

    build_dir 为 tools/font_cjk_build.py 的输出（meta.json/glyphs.json/cjk_page_*.png）。
    约束：不新增字体资产（fonts=20 不变）；不新增纹理页（约束④：新页不被字体渲染器加载）。
    对话触发块生成见 cjk-trigger 命令；游戏内渲染已由 B4 boot 实证（`* B4中文测试ABC`）。
    """
    import json as _json
    work_dir = work_dir or (game_file.parent / "cjk_work")
    work_dir.mkdir(parents=True, exist_ok=True)

    # 1) build_dir 校验
    meta_path = build_dir / "meta.json"
    if not meta_path.exists():
        raise RuntimeError(f"缺 {meta_path}——先运行 tools/font_cjk_build.py 生成字形页")
    meta = _json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("px") != 12 or meta.get("cell") != 13:
        raise RuntimeError(f"build_dir 度量不符（px={meta.get('px')} cell={meta.get('cell')}，"
                           f"需 12/13）——重新运行 font_cjk_build.py")
    if not (build_dir / "glyphs.json").exists() or not (build_dir / "cjk_page_0.png").exists():
        raise RuntimeError(f"build_dir 缺 glyphs.json/cjk_page_*.png: {build_dir}")

    # 2) pass1（只读）
    if not skip_pass1:
        out = utmt._run_utmt(_build_cjk_pass1_csx(str(work_dir)), game_file, save=False)
        if "CJK_PASS1_OK" not in out:
            raise RuntimeError(f"pass1 失败（未注入任何内容）：\\n{out}")

    # 3) 共享图集构建（in-page 模式，纯 Python，确定性）
    atlas_tool = Path(__file__).resolve().parents[2] / "tools" / "font_cjk_atlas.py"
    r = subprocess.run(
        [sys.executable, str(atlas_tool),
         "--build-dir", str(build_dir), "--pass1-dir", str(work_dir),
         "--out-dir", str(work_dir), "--mode", "in-page"],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("图集构建失败：\\n" + r.stdout + r.stderr)
    print(r.stdout.strip())

    # 4) emb20 象限合成（像素 diff 自证；越界变化 → 硬失败）
    compose_tool = Path(__file__).resolve().parents[2] / "tools" / "font_emb20_compose.py"
    r = subprocess.run(
        [sys.executable, str(compose_tool),
         "--emb20", str(work_dir / "emb20_page.png"),
         "--atlas", str(work_dir / "font_atlas_inpage.png"),
         "--out", str(work_dir / "emb20_page_new.png"), "--verify"],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("emb20 合成失败：\\n" + r.stdout + r.stderr)
    print(r.stdout.strip())

    # 5) pass2（写，默认沙箱）
    out = utmt._run_utmt(_build_cjk_pass2_csx(str(work_dir)), game_file, save=True)
    if "CJK_PASS2_OK" not in out:
        raise RuntimeError(f"pass2 失败（沙箱未变更/回退）：\\n{out}")

    # 6) scr_setfont 字节级体检（WARN/不稳定 → 返回 False）
    print("→ verify-code gml_Script_scr_setfont（域F 协议）")
    return verify.cmd_verify_code(game_file, "gml_Script_scr_setfont")


def cjk_wrap_text(text: str, chars_per_line: int) -> str:
    """按 writer 均匀步距模型折行：typer 的 spacing 对每个字符一视同仁
    （Draw_0 逐字符 letterx += spacing，空格也占一格），故一格 = 一字符。

    规则：
    - ASCII 词 [A-Za-z0-9'] 整体打包不切分（超长词硬切）；CJK 逐字可断
    - 断行处空格吞掉（rstrip），行中空格占格
    - 已有的 "&"（writer 硬换行）重置行计数；行间插 "&"（SCR_NEWLINE 标记）
    - 短于限宽原样返回
    """
    if chars_per_line <= 0 or not text:
        return text
    out = []
    for seg in text.split("&"):
        if seg == "":
            out.append("")               # 保留显式空行（"&&"）
            continue
        # 词元化：ASCII 词整体 / 单个非 ASCII 字符 / 空格
        tokens = []
        i = 0
        while i < len(seg):
            ch = seg[i]
            if ch == " ":
                tokens.append(" ")
                i += 1
            elif ch.isascii() and (ch.isalnum() or ch == "'"):
                j = i
                while j < len(seg) and seg[j].isascii() and (seg[j].isalnum() or seg[j] == "'"):
                    j += 1
                tokens.append(seg[i:j])
                i = j
            else:
                tokens.append(ch)
                i += 1
        cur = ""
        for tok in tokens:
            if tok == " ":
                if cur:
                    cur += tok       # 行尾空格暂挂，落行时 rstrip
                continue
            if len(tok) > chars_per_line:
                if cur:
                    out.append(cur.rstrip(" "))
                w = tok
                while len(w) > chars_per_line:
                    out.append(w[:chars_per_line])
                    w = w[chars_per_line:]
                cur = w
                continue
            if len(cur) + len(tok) <= chars_per_line:   # cur 含试探性尾随空格
                cur += tok
            else:
                out.append(cur.rstrip(" "))
                cur = tok
        if cur:
            out.append(cur.rstrip(" "))
    return "&".join(out)


def _gml_escape(text: str) -> str:
    """GML 字符串字面量转义：反斜杠 1→2、双引号 → \"（GML 层）。"""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _csx_escape(text: str) -> str:
    """C# 常规字符串字面量转义：反斜杠/双引号/真实换行（CSX 宿主层）。

    嵌套次序：原始文本 → _gml_escape（GML 层）→ _csx_escape（C# 层）。
    C# 反转义后即得 GML 转义形态，GML 反转义后即得原始文本。
    """
    return (text.replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t"))


def _build_cjk_trigger_csx(room_name: str, obj_name: str, x: int, y: int,
                           typer: int, text: str, wrap: bool = True,
                           width_room_px: int = None) -> str:
    """生成单个 CJK 对话触发块 CSX（追加到 obj_<名>_Step_1）。

    触发块形态 = B4 实证全形态（缺一即幽灵框/空框，见 AUDIT §八/§九）：
    msc=0 / typer / facechoice=3 / faceemotion=0 / msg[0] 带 "/%%" 终止符 /
    msg[1]="%%%" / id 守卫三连 / distance<60。
    typer 必须在 CJK_TYPER_TABLE 内（几何未核对的 typer 拒绝）。
    位置硬校验：0 <= x < 320（房间宽 320——越界即物理不可触发，B2 教训）。
    """
    if typer not in CJK_TYPER_TABLE:
        raise RuntimeError(f"typer {typer} 几何未核对（合法值："
                           f"{sorted(CJK_TYPER_TABLE)}）——查 SCR_TEXTTYPE 后再加表")
    if not (0 <= x < 320 and 0 <= y < 480):
        raise RuntimeError(f"触发位 ({x},{y}) 越界——房间 320×480，越界即不可触发"
                           f"（B2 教训：报告 §九）")
    if not text or not text.strip():
        raise RuntimeError("text 为空")
    if "\n" in text or "\r" in text:
        raise RuntimeError("text 含真实换行——多行对话请用 writer 硬换行标记 & 或拆多条触发块")
    if "\t" in text:
        raise RuntimeError("text 含制表符——writer 无此字形，请改空格")
    # 终止符摘出（折行不得劈开 "/%%"），中部 writer 专用字符校验
    terminator = ""
    if text.endswith("/%%"):
        text, terminator = text[:-3], "/%%"
    for ch in ("/", "%"):
        if ch in text:
            raise RuntimeError(f"text 含 writer 专用字符 {ch!r}（halt/翻页语义）——"
                               f"请改写文本（百分号用中文表述）")
    if wrap:
        spacing, wxend = CJK_TYPER_TABLE[typer]
        if width_room_px is None:
            # typer31 无引擎折行（wxend=9999）→ 默认按标准框宽 202（view+290 − view+88）
            width_room_px = 202
        if 0 < wxend < 9000:                       # 引擎会按 wxend 二次折行 → 预折行不超它
            width_room_px = min(width_room_px, wxend)
        text = cjk_wrap_text(text, max(1, width_room_px // spacing))
    text = text + terminator
    if not text.endswith("/%%"):
        text = text + "/%%"
    gml_text = _csx_escape(_gml_escape(text))
    step_name = f"gml_Object_{obj_name}_Step_1"
    return f'''// C3b S6 cjk-trigger：CJK 对话触发块（B4 实证全形态）
using System;
using System.Linq;
try {{
    var room = Data.Rooms.First(r => r.Name.Content == "{room_name}");
    var obj = Data.GameObjects.First(o => o.Name.Content == "{obj_name}");
    string stepName = "{step_name}";
    var stepCode = Data.Code.ByName(stepName);
    string tgml = GetDecompiledText(stepName);
    if (tgml.Contains("CJK_TRIGGER")) {{ ScriptMessage("ERROR: CJK 触发块已存在——先回滚"); return; }}
    // 幂等守卫（计数式）：ja_maintext 共享表未注入则拒绝（触发块依赖 CJK 栈）
    var jaText = Data.Fonts.FirstOrDefault(f => f.Name != null && f.Name.Content == "fnt_ja_maintext");
    if (jaText == null || jaText.Glyphs.Count <= 1000) {{
        ScriptMessage("ERROR: CJK 页内栈未注入——先运行 cjk-font"); return;
    }}
    uint iid = Data.GeneralInfo.LastObj;
    Data.GeneralInfo.LastObj = iid + 1;
    var inst = new UndertaleRoom.GameObject();
    inst.InstanceID = iid;
    inst.X = {x}; inst.Y = {y};
    inst.ObjectDefinition = obj;
    room.GameObjects.Add(inst);
    string block = ""
        + "if (id == " + iid + " && !instance_exists(obj_dialoguer) && !instance_exists(OBJ_WRITER) && !instance_exists(obj_choicer))\\n"
        + "{{\\n"
        + "    if (distance_to_object(obj_mainchara) < 60)\\n"
        + "    {{\\n"
        + "        global.msc = 0;\\n"
        + "        global.typer = {typer};\\n"
        + "        global.facechoice = 3;\\n        global.faceemotion = 0;\\n"
        + "        global.msg[0] = \\"{gml_text}\\";\\n"
        + "        global.msg[1] = \\"%%%\\";\\n"
        + "        instance_create(0, 0, obj_dialoguer);\\n"
        + "    }}\\n"
        + "}}\\n"
        + "// CJK_TRIGGER\\n";
    tgml = tgml + "\\n" + block;
    var ig = new CodeImportGroup(Data) {{ MainThreadAction = MainThreadAction }};
    ig.QueueReplace(stepCode, tgml);
    ig.Import();
    ScriptMessage("CJK_TRIGGER_OK id=" + iid + " typer={typer} @({x},{y})");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.GetType().Name + ": " + ex.Message);
}}'''


def cmd_cjk_trigger(game_file: Path, room_name: str, obj_name: str, x: int, y: int,
                    typer: int, text: str, wrap: bool = True,
                    width_room_px: int = None) -> bool:
    """C3b S6：注入单个 CJK 对话触发块（默认沙箱）+ 触发后体检。"""
    csx = _build_cjk_trigger_csx(room_name, obj_name, x, y, typer, text, wrap, width_room_px)
    out = utmt._run_utmt(csx, game_file, save=True)
    if "CJK_TRIGGER_OK" not in out:
        raise RuntimeError(f"cjk-trigger 失败（沙箱未变更/回退）：\\n{out}")
    print(out.strip().splitlines()[-1])
    step_name = f"gml_Object_{obj_name}_Step_1"
    print(f"→ verify-code {step_name}（域F 协议）")
    return verify.cmd_verify_code(game_file, step_name)
