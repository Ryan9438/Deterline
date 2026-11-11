"""Command adapters and the registry used by CLI dispatch and documentation."""

import sys
import tempfile
from pathlib import Path

from . import config, file0, inifile, paths, sandbox, state, transactions, utmt
from .cmds import cjk, code, dialogue, doctor, door, npc, room, save_cmds, sprite, verify


def _doctor(args, parser, target):
    try:
        save_dir = paths.find_save_dir(args.dir)
    except FileNotFoundError as exc:
        print(f"  ✗ 存档目录定位 — {exc}", file=sys.stderr)
        save_dir = None
    doctor.cmd_doctor(save_dir, args.dir)


def _md5(args, parser, target):
    game_file = paths.find_game_data_file(args.dir)
    print(f"{utmt._md5_file(game_file)}  {game_file}")


def _sandbox_restore(args, parser, target):
    game_file = paths.find_game_data_file(args.dir)
    copy = sandbox.sandbox_path(game_file)
    if not copy.is_file():
        raise FileNotFoundError(f"沙箱备份不存在: {copy}")
    baseline = sandbox.check_baseline(game_file, copy)
    transactions.EditPlan((transactions.FileEdit(game_file.resolve(), copy, baseline),)).apply()
    if state.PREVIEW:
        return
    sandbox.remove_workspace(copy)
    print(f"✓ 沙箱备份已恢复: {copy} → {game_file}")


def _set_derived(args, parser, target):
    if args.key is None or args.value is None:
        parser.error("set-derived 需要 --key (HP/MAXHP/AT/DF) 和 --value")
    code.cmd_set_derived(paths.find_save_dir(args.dir), paths.find_game_data_file(args.dir),
                         args.key, args.value)


def _list_strings_data_win(args, parser, game_file):
    dialogue.cmd_strg_list(game_file, args.limit, args.offset, args.hex)


def _get_string_data_win(args, parser, game_file):
    if args.key is None:
        parser.error("--key 是必需的 (字符串索引)")
    dialogue.cmd_strg_get(game_file, int(args.key))


def _set_string_data_win(args, parser, game_file):
    if args.key is None or args.value is None:
        parser.error("--key 和 --value 是必需的")
    dialogue.cmd_strg_set(game_file, int(args.key), args.value)


def _add_string_data_win(args, parser, game_file):
    if args.value is None:
        parser.error("--value 是必需的 (新对话文本)")
    dialogue.cmd_strg_add(game_file, args.value)


def _delete_string_data_win(args, parser, game_file):
    if args.key is None:
        parser.error("--key 是必需的 (要删除的索引)")
    dialogue.cmd_strg_delete(game_file, int(args.key))


def _replace_string_data_win(args, parser, game_file):
    if args.old is None or args.value is None:
        parser.error("--old 和 --value 是必需的")
    dialogue.cmd_strg_replace(game_file, args.old, args.value)


def _search_strings_data_win(args, parser, game_file):
    if args.value is None:
        parser.error("--value 是必需的 (搜索关键词)")
    dialogue.cmd_strg_search(game_file, args.value, args.limit)


def _list_codes_data_win(args, parser, game_file):
    code.cmd_code_list(game_file, args.limit, args.offset)


def _decompile_code_data_win(args, parser, game_file):
    if args.key is None:
        parser.error("--key 是必需的 (代码名称)")
    code.cmd_code_decompile(game_file, args.key, args.limit, search=args.search or args.old or "")


def _replace_code_data_win(args, parser, game_file):
    if args.key is None or args.value is None:
        parser.error("--key 和 --value 是必需的 (代码名称 + GML 源码或文件路径)")
    code.cmd_code_replace(game_file, args.key, args.value, value_is_file=args.file_path,
                     show_diff=args.show_diff, dry_run=args.dry_run)


