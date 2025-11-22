from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.background import BackgroundScheduler
from flask_socketio import SocketIO, emit, join_room
import json
import eventlet

# 替换标准库的线程实现，以支持SocketIO的异步功能
eventlet.monkey_patch()

app = Flask(__name__)
CORS(app)  # 启用CORS支持所有域名的请求
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///task_manager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 初始化SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# 存储连接的客户端
connected_clients = set()

# 任务分类枚举
TASK_CATEGORIES = ['任务', '想尝试', '提醒']

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
            'title': self.title,
            'content': self.content,
            'category': self.category,
            'completed': self.completed,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

# 初始化数据库
with app.app_context():
    db.create_all()

# 邮件配置
EMAIL_CONFIG = {
    'smtp_server': 'smtp.qq.com',
    'port': 587,
    'username': 'xxxxxxxx@qq.com',
    'password': 'xxxxxxxx',
    'sender': 'xxxxxxxx@qq.com',
    'recipient': 'xxxxxxxx@qq.com'
}

# 发送邮件函数
def send_email_tasks():
    with app.app_context():
        # 获取所有未完成的任务
        tasks = Task.query.filter_by(completed=False).all()

        if not tasks:
            # 如果没有待办任务，也发送一封空邮件通知
            email_content = """
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px;">今日待办事项</h2>
                <p style="color: #666; font-size: 16px;">目前没有待办任务，继续保持！</p>
            </div>
            """
        else:
            # 按分类组织任务
            tasks_by_category = {}
            for category in TASK_CATEGORIES:
                tasks_by_category[category] = [task for task in tasks if task.category == category]

            # 构建邮件内容
            email_content = """
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px;">待办任务清单</h2>
                <p style="color: #666; font-size: 16px; background-color: #f9f9f9; padding: 10px; border-radius: 5px;">
                    待办任务总数：<strong>{}</strong>
                </p>
            """.format(len(tasks))

            for category, category_tasks in tasks_by_category.items():
                if category_tasks:
                    email_content += """
                    <div style="margin: 20px 0;">
                        <h3 style="color: #4CAF50; background-color: #f5f5f5; padding: 10px; border-radius: 5px;">
                            {} ({})
                        </h3>
                        <ul style="list-style-type: none; padding: 0;">
                    """.format(category, len(category_tasks))

                    for index, task in enumerate(category_tasks, 1):
                        task_title = task.title if task.title else ""
                        task_content = task.content if task.content else "无详细内容"
                        created_date = task.created_at.strftime('%Y-%m-%d') if task.created_at else "未知"

                        # 如果有标题，显示标题；否则只显示序号和内容
                        if task_title:
                            display_text = "<span style='font-weight: bold; color: #333; font-size: 16px;'>{}. {}</span>".format(
                                index, task_title)
                        else:
                            display_text = "<span style='font-weight: bold; color: #333; font-size: 16px;'>{}. {}</span>".format(
                                index, '')

                        email_content += """
                        <li style="background-color: #fff; margin: 10px 0; padding: 15px; border-radius: 8px; border-left: 4px solid #4CAF50; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            {}
                            <div style="color: #666; margin-top: 5px; font-size: 14px;">{}</div>
                            <div style="color: #999; font-size: 12px; margin-top: 8px;">创建时间: {}</div>
                        </li>
                        """.format(display_text, task_content, created_date)

                    email_content += """
                        </ul>
                    </div>
                    """

            email_content += "</div>"

        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['sender']
        msg['To'] = EMAIL_CONFIG['recipient']
        msg['Subject'] = f"待办事项提醒 - {datetime.now().strftime('%Y-%m-%d')}"

        msg.attach(MIMEText(email_content, 'html'))

        try:
            # 发送邮件
            server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['port'])
            server.starttls()
            server.login(EMAIL_CONFIG['username'], EMAIL_CONFIG['password'])
            server.send_message(msg)
            server.quit()
            print(f"邮件发送成功: {datetime.now()}")

            # 记录发送历史
            email_log = EmailLog(
                sent_at=datetime.utcnow(),
                task_count=len(tasks),
                status=True
            )
            db.session.add(email_log)
            db.session.commit()
        except Exception as e:
            print(f"邮件发送失败: {e}")
            # 记录失败状态
            email_log = EmailLog(
                sent_at=datetime.utcnow(),
                task_count=len(tasks) if 'tasks' in locals() else 0,
                status=False
            )
            db.session.add(email_log)
            db.session.commit()
# 配置定时任务
scheduler = BackgroundScheduler(timezone='Asia/Shanghai')  # 设置为上海时区

