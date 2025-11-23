"""
数据库备份模块
每次启动时自动备份数据库到back文件夹
"""

import json
import os
from datetime import datetime

# 延迟导入，避免循环依赖
app = None
db = None
Task = None

def init_app(flask_app, flask_db, task_model):
    """初始化备份模块，设置应用上下文和模型"""
    global app, db, Task
    app = flask_app
    db = flask_db
    Task = task_model

def ensure_backup_dir():
    """确保备份目录存在"""
    backup_dir = os.path.join(os.getcwd(), 'back')
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    return backup_dir

def backup_database():
    """
    备份数据库到JSON文件
    文件名格式: backup_YYYYMMDD_HHMMSS.json
    
    Returns:
        str: 备份文件路径，失败返回None
    """
    try:
        # 检查是否已初始化
        if not app or not db or not Task:
            print('备份模块未初始化，请先调用init_app')
            return None
            
        with app.app_context():
            # 确保备份目录存在
            backup_dir = ensure_backup_dir()
            
            # 获取所有任务
            tasks = Task.query.all()
            
            # 转换为字典格式
            backup_data = {
                'backup_time': datetime.now().isoformat(),
                'total_tasks': len(tasks),
                'tasks': []
            }
            
            for task in tasks:
                # 检查是否有to_dict方法，没有则手动构建字典
                if hasattr(task, 'to_dict'):
                    task_dict = task.to_dict()
                else:
                    task_dict = {
                        'id': task.id,
                        'title': task.title,
                        'content': task.content,
                        'category': task.category,
                        'completed': task.completed,
                        'created_at': task.created_at.isoformat() if task.created_at else None,
                        'completed_at': task.completed_at.isoformat() if task.completed_at else None
                    }
                backup_data['tasks'].append(task_dict)
            
            # 生成备份文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f'backup_{timestamp}.json'
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # 写入JSON文件
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            print(f'数据库备份完成: {backup_path}')
            print(f'备份了 {backup_data["total_tasks"]} 个任务')
            
            # 清理旧备份（保留最新10个）
            cleanup_old_backups(backup_dir, keep_count=10)
            
            return backup_path
            
    except Exception as e:
        print(f'数据库备份失败: {e}')
        return None

def cleanup_old_backups(backup_dir, keep_count=10):
    """
    清理旧备份文件，只保留最新的keep_count个文件
    """
    try:
        # 获取所有备份文件
        backup_files = []
        for filename in os.listdir(backup_dir):
            if filename.startswith('backup_') and filename.endswith('.json'):
                filepath = os.path.join(backup_dir, filename)
                # 获取文件修改时间
                mtime = os.path.getmtime(filepath)
                backup_files.append((mtime, filepath, filename))
        
        # 按时间排序（最新的在前面）
        backup_files.sort(reverse=True)
        
        # 删除多余的备份文件
        if len(backup_files) > keep_count:
            for mtime, filepath, filename in backup_files[keep_count:]:
                os.remove(filepath)
                print(f'删除旧备份: {filename}')
                
    except Exception as e:
        print(f'清理旧备份失败: {e}')

def list_backups():
    """
    列出所有备份文件
    返回格式: [(filename, filepath, backup_time, task_count)]
    """
    try:
        backup_dir = ensure_backup_dir()
        backups = []
        
        for filename in os.listdir(backup_dir):
            if filename.startswith('backup_') and filename.endswith('.json'):
                filepath = os.path.join(backup_dir, filename)
                
                try:
                    # 读取备份文件信息
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    backup_time = data.get('backup_time', '')
                    task_count = data.get('total_tasks', 0)
                    file_size = os.path.getsize(filepath)
                    
                    backups.append((filename, filepath, backup_time, task_count, file_size))
                except Exception as e:
                    print(f'读取备份文件 {filename} 失败: {e}')
        
        # 按文件名排序（时间戳）
        backups.sort(reverse=True)
        return backups
        
    except Exception as e:
        print(f'列出备份文件失败: {e}')
        return []

def auto_backup():
    """
    自动备份函数，供应用启动时调用
    静默执行，只输出日志
    
    Returns:
        str: 备份文件路径，如果失败返回None
    """
    try:
        print("\n[自动备份] 开始备份数据库...")
        backup_file = backup_database()
        if backup_file:
            print(f"[自动备份] 备份成功: {backup_file}")
            return backup_file
        else:
            print("[自动备份] 备份失败")
            return None
    except Exception as e:
        print(f"[自动备份] 发生错误: {e}")
        return None
    finally:
        print()

if __name__ == '__main__':
    # 直接运行时需要导入app
    from app import app, db, Task
    init_app(app, db, Task)
    print("开始备份数据库...")
    backup_file = backup_database()
    if backup_file:
        print(f"备份成功: {backup_file}")
    else:
        print("备份失败")