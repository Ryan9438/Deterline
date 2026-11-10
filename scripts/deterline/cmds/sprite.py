"""精灵/纹理域命令（O2 步 7：从 modify_save.py 1:1 平移，方案 §1.2 sprite/texture 项）。

sprite/texture 导出替换全家（含 obj-get/obj-set-sprite）。跨模块一律模块属性
形式：utmt./state./errors.（cmd_texture_replace 的写入回执读 state.SANDBOX_
ACTIVE——旗标单点纪律）。PIL 为函数内局部导入（1:1 保留）。
"""

import os
import subprocess
import sys
from pathlib import Path

from .. import errors, paths, state, utmt

def cmd_sprite_list(game_file: Path, limit: int) -> None:
    """List all sprites with name, dimensions, frame count."""
    csx = f'''
int limit = {limit};
int count = 0;
for (int i = 0; i < Data.Sprites.Count && count < limit; i++) {{
    var spr = Data.Sprites[i];
    string fcount = (spr.Textures != null) ? spr.Textures.Count.ToString() : "0";
    string stype = spr.IsSpecialType ? spr.SSpriteType.ToString() : "Normal";
    ScriptMessage(spr.Name.Content + " | " + spr.Width + "x" + spr.Height + " | frames=" + fcount + " | type=" + stype);
    count++;
}}
ScriptMessage("(total: " + Data.Sprites.Count + " sprites, showing " + count + ")");
'''
    out = utmt._run_utmt(csx, game_file, save=False)
    for line in utmt._parse_msg(out):
        print(line)


def cmd_sprite_search(game_file: Path, query: str, limit: int) -> None:
    """Search sprites by name."""
    esc = utmt._csx_escape(query)
    csx = f'''
int limit = {limit};
int found = 0;
for (int i = 0; i < Data.Sprites.Count && found < limit; i++) {{
    var spr = Data.Sprites[i];
    if (spr.Name.Content.IndexOf("{esc}", StringComparison.OrdinalIgnoreCase) >= 0) {{
        string fcount = (spr.Textures != null) ? spr.Textures.Count.ToString() : "0";
        ScriptMessage(spr.Name.Content + " | " + spr.Width + "x" + spr.Height + " | frames=" + fcount);
        found++;
    }}
}}
if (found == 0) {{
    ScriptMessage("(no matching sprites)");
}} else {{
    ScriptMessage("(found " + found + " sprites)");
}}
'''
    out = utmt._run_utmt(csx, game_file, save=False)
    lines = utmt._parse_msg(out)
    for line in lines:
        print(line)
    utmt._fail_if_no_match(lines, "search-sprite", query)


