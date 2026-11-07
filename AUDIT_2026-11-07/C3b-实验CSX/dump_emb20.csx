using System;
using System.IO;
using System.Linq;
var tex = Data.EmbeddedTextures.First(t => t.Name != null && t.Name.Content == "Texture 20");
using (var fs = File.Create("/Users/ryan/Desktop/UT 存档修改/Deterline/build/font_cjk_pass1/emb20_page.png"))
    tex.TextureData.Image.SavePng(fs);
ScriptMessage("EMB20_DUMP_OK " + tex.TextureData.Width + "x" + tex.TextureData.Height);