# 配置应用设置
app.config['MAIL_NOTIFICATION_ENABLED'] = True  # 可以通过环境变量控制是否启用邮件通知

# 检查今天是否已经发送过邮件
def check_today_email_sent():
    with app.app_context():
        # 获取今天的开始时间（UTC时间）
        today = datetime.utcnow().date()
        start_of_day = datetime.combine(today, datetime.min.time())

        # 查询今天是否有成功发送的邮件记录
        today_logs = EmailLog.query.filter(
            EmailLog.sent_at >= start_of_day,
            EmailLog.status == True
        ).first()

        return today_logs is not None

# 每天24点（午夜）执行
scheduler.add_job(
    func=send_email_tasks,
    trigger="cron",
    hour=0,
    minute=0,
    id='daily_todo_email',
    replace_existing=True,
    coalesce=True,  # 如果任务积压，只执行一次
    max_instances=1  # 最多只有一个实例运行
)

# 添加一个辅助函数来手动触发邮件发送（用于测试）
@app.route('/api/send-test-email', methods=['POST'])
def send_test_email():
    if not app.config.get('MAIL_NOTIFICATION_ENABLED', True):
        return jsonify({'error': '邮件通知功能已禁用'}), 403

    try:
        send_email_tasks()
        return jsonify({'message': '测试邮件已发送'}), 200
    except Exception as e:
        return jsonify({'error': f'发送失败: {str(e)}'}), 500

scheduler.start()
print("定时任务已启动: 每天午夜24点发送待办事项邮件")

# 应用启动时检查今天是否已发送邮件
with app.app_context():
    if check_today_email_sent():
        print("今日邮件已发送，无需重复发送")
    else:
        print("今日邮件未发送，正在立即发送...")
        if app.config.get('MAIL_NOTIFICATION_ENABLED', True):
            send_email_tasks()
        else:
            print("邮件通知功能已禁用，跳过发送")

# CORS中间件
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

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

# WebSocket事件处理

@socketio.on('connect')
def handle_connect():
    """处理客户端连接"""
    client_id = request.sid
    connected_clients.add(client_id)
    print(f'客户端已连接: {client_id}')
    # 发送连接成功消息
    emit('connected', {'message': '连接成功'})

@socketio.on('disconnect')
def handle_disconnect():
    """处理客户端断开连接"""
    client_id = request.sid
    if client_id in connected_clients:
        connected_clients.remove(client_id)
        print(f'客户端已断开: {client_id}')

@socketio.on('fetch_tasks')
def handle_fetch_tasks(*args):
    """处理获取任务列表请求"""
    print(f'收到 fetch_tasks 事件，参数: {args}')
    try:
        # 解析参数（args 可能包含数据）
        data = args[0] if args and isinstance(args[0], dict) else {}
        category = data.get('category')
        completed = data.get('completed')

        query = Task.query

        if category and category in TASK_CATEGORIES:
            query = query.filter_by(category=category)

        if completed is not None:
            query = query.filter_by(completed=completed)

        tasks = query.order_by(Task.created_at.desc()).all()
        tasks_data = [task.to_dict() for task in tasks]
        
        emit('tasks_data', {'tasks': tasks_data})
    except Exception as e:
        print(f'获取任务失败: {str(e)}')
        emit('error', {'code': 'FETCH_ERROR', 'message': f'获取任务失败: {str(e)}'})

@socketio.on('create_task')
def handle_create_task(*args):
    """处理创建任务请求"""
    print(f'收到 create_task 事件，参数: {args}')
    try:
        data = args[0] if args and isinstance(args[0], dict) else {}
        
        # 检查是否有嵌套的任务数据
        task_data = data.get('task', data)
        temp_id = data.get('tempId', task_data.get('tempId'))
        
        if 'content' not in task_data or not task_data['content'].strip():
            emit('error', {'code': 'VALIDATION_ERROR', 'message': '内容是必填项'})
            return

        category = task_data.get('category', '任务')
        if category not in TASK_CATEGORIES:
            emit('error', {'code': 'VALIDATION_ERROR', 'message': '无效的分类'})
            return

        new_task = Task(
            title=task_data.get('title'),
            content=task_data['content'],
            category=category,
            completed=task_data.get('completed', False)
        )

        db.session.add(new_task)
        db.session.commit()
        
        task_data = new_task.to_dict()
        # 通知所有客户端有新任务创建
        socketio.emit('sync_notification', {
            'action': 'create',
            'task': task_data
        })
        
        # 回复请求客户端
        print(f'任务创建成功: {new_task.id}, tempId: {temp_id}')
        response = {'task': task_data, 'tempId': temp_id}
        emit('task_created', response)
    except Exception as e:
        print(f'创建任务失败: {str(e)}')
        emit('error', {'code': 'CREATE_ERROR', 'message': f'创建任务失败: {str(e)}'})
        db.session.rollback()

