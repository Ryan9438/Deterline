
var room = Data.Rooms.ByName("room_golden");
if (room == null) {
    for (int r = 0; r < Data.Rooms.Count; r++) {
        if (Data.Rooms[r].Name.Content.IndexOf("room_golden", StringComparison.OrdinalIgnoreCase) >= 0) {
            room = Data.Rooms[r];
            break;
        }
    }
}
if (room == null) {
    ScriptMessage("ERROR: Room not found: room_golden");
    return;
}

ScriptMessage("SIZE:" + room.Width + ":" + room.Height);

=== CALL ===

var bg = Data.Backgrounds.ByName("bg_solid_0000ff");
ScriptMessage("EXISTS:" + (bg != null));

=== CALL ===

string bgName = "bg_solid_0000ff";
string pngPath = @"/private/tmp/golden_test/det_solid_fixed.png";

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

=== CALL ===

var room = Data.Rooms.ByName("room_golden");
if (room == null) {
    for (int r = 0; r < Data.Rooms.Count; r++) {
        if (Data.Rooms[r].Name.Content.IndexOf("room_golden", StringComparison.OrdinalIgnoreCase) >= 0) {
            room = Data.Rooms[r];
            break;
        }
    }
}
if (room == null) {
    ScriptMessage("ERROR: Room not found: room_golden");
    return;
}

for (int i = 0; i < (room.Backgrounds?.Count ?? 0); i++) {
    if (room.Backgrounds[i].Enabled) ScriptMessage("ENABLED:" + i);
}

=== CALL ===

var room = Data.Rooms.ByName("room_golden");
if (room == null) {
    for (int r = 0; r < Data.Rooms.Count; r++) {
        if (Data.Rooms[r].Name.Content.IndexOf("room_golden", StringComparison.OrdinalIgnoreCase) >= 0) {
            room = Data.Rooms[r];
            break;
        }
    }
}
if (room == null) {
    ScriptMessage("ERROR: Room not found: room_golden");
    return;
}

var bgDef = Data.Backgrounds.ByName("bg_solid_0000ff");
if (bgDef == null) { ScriptMessage("ERROR: Background not found: bg_solid_0000ff"); return; }

if (room.Backgrounds.Count > 0) {
    room.Backgrounds[0].BackgroundDefinition = bgDef;
    room.Backgrounds[0].Enabled = true;
    room.Backgrounds[0].TiledHorizontally = true;
    room.Backgrounds[0].TiledVertically = true;
    room.Backgrounds[0].X = 0;
    room.Backgrounds[0].Y = 0;
    room.Backgrounds[0].Foreground = false;
}

ScriptMessage("OK: Assigned bg_solid_0000ff to layers [0] of " + room.Name.Content);

=== CALL ===

var code = Data.Code.ByName("gml_Object_obj_mainchara_Step_0");
if (code == null) {
    ScriptMessage("ERROR: Code entry not found: gml_Object_obj_mainchara_Step_0");
    return;
}
if (code.ParentEntry != null) {
    ScriptMessage("SKIP: child entry, use parent instead");
    return;
}
try {
    string existingGml = GetDecompiledText(code);
    string newGml = existingGml + "\n" + @"if (room == room_golden)
{
if (!variable_global_exists(""det_bg_room_golden_0_bg_solid_0000ff""))
{
global.det_bg_room_golden_0_bg_solid_0000ff = 1;
background_visible[0] = true;
background_index[0] = bg_solid_0000ff;
background_htiled[0] = true;
background_vtiled[0] = true;
background_foreground[0] = false;
for (var _det_i = 0 + 1; _det_i < 8; _det_i++) { background_visible[_det_i] = false; }
}
background_x[0] = floor(view_xview[0] - (view_xview[0] * 0.0));
background_y[0] = floor(view_yview[0] - (view_yview[0] * 0.0));
}";
    CodeImportGroup importGroup = new(Data)
    {
        MainThreadAction = MainThreadAction
    };
    importGroup.QueueReplace(code, newGml);
    importGroup.Import();
    ScriptMessage("OK: Appended to " + "gml_Object_obj_mainchara_Step_0" + " (len " + newGml.Length + ")");
} catch (Exception ex) {
    ScriptMessage("ERROR: " + ex.Message);
}