def _find_replace_code_data_win(args, parser, game_file):
    if args.key is None or args.old is None or args.value is None:
        parser.error("--key, --old 和 --value 是必需的")
    code.cmd_code_find_replace(game_file, args.key, args.old, args.value,
                          show_diff=args.show_diff, dry_run=args.dry_run)


def _search_textdata_data_win(args, parser, game_file):
    if args.value is None:
        parser.error("--value 是必需的 (搜索关键词)")
    dialogue.cmd_textdata_search(game_file, args.value, args.limit)


def _add_textentry_data_win(args, parser, game_file):
    if args.key is None or args.value is None:
        parser.error("--key 和 --value 是必需的")
    dialogue.cmd_textdata_add(game_file, args.key, args.value,
                     face=args.face, emotion=args.emotion)


def _guided_add_dialogue_data_win(args, parser, game_file):
    if args.key is None or args.value is None:
        parser.error("--key (文本 key) 和 --value (对话内容) 是必需的")
    dialogue.cmd_guided_add_dialogue(game_file, args.key, args.value,
                            face=args.face, emotion=args.emotion)


def _delete_textentry_data_win(args, parser, game_file):
    if args.key is None:
        parser.error("--key 是必需的 (要删除的 textdata key)")
    dialogue.cmd_textdata_delete(game_file, args.key)


def _update_textentry_data_win(args, parser, game_file):
    if args.key is None or args.value is None:
        parser.error("--key 和 --value 是必需的 (已存在的 textdata key + 新文本)")
    dialogue.cmd_textdata_update(game_file, args.key, args.value,
                        face=args.face, emotion=args.emotion)


def _search_vars_data_win(args, parser, game_file):
    if args.value is None:
        parser.error("--value 是必需的 (变量名/精灵名/任意代码片段)")
    code.cmd_search_vars(game_file, args.value, args.limit)


def _room_objects_data_win(args, parser, game_file):
    if args.value is None:
        parser.error("--value 是必需的 (房间内部名，如 torielroom)")
    room.cmd_room_objects(game_file, args.value)


def _create_script_data_win(args, parser, game_file):
    if args.key is None or args.value is None:
        parser.error("--key 和 --value 是必需的 (代码名 + GML 源码或文件路径)")
    code.cmd_create_script(game_file, args.key, args.value, value_is_file=args.file_path)


def _search_sctext_data_win(args, parser, game_file):
    if args.value is None:
        parser.error("--value 是必需的 (搜索关键词)")
    dialogue.cmd_search_sctext(game_file, args.value, args.limit)


def _spawn_obj_data_win(args, parser, game_file):
    if args.value is None or args.key is None:
        parser.error("--value (房间名) 和 --key (对象名) 是必需的")
    room.cmd_spawn_obj(game_file, args.value, args.key, args.x, args.y)


def _npc_dialogue_data_win(args, parser, game_file):
    if args.value is None or args.key is None:
        parser.error("--value (房间名) 和 --key (对象名) 是必需的")
    if args.text_key is None or args.text is None:
        parser.error("--text-key (textdata key) 和 --text (对话内容) 是必需的")
    npc.cmd_npc_dialogue(game_file, args.value, args.key, args.x, args.y,
                     args.text_key, args.text,
                     face=args.face, emotion=args.emotion, once=args.once,
                     range_=args.range)


def _npc_choice_data_win(args, parser, game_file):
    if args.value is None or args.key is None:
        parser.error("--value (房间名) 和 --key (对象名) 是必需的")
    if args.text_key is None or args.text is None:
        parser.error("--text-key (选择文本 key) 和 --text (选择文本) 是必需的")
    npc.cmd_npc_choice(game_file, args.value, args.key, args.x, args.y,
                   args.text_key, args.text,
                   yes_key=args.yes_text_key, yes_text=args.yes_text,
                   no_key=args.no_text_key, no_text=args.no_text,
                   face=args.face, emotion=args.emotion, range_=args.range,
                   goto_room=args.goto, item_id=args.item,
                   repeat=args.repeat)


