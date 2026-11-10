"""rooms.json 数据域（O2 步 2：从 modify_save.py 1:1 平移）。

ROOMS/_ROOMS_LOADED 是本模块私有全局（_load_rooms 会**重绑定** ROOMS——
外部一律经 rooms_data.ROOMS 模块属性读取，禁止 from-import 快照）。
rooms.json 路径：本文件位于 scripts/deterline/，包根解析 parents[1] = scripts/
（O2-step0 风险 #3：拆包后层级 +1，原 `parent / rooms.json` 已修正并登记于
tests/test_o2_step0.py::TestFileMigrationChecklist）。
"""

import json
import sys
from pathlib import Path

from . import errors

ROOMS: dict[str, str] = {}
_ROOMS_LOADED = False


def _rooms_json_path() -> Path:
    return Path(__file__).resolve().parents[1] / "rooms.json"


def _load_rooms() -> None:
    global ROOMS, _ROOMS_LOADED
    if _ROOMS_LOADED:
        return
    p = _rooms_json_path()
    try:
        with open(str(p), "r", encoding="utf-8") as f:
            loaded = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        loaded = {}
    if isinstance(loaded, dict):
        # rooms.json 的合法形态是 {数字房间ID: 中文名}。历史版本曾把内部名
        # 当 key 写入（污染出非数字键，导致 room-list 的 int() 排序崩溃）——
        # 这里过滤并报告，而不是让下游崩溃。
        bad = [k for k in loaded if not str(k).lstrip("-").isdigit()]
        if bad:
            print(f"警告: rooms.json 含 {len(bad)} 个非数字键，已忽略: {bad[:5]}"
                  f"{'...' if len(bad) > 5 else ''}", file=sys.stderr)
        ROOMS = {str(k): v for k, v in loaded.items() if str(k).lstrip("-").isdigit()}
    else:
        ROOMS = {}
    _ROOMS_LOADED = True


def _update_rooms_json(room_id: str, name: str) -> None:
    """Add or update a room entry in rooms.json (numeric room ID keys only)."""
    if not str(room_id).lstrip("-").isdigit():
        print(f"警告: 拒绝写入 rooms.json——房间 ID 必须是数字，收到 '{room_id}'", file=sys.stderr)
        return
    _load_rooms()
    p = _rooms_json_path()
    if room_id in ROOMS:
        return
    ROOMS[room_id] = name
    try:
        with open(str(p), "w", encoding="utf-8") as f:
            json.dump(ROOMS, f, ensure_ascii=False, indent=2)
        print(f"  rooms.json 已更新: [{room_id}] {name}")
    except OSError as e:
        print(f"  警告: rooms.json 写入失败 ({e})", file=sys.stderr)


def resolve_room(val: str) -> str:
    """Return numeric room ID string given a room number or Chinese name."""
    _load_rooms()
    # already a number
    if val.lstrip("-").isdigit():
        return val
    # exact Chinese name match
    for rid, name in ROOMS.items():
        if name == val:
            return rid
    # partial match — find all matches
    candidates = [(rid, name) for rid, name in ROOMS.items() if val in name]
    if len(candidates) == 1:
        return candidates[0][0]
    if len(candidates) > 1:
        lines = "\n".join(f"  [{rid}] {name}" for rid, name in candidates)
        print(f"匹配到多个房间:\n{lines}\n请使用更精确的名称或直接使用房间 ID。", file=sys.stderr)
        raise errors.NotFoundError(f"匹配到多个房间: {val}")
    print(f"错误: 未找到匹配 '{val}' 的房间", file=sys.stderr)
    raise errors.NotFoundError(f"未找到匹配的房间: {val}")


def format_room(rid: str) -> str:
    """Display room ID with its Chinese name."""
    _load_rooms()
    name = ROOMS.get(rid)
    return f"房间 {rid} — {name}" if name else f"房间 {rid}"
