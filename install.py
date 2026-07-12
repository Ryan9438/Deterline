#!/usr/bin/env python3
"""一键将 undertale-save-editor 安装到本地 Agent (OpenCode / Claude Code / Cursor / Codex)。

用法:
  python install.py

也可双击运行 (macOS/Linux 需先 chmod +x install.py)。
"""

import os
import shutil
import sys
import subprocess
from pathlib import Path


# Agent 配置目录检测列表
AGENTS = [
    ("OpenCode",   Path.home() / ".config" / "opencode" / "skills"),
    ("Claude Code", Path.home() / ".claude" / "skills"),
    ("Cursor",     Path.home() / ".agents" / "skills"),
    ("Codex",      Path.home() / ".codex" / "skills"),
]


def _agent_in_path(name: str) -> bool:
    """Check if an agent CLI is on PATH."""
    cmds = {"OpenCode": "opencode", "Claude Code": "claude", "Codex": "codex"}
    cmd = cmds.get(name)
    return shutil.which(cmd) is not None if cmd else False


def _install_to(src: Path, dst: Path) -> str | None:
    """Install skill to dst. Returns error string or None on success."""
    if dst.exists() or dst.is_symlink():
        return f"已存在，跳过 (如需覆盖请先删除 {dst})"

    dst.parent.mkdir(parents=True, exist_ok=True)

    try:
        if sys.platform == "win32":
            shutil.copytree(str(src), str(dst), ignore_dangling_symlinks=True)
        else:
            os.symlink(str(src), str(dst), target_is_directory=True)
        return None
    except OSError as e:
        return str(e)


def main():
    src = Path(__file__).resolve().parent
    print(f"📁 源目录: {src}")
    print()

    found_any = False
    installed_any = False

    for name, skill_dir in AGENTS:
        if not skill_dir.exists() and not _agent_in_path(name):
            continue
        found_any = True
        dst = skill_dir / "undertale-save-editor"
        print(f"  [{name}] {dst}")
        err = _install_to(src, dst)
        if err is None:
            print(f"    ✓ 安装成功")
            installed_any = True
        else:
            print(f"    ⚠ {err}")

    if not found_any:
        print("未检测到已安装的 Agent（OpenCode / Claude Code / Cursor / Codex）。")
        print()
    elif not installed_any:
        print()
        print("所有目标均已存在，无需操作。")

    print()
    print("💡 你仍然可以直接在终端使用:")
    print(f"   python {src / 'run.py'} --action get --key Love")
    print()

    if sys.platform != "win32" and not installed_any:
        print("ℹ️  如需重新安装，先删除目标目录再运行本脚本。")

    return 0 if installed_any or not found_any else 1


if __name__ == "__main__":
    sys.exit(main())
