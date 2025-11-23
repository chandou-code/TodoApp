from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import json
import threading
import time
import base64
import hashlib
from email_service import EmailService
# 导入备份模块
from backup import init_app as init_backup, auto_backup

app = Flask(__name__)
CORS(app)  # 启用CORS支持所有域名的请求
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///task_manager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# 简单的WebSocket服务器类
class SimpleWebSocketServer:
    def __init__(self, app, host='0.0.0.0', port=5001):
        self.app = app
        self.host = host
        self.port = port
        self.clients = set()
        self.running = False

    def add_client(self, websocket):
        self.clients.add(websocket)
        print(f'WebSocket客户端已连接: {len(self.clients)} 个客户端')

    def remove_client(self, websocket):
        self.clients.discard(websocket)
        print(f'WebSocket客户端已断开: {len(self.clients)} 个客户端')

    def broadcast_to_all(self, message):
        """向所有连接的客户端广播消息"""
        if not self.clients:
            return
        
        message_str = json.dumps(message)
        dead_clients = set()
        
        for client_socket in self.clients:
            try:
                self.send_to_client(client_socket, message_str, is_string=True)
            except Exception as e:
                print(f'广播消息失败: {e}')
                dead_clients.add(client_socket)
        
        # 清理死连接
        for client in dead_clients:
            self.remove_client(client)

    def start(self):
        """启动WebSocket服务器线程"""

        def run_server():
            try:
                import socket
                import select

                server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server_socket.bind((self.host, self.port))
                server_socket.listen(5)
                self.running = True
                print(f'原生WebSocket服务器启动在 ws://{self.host}:{self.port}')

                while self.running:
                    try:
                        readable, _, _ = select.select([server_socket], [], [], 1)
                        if server_socket in readable:
                            client_socket, address = server_socket.accept()
                            print(f'新WebSocket连接来自: {address}')

                            # 启动客户端处理线程
                            client_thread = threading.Thread(
                                target=self.handle_client,
                                args=(client_socket, address),
                                daemon=True
                            )
                            client_thread.start()
                    except Exception as e:
                        if self.running:
                            print(f'WebSocket服务器错误: {e}')

            except Exception as e:
                print(f'启动WebSocket服务器失败: {e}')

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

    def handle_client(self, client_socket, address):
        """处理单个WebSocket客户端"""
        try:
            # WebSocket握手
            data = client_socket.recv(1024).decode('utf-8')
            if 'Sec-WebSocket-Key' in data:
                # 执行WebSocket握手
                lines = data.split('\r\n')  # 修复这里：使用转义字符
                key_line = [line for line in lines if line.startswith('Sec-WebSocket-Key:')][0]
                key = key_line.split(': ')[1]
                accept_key = self.compute_accept_key(key)

                response = (
                        "HTTP/1.1 101 Switching Protocols\r\n"
                        "Upgrade: websocket\r\n"
                        "Connection: Upgrade\r\n"
                        "Sec-WebSocket-Accept: " + accept_key + "\r\n\r\n"
                )
                client_socket.send(response.encode('utf-8'))

                # 添加到客户端列表
                self.add_client(client_socket)

                # 处理消息
                while self.running:
                    try:
                        data = client_socket.recv(1024)
                        if not data:
                            break

                        # 解析WebSocket帧
                        message = self.parse_websocket_frame(data)
                        if message:
                            self.handle_message(client_socket, message)

                    except Exception as e:
                        print(f'处理WebSocket消息错误: {e}')
                        break

        except Exception as e:
            print(f'WebSocket客户端处理错误: {e}')
        finally:
            self.remove_client(client_socket)
            client_socket.close()

    def compute_accept_key(self, key):
        """计算WebSocket握手accept key"""
        MAGIC_STRING = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        accept = base64.b64encode(
            hashlib.sha1((key + MAGIC_STRING).encode('utf-8')).digest()
        ).decode('utf-8')
        return accept

    def parse_websocket_frame(self, data):
        """解析WebSocket数据帧"""
        if len(data) < 2:
            return None

        # 第一个字节：FIN和操作码
        first_byte = data[0]
        fin = (first_byte & 0x80) != 0
        opcode = first_byte & 0x0f

        # 第二个字节：掩码和负载长度
        second_byte = data[1]
        masked = (second_byte & 0x80) != 0
        payload_length = second_byte & 0x7f

        offset = 2

        # 扩展负载长度
        if payload_length == 126:
            payload_length = int.from_bytes(data[offset:offset + 2], 'big')
            offset += 2
        elif payload_length == 127:
            payload_length = int.from_bytes(data[offset:offset + 8], 'big')
            offset += 8

        # 掩码
        if masked:
            mask = data[offset:offset + 4]
            offset += 4
        else:
            mask = None

        # 负载数据
        payload = data[offset:offset + payload_length]

        # 如果有掩码，解码
        if mask:
            payload = bytes([b ^ mask[i % 4] for i, b in enumerate(payload)])

        try:
            return payload.decode('utf-8')
        except:
            return payload.decode('utf-8', errors='ignore')

    def handle_message(self, client_socket, message):
        """处理接收到的WebSocket消息"""
        with self.app.app_context():  # 添加应用上下文
            try:
                data = json.loads(message)
                event_type = data.get('type')
                payload = data.get('data', {})

                print(f'收到WebSocket消息: {event_type}')

                # 根据事件类型处理
                if event_type == 'fetch_tasks':
                    tasks = Task.query.order_by(Task.created_at.desc()).all()
                    response = {
                        'type': 'tasks_data',
                        'data': {
                            'tasks': [task.to_dict() for task in tasks]
                        }
                    }
                    self.send_to_client(client_socket, response)

                elif event_type == 'create_task':
                    # 创建任务逻辑
                    task_data = payload.get('task', payload)  # 兼容两种格式
                    request_id = data.get('requestId')

                    if 'content' in task_data and task_data['content'].strip():
                        new_task = Task(
                            title=task_data.get('title'),
                            content=task_data['content'],
                            category=task_data.get('category', '任务'),
                            completed=task_data.get('completed', False)
                        )
                        db.session.add(new_task)
                        db.session.commit()
                        task_data = new_task.to_dict()

                        # 广播任务创建通知给所有客户端
                        broadcast_message = {
                            'type': 'sync_notification',
                            'data': {
                                'action': 'create',
                                'task': task_data
                            }
                        }
                        self.broadcast_to_all(broadcast_message)

                        # 发送创建响应给请求客户端
                        response = {
                            'type': 'task_created',
                            'data': {
                                'task': task_data,
                                'requestId': request_id
                            }
                        }
                        print(f'发送创建任务响应，requestId: {request_id}, task: {task_data}')
                        self.send_to_client(client_socket, response)

                elif event_type == 'update_task':
                    # 更新任务逻辑
                    task_id = payload.get('id')
                    if task_id:
                        task = Task.query.get(task_id)
                        if task:
                            # 从payload中获取任务数据
                            task_data = payload.get('task', payload)
                            
                            if 'content' in task_data:
                                task.content = task_data['content']
                            if 'title' in task_data:
                                task.title = task_data['title']
                            if 'category' in task_data:
                                task.category = task_data['category']
                            if 'completed' in task_data:
                                task.completed = task_data['completed']
                                if task_data['completed']:
                                    task.completed_at = datetime.utcnow()
                                else:
                                    task.completed_at = None
                            db.session.commit()
                            updated_task_data = task.to_dict()

                            # 广播任务更新通知给所有客户端
                            broadcast_message = {
                                'type': 'sync_notification',
                                'data': {
                                    'action': 'update',
                                    'task': updated_task_data
                                }
                            }
                            self.broadcast_to_all(broadcast_message)

                            # 发送更新响应给请求客户端
                            response = {
                                'type': 'task_updated',
                                'data': {
                                    'task': updated_task_data,
                                    'requestId': data.get('requestId')
                                }
                            }
                            self.send_to_client(client_socket, response)

                elif event_type == 'delete_task':
                    # 删除任务逻辑
                    task_id = payload.get('id')
                    if task_id:
                        task = Task.query.get(task_id)
                        if task:
                            db.session.delete(task)
                            db.session.commit()

                            response = {
                                'type': 'task_deleted',
                                'data': {
                                    'id': task_id,
                                    'requestId': data.get('requestId')
                                }
                            }
                            self.send_to_client(client_socket, response)

                elif event_type == 'update_task_completed':
                    # 更新任务完成状态逻辑
                    task_id = payload.get('id')
                    completed = payload.get('completed')

                    if task_id is not None and completed is not None:
                        task = Task.query.get(task_id)
                        if task:
                            task.completed = completed
                            if completed:
                                task.completed_at = datetime.utcnow()
                            else:
                                task.completed_at = None
                            db.session.commit()

                            response = {
                                'type': 'task_completed_updated',
                                'data': {
                                    'task': task.to_dict(),
                                    'requestId': data.get('requestId')
                                }
                            }
                            self.send_to_client(client_socket, response)

                elif event_type == 'clear_all_tasks':
                    # 清空所有任务
                    try:
                        Task.query.delete()
                        db.session.commit()
                        
                        response = {
                            'type': 'all_tasks_cleared',
                            'data': {}
                        }
                        self.send_to_client(client_socket, response)
                    except Exception as e:
                        print(f'清空任务失败: {e}')
                        error_response = {
                            'type': 'error',
                            'data': {
                                'code': 'CLEAR_ERROR',
                                'message': f'清空任务失败: {str(e)}'
                            }
                        }
                        self.send_to_client(client_socket, error_response)
                        
                elif event_type == 'ping':
                    # 心跳响应
                    response = {'type': 'pong', 'data': {}}
                    self.send_to_client(client_socket, response)

            except Exception as e:
                print(f'处理WebSocket消息失败: {e}')
                error_response = {
                    'type': 'error',
                    'data': {
                        'code': 'PROCESS_ERROR',
                        'message': f'处理消息失败: {str(e)}'
                    }
                }
                self.send_to_client(client_socket, error_response)

    def send_to_client(self, client_socket, message, is_string=False):
        """向特定客户端发送消息"""
        try:
            if not is_string:
                json_message = json.dumps(message)
            else:
                json_message = message
            frame = self.create_websocket_frame(json_message)
            client_socket.send(frame)
        except Exception as e:
            print(f'发送消息到客户端失败: {e}')

    def create_websocket_frame(self, message):
        """创建WebSocket数据帧"""
        message_bytes = message.encode('utf-8')
        message_length = len(message_bytes)

        frame = bytearray()

        # 第一个字节：FIN=1, 操作码=1 (文本)
        frame.append(0x81)

        # 负载长度
        if message_length < 126:
            frame.append(message_length)
        elif message_length < 65536:
            frame.append(126)
            frame.extend(message_length.to_bytes(2, 'big'))
        else:
            frame.append(127)
            frame.extend(message_length.to_bytes(8, 'big'))

        # 负载数据
        frame.extend(message_bytes)

        return bytes(frame)

    def stop(self):
        """停止WebSocket服务器"""
        self.running = False


