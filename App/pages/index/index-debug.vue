<template>
	<view class="todo-app">
		<view class="header">
			<text class="page-title">待办事项（调试版）</text>
			<view class="debug-info">
				<text>平台: {{platform}}</text>
				<text>连接状态: {{connectionStatus}}</text>
			</view>
		</view>
		
		<view class="task-list">
			<view class="task-item">
				<text>调试模式 - 简化版本</text>
				<text>点击按钮测试功能</text>
			</view>
			
			<view class="test-buttons">
				<button @click="testLocalStorage" class="test-btn">测试本地存储</button>
				<button @click="testWebSocket" class="test-btn">测试WebSocket</button>
				<button @click="testSimpleTask" class="test-btn">添加简单任务</button>
			</view>
		</view>
	</view>
</template>

<script>
// 导入WebSocket管理器（简化版）
// import websocketManager from '@/utils/websocketManager';

export default {
	data() {
		return {
			platform: '',
			connectionStatus: 'disconnected',
			tasks: []
		}
	},
	onLoad() {
		// 获取平台信息
		// #ifdef H5
		this.platform = 'H5';
		// #endif
		// #ifdef APP-PLUS
		this.platform = 'APP';
		// #endif
		// #ifdef MP-WEIXIN
		this.platform = '微信小程序';
		// #endif
		
		console.log('当前平台:', this.platform);
	},
	methods: {
		testLocalStorage() {
			try {
				const testData = {
					id: Date.now(),
					title: '测试任务',
					content: '这是一个测试任务',
					category: '任务',
					completed: false,
					created_at: new Date().toISOString()
				};
				
				uni.setStorageSync('debug_task', testData);
				console.log('本地存储测试成功');
				uni.showToast({
					title: '本地存储测试成功',
					icon: 'success'
				});
			} catch (e) {
				console.error('本地存储测试失败:', e);
				uni.showToast({
					title: '本地存储失败',
					icon: 'error'
				});
			}
		},
		
		testWebSocket() {
			try {
				console.log('测试WebSocket连接...');
				
				// 简化的WebSocket测试
				uni.connectSocket({
					url: 'ws://192.168.1.7:5000',
					success: () => {
						console.log('WebSocket连接成功');
						this.connectionStatus = 'connected';
						uni.showToast({
							title: 'WebSocket连接成功',
							icon: 'success'
						});
					},
					fail: (err) => {
						console.error('WebSocket连接失败:', err);
						this.connectionStatus = 'error';
						uni.showToast({
							title: 'WebSocket连接失败',
							icon: 'error'
						});
					}
				});
				
				// 监听消息
				uni.onSocketMessage((res) => {
					console.log('收到WebSocket消息:', res);
					try {
						const data = JSON.parse(res.data);
						console.log('解析后的数据:', data);
					} catch (e) {
						console.error('解析消息失败:', e);
					}
				});
				
			} catch (e) {
				console.error('WebSocket测试失败:', e);
				uni.showToast({
					title: 'WebSocket测试失败',
					icon: 'error'
				});
			}
		},
		
		testSimpleTask() {
			try {
				const newTask = {
					id: 'test_' + Date.now(),
					title: '简单测试任务',
					content: '这是通过按钮添加的测试任务',
					category: '任务',
					completed: false,
					created_at: new Date().toISOString()
				};
				
				this.tasks.push(newTask);
				console.log('添加测试任务:', newTask);
				
				uni.showToast({
					title: '添加测试任务成功',
					icon: 'success'
				});
			} catch (e) {
				console.error('添加测试任务失败:', e);
				uni.showToast({
					title: '添加测试任务失败',
					icon: 'error'
				});
			}
		}
	}
}
</script>

<style>
.todo-app {
	padding: 20rpx;
	min-height: 100vh;
	background-color: #f8f8f8;
}

.header {
	padding: 30rpx 0;
	text-align: center;
	margin-bottom: 20rpx;
}

.page-title {
	font-size: 44rpx;
	font-weight: bold;
	color: #333;
	margin-bottom: 20rpx;
}

.debug-info {
	display: flex;
	justify-content: space-around;
	margin-bottom: 20rpx;
}

.debug-info text {
	font-size: 28rpx;
	color: #666;
}

.task-list {
	background-color: #fff;
	border-radius: 12rpx;
	padding: 20rpx;
}

.task-item {
	padding: 20rpx;
	border-bottom: 1rpx solid #f0f0f0;
	text-align: center;
}

.test-buttons {
	display: flex;
	flex-direction: column;
	gap: 20rpx;
	margin-top: 30rpx;
}

.test-btn {
	background-color: #007aff;
	color: #fff;
	border: none;
	border-radius: 8rpx;
	padding: 20rpx;
	font-size: 32rpx;
}
</style>