if (instance_exists(writer) == 0)
{
    instance_destroy();
}
else if (control_check_pressed(1))
{
    if (writer.halt == 0)
    {
        if (global.typer != 10)
        {
            global.flag[25] += 1;
            writer.stringpos = string_length(writer.originalstring);
        }
    }
    control_clear(1);
}
if (global.facechange == 2)
{
    global.facechange = 0;
}
if (global.facechange == 1 && global.facechoice == 0)
{
    if (instance_exists(writer))
    {
        writer.x = xx + 30;
        writer.writingx = writer.x;
        writer.writingxend = writer.writingxend_base;
    }
    if (instance_exists(obj_face) == 1)
    {
        with (obj_face)
        {
            instance_destroy();
        }
    }
    global.facechange = 2;
}
if (global.facechange == 1)
{
    if (instance_exists(writer))
    {
        writer.x = xx + 68;
        writer.writingx = writer.x + 20;
        writer.writingxend = writer.writingxend_base;
        if (global.facechoice == 1)
        {
            if (!instance_exists(obj_face_torieltalk) && !instance_exists(obj_face_torielblink))
            {
                script_execute(scr_facechoice);
            }
        }
        if (global.facechoice == 2)
        {
            if (!instance_exists(obj_face_floweytalk))
            {
                script_execute(scr_facechoice);
            }
        }
        if (global.facechoice == 3)
        {
            if (!instance_exists(obj_face_sans))
            {
                script_execute(scr_facechoice);
            }
        }
        if (global.facechoice == 4)
        {
            if (global.language == "ja")
            {
                writer.x = xx + 10;
                writer.writingx = xx + 30;
                writer.writingxend = writer.writingxend_base - 38;
            }
            if (!instance_exists(obj_face_papyrus))
            {
                script_execute(scr_facechoice);
            }
        }
        if (global.facechoice == 5)
        {
            if (!instance_exists(obj_face_undyne))
            {
                script_execute(scr_facechoice);
            }
        }
        if (global.facechoice == 6)
        {
            if (!instance_exists(obj_face_alphys))
            {
                script_execute(scr_facechoice);
            }
        }
        if (global.facechoice == 7)
        {
            if (!instance_exists(obj_face_asgore))
            {
                script_execute(scr_facechoice);
            }
        }
        if (global.facechoice == 8)
        {
            if (!instance_exists(obj_face_mettaton))
            {
                script_execute(scr_facechoice);
            }
        }
        if (global.facechoice == 9)
        {
            if (!instance_exists(obj_face_asriel))
            {
                script_execute(scr_facechoice);
            }
        }
        global.facechange = 2;
    }
}
