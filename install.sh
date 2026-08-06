#!/bin/bash
# Deterline 一键安装入口 (Linux)
# 全部逻辑委托给 install.py（环境体检 → 智能分叉）
cd "$(dirname "$0")" || exit 1

if [ ! -f "install.py" ]; then
    echo "✗ 错误: 未找到 install.py，请从项目根目录运行此脚本。"
    read -p "按回车退出..."
    exit 1
fi

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

# ── 2. 委托 install.py（体检 → 智能分叉）────────
echo ""
$PYTHON install.py --auto

echo ""
read -p "按回车退出..."