def cmd_obj_get(game_file: Path, obj_name: str) -> None:
    """Show detailed info about a game object, including its sprite."""
    esc = utmt._csx_escape(obj_name)
    csx = f'''
var obj = Data.GameObjects.ByName("{esc}");
if (obj == null) {{
    obj = Data.GameObjects.ByName("{esc}", true);
}}
if (obj == null) {{
    string query = "{esc}";
    int first = -1;
    int count = 0;
    for (int o = 0; o < Data.GameObjects.Count; o++) {{
        string on = Data.GameObjects[o].Name.Content;
        if (on.IndexOf(query, StringComparison.OrdinalIgnoreCase) >= 0) {{
            if (first < 0) first = o;
            count++;
        }}
    }}
    if (first >= 0) {{
        obj = Data.GameObjects[first];
        if (count > 1) ScriptMessage("(found " + count + " matches, using: " + obj.Name.Content + ")");
    }}
}}
if (obj == null) {{
    ScriptMessage("ERROR: Object not found: {esc}");
    string suggest = "";
    int found = 0;
    for (int o = 0; o < Data.GameObjects.Count && found < 5; o++) {{
        string on = Data.GameObjects[o].Name.Content;
        if (on.IndexOf("{esc}", StringComparison.OrdinalIgnoreCase) >= 0 ||
            "{esc}".IndexOf(on, StringComparison.OrdinalIgnoreCase) >= 0) {{
            suggest += (found > 0 ? ", " : "") + on;
            found++;
        }}
    }}
    if (found > 0) ScriptMessage("HINT: Did you mean: " + suggest);
    return;
}}
ScriptMessage("=== " + obj.Name.Content + " ===");
ScriptMessage("Sprite: " + (obj.Sprite?.Name?.Content ?? "(none)"));
ScriptMessage("Sprite Size: " + (obj.Sprite?.Width ?? 0) + "x" + (obj.Sprite?.Height ?? 0));
ScriptMessage("Visible: " + obj.Visible + " | Solid: " + obj.Solid);
ScriptMessage("Depth: " + obj.Depth + " | Persistent: " + obj.Persistent);
ScriptMessage("TextureMask: " + (obj.TextureMaskId?.Name?.Content ?? "(none)"));
ScriptMessage("Physics: " + obj.UsesPhysics);
// Full inheritance chain (walk ParentId to root)
var chainNames = new List<string>();
var chainCur = obj;
int chainGuard = 0;
bool nativeInteractable = false;
while (chainCur != null && chainGuard < 30)
{{
    string cn = chainCur.Name?.Content ?? "(unknown)";
    chainNames.Add(cn);
    if (cn == "obj_interactable" || cn == "obj_readablesolid") nativeInteractable = true;
    chainCur = chainCur.ParentId;
    chainGuard++;
}}
ScriptMessage("Parent Chain: " + string.Join(" → ", chainNames));
if (nativeInteractable)
{{
    ScriptMessage("WARN: 原生交互对象 (继承 obj_readablesolid/obj_interactable)");
    ScriptMessage("     该对象有原生 Z 键/触碰交互系统 (myinteract → alarm[0] → Alarm_0 默认对话)。");
    ScriptMessage("     用 myinteract 做距离触发会与默认对话重叠 → 改用 flag 状态机 + 守卫 Alarm_0，");
    ScriptMessage("     或直接用 npc-dialogue / guard-npc-alarm 命令。");
}}
int evtCount = 0;
for (int e = 0; e < obj.Events.Count; e++) {{
    var evtList = obj.Events[e];
    if (evtList != null && evtList.Count > 0) {{
        evtCount += evtList.Count;
    }}
}}
ScriptMessage("Events: " + evtCount + " total");
'''
    out = utmt._run_utmt(csx, game_file, save=False)
    for line in utmt._parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("HINT:"):
            print(line, file=sys.stderr)
        else:
            print(line)