# 初始化原生WebSocket服务器
websocket_server = SimpleWebSocketServer(app, host='0.0.0.0', port=5001)

# 任务分类枚举
TASK_CATEGORIES = ['任务', '想尝试', '提醒']

# 初始化邮件服务
email_service = EmailService()

# 全局标志防止重复初始化邮件服务
_email_service_initialized = False


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=True)  # 选填标题
    content = db.Column(db.Text, nullable=False)  # 必填内容
    category = db.Column(db.String(50), nullable=False, default='任务')  # 分类
    completed = db.Column(db.Boolean, default=False)  # 完成状态
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 创建时间
    completed_at = db.Column(db.DateTime, nullable=True)  # 完成时间

    def to_dict(self):
        return {
            'id': str(self.id),
            'title': self.title,
            'content': self.content,
            'category': self.category,
            'completed': self.completed,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


# 邮件发送历史记录表
class EmailLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)  # 发送时间
    task_count = db.Column(db.Integer, default=0)  # 发送的任务数量
    status = db.Column(db.Boolean, default=True)  # 发送状态，True表示成功

    def to_dict(self):
        return {
            'id': self.id,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'task_count': self.task_count,
            'status': self.status
        }


# 初始化数据库
with app.app_context():
    db.create_all()

def init_email_service_once():
    """延迟初始化邮件服务，防止Flask重启时重复调用"""
    global _email_service_initialized
    if not _email_service_initialized:
        with app.app_context():
            # 初始化邮件服务
            email_service.init_app(app, db, Task, EmailLog)
            
            # 应用启动时检查邮件发送状态（避免重复发送）
            email_service.init_daily_check()
            
            _email_service_initialized = True
            print("邮件服务初始化完成")

