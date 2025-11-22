#!/usr/bin/env python3
"""
TodoApp 启动脚本
一键启动前后端服务
"""

import os
import sys
import subprocess
import threading
import time
from pathlib import Path

def check_python():
    """检查 Python 版本"""
    if sys.version_info < (3, 8):
        print("❌ 需要 Python 3.8 或更高版本")
        print(f"当前版本: {sys.version}")
        sys.exit(1)
    print(f"✅ Python 版本检查通过: {sys.version}")

def check_venv():
    """检查虚拟环境"""
    venv_path = Path("venv")
    if not venv_path.exists():
        print("📦 创建虚拟环境...")
        subprocess.run([sys.executable, "-m", "venv", "venv"])
        print("✅ 虚拟环境创建完成")
    else:
        print("✅ 虚拟环境已存在")

def install_requirements():
    """安装依赖"""
    print("📦 检查并安装依赖...")
    
    # 激活虚拟环境并安装依赖
    if os.name == 'nt':  # Windows
        pip_path = Path("venv/Scripts/pip")
        python_path = Path("venv/Scripts/python")
    else:  # macOS/Linux
        pip_path = Path("venv/bin/pip")
        python_path = Path("venv/bin/python")
    
    if pip_path.exists():
        subprocess.run([str(pip_path), "install", "-r", "requirements.txt"])
        print("✅ 依赖安装完成")

def start_backend():
    """启动后端服务"""
    print("🚀 启动后端服务...")
    
    if os.name == 'nt':  # Windows
        python_exe = "venv/Scripts/python"
    else:  # macOS/Linux
        python_exe = "venv/bin/python"
    
    try:
        subprocess.run([python_exe, "app.py"])
    except KeyboardInterrupt:
        print("\n⏹ 后端服务已停止")

def start_frontend():
    """启动前端服务"""
    app_dir = Path("App")
    if not app_dir.exists():
        print("❌ App 目录不存在，跳过前端启动")
        return
    
    print("🚀 启动前端服务...")
    
    # 检查是否安装了 Node.js
    try:
        subprocess.run(["npm", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ 未找到 Node.js，请先安装 Node.js")
        return
    
    # 进入 App 目录并启动
    os.chdir("App")
    try:
        subprocess.run(["npm", "run", "dev:h5"])
    except KeyboardInterrupt:
        print("\n⏹ 前端服务已停止")
    finally:
        os.chdir("..")

def start_all():
    """同时启动前后端"""
    print("🌟 启动 TodoApp 完整服务")
    print("=" * 50)
    
    # 环境检查
    check_python()
    check_venv()
    install_requirements()
    
    print("=" * 50)
    print("选择启动方式:")
    print("1. 仅启动后端")
    print("2. 仅启动前端")
    print("3. 同时启动前后端")
    
    try:
        choice = input("请输入选择 (1-3): ").strip()
    except KeyboardInterrupt:
        print("\n👋 启动取消")
        return
    
    if choice == "1":
        start_backend()
    elif choice == "2":
        start_frontend()
    elif choice == "3":
        print("🔄 同时启动前后端服务...")
        
        # 在新线程中启动后端
        backend_thread = threading.Thread(target=start_backend)
        backend_thread.daemon = True
        backend_thread.start()
        
        # 等待一下后端启动
        time.sleep(3)
        
        # 启动前端
        start_frontend()
    else:
        print("❌ 无效选择")

if __name__ == "__main__":
    start_all()