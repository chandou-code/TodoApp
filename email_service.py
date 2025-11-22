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
    'username': '1071718696@qq.com',
    'password': 'czxzcmubbpelbcgh',
    'sender': '1071718696@qq.com',
    'recipient': '1071718696@qq.com'
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
            
        # 每天24点（午夜）执行
        self.scheduler.add_job(
            func=self._send_daily_email,
            trigger="cron",
            hour=0,
            minute=0,
            id='daily_todo_email',
            replace_existing=True,
            coalesce=True,  # 如果任务积压，只执行一次
            max_instances=1  # 最多只有一个实例运行
        )
        
        self.scheduler.start()
        print("定时任务已启动: 每天午夜24点发送待办事项邮件")
        
    def check_today_email_sent(self):
        """检查今天是否已经发送过邮件"""
        if not self.db or not self.email_log_model:
            return False
            
        with current_app.app_context():
            # 获取今天的开始时间（UTC时间）
            today = datetime.utcnow().date()
            start_of_day = datetime.combine(today, datetime.min.time())

            # 查询今天是否有成功发送的邮件记录
            today_logs = self.email_log_model.query.filter(
                self.email_log_model.sent_at >= start_of_day,
                self.email_log_model.status == True
            ).first()

            return today_logs is not None
            
    def init_daily_check(self):
        """应用启动时的每日检查（只在需要时发送）"""
        if not current_app.config.get('MAIL_NOTIFICATION_ENABLED', True):
            print("邮件通知功能已禁用，跳过发送")
            return
            
        # 添加额外的检查：如果是应用重启且短时间内已发送过邮件，则跳过
        if self._should_skip_email():
            print("检测到短时间内已发送过邮件，跳过本次发送")
            return
        
        # 检查最近失败记录，避免频繁重试网络错误
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
            # 检查最近30分钟内是否有失败的发送记录
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
        """检查是否应该跳过邮件发送（防止频繁重启导致的重复发送）"""
        if not self.db or not self.email_log_model:
            return False
            
        try:
            # 检查最近5分钟内是否已发送过邮件
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
            # 测试DNS解析
            socket.gethostbyname(EMAIL_CONFIG['smtp_server'])
            # 测试TCP连接
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['port']))
            sock.close()
            return result == 0
        except Exception as e:
            print(f"网络连接测试失败: {e}")
            return False
            
    def _send_daily_email(self):
        """发送每日待办邮件（内部方法）"""
        if not self.db or not self.task_model:
            print("数据库模型未初始化，无法发送邮件")
            return
            
        # 先测试网络连接
        if not self._test_network_connection():
            print("网络连接测试失败，跳过邮件发送")
            # 记录网络失败
            with current_app.app_context():
                if self.email_log_model:
                    email_log = self.email_log_model(
                        sent_at=datetime.utcnow(),
                        task_count=0,
                        status=False
                    )
                    self.db.session.add(email_log)
                    self.db.session.commit()
            return
            
        with current_app.app_context():
            try:
                # 获取所有未完成的任务
                tasks = self.task_model.query.filter_by(completed=False).all()

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

                # 发送邮件 - 添加连接超时和重试机制
                try:
                    server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['port'], timeout=10)
                    server.starttls()
                    server.login(EMAIL_CONFIG['username'], EMAIL_CONFIG['password'])
                    server.send_message(msg)
                    server.quit()
                    print(f"邮件发送成功: {datetime.now()}")
                except Exception as smtp_error:
                    print(f"SMTP连接错误，尝试备用方案: {smtp_error}")
                    # 备用方案：使用IP地址（需要先获取SMTP服务器IP）
                    try:
                        # 如果DNS解析失败，可以尝试使用已知IP
                        # qq.com的SMTP服务器备用IP（可能需要更新）
                        backup_server = "smtp.qq.com"
                        server = smtplib.SMTP(backup_server, EMAIL_CONFIG['port'], timeout=15)
                        server.starttls()
                        server.login(EMAIL_CONFIG['username'], EMAIL_CONFIG['password'])
                        server.send_message(msg)
                        server.quit()
                        print(f"邮件发送成功（备用方案）: {datetime.now()}")
                    except Exception as backup_error:
                        raise backup_error  # 如果备用方案也失败，抛出原错误

                # 记录发送历史
                if self.email_log_model:
                    email_log = self.email_log_model(
                        sent_at=datetime.utcnow(),
                        task_count=len(tasks),
                        status=True
                    )
                    self.db.session.add(email_log)
                    self.db.session.commit()
                    
            except smtplib.SMTPRecipientsRefused as e:
                print(f"邮件发送失败 - 收件人被拒绝: {e}")
                # 记录失败状态
                if self.email_log_model:
                    email_log = self.email_log_model(
                        sent_at=datetime.utcnow(),
                        task_count=len(tasks) if 'tasks' in locals() else 0,
                        status=False
                    )
                    self.db.session.add(email_log)
                    self.db.session.commit()
                    
            except smtplib.SMTPAuthenticationError as e:
                print(f"邮件发送失败 - 认证错误: {e}")
                # 记录失败状态
                if self.email_log_model:
                    email_log = self.email_log_model(
                        sent_at=datetime.utcnow(),
                        task_count=len(tasks) if 'tasks' in locals() else 0,
                        status=False
                    )
                    self.db.session.add(email_log)
                    self.db.session.commit()
                    
            except smtplib.SMTPException as e:
                print(f"邮件发送失败 - SMTP错误: {e}")
                # 记录失败状态
                if self.email_log_model:
                    email_log = self.email_log_model(
                        sent_at=datetime.utcnow(),
                        task_count=len(tasks) if 'tasks' in locals() else 0,
                        status=False
                    )
                    self.db.session.add(email_log)
                    self.db.session.commit()
                    
            except Exception as e:
                print(f"邮件发送失败 - 未知错误: {e}")
                # 记录失败状态
                if self.email_log_model:
                    email_log = self.email_log_model(
                        sent_at=datetime.utcnow(),
                        task_count=len(tasks) if 'tasks' in locals() else 0,
                        status=False
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