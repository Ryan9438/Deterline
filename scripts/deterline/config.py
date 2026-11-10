"""常量与数据表（O2 步 1：从 modify_save.py L31-60 1:1 平移）。

只放与任何域都不耦合的纯数据表；域内数据表（FILE0_FIELDS/ITEMS/DOOR_* 等）
随所属域在步 2-9 平移，不在此处。本模块无内部依赖。
跨模块引用一律 `config.X` 模块属性形式（运行时查找）。
"""

# ============================================================
# Constants
# ============================================================

FLAG_INDEX_MAX = 511
FLAG_CUSTOM_START = 510
FLAG_CUSTOM_END = 511

FACE_CHOICES: dict[int, str] = {
    0: "无头像",
    1: "Toriel", 2: "Flowey", 3: "Sans",
    4: "Papyrus", 5: "Undyne", 6: "Alphys",
    7: "Asgore", 8: "Mettaton", 9: "Asriel",
}

SANS_EMOTIONS: dict[int, str] = {
    0: "普通", 1: "轻笑", 2: "眨眼", 3: "慢眨眼", 4: "无眼",
}

DISTANCE_TRIGGER = 50
QUEST_STATE_INIT = 0

ROOM_BG_WARNING = (
    "提示: 背景渲染分三类，先诊断再改：",
    "  A 纯 Tile 房: 房间数据 8 层全 Enabled=false，渲染器跳过背景，改房间数据无效",
    "  B 房间数据驱动: 部分层 Enabled=true 且无 obj_backgrounder_*，房间数据即渲染来源",
    "  C 对象驱动: 有 obj_backgrounder_* 对象，运行时覆盖房间数据",
    "  诊断: `room-bg-info --value <房间> --file data_win`",
    "  遮挡: 高 slot 层画在低 slot 之上，只改低层会被盖住（用 gml-bg --hide-above）",
)
