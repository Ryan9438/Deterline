"""undertale.ini 读写域（O2 步 2：从 modify_save.py 1:1 平移）。

跨模块一律模块属性形式：errors./paths./rooms_data./file0.（运行时查找，
保 mock/旗标写入可见——研讨会2/01 风险 #1 铁律）。
"""

import configparser
import sys
from pathlib import Path

from . import errors, file0, paths, rooms_data

# ============================================================
# INI Value Helpers
# ============================================================

def format_ini_value(value: str) -> str:
    try:
        num = float(value)
        return f'"{num:.6f}"'
    except ValueError:
        return f'"{value}"'


def parse_ini_value(raw: str) -> str:
    s = raw.strip()
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    try:
        f = float(s)
        return str(int(f)) if f == int(f) else s
    except ValueError:
        return s


# ============================================================
# INI Operations
# ============================================================

KNOWN_KEYS = {
    "Love": "LOVE / 等级 (1-20)",
    "Kills": "击杀数 (屠杀线判定)",
    "Room": "当前房间 ID (支持中文名称)",
    "fun": "趣味值 (影响 Gaster 等隐藏事件)",
    "Name": "玩家名称",
    "Time": "游戏时间 (秒)",
    "Gameover": "死亡次数",
}


def normalize_key(key: str) -> str:
    upper = key.upper()
    for known in KNOWN_KEYS:
        if known.upper() == upper:
            return known
    return key


class _CasePreservingConfigParser(configparser.ConfigParser):
    """Preserve key case for Undertale's case-sensitive INI parser."""
    def optionxform(self, optionstr: str) -> str:
        return optionstr

    def get(self, section: str, option: str, **kwargs) -> str:
        return super().get(section, self._find_key(section, option), **kwargs)

    def set(self, section: str, option: str, value: str | None = None) -> None:
        super().set(section, self._find_key(section, option), value)

    def has_option(self, section: str, option: str) -> bool:
        return super().has_option(section, self._find_key(section, option))

    def _find_key(self, section: str, option: str) -> str:
        if super().has_option(section, option):
            return option
        for opt in self.options(section):
            if opt.lower() == option.lower():
                return opt
        return option


def _read_ini(path: Path) -> _CasePreservingConfigParser:
    if not path.exists():
        raise FileNotFoundError(f"存档文件不存在: {path}")
    try:
        cp = _CasePreservingConfigParser()
        cp.read(str(path), encoding="utf-8")
        return cp
    except configparser.DuplicateOptionError:
        cp = _CasePreservingConfigParser(strict=False)
        cp.read(str(path), encoding="utf-8")
        print("检测到 INI 重复键 (游戏多周目残留)，自动清理...")
        _write_ini(path, cp)
        print("  ✓ 已清理")
        cp = _CasePreservingConfigParser()
        cp.read(str(path), encoding="utf-8")
        return cp


def _write_ini(path: Path, cp: configparser.ConfigParser) -> None:
    paths.backup_file(path)
    with open(str(path), "w", encoding="utf-8") as f:
        cp.write(f, space_around_delimiters=False)


def cmd_ini_list(save_dir: Path) -> None:
    path = save_dir / "undertale.ini"
    cp = _read_ini(path)
    for section in cp.sections():
        print(f"\n[{section}]")
        for key, value in cp.items(section):
            display = parse_ini_value(value)
            desc = KNOWN_KEYS.get(key, "")
            line = f"  {key} = {display}"
            if desc:
                line += f"  ({desc})"
            if key == "Room":
                rooms_data._load_rooms()
                name = rooms_data.ROOMS.get(str(display))
                if name:
                    line += f"\n    → {name}"
            print(line)


def cmd_ini_get(save_dir: Path, section: str, key: str) -> None:
    path = save_dir / "undertale.ini"
    cp = _read_ini(path)
    key = normalize_key(key)
    try:
        raw = cp.get(section, key)
    except (configparser.NoSectionError, configparser.NoOptionError):
        raise errors.NotFoundError(f"[{section}] 中未找到 '{key}'")
    display = parse_ini_value(raw)
    desc = KNOWN_KEYS.get(key, "")
    line = f"{key} = {display}"
    if desc:
        line += f"  ({desc})"
    if key == "Room":
        rooms_data._load_rooms()
        name = rooms_data.ROOMS.get(str(display))
        if name:
            line += f"\n  → {name}"
    print(line)


# ini [General] 中"镜像"键 → file0 权威字段（对照 scr_save / scr_load 确认：
# 游戏运行时 LOVE/Kills/Room 从 file0 读取，ini 只是存档时写入的副本）
INI_TO_FILE0_SYNC = {
    "Love": "LOVE",
    "Kills": "KILLS",
    "Room": "LOCATION",
}

# 只存在于 file0 的键（ini 模式写它们不生效）——用于 cmd_ini_set 的 footgun 警告
FILE0_ONLY_KEYS = {
    "HP", "MAXHP", "MAXEN", "AT", "DF", "WEAPON", "ARMOR", "EXP", "GOLD",
    "SP", "FACE", "RUINS_KILLS", "SNOWKILLS", "WATERKILLS", "FIREKILLS",
    "DEFEATED_ASRIEL", "PLOT",
}


def cmd_ini_set(save_dir: Path, section: str, key: str, value: str) -> None:
    path = save_dir / "undertale.ini"
    cp = _read_ini(path)
    key = normalize_key(key)

    # ⚠️ footgun 防护（2026-11 审计）：HP/EXP/GOLD/装备/Boss 等核心属性只存在于
    # file0，写进 ini 不会同步也不会生效——提醒用户改用 --file file0。
    if key.upper() in FILE0_ONLY_KEYS and not (
            section.lower() == "general" and key in INI_TO_FILE0_SYNC):
        print(f"警告: '{key}' 是 file0 专属属性（游戏运行时读 file0，scr_load 已核实），"
              f"写入 ini 不会生效也不会同步。请改用: set --key {key} --value {value} --file file0",
              file=sys.stderr)

    if not cp.has_section(section):
        cp.add_section(section)

    # Room 支持中文名称
    actual = rooms_data.resolve_room(value) if key == "Room" else value

    formatted = format_ini_value(actual)
    old_raw = cp.get(section, key, fallback=None)
    old_display = parse_ini_value(old_raw) if old_raw else "(不存在)"

    cp.set(section, key, formatted)
    _write_ini(path, cp)

    new_display = parse_ini_value(formatted)
    msg = f"✓ [{section}] {key}: {old_display} → {new_display}"

    # ini [General] 的 Love/Kills/Room 只是镜像副本，游戏运行时读 file0（scr_load）。
    # 修改这些键必须同步 file0 才生效。
    if section.lower() == "general" and key in INI_TO_FILE0_SYNC:
        file0_key = INI_TO_FILE0_SYNC[key]
        if key == "Room":
            rooms_data._load_rooms()
            name = rooms_data.ROOMS.get(new_display)
            if name:
                msg += f"  ({name})"
        file0.cmd_file0_set(save_dir, file0_key, str(actual))
        msg += "  (游戏读 file0，已同步)"

    print(msg)