def cmd_obj_set_sprite(game_file: Path, obj_name: str, sprite_name: str) -> None:
    """Change the sprite reference of a game object."""
    esc_obj = utmt._csx_escape(obj_name)
    esc_spr = utmt._csx_escape(sprite_name)
    csx = f'''
var obj = Data.GameObjects.ByName("{esc_obj}");
if (obj == null) {{
    obj = Data.GameObjects.ByName("{esc_obj}", true);
}}
if (obj == null) {{
    string query = "{esc_obj}";
    int first = -1;
    int count = 0;
    for (int o = 0; o < Data.GameObjects.Count; o++) {{
        string on = Data.GameObjects[o].Name.Content;
        if (on.IndexOf(query, StringComparison.OrdinalIgnoreCase) >= 0) {{
            if (first < 0) first = o;
            count++;
        }}
    }}
    if (first >= 0) {{
        obj = Data.GameObjects[first];
        if (count > 1) ScriptMessage("(found " + count + " matches, using: " + obj.Name.Content + ")");
    }}
}}
if (obj == null) {{
    ScriptMessage("ERROR: Object not found: {esc_obj}");
    string suggest = "";
    int found = 0;
    for (int o = 0; o < Data.GameObjects.Count && found < 5; o++) {{
        string on = Data.GameObjects[o].Name.Content;
        if (on.IndexOf("{esc_obj}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            suggest += (found > 0 ? ", " : "") + on;
            found++;
        }}
    }}
    if (found > 0) ScriptMessage("HINT: Did you mean: " + suggest);
    return;
}}
var spr = Data.Sprites.ByName("{esc_spr}");
if (spr == null) {{
    spr = Data.Sprites.ByName("{esc_spr}", true);
}}
if (spr == null) {{
    string query = "{esc_spr}";
    int first = -1;
    int count = 0;
    for (int s = 0; s < Data.Sprites.Count; s++) {{
        string sn = Data.Sprites[s].Name.Content;
        if (sn.IndexOf(query, StringComparison.OrdinalIgnoreCase) >= 0) {{
            if (first < 0) first = s;
            count++;
        }}
    }}
    if (first >= 0) {{
        spr = Data.Sprites[first];
        if (count > 1) ScriptMessage("(found " + count + " sprites, using: " + spr.Name.Content + ")");
    }}
}}
if (spr == null) {{
    ScriptMessage("ERROR: Sprite not found: {esc_spr}");
    string suggest = "";
    int found = 0;
    for (int s = 0; s < Data.Sprites.Count && found < 5; s++) {{
        string sn = Data.Sprites[s].Name.Content;
        if (sn.IndexOf("{esc_spr}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            suggest += (found > 0 ? ", " : "") + sn;
            found++;
        }}
    }}
    if (found > 0) ScriptMessage("HINT: Did you mean: " + suggest);
    return;
}}
string oldSpr = obj.Sprite?.Name?.Content ?? "(none)";
obj.Sprite = spr;
ScriptMessage("OK: " + obj.Name.Content + ": " + oldSpr + " → " + spr.Name.Content);
ScriptMessage("(Sprite size: " + spr.Width + "x" + spr.Height + ")");
'''
    out = utmt._run_utmt(csx, game_file, save=True)
    for line in utmt._parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)
        else:
            print(line)


def cmd_texture_list(game_file: Path, limit: int) -> None:
    """List all embedded textures (TXTR)."""
    csx = f'''
int limit = {limit};
for (int i = 0; i < Data.EmbeddedTextures.Count && i < limit; i++) {{
    var t = Data.EmbeddedTextures[i];
    int w = t.TextureData?.Width ?? 0;
    int h = t.TextureData?.Height ?? 0;
    string texName = t.Name?.Content ?? "(unnamed)";
    ScriptMessage(texName + " | " + w + "x" + h + " | external=" + t.TextureExternal);
}}
ScriptMessage("(total: " + Data.EmbeddedTextures.Count + " textures)");
'''
    out = utmt._run_utmt(csx, game_file, save=False)
    for line in utmt._parse_msg(out):
        print(line)


def _export_sprite_json(game_file: Path, sprite_name: str) -> None:
    """Export sprite metadata as JSON to stderr."""
    esc = utmt._csx_escape(sprite_name)
    csx = f'''
var spr = Data.Sprites.ByName("{esc}");
if (spr == null) {{
    spr = Data.Sprites.ByName("{esc}", true);
}}
if (spr == null) return;
string frames = "[";
for (int i = 0; i < (spr.Textures?.Count ?? 0); i++) {{
    if (i > 0) frames += ",";
    var t = spr.Textures[i]?.Texture;
    if (t != null) {{
        frames += "{{";
        frames += "\\"frame\\":\\"" + i + "\\",";
        frames += "\\"src\\":\\"" + t.SourceX + "," + t.SourceY + " " + t.SourceWidth + "x" + t.SourceHeight + "\\",";
        frames += "\\"target\\":\\"" + t.TargetX + "," + t.TargetY + " " + t.TargetWidth + "x" + t.TargetHeight + "\\",";
        frames += "\\"bound\\":\\"" + t.BoundingWidth + "x" + t.BoundingHeight + "\\",";
        frames += "\\"page\\":\\"" + (t.TexturePage?.Name?.Content ?? "?") + "\\"";
        frames += "}}";
    }}
}}
frames += "]";
ScriptMessage("JSON:" + "{{");
ScriptMessage("JSON:  \\"name\\": \\"" + spr.Name.Content + "\\",");
ScriptMessage("JSON:  \\"width\\": " + spr.Width + ",");
ScriptMessage("JSON:  \\"height\\": " + spr.Height + ",");
ScriptMessage("JSON:  \\"frames\\": " + (spr.Textures?.Count ?? 0) + ",");
ScriptMessage("JSON:  \\"tex_entries\\": " + frames);
ScriptMessage("JSON:}}");
'''
    out = utmt._run_utmt(csx, game_file, save=False)
    for line in utmt._parse_msg(out):
        if line.startswith("JSON:"):
            print(line[5:])  # print JSON fragment to stdout


