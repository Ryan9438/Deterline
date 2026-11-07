var xx = argument0;
var yy = argument1;
var use_font;
if (global.language == "ja")
{
    use_font = 12;
    yy += 3;
}
else
{
    use_font = 7;
    for (var i = 1; i < strlen(global.charname); i++)
    {
        if (ord(string_char_at(global.charname, i)) >= 12288)
        {
            use_font = 12;
            yy += 3;
            break;
        }
    }
}
draw_set_font(use_font);
draw_text(xx, yy, global.charname);
return string_width(global.charname);
