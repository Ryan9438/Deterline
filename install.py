#!/usr/bin/env python3
"""Deterline 一键安装工具。

安装 Agent Skill + .NET SDK + UndertaleModTool CLI + 环境变量配置。

用法:
  python install.py          # 交互式安装（推荐）
  python install.py --skill  # 仅安装 Agent Skill
  python install.py --dotnet # 仅安装 .NET SDK
  python install.py --utmt   # 仅安装 UndertaleModTool CLI
  python install.py --env    # 仅配置环境变量
  python install.py --help   # 查看完整帮助
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


# ============================================================
# Constants
# ============================================================

PROJECT = "Deterline"
SKILL_NAME = "deterline"

AGENTS = [
    ("OpenCode",   Path.home() / ".config" / "opencode" / "skills"),
    ("Claude Code", Path.home() / ".claude" / "skills"),
    ("Cursor",     Path.home() / ".agents" / "skills"),
    ("Codex",      Path.home() / ".codex" / "skills"),
]

UTMT_DIR = Path.home() / "UndertaleModTool"
UTMT_DLL_NAME = "UndertaleModCli.dll"

ENV_FILE = Path.home() / ".deterline.env"
RC_FILES = {
    "zsh":  Path.home() / ".zshrc",
    "bash": Path.home() / ".bashrc",
    "fish": Path.home() / ".config" / "fish" / "config.fish",
}

SHELL_RC_MAP = {
    "zsh": RC_FILES["zsh"],
    "bash": RC_FILES["bash"],
    "fish": RC_FILES["fish"],
}


# ============================================================
# Utils
# ============================================================

def _green(text: str) -> str:
    return f"\033[92m{text}\033[0m" if sys.platform != "win32" else text


def _yellow(text: str) -> str:
    return f"\033[93m{text}\033[0m" if sys.platform != "win32" else text


def _red(text: str) -> str:
    return f"\033[91m{text}\033[0m" if sys.platform != "win32" else text


def _bold(text: str) -> str:
    return f"\033[1m{text}\033[0m" if sys.platform != "win32" else text


def _prompt_yes_no(question: str, default: bool = True) -> bool:
    """Ask a yes/no question. Returns True for yes, False for no."""
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        try:
            answer = input(_yellow(question) + suffix).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return False
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  请输入 y 或 n。")


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    quiet = kwargs.pop("quiet", False)
    if not quiet:
        print(f"  $ {' '.join(cmd)}")
    try:
        return subprocess.run(cmd, **kwargs)
    except FileNotFoundError:
        print(f"  {_red('错误:')} 未找到命令: {cmd[0]}")
        return subprocess.CompletedProcess(cmd, 1)


def _find_net_version() -> str | None:
    """Return the highest .NET SDK version found, or None."""
    try:
        result = subprocess.run(
            ["dotnet", "--list-sdks"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return None
        versions = [
            line.strip().split(" ")[0]
            for line in result.stdout.strip().splitlines()
            if line.strip()
        ]
        return versions[-1] if versions else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def _detect_shell() -> str:
    """Detect the current shell."""
    shell = os.environ.get("SHELL", "")
    if "zsh" in shell:
        return "zsh"
    if "bash" in shell:
        return "bash"
    if "fish" in shell:
        return "fish"
    # Default to bash on Windows/macOS
    return "bash"


# ============================================================
# Steps
# ============================================================

def step_agent_skill(src: Path) -> bool:
    """Install Agent Skill to all detected agent directories."""
    print(f"\n{_bold('[1/4] 安装 Agent Skill')}")
    print("-" * 40)

    # Clean up old skill name (pre-v2.0.0)
    old_name = "undertale-save-editor"
    for name, skill_dir in AGENTS:
        old_dst = skill_dir / old_name
        if old_dst.exists() or old_dst.is_symlink():
            try:
                if old_dst.is_symlink() or old_dst.is_dir():
                    shutil.rmtree(str(old_dst))
                else:
                    old_dst.unlink()
                print(f"  [{name}] 已删除旧链接: {old_name}")
            except OSError as e:
                print(f"  [{name}] 删除旧链接失败: {e}")

    found_any = False
    installed_any = False

    for name, skill_dir in AGENTS:
        if not skill_dir.exists():
            continue
        found_any = True
        dst = skill_dir / SKILL_NAME
        print(f"  [{name}] {dst}")
        if dst.exists() or dst.is_symlink():
            print(f"    {_yellow('⚠ 已存在，跳过')}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                shutil.copytree(str(src), str(dst), ignore_dangling_symlinks=True)
            else:
                os.symlink(str(src), str(dst), target_is_directory=True)
            print(f"    {_green('✓ 安装成功')}")
            installed_any = True
        except OSError as e:
            print(f"    {_red('✗')} {e}")

    if not found_any:
        print("  未检测到已安装的 Agent。")
    return installed_any


def step_dotnet() -> bool:
    """Check and optionally install .NET SDK."""
    print(f"\n{_bold('[2/4] .NET SDK')}")
    print("-" * 40)

    version = _find_net_version()
    if version:
        print(f"  {_green('✓ 已安装')} .NET SDK {version}")
        return True

    print(f"  {_yellow('⚠ 未安装 .NET SDK')}")
    print("  Deterline 需要 .NET SDK 来编译对话/脚本编辑工具 (UTMT CLI)。")
    if not _prompt_yes_no("  安装 .NET SDK？"):
        print("  - 跳过。安装 UTMT CLI 时需要手动安装: brew install dotnet")
        return False

    platform = sys.platform
    if platform == "darwin":
        print("  → 使用 Homebrew 安装...")
        result = _run(["brew", "install", "dotnet"], timeout=300)
        if result.returncode != 0:
            print(f"  {_red('✗ 安装失败')}")
            print("  手动安装: brew install dotnet")
            return False
    elif platform == "win32":
        print("  → 使用 winget 安装...")
        result = _run(["winget", "install", "Microsoft.DotNet.SDK.10"], timeout=300)
        if result.returncode != 0:
            print(f"  {_red('✗ 安装失败')}")
            print("  手动安装: https://dotnet.microsoft.com/download")
            return False
    else:
        print(f"  {_yellow('⚠ Linux 需要手动安装')}")
        print("  参考: https://learn.microsoft.com/dotnet/core/install/linux")
        return False

    version = _find_net_version()
    if version:
        print(f"  {_green('✓ 安装成功')} .NET SDK {version}")
        return True
    print(f"  {_red('✗ 安装可能未完成')}，请手动运行: brew install dotnet")
    return False


def step_utmt() -> bool:
    """Clone and build UndertaleModTool CLI."""
    print(f"\n{_bold('[3/4] UndertaleModTool CLI')}")
    print("-" * 40)

    # Check if already compiled
    dll = _find_utmt_dll()
    if dll:
        print(f"  {_green('✓ 已就绪')} {dll}")
        return True

    utmt_dir = UTMT_DIR
    net_dir = utmt_dir / "UndertaleModCli" / "bin" / "Release"

    if utmt_dir.exists():
        print(f"  {_green('✓ 仓库已存在')} {utmt_dir}")
    else:
        print(f"  → 需要从 GitHub 克隆 (约 200MB)...")
        if not _prompt_yes_no("  克隆 UndertaleModTool？"):
            print("  - 跳过。安装完成后无法使用对话/脚本/房间编辑功能。")
            return False
        print("  克隆中，请稍候...")
        result = _run(
            ["git", "clone", "https://github.com/UnderminersTeam/UndertaleModTool.git", str(utmt_dir)],
            timeout=600
        )
        if result.returncode != 0:
            print(f"  {_red('✗ 克隆失败')}")
            print("  手动克隆: git clone https://github.com/UnderminersTeam/UndertaleModTool.git")
            return False
        print(f"  {_green('✓ 克隆完成')}")

    # Find the highest .NET version folder to build against
    sdk_version = _find_net_version()
    if not sdk_version:
        print(f"  {_red('✗ .NET SDK 未安装')}，请先安装")
        return False
    target_framework = f"net{sdk_version.split('.')[0]}.0"
    print(f"  → 使用 .NET {target_framework} 编译")

    if not _prompt_yes_no("  编译 UndertaleModTool CLI（约 1-3 分钟）？"):
        print("  - 跳过。需要时手动编译: dotnet build UndertaleModCli")
        return False

    print("  编译中，请耐心等待...")
    cli_dir = utmt_dir / "UndertaleModCli"
    result = _run(
        ["dotnet", "build", "-c", "Release", str(cli_dir)],
        timeout=600
    )
    if result.returncode != 0:
        print(f"  {_red('✗ 编译失败')}")
        print("  手动编译: cd ~/UndertaleModTool && dotnet build -c Release UndertaleModCli")
        return False

    # Find the compiled dll
    dll = _find_utmt_dll()
    if dll:
        print(f"  {_green('✓ 编译成功')} {dll}")
        return True

    print(f"  {_yellow('⚠ 编译完成，但 DLL 未在预期位置找到')}")
    return False


def _find_utmt_dll() -> Path | None:
    """Find the compiled UTMT CLI dll."""
    base = UTMT_DIR / "UndertaleModCli" / "bin" / "Release"
    if not base.exists():
        return None
    # Search net*.* directories
    for d in sorted(base.iterdir(), reverse=True):
        if d.is_dir() and d.name.startswith("net"):
            dll = d / UTMT_DLL_NAME
            if dll.exists():
                return dll
    return None


def step_env() -> bool:
    """Configure UTMT_CLI environment variable."""
    print(f"\n{_bold('[4/4] 环境变量')}")
    print("-" * 40)

    dll = _find_utmt_dll()
    if not dll:
        print(f"  {_yellow('⚠ UTMT CLI 未编译，跳过环境变量配置')}")
        print("  - 安装完成后手动运行: python install.py --env")
        return False

    # Check if UTMT_CLI is already set correctly
    current = os.environ.get("UTMT_CLI", "")
    if current == str(dll):
        print(f"  {_green('✓ UTMT_CLI 已指向')} {dll}")
        return True

    # Detect shell and write to rc file
    shell = _detect_shell()
    rc_file = SHELL_RC_MAP.get(shell)
    if not rc_file:
        print(f"  {_yellow('⚠ 无法识别的 shell: {shell}')}")
        print(f"  请手动添加: export UTMT_CLI={dll}")
        return False

    export_line = f'\n# Deterline: UTMT CLI path\nexport UTMT_CLI="{dll}"\n'

    if rc_file.exists():
        existing = rc_file.read_text()
        if "UTMT_CLI" in existing:
            print(f"  {_yellow('⚠ UTMT_CLI 已在 {rc_file} 中存在')}")
            print(f"  跳过，如需更新请手动修改。")
            return True

    rc_file.parent.mkdir(parents=True, exist_ok=True)
    with open(str(rc_file), "a") as f:
        f.write(export_line)

    print(f"  {_green('✓ 已写入')} {rc_file}")
    print(f"  {_yellow('ℹ 请运行以下命令使环境变量生效:')}")
    print(f"     source {rc_file}")
    return True


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description=f"{PROJECT} 一键安装工具",
        epilog="""
