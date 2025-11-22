@echo off
:: 由用户10717请求创建的开机自启路径显示工具
:: 完善日期：2025/11/12
:: 功能：显示所有可能的开机自启文件路径（含文件夹和注册表项）

setlocal enabledelayedexpansion

:: ==============================================
:: 1. 启动文件夹路径（通过文件夹启动的程序）
:: ==============================================
echo.
echo ==================== 启动文件夹路径 ====================
echo.

:: 1.1 当前用户专属启动文件夹（仅对当前用户生效）
set "userStartup=%USERPROFILE%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup"
echo [当前用户专属]
echo %userStartup%
echo.

:: 1.2 所有用户共用启动文件夹（对系统所有用户生效，需管理员权限）
set "allUsersStartup=%ProgramData%\Microsoft\Windows\Start Menu\Programs\Startup"
echo [所有用户共用]
echo %allUsersStartup%
echo.


:: ==============================================
:: 2. 注册表启动项路径（通过注册表加载的程序）
:: ==============================================
echo ==================== 注册表启动项路径 ====================
echo.

:: 2.1 当前用户专属注册表启动项（仅对当前用户生效）
echo [当前用户专属 - 注册表]
echo HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run
echo HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\RunOnce
echo HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\RunOnceEx
echo.

:: 2.2 所有用户共用注册表启动项（对系统所有用户生效，需管理员权限）
echo [所有用户共用 - 注册表]
echo HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\Run
echo HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\RunOnce
echo HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\RunOnceEx
echo.

:: 2.3 64位系统中32位程序的注册表启动项
if exist "%SystemRoot%\SysWOW64" (
    echo [64位系统专属 - 32位程序注册表]
    echo HKEY_LOCAL_MACHINE\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Run
    echo HKEY_LOCAL_MACHINE\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\RunOnce
    echo.
)


:: ==============================================
:: 3. 额外关键自启路径（任务计划、服务等）
:: ==============================================
echo ==================== 其他关键自启路径 ====================
echo.

:: 3.1 任务计划程序（通过任务计划触发的自启）
echo [任务计划程序]
echo 路径：控制面板\所有控制面板项\任务计划程序\任务计划程序库
echo 注册表对应：HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Schedule\TaskCache\Tasks
echo.

:: 3.2 系统服务（以服务形式自启的程序）
echo [系统服务]
echo 路径：services.msc（运行命令打开）
echo 注册表对应：HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services
echo.


:: ==============================================
:: 4. 打开常用启动文件夹（保留原功能）
:: ==============================================
echo ==================== 打开启动文件夹 ====================
echo.

:: 优先打开当前用户启动文件夹，若不存在则打开所有用户共用文件夹
if exist "%userStartup%" (
    echo 正在打开当前用户启动文件夹...
    explorer "%userStartup%"
) else if exist "%allUsersStartup%" (
    echo 正在打开所有用户共用启动文件夹...
    explorer "%allUsersStartup%"
) else (
    echo 未找到可用的启动文件夹！
)

echo.
echo 操作完成，所有开机自启路径已列出。
pause

endlocal