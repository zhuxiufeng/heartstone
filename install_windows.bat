@echo off
chcp 65001 >nul
echo ========================================================
echo   炉石传说竞技场全场景 AI 助手 - Windows 环境一键安装
echo ========================================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10 或更高版本，
    echo 并确保在安装时勾选了 "Add python.exe to PATH"！
    pause
    exit /b 1
)

echo [1/3] 正在创建 Python 虚拟环境 (.venv)...
if not exist ".venv" (
    python -m venv .venv
)

echo [2/3] 正在升级 pip 并安装 Windows 依赖 (包含 PyQt5, pywin32, OpenCV, Tesseract, mss 等)...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo [3/3] 安装完成！
echo.
echo 提示：
echo 1. 启动助手请直接双击运行 "start_windows.bat"
echo 2. 如需打包为单文件免安装 exe，可运行 "build_exe.bat"
echo ========================================================
pause