def _guard_npc_alarm_data_win(args, parser, game_file):
    if args.key is None or args.instance is None:
        parser.error("--key (对象名) 和 --instance (实例 ID) 是必需的")
    npc.cmd_guard_npc_alarm(game_file, args.key, args.instance, text_key=args.text_key)


def _verify_nsid_data_win(args, parser, game_file):
    npc.cmd_verify_nsid(game_file, fix=args.fix)


def _verify_instances_data_win(args, parser, game_file):
    npc.cmd_verify_instances(game_file, fix=args.fix)


def _verify_code_data_win(args, parser, game_file):
    if args.key is None:
        parser.error("--key (代码条目名) 是必需的")
    _stable = verify.cmd_verify_code(game_file, args.key, show_asm=args.asm)
    if _stable is False:
        sys.exit(1)  # 往返不稳定（WARN）必须非零退出


def _diff_snapshots_data_win(args, parser, game_file):
    if args.key is None or args.value is None:
        parser.error("--key (基线文件) 和 --value (对比文件) 是必需的")
    verify.cmd_diff_snapshots(Path(args.key).expanduser(), Path(args.value).expanduser())


def _smoke_test_data_win(args, parser, game_file):
    # 注意: --dir 在 data_win 语境下是游戏数据文件；存档目录固定走默认定位
    _ok = verify.cmd_smoke_test(game_file, paths.find_save_dir(None),
                   room_name=args.value or "room_torielroom",
                   obj_name=args.key or "obj_cactus",
                   x=args.x if args.x is not None else 160,
                   y=args.y if args.y is not None else 150,
                   timeout=args.timeout or 120,
                   send_keys=args.keys or "external")
    if not _ok:
        sys.exit(1)  # FAIL 必须非零退出，否则自动化无法感知


def _create_door_data_win(args, parser, game_file):
    if args.value is None or args.key is None:
        parser.error("--value (当前房间名) 和 --key (目标房间名) 是必需的")
    door.cmd_create_door(game_file, args.value, args.key,
                    args.x, args.y, args.spawn_x, args.spawn_y)


def _list_doors_data_win(args, parser, game_file):
    if args.value is None:
        parser.error("--value 是必需的 (房间名)")
    door.cmd_list_doors(game_file, args.value)


def _remove_door_data_win(args, parser, game_file):
    if args.value is None:
        parser.error("--value 是必需的 (房间名)")
    if not args.all and not ((args.x_raw is not None) and (args.y_raw is not None)):
        parser.error("--x 和 --y (坐标) 或 --all (全部移除) 是必需的")
    door.cmd_remove_door(game_file, args.value,
                    args.x if (args.x_raw is not None) else None,
                    args.y if (args.y_raw is not None) else None,
                    remove_all=args.all)


def _create_pit_data_win(args, parser, game_file):
    if args.value is None or args.key is None:
        parser.error("--value (当前房间名) 和 --key (目标房间名) 是必需的")
    door.cmd_create_pit(game_file, args.value, args.key,
                   args.x, args.y, args.spawn_x, args.spawn_y)


def _create_battle_data_win(args, parser, game_file):
    if args.value is None or args.key is None:
        parser.error("--value (房间名) 和 --key (battlegroup ID) 是必需的")
    try:
        bg_id = int(args.key)
    except ValueError:
        parser.error("--key 必须是数字 (battlegroup ID)")
    door.cmd_create_battle(game_file, args.value, bg_id,
                      border=args.border, x=args.x, y=args.y)


def _remove_obj_data_win(args, parser, game_file):
    if args.value is None:
        parser.error("--value 是必需的 (房间名)")
    if args.instance is None and args.key is None:
        parser.error("--instance (实例 ID) 或 --key (对象名) 是必需的")
    room.cmd_remove_obj(game_file, args.value, args.key or "",
                   instance_id=args.instance, remove_all=args.all)


