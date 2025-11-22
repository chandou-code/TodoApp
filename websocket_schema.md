# WebSocket 通信方案设计

## 1. 消息格式

所有WebSocket消息将采用JSON格式，包含以下基本字段：

```json
{
  "type": "事件类型",
  "payload": { /* 消息数据 */ },
  "requestId": "请求标识符" // 可选，用于请求-响应配对
}
```

## 2. 事件类型设计

### 2.1 客户端发送到服务器的事件

| 事件类型 | 描述 | payload 格式 | 对应原HTTP操作 |
|---------|------|------------|------------|
| `fetch_tasks` | 获取任务列表 | `{"category": "任务类别", "completed": true/false}` (可选) | GET /api/tasks |
| `create_task` | 创建新任务 | `{"title": "标题", "content": "内容", "category": "任务类别"}` | POST /api/tasks |
| `update_task` | 更新任务 | `{"id": "任务ID", "title": "标题", "content": "内容", "category": "任务类别"}` | PUT /api/tasks/:id |
| `delete_task` | 删除任务 | `{"id": "任务ID"}` | DELETE /api/tasks/:id |
| `toggle_complete` | 切换任务完成状态 | `{"id": "任务ID", "completed": true/false}` | PUT /api/tasks/:id/complete |
| `sync_tasks` | 同步本地未同步任务 | `{"tasks": [任务对象数组]}` | 批量同步 |
| `ping` | 心跳检测 | 无或空对象 | 无 |

### 2.2 服务器发送到客户端的事件

| 事件类型 | 描述 | payload 格式 |
|---------|------|------------|
| `tasks_data` | 任务数据（获取任务列表响应） | `{"tasks": [任务对象数组]}` |
| `task_created` | 任务创建成功响应 | `{"task": 任务对象, "tempId": "临时ID"}` |
| `task_updated` | 任务更新成功响应 | `{"task": 任务对象}` |
| `task_deleted` | 任务删除成功响应 | `{"id": "任务ID"}` |
| `sync_result` | 批量同步结果 | `{"success": true/false, "syncedTasks": [任务对象数组], "errors": []}` |
| `sync_notification` | 其他客户端的变更通知 | `{"action": "create/update/delete", "task": 任务对象}` |
| `error` | 错误响应 | `{"code": "错误代码", "message": "错误消息"}` |
| `pong` | 心跳响应 | 无或空对象 |

## 3. 任务对象格式

```json
{
  "id": "任务ID", // 服务器生成的ID或临时ID
  "title": "任务标题", // 可选
  "content": "任务内容", // 必填
  "category": "任务类别", // 任务、想尝试、提醒
  "completed": false, // 完成状态
  "created_at": "2024-01-01T12:00:00Z", // ISO格式时间
  "completed_at": "2024-01-01T12:00:00Z", // 可选，完成时间
  "needsSync": false // 客户端字段，标记是否需要同步
}
```

## 4. 通信流程

### 4.1 连接建立
1. 客户端连接到WebSocket服务器
2. 服务器验证连接
3. 客户端发送心跳保持连接

### 4.2 任务同步策略
1. **离线优先**：继续保持离线优先策略
2. **本地存储**：保留本地任务存储机制
3. **自动重连**：WebSocket连接断开时自动重连
4. **连接恢复后同步**：重连成功后自动同步本地未同步任务

### 4.3 冲突解决
1. 基于时间戳的冲突检测
2. 客户端优先原则（保持离线优先体验）

## 5. 错误处理
1. 连接错误：自动重试连接
2. 操作错误：记录错误并保持离线可用
3. 网络中断：保存到本地，等待网络恢复

## 6. 安全考虑
1. 消息验证：验证所有消息格式和内容
2. 防止过度请求：实施请求限流
3. 数据验证：在服务器端重新验证所有数据