def cmd_sprite_export(game_file: Path, sprite_name: str, output: str, frame: int = -1) -> None:
    """Export sprite frame(s) as PNG.

    If frame is -1, export all frames to output directory.
    If frame >= 0, export single frame to output path.
    """
    esc = utmt._csx_escape(sprite_name)
    esc_path = utmt._csx_escape(output)
    csx = f'''
using UndertaleModLib.Util;
using ImageMagick;
var spr = Data.Sprites.ByName("{esc}");
if (spr == null) {{
    spr = Data.Sprites.ByName("{esc}", true);
}}
if (spr == null) {{
    int first = -1;
    int count = 0;
    for (int s = 0; s < Data.Sprites.Count; s++) {{
        var sn = Data.Sprites[s].Name.Content;
        if (sn.IndexOf("{esc}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            if (first < 0) first = s;
            count++;
        }}
    }}
    if (first >= 0) spr = Data.Sprites[first];
}}
if (spr == null) {{
    ScriptMessage("ERROR: Sprite not found: {esc}");
    return;
}}
if (spr.Textures == null || spr.Textures.Count == 0) {{
    ScriptMessage("ERROR: Sprite has no textures");
    return;
}}
int frameNum = {frame};
int totalFrames = spr.Textures.Count;
var worker = new TextureWorker();
if (frameNum < 0) {{
    string outDir = "{esc_path}";
    System.IO.Directory.CreateDirectory(outDir);
    for (int i = 0; i < totalFrames; i++) {{
        var entry = spr.Textures[i];
        if (entry?.Texture == null) continue;
        string fp = System.IO.Path.Combine(outDir, spr.Name.Content + "_" + i + ".png");
        worker.ExportAsPNG(entry.Texture, fp);
    }}
    ScriptMessage("OK: Exported " + totalFrames + " frames to " + outDir);
}} else {{
    if (frameNum >= totalFrames) {{
        ScriptMessage("ERROR: Frame " + frameNum + " out of range (0-" + (totalFrames - 1) + ")");
        return;
    }}
    var entry = spr.Textures[frameNum];
    if (entry?.Texture == null) {{
        ScriptMessage("ERROR: Frame " + frameNum + " has no texture");
        return;
    }}
    worker.ExportAsPNG(entry.Texture, "{esc_path}");
    ScriptMessage("OK: Exported " + spr.Name.Content + "[" + frameNum + "] → {esc_path}");
}}
'''
    out = utmt._run_utmt(csx, game_file, save=False)
    for line in utmt._parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        else:
            print(line)


