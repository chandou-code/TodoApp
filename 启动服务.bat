@echo off
chcp 65001 >nul
title TodoApp 服务启动器

echo.
echo ========================================
echo     TodoApp 跨平台待办事项应用
echo ========================================
echo.

REM 检查 Python 版本
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

REM 检查虚拟环境
if not exist "venv" (
    echo 📦 创建虚拟环境...
    python -m venv venv
    echo ✅ 虚拟环境创建完成
) else (
    echo ✅ 虚拟环境已存在
)

REM 激活虚拟环境并安装依赖
if exist "venv\Scripts\activate.bat" (
    echo 📦 检查并安装依赖...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    echo ✅ 依赖安装完成
    deactivate
)

echo.
echo ========================================
echo     请选择启动方式
echo ========================================
echo.
echo 1. 仅启动后端服务 (Flask)
echo 2. 仅启动前端服务 (H5)
echo 3. 同时启动前后端服务
echo 4. 退出
echo.

set /p choice=请输入选择 (1-4): 

if "%choice%"=="1" goto backend
if "%choice%"=="2" goto frontend
if "%choice%"=="3" goto both
if "%choice%"=="4" goto end

echo ❌ 无效选择
pause
goto end

:backend
echo.
echo 🚀 启动后端服务...
echo 访问地址: http://localhost:5000
echo 按 Ctrl+C 停止服务
echo.
call venv\Scripts\activate.bat
python app.py
deactivate
goto end

:frontend
echo.
echo 🚀 启动前端服务...
cd App
echo 访问地址: http://localhost:8080
echo 按 Ctrl+C 停止服务
echo.
npm run dev:h5
cd ..
goto end

:both
echo.
echo 🔄 同时启动前后端服务...
echo 后端: http://localhost:5000
echo 前端: http://localhost:8080
echo 按 Ctrl+C 停止服务
echo.

REM 在新窗口启动后端
start "后端服务" /D cmd /c "call venv\Scripts\activate.bat && python app.py && deactivate"

REM 等待后端启动
timeout /t 3 /nobreak >nul

REM 启动前端
cd App
start "前端服务" /D cmd /c "npm run dev:h5"
cd ..

echo.
echo ✅ 服务启动完成！
echo 请查看新打开的窗口
echo.
pause

:end
echo.
echo 👋 感谢使用 TodoApp！
echo.