# 在应用启动时初始化邮件服务
init_email_service_once()


# CORS中间件
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


# 根路径路由
@app.route('/', methods=['GET', 'OPTIONS'])
def index():
    # 处理OPTIONS预检请求
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'CORS preflight'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

    try:
        # 记录请求信息用于调试
        print(f"根路径请求 - User-Agent: {request.headers.get('User-Agent', 'Unknown')}")
        print(f"根路径请求 - Headers: {dict(request.headers)}")

        response_data = {
            'message': 'TodoApp API Server',
            'version': '1.0.0',
            'status': 'running',
            'endpoints': {
                'tasks': '/api/tasks',
                'create_task': '/api/tasks (POST)',
                'update_task': '/api/tasks/<id> (PUT)',
                'delete_task': '/api/tasks/<id> (DELETE)',
                'complete_task': '/api/tasks/<id>/complete (PUT)',
                'test_email': '/api/send-test-email (POST)'
            },
            'websocket_events': [
                'connect', 'disconnect', 'fetch_tasks',
                'create_task', 'update_task', 'delete_task',
                'toggle_complete', 'sync_tasks', 'ping'
            ]
        }

        response = jsonify(response_data)
        # 确保CORS头被正确设置
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')

        return response

    except Exception as e:
        print(f"根路径处理错误: {str(e)}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': str(e)
        }), 500


