"""
TodoApp API 测试文件
"""

import pytest
import json
import tempfile
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Task

class TestTodoAPI:
    """TodoApp API 测试类"""
    
    def setup_method(self):
        """每个测试方法前执行"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()
        
        with app.app_context():
            db.create_all()
    
    def teardown_method(self):
        """每个测试方法后执行"""
        with app.app_context():
            db.drop_all()
    
    def test_get_tasks_empty(self):
        """测试获取空任务列表"""
        response = self.client.get('/api/tasks')
        assert response.status_code == 200
        assert json.loads(response.data) == []
    
    def test_create_task(self):
        """测试创建任务"""
        task_data = {
            'title': '测试任务',
            'content': '这是一个测试任务',
            'category': '任务'
        }
        
        response = self.client.post('/api/tasks', 
                               data=json.dumps(task_data),
                               content_type='application/json')
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['title'] == task_data['title']
        assert data['content'] == task_data['content']
        assert data['category'] == task_data['category']
        assert not data['completed']
    
    def test_create_task_validation(self):
        """测试任务创建验证"""
        # 测试空内容
        response = self.client.post('/api/tasks',
                               data=json.dumps({'title': '标题'}),
                               content_type='application/json')
        assert response.status_code == 400
        assert '内容是必填项' in response.get_json()['error']
        
        # 测试无效分类
        response = self.client.post('/api/tasks',
                               data=json.dumps({'content': '内容', 'category': '无效分类'}),
                               content_type='application/json')
        assert response.status_code == 400
        assert '无效的分类' in response.get_json()['error']
    
    def test_get_tasks_with_filter(self):
        """测试带过滤条件的任务获取"""
        # 创建测试数据
        with app.app_context():
            task1 = Task(title='任务1', content='内容1', category='任务', completed=False)
            task2 = Task(title='任务2', content='内容2', category='想尝试', completed=True)
            task3 = Task(title='任务3', content='内容3', category='任务', completed=True)
            db.session.add_all([task1, task2, task3])
            db.session.commit()
        
        # 测试按分类过滤
        response = self.client.get('/api/tasks?category=任务')
        assert response.status_code == 200
        tasks = json.loads(response.data)
        assert len(tasks) == 2
        assert all(task['category'] == '任务' for task in tasks)
        
        # 测试按完成状态过滤
        response = self.client.get('/api/tasks?completed=true')
        assert response.status_code == 200
        tasks = json.loads(response.data)
        assert len(tasks) == 2
        assert all(task['completed'] for task in tasks)
    
    def test_update_task(self):
        """测试更新任务"""
        # 先创建任务
        with app.app_context():
            task = Task(title='原标题', content='原内容', category='任务')
            db.session.add(task)
            db.session.commit()
            task_id = task.id
        
        # 更新任务
        update_data = {
            'title': '新标题',
            'content': '新内容',
            'category': '想尝试'
        }
        
        response = self.client.put(f'/api/tasks/{task_id}',
                              data=json.dumps(update_data),
                              content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['title'] == update_data['title']
        assert data['content'] == update_data['content']
        assert data['category'] == update_data['category']
    
    def test_delete_task(self):
        """测试删除任务"""
        # 先创建任务
        with app.app_context():
            task = Task(title='待删除任务', content='内容', category='任务')
            db.session.add(task)
            db.session.commit()
            task_id = task.id
        
        # 删除任务
        response = self.client.delete(f'/api/tasks/{task_id}')
        assert response.status_code == 200
        
        # 验证已删除
        response = self.client.get(f'/api/tasks/{task_id}')
        assert response.status_code == 404
    
    def test_complete_task(self):
        """测试完成任务"""
        # 先创建未完成任务
        with app.app_context():
            task = Task(title='待完成任务', content='内容', category='任务', completed=False)
            db.session.add(task)
            db.session.commit()
            task_id = task.id
        
        # 标记为完成
        response = self.client.put(f'/api/tasks/{task_id}/complete',
                              data=json.dumps({'completed': True}),
                              content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['completed'] is True
        assert data['completed_at'] is not None

if __name__ == '__main__':
    pytest.main([__file__, '-v'])