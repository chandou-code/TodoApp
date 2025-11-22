@echo off
chcp 65001 > nul
set "PYTHON_PROJECT=C:\Users\10717\PycharmProjects\todoApp"

REM 隐藏窗口
if "%1"=="hide" (
    powershell -WindowStyle Hidden -Command "& { Start-Process -FilePath '%0' -ArgumentList 'run' -WindowStyle Hidden }"
    exit
)

REM 检查虚拟环境
if not exist "C:\Users\10717\PycharmProjects\todoApp\.venv\Scripts\activate.bat" (
    echo 错误：虚拟环境不存在于以下路径：
    echo %PYTHON_PROJECT%\.venv
    pause
    exit /b 1
)

REM 激活虚拟环境 - 使用完整路径
echo 正在激活虚拟环境...
call "C:\Users\10717\PycharmProjects\todoApp\.venv\Scripts\activate.bat"
if errorlevel 1 (
    echo 激活虚拟环境失败！
    pause
    exit /b 1
)

REM 运行脚本
echo 正在运行脚本...
cd /d "%PYTHON_PROJECT%"
python app.py

REM 保持窗口
echo 执行完成
pause
