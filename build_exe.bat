@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================================
echo   炉石传说竞技场 AI 助手 - Windows 单文件 EXE 打包脚本
echo ========================================================
echo.

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

echo [1/2] 安装 PyInstaller 打包工具...
pip install pyinstaller

echo [2/2] 开始构建可执行文件 (炉石竞技场AI助手.exe)...
pyinstaller --noconfirm --onedir --windowed ^
    --name "炉石竞技场AI助手" ^
    --add-data "data;data" ^
    --hidden-import "win32gui" ^
    --hidden-import "win32con" ^
    --hidden-import "PyQt5.QtCore" ^
    --hidden-import "PyQt5.QtWidgets" ^
    --hidden-import "google.generativeai" ^
    main.py

echo.
echo ========================================================
echo 打包完成！生成文件位于 dist\炉石竞技场AI助手\
echo 您可以将该文件夹直接复制到任何 Windows 电脑运行！
echo ========================================================
pause
