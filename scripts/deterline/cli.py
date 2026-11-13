"""Parse legacy CLI options and dispatch through the command registry."""

import argparse
import sys

from . import command_handlers, errors, paths, sandbox, state, utmt

ACTION_CHOICES = list(command_handlers.COMMANDS)


def main():
    parser = argparse.ArgumentParser(
        description="UNDERTALE Save Editor — 修改 undertale.ini / file0",
        epilog="""
示例:
  %(prog)s --action get  --key Love
  %(prog)s --action set  --key LOVE --value 20
  %(prog)s --action set  --key Kills --value 0
  %(prog)s --action set  --key Room --value 31
  %(prog)s --action set  --key Room --value "安黛因竞技场"
  %(prog)s --action list
  %(prog)s --action room-list
  %(prog)s --action room-list --value 瀑布
  %(prog)s --action reset-flags
  %(prog)s --action reset-all   # 全量重置（BOSS、物品、击杀、plot），保留自定义 flag
  %(prog)s --action set  --key HP  --value 99 --file file0
  %(prog)s --action get  --key HP  --file file0
  %(prog)s --action list --file file0
  %(prog)s --action set  --key WEAPON --value 51 --file file0   (自动 AT=99)
  %(prog)s --action set  --key TORIEL --value 5 --file file0    (宽恕)
  %(prog)s --action set  --key RUINS_KILLS --value 20 --file file0
  %(prog)s --action create-system-info --value 962
  
  # Dialogue editing (game.ios / data.win) — via UndertaleModTool
  %(prog)s --action list-strings --file data_win --limit 10
  %(prog)s --action get-string --key 500 --file data_win
  %(prog)s --action set-string --key 500 --value "Hello" --file data_win
  %(prog)s --action add-string --value "新对话内容" --file data_win
  %(prog)s --action delete-string --key 50000 --file data_win
  %(prog)s --action search-strings --value "Toriel" --file data_win
  %(prog)s --action replace-string --old "Toriel" --value "TORIEL" --file data_win
  
  # Code editing (game.ios / data.win) — via UndertaleModTool
  %(prog)s --action list-codes --file data_win --limit 10
  %(prog)s --action decompile-code --key "gml_Object_obj_dialoguer_Create_0" --file data_win
  %(prog)s --action replace-code --key "gml_Script_test" --value "return 0;" --file data_win
  %(prog)s --action replace-code --key "gml_Script_test" --value "./mycode.gml" --file-path --file data_win
  %(prog)s --action find-replace-code --key "gml_Object_obj_dialoguer_Step_0" --old "old_code" --value "new_code" --file data_win
  
  # Text data editing (game.ios / data.win) — via UndertaleModTool
  %(prog)s --action search-textdata --value "darksans1" --file data_win
  %(prog)s --action add-textentry --key "obj_myevent_001" --value "我的新对话/" --file data_win
  %(prog)s --action delete-textentry --key "obj_test_entry" --file data_win
  
  # Variable/code search
  %(prog)s --action search-vars --value "global.flag" --file data_win
  %(prog)s --action create-script --key "gml_Script_myFunc" --value "return 0;" --file data_win
  
  # Room inspection
  %(prog)s --action room-objects --value "torielroom" --file data_win

  # Room layout editing
  %(prog)s --action spawn-obj --value "room_asrielroom" --key "obj_dummy1" --x 160 --y 120 --file data_win
  %(prog)s --action remove-obj --value "room_asrielroom" --instance 113930 --file data_win
  %(prog)s --action remove-obj --value "room_asrielroom" --key "obj_dummy1" --all --file data_win

  # Safe NPC dialogue (one-shot: spawn + textdata + flag-state trigger + Alarm_0 guard)
  %(prog)s --action npc-dialogue --value "room_torielroom" --key "obj_cactus" --x 170 --y 180 --text-key "obj_cactus_deterline" --text "* Stay determined!/%%" --file data_win
  # Guard an existing NPC whose myinteract trigger overlaps native dialogue
  %(prog)s --action guard-npc-alarm --key "obj_cactus" --instance 113927 --text-key "obj_cactus_deterline" --file data_win
  # Single-trigger NPC dialogue (NPC self-destructs after trigger; no movement lock)
  %(prog)s --action npc-dialogue --value "room_asrielroom" --key "obj_dummy1" --x 170 --y 180 --text-key "obj_dummy_hi" --text "* Hi!/%%" --once --file data_win
  # Choice NPC: YES/NO box + follow-up texts + teleport on YES (single-trigger by default)
  %(prog)s --action npc-choice --value "room_water_undynefinal" --key "obj_kitchentable" --x 160 --y 420 --text-key "obj_table_ask" --text "* Let's go?& &         Yes         No      \\C " --yes-text-key "obj_table_yes" --yes-text "* Okay!/%%" --no-text-key "obj_table_no" --no-text "* .../%%" --goto "雪镇 - 船夫(妇)" --item 48 --range 160 --file data_win
  # Check for corrupted variable NameStringID (crash trap), --fix to repair
  %(prog)s --action verify-nsid --file data_win
  %(prog)s --action verify-nsid --fix --file data_win
  %(prog)s --action verify-instances --file data_win
  %(prog)s --action verify-instances --fix --file data_win

  # Lock LV-derived stats so the game stops recomputing them (writes file0 + patches game scripts)
  %(prog)s --action set-derived --key HP --value 50
  %(prog)s --action set-derived --key AT --value 99

  # Code append/prepend (新增，无需完全替换)
  %(prog)s --action append-code --key "gml_Object_obj_dummy1_Step_0" --value "if (global.flag[510]==99) instance_destroy();" --file data_win
  %(prog)s --action append-code --key "gml_Object_obj_dummy1_Step_0" --value "./append.gml" --file-path --file data_win
  %(prog)s --action prepend-code --key "gml_Object_obj_dummy1_Step_0" --value "// custom code here" --file data_win

  # Batch import dialogues from JSON
  %(prog)s --action batch-add-textentry --value "./dialogues.json" --face 3 --file data_win

  # Quest management
  %(prog)s --action quest-init
  %(prog)s --action quest-init --flag 511
  %(prog)s --action quest-status

  # SCR_TEXT case search
  %(prog)s --action search-sctext --value "Toriel" --file data_win
  
  # P4-1 Sprite/Texture replacement
  %(prog)s --action list-textures --file data_win --limit 10
  %(prog)s --action export-sprite --key "spr_sans_d" --value "sans.png" --frame 0 --file data_win
  %(prog)s --action replace-sprite --key "spr_sans_d" --value "sans_edit.png" --frame 0 --file data_win
  %(prog)s --action duplicate-sprite --key "spr_sans_d" --value "spr_sans_d_red" --file data_win
  %(prog)s --action colorize-sprite --key "spr_sans_d" --value "spr_sans_d_red" --hue-from "180-260" --hue-to 0 --file data_win
  %(prog)s --action preview-sprite --key "spr_sans_d" --file data_win
  %(prog)s --action export-texture --value "./textures" --file data_win
  %(prog)s --action replace-texture --key "Texture 0" --value "tex0.png" --file data_win
  %(prog)s --action dump-sprites --value "./sprites" --file data_win

  # Experiment snapshots (isolate experiments from each other)
  %(prog)s --action experiment-snapshot --value "sans_face_test"
  %(prog)s --action experiment-list
  %(prog)s --action experiment-restore --value "sans_face_test"

  # Backups
  %(prog)s --action list-backups --value data_win
  %(prog)s --action undo --value data_win --backup 20240714_193500
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--action", required=True,
                        choices=ACTION_CHOICES)
    parser.add_argument("--key", help="键名或数字索引 (file0 用数字)")
    parser.add_argument("--value", help="要设置/搜索的值 (set/find 操作必需)")
    parser.add_argument("--old", help="replace-string 的旧文本 (decompile-code 兼容别名，等同 --search)")
    parser.add_argument("--search", help="decompile-code: 仅显示匹配该文本的行 (等同行过滤)")
    parser.add_argument("--preview", action="store_true",
                        help="运行检查并预览拟写入文件，不提交编辑方案")
    parser.add_argument("--dry-run", action="store_true",
                        help="预览替换结果/匹配数，不写入文件 (replace-code/find-replace-code 用)")
    parser.add_argument("--section", default="General",
                        help="INI 节名 (默认: General)")
    parser.add_argument("--file", choices=["ini", "file0", "data_win"], default="ini",
                        help="目标文件 (默认: ini)")
    parser.add_argument("--dir", help="手动指定存档目录或游戏数据文件路径 (backup-index/recovery-scan 亦接受含 game.ios/data.win 的目录)")
    parser.add_argument("--limit", type=int, default=30,
                        help="最大显示条数 (默认: 30)")
    parser.add_argument("--offset", type=int, default=0,
                        help="起始偏移 (list-strings 用)")
    parser.add_argument("--hex", action="store_true",
                        help="显示十六进制 (list-strings 用)")
    parser.add_argument("--file-path", action="store_true",
                        help="--value 是文件路径而非内联内容 (replace-code 用)")
    parser.add_argument("--backup", type=str, default=None,
                        help="备份时间戳 (undo 恢复到指定版本, list-backups 可查看)")
    parser.add_argument("--x", type=int, default=None,
                        help="X 坐标 (spawn-obj/create-door 用, 默认: 320)")
    parser.add_argument("--y", type=int, default=None,
                        help="Y 坐标 (spawn-obj/create-door 用, 默认: 240)")
    parser.add_argument("--spawn-x", type=int, default=160,
                        help="目标房间出生 X (create-door 用, 默认: 160)")
    parser.add_argument("--spawn-y", type=int, default=120,
                        help="目标房间出生 Y (create-door 用, 默认: 120)")
    parser.add_argument("--border", type=int, default=0,
                        help="战斗边框样式 (create-battle 用, 默认: 0)")
    parser.add_argument("--all", action="store_true",
                        help="移除所有匹配实例 (remove-obj 用)")
    parser.add_argument("--instance", type=int, default=None,
                        help="实例 ID (remove-obj 用, 优先级高于 --key 匹配)")
    parser.add_argument("--face", type=int, default=0,
                        help="头像角色 (0=无, 1=Toriel, 2=Flowey, 3=Sans, 4=Papyrus, 5=Undyne, 6=Alphys, 7=Asgore, 8=Mettaton, 9=Asriel)")
    parser.add_argument("--emotion", type=int, default=0,
                        help="头像表情 (Sans: 0=普通, 1=轻笑, 2=眨眼, 3=慢眨眼, 4=无眼)")
    parser.add_argument("--flag", type=int, default=None,
                        help="flag 索引 (quest-init 用, 默认 510)")
    parser.add_argument("--text-key", type=str, default=None,
                        help="textdata key (npc-dialogue/guard-npc-alarm/npc-choice 用)")
    parser.add_argument("--text", type=str, default=None,
                        help="对话文本 (npc-dialogue 用 ASCII；cjk-trigger 用 CJK，触发框全形态+预折行自动补全)")
    parser.add_argument("--yes-text-key", type=str, default=None,
                        help="YES 分支 textdata key (npc-choice 用)")
    parser.add_argument("--yes-text", type=str, default=None,
                        help="YES 分支对话内容 ASCII (npc-choice 用)")
    parser.add_argument("--no-text-key", type=str, default=None,
                        help="NO 分支 textdata key (npc-choice 用, 必需)")
    parser.add_argument("--no-text", type=str, default=None,
                        help="NO 分支对话内容 ASCII (npc-choice 用, 必需)")
    parser.add_argument("--goto", type=str, default=None,
                        help="YES 分支传送目标房间（中文名/ID，npc-choice 用）")
    parser.add_argument("--item", type=int, default=None,
                        help="YES 分支奖励物品 ID (npc-choice 用, 0-65)")
    parser.add_argument("--range", type=int, default=50,
                        help="触发距离像素 (npc-dialogue/npc-choice 用, 默认: 50)")
    parser.add_argument("--repeat", action="store_true",
                        help="可重复触发（走开再靠近可再触发；npc-choice 用，默认单次）")
    parser.add_argument("--frame", type=int, default=None,
                        help="帧索引 (export-sprite/replace-sprite 用, 默认: replace 全部帧的 0 / export 全部帧到目录; "
                             "export 时 --value 以 .png 结尾则默认单帧导出到该文件)")
    parser.add_argument("--show-diff", action="store_true",
                        help="替换代码时显示新旧 diff (replace-code 用)")
    parser.add_argument("--json", action="store_true",
                        help="以 JSON 输出结构化结果 (backup-index/recovery-scan/backup-prune 用; export-sprite 为附加元数据)")
    parser.add_argument("--keep-archives", type=int, default=3,
                        help="backup-prune 每目标保留的最近归档份数 (默认: 3)")
    parser.add_argument("--hue-from", type=str, default=None,
                        help="色相范围 \"min-max\" (colorize-sprite 用, 如 \"180-260\")")
    parser.add_argument("--hue-to", type=float, default=None,
                        help="目标色相角度 0-360 (colorize-sprite 用)")
    parser.add_argument("--workspace", type=sandbox.workspace_name,
                        help="选择独立实验工作区（读取也使用该工作区）")
    parser.add_argument("--sandbox", action="store_true",
                        help="沙箱模式: 在实验工作区副本上操作（v2 起写操作默认即沙箱，此参数保留为显式声明）")
    parser.add_argument("--commit", action="store_true",
                        help="v2 写入安全: 直写真实文件（默认写操作只落沙箱副本）；含 Steam 同步")
    parser.add_argument("--no-steam-sync", action="store_true",
                        help="v2 写入安全: 即使 --commit 也不同步 Steam 路径")
    parser.add_argument("--allow-cjk", action="store_true",
                        help="C3a: 放行 CJK 对话文本（需中文字体注入支持，否则显示空白）")
    parser.add_argument("--asm", action="store_true",
                        help="verify-code: 输出完整反汇编文本（ASM| 行）")
    parser.add_argument("--work-dir", type=str, default=None,
                        help="cjk-font: 中间产物目录（pass1 dump/图集；默认 game 文件旁 cjk_work/）")
    parser.add_argument("--room", type=str, default="room_ruins1",
                        help="cjk-trigger: 目标房间名（默认 room_ruins1）")
    parser.add_argument("--object", type=str, default="obj_cactus",
                        help="cjk-trigger: 承载触发块的对象名（其 Step_1 被追加；默认 obj_cactus）")
    parser.add_argument("--typer", type=int, default=31,
                        help="cjk-trigger: SCR_TEXTTYPE 编号（默认 31 = fnt_maintext spacing12；须在 CJK_TYPER_TABLE）")
    parser.add_argument("--glyphs", type=str, default=None,
                        help="cjk-check/cjk-trigger: 字形表路径（默认 build/font_cjk/glyphs.json）")
    parser.add_argument("--detail", action="store_true",
                        help="diff-snapshots: 输出资源级差异（字符串哈希/实例坐标/代码指纹/字体）")
    parser.add_argument("--expected", type=str, default=None,
                        help="diff-snapshots --detail: 声明允许改变的资源范围 JSON（范围外差异退出码 1）")
    parser.add_argument("--utmt-timeout", type=int, default=None,
                        help="diff-snapshots: 单次 UTMT 遍历超时（默认 300s，--detail 因全量反汇编指纹需更长）")
    parser.add_argument("--hash", action="store_true",
                        help="backup-index: 逐项追加 SHA-256（大文件耗时）")
    # cjk-trigger 复用全局 --x/--y/--text/--width：x,y=触发位（x 须<320）、text=对话文本、width=预折行宽度(房间像素)
    parser.add_argument("--no-wrap", action="store_true",
                        help="cjk-trigger: 关闭预折行（默认开）")
    parser.add_argument("--auto-snapshot", action="store_true",
                        help="每次写入操作前自动创建实验快照")
    parser.add_argument("--apply", action="store_true",
                        help="应用模式 (handler-extract 用, 默认仅诊断)")
    parser.add_argument("--once", action="store_true",
                        help="单次触发（触发后 NPC 自毁消失；不锁移动——状态机形态 v2.3.0 已废弃）")
    parser.add_argument("--timeout", type=int, default=None,
                        help="smoke-test 轮询超时秒数 (默认 120)")
    parser.add_argument("--keys", type=str, default=None, choices=["external", "osascript"],
                        help="smoke-test 按键模式: external(默认,由调用方按键)/osascript(盲发 Z,需辅助功能权限)")
    parser.add_argument("--fix", action="store_true",
                        help="自动修复 (verify-nsid 用: 重置损坏变量的 NameStringID；verify-instances 用: 为 ID=0/重复实例分配唯一 ID)")

    # Room editing (P4-2)
    parser.add_argument("--width", type=int, default=None,
                        help="房间宽度 (create-room/set-room-prop)；cjk-trigger: 预折行宽度（房间像素，默认 typer31=202 且不超该 typer 的 writingxend）")
    parser.add_argument("--height", type=int, default=None,
                        help="房间高度 (create-room/set-room-prop 用)")
    parser.add_argument("--speed", type=int, default=None,
                        help="房间帧率 (create-room/set-room-prop 用)")
    parser.add_argument("--caption", type=str, default="",
                        help="房间标题 (create-room/set-room-prop 用)")
    parser.add_argument("--bg-color", type=str, default="000000",
                        help="背景色 hex RGB (create-room/set-room-prop 用, 默认: 000000)")
    parser.add_argument("--persistent", action="store_true",
                        help="房间是否持久化 (set-room-prop 用)")
    parser.add_argument("--bg", type=str, default=None,
                        help="背景资源名 (set-room-bg/gml-bg 用; create-bg-asset 的资产名走 --value, PNG 走 --image)")
    parser.add_argument("--index", type=int, default=0,
                        help="背景/视图层索引 (set-room-bg/set-room-view 用, 默认: 0)")
    parser.add_argument("--enable", type=str, default=None,
                        help="启用/禁用 bool (set-room-bg/set-room-view 用)")
    parser.add_argument("--foreground", type=str, default=None,
                        help="是否前景层 bool (set-room-bg 用)")
    parser.add_argument("--speedx", type=float, default=None,
                        help="背景水平视差速度 (set-room-bg 用)")
    parser.add_argument("--speedy", type=float, default=None,
                        help="背景垂直视差速度 (set-room-bg 用)")
    parser.add_argument("--tiled-h", type=str, default=None,
                        help="水平平铺 bool (set-room-bg 用)")
    parser.add_argument("--tiled-v", type=str, default=None,
                        help="垂直平铺 bool (set-room-bg 用)")
    parser.add_argument("--stretch", type=str, default=None,
                        help="拉伸 bool (set-room-bg 用)")
    parser.add_argument("--follow", type=str, default=None,
                        help="视角跟随对象 (set-room-view 用, 如 obj_mainchara)")
    parser.add_argument("--view-w", type=int, default=None,
                        help="视图宽度 (set-room-view 用)")
    parser.add_argument("--view-h", type=int, default=None,
                        help="视图高度 (set-room-view 用)")
    parser.add_argument("--port-w", type=int, default=None,
                        help="视口宽度 (set-room-view 用)")
    parser.add_argument("--port-h", type=int, default=None,
                        help="视口高度 (set-room-view 用)")
    parser.add_argument("--border-x", type=int, default=None,
                        help="视图跟随水平边界 (set-room-view 用)")
    parser.add_argument("--border-y", type=int, default=None,
                        help="视图跟随垂直边界 (set-room-view 用)")
    parser.add_argument("--image", type=str, default=None,
                        help="PNG 图片路径 (create-bg-asset 用)")
    parser.add_argument("--slot", type=int, default=0,
                        help="背景槽位索引 (gml-bg 用, 默认: 0)")
    parser.add_argument("--layers", type=str, default=None,
                        help="背景层索引列表, 逗号分隔 (gml-bg/set-room-solid-bg 用, 如 0,1)")
    parser.add_argument("--all-layers", action="store_true",
                        help="应用到全部 8 个背景层 (gml-bg 用)")
    parser.add_argument("--hide-above", action="store_true",
                        help="隐藏目标层之上的所有层, 防止遮挡 (gml-bg 用)")
    parser.add_argument("--keep-bg-color", action="store_true",
                        help="启用背景层时保留 DrawBackgroundColor (set-room-bg 用)")
    parser.add_argument("--color", type=str, default=None,
                        help="纯色 hex RGB, 6 位 (set-room-solid-bg 用, 如 0000FF)")
    parser.add_argument("--asset-name", type=str, default=None,
                        help="背景资源名 (set-room-solid-bg 用, 默认 bg_solid_<color>)")
    parser.add_argument("--no-runtime", action="store_true",
                        help="只改房间数据, 不注入运行时覆盖 (set-room-solid-bg 用)")
    args = parser.parse_args()

    # --x/--y default to None so remove-door can require explicit coordinates;
    # other commands keep the historical 320/240 default.
    # cjk-trigger 用原始 None 判定（其默认 220/330 与 spawn 的 320/240 不同）
    args.x_raw = args.x
    args.y_raw = args.y
    if args.x is None:
        args.x = 320
    if args.y is None:
        args.y = 240

    # Activate sandbox mode
    if (args.sandbox or args.workspace) and args.commit:
        print("错误: --sandbox / --workspace 与 --commit 互斥（沙箱=彩排，commit=直写，二选一）", file=sys.stderr)
        sys.exit(2)
    if args.action == "smoke-test" and (args.preview or args.sandbox or args.workspace):
        parser.error("smoke-test 需要启动游戏，不能与预览或工作区一起使用")
    state.PREVIEW = args.preview
    if args.preview:
        print("预览模式：下面的修改方案不会提交。")
    state.WORKSPACE = args.workspace
    state.SANDBOX_ACTIVE = bool(args.sandbox or args.workspace)
    state.SANDBOX_ORIGINAL = None
    state.COMMIT_ACTIVE = args.commit
    state.NO_STEAM_SYNC = args.no_steam_sync
    state.ALLOW_CJK = args.allow_cjk
    state.AUTO_SNAPSHOT = args.auto_snapshot

    routes = command_handlers.COMMANDS[args.action]
    handler = routes.get("any") or routes.get(args.file)
    if handler is None:
        if args.file == "data_win":
            parser.error(f"'{args.action}' 不支持 data_win 文件")
        if args.file == "file0":
            parser.error(f"'{args.action}' 仅支持 INI 文件")
        parser.error(f"'{args.action}' 仅支持 --file data_win (游戏数据) 操作；"
                     "ini/file0 模式不适用该命令")

    try:
        if "any" in routes:
            handler(args, parser, None)
        elif args.file == "data_win":
            try:
                game_file = paths.find_game_data_file(args.dir)
            except FileNotFoundError:
                # diff-snapshots 的显式 A/B 输入不依赖默认游戏文件（B P2-3）；
                # 显式 --dir 无效仍须报错，不得静默回退。
                if args.action != "diff-snapshots" or args.dir:
                    raise
                game_file = None
            if args.action == "smoke-test":
                handler(args, parser, game_file)
            else:
                with utmt.game_edit(args.action, read_workspace=command_handlers.edits_game(args)):
                    handler(args, parser, game_file)
        else:
            handler(args, parser, paths.find_save_dir(args.dir))
    except (OSError, ValueError, IndexError, RuntimeError, errors.DeterlineError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