@socketio.on('update_task')
def handle_update_task(*args):
    """处理更新任务请求"""
    print(f'收到 update_task 事件，参数: {args}')
    try:
        # args 格式: [data, requestId]
        data = args[0] if args and isinstance(args[0], dict) else {}
        request_id = args[1] if len(args) > 1 else None
        
        task_id = data.get('id')
        
        if not task_id:
            emit('error', {'code': 'VALIDATION_ERROR', 'message': '任务ID不能为空'})
            return
        
        # 如果是临时ID，跳过更新
        if task_id.startswith('temp_'):
            emit('error', {'code': 'VALIDATION_ERROR', 'message': '不能使用临时ID更新任务'})
            return
        
        task = Task.query.get(task_id)
        if not task:
            emit('error', {'code': 'NOT_FOUND', 'message': '任务不存在'})
            return
        
        # 检查是否有嵌套的任务数据
        task_data = data.get('task', data)
        
        if 'content' in task_data:
            task.content = task_data['content']
        if 'title' in task_data:
            task.title = task_data['title']
        if 'category' in task_data:
            if task_data['category'] not in TASK_CATEGORIES:
                emit('error', {'code': 'VALIDATION_ERROR', 'message': '无效的分类'})
                return
            task.category = task_data['category']
        if 'completed' in task_data:
            task.completed = task_data['completed']
            if task_data['completed']:
                task.completed_at = datetime.utcnow()
            else:
                task.completed_at = None
        
        db.session.commit()
        updated_task_data = task.to_dict()
        
        # 通知所有客户端任务已更新
        socketio.emit('sync_notification', {
            'action': 'update',
            'task': updated_task_data
        })
        
        # 回复请求客户端（包含 requestId）
        print(f'任务更新成功: {task_id}')
        response = {'task': updated_task_data}
        if request_id:
            response['requestId'] = request_id
        emit('task_updated', response)
    except Exception as e:
        print(f'更新任务失败: {str(e)}')
        emit('error', {'code': 'UPDATE_ERROR', 'message': f'更新任务失败: {str(e)}'})
        db.session.rollback()

@socketio.on('delete_task')
def handle_delete_task(*args):
    """处理删除任务请求"""
    try:
        data = args[0] if args and isinstance(args[0], dict) else {}
        task_id = data.get('id')
        if not task_id:
            emit('error', {'code': 'VALIDATION_ERROR', 'message': '任务ID不能为空'})
            return
        
        # 移除temp_前缀
        if task_id.startswith('temp_'):
            emit('error', {'code': 'VALIDATION_ERROR', 'message': '不能删除临时任务'})
            return
        
        task = Task.query.get(task_id)
        if not task:
            emit('error', {'code': 'NOT_FOUND', 'message': '任务不存在'})
            return
        
        db.session.delete(task)
        db.session.commit()
        
        # 通知所有客户端任务已删除
        socketio.emit('sync_notification', {
            'action': 'delete',
            'task': {'id': task_id}
        })
        
        # 回复请求客户端（包含 requestId）
        print(f'任务删除成功: {task_id}')
        response = {'id': task_id}
        if len(args) > 1:
            response['requestId'] = args[1]
        emit('task_deleted', response)
    except Exception as e:
        print(f'删除任务失败: {str(e)}')
        emit('error', {'code': 'DELETE_ERROR', 'message': f'删除任务失败: {str(e)}'})
        db.session.rollback()

@socketio.on('toggle_complete')
def handle_toggle_complete(*args):
    """处理切换任务完成状态请求"""
    try:
        data = args[0] if args and isinstance(args[0], dict) else {}
        task_id = data.get('id')
        completed = data.get('completed', False)
        
        if not task_id:
            emit('error', {'code': 'VALIDATION_ERROR', 'message': '任务ID不能为空'})
            return
        
        # 移除temp_前缀
        if task_id.startswith('temp_'):
            emit('error', {'code': 'VALIDATION_ERROR', 'message': '不能操作临时任务'})
            return
        
        task = Task.query.get(task_id)
        if not task:
            emit('error', {'code': 'NOT_FOUND', 'message': '任务不存在'})
            return
        
        task.completed = completed
        if completed:
            task.completed_at = datetime.utcnow()
        else:
            task.completed_at = None
        
        db.session.commit()
        task_data = task.to_dict()
        
        # 通知所有客户端任务状态已更新
        socketio.emit('sync_notification', {
            'action': 'update',
            'task': task_data
        })
        
        # 回复请求客户端
        emit('task_updated', {'task': task_data})
    except Exception as e:
        print(f'更新任务状态失败: {str(e)}')
        emit('error', {'code': 'STATUS_ERROR', 'message': f'更新任务状态失败: {str(e)}'})
        db.session.rollback()

