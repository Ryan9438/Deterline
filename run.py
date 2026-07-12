#!/usr/bin/env python3
"""UNDERTALE Save Editor — 快捷入口。

用法:
  python run.py --action get --key Love
  python run.py --action set --key HP --value 50 --file file0
  python run.py --install      ← 一键安装到本地 Agent
"""

import sys
import subprocess
from pathlib import Path


def main():
    args = sys.argv[1:]

    # --install 单独处理
    if "--install" in args:
        install = Path(__file__).resolve().parent / "install.py"
        if not install.exists():
            print("错误: 找不到 install.py", file=sys.stderr)
            sys.exit(1)
        cmd = [sys.executable, str(install)]
        proc = subprocess.run(cmd)
        sys.exit(proc.returncode)

    # 其余参数转发到 modify_save.py
    script = Path(__file__).resolve().parent / "scripts" / "modify_save.py"
    if not script.exists():
        print(f"错误: 找不到核心脚本: {script}", file=sys.stderr)
        sys.exit(1)

    cmd = [sys.executable, str(script)] + args
    try:
        proc = subprocess.run(cmd)
        sys.exit(proc.returncode)
    except FileNotFoundError:
        print("错误: 未找到 Python 解释器。请确保已安装 Python 3.10+。", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
