@echo off
cd /d "%~dp0"

:: 检查是否已运行
if exist .pid (
    set /p pid=<.pid
    tasklist /fi "pid eq %pid%" 2>nul | find "%pid%" >nul
    if not errorlevel 1 (
        echo 服务已在运行 (PID: %pid%)
        exit /b 1
    )
)

:: 后台启动
start /b python -m src.main > log.log 2>&1

:: 获取 PID
for /f "tokens=2" %%a in ('tasklist /fi "imagename eq python.exe" /fo list ^| find "PID:"') do (
    echo %%a> .pid
    echo 服务已启动 (PID: %%a)
    goto :done
)

:done
echo 日志: type log.log
