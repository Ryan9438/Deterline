"""argparse 入口与 85 分支 dispatch（O2 步 10：main() 1:1 平移）。

1:1 平移；表驱动/subparsers 改造为独立后续项（方案 §2.2 步 10 明文）。
唯一声明内变更：--action 的 choices 字面量上提为模块级 ACTION_CHOICES
（gen_docs import-first 契约，O2-step0 地雷 #2；内容逐字节同源，--help
golden 逐字节断言护航）。dispatch 裸名经 AST 引导统一为模块属性形式
（与包纪律一致；mock 面不变——cmd 函数对象无 patch 消费者）。
"""

import argparse
import json
import os
import sys
from pathlib import Path

from . import (config, errors, file0, inifile, paths, state, utmt)
from .cmds import (cjk, code, dialogue, door, npc, room, save_cmds, sprite,
                   verify)

# gen_docs.authoritative_actions 的 import-first 契约（O1b/O2-step0）
ACTION_CHOICES = ["get", "set", "list", "find", "reset-flags", "reset-all",
                                 "room-list", "create-system-info", "undo",
                                 "list-backups",
                                 "list-strings", "get-string", "set-string",
                                 "add-string", "delete-string",
                                 "replace-string", "search-strings",
                                 "list-codes", "decompile-code",
                                 "replace-code", "find-replace-code",
                                 "append-code", "prepend-code",
                                  "search-textdata", "add-textentry", "update-textentry",
                                  "delete-textentry",
                                   "batch-add-textentry",
                                   "guided-add-dialogue",
                                 "search-vars", "search-code", "create-script",
                                   "room-objects", "search-sctext",
                                    "spawn-obj", "remove-obj",
                                    "npc-dialogue", "npc-choice", "guard-npc-alarm",
                                   "quest-init", "quest-status",
                                   "sandbox-restore",
                                   "list-sprites", "search-sprite",
                                   "get-obj", "set-obj-sprite",
                                   "list-textures", "export-sprite",
                                   "replace-sprite", "duplicate-sprite",
                                   "preview-sprite", "colorize-sprite",
                                   "export-texture", "replace-texture",
                                   "dump-sprites",
                                    "experiment-snapshot", "experiment-list",
                                    "experiment-restore",
                                    "room-info", "create-room",
                                    "set-room-bg", "set-room-prop", "set-room-view",
                                    "list-game-bgs", "create-bg-asset",
                                    "gml-bg", "set-room-solid-bg", "room-bg-info",
                                     "remove-tile",
                                     "handler-extract",
                                     "create-door",
                                     "list-doors",
                                     "remove-door",
                                     "create-pit",
                                     "create-battle",
                                     "verify-nsid", "verify-instances", "verify-code", "smoke-test", "diff-snapshots", "set-derived",
                                     "cjk-font", "cjk-trigger", "cjk-check", "md5"]


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
    parser.add_argument("--dry-run", action="store_true",
                        help="预览替换结果/匹配数，不写入文件 (replace-code/find-replace-code 用)")
    parser.add_argument("--section", default="General",
                        help="INI 节名 (默认: General)")
    parser.add_argument("--file", choices=["ini", "file0", "data_win"], default="ini",
                        help="目标文件 (默认: ini)")
    parser.add_argument("--dir", help="手动指定存档目录或游戏数据文件路径")
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
                        help="导出时同时输出 JSON 元数据 (export-sprite 用)")
    parser.add_argument("--hue-from", type=str, default=None,
                        help="色相范围 \"min-max\" (colorize-sprite 用, 如 \"180-260\")")
    parser.add_argument("--hue-to", type=float, default=None,
                        help="目标色相角度 0-360 (colorize-sprite 用)")
    parser.add_argument("--sandbox", action="store_true",
                        help="沙箱模式: 在 game.ios.sandbox 副本上操作（v2 起写操作默认即沙箱，此参数保留为显式声明）")
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
                        help="cjk-check: 字形表路径（默认 build/font_cjk/glyphs.json）")
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
    x_explicit = args.x is not None
    y_explicit = args.y is not None
    # cjk-trigger 用原始 None 判定（其默认 220/330 与 spawn 的 320/240 不同）
    args.x_raw = args.x
    args.y_raw = args.y
    if args.x is None:
        args.x = 320
    if args.y is None:
        args.y = 240

    # Activate sandbox mode
    if args.sandbox and args.commit:
        print("错误: --sandbox 与 --commit 互斥（沙箱=彩排，commit=直写，二选一）", file=sys.stderr)
        sys.exit(2)
    if args.sandbox:
        state.SANDBOX_ACTIVE = True
    if args.commit:
        state.COMMIT_ACTIVE = True
    if getattr(args, "no_steam_sync", False):
        state.NO_STEAM_SYNC = True
    if getattr(args, "allow_cjk", False):
        state.ALLOW_CJK = True
    if args.auto_snapshot:
        state.AUTO_SNAPSHOT = True

    # Handle sandbox-restore before file-type checks
    if args.action == "sandbox-restore":
        try:
            game_file = paths.find_game_data_file(args.dir)
            sandbox_path = game_file.with_suffix(game_file.suffix + ".sandbox")
            if not sandbox_path.exists():
                print(f"错误: 沙箱备份不存在: {sandbox_path}", file=sys.stderr)
                sys.exit(1)
            shutil.copy2(str(sandbox_path), str(game_file))
            sandbox_path.unlink()
            print(f"✓ 沙箱备份已恢复: {sandbox_path.name} → {game_file.name}")
        except FileNotFoundError as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # Handle md5 before file-type checks (read-only; prints game data file hash).
    # Lets a report include the raw hash so "did the file actually change?" is
    # verifiable in one line.
    if args.action == "md5":
        try:
            game_file = paths.find_game_data_file(args.dir)
        except FileNotFoundError as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)
        digest = hashlib.md5(game_file.read_bytes()).hexdigest()
        print(f"{digest}  {game_file}")
        return

    # Handle set-derived before file-type checks (touches both file0 and data_win)
    if args.action == "set-derived":
        if args.key is None or args.value is None:
            parser.error("set-derived 需要 --key (HP/MAXHP/AT/DF) 和 --value")
        try:
            save_dir = paths.find_save_dir(args.dir)
            game_file = paths.find_game_data_file(args.dir)
        except FileNotFoundError as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)
        try:
            code.cmd_set_derived(save_dir, game_file, args.key, args.value)
        except (FileNotFoundError, ValueError, RuntimeError, errors.DeterlineError) as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # ── Dialogue editor actions (data_win) ────────────────
    if args.file == "data_win":
        try:
            game_file = paths.find_game_data_file(args.dir)
        except FileNotFoundError as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)

        if state.SANDBOX_ACTIVE:
            sandbox_path = game_file.with_suffix(game_file.suffix + ".sandbox")
            print(f"🔒 沙箱模式: 所有操作作用于 {sandbox_path.name}", file=sys.stderr)

        try:
            if args.action == "list-strings":
                dialogue.cmd_strg_list(game_file, args.limit, args.offset, args.hex)
            elif args.action == "get-string":
                if args.key is None:
                    parser.error("--key 是必需的 (字符串索引)")
                dialogue.cmd_strg_get(game_file, int(args.key))
            elif args.action == "set-string":
                if args.key is None or args.value is None:
                    parser.error("--key 和 --value 是必需的")
                dialogue.cmd_strg_set(game_file, int(args.key), args.value)
            elif args.action == "add-string":
                if args.value is None:
                    parser.error("--value 是必需的 (新对话文本)")
                dialogue.cmd_strg_add(game_file, args.value)
            elif args.action == "delete-string":
                if args.key is None:
                    parser.error("--key 是必需的 (要删除的索引)")
                dialogue.cmd_strg_delete(game_file, int(args.key))
            elif args.action == "replace-string":
                if args.old is None or args.value is None:
                    parser.error("--old 和 --value 是必需的")
                dialogue.cmd_strg_replace(game_file, args.old, args.value)
            elif args.action == "search-strings":
                if args.value is None:
                    parser.error("--value 是必需的 (搜索关键词)")
                dialogue.cmd_strg_search(game_file, args.value, args.limit)
            elif args.action == "list-codes":
                code.cmd_code_list(game_file, args.limit, args.offset)
            elif args.action == "decompile-code":
                if args.key is None:
                    parser.error("--key 是必需的 (代码名称)")
                code.cmd_code_decompile(game_file, args.key, args.limit, search=args.search or args.old or "")
            elif args.action == "replace-code":
                if args.key is None or args.value is None:
                    parser.error("--key 和 --value 是必需的 (代码名称 + GML 源码或文件路径)")
                code.cmd_code_replace(game_file, args.key, args.value, value_is_file=args.file_path,
                                 show_diff=args.show_diff, dry_run=args.dry_run)
            elif args.action == "find-replace-code":
                if args.key is None or args.old is None or args.value is None:
                    parser.error("--key, --old 和 --value 是必需的")
                code.cmd_code_find_replace(game_file, args.key, args.old, args.value,
                                      show_diff=args.show_diff, dry_run=args.dry_run)
            elif args.action == "search-textdata":
                if args.value is None:
                    parser.error("--value 是必需的 (搜索关键词)")
                dialogue.cmd_textdata_search(game_file, args.value, args.limit)
            elif args.action == "add-textentry":
                if args.key is None or args.value is None:
                    parser.error("--key 和 --value 是必需的")
                dialogue.cmd_textdata_add(game_file, args.key, args.value,
                                 face=args.face, emotion=args.emotion)
            elif args.action == "guided-add-dialogue":
                if args.key is None or args.value is None:
                    parser.error("--key (文本 key) 和 --value (对话内容) 是必需的")
                dialogue.cmd_guided_add_dialogue(game_file, args.key, args.value,
                                        face=args.face, emotion=args.emotion)
            elif args.action == "delete-textentry":
                if args.key is None:
                    parser.error("--key 是必需的 (要删除的 textdata key)")
                dialogue.cmd_textdata_delete(game_file, args.key)
            elif args.action == "update-textentry":
                if args.key is None or args.value is None:
                    parser.error("--key 和 --value 是必需的 (已存在的 textdata key + 新文本)")
                dialogue.cmd_textdata_update(game_file, args.key, args.value,
                                    face=args.face, emotion=args.emotion)
            elif args.action in ("search-vars", "search-code"):
                if args.value is None:
                    parser.error("--value 是必需的 (变量名/精灵名/任意代码片段)")
                code.cmd_search_vars(game_file, args.value, args.limit)
            elif args.action == "room-objects":
                if args.value is None:
                    parser.error("--value 是必需的 (房间内部名，如 torielroom)")
                room.cmd_room_objects(game_file, args.value)
            elif args.action == "create-script":
                if args.key is None or args.value is None:
                    parser.error("--key 和 --value 是必需的 (代码名 + GML 源码或文件路径)")
                code.cmd_create_script(game_file, args.key, args.value, value_is_file=args.file_path)
            elif args.action == "search-sctext":
                if args.value is None:
                    parser.error("--value 是必需的 (搜索关键词)")
                dialogue.cmd_search_sctext(game_file, args.value, args.limit)
            elif args.action == "spawn-obj":
                if args.value is None or args.key is None:
                    parser.error("--value (房间名) 和 --key (对象名) 是必需的")
                room.cmd_spawn_obj(game_file, args.value, args.key, args.x, args.y)
            elif args.action == "npc-dialogue":
                if args.value is None or args.key is None:
                    parser.error("--value (房间名) 和 --key (对象名) 是必需的")
                if args.text_key is None or args.text is None:
                    parser.error("--text-key (textdata key) 和 --text (对话内容) 是必需的")
                npc.cmd_npc_dialogue(game_file, args.value, args.key, args.x, args.y,
                                 args.text_key, args.text,
                                 face=args.face, emotion=args.emotion, once=args.once,
                                 range_=args.range)
            elif args.action == "npc-choice":
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
            elif args.action == "guard-npc-alarm":
                if args.key is None or args.instance is None:
                    parser.error("--key (对象名) 和 --instance (实例 ID) 是必需的")
                npc.cmd_guard_npc_alarm(game_file, args.key, args.instance, text_key=args.text_key)
            elif args.action == "verify-nsid":
                npc.cmd_verify_nsid(game_file, fix=args.fix)
            elif args.action == "verify-instances":
                npc.cmd_verify_instances(game_file, fix=args.fix)
            elif args.action == "verify-code":
                if args.key is None:
                    parser.error("--key (代码条目名) 是必需的")
                _stable = verify.cmd_verify_code(game_file, args.key, show_asm=args.asm)
                if _stable is False:
                    sys.exit(1)  # 往返不稳定（WARN）必须非零退出
            elif args.action == "diff-snapshots":
                if args.key is None or args.value is None:
                    parser.error("--key (基线文件) 和 --value (对比文件) 是必需的")
                verify.cmd_diff_snapshots(Path(args.key).expanduser(), Path(args.value).expanduser())
            elif args.action == "smoke-test":
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
            elif args.action == "create-door":
                if args.value is None or args.key is None:
                    parser.error("--value (当前房间名) 和 --key (目标房间名) 是必需的")
                door.cmd_create_door(game_file, args.value, args.key,
                                args.x, args.y, args.spawn_x, args.spawn_y)
            elif args.action == "list-doors":
                if args.value is None:
                    parser.error("--value 是必需的 (房间名)")
                door.cmd_list_doors(game_file, args.value)
            elif args.action == "remove-door":
                if args.value is None:
                    parser.error("--value 是必需的 (房间名)")
                if not args.all and not (x_explicit and y_explicit):
                    parser.error("--x 和 --y (坐标) 或 --all (全部移除) 是必需的")
                door.cmd_remove_door(game_file, args.value,
                                args.x if x_explicit else None,
                                args.y if y_explicit else None,
                                remove_all=args.all)
            elif args.action == "create-pit":
                if args.value is None or args.key is None:
                    parser.error("--value (当前房间名) 和 --key (目标房间名) 是必需的")
                door.cmd_create_pit(game_file, args.value, args.key,
                               args.x, args.y, args.spawn_x, args.spawn_y)
            elif args.action == "create-battle":
                if args.value is None or args.key is None:
                    parser.error("--value (房间名) 和 --key (battlegroup ID) 是必需的")
                try:
                    bg_id = int(args.key)
                except ValueError:
                    parser.error("--key 必须是数字 (battlegroup ID)")
                door.cmd_create_battle(game_file, args.value, bg_id,
                                  border=args.border, x=args.x, y=args.y)
            elif args.action == "remove-obj":
                if args.value is None:
                    parser.error("--value 是必需的 (房间名)")
                if args.instance is None and args.key is None:
                    parser.error("--instance (实例 ID) 或 --key (对象名) 是必需的")
                room.cmd_remove_obj(game_file, args.value, args.key or "",
                               instance_id=args.instance, remove_all=args.all)
            elif args.action == "room-info":
                if args.value is None:
                    parser.error("--value 是必需的 (房间名)")
                room.cmd_room_info(game_file, args.value)
            elif args.action == "create-room":
                if args.value is None:
                    parser.error("--value 是必需的 (房间内部名)")
                room.cmd_create_room(game_file, args.value, args.width, args.height,
                                args.speed, args.caption, args.bg_color)
            elif args.action == "set-room-bg":
                if args.value is None:
                    parser.error("--value 是必需的 (房间名)")
                room.cmd_set_room_bg(game_file, args.value, args.index,
                                enable=utmt._bool_or_none(args.enable),
                                bg_name=args.bg,
                                foreground=utmt._bool_or_none(args.foreground),
                                x=(args.x if x_explicit else None),
                                y=(args.y if y_explicit else None),
                                speedx=args.speedx, speedy=args.speedy,
                                tiled_h=utmt._bool_or_none(args.tiled_h),
                                tiled_v=utmt._bool_or_none(args.tiled_v),
                                stretch=utmt._bool_or_none(args.stretch),
                                keep_bg_color=args.keep_bg_color)
            elif args.action == "set-room-solid-bg":
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
            elif args.action == "room-bg-info":
                if args.value is None:
                    parser.error("--value 是必需的 (房间名)")
                room.cmd_room_bg_info(game_file, args.value)
            elif args.action == "set-room-prop":
                if args.value is None:
                    parser.error("--value 是必需的 (房间名)")
                room.cmd_set_room_prop(game_file, args.value,
                                  width=args.width, height=args.height,
                                  speed=args.speed, caption=args.caption,
                                  bg_color=args.bg_color,
                                  persistent=args.persistent)
            elif args.action == "set-room-view":
                if args.value is None:
                    parser.error("--value 是必需的 (房间名)")
                room.cmd_set_room_view(game_file, args.value, args.index,
                                  enable=utmt._bool_or_none(args.enable),
                                  view_w=args.view_w, view_h=args.view_h,
                                  port_w=args.port_w, port_h=args.port_h,
                                  follow=args.follow,
                                  border_x=args.border_x, border_y=args.border_y)
            elif args.action == "list-game-bgs":
                room.cmd_list_game_bgs(game_file, args.value or "")
            elif args.action == "create-bg-asset":
                if args.value is None or args.image is None:
                    parser.error("--value (背景名) 和 --image (PNG 路径) 是必需的")
                room.cmd_create_bg_asset(game_file, args.value, args.image)
            elif args.action == "gml-bg":
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
            elif args.action == "remove-tile":
                if args.value is None:
                    parser.error("--value 是必需的 (房间名)")
                room.cmd_remove_tile(game_file, args.value, instance=args.instance)
            elif args.action == "handler-extract":
                code.cmd_handler_extract(game_file, apply=args.apply)
            elif args.action == "append-code":
                if args.key is None or args.value is None:
                    parser.error("--key (代码名) 和 --value (GML) 是必需的")
                code.cmd_code_append(game_file, args.key, args.value, value_is_file=args.file_path)
            elif args.action == "prepend-code":
                if args.key is None or args.value is None:
                    parser.error("--key (代码名) 和 --value (GML) 是必需的")
                code.cmd_code_prepend(game_file, args.key, args.value, value_is_file=args.file_path)
            elif args.action == "batch-add-textentry":
                if args.value is None:
                    parser.error("--value 是必需的 (JSON 文件路径)")
                dialogue.cmd_batch_textdata(game_file, args.value,
                                   face=args.face, emotion=args.emotion)
            elif args.action == "list-sprites":
                sprite.cmd_sprite_list(game_file, args.limit)
            elif args.action == "search-sprite":
                if args.value is None:
                    parser.error("--value 是必需的 (搜索关键词)")
                sprite.cmd_sprite_search(game_file, args.value, args.limit)
            elif args.action == "get-obj":
                if args.key is None:
                    parser.error("--key 是必需的 (对象名称)")
                sprite.cmd_obj_get(game_file, args.key)
            elif args.action == "set-obj-sprite":
                if args.key is None or args.value is None:
                    parser.error("--key (对象名) 和 --value (精灵名) 是必需的")
                sprite.cmd_obj_set_sprite(game_file, args.key, args.value)
            elif args.action == "list-textures":
                sprite.cmd_texture_list(game_file, args.limit)
            elif args.action == "export-sprite":
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
            elif args.action == "replace-sprite":
                if args.key is None or args.value is None:
                    parser.error("--key (精灵名) 和 --value (PNG 路径) 是必需的")
                sprite.cmd_sprite_replace(game_file, args.key, args.value, frame=args.frame if args.frame is not None else 0, all_frames=args.all)
            elif args.action == "duplicate-sprite":
                if args.key is None or args.value is None:
                    parser.error("--key (源精灵名) 和 --value (新精灵名) 是必需的")
                sprite.cmd_sprite_duplicate(game_file, args.key, args.value)
            elif args.action == "preview-sprite":
                if args.key is None:
                    parser.error("--key 是必需的 (精灵名)")
                sprite.cmd_sprite_preview(game_file, args.key)
            elif args.action == "colorize-sprite":
                if args.key is None or args.value is None or args.hue_from is None or args.hue_to is None:
                    parser.error("--key (源), --value (目标名), --hue-from (如 180-260), --hue-to (目标色相) 是必需的")
                try:
                    hf = tuple(float(x) / 360.0 for x in args.hue_from.split("-"))
                except Exception:
                    parser.error("--hue-from 格式错误，应为 \"180-260\"")
                sprite.cmd_sprite_colorize(game_file, args.key, args.value, hue_from=hf, hue_to=args.hue_to)
            elif args.action == "export-texture":
                if args.value is None:
                    parser.error("--value 是必需的 (输出目录)")
                sprite.cmd_texture_export(game_file, args.key, args.value)
            elif args.action == "replace-texture":
                if args.key is None or args.value is None:
                    parser.error("--key (纹理名) 和 --value (PNG 路径) 是必需的")
                sprite.cmd_texture_replace(game_file, args.key, args.value)
            elif args.action == "dump-sprites":
                if args.value is None:
                    parser.error("--value 是必需的 (输出目录)")
                sprite.cmd_sprite_dump_all(game_file, args.value)
            elif args.action == "cjk-font":
                if args.value is None:
                    parser.error("--value 是必需的 (font_cjk_build.py 输出目录)")
                if not cjk.cmd_cjk_font(game_file, Path(args.value).expanduser(),
                                    Path(args.work_dir).expanduser() if args.work_dir else None):
                    sys.exit(1)  # scr_setfont 字节级体检 WARN 必须非零退出
            elif args.action == "cjk-trigger":
                if args.text is None:
                    parser.error("--text 是必需的 (对话文本)")
                if not cjk.cmd_cjk_trigger(game_file, args.room, args.object,
                                       220 if args.x_raw is None else args.x_raw,
                                       330 if args.y_raw is None else args.y_raw,
                                       args.typer, args.text,
                                       wrap=not args.no_wrap,
                                       width_room_px=args.width):
                    sys.exit(1)  # Step_1 字节级体检 WARN 必须非零退出
            elif args.action == "cjk-check":
                if args.text is None and args.value is None:
                    parser.error("--text 传文本 或 --value 传文本文件路径，二选一")
                cjk.cmd_cjk_check(args.text,
                                  Path(args.glyphs) if args.glyphs else None,
                                  Path(args.value) if args.value else None)

            else:
                parser.error(f"'{args.action}' 不支持 data_win 文件")
        except (FileNotFoundError, ValueError, IndexError, RuntimeError, errors.DeterlineError) as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # ── Save editor actions (ini / file0) ────────────────
    try:
        save_dir = paths.find_save_dir(args.dir)
    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        if args.file == "file0":
            if args.action == "list":
                file0.cmd_file0_list(save_dir)
            elif args.action == "find":
                if args.value is None:
                    parser.error("--value 是必需的 (搜索目标值)")
                file0.cmd_file0_find(save_dir, args.value)
            elif args.action == "get":
                if not args.key:
                    parser.error("--key 是必需的")
                file0.cmd_file0_get(save_dir, args.key)
            elif args.action == "set":
                if not args.key or args.value is None:
                    parser.error("--key 和 --value 是必需的")
                file0.cmd_file0_set(save_dir, args.key, args.value)
            else:
                parser.error(f"'{args.action}' 仅支持 INI 文件")
        else:
            if args.action == "list":
                inifile.cmd_ini_list(save_dir)
            elif args.action == "room-list":
                room.cmd_room_list(args.value or "")
            elif args.action == "get":
                if not args.key:
                    parser.error("--key 是必需的")
                inifile.cmd_ini_get(save_dir, args.section, args.key)
            elif args.action == "set":
                if not args.key or args.value is None:
                    parser.error("--key 和 --value 是必需的")
                inifile.cmd_ini_set(save_dir, args.section, args.key, args.value)
            elif args.action == "find":
                print("find 仅支持 file0 (在 INI 中用 get 或 list)", file=sys.stderr)
                sys.exit(1)
            elif args.action == "undo":
                if not args.value:
                    parser.error("--value 是必需的 (ini, file0, 或 data_win)")
                save_cmds.cmd_undo(save_dir, args.value, backup_ts=args.backup,
                         dir_override=args.dir)
            elif args.action == "list-backups":
                if not args.value:
                    parser.error("--value 是必需的 (ini, file0, 或 data_win)")
                save_cmds.cmd_list_backups(save_dir, args.value, dir_override=args.dir)
            elif args.action == "create-system-info":
                if args.value is None:
                    parser.error("--value 是必需的 (962 或 963)")
                save_cmds.cmd_create_system_info(save_dir, args.value)
            elif args.action == "quest-init":
                flag_idx = args.flag if args.flag is not None else config.FLAG_CUSTOM_START
                dialogue.cmd_quest_init(save_dir, flag_idx)
            elif args.action == "quest-status":
                dialogue.cmd_quest_status(save_dir)
            elif args.action == "reset-all":
                save_cmds.cmd_reset_all(save_dir)
            elif args.action == "experiment-snapshot":
                save_cmds.cmd_experiment_snapshot(save_dir, args.value)
            elif args.action == "experiment-list":
                save_cmds.cmd_experiment_list(save_dir)
            elif args.action == "experiment-restore":
                if not args.value:
                    parser.error("--value 是必需的 (快照标签)")
                save_cmds.cmd_experiment_restore(save_dir, args.value)
            elif args.action == "reset-flags":
                save_cmds.cmd_reset_flags(save_dir)
            else:
                parser.error(
                    f"'{args.action}' 仅支持 --file data_win (游戏数据) 操作；"
                    f"ini/file0 模式不适用该命令"
                )
    except (FileNotFoundError, ValueError, errors.DeterlineError) as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
