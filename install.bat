@echo off
chcp 65001 >nul
echo ============================================
echo  undertale-save-editor — 一键安装
echo ============================================
echo.

cd /d "%~dp0"
python install.py

echo.
echo 按任意键退出...
pause >nul