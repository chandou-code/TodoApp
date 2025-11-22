# TodoApp - 跨平台待办事项应用

<div align="center">
  <img src="https://img.shields.io/badge/Flask-2.3.2-green" alt="Flask Version">
  <img src="https://img.shields.io/badge/UniApp-Vue3-blue" alt="Framework">
  <img src="https://img.shields.io/badge/WebSocket-Socket.IO-orange" alt="WebSocket">
  <img src="https://img.shields.io/badge/SQLite-Database-lightgrey" alt="Database">
</div>

## 📝 项目简介

TodoApp 是一个基于 **UniApp + Flask** 的跨平台待办事项应用，支持多端同步和实时协作。应用采用前后端分离架构，具备完善的离线优先策略和 WebSocket 实时通信能力。

### ✨ 核心特性

- 🌐 **跨平台支持**：一套代码，多端发布（H5、App、小程序）
- 🔄 **实时同步**：基于 WebSocket 的实时数据同步
- 📱 **离线优先**：支持离线使用，网络恢复后自动同步
- 🎯 **任务分类**：支持任务、想尝试、提醒三种分类
- 🔔 **邮件提醒**：每日定时发送待办任务邮件通知
- 💾 **本地存储**：本地持久化存储，数据安全可靠
- 🔄 **自动重连**：网络断开自动重连，保证连接稳定性

## 🏗️ 技术架构

### 前端技术栈

- **框架**: UniApp (Vue 3)
- **UI组件**: @dcloudio/uni-ui
- **状态管理**: Vue Composition API
- **通信方式**: Socket.IO Client + WebSocket
- **存储**: uni.storage (本地存储)

### 后端技术栈

- **框架**: Flask 2.3.2
- **数据库**: SQLite + SQLAlchemy ORM
- **实时通信**: Flask-SocketIO + eventlet
- **任务调度**: APScheduler (定时邮件)
- **跨域支持**: Flask-Cors

### 系统架构图

```
┌─────────────────┐    WebSocket     ┌─────────────────┐
│   UniApp 前端  │ ◄──────────────► │  Flask 后端    │
│                │                 │                │
│ - H5/APP/小程序  │                 │ - RESTful API  │
│ - 本地存储       │                 │ - WebSocket     │
│ - 离线优先     │                 │ - 定时任务     │
└─────────────────┘                 └─────────────────┘
        │                                 │
        ▼                                 ▼
┌─────────────────┐                 ┌─────────────────┐
│  浏览器存储     │                 │   SQLite 数据库   │
└─────────────────┘                 └─────────────────┘
```

## 🚀 快速开始

### 环境要求

- **Python**: 3.8+
- **Node.js**: 16+
- **UniApp CLI**: 最新版本

### 1. 克隆项目

```bash
git clone https://github.com/chandou-code/todoapp.git
cd todoapp
```

### 2. 后端启动

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动后端服务
python app.py
```

后端服务将启动在 `http://localhost:5000`

### 3. 前端启动

```bash
# 进入前端目录
cd App

# 安装依赖
npm install

# 启动开发服务器
npm run dev:h5
```

前端开发服务器将启动在 `http://localhost:8080`

## 📱 平台发布

### H5 部署

```bash
# 构建生产版本
npm run build:h5

# 部署到 Web 服务器
# 将 dist/build/h5 目录部署到 Nginx/Apache 等
```

### App 发布

```bash
# 使用 HBuilderX 打包
# 1. 用 HBuilderX 打开项目
# 2. 发行 -> 原生App-云打包
# 3. 选择 Android/iOS 平台
# 4. 配置签名信息和打包参数
```

### 小程序发布

```bash
# 微信小程序
npm run dev:mp-weixin

# 支付宝小程序  
npm run dev:mp-alipay

# 构建发布版本
npm run build:mp-weixin
```

## 🔧 配置说明

### 后端配置

1. **数据库配置**：
   ```python
   # app.py
   app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///task_manager.db'
   ```

