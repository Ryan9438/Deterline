// C3b recon probe 3b: texture page system + free space analysis (READ-ONLY)
using System;
using System.Linq;
using System.Reflection;
using System.Collections.Generic;

ScriptMessage("=== P3b TEXTURE PAGE SYSTEM ===");

// TextureGroupInfo shape
ScriptMessage("--- UndertaleTextureGroupInfo shape ---");
foreach (var p in typeof(UndertaleTextureGroupInfo).GetProperties(BindingFlags.Public | BindingFlags.Instance).OrderBy(p => p.Name))
    ScriptMessage("  TGPROP " + p.PropertyType.Name + " " + p.Name);

ScriptMessage("--- EmbeddedTextures inventory ---");
int idx = 0;
foreach (var t in Data.EmbeddedTextures) {
    string grp = (t.TextureInfo != null && t.TextureInfo.Name != null) ? t.TextureInfo.Name.Content : "(null)";
    ScriptMessage("EMB|" + idx
        + "|name=" + (t.Name != null ? t.Name.Content : "(null)")
        + "|WH=" + t.TextureData.Width + "x" + t.TextureData.Height
        + "|fmtBZ2=" + t.TextureData.FormatBZ2 + "|fmtQOI=" + t.TextureData.FormatQOI
        + "|IndexInGroup=" + t.IndexInGroup
        + "|group=" + grp
        + "|external=" + t.TextureExternal + "|scaled=" + t.Scaled + "|mips=" + t.GeneratedMips
        + "|loaded=" + t.TextureLoaded);
    idx++;
}

// occupancy per interesting page
Func<int, string> PageOccupancy = (embIdx) => {
    var t = Data.EmbeddedTextures[embIdx];
    int W = t.TextureData.Width, H = t.TextureData.Height;
    var tpis = new List<UndertaleTexturePageItem>();
    foreach (var tpi in Data.TexturePageItems)
        if (tpi.TexturePage == t) tpis.Add(tpi);
    // grid-based free space estimate (8px cells)
    bool[,] occ = new bool[W / 8 + 1, H / 8 + 1];
    foreach (var tpi in tpis) {
        for (int x = tpi.SourceX / 8; x < (tpi.SourceX + tpi.SourceWidth + 7) / 8 && x < occ.GetLength(0); x++)
            for (int y = tpi.SourceY / 8; y < (tpi.SourceY + tpi.SourceHeight + 7) / 8 && y < occ.GetLength(1); y++)
                occ[x, y] = true;
    }
    int usedCells = 0, totalCells = (W / 8) * (H / 8);
    for (int x = 0; x < W / 8; x++) for (int y = 0; y < H / 8; y++) if (occ[x, y]) usedCells++;
    // find largest free rectangle (greedy scan)
    int bestA = 0, bestX = 0, bestY = 0, bestW = 0, bestH = 0;
    for (int y = 0; y < H / 8; y++) {
        for (int x = 0; x < W / 8; x++) {
            if (occ[x, y]) continue;
            int maxW = W / 8 - x;
            for (int hh = 1; y + hh <= H / 8; hh++) {
                int w = 0;
                while (w < maxW && !occ[x + w, y + hh - 1]) w++;
                maxW = Math.Min(maxW, w);
                if (maxW == 0) break;
                int a = maxW * hh;
                if (a > bestA) { bestA = a; bestX = x * 8; bestY = y * 8; bestW = maxW * 8; bestH = hh * 8; }
            }
        }
    }
    string listing = string.Join("; ", tpis.Select(tp => Data.TexturePageItems.IndexOf(tp) + ":" + tp.SourceX + "," + tp.SourceY + "+" + tp.SourceWidth + "x" + tp.SourceHeight + "(" + ((tp.Name != null) ? tp.Name.Content : "?") + ")"));
    return "PAGE emb#" + embIdx + " " + W + "x" + H + " tpis=" + tpis.Count
        + " usedCells8px=" + usedCells + "/" + totalCells + " (" + (usedCells * 100 / totalCells) + "%)"
        + " | largestFreeRect=" + bestW + "x" + bestH + " at " + bestX + "," + bestY
        + Environment.NewLine + "  TPIs: " + listing;
};

foreach (int embIdx in new int[] { 18, 19, 20 }) {
    ScriptMessage(PageOccupancy(embIdx));
}

// who uses the ja page (emb#20) TPIs -> confirms it is font-only
ScriptMessage("--- users of emb#20 TPIs ---");
var emb20 = Data.EmbeddedTextures[20];
foreach (var tpi in Data.TexturePageItems.Where(t => t.TexturePage == emb20)) {
    var fonts = Data.Fonts.Where(f => f.Texture == tpi).Select(f => f.Name.Content);
    var spr = Data.Sprites.FirstOrDefault(s => s.Textures != null && s.Textures.Any(tx => tx != null && tx.Texture == tpi));
    var bg = Data.Backgrounds.FirstOrDefault(b => b.Texture == tpi);
    ScriptMessage("  TPI#" + Data.TexturePageItems.IndexOf(tpi) + " fonts=[" + string.Join(",", fonts) + "]"
        + " sprite=" + (spr != null ? spr.Name.Content : "-") + " bg=" + (bg != null ? bg.Name.Content : "-"));
}

ScriptMessage("P3b_DONE");