@socketio.on('update_task_completed')
def handle_update_task_completed(*args):
    """处理更新任务完成状态请求（前端专用事件名）"""
    print(f'收到 update_task_completed 事件，参数: {args}')
    try:
        data = args[0] if args and isinstance(args[0], dict) else {}
        task_id = data.get('id')
        completed = data.get('completed', False)
        
        if not task_id:
            emit('error', {'code': 'VALIDATION_ERROR', 'message': '任务ID不能为空'})
            return
        
        # 移除temp_前缀
        if task_id.startswith('temp_'):
            emit('error', {'code': 'VALIDATION_ERROR', 'message': '不能使用临时ID更新任务状态'})
            return
        
        task = Task.query.get(task_id)
        if not task:
            emit('error', {'code': 'NOT_FOUND', 'message': '任务不存在'})
            return
        
        task.completed = completed
        if completed:
            task.completed_at = datetime.utcnow()
        else:
            task.completed_at = None
        
        db.session.commit()
        task_data = task.to_dict()
        
        # 通知所有客户端任务状态已更新
        socketio.emit('sync_notification', {
            'action': 'update',
            'task': task_data
        })
        
        # 回复请求客户端
        print(f'任务完成状态更新成功: {task_id}, completed: {completed}')
        response = {'id': task_id}
        if len(args) > 1:
            response['requestId'] = args[1]
        emit('task_completed_updated', response)
    except Exception as e:
        print(f'更新任务完成状态失败: {str(e)}')
        emit('error', {'code': 'STATUS_ERROR', 'message': f'更新任务状态失败: {str(e)}'})
        db.session.rollback()

@socketio.on('sync_tasks')
def handle_sync_tasks(*args):
    """处理批量同步任务请求"""
    try:
        data = args[0] if args and isinstance(args[0], dict) else {}
        tasks = data.get('tasks', [])
        synced_tasks = []
        errors = []
        
        for task in tasks:
            try:
                task_id = task.get('id')
                # 处理临时ID的任务（创建新任务）
                if task_id and task_id.startswith('temp_'):
                    new_task = Task(
                        title=task.get('title'),
                        content=task.get('content'),
                        category=task.get('category', '任务'),
                        completed=task.get('completed', False)
                    )
                    if new_task.completed:
                        new_task.completed_at = datetime.utcnow()
                    db.session.add(new_task)
                    db.session.commit()
                    
                    new_task_data = new_task.to_dict()
                    new_task_data['tempId'] = task_id
                    synced_tasks.append(new_task_data)
                    
                    # 通知所有客户端
                    socketio.emit('sync_notification', {
                        'action': 'create',
                        'task': new_task_data
                    })
                else:
                    # 更新已有任务
                    existing_task = Task.query.get(task_id)
                    if existing_task:
                        if 'content' in task:
                            existing_task.content = task['content']
                        if 'title' in task:
                            existing_task.title = task['title']
                        if 'category' in task:
                            existing_task.category = task['category']
                        if 'completed' in task:
                            existing_task.completed = task['completed']
                            if task['completed']:
                                existing_task.completed_at = datetime.utcnow()
                            else:
                                existing_task.completed_at = None
                        
                        db.session.commit()
                        updated_task_data = existing_task.to_dict()
                        synced_tasks.append(updated_task_data)
                        
                        # 通知所有客户端
                        socketio.emit('sync_notification', {
                            'action': 'update',
                            'task': updated_task_data
                        })
            except Exception as e:
                errors.append({'taskId': task.get('id'), 'error': str(e)})
        
        # 回复同步结果
        emit('sync_result', {
            'success': len(errors) == 0,
            'syncedTasks': synced_tasks,
            'errors': errors
        })
    except Exception as e:
        print(f'批量同步失败: {str(e)}')
        emit('error', {'code': 'SYNC_ERROR', 'message': f'批量同步失败: {str(e)}'})

@socketio.on('ping')
def handle_ping(*args):
    """处理心跳检测"""
    print('收到心跳请求')
    emit('pong')

# 广播函数，用于在任务变更时通知所有客户端
def broadcast_task_change(action, task_data):
    """广播任务变更给所有连接的客户端"""
    socketio.emit('sync_notification', {
        'action': action,
        'task': task_data
    })

# 启动应用
if __name__ == '__main__':
    # 使用socketio.run替代app.run

    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