2. **邮件配置**：
   ```python
   # 修改 app.py 中的邮件配置
   EMAIL_CONFIG = {
       'smtp_server': 'smtp.qq.com',
       'port': 587,
       'username': 'your@qq.com',
       'password': 'your_password',
       'sender': 'your@qq.com',
       'recipient': 'recipient@qq.com'
   }
   ```

3. **CORS 配置**：
   ```python
   # 已配置允许所有域名，生产环境建议限制
   CORS(app)
   ```

### 前端配置

1. **网络配置** (`App/manifest.json`)：
   ```json
   {
     "h5": {
       "devServer": {
         "proxy": {
           "/api": {
             "target": "http://localhost:5000",
             "changeOrigin": true
           }
         }
       }
     }
   }
   ```

2. **网络安全配置**：
   ```json
   {
     "networkSecurity": {
       "domains": {
         "*": ["localhost", "127.0.0.1", "192.168.1.*"]
       }
     }
   }
   ```

## 📊 API 文档

### RESTful API

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/tasks` | 获取任务列表 |
| POST | `/api/tasks` | 创建新任务 |
| PUT | `/api/tasks/:id` | 更新任务 |
| DELETE | `/api/tasks/:id` | 删除任务 |
| PUT | `/api/tasks/:id/complete` | 更新完成状态 |

### WebSocket 事件

详细的 WebSocket 通信协议请参考 [WebSocket Schema 文档](./websocket_schema.md)

## 🎨 界面预览

### 主要功能界面

1. **任务列表页**
   - 按分类展示任务
   - 已完成/未完成任务分组
   - 支持展开/收起已完成任务

2. **添加/编辑任务**
   - 标题和内容编辑
   - 分类选择
   - 实时保存和同步

3. **同步状态显示**
   - 连接状态指示器
   - 同步进度显示
   - 错误状态提示

## 🔒 安全特性

- **数据验证**: 前后端双重数据验证
- **XSS防护**: 输入内容过滤和转义
- **CSRF保护**: API 请求Token验证
- **网络安全**: 配置允许的域名白名单
- **SQL注入防护**: SQLAlchemy ORM 参数化查询

## 📈 性能优化

- **离线缓存**: 本地存储减少网络请求
- **数据分页**: 大量数据分页加载
- **连接复用**: WebSocket 长连接减少握手开销
- **图片压缩**: 资源文件压缩优化
- **代码分割**: 按需加载减少初始化时间

## 🧪 测试

### 运行测试

```bash
# 后端测试
python -m pytest

# 前端测试
cd App && npm test
```

### 测试覆盖

- ✅ 单元测试: 核心业务逻辑
- ✅ 集成测试: API 和 WebSocket
- ✅ E2E测试: 完整用户流程
- ✅ 性能测试: 并发和压力测试

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### 代码规范

- **Python**: 遵循 PEP 8 规范
- **JavaScript**: 使用 ESLint + Prettier
- **Vue3**: 使用 Composition API
- **提交信息**: 使用约定式提交格式

## 📝 更新日志

### v1.0.0 (2024-11-22)

#### ✨ 新特性
- 🎉 初始版本发布
- 📱 跨平台支持 (H5/Android/iOS/小程序)
- 🔄 WebSocket 实时同步
- 💾 离线优先策略
- 🎯 任务分类管理
- 🔔 邮件提醒功能
- 📊 数据统计展示

#### 🐛 Bug修复
- 修复 WebSocket 连接超时问题
- 修复数据同步冲突
- 修复本地存储异常

#### ⚡ 性能优化
- 优化 WebSocket 重连机制
- 优化本地存储读写性能
- 减少不必要的网络请求

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

感谢以下开源项目：

- [UniApp](https://uniapp.dcloud.io/) - 跨平台开发框架
- [Flask](https://flask.palletsprojects.com/) - Python Web 框架
- [Socket.IO](https://socket.io/) - 实时通信库
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python ORM 工具

## 📞 联系方式

- **作者**: chandou-code
- **GitHub**: https://github.com/chandou-code
- **邮箱**: [your-email@example.com]

---

<div align="center">
  <p>如果这个项目对你有帮助，请给个 ⭐️ 支持一下！</p>
</div>