SCR_TEXTTYPE(global.typer);
x = round(x);
y = round(y);
writingx = round(writingx);
writingy = round(writingy);
stringno = 0;
stringpos = 0;
halt = 0;
dfy = 0;
sound_enable = 1;
for (var n = 0; global.msg[n] != "%%%"; n++)
{
    mystring[n] = global.msg[n];
}
originalstring = scr_replace_buttons_pc(mystring[0]);
alarm[0] = textspeed;
