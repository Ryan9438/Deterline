@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Deterline — 一键安装

cd /d "%~dp0"

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

:: ── 2. 健康检查 ──────────────────────────
echo.
echo → 检查环境...

set dotnet_ok=0
set utmt_ok=0
set env_ok=0

dotnet --version >nul 2>&1 && set dotnet_ok=1
if !dotnet_ok!==1 ( echo   ✓ .NET SDK ) else ( echo   ✗ .NET SDK )

if exist "%USERPROFILE%\UndertaleModTool" (
    if exist "%USERPROFILE%\UndertaleModTool\UndertaleModCli\bin\Release\net10.0\UndertaleModCli.dll" (
        set utmt_ok=1
        echo   ✓ UndertaleModTool CLI
    ) else if exist "%USERPROFILE%\UndertaleModTool\UndertaleModCli\bin\Release\net9.0\UndertaleModCli.dll" (
        set utmt_ok=1
        echo   ✓ UndertaleModTool CLI
    ) else if exist "%USERPROFILE%\UndertaleModTool\UndertaleModCli\bin\Release\net8.0\UndertaleModCli.dll" (
        set utmt_ok=1
        echo   ✓ UndertaleModTool CLI
    ) else (
        echo   ✗ UndertaleModTool CLI — 需要编译
    )
) else (
    echo   ✗ UndertaleModTool CLI — 需要下载
)

if defined UTMT_CLI (
    set env_ok=1
    echo   ✓ UTMT_CLI 环境变量
) else (
    echo   ✗ UTMT_CLI 环境变量 — 需要配置
)

:: ── 3. 智能分叉 ──────────────────────────
echo.
if !dotnet_ok!==1 if !utmt_ok!==1 if !env_ok!==1 (
    echo ✓ 环境完整，仅安装 Agent Skill...
    echo.
    python install.py --skill
    echo.
    echo ✓ 完成！所有组件已就绪。
) else (
    echo → 需要安装依赖组件...
    echo.
    python install.py --all
)

echo.
pause
endlocal