def _room_info_data_win(args, parser, game_file):
    if args.value is None:
        parser.error("--value 是必需的 (房间名)")
    room.cmd_room_info(game_file, args.value)


def _create_room_data_win(args, parser, game_file):
    if args.value is None:
        parser.error("--value 是必需的 (房间内部名)")
    room.cmd_create_room(game_file, args.value, args.width, args.height,
                    args.speed, args.caption, args.bg_color)


def _set_room_bg_data_win(args, parser, game_file):
    if args.value is None:
        parser.error("--value 是必需的 (房间名)")
    room.cmd_set_room_bg(game_file, args.value, args.index,
                    enable=utmt._bool_or_none(args.enable),
                    bg_name=args.bg,
                    foreground=utmt._bool_or_none(args.foreground),
                    x=(args.x if (args.x_raw is not None) else None),
                    y=(args.y if (args.y_raw is not None) else None),
                    speedx=args.speedx, speedy=args.speedy,
                    tiled_h=utmt._bool_or_none(args.tiled_h),
                    tiled_v=utmt._bool_or_none(args.tiled_v),
                    stretch=utmt._bool_or_none(args.stretch),
                    keep_bg_color=args.keep_bg_color)


def _set_room_solid_bg_data_win(args, parser, game_file):
    if args.value is None or args.color is None:
        parser.error("--value (房间名) 和 --color (6位hex RGB) 是必需的")
    try:
        room._parse_layers(args.layers)
    except ValueError as e:
        parser.error(str(e))
    room.cmd_set_room_solid_bg(game_file, args.value, args.color,
                          asset_name=args.asset_name,
                          layers=args.layers,
                          runtime=not args.no_runtime)


def _room_bg_info_data_win(args, parser, game_file):
    if args.value is None:
        parser.error("--value 是必需的 (房间名)")
    room.cmd_room_bg_info(game_file, args.value)


def _set_room_prop_data_win(args, parser, game_file):
    if args.value is None:
        parser.error("--value 是必需的 (房间名)")
    room.cmd_set_room_prop(game_file, args.value,
                      width=args.width, height=args.height,
                      speed=args.speed, caption=args.caption,
                      bg_color=args.bg_color,
                      persistent=args.persistent)


def _set_room_view_data_win(args, parser, game_file):
    if args.value is None:
        parser.error("--value 是必需的 (房间名)")
    room.cmd_set_room_view(game_file, args.value, args.index,
                      enable=utmt._bool_or_none(args.enable),
                      view_w=args.view_w, view_h=args.view_h,
                      port_w=args.port_w, port_h=args.port_h,
                      follow=args.follow,
                      border_x=args.border_x, border_y=args.border_y)


def _list_game_bgs_data_win(args, parser, game_file):
    room.cmd_list_game_bgs(game_file, args.value or "")


def _create_bg_asset_data_win(args, parser, game_file):
    if args.value is None or args.image is None:
        parser.error("--value (背景名) 和 --image (PNG 路径) 是必需的")
    room.cmd_create_bg_asset(game_file, args.value, args.image)


def _gml_bg_data_win(args, parser, game_file):
    if args.value is None or args.bg is None:
        parser.error("--value (房间名) 和 --bg (背景名/ID) 是必需的")
    try:
        room._parse_layers(args.layers)
    except ValueError as e:
        parser.error(str(e))
    room.cmd_gml_bg(game_file, args.value, args.bg, args.slot,
               args.speedx, args.speedy,
               layers=args.layers, all_layers=args.all_layers,
               hide_above=args.hide_above,
               vtiled=(utmt._bool_or_none(args.tiled_v) is not False),
               foreground=(utmt._bool_or_none(args.foreground) is True))


def _remove_tile_data_win(args, parser, game_file):
    if args.value is None:
        parser.error("--value 是必需的 (房间名)")
    room.cmd_remove_tile(game_file, args.value, instance=args.instance)


