# TodoApp - 跨平台待办事项同步应用

一个基于原生WebSocket的无需云服务器的个人待办事项管理应用，支持手机和PC自动同步，让你的灵感永不丢失！

## ✨ 特色功能

![TodoApp Logo](https://via.placeholder.com/600x200/4CAF50/ffffff?text=TodoApp-原生WebSocket跨平台同步)

> 💡 **核心理念**：手机随时记录，电脑自动同步，再也不怕忘事儿和三分钟热度！

### 📱 原生WebSocket同步
- **手机端**：随时使用 `TodoApp.apk` 记录想法和待办事项
- **PC端**：原生WebSocket服务器自动接收和存储数据
- **自动同步**：回家后手机自动连接WiFi同步数据到电脑
- **完全兼容**：不受Android 9+网络安全策略限制，无需HTTPS证书

### 🔄 手动同步机制
- **拉取数据**：一键从WebSocket服务器获取最新待办事项
- **手动同步**：将本地数据推送到服务器数据库
- **完全替换**：避免数据冲突，采用替换策略确保数据一致性

### 📧 智能邮件提醒
- **每日邮件**：每天24点自动发送待办事项到QQ邮箱
- **分类提醒**：按"任务"、"想尝试"、"提醒"分类显示
- **空任务提醒**：没有待办时也会发送鼓励邮件
- **开机自启**：通过VBS脚本实现开机自动启动

### 🌐 离线优先设计
- **本地存储**：手机端数据本地持久化存储
- **离线可用**：无网络时也能正常记录和查看待办
- **联网同步**：有网络时随时同步数据

### 🔒 安全兼容性
- **原生WebSocket**：不依赖Flask等Web框架，避免HTTP限制
- **Android 9+兼容**：不受明文HTTP传输限制影响
- **无需HTTPS证书**：纯WebSocket通信，更安全简便
- **本地部署**：所有数据都在本地，绝对安全

## 🚀 快速开始

### 环境要求
- Python 3.7+
- Node.js (用于uni-app开发，可选)
- Android手机 (用于APK安装)
- **注意**：不需要安装和配置Flask或其他Web服务器，使用原生WebSocket实现

### 安装步骤

#### 1. 克隆项目
```bash
git clone https://github.com/yourusername/todoapp.git
cd todoapp
```

#### 2. 安装Python依赖
```bash
pip install -r requirements.txt
```

#### 3. 启动WebSocket服务器
```bash
python app.py
```
或使用提供的批处理文件：
```bash
# Windows
启动TodoApp.bat
# 或者
启动服务.bat
```

**注意**：此命令会启动原生WebSocket服务器，无需Flask等Web框架。

#### 4. 安装手机APK
将 `TodoApp.apk` 安装到Android手机上

#### 5. 配置开机自启 (可选)
将 `启动TodoApp.vbs` 复制到Windows开机自启目录：
```
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\
```

**注意**：需要修改VBS文件中的路径为你自己的项目路径：
```vbs
WshShell.Run chr(34) & "你的项目路径\Todoapp.bat" & chr(34), 0
```

## 📁 项目结构

```
todoApp/
├── app.py                    # 原生WebSocket服务器 (36KB)
├── email_service.py          # 邮件服务模块 (15KB)
├── requirements.txt          # Python依赖
├── TodoApp.apk             # Android应用安装包 (14MB)
├── 启动TodoApp.vbs         # Windows启动脚本
├── 启动服务.bat            # Windows批处理启动
├── Todoapp.bat             # 项目专用启动脚本
├── start.py                # 备用启动脚本
├── LICENSE                 # MIT许可证
├── README.md               # 项目文档
├── App/                    # uni-app前端代码
│   ├── pages/              # 页面文件
│   ├── utils/              # 工具类
│   └── ...                # 其他前端资源
├── instance/               # SQLite数据库文件
│   └── task_manager.db     # 主数据库文件
├── tests/                 # 测试文件
└── __pycache__/           # Python缓存文件
```

**架构说明**：
- `app.py` 包含完整的原生WebSocket服务器实现
- 不依赖Flask等Web框架，使用纯Python Socket实现
- 兼容Android 9+网络安全策略，无需HTTPS配置

## ⚙️ 配置说明

### 邮件配置
在 `email_service.py` 中修改邮件配置：
```python
EMAIL_CONFIG = {
    'smtp_server': 'smtp.qq.com',    # SMTP服务器
    'port': 587,                     # SMTP端口
    'username': 'your@qq.com',        # QQ邮箱
    'password': 'your_password',       # QQ邮箱授权码
    'sender': 'your@qq.com',          # 发件人
    'recipient': 'your@qq.com'        # 收件人
}
```

### 服务器配置
默认配置：
- **WebSocket服务器**：`ws://localhost:5001` (原生实现，无需Flask)
- **数据库**：SQLite (自动创建)
- **端口说明**：5001端口用于WebSocket通信，无需HTTP服务

## 🎯 快速使用指南

### 第一次使用
1. **启动服务**：运行 `python app.py` 或双击 `启动服务.bat`
2. **安装APK**：在手机上安装 `TodoApp.apk`
3. **连接测试**：确保手机和电脑在同一WiFi下，打开APP测试连接
4. **配置邮箱**：修改 `email_service.py` 中的邮箱配置
5. **设置自启**：将VBS文件复制到启动文件夹

### 日常使用
1. **记录想法**：随时在手机上记录待办事项
2. **回家同步**：手机连上WiFi后自动同步数据
3. **查看邮件**：每天24点收到邮件提醒
4. **手动同步**：需要时可在APP上手动拉取或推送数据

## 🎯 使用场景

### 📱 移动办公
> 在外面突然想到一个好点子？打开TodoApp.apk快速记录，回家后自动通过WebSocket同步到电脑，再也不怕忘记！

### 🏠 家庭管理
> 把家里要办的事情记在手机上，回家打开电脑就能看到完整的待办清单。基于原生WebSocket实现，Android 9+完全兼容！

### 💡 创意记录
> 灵感总是来得突然？用手机随时记录，回到家在电脑上整理和完善，避免三分钟热度。无需担心HTTP限制！

### 📅 每日提醒
> 每天开机自动收到邮件提醒，查看今天的待办事项，合理安排一天的时间。WebSocket服务器确保稳定连接！

## 🔧 技术栈

### 后端技术
- **原生WebSocket服务器** - 纯Python Socket实现，无需Web框架
- **Flask-SQLAlchemy** - 数据库ORM
- **APScheduler** - 定时任务调度
- **SMTPlib** - 邮件发送
- **Threading** - 多线程客户端处理

### 前端技术
- **uni-app** - 跨平台移动应用框架
- **Vue.js** - 前端框架
- **原生WebSocket客户端** - 实时数据同步
- **LocalStorage** - 本地数据持久化

### 数据库
- **SQLite** - 轻量级本地数据库

### 架构优势
- **无HTTP依赖**：纯WebSocket通信，避免Android 9+限制
- **原生实现**：更稳定、更高效的通信方式
- **完全兼容**：支持所有Android版本，无需特殊配置

## 📋 功能特性

### ✅ 已实现功能
- [x] 跨平台数据同步
- [x] 本地数据持久化
- [x] 分类管理 (任务/想尝试/提醒)
- [x] 完成状态管理
- [x] 每日邮件提醒
- [x] WebSocket实时通信
- [x] 开机自启动
- [x] 数据库自动初始化

### 🚧 计划功能
- [ ] 数据备份和恢复
- [ ] 多语言支持
- [ ] 主题切换
- [ ] 任务优先级
- [ ] 附件支持
- [ ] 任务分享
- [ ] 多设备同步（扩展WebSocket协议）
- [ ] 端到端加密（基于WebSocket）

## 🐛 常见问题

### Q: 邮件发送失败怎么办？
A: 检查QQ邮箱授权码是否正确，确保网络连接正常。程序有30分钟失败重试保护机制。

### Q: 手机无法连接到电脑？
A: 确保手机和电脑在同一WiFi网络下，检查防火墙设置是否阻止了5001端口。注意：本项目使用纯WebSocket，不占用HTTP端口5000。

### Q: 为什么选择WebSocket而不是HTTP？
A: WebSocket不受Android 9+网络安全限制，无需HTTPS证书，连接更稳定，资源占用更少。

### Q: 数据同步有延迟？
A: 可以手动点击"拉取数据"或"手动同步"按钮进行强制同步。

### Q: 如何更换邮箱？
A: 修改 `email_service.py` 中的 `EMAIL_CONFIG` 配置即可。

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [Flask](https://flask.palletsprojects.com/) - 优秀的Web框架
- [uni-app](https://uniapp.dcloud.net.cn/) - 跨平台开发框架
- [Socket.IO](https://socket.io/) - 实时通信解决方案

---

## 📊 项目统计

![GitHub stars](https://img.shields.io/github/stars/chandou-code/TodoApp)
![GitHub forks](https://img.shields.io/github/forks/chandou-code/TodoApp)
![GitHub issues](https://img.shields.io/github/issues/chandou-code/TodoApp)
![GitHub license](https://img.shields.io/github/license/chandou-code/TodoApp)

## 🔗 相关链接

- **GitHub仓库**: https://github.com/chandou-code/TodoApp
- [Bug反馈](https://github.com/chandou-code/TodoApp/issues)
- [功能建议](https://github.com/chandou-code/TodoApp/issues/new?template=feature_request.md)
- [讨论区](https://github.com/chandou-code/TodoApp/discussions)

## 📝 更新日志

### v1.0.0 (2025-11-22)
- ✨ 首次发布
- 📱 支持Android应用
- 💻 支持PC端原生WebSocket服务器
- 🔄 实现纯WebSocket同步（无HTTP依赖）
- 📧 添加邮件提醒功能
- ⚡ 支持开机自启动
- 🔒 Android 9+完全兼容
- 🚫 无需HTTPS证书配置

---

⭐ 如果这个项目对你有帮助，请给个Star鼓励一下！

📧 有问题或建议？欢迎提交Issue或邮件联系我。

🔄 **原生WebSocket，自动同步，永不忘记！** 🔄
