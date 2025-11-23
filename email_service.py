"""
邮件服务模块
负责处理待办事项邮件提醒功能
"""

import smtplib
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from flask_sqlalchemy import SQLAlchemy
from flask import current_app


# 任务分类枚举
TASK_CATEGORIES = ['任务', '想尝试', '提醒']

# 邮件配置
EMAIL_CONFIG = {
    'smtp_server': 'smtp.qq.com',
    'port': 587,
    'username': 'xxxxxx@qq.com',
    'password': 'xxxxxx',
    'sender': 'xxxxxx@qq.com',
    'recipient': 'xxxxxx@qq.com'
}


class EmailService:
    """邮件服务类"""

    def __init__(self, db=None, task_model=None):
        self.db = db
        self.task_model = task_model
        self.scheduler = None

    def init_app(self, app, db, task_model, email_log_model):
        """初始化邮件服务"""
        self.db = db
        self.task_model = task_model
        self.email_log_model = email_log_model

        # 创建定时任务调度器
        self.scheduler = BackgroundScheduler(timezone='Asia/Shanghai')

        # 配置应用设置
        app.config['MAIL_NOTIFICATION_ENABLED'] = True

        # 启动调度器
        self._setup_scheduler()

    def _setup_scheduler(self):
        """设置定时任务"""
        if not self.scheduler:
            return

        self.scheduler.add_job(
            func=self._send_daily_email,
            trigger="cron",
            hour=0,
            minute=0,
            id='daily_todo_email'
        )

        self.scheduler.start()
        print("定时任务已启动: 每天午夜24点发送待办事项邮件")

    def check_today_email_sent(self):
        """检查今天是否已经发送过邮件"""
        if not self.db or not self.email_log_model:
            return False

        with current_app.app_context():
            today = datetime.utcnow().date()
            start_of_day = datetime.combine(today, datetime.min.time())

            today_logs = self.email_log_model.query.filter(
                self.email_log_model.sent_at >= start_of_day,
                self.email_log_model.status == True
            ).first()

            return today_logs is not None

    def init_daily_check(self):
        """应用启动时的每日检查"""
        if not current_app.config.get('MAIL_NOTIFICATION_ENABLED', True):
            print("邮件通知功能已禁用，跳过发送")
            return

        if self._should_skip_email():
            print("检测到短时间内已发送过邮件，跳过本次发送")
            return

        if self._should_skip_due_to_network_error():
            print("检测到最近网络错误，暂时跳过邮件发送")
            return

        if self.check_today_email_sent():
            print("今日邮件已发送，无需重复发送")
        else:
            print("今日邮件未发送，正在立即发送...")
            self._send_daily_email()

    def _should_skip_due_to_network_error(self):
        """检查是否应因网络错误跳过邮件发送"""
        if not self.db or not self.email_log_model:
            return False

        try:
            thirty_minutes_ago = datetime.utcnow() - timedelta(minutes=30)
            recent_failure = self.email_log_model.query.filter(
                self.email_log_model.sent_at >= thirty_minutes_ago,
                self.email_log_model.status == False
            ).first()
            return recent_failure is not None
        except Exception as e:
            print(f"检查网络错误状态时出错: {e}")
            return False

    def _should_skip_email(self):
        """检查是否应该跳过邮件发送"""
        if not self.db or not self.email_log_model:
            return False

        try:
            five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
            recent_log = self.email_log_model.query.filter(
                self.email_log_model.sent_at >= five_minutes_ago,
                self.email_log_model.status == True
            ).first()
            return recent_log is not None
        except Exception as e:
            print(f"检查邮件发送状态时出错: {e}")
            return False

    def _test_network_connection(self):
        """测试网络连接"""
        try:
            socket.gethostbyname(EMAIL_CONFIG['smtp_server'])
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['port']))
            sock.close()
            return result == 0
        except Exception as e:
            print(f"网络连接测试失败: {e}")
            return False

    def _build_email_content(self, tasks):
        """构建邮件内容"""
        if not tasks:
            return "<p>目前没有待办任务，继续保持！</p>"

        content = f"<h2>待办事项清单 - {datetime.now().strftime('%Y-%m-%d')}</h2>"
        content += f"<p>待办任务总数：<strong>{len(tasks)}</strong></p>"

        for category in TASK_CATEGORIES:
            category_tasks = [task for task in tasks if task.category == category]
            if not category_tasks:
                continue

            content += f"<h3>{category} ({len(category_tasks)})</h3><ul>"

            for index, task in enumerate(category_tasks, 1):
                task_title = task.title or " "
                task_content = task.content or "无详细内容"

                title_part = f"{index}. {task_title}" if task_title else f"{index}."
                content += f"<li><strong>{title_part}</strong><br>{task_content}</li>"

            content += "</ul>"

        return content

    def _send_daily_email(self):
        """发送每日待办邮件"""
        if not self.db or not self.task_model:
            print("数据库模型未初始化，无法发送邮件")
            return

        if not self._test_network_connection():
            print("网络连接测试失败，跳过邮件发送")
            self._log_email_status(False, 0)
            return

        with current_app.app_context():
            try:
                tasks = self.task_model.query.filter_by(completed=False).all()
                email_content = self._build_email_content(tasks)

                # 创建邮件
                msg = MIMEMultipart()
                msg['From'] = EMAIL_CONFIG['sender']
                msg['To'] = EMAIL_CONFIG['recipient']
                msg['Subject'] = f"待办事项提醒 - {datetime.now().strftime('%Y-%m-%d')}"
                msg.attach(MIMEText(email_content, 'html'))

                # 发送邮件
                server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['port'], timeout=10)
                server.starttls()
                server.login(EMAIL_CONFIG['username'], EMAIL_CONFIG['password'])
                server.send_message(msg)
                server.quit()

                print(f"邮件发送成功: {datetime.now()}")
                self._log_email_status(True, len(tasks))

            except Exception as e:
                print(f"邮件发送失败: {e}")
                self._log_email_status(False, len(tasks) if 'tasks' in locals() else 0)

    def _log_email_status(self, status, task_count):
        """记录邮件发送状态"""
        if not self.email_log_model:
            return

        email_log = self.email_log_model(
            sent_at=datetime.utcnow(),
            task_count=task_count,
            status=status
        )
        self.db.session.add(email_log)
        self.db.session.commit()

    def send_test_email(self):
        """手动发送测试邮件"""
        if not current_app.config.get('MAIL_NOTIFICATION_ENABLED', True):
            raise Exception('邮件通知功能已禁用')

        self._send_daily_email()
        return '测试邮件已发送'

    def stop(self):
        """停止邮件服务"""
        if self.scheduler:
            self.scheduler.shutdown()
            print("邮件服务已停止")