def cmd_sprite_replace(game_file: Path, sprite_name: str, png_path: str, frame: int = 0, all_frames: bool = False) -> None:
    """Replace a sprite frame's texture with a PNG file.

    If all_frames is True, replace all frames with the same PNG.
    """
    esc = utmt._csx_escape(sprite_name)
    esc_png = utmt._csx_escape(png_path)
    all_flag = "true" if all_frames else "false"
    csx = f'''
using UndertaleModLib.Util;
using ImageMagick;
var spr = Data.Sprites.ByName("{esc}");
if (spr == null) {{
    spr = Data.Sprites.ByName("{esc}", true);
}}
if (spr == null) {{
    int first = -1;
    int count = 0;
    for (int s = 0; s < Data.Sprites.Count; s++) {{
        var sn = Data.Sprites[s].Name.Content;
        if (sn.IndexOf("{esc}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            if (first < 0) first = s;
            count++;
        }}
    }}
    if (first >= 0) spr = Data.Sprites[first];
}}
if (spr == null) {{
    ScriptMessage("ERROR: Sprite not found: {esc}");
    return;
}}
string pngPath = "{esc_png}";
if (!System.IO.File.Exists(pngPath)) {{
    ScriptMessage("ERROR: File not found: " + pngPath);
    return;
}}
byte[] pngBytes = System.IO.File.ReadAllBytes(pngPath);
bool allMode = {all_flag};
int totalFrames = spr.Textures?.Count ?? 0;
int frameNum = {frame};
int startFrame = allMode ? 0 : frameNum;
int endFrame = allMode ? totalFrames - 1 : frameNum;
int replaced = 0;
for (int f = startFrame; f <= endFrame; f++) {{
    if (spr.Textures == null || spr.Textures.Count <= f) continue;
    var entry = spr.Textures[f];
    if (entry?.Texture?.TexturePage == null) continue;
    var texItem = entry.Texture;
    var embeddedTex = texItem.TexturePage;
    try {{
        using var editImg = new MagickImage(pngBytes);
        uint sw = texItem.SourceWidth;
        uint sh = texItem.SourceHeight;
        bool resized = false;
        if (editImg.Width != sw || editImg.Height != sh) {{
            ScriptMessage("Resize[" + f + "]: " + editImg.Width + "x" + editImg.Height + " -> " + sw + "x" + sh);
            editImg.InterpolativeResize(sw, sh, PixelInterpolateMethod.Bilinear);
            resized = true;
        }}
        var worker = new TextureWorker();
        var pageImg = worker.GetEmbeddedTexture(embeddedTex);
        lock (pageImg) {{
            pageImg.Composite(editImg, (int)texItem.SourceX, (int)texItem.SourceY, CompositeOperator.Copy);
        }}
        using var ms = new System.IO.MemoryStream();
        pageImg.Write(ms, MagickFormat.Png);
        embeddedTex.TextureData.Image = GMImage.FromPng(ms.ToArray());
        replaced++;
        ScriptMessage("OK: Replaced " + spr.Name.Content + "[" + f + "]");
        if (totalFrames > 1) ScriptMessage("(progress: " + replaced + "/" + (endFrame - startFrame + 1) + ")");
    }} catch (System.Exception ex) {{
        ScriptMessage("ERROR: [" + f + "] " + ex.Message);
    }}
}}
if (replaced == 0) {{
    ScriptMessage("ERROR: No frames were replaced");
}} else {{
    ScriptMessage("Done: " + replaced + " frame(s) replaced");
}}
'''
    out = utmt._run_utmt(csx, game_file, save=True)
    for line in utmt._parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("WARN:") or line.startswith("Resize"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:") or line.startswith("Done:"):
            print(line)
        else:
            print(line)


def cmd_sprite_duplicate(game_file: Path, src_name: str, dst_name: str) -> None:
    """Duplicate a sprite with a new name for independent editing."""
    esc_src = utmt._csx_escape(src_name)
    esc_dst = utmt._csx_escape(dst_name)
    csx = f'''
var src = Data.Sprites.ByName("{esc_src}");
if (src == null) {{
    src = Data.Sprites.ByName("{esc_src}", true);
}}
if (src == null) {{
    int first = -1;
    for (int s = 0; s < Data.Sprites.Count; s++) {{
        if (Data.Sprites[s].Name.Content.IndexOf("{esc_src}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            if (first < 0) first = s;
        }}
    }}
    if (first >= 0) src = Data.Sprites[first];
}}
if (src == null) {{
    ScriptMessage("ERROR: Source sprite not found: {esc_src}");
    return;
}}
// Check if destination already exists
var existing = Data.Sprites.ByName("{esc_dst}");
if (existing != null) {{
    ScriptMessage("ERROR: Destination sprite already exists: {esc_dst}");
    return;
}}
var dst = new UndertaleModLib.Models.UndertaleSprite();
dst.Name = Data.Strings.MakeString("{esc_dst}");
dst.Width = src.Width;
dst.Height = src.Height;
dst.MarginLeft = src.MarginLeft;
dst.MarginRight = src.MarginRight;
dst.MarginTop = src.MarginTop;
dst.MarginBottom = src.MarginBottom;
dst.Transparent = src.Transparent;
dst.Smooth = src.Smooth;
dst.Preload = src.Preload;
dst.BBoxMode = src.BBoxMode;
dst.SepMasks = src.SepMasks;
dst.OriginX = src.OriginX;
dst.OriginY = src.OriginY;
// Copy textures with INDEPENDENT texture data
if (src.Textures != null) {{
    dst.Textures = new UndertaleModLib.UndertaleSimpleList<UndertaleModLib.Models.UndertaleSprite.TextureEntry>();
    var worker = new UndertaleModLib.Util.TextureWorker();
    for (int i = 0; i < src.Textures.Count; i++) {{
        var srcEntry = src.Textures[i];
        if (srcEntry?.Texture == null) continue;
        // Extract frame's pixel data from texture page as PNG bytes
        var frameImg = worker.GetTextureFor(srcEntry.Texture, src.Name.Content + "_frame" + i);
        var ms = new System.IO.MemoryStream();
        frameImg.Write(ms, ImageMagick.MagickFormat.Png);
        byte[] pngBytes = ms.ToArray();
        ms.Dispose();
        // Create new standalone embedded texture for this frame
        var newTex = new UndertaleModLib.Models.UndertaleEmbeddedTexture();
        newTex.Name = Data.Strings.MakeString(dst.Name.Content + "_frame" + i);
        newTex.TextureData = new UndertaleModLib.Models.UndertaleEmbeddedTexture.TexData();
        newTex.TextureData.Image = UndertaleModLib.Util.GMImage.FromPng(pngBytes);
        Data.EmbeddedTextures.Add(newTex);
        // Create new TexturePageItem pointing to standalone texture
        var newItem = new UndertaleModLib.Models.UndertaleTexturePageItem();
        newItem.Name = Data.Strings.MakeString(dst.Name.Content + "_item" + i);
        newItem.SourceX = 0;
        newItem.SourceY = 0;
        newItem.SourceWidth = (ushort)frameImg.Width;
        newItem.SourceHeight = (ushort)frameImg.Height;
        newItem.TargetX = srcEntry.Texture.TargetX;
        newItem.TargetY = srcEntry.Texture.TargetY;
        newItem.TargetWidth = srcEntry.Texture.TargetWidth;
        newItem.TargetHeight = srcEntry.Texture.TargetHeight;
        newItem.BoundingWidth = srcEntry.Texture.BoundingWidth;
        newItem.BoundingHeight = srcEntry.Texture.BoundingHeight;
        newItem.TexturePage = newTex;
        Data.TexturePageItems.Add(newItem);
        frameImg.Dispose();
        // Point sprite frame to new item
        var entry = new UndertaleModLib.Models.UndertaleSprite.TextureEntry();
        entry.Texture = newItem;
        dst.Textures.Add(entry);
    }}
    worker.Dispose();
}}
// Copy collision masks
if (src.CollisionMasks != null) {{
    dst.CollisionMasks = new UndertaleModLib.UndertaleObservableList<UndertaleModLib.Models.UndertaleSprite.MaskEntry>();
    for (int i = 0; i < src.CollisionMasks.Count; i++) {{
        var srcMask = src.CollisionMasks[i];
        byte[] maskData = new byte[srcMask.Data.Length];
        System.Array.Copy(srcMask.Data, maskData, srcMask.Data.Length);
        dst.CollisionMasks.Add(new UndertaleModLib.Models.UndertaleSprite.MaskEntry(maskData, srcMask.Width, srcMask.Height));
    }}
}}
Data.Sprites.Add(dst);
ScriptMessage("OK: Duplicated " + src.Name.Content + " → " + dst.Name.Content + " (" + (src.Textures?.Count ?? 0) + " frames)");
    ScriptMessage("(Use replace-sprite to edit the copy independently)");
'''
    out = utmt._run_utmt(csx, game_file, save=True)
    for line in utmt._parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)
        else:
            print(line)