def _handler_extract_data_win(args, parser, game_file):
    code.cmd_handler_extract(game_file, apply=args.apply)


def _append_code_data_win(args, parser, game_file):
    if args.key is None or args.value is None:
        parser.error("--key (代码名) 和 --value (GML) 是必需的")
    code.cmd_code_append(game_file, args.key, args.value, value_is_file=args.file_path)


def _prepend_code_data_win(args, parser, game_file):
    if args.key is None or args.value is None:
        parser.error("--key (代码名) 和 --value (GML) 是必需的")
    code.cmd_code_prepend(game_file, args.key, args.value, value_is_file=args.file_path)


def _batch_add_textentry_data_win(args, parser, game_file):
    if args.value is None:
        parser.error("--value 是必需的 (JSON 文件路径)")
    dialogue.cmd_batch_textdata(game_file, args.value,
                       face=args.face, emotion=args.emotion)


def _list_sprites_data_win(args, parser, game_file):
    sprite.cmd_sprite_list(game_file, args.limit)


def _search_sprite_data_win(args, parser, game_file):
    if args.value is None:
        parser.error("--value 是必需的 (搜索关键词)")
    sprite.cmd_sprite_search(game_file, args.value, args.limit)


def _get_obj_data_win(args, parser, game_file):
    if args.key is None:
        parser.error("--key 是必需的 (对象名称)")
    sprite.cmd_obj_get(game_file, args.key)


def _set_obj_sprite_data_win(args, parser, game_file):
    if args.key is None or args.value is None:
        parser.error("--key (对象名) 和 --value (精灵名) 是必需的")
    sprite.cmd_obj_set_sprite(game_file, args.key, args.value)


def _list_textures_data_win(args, parser, game_file):
    sprite.cmd_texture_list(game_file, args.limit)


def _export_sprite_data_win(args, parser, game_file):
    if args.key is None:
        parser.error("--key 是必需的 (精灵名)")
    if args.json:
        sprite._export_sprite_json(game_file, args.key)
    else:
        if args.value is None:
            parser.error("--value 是必需的 (路径)")
        # --value 以 .png 结尾且未显式指定 --frame 时，按"单帧导出到文件"处理
        if args.frame is not None:
            frame = args.frame
        elif args.value.lower().endswith(".png"):
            frame = 0
        else:
            frame = -1
        sprite.cmd_sprite_export(game_file, args.key, args.value, frame=frame)


def _replace_sprite_data_win(args, parser, game_file):
    if args.key is None or args.value is None:
        parser.error("--key (精灵名) 和 --value (PNG 路径) 是必需的")
    sprite.cmd_sprite_replace(game_file, args.key, args.value, frame=args.frame if args.frame is not None else 0, all_frames=args.all)


def _duplicate_sprite_data_win(args, parser, game_file):
    if args.key is None or args.value is None:
        parser.error("--key (源精灵名) 和 --value (新精灵名) 是必需的")
    sprite.cmd_sprite_duplicate(game_file, args.key, args.value)


def _preview_sprite_data_win(args, parser, game_file):
    if args.key is None:
        parser.error("--key 是必需的 (精灵名)")
    sprite.cmd_sprite_preview(game_file, args.key)


def _colorize_sprite_data_win(args, parser, game_file):
    if args.key is None or args.value is None or args.hue_from is None or args.hue_to is None:
        parser.error("--key (源), --value (目标名), --hue-from (如 180-260), --hue-to (目标色相) 是必需的")
    try:
        hf = tuple(float(x) / 360.0 for x in args.hue_from.split("-"))
    except Exception:
        parser.error("--hue-from 格式错误，应为 \"180-260\"")
    sprite.cmd_sprite_colorize(game_file, args.key, args.value, hue_from=hf, hue_to=args.hue_to)


