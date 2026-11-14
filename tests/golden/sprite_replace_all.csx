
using UndertaleModLib.Util;
using ImageMagick;
var spr = Data.Sprites.ByName("spr_golden");
if (spr == null) {
    spr = Data.Sprites.ByName("spr_golden", true);
}
if (spr == null) {
    int first = -1;
    int count = 0;
    for (int s = 0; s < Data.Sprites.Count; s++) {
        var sn = Data.Sprites[s].Name.Content;
        if (sn.IndexOf("spr_golden", StringComparison.OrdinalIgnoreCase) >= 0) {
            if (first < 0) first = s;
            count++;
        }
    }
    if (first >= 0) spr = Data.Sprites[first];
}
if (spr == null) {
    ScriptMessage("ERROR: Sprite not found: spr_golden");
    return;
}
string pngPath = "<GOLDEN_TMP>/spr_golden.png";
if (!System.IO.File.Exists(pngPath)) {
    ScriptMessage("ERROR: File not found: " + pngPath);
    return;
}
byte[] pngBytes = System.IO.File.ReadAllBytes(pngPath);
bool allMode = true;
int totalFrames = spr.Textures?.Count ?? 0;
int frameNum = 0;
int startFrame = allMode ? 0 : frameNum;
int endFrame = allMode ? totalFrames - 1 : frameNum;
int replaced = 0;
for (int f = startFrame; f <= endFrame; f++) {
    if (spr.Textures == null || spr.Textures.Count <= f) continue;
    var entry = spr.Textures[f];
    if (entry?.Texture?.TexturePage == null) continue;
    var texItem = entry.Texture;
    var embeddedTex = texItem.TexturePage;
    try {
        using var editImg = new MagickImage(pngBytes);
        uint sw = texItem.SourceWidth;
        uint sh = texItem.SourceHeight;
        bool resized = false;
        if (editImg.Width != sw || editImg.Height != sh) {
            ScriptMessage("Resize[" + f + "]: " + editImg.Width + "x" + editImg.Height + " -> " + sw + "x" + sh);
            editImg.InterpolativeResize(sw, sh, PixelInterpolateMethod.Bilinear);
            resized = true;
        }
        var worker = new TextureWorker();
        var pageImg = worker.GetEmbeddedTexture(embeddedTex);
        lock (pageImg) {
            pageImg.Composite(editImg, (int)texItem.SourceX, (int)texItem.SourceY, CompositeOperator.Copy);
        }
        using var ms = new System.IO.MemoryStream();
        pageImg.Write(ms, MagickFormat.Png);
        embeddedTex.TextureData.Image = GMImage.FromPng(ms.ToArray());
        replaced++;
        ScriptMessage("OK: Replaced " + spr.Name.Content + "[" + f + "]");
        if (totalFrames > 1) ScriptMessage("(progress: " + replaced + "/" + (endFrame - startFrame + 1) + ")");
    } catch (System.Exception ex) {
        ScriptMessage("ERROR: [" + f + "] " + ex.Message);
    }
}
if (replaced == 0) {
    ScriptMessage("ERROR: No frames were replaced");
} else {
    ScriptMessage("Done: " + replaced + " frame(s) replaced");
}
