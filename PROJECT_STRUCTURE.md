# TodoApp 项目结构说明

```
todoapp/
├── README.md                    # 项目说明文档
├── LICENSE                      # MIT 开源协议
├── .gitignore                   # Git 忽略文件
├── requirements.txt              # Python 依赖包
├── app.py                      # Flask 后端入口
├── start.py                     # 一键启动脚本
├── websocket_schema.md           # WebSocket 通信协议
├── instance/                    # Flask 实例文件夹
│   └── task_manager.db         # SQLite 数据库文件
├── App/                        # UniApp 前端项目
│   ├── manifest.json            # UniApp 配置文件
│   ├── pages.json              # 页面路由配置
│   ├── package.json            # NPM 依赖配置
│   ├── main.js                # UniApp 入口文件
│   ├── App.vue                # 根组件
│   ├── index.html             # H5 入口 HTML
│   ├── uni.scss               # 全局样式
│   ├── pages/                 # 页面目录
│   │   └── index/            # 首页
│   │       ├── index.vue      # 主页面组件
│   │       └── index.json    # 页面配置
│   ├── utils/                 # 工具类目录
│   │   └── websocketManager.js  # WebSocket 管理器
│   ├── static/                # 静态资源
│   ├── res/                   # 资源文件
│   └── unpackage/             # 编译输出目录
└── venv/                      # Python 虚拟环境
```

## 核心文件说明

### 后端核心文件

- **app.py**: Flask 应用主文件，包含：
  - API 路由定义
  - WebSocket 事件处理
  - 数据库模型
  - 定时任务配置
  - CORS 设置

### 前端核心文件

- **App/pages/index/index.vue**: 主页面组件，包含：
  - 任务列表展示
  - 任务分类切换
  - 添加/编辑任务
  - WebSocket 连接管理
  - 本地存储逻辑

- **App/utils/websocketManager.js**: WebSocket 通信管理器，包含：
  - 连接建立和重连
  - 消息发送和接收
  - 事件监听器管理
  - 错误处理

### 配置文件

- **App/manifest.json**: UniApp 应用配置，包含：
  - 应用基本信息
  - 平台特定配置
  - 网络安全设置
  - 开发代理配置

- **requirements.txt**: Python 依赖包列表
- **package.json**: 前端 NPM 依赖

### 文档文件

- **README.md**: 项目主要说明文档
- **websocket_schema.md**: WebSocket 通信协议详细说明
- **LICENSE**: 开源协议文件
- **PROJECT_STRUCTURE.md**: 本结构说明文件

## 数据流向

```
用户操作 → index.vue → websocketManager.js → WebSocket → Flask-SocketIO → SQLAlchemy → SQLite
     ↑                                                                                ↓
     ↑                                    WebSocket 响应                                数据持久化
     ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←
```

## 技术要点

1. **离线优先策略**: 本地存储为主，网络恢复后同步
2. **实时通信**: 基于 Socket.IO 的双向通信
3. **跨平台能力**: UniApp 框架支持多端发布
4. **数据安全**: 前后端验证 + 本地存储加密
5. **自动重连**: WebSocket 断开自动重连机制