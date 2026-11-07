// C3b recon probe 3d: EmbeddedTexture/TexData/GMImage API shape for building a page from PNG (NO save, NO Data mutation)
using System;
using System.Linq;
using System.Reflection;
using System.Collections.Generic;

ScriptMessage("=== P3d EMBEDDED TEXTURE API SHAPE (no embedding) ===");

// GMImage type shape
Type gmImageType = typeof(UndertaleEmbeddedTexture).Assembly.GetTypes().FirstOrDefault(t => t.Name == "GMImage");
if (gmImageType == null) {
    foreach (var t in typeof(UndertaleEmbeddedTexture).Assembly.GetTypes()) if (t.FullName != null && t.FullName.Contains("GMImage")) { gmImageType = t; break; }
}
ScriptMessage("GMIMAGE_TYPE:" + (gmImageType != null ? gmImageType.FullName : "NOT FOUND"));
if (gmImageType != null) {
    ScriptMessage("--- GMImage properties ---");
    foreach (var p in gmImageType.GetProperties(BindingFlags.Public | BindingFlags.Instance).OrderBy(p => p.Name))
        ScriptMessage("  PROP " + p.PropertyType.Name + " " + p.Name);
    ScriptMessage("--- GMImage static methods ---");
    foreach (var m in gmImageType.GetMethods(BindingFlags.Public | BindingFlags.Static).Where(m => !m.IsSpecialName).OrderBy(m => m.Name))
        ScriptMessage("  STATIC " + m.Name + "(" + string.Join(", ", m.GetParameters().Select(p => p.ParameterType.Name + " " + p.Name)) + ")");
    ScriptMessage("--- GMImage instance methods ---");
    foreach (var m in gmImageType.GetMethods(BindingFlags.Public | BindingFlags.Instance).Where(m => !m.IsSpecialName).OrderBy(m => m.Name))
        ScriptMessage("  METHOD " + m.Name + "(" + string.Join(", ", m.GetParameters().Select(p => p.ParameterType.Name + " " + p.Name)) + ")");
    // nested types (color formats etc.)
    foreach (var nt in gmImageType.GetNestedTypes(BindingFlags.Public))
        ScriptMessage("  NESTED " + nt.Name);
}

// Magick.NET availability
ScriptMessage("--- Magick.NET availability ---");
try {
    var magickType = Type.GetType("ImageMagick.MagickImage, Magick.NET-Q8-AnyCPU");
    if (magickType == null) {
        foreach (var an in AppDomain.CurrentDomain.GetAssemblies()) {
            if (an.FullName.StartsWith("Magick.NET")) {
                magickType = an.GetType("ImageMagick.MagickImage");
                if (magickType != null) { ScriptMessage("MAGICK_ASSEMBLY:" + an.FullName); break; }
            }
        }
    }
    ScriptMessage("MAGICK_TYPE:" + (magickType != null ? magickType.FullName : "NOT RESOLVED via Type.GetType"));
    if (magickType != null) {
        var mi = gmImageType.GetMethods(BindingFlags.Public | BindingFlags.Static).FirstOrDefault(m => m.Name.Contains("Magick"));
        ScriptMessage("GMIMAGE_MAGICK_FACTORY:" + (mi != null ? mi.ToString() : "(none named *Magick*)"));
    }
} catch (Exception e) { ScriptMessage("MAGICK_CHECK_ERR:" + e.Message); }