def _export_texture_data_win(args, parser, game_file):
    if args.value is None:
        parser.error("--value 是必需的 (输出目录)")
    sprite.cmd_texture_export(game_file, args.key, args.value)


def _replace_texture_data_win(args, parser, game_file):
    if args.key is None or args.value is None:
        parser.error("--key (纹理名) 和 --value (PNG 路径) 是必需的")
    sprite.cmd_texture_replace(game_file, args.key, args.value)


def _dump_sprites_data_win(args, parser, game_file):
    if args.value is None:
        parser.error("--value 是必需的 (输出目录)")
    sprite.cmd_sprite_dump_all(game_file, args.value)


def _cjk_font_data_win(args, parser, game_file):
    if args.value is None:
        parser.error("--value 是必需的 (font_cjk_build.py 输出目录)")
    build_dir = Path(args.value).expanduser()
    if state.PREVIEW:
        with tempfile.TemporaryDirectory(prefix="deterline-font-") as directory:
            ok = cjk.cmd_cjk_font(game_file, build_dir, Path(directory))
    else:
        work_dir = Path(args.work_dir).expanduser() if args.work_dir else None
        ok = cjk.cmd_cjk_font(game_file, build_dir, work_dir)
    if not ok:
        sys.exit(1)



def _cjk_trigger_data_win(args, parser, game_file):
    if args.text is None:
        parser.error("--text 是必需的 (对话文本)")
    if not cjk.cmd_cjk_trigger(game_file, args.room, args.object,
                           220 if args.x_raw is None else args.x_raw,
                           330 if args.y_raw is None else args.y_raw,
                           args.typer, args.text,
                           wrap=not args.no_wrap,
                           width_room_px=args.width):
        sys.exit(1)  # Step_1 字节级体检 WARN 必须非零退出


def _cjk_check_data_win(args, parser, game_file):
    if args.text is None and args.value is None:
        parser.error("--text 传文本 或 --value 传文本文件路径，二选一")
    if args.text is not None and args.value is not None:
        parser.error("--text 与 --value 互斥（复核 P2-3：并给时此前静默 --value 胜）")
    cjk.cmd_cjk_check(args.text,
                      Path(args.glyphs) if args.glyphs else None,
                      Path(args.value) if args.value else None)


def _list_file0(args, parser, save_dir):
    file0.cmd_file0_list(save_dir)


def _find_file0(args, parser, save_dir):
    if args.value is None:
        parser.error("--value 是必需的 (搜索目标值)")
    file0.cmd_file0_find(save_dir, args.value)


def _get_file0(args, parser, save_dir):
    if not args.key:
        parser.error("--key 是必需的")
    file0.cmd_file0_get(save_dir, args.key)


def _set_file0(args, parser, save_dir):
    if not args.key or args.value is None:
        parser.error("--key 和 --value 是必需的")
    file0.cmd_file0_set(save_dir, args.key, args.value)


def _list_ini(args, parser, save_dir):
    inifile.cmd_ini_list(save_dir)


def _room_list_ini(args, parser, save_dir):
    room.cmd_room_list(args.value or "")


def _get_ini(args, parser, save_dir):
    if not args.key:
        parser.error("--key 是必需的")
    inifile.cmd_ini_get(save_dir, args.section, args.key)


def _set_ini(args, parser, save_dir):
    if not args.key or args.value is None:
        parser.error("--key 和 --value 是必需的")
    inifile.cmd_ini_set(save_dir, args.section, args.key, args.value)


def _find_ini(args, parser, save_dir):
    print("find 仅支持 file0 (在 INI 中用 get 或 list)", file=sys.stderr)
    sys.exit(1)


def _undo_ini(args, parser, save_dir):
    if not args.value:
        parser.error("--value 是必需的 (ini, file0, 或 data_win)")
    save_cmds.cmd_undo(save_dir, args.value, backup_ts=args.backup,
             dir_override=args.dir)