# API接口

# 获取任务列表
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    category = request.args.get('category', type=str)
    completed = request.args.get('completed', type=lambda v: v.lower() == 'true')

    query = Task.query

    if category and category in TASK_CATEGORIES:
        query = query.filter_by(category=category)

    if completed is not None:
        query = query.filter_by(completed=completed)

    tasks = query.order_by(Task.created_at.desc()).all()
    return jsonify([task.to_dict() for task in tasks])


# 创建新任务
@app.route('/api/tasks', methods=['POST'])
def create_task():
    data = request.get_json()

    if not data or 'content' not in data:
        return jsonify({'error': '内容是必填项'}), 400

    category = data.get('category', '任务')
    if category not in TASK_CATEGORIES:
        return jsonify({'error': '无效的分类'}), 400

    new_task = Task(
        title=data.get('title'),
        content=data['content'],
        category=category
    )

    db.session.add(new_task)
    db.session.commit()

    return jsonify(new_task.to_dict()), 201


# 获取单个任务
@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    task = Task.query.get_or_404(task_id)
    return jsonify(task.to_dict())


# 更新任务
@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.get_json()

    if not data:
        return jsonify({'error': '请求数据为空'}), 400

    if 'content' in data:
        task.content = data['content']

    if 'title' in data:
        task.title = data['title']

    if 'category' in data:
        if data['category'] not in TASK_CATEGORIES:
            return jsonify({'error': '无效的分类'}), 400
        task.category = data['category']

    db.session.commit()
    return jsonify(task.to_dict())


# 删除任务
@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return jsonify({'message': '任务删除成功'})


# 更新任务完成状态
@app.route('/api/tasks/<int:task_id>/complete', methods=['PUT'])
def complete_task(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.get_json()

    completed = data.get('completed', not task.completed)
    task.completed = completed

    if completed:
        task.completed_at = datetime.utcnow()
    else:
        task.completed_at = None

    db.session.commit()
    return jsonify(task.to_dict())


# 添加一个辅助函数来手动触发邮件发送（用于测试）
@app.route('/api/send-test-email', methods=['POST'])
def send_test_email():
    try:
        message = email_service.send_test_email()
        return jsonify({'message': message}), 200
    except Exception as e:
        return jsonify({'error': f'发送失败: {str(e)}'}), 500


# 广播函数，用于在任务变更时通知所有客户端
def broadcast_task_change(action, task_data):
    """通过原生WebSocket广播任务变更给所有连接的客户端"""
    message = {
        'type': 'sync_notification',
        'data': {
            'action': action,
            'task': task_data
        }
    }
    websocket_server.broadcast_to_all(message)


# 启动应用
# 初始化备份模块
init_backup(app, db, Task)

if __name__ == '__main__':
    # 启动前自动备份数据库
    auto_backup()
    
    # 启动原生WebSocket服务器
    websocket_server.start()
    time.sleep(1)  # 等待WebSocket服务器启动

    # 启动Flask应用（仅用于HTTP API）
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)