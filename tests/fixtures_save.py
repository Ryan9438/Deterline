"""存档夹具（阶段 0.3）：只用标准库，生成 tmp 存档目录与 file0/INI 内容。

用法（测试内）：
    from fixtures_save import make_save_dir, SAMPLE_FILE0_NUMBERS
    save_dir = make_save_dir()          # tempfile 目录，含 file0 + undertale.ini
    ...

约定：
- 全部写入 tempfile.mkdtemp 目录（调用方负责清理或用 addCleanup）。
- file0 默认用"标准 CRLF"新格式生成（_parse_file0 两种行尾都能读）。
- 不 import modify_save/deterline——纯标准库，供任何层级的测试使用。
"""

import tempfile
from pathlib import Path

# 与真实 file0 布局对齐的最小合法内容：name 行 + 80 个 0 + 10 个 1
# （flag 域 [29..] 内 36/510/511 等由测试按需覆写）
SAMPLE_FILE0_NUMBERS = [0] * 80 + [1] * 10
SAMPLE_FILE0_NAME = "Frisk"

SAMPLE_INI_TEXT = "[General]\nLove=1\nKills=0\nRoom=4\nfun=42\nName=Frisk\n"


def serialize_file0(name: str = SAMPLE_FILE0_NAME,
                    numbers=None) -> bytes:
    """标准 CRLF 序列化（与 deterline.file0._serialize_file0 字节级一致）。"""
    numbers = list(numbers if numbers is not None else SAMPLE_FILE0_NUMBERS)
    return (name + "\r\n" + "".join(f"{n} \r\n" for n in numbers)).encode("utf-8")


def serialize_file0_legacy(name: str = SAMPLE_FILE0_NAME,
                           numbers=None) -> bytes:
    """旧格式（\\r\\r\\n 双 CR）——用于验证 _parse_file0 的行尾兼容。"""
    numbers = list(numbers if numbers is not None else SAMPLE_FILE0_NUMBERS)
    return (name + "\r\r\n" + "".join(f"{n} \r\r\n" for n in numbers)).encode("utf-8")


def make_save_dir(numbers=None, *, ini_text: str = SAMPLE_INI_TEXT,
                  with_name: str = SAMPLE_FILE0_NAME) -> Path:
    """创建含 file0 + undertale.ini 的临时存档目录。返回目录路径。"""
    d = Path(tempfile.mkdtemp(prefix="deterline_save_fixture_"))
    (d / "file0").write_bytes(serialize_file0(with_name, numbers))
    (d / "undertale.ini").write_text(ini_text, encoding="utf-8")
    return d


def read_file0_numbers(path: Path) -> list[int]:
    """无依赖解析 file0 数字行（测试内快速断言用）。"""
    lines = path.read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines[1:]:
        stripped = line.strip()
        if stripped:
            out.append(int(stripped))
    return out