def _list_backups_ini(args, parser, save_dir):
    if not args.value:
        parser.error("--value 是必需的 (ini, file0, 或 data_win)")
    save_cmds.cmd_list_backups(save_dir, args.value, dir_override=args.dir)


def _create_system_info_ini(args, parser, save_dir):
    if args.value is None:
        parser.error("--value 是必需的 (962 或 963)")
    save_cmds.cmd_create_system_info(save_dir, args.value)


def _quest_init_ini(args, parser, save_dir):
    flag_idx = args.flag if args.flag is not None else config.FLAG_CUSTOM_START
    dialogue.cmd_quest_init(save_dir, flag_idx)


def _quest_status_ini(args, parser, save_dir):
    dialogue.cmd_quest_status(save_dir)


def _reset_all_ini(args, parser, save_dir):
    save_cmds.cmd_reset_all(save_dir)


def _experiment_snapshot_ini(args, parser, save_dir):
    save_cmds.cmd_experiment_snapshot(save_dir, args.value)


def _experiment_list_ini(args, parser, save_dir):
    save_cmds.cmd_experiment_list(save_dir)


def _experiment_restore_ini(args, parser, save_dir):
    if not args.value:
        parser.error("--value 是必需的 (快照标签)")
    save_cmds.cmd_experiment_restore(save_dir, args.value)


def _reset_flags_ini(args, parser, save_dir):
    save_cmds.cmd_reset_flags(save_dir)

