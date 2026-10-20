@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo 正在启动炉石传说竞技场全场景 AI 助手...

if exist ".venv\Scripts\python.exe" (
    call .venv\Scripts\activate.bat
    python main.py %*
) else (
    echo [提示] 未检测到 .venv 虚拟环境，使用系统 Python 启动...
    python main.py %*
)

if %ERRORLEVEL% neq 0 (
    echo.
    echo [错误] 启动异常，若尚未安装依赖，请先双击运行 "install_windows.bat"
    pause
)
