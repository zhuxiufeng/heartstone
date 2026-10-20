@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo 正在清理旧版助手进程...
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM pythonw.exe /T 2>nul

echo 正在以更新后的配置启动最新程序...
if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\python.exe" main.py
) else (
    start "" python main.py
)
echo 启动完成！已应用最新热更新。