示例:
  python install.py            完整安装（交互式）
  python install.py --skill    仅安装 Agent Skill
  python install.py --dotnet   仅安装 .NET SDK
  python install.py --utmt     仅安装 UndertaleModTool CLI
  python install.py --env      仅配置环境变量
  python install.py --all      跳过确认，自动安装全部
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--skill", action="store_true", help="仅安装 Agent Skill")
    parser.add_argument("--dotnet", action="store_true", help="仅安装 .NET SDK")
    parser.add_argument("--utmt", action="store_true", help="仅安装 UTMT CLI")
    parser.add_argument("--env", action="store_true", help="仅配置环境变量")
    parser.add_argument("--all", action="store_true", help="自动安装全部（跳过确认）")
    args = parser.parse_args()

    src = Path(__file__).resolve().parent
    specific_mode = args.skill or args.dotnet or args.utmt or args.env

    print(f"\n  {_bold('=' * 42)}")
    print(f"  {_bold(f'  {PROJECT} — 一键安装')}")
    print(f"  {_bold('=' * 42)}")
    print(f"  源目录: {src}")
    print(f"  平台: {sys.platform}")

    if specific_mode:
        # Run specific steps
        if args.skill:
            step_agent_skill(src)
        if args.dotnet:
            step_dotnet()
        if args.utmt:
            step_utmt()
        if args.env:
            step_env()
    else:
        # Full interactive install
        step_agent_skill(src)

        print(f"\n  {'─' * 42}")
        print(f"  {_bold('依赖组件安装')}")
        print(f"  {'─' * 42}")
        print(f"  提示: 存档编辑（LOVE/HP/Room）不需要 .NET 和 UTMT。")
        print(f"        仅对话/脚本/房间编辑才需要以下组件。")
        print()

        if args.all:
            # Auto-install with no prompts
            if not step_dotnet():
                pass
            if not step_utmt():
                pass
            step_env()
        else:
            if _prompt_yes_no("  安装 .NET SDK（对话/脚本编辑需要）?", default=True):
                step_dotnet()
            else:
                print("  - 跳过 .NET 安装")

            if _prompt_yes_no("  安装 UndertaleModTool CLI（需要 .NET）?", default=True):
                step_utmt()
            else:
                print("  - 跳过 UTMT 安装")

            dll = _find_utmt_dll()
            if dll and _prompt_yes_no("  配置环境变量?", default=True):
                step_env()
            elif dll:
                print("  - 跳过环境变量配置")
            else:
                print("  - 环境变量: UTMT CLI 未编译，稍后运行 python install.py --env")

    # Summary
    print(f"\n  {_bold('=' * 42)}")
    print(f"  {_bold('  安装完成')}")
    print(f"  {_bold('=' * 42)}")

    dll = _find_utmt_dll()
    print(f"  Agent Skill: {_green('✓') if step_agent_skill(src) else _yellow('⚠')}")
    print(f"  .NET SDK:    {_green('✓') if _find_net_version() else _red('✗')}")
    print(f"  UTMT CLI:    {_green('✓') if dll else _red('✗')}")
    print(f"  UTMT_CLI:    {_green('✓') if os.environ.get('UTMT_CLI') == str(dll) else _yellow('⚠')}")
    print()
    print(f"  {_bold('用法')}")
    print(f"    python run.py --action get --key Love")
    print(f"    python run.py --action spawn-obj --value room_asrielroom --key obj_dummy1 --file data_win")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
