@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Deterline — 一键安装

cd /d "%~dp0"

if not exist "install.py" (
    echo ✗ 错误: 未找到 install.py，请从项目根目录运行此脚本。
    pause
    exit /b 1
)

echo ============================================
echo   Deterline — 一键安装
echo ============================================
echo.

:: ── 1. 确保 Python ──────────────────────────
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo → Python 3 未安装
    echo.
    echo   1) 打开 Python 官网下载（推荐）
    echo   2) 跳过，我稍后手动安装
    echo.
    set /p choice=请选择 (1/2):
    if "!choice!"=="1" (
        start https://www.python.org/downloads/
        echo.
        echo   请下载并安装 Python 3.10+ 版本
        echo   安装时务必勾选 "Add Python to PATH"
        echo.
    )
    echo.
    echo   安装 Python 后请重新运行 install.bat
    pause
    exit /b 1
)
echo ✓ 检测到 Python

:: ── 2. 委托 install.py（体检 → 智能分叉）────
echo.
python install.py --auto

echo.
pause
endlocal
