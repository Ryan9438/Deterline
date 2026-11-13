#!/usr/bin/env python3
"""Deterline 一键安装工具。

安装 Agent Skill + .NET SDK + UndertaleModTool CLI + 环境变量配置。

用法:
  python install.py            交互式安装（推荐）
  python install.py --skill    仅安装 Agent Skill
  python install.py --dotnet   仅安装 .NET SDK
  python install.py --utmt     仅安装 UndertaleModTool CLI
  python install.py --env      仅配置环境变量
  python install.py --all      自动安装全部（跳过确认）
  python install.py --auto     智能模式（体检 → 就绪仅装 Skill，否则自动装全部）
  python install.py --check    只读环境体检（不修改任何文件）
  python install.py --update   修复/更新（重指向 Skill 链接、重建 UTMT）
  python install.py --uninstall 卸载（删除 Skill 链接与环境变量）
  python install.py --help     查看完整帮助
"""

__version__ = "2.5.4"

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
OLD_SKILL_NAME = "undertale-save-editor"

AGENTS = [
    ("OpenCode",   Path.home() / ".config" / "opencode" / "skills"),
    ("Claude Code", Path.home() / ".claude" / "skills"),
    ("Cursor",     Path.home() / ".agents" / "skills"),
    ("Codex",      Path.home() / ".codex" / "skills"),
]

UTMT_DIR = Path.home() / "UndertaleModTool"
UTMT_DLL_NAME = "UndertaleModCli.dll"

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

# 全局自动确认开关（--yes / --all / --auto 时置 True）
_AUTO_YES = False

# Steam 游戏数据候选路径（用于 --check 只读体检）
GAME_DATA_CANDIDATES = {
    "darwin": [
        Path.home() / "Library/Application Support/Steam/steamapps/common/"
        "Undertale/UNDERTALE.app/Contents/Resources/game.ios",
        Path.home() / "Library/Application Support/Steam/steamapps/common/"
        "Undertale/UNDERTALE.app/Contents/Resources/data.win",
    ],
    "win32": [
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
        / "Steam/steamapps/common/Undertale/data.win",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        / "Steam/steamapps/common/Undertale/data.win",
    ],
}