// TexData construction dry-run: build a 4x4 raw image from RGBA bytes in memory only, NOT added to Data
ScriptMessage("--- TexData in-memory dry run (4x4, never added to Data.EmbeddedTextures) ---");
try {
    var tex = new UndertaleEmbeddedTexture();
    tex.Name = Data.Strings.MakeString("Texture c3b_probe");
    tex.Scaled = 0; tex.GeneratedMips = 0;
    tex.TextureWidth = 4; tex.TextureHeight = 4;
    tex.TextureData = new UndertaleEmbeddedTexture.TexData();
    // NOTE: TexData.Width/Height AND FormatBZ2/FormatQOI are READ-ONLY (derived from the
    // assigned GMImage implementation) — confirmed by CS0200 in two probe runs.
    // build a GMImage from PNG bytes: round-trip proof — extract emb#19 image to PNG bytes
    // in memory, then feed through GMImage.FromPng into the scratch texture (no Magick needed)
    string builtVia = "(not built)";
    if (gmImageType != null) {
        var anyFrom = gmImageType.GetMethods(BindingFlags.Public | BindingFlags.Static).Where(m => m.Name.StartsWith("From")).Select(m => m.Name).ToArray();
        ScriptMessage("FACTORIES:" + string.Join(",", anyFrom) + " (NOTE: no FromRgba/FromBgra in this build)");
        var fromPng = gmImageType.GetMethod("FromPng", new Type[] { typeof(byte[]), typeof(bool) });
        var srcImg = Data.EmbeddedTextures[19].TextureData.Image;
        if (fromPng != null && srcImg != null) {
            byte[] data;
            using (var ms = new MemoryStream()) { srcImg.SavePng(ms); data = ms.ToArray(); }
            var img = fromPng.Invoke(null, new object[] { data, false });
            tex.TextureData.GetType().GetProperty("Image").SetValue(tex.TextureData, img);
            builtVia = "SavePng(" + data.Length + "B)->FromPng (round-trip)";
        }
    }
    ScriptMessage("TEXDATA_DRYRUN_OK: Image built via " + builtVia + " W=" + tex.TextureData.Width + " H=" + tex.TextureData.Height
        + " imgType=" + (tex.TextureData.Image != null ? tex.TextureData.Image.GetType().Name : "null")
        + " fmtBZ2=" + tex.TextureData.FormatBZ2 + " fmtQOI=" + tex.TextureData.FormatQOI
        + " addedToData=false (will be dropped)");
    // inspect what a loaded existing texture's Image looks like
    var ex = Data.EmbeddedTextures[18].TextureData;
    ScriptMessage("EXISTING_emb18: W=" + ex.Width + " H=" + ex.Height + " ImageType=" + (ex.Image != null ? ex.Image.GetType().FullName : "null"));
} catch (Exception e) { ScriptMessage("ERROR: TexData dry run failed: " + e.GetType().Name + ": " + e.Message); }

// extraction proof: save emb#19 (the en font page) to PNG via Image.SavePng (evidence artifact, recon dir)
ScriptMessage("--- extraction proof: emb#19 -> png ---");
try {
    var exImg = Data.EmbeddedTextures[19].TextureData.Image;
    if (exImg != null) {
        string pngPath = "/Users/ryan/Desktop/UT 存档修改/Deterline/AUDIT_2026-11-07/C3b侦察-字体/emb19_font_page_extract.png";
        using (var fs = File.Create(pngPath)) exImg.SavePng(fs);
        ScriptMessage("EXTRACT_OK: emb#19 " + exImg.Width + "x" + exImg.Height + " fmt=" + exImg.Format + " -> emb19_font_page_extract.png (" + new FileInfo(pngPath).Length + " bytes)");
    } else ScriptMessage("EXTRACT_SKIP: emb#19 Image not loaded in memory");
} catch (Exception e) { ScriptMessage("ERROR: extraction failed: " + e.GetType().Name + ": " + e.Message); }

// what UMT needs to serialize a new texture: check UndertaleEmbeddedTexture serializable fields via UndertaleObject interface
ScriptMessage("--- check UndertaleEmbeddedTexture.BuildUncached / serialization hooks (info only) ---");
foreach (var m in typeof(UndertaleEmbeddedTexture).GetMethods(BindingFlags.Public | BindingFlags.Instance).Where(m => m.Name.Contains("Unserialize") || m.Name.Contains("Serialize") || m.Name.Contains("Build")).OrderBy(m => m.Name))
    ScriptMessage("  SER " + m.Name + "(" + string.Join(", ", m.GetParameters().Select(p => p.ParameterType.Name)) + ")");

ScriptMessage("P3d_DONE");
