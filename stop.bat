@echo off
cd /d "%~dp0"

if not exist .pid (
    echo 服务未运行
    exit /b 0
)

set /p pid=<.pid

tasklist /fi "pid eq %pid%" 2>nul | find "%pid%" >nul
if errorlevel 1 (
    del .pid
    echo 服务未运行
    exit /b 0
)

taskkill /pid %pid% /f >nul 2>&1
del .pid
echo 服务已停止 (PID: %pid%)
