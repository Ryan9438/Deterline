// C3b recon probe 0: pure-reflection API survey of font/texture types (READ-ONLY)
// No compile-time property access, so this always runs regardless of API renames.
using System;
using System.Linq;
using System.Reflection;
using System.Collections.Generic;

Func<Type, string> Props = (t) => {
    var lines = new List<string>();
    foreach (var p in t.GetProperties(BindingFlags.Public | BindingFlags.Instance).OrderBy(p => p.Name))
        lines.Add("  PROP " + p.PropertyType.Name + " " + p.Name);
    foreach (var f in t.GetFields(BindingFlags.Public | BindingFlags.Instance).OrderBy(f => f.Name))
        lines.Add("  FIELD " + f.FieldType.Name + " " + f.Name);
    return string.Join(Environment.NewLine, lines);
};

ScriptMessage("=== P0 UNDERTALEDATA list-typed properties ===");
foreach (var p in typeof(UndertaleData).GetProperties(BindingFlags.Public | BindingFlags.Instance).OrderBy(p => p.Name))
    if (typeof(System.Collections.IEnumerable).IsAssignableFrom(p.PropertyType) && p.PropertyType != typeof(string))
        ScriptMessage("  LIST " + p.PropertyType.Name + " " + p.Name);

ScriptMessage("=== P0 UndertaleFont full shape ===");
ScriptMessage(Props(typeof(UndertaleFont)));

// find GlyphInfo type (nested or standalone)
Type giType = typeof(UndertaleFont).GetNestedTypes(BindingFlags.Public)
    .FirstOrDefault(t => t.Name.ToLower().Contains("glyph"));
if (giType == null) {
    // try to discover from an actual instance
    var anyFont = Data.Fonts.FirstOrDefault(fo => fo != null);
    var glyphsProp = typeof(UndertaleFont).GetProperties().FirstOrDefault(p => p.Name.ToLower().Contains("glyph") && typeof(System.Collections.IEnumerable).IsAssignableFrom(p.PropertyType));
    if (glyphsProp != null && anyFont != null) {
        var list = glyphsProp.GetValue(anyFont) as System.Collections.IEnumerable;
        if (list != null) foreach (var g in list) { giType = g.GetType(); break; }
    }
}
ScriptMessage("GLYPHINFO_TYPE:" + (giType != null ? giType.FullName : "NOT FOUND"));
if (giType != null) ScriptMessage(Props(giType));

ScriptMessage("=== P0 UndertaleTexturePageItem full shape ===");
ScriptMessage(Props(typeof(UndertaleTexturePageItem)));

ScriptMessage("=== P0 UndertaleEmbeddedTexture full shape ===");
ScriptMessage(Props(typeof(UndertaleEmbeddedTexture)));

// nested types of EmbeddedTexture (TextureDataBlob etc.)
ScriptMessage("=== P0 UndertaleEmbeddedTexture nested types ===");
foreach (var nt in typeof(UndertaleEmbeddedTexture).GetNestedTypes(BindingFlags.Public)) {
    ScriptMessage("NESTED:" + nt.FullName);
    ScriptMessage(Props(nt));
}

ScriptMessage("P0_DONE");