SAVE_DIR_CANDIDATES = {
    "darwin": [Path.home() / "Library/Application Support/com.tobyfox.undertale"],
    "win32": [Path(os.environ.get("LOCALAPPDATA", "")) / "UNDERTALE"],
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
    if _AUTO_YES:
        return default
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
    old_name = OLD_SKILL_NAME
    for name, skill_dir in AGENTS:
        old_dst = skill_dir / old_name
        if old_dst.exists() or old_dst.is_symlink():
            try:
                _remove_path(old_dst)
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
        print(f"  {_yellow(f'⚠ 无法识别的 shell: {shell}')}")
        print(f"  请手动添加: export UTMT_CLI={dll}")
        return False

    export_line = f'\n# Deterline: UTMT CLI path\nexport UTMT_CLI="{dll}"\n'

    if rc_file.exists():
        existing = rc_file.read_text()
        if "UTMT_CLI" in existing:
            # 校验现有行的实际指向
            for line in existing.splitlines():
                if "UTMT_CLI" in line and str(dll) in line:
                    print(f"  {_green('✓ UTMT_CLI 已正确指向')} {dll}")
                    return True
            print(f"  {_yellow(f'⚠ {rc_file} 中已存在 UTMT_CLI，但指向不符')}")
            print(f"  当前指向: {_find_existing_utmt_path(existing) or '(无法解析)'}")
            if not _prompt_yes_no("  更新为正确路径？"):
                print("  - 跳过。如需更新请手动修改。")
                return False
            # 替换已有 UTMT_CLI 行为新路径
            lines = existing.splitlines(keepends=True)
            lines = [l for l in lines if "UTMT_CLI" not in l or "Deterline" in l]
            if not existing.rstrip().endswith("\n"):
                export_line = "\n" + export_line
            rc_file.write_text("".join(lines) + export_line)
            print(f"  {_green('✓ 已更新')} {rc_file}")
            print(f"  {_yellow('ℹ 请运行以下命令使环境变量生效:')}")
            print(f"     source {rc_file}")
            return True

    rc_file.parent.mkdir(parents=True, exist_ok=True)
    with open(str(rc_file), "a") as f:
        f.write(export_line)

    print(f"  {_green('✓ 已写入')} {rc_file}")
    print(f"  {_yellow('ℹ 请运行以下命令使环境变量生效:')}")
    print(f"     source {rc_file}")
    return True


def _find_existing_utmt_path(existing: str) -> str | None:
    """Extract the current UTMT_CLI path from rc file content."""
    for line in existing.splitlines():
        line = line.strip()
        if line.startswith("export UTMT_CLI="):
            val = line.split("=", 1)[1].strip().strip('"')
            if val:
                return val
    return None


# ============================================================
# Health check (--check) / Update (--update) / Uninstall (--uninstall)
# ============================================================

def _skill_installed() -> bool:
    """Return True if the skill is present in any agent directory."""
    for _, skill_dir in AGENTS:
        dst = skill_dir / SKILL_NAME
        if dst.exists() or dst.is_symlink():
            return True
    return False


def _find_game_data() -> Path | None:
    """Locate the UNDERTALE game data file (game.ios/data.win)."""
    candidates = GAME_DATA_CANDIDATES.get(sys.platform, [])
    for p in candidates:
        if p and p.exists():
            return p
    return None


def _find_save_dir() -> Path | None:
    """Locate the UNDERTALE save directory."""
    candidates = SAVE_DIR_CANDIDATES.get(sys.platform, [])
    for p in candidates:
        if p and p.exists() and p.is_dir():
            return p
    return None


def _env_ok(dll: Path | None) -> bool:
    """Check whether UTMT_CLI points at the found DLL."""
    if not dll:
        return False
    if os.environ.get("UTMT_CLI") == str(dll):
        return True
    # Also accept a valid entry in any rc file
    for _, rc in SHELL_RC_MAP.items():
        if rc.exists() and "UTMT_CLI" in rc.read_text(errors="ignore"):
            if _find_existing_utmt_path(rc.read_text(errors="ignore")) == str(dll):
                return True
    return False


def check_env(verbose: bool = True) -> bool:
    """Read-only environment health check. Returns True if all ready."""
    print(f"\n  {_bold('=' * 42)}")
    print(f"  {_bold(f'  {PROJECT} — 环境体检')}")
    print(f"  {_bold('=' * 42)}")

    skill_ok = _skill_installed()
    net = _find_net_version()
    net_ok = net is not None
    dll = _find_utmt_dll()
    utmt_ok = dll is not None
    env_ok = _env_ok(dll)
    game = _find_game_data()
    save = _find_save_dir()

    rows = [
        ("Agent Skill",   skill_ok, f"{'已安装' if skill_ok else '未安装'}"),
        (".NET SDK",      net_ok,   f"{net or '未安装'}"),
        ("UTMT CLI",      utmt_ok,  str(dll) if dll else "未编译"),
        ("UTMT_CLI 环境变量", env_ok, "✓" if env_ok else "未配置/指向不符"),
        ("游戏本体 (game.ios/data.win)", game is not None, str(game) if game else "未找到（跳过）"),
        ("存档目录",      save is not None, str(save) if save else "未找到（跳过）"),
    ]

    if verbose:
        for name, ok, detail in rows:
            mark = _green("✓") if ok else (_yellow("⚠") if name.startswith("游戏") else _red("✗"))
            print(f"  {mark} {name}")
            if detail:
                print(f"      {detail}")

    print()
    all_ok = skill_ok and net_ok and utmt_ok and env_ok
    if all_ok:
        print(f"  {_green('✓ 环境完整，可以直接使用。')}")
    else:
        print(f"  {_yellow('⚠ 环境不完整。运行 python install.py --all 自动补全，')}")
        print(f"    或仅需要存档编辑（LOVE/HP/Room）时可直接使用。")
    return all_ok


def _remove_path(dst: Path) -> None:
    """Remove a file, directory, or symlink (symlink must be unlinked, not rmtree'd)."""
    if dst.is_symlink() or dst.is_file():
        dst.unlink()
    elif dst.is_dir():
        shutil.rmtree(str(dst))
    else:
        dst.unlink()


def _remove_skill_links(src: Path) -> None:
    """Remove old skill name and current skill links from all agent dirs."""
    removed_any = False
    for name, skill_dir in AGENTS:
        for dst_name in (OLD_SKILL_NAME, SKILL_NAME):
            dst = skill_dir / dst_name
            if dst.exists() or dst.is_symlink():
                try:
                    _remove_path(dst)
                    print(f"  [{name}] 已删除: {dst_name}")
                    removed_any = True
                except OSError as e:
                    print(f"  [{name}] 删除失败: {e}")
    if not removed_any:
        print("  未发现已安装的 Skill 链接。")


def _remove_env_lines() -> None:
    """Remove Deterline/UTMT_CLI lines from shell rc files."""
    removed_any = False
    for shell, rc in SHELL_RC_MAP.items():
        if not rc.exists():
            continue
        lines = rc.read_text().splitlines(keepends=True)
        kept = [l for l in lines
                if "UTMT_CLI" not in l and "Deterline: UTMT CLI path" not in l]
        if len(kept) != len(lines):
            rc.write_text("".join(kept))
            print(f"  [{shell}] 已清除 {rc} 中的 UTMT_CLI 配置")
            removed_any = True
    if not removed_any:
        print("  未发现需清除的环境变量配置。")


def uninstall() -> bool:
    """Remove skill links, env lines, and (optionally) UTMT checkout."""
    print(f"\n  {_bold('=' * 42)}")
    print(f"  {_bold(f'  {PROJECT} — 卸载')}")
    print(f"  {_bold('=' * 42)}")

    print(f"\n  {_bold('[1/3] 删除 Agent Skill 链接')}")
    print("-" * 40)
    _remove_skill_links(Path(__file__).resolve().parent)

    print(f"\n  {_bold('[2/3] 清除环境变量配置')}")
    print("-" * 40)
    _remove_env_lines()

    print(f"\n  {_bold('[3/3] 可选：删除 UndertaleModTool')}")
    print("-" * 40)
    if UTMT_DIR.exists():
        if _prompt_yes_no(f"  删除 {UTMT_DIR}（约数百 MB）？", default=False):
            try:
                shutil.rmtree(str(UTMT_DIR))
                print(f"  {_green('✓ 已删除')} {UTMT_DIR}")
            except OSError as e:
                print(f"  {_red('✗ 删除失败')} {e}")
        else:
            print("  - 保留 ~/UndertaleModTool（可能被其他工具使用）")
    else:
        print("  - 未发现 ~/UndertaleModTool")

    print(f"\n  {_green('✓ 卸载完成。')}")
    print(f"  如需完整移除可手动删除项目目录本身。")
    return True


def _relink_skill(src: Path) -> None:
    """Re-point stale/broken skill symlinks to the current source."""
    for name, skill_dir in AGENTS:
        if not skill_dir.exists():
            continue
        dst = skill_dir / SKILL_NAME
        stale = False
        if dst.is_symlink():
            try:
                target = Path(os.readlink(str(dst))).resolve()
                stale = (not dst.exists()) or (str(target) != str(src.resolve()))
            except OSError:
                stale = True
        if stale:
            try:
                _remove_path(dst)
                if sys.platform == "win32":
                    shutil.copytree(str(src), str(dst), ignore_dangling_symlinks=True)
                else:
                    os.symlink(str(src), str(dst), target_is_directory=True)
                print(f"  [{name}] 已重新指向 → {src}")
            except OSError as e:
                print(f"  [{name}] 更新失败: {e}")
        elif dst.exists() or dst.is_symlink():
            print(f"  [{name}] 已是最新，跳过")
        else:
            print(f"  [{name}] 未安装，跳过")


def update() -> bool:
    """Re-point stale skill links and optionally rebuild UTMT CLI."""
    src = Path(__file__).resolve().parent
    print(f"\n  {_bold('=' * 42)}")
    print(f"  {_bold(f'  {PROJECT} — 更新 / 修复')}")
    print(f"  {_bold('=' * 42)}")

    print(f"\n  {_bold('[1/2] 重指向 Agent Skill 链接')}")
    print("-" * 40)
    _relink_skill(src)

    print(f"\n  {_bold('[2/2] 重建 UndertaleModTool CLI')}")
    print("-" * 40)
    if not _find_net_version():
        print("  - .NET SDK 未安装，跳过（可先运行: python install.py --dotnet）")
        return False
    if not UTMT_DIR.exists():
        print("  - 未发现 ~/UndertaleModTool 仓库，跳过（可先运行: python install.py --utmt）")
        return False
    if _prompt_yes_no("  从 GitHub 拉取最新代码并重新编译？"):
        _run(["git", "-C", str(UTMT_DIR), "pull"], timeout=300)
        cli_dir = UTMT_DIR / "UndertaleModCli"
        result = _run(["dotnet", "build", "-c", "Release", str(cli_dir)], timeout=600)
        if result.returncode == 0 and _find_utmt_dll():
            print(f"  {_green('✓ 编译成功')}")
            return True
        print(f"  {_red('✗ 编译失败')}，请手动检查: cd ~/UndertaleModTool && dotnet build -c Release UndertaleModCli")
        return False
    print("  - 跳过重建。")
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
    parser.add_argument("--auto", action="store_true", help="智能模式（体检 → 就绪仅装 Skill，否则自动装全部）")
    parser.add_argument("--check", action="store_true", help="只读环境体检，不修改任何文件")
    parser.add_argument("--update", action="store_true", help="更新/修复（重指向 Skill 链接、重建 UTMT）")
    parser.add_argument("--uninstall", action="store_true", help="卸载（删除 Skill 链接与环境变量）")
    parser.add_argument("--yes", action="store_true", help="自动确认所有提示（非交互）")
    args = parser.parse_args()

    global _AUTO_YES
    if args.yes or args.all or args.auto:
        _AUTO_YES = True

    src = Path(__file__).resolve().parent

    # ── 只读体检 / 卸载 / 更新 ──────────────────────
    if args.check:
        return 0 if check_env() else 1
    if args.uninstall:
        return 0 if uninstall() else 1
    if args.update:
        return 0 if update() else 1

    print(f"\n  {_bold('=' * 42)}")
    print(f"  {_bold(f'  {PROJECT} — 一键安装')}")
    print(f"  {_bold('=' * 42)}")
    print(f"  源目录: {src}")
    print(f"  平台: {sys.platform}")

    # ── 智能模式：体检 → 就绪仅装 Skill，否则自动装全部 ──
    if args.auto:
        print(f"\n  {_bold('→ 环境体检中...')}")
        ready = check_env()
        print()
        if ready:
            print(f"  {_green('✓ 环境完整，仅安装 Agent Skill...')}")
            step_agent_skill(src)
            _print_summary(src)
            return 0
        print(f"  {_yellow('→ 环境不完整，自动安装全部组件...')}")
        step_agent_skill(src)
        _install_deps(auto=True)
        _print_summary(src)
        return 0

    skill_ok = False
    specific_mode = args.skill or args.dotnet or args.utmt or args.env
    if specific_mode:
        # Run specific steps
        if args.skill:
            skill_ok = step_agent_skill(src)
        if args.dotnet:
            step_dotnet()
        if args.utmt:
            step_utmt()
        if args.env:
            step_env()
    else:
        # Full interactive install
        skill_ok = step_agent_skill(src)
        _install_deps(auto=args.all)

    _print_summary(src)
    return 0


def _install_deps(auto: bool) -> None:
    """Install dependency components (.NET / UTMT / env)."""
    print(f"\n  {'─' * 42}")
    print(f"  {_bold('依赖组件安装')}")
    print(f"  {'─' * 42}")
    print(f"  提示: 存档编辑（LOVE/HP/Room）不需要 .NET 和 UTMT。")
    print(f"        仅对话/脚本/房间编辑才需要以下组件。")
    print()

    if auto:
        # Auto-install with no prompts
        step_dotnet()
        step_utmt()
        step_env()
        return

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


def _print_summary(src: Path) -> None:
    """Print the final installation summary."""
    print(f"\n  {_bold('=' * 42)}")
    print(f"  {_bold('  安装完成')}")
    print(f"  {_bold('=' * 42)}")

    dll = _find_utmt_dll()
    print(f"  Agent Skill: {_green('✓') if _skill_installed() else _yellow('⚠')}")
    print(f"  .NET SDK:    {_green('✓') if _find_net_version() else _red('✗')}")
    print(f"  UTMT CLI:    {_green('✓') if dll else _red('✗')}")
    print(f"  UTMT_CLI:    {_green('✓') if _env_ok(dll) else _yellow('⚠')}")
    print()
    print(f"  {_bold('用法')}")
    print(f"    python run.py --action get --key Love")
    print(f"    python run.py --action spawn-obj --value room_asrielroom --key obj_dummy1 --file data_win")
    print()


if __name__ == "__main__":
    sys.exit(main())