def cmd_sprite_preview(game_file: Path, sprite_name: str) -> None:
    """Preview a sprite as ASCII art in terminal."""
    import tempfile
    from PIL import Image
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "preview.png"
        cmd_sprite_export(game_file, sprite_name, str(p), frame=0)
        if not p.exists():
            print("(sprite not found)", file=sys.stderr)
            return
        img = Image.open(str(p)).convert("RGBA")
        w, h = img.size
        print(f"{sprite_name}: {w}x{h}")
        chars = " .:oO8@"
        for y in range(h):
            row = ""
            for x in range(w):
                r, g, b, a = img.getpixel((x, y))
                if a == 0:
                    row += " "
                else:
                    bri = int(0.299 * r + 0.587 * g + 0.114 * b)
                    row += chars[min(bri * len(chars) // 256, len(chars) - 1)]
            print(row)


def cmd_sprite_colorize(game_file: Path, src_name: str, dst_name: str,
                         hue_from: tuple[float, float], hue_to: float,
                         sat_min: float = 0.05, val_min: float = 0.15, val_max: float = 0.95) -> None:
    """Duplicate a sprite and apply HSV-based selective color shift."""
    from PIL import Image
    import colorsys

    # Step 1: duplicate
    cmd_sprite_duplicate(game_file, src_name, dst_name)
    path_base = Path(tempfile.mktemp(suffix=""))
    temp_dir = path_base.parent / f"_clr_{path_base.name}"
    temp_dir.mkdir(exist_ok=True)
    try:
        # Step 2: export all frames
        cmd_sprite_export(game_file, dst_name, str(temp_dir))
        # Step 3: process each frame
        for f in sorted(temp_dir.iterdir()):
            if not f.name.endswith(".png"):
                continue
            img = Image.open(str(f)).convert("RGBA")
            px = img.load()
            w, h = img.size
            changed = 0
            for x in range(w):
                for y in range(h):
                    r, g, b, a = px[x, y]
                    if a == 0:
                        continue
                    hh, ss, vv = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
                    in_hue = (hue_from[0] <= hh <= hue_from[1]) if hue_from[0] <= hue_from[1] else (hh >= hue_from[0] or hh <= hue_from[1])
                    if in_hue and ss > sat_min and val_min < vv < val_max:
                        nr, ng, nb = colorsys.hsv_to_rgb(hue_to / 360.0, ss, vv)
                        px[x, y] = (int(nr * 255), int(ng * 255), int(nb * 255), a)
                        changed += 1
            img.save(str(f))
            print(f"  {f.name}: {changed} pixels shifted")
        # Step 4: replace all frames
        for f in sorted(temp_dir.iterdir()):
            if not f.name.endswith(".png"):
                continue
            frame_str = f.stem.rsplit("_", 1)[-1]
            try:
                frame = int(frame_str)
            except ValueError:
                continue
            cmd_sprite_replace(game_file, dst_name, str(f), frame=frame)
    finally:
        shutil.rmtree(str(temp_dir), ignore_errors=True)
    print(f"✓ {src_name} → {dst_name}: hue shift {hue_from[0]*360:.0f}°-{hue_from[1]*360:.0f}° → {hue_to}°")


def cmd_texture_export(game_file: Path, texture_name: str | None, output_dir: str) -> None:
    """Export embedded texture(s) as PNG.

    If texture_name is None, export all (via UTMT CLI dump -t).
    If texture_name is given, export single texture (via CSX).
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    if texture_name is None:
        # Export all textures via UTMT CLI dump -t
        cmd = ["dotnet", utmt._find_utmt_cli(), "dump", str(utmt._effective_game_file(game_file)), "-t", "-o", str(out_path)]
        subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=True)
        print(f"✓ 所有纹理已导出到: {out_path}")
    else:
        # Export single texture via CSX
        esc = utmt._csx_escape(texture_name)
        esc_path = utmt._csx_escape(str(out_path))
        csx = f'''
using UndertaleModLib.Util;
var tex = Data.EmbeddedTextures.ByName("{esc}");
if (tex == null) {{
    for (int i = 0; i < Data.EmbeddedTextures.Count; i++) {{
        if (Data.EmbeddedTextures[i].Name.Content.IndexOf("{esc}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            tex = Data.EmbeddedTextures[i];
            break;
        }}
    }}
}}
if (tex == null) {{
    ScriptMessage("ERROR: Texture not found: {esc}");
    return;
}}
string outPath = "{esc_path}";
System.IO.Directory.CreateDirectory(outPath);
string fp = System.IO.Path.Combine(outPath, tex.Name.Content + ".png");
if (tex.TextureData?.Image != null) {{
    using var fs = new System.IO.FileStream(fp, System.IO.FileMode.Create);
    tex.TextureData.Image.SavePng(fs);
    ScriptMessage("OK: Exported " + tex.Name.Content + " → " + fp);
}} else {{
    ScriptMessage("ERROR: Texture has no image data");
}}
'''
        out = utmt._run_utmt(csx, game_file, save=False)
        for line in utmt._parse_msg(out):
            if line.startswith("ERROR:"):
                print(line, file=sys.stderr)
            elif line.startswith("OK:"):
                print(line)
            else:
                print(line)


def cmd_texture_replace(game_file: Path, texture_name: str, png_path: str) -> None:
    """Replace an embedded texture with a PNG file (via UTMT CLI replace -t)."""
    p = Path(png_path)
    if not p.exists():
        raise errors.NotFoundError(f"文件不存在: {png_path}")
    cli = utmt._find_utmt_cli()
    target = utmt._resolve_write_target(game_file)
    _before = utmt._md5_file(target)
    if not state.SANDBOX_ACTIVE:
        paths.backup_file(target)
    cmd = ["dotnet", cli, "replace", str(target), "-t", f"{texture_name}={png_path}", "-o", str(target)]
    subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=True)
    _after = utmt._md5_file(target)
    _scope = "仅沙箱副本" if state.SANDBOX_ACTIVE else "真实文件（目标即 Steam 路径，无需同步）"
    print(f"📝 写入回执: {target}")
    print(f"   MD5: {_before[:12]}… → {_after[:12]}… | 范围: {_scope}")
    if state.SANDBOX_ACTIVE:
        print("   应用: --commit 直写 或 sandbox-restore；放弃: 直接删除 *.sandbox")
    else:
        print("   退路: undo --value data_win / list-backups")
    print(f"✓ {texture_name} 已替换: {png_path}")


def cmd_sprite_dump_all(game_file: Path, output_dir: str) -> None:
    """Dump ALL sprites as PNGs to a directory (via UTMT CLI dump --sprites)."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    cli = utmt._find_utmt_cli()
    cmd = ["dotnet", cli, "dump", str(utmt._effective_game_file(game_file)), "--sprites", "-o", str(out_path)]
    subprocess.run(cmd, capture_output=True, text=True, timeout=600, check=True)
    print(f"✓ 所有精灵已导出到: {out_path}")
