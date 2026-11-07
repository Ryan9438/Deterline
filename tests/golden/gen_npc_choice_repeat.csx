if (id == 113930 && !instance_exists(obj_dialoguer) && !instance_exists(OBJ_WRITER) && !instance_exists(obj_choicer))
{
    if (distance_to_object(obj_mainchara) < 50)
    {
        global.msc = 0;
        global.typer = 5;
        global.facechoice = 3;
        global.faceemotion = 1;
        global.msg[0] = scr_gettext("obj_ask");
        global.msg[1] = "%%%";
        instance_create(0, 0, obj_dialoguer);
    }
}
if (id == 113930 && global.choice != -1)
{
    if (global.choice == 0)
    {
        global.choice = -1;
        global.msc = -1;
        global.typer = 5;
        global.facechoice = 3;
        global.faceemotion = 1;
        global.msg[0] = scr_gettext("obj_yes");
        global.msg[1] = "%%%";
    }
    else
    {
        global.choice = -1;
        global.msc = -1;
        global.typer = 5;
        global.facechoice = 3;
        global.faceemotion = 1;
        global.msg[0] = scr_gettext("obj_no");
        global.msg[1] = "%%%";
    }
}
