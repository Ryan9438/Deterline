#!/bin/bash
# Deterline 一键安装入口 (Linux)
# 健康检查 → 有全套依赖则仅装 Skill，否则装全部
cd "$(dirname "$0")" || exit 1

echo "============================================"
echo "  Deterline — 一键安装"
echo "============================================"

# ── 1. 确保 Python 3 ──────────────────────────
PYTHON=""
for cmd in python3.12 python3.11 python3.10 python3; do
    if command -v "$cmd" &> /dev/null; then
        PYTHON="$cmd"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "→ Python 3 未安装，正在安装..."
    if command -v apt &> /dev/null; then
        sudo apt update && sudo apt install -y python3 || exit 1
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y python3 || exit 1
    elif command -v pacman &> /dev/null; then
        sudo pacman -Sy --noconfirm python || exit 1
    else
        echo "✗ 请手动安装 Python: https://www.python.org/downloads/"
        read -p "按回车退出..."
        exit 1
    fi
    PYTHON="python3"
    echo "✓ Python 安装完成"
else
    echo "✓ 检测到 $PYTHON"
fi

# ── 2. 健康检查 ─────────────────────────────
echo ""
echo "→ 检查环境..."

dotnet_ok=false
utmt_ok=false
env_ok=false

if command -v dotnet &> /dev/null; then
    dotnet_ok=true
    echo "  ✓ .NET SDK"
else
    echo "  ✗ .NET SDK — 需要安装"
fi

if [ -d "$HOME/UndertaleModTool" ]; then
    dll=$(find "$HOME/UndertaleModTool" -name "UndertaleModCli.dll" -path "*/Release/net*" 2>/dev/null | head -1)
    if [ -n "$dll" ]; then
        utmt_ok=true
        echo "  ✓ UndertaleModTool CLI"
        if [ "$UTMT_CLI" = "$dll" ]; then
            env_ok=true
            echo "  ✓ UTMT_CLI 环境变量"
        else
            echo "  ✗ UTMT_CLI 环境变量 — 需要配置"
        fi
    else
        echo "  ✗ UndertaleModTool CLI — 需要编译"
    fi
else
    echo "  ✗ UndertaleModTool CLI — 需要下载"
fi

# ── 3. 智能分叉 ─────────────────────────────
echo ""
if $dotnet_ok && $utmt_ok && $env_ok; then
    echo "✓ 环境完整，仅安装 Agent Skill..."
    echo ""
    $PYTHON install.py --skill
    echo ""
    echo "✓ 完成！所有组件已就绪。"
else
    echo "→ 需要安装依赖组件..."
    echo ""
    $PYTHON install.py --all
fi

echo ""
read -p "按回车退出..."
