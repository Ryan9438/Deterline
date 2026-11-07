
var src = Data.Sprites.ByName("spr_golden");
if (src == null) {
    src = Data.Sprites.ByName("spr_golden", true);
}
if (src == null) {
    int first = -1;
    for (int s = 0; s < Data.Sprites.Count; s++) {
        if (Data.Sprites[s].Name.Content.IndexOf("spr_golden", StringComparison.OrdinalIgnoreCase) >= 0) {
            if (first < 0) first = s;
        }
    }
    if (first >= 0) src = Data.Sprites[first];
}
if (src == null) {
    ScriptMessage("ERROR: Source sprite not found: spr_golden");
    return;
}
// Check if destination already exists
var existing = Data.Sprites.ByName("spr_golden_copy");
if (existing != null) {
    ScriptMessage("ERROR: Destination sprite already exists: spr_golden_copy");
    return;
}
var dst = new UndertaleModLib.Models.UndertaleSprite();
dst.Name = Data.Strings.MakeString("spr_golden_copy");
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
if (src.Textures != null) {
    dst.Textures = new UndertaleModLib.UndertaleSimpleList<UndertaleModLib.Models.UndertaleSprite.TextureEntry>();
    var worker = new UndertaleModLib.Util.TextureWorker();
    for (int i = 0; i < src.Textures.Count; i++) {
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
    }
    worker.Dispose();
}
// Copy collision masks
if (src.CollisionMasks != null) {
    dst.CollisionMasks = new UndertaleModLib.UndertaleObservableList<UndertaleModLib.Models.UndertaleSprite.MaskEntry>();
    for (int i = 0; i < src.CollisionMasks.Count; i++) {
        var srcMask = src.CollisionMasks[i];
        byte[] maskData = new byte[srcMask.Data.Length];
        System.Array.Copy(srcMask.Data, maskData, srcMask.Data.Length);
        dst.CollisionMasks.Add(new UndertaleModLib.Models.UndertaleSprite.MaskEntry(maskData, srcMask.Width, srcMask.Height));
    }
}
Data.Sprites.Add(dst);
ScriptMessage("OK: Duplicated " + src.Name.Content + " → " + dst.Name.Content + " (" + (src.Textures?.Count ?? 0) + " frames)");
    ScriptMessage("(Use replace-sprite to edit the copy independently)");
