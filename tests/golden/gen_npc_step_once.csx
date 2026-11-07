if (id == 113928 && !instance_exists(obj_dialoguer) && !instance_exists(OBJ_WRITER) && !instance_exists(obj_choicer))
{
    if (distance_to_object(obj_mainchara) < 50)
    {
        global.msc = 0;
        global.typer = 5;
        global.facechoice = 3;
        global.faceemotion = 1;
        global.msg[0] = scr_gettext("obj_k");
        global.msg[1] = "%%%";
        instance_create(0, 0, obj_dialoguer);
            instance_destroy();
    }
}
