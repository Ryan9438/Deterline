
string bgName = "bg_golden";
string pngPath = @"/private/tmp/golden_test/bg_golden.png";

var existing = Data.Backgrounds.ByName(bgName);
if (existing != null) {
    ScriptMessage("ERROR: Background already exists: " + bgName);
    return;
}

byte[] pngBytes;
try { pngBytes = System.IO.File.ReadAllBytes(pngPath); }
catch (System.Exception ex) { ScriptMessage("ERROR: " + ex.Message); return; }

var tex = new UndertaleModLib.Models.UndertaleEmbeddedTexture();
tex.Name = Data.Strings.MakeString(bgName + "_tex");
tex.TextureData = new UndertaleModLib.Models.UndertaleEmbeddedTexture.TexData();
tex.TextureData.Image = UndertaleModLib.Util.GMImage.FromPng(pngBytes);
Data.EmbeddedTextures.Add(tex);

var mgk = new ImageMagick.MagickImage(pngBytes);
int imgW = (int)mgk.Width;
int imgH = (int)mgk.Height;
mgk.Dispose();

var item = new UndertaleModLib.Models.UndertaleTexturePageItem();
item.Name = Data.Strings.MakeString(bgName + "_item");
item.SourceX = 0; item.SourceY = 0;
item.SourceWidth = (ushort)imgW; item.SourceHeight = (ushort)imgH;
item.TargetX = 0; item.TargetY = 0;
item.TargetWidth = (ushort)imgW; item.TargetHeight = (ushort)imgH;
item.BoundingWidth = (ushort)imgW; item.BoundingHeight = (ushort)imgH;
item.TexturePage = tex;
Data.TexturePageItems.Add(item);

var bg = new UndertaleModLib.Models.UndertaleBackground();
bg.Name = Data.Strings.MakeString(bgName);
bg.Transparent = false; bg.Smooth = false; bg.Preload = true;
bg.Texture = item;
Data.Backgrounds.Add(bg);

ScriptMessage("OK: Created background '" + bgName + "' (" + imgW + "x" + imgH + ")");
ScriptMessage("  Use: set-room-bg --bg \"" + bgName + "\" --index N");