COMMANDS = {
    "get": {"file0": _get_file0, "ini": _get_ini},
    "set": {"file0": _set_file0, "ini": _set_ini},
    "list": {"file0": _list_file0, "ini": _list_ini},
    "find": {"file0": _find_file0, "ini": _find_ini},
    "reset-flags": {"ini": _reset_flags_ini},
    "reset-all": {"ini": _reset_all_ini},
    "room-list": {"ini": _room_list_ini},
    "create-system-info": {"ini": _create_system_info_ini},
    "undo": {"any": _undo_ini},
    "list-backups": {"any": _list_backups_ini},
    "list-strings": {"data_win": _list_strings_data_win},
    "get-string": {"data_win": _get_string_data_win},
    "set-string": {"data_win": _set_string_data_win},
    "add-string": {"data_win": _add_string_data_win},
    "delete-string": {"data_win": _delete_string_data_win},
    "replace-string": {"data_win": _replace_string_data_win},
    "search-strings": {"data_win": _search_strings_data_win},
    "list-codes": {"data_win": _list_codes_data_win},
    "decompile-code": {"data_win": _decompile_code_data_win},
    "replace-code": {"data_win": _replace_code_data_win},
    "find-replace-code": {"data_win": _find_replace_code_data_win},
    "append-code": {"data_win": _append_code_data_win},
    "prepend-code": {"data_win": _prepend_code_data_win},
    "search-textdata": {"data_win": _search_textdata_data_win},
    "add-textentry": {"data_win": _add_textentry_data_win},
    "update-textentry": {"data_win": _update_textentry_data_win},
    "delete-textentry": {"data_win": _delete_textentry_data_win},
    "batch-add-textentry": {"data_win": _batch_add_textentry_data_win},
    "guided-add-dialogue": {"data_win": _guided_add_dialogue_data_win},
    "search-vars": {"data_win": _search_vars_data_win},
    "search-code": {"data_win": _search_vars_data_win},
    "create-script": {"data_win": _create_script_data_win},
    "room-objects": {"data_win": _room_objects_data_win},
    "search-sctext": {"data_win": _search_sctext_data_win},
    "spawn-obj": {"data_win": _spawn_obj_data_win},
    "remove-obj": {"data_win": _remove_obj_data_win},
    "npc-dialogue": {"data_win": _npc_dialogue_data_win},
    "npc-choice": {"data_win": _npc_choice_data_win},
    "guard-npc-alarm": {"data_win": _guard_npc_alarm_data_win},
    "quest-init": {"ini": _quest_init_ini},
    "quest-status": {"ini": _quest_status_ini},
    "sandbox-restore": {"any": _sandbox_restore},
    "list-sprites": {"data_win": _list_sprites_data_win},
    "search-sprite": {"data_win": _search_sprite_data_win},
    "get-obj": {"data_win": _get_obj_data_win},
    "set-obj-sprite": {"data_win": _set_obj_sprite_data_win},
    "list-textures": {"data_win": _list_textures_data_win},
    "export-sprite": {"data_win": _export_sprite_data_win},
    "replace-sprite": {"data_win": _replace_sprite_data_win},
    "duplicate-sprite": {"data_win": _duplicate_sprite_data_win},
    "preview-sprite": {"data_win": _preview_sprite_data_win},
    "colorize-sprite": {"data_win": _colorize_sprite_data_win},
    "export-texture": {"data_win": _export_texture_data_win},
    "replace-texture": {"data_win": _replace_texture_data_win},
    "dump-sprites": {"data_win": _dump_sprites_data_win},
    "experiment-snapshot": {"ini": _experiment_snapshot_ini},
    "experiment-list": {"ini": _experiment_list_ini},
    "experiment-restore": {"ini": _experiment_restore_ini},
    "room-info": {"data_win": _room_info_data_win},
    "create-room": {"data_win": _create_room_data_win},
    "set-room-bg": {"data_win": _set_room_bg_data_win},
    "set-room-prop": {"data_win": _set_room_prop_data_win},
    "set-room-view": {"data_win": _set_room_view_data_win},
    "list-game-bgs": {"data_win": _list_game_bgs_data_win},
    "create-bg-asset": {"data_win": _create_bg_asset_data_win},
    "gml-bg": {"data_win": _gml_bg_data_win},
    "set-room-solid-bg": {"data_win": _set_room_solid_bg_data_win},
    "room-bg-info": {"data_win": _room_bg_info_data_win},
    "remove-tile": {"data_win": _remove_tile_data_win},
    "handler-extract": {"data_win": _handler_extract_data_win},
    "create-door": {"data_win": _create_door_data_win},
    "list-doors": {"data_win": _list_doors_data_win},
    "remove-door": {"data_win": _remove_door_data_win},
    "create-pit": {"data_win": _create_pit_data_win},
    "create-battle": {"data_win": _create_battle_data_win},
    "verify-nsid": {"data_win": _verify_nsid_data_win},
    "verify-instances": {"data_win": _verify_instances_data_win},
    "verify-code": {"data_win": _verify_code_data_win},
    "smoke-test": {"data_win": _smoke_test_data_win},
    "diff-snapshots": {"data_win": _diff_snapshots_data_win},
    "set-derived": {"any": _set_derived},
    "cjk-font": {"data_win": _cjk_font_data_win},
    "cjk-trigger": {"data_win": _cjk_trigger_data_win},
    "cjk-check": {"data_win": _cjk_check_data_win},
    "doctor": {"any": _doctor},
    "md5": {"any": _md5},
}

# Query commands keep reading the source by default; --sandbox/--workspace select a copy.
GAME_QUERIES = {
    "list-strings", "get-string", "search-strings", "list-codes", "decompile-code",
    "search-textdata", "search-vars", "search-code", "room-objects", "search-sctext",
    "verify-code", "diff-snapshots", "list-doors", "room-info", "list-game-bgs",
    "room-bg-info", "list-sprites", "search-sprite", "get-obj", "list-textures",
    "export-sprite", "preview-sprite", "export-texture", "dump-sprites", "cjk-check",
}


def edits_game(args) -> bool:
    if args.action in {"verify-nsid", "verify-instances"}:
        return args.fix
    if args.action == "handler-extract":
        return args.apply
    if args.action in {"replace-code", "find-replace-code"} and args.dry_run:
        return False
    return args.action not in GAME_QUERIES
