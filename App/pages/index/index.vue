<template>
	<view class="todo-app">
	<!-- 页面标题 -->
	<view class="header">
		<text class="page-title">待办事项</text>
		<view class="sync-status" :class="syncStatus">
			<text v-if="syncStatus === 'synced'" class="status-icon">✓</text>
			<text v-else-if="syncStatus === 'syncing'" class="status-icon">⟳</text>
			<text v-else class="status-icon">⚠</text>
			<text class="status-text">
				{{ syncStatus === 'synced' ? '已同步' : syncStatus === 'syncing' ? '同步中' : '未同步' }}
			</text>
		</view>
	</view>
		
		<!-- 分类标签栏 -->
		<view class="category-tabs">
			<view 
				v-for="category in categories" 
				:key="category"
				:class="['tab', { active: currentCategory === category }]"
				@click="switchCategory(category)"
			>
				{{ category }}
			</view>
		</view>
		
		<!-- 任务列表 -->
		<view class="task-list">
			<!-- 未完成任务 -->
			<view class="task-section">
				<view class="task-item" v-for="task in filteredTasks.filter(t => !t.completed)" :key="task.id">
					<view class="task-content" @click="editTask(task)">
						<text class="task-title" v-if="task.title">{{ task.title }}</text>
						<text class="task-text">{{ task.content }}</text>
					</view>
					<view class="task-actions">
						<view class="icon-btn check-btn" @click.stop="toggleComplete(task)">✓</view>
						<view class="icon-btn edit-btn" @click.stop="editTask(task)">✏️</view>
						<view class="icon-btn delete-btn" @click.stop="deleteTask(task.id)">🗑️</view>
					</view>
				</view>
			</view>
			
			<!-- 已完成任务区域 -->
			<view class="completed-section">
				<view class="completed-header" @click="toggleCompleted">
					<text class="completed-text">
						已完成 ({{ filteredTasks.filter(t => t.completed).length }})
					</text>
					<view class="arrow-icon">
						{{ showCompleted ? '↑' : '↓' }}
					</view>
				</view>
				
				<!-- 已完成任务列表 -->
				<view class="completed-tasks" v-if="showCompleted">
					<view class="task-item completed" v-for="task in filteredTasks.filter(t => t.completed)" :key="task.id">
						<view class="task-content" @click="editTask(task)">
							<text class="task-title" v-if="task.title">{{ task.title }}</text>
							<text class="task-text">{{ task.content }}</text>
						</view>
						<view class="task-actions">
							<view class="icon-btn check-btn checked" @click.stop="toggleComplete(task)">✓</view>
							<view class="icon-btn edit-btn" @click.stop="editTask(task)">✏️</view>
							<view class="icon-btn delete-btn" @click.stop="deleteTask(task.id)">🗑️</view>
						</view>
					</view>
				</view>
			</view>
			
			<!-- 空状态 -->
			<view class="empty-state" v-if="filteredTasks.length === 0">
			<view class="empty-icon">📝</view>
			<text class="empty-text">暂无任务</text>
			<text class="empty-hint">点击右下角按钮添加任务</text>
		</view>
		</view>
		
		<!-- 添加任务按钮 -->
		<view class="add-btn" @click="openAddTask">
			+</view>
		
		<!-- 添加/编辑任务弹窗 -->
		<view class="popup-mask" v-if="showTaskDialog" @click="closeTaskDialog"></view>
		<view class="popup" v-if="showTaskDialog">
			<view class="popup-content">
				<view class="popup-header">
					<text class="popup-title">{{ editingTask ? '编辑任务' : '添加' + currentCategory }}</text>
					<view class="close-btn" @click="closeTaskDialog">✕</view>
				</view>
				<view class="popup-body">
					<input 
						v-model="currentTask.title" 
						placeholder="请输入标题（选填）"
						class="input-item"
						type="text"
					/>
					<textarea 
						v-model="currentTask.content" 
						placeholder="请输入内容（必填）"
						maxlength="200"
						rows="4"
						class="input-item textarea"
					/>
					<view class="btn-group">
						<button class="cancel-btn" @click="closeTaskDialog">取消</button>
						<button class="confirm-btn" @click="saveTask">{{ editingTask ? '更新' : '确定' }}</button>
					</view>
				</view>
			</view>
		</view>
	</view>
</template>

<script>
// 导入WebSocket管理器
import websocketManager from '@/utils/websocketManager';

export default {
		data() {
				return {
					categories: ['任务', '想尝试', '提醒'],
					currentCategory: '任务',
					tasks: [],
					localTasks: [],
					showCompleted: false,
					showTaskDialog: false,
					editingTask: false,
					syncStatus: 'synced', // synced, syncing, unsynced
					currentTask: {
						id: null,
						title: '',
						content: '',
						category: '任务'
					},
					// WebSocket相关状态
					wsConnected: false,
					// 请求ID映射，用于处理响应
					pendingRequests: {}
				}
			},
		computed: {
			filteredTasks() {
				return this.tasks.filter(task => task.category === this.currentCategory);
			}
		},
		onLoad() {
			// 先从本地存储加载任务
			this.loadLocalTasks();
			
			// 初始化WebSocket连接
			this.initWebSocket();
			
			// 页面显示时也重新加载任务
		},
		onShow() {
			// 如果WebSocket已连接，获取最新任务
			if (this.wsConnected) {
				this.fetchTasks();
			}
			// 页面显示时启动自动同步检查
			this.startAutoSyncCheck();
		},
		
		// 页面隐藏时清理定时器
		onHide() {
			this.stopAutoSyncCheck();
		},
		
		// 页面卸载时清理所有资源
		onUnload() {
			this.stopAutoSyncCheck();
			// 页面卸载时清理WebSocket连接
			websocketManager.close();
		},
		methods: {
			// 初始化WebSocket连接
			initWebSocket() {
				// 在H5环境下，直接连接到Flask服务器的Socket.IO端点
				// 使用 Socket.IO 客户端格式
				const hostname = window.location.hostname;
				const wsUrl = `http://${hostname}:5000`;
				
				console.log('尝试连接Socket.IO服务器:', wsUrl);
				
				// 初始化WebSocket连接
				websocketManager.init(wsUrl);
				
				// 添加事件监听器
				websocketManager.on('connected', this.handleWsConnected);
				websocketManager.on('disconnected', this.handleWsDisconnected);
				websocketManager.on('tasks_data', this.handleTasksData);
				websocketManager.on('task_created', this.handleTaskCreated);
				websocketManager.on('task_updated', this.handleTaskUpdated);
				websocketManager.on('task_deleted', this.handleTaskDeleted);
				websocketManager.on('task_completed_updated', this.handleTaskCompletedUpdated);
				websocketManager.on('sync_completed', this.handleSyncCompleted);
				websocketManager.on('error', this.handleWsError);
			},
			
			// 处理WebSocket连接成功
			handleWsConnected() {
				console.log('WebSocket连接成功');
				this.wsConnected = true;
				this.syncStatus = 'syncing';
				
				// 连接成功后立即获取最新任务
				this.fetchTasks();
			},
			
			// 处理WebSocket连接断开
			handleWsDisconnected() {
				console.log('WebSocket连接断开');
				this.wsConnected = false;
				this.syncStatus = 'unsynced';
			},
			
			// 处理任务数据更新
			handleTasksData(data) {
				try {
					// 处理服务器返回的数据，合并本地未同步的任务
					const serverTasks = Array.isArray(data.tasks) ? data.tasks : [];
					const localUnsyncedTasks = this.tasks.filter(task => task.needsSync);
					
					// 合并策略：本地未同步的任务优先级高于服务器任务
					// 1. 创建服务器任务ID映射
					const serverTaskMap = {};
					serverTasks.forEach(task => {
						// 确保task.id是字符串类型
						const taskId = String(task.id);
						if (!taskId.startsWith('temp_')) {
							serverTaskMap[taskId] = task;
						}
					});
					
					// 2. 合并任务，保留本地未同步的任务
					const mergedTasks = [...localUnsyncedTasks];
					
					// 3. 添加服务器任务，但如果本地有同名ID且未同步的任务则跳过
					serverTasks.forEach(task => {
						// 确保task.id是字符串类型
						const taskId = String(task.id);
						if (!mergedTasks.some(t => String(t.id) === taskId)) {
							mergedTasks.push({
								...task,
								id: taskId, // 确保ID是字符串
								needsSync: false // 服务器任务默认已同步
							});
						}
					});
					
					this.tasks = mergedTasks;
					this.saveLocalTasks(); // 保存合并后的数据到本地
					this.syncStatus = 'synced';
					
					// 尝试同步未同步的任务
					this.syncUnsyncedTasks();
				} catch (error) {
					console.error('处理任务数据失败:', error);
					this.syncStatus = 'unsynced';
				} finally {
					uni.hideLoading();
				}
			},
			
			// 处理任务创建响应
			handleTaskCreated(data) {
				try {
					const { requestId, task } = data;
					if (requestId && this.pendingRequests[requestId]) {
						const tempId = this.pendingRequests[requestId];
						// 更新本地任务的ID和同步状态
						const index = this.tasks.findIndex(t => String(t.id) === tempId);
						if (index !== -1) {
							this.tasks[index] = {
								...this.tasks[index],
								id: String(task.id),
								needsSync: false
							};
							this.saveLocalTasks();
							console.log(`任务创建成功，临时ID: ${tempId} -> 服务器ID: ${task.id}`);
						}
						// 移除挂起的请求
						delete this.pendingRequests[requestId];
					}
					// 检查是否所有任务都已同步
					if (!this.tasks.some(t => t.needsSync)) {
						this.syncStatus = 'synced';
					}
				} catch (error) {
					console.error('处理任务创建响应失败:', error);
				}
			},
			
			// 处理任务更新响应
			handleTaskUpdated(data) {
				try {
					const { requestId } = data;
					if (requestId && this.pendingRequests[requestId]) {
						const taskId = this.pendingRequests[requestId];
						// 更新本地任务的同步状态
						const index = this.tasks.findIndex(t => String(t.id) === taskId);
						if (index !== -1) {
							this.tasks[index].needsSync = false;
							this.saveLocalTasks();
							console.log(`任务更新成功: ${taskId}`);
						}
						// 移除挂起的请求
						delete this.pendingRequests[requestId];
					}
					// 检查是否所有任务都已同步
					if (!this.tasks.some(t => t.needsSync)) {
						this.syncStatus = 'synced';
					}
				} catch (error) {
					console.error('处理任务更新响应失败:', error);
				}
			},
			
			// 处理任务删除响应
			handleTaskDeleted(data) {
				try {
					const { requestId } = data;
					if (requestId && this.pendingRequests[requestId]) {
						// 删除操作已在服务器端完成，本地已删除，无需额外操作
						delete this.pendingRequests[requestId];
						console.log('任务删除成功');
					}
					// 检查是否所有任务都已同步
					if (!this.tasks.some(t => t.needsSync)) {
						this.syncStatus = 'synced';
					}
				} catch (error) {
					console.error('处理任务删除响应失败:', error);
				}
			},
			
			// 处理任务完成状态更新响应
			handleTaskCompletedUpdated(data) {
				try {
					const { requestId } = data;
					if (requestId && this.pendingRequests[requestId]) {
						const taskId = this.pendingRequests[requestId];
						// 更新本地任务的同步状态
						const index = this.tasks.findIndex(t => String(t.id) === taskId);
						if (index !== -1) {
							this.tasks[index].needsSync = false;
							this.saveLocalTasks();
							console.log(`任务完成状态更新成功: ${taskId}`);
						}
						// 移除挂起的请求
						delete this.pendingRequests[requestId];
					}
					// 检查是否所有任务都已同步
					if (!this.tasks.some(t => t.needsSync)) {
						this.syncStatus = 'synced';
					}
				} catch (error) {
					console.error('处理任务完成状态更新响应失败:', error);
				}
			},
			
			// 处理批量同步完成
			handleSyncCompleted(data) {
				console.log('批量同步完成');
				this.syncStatus = 'synced';
				this.saveLocalTasks();
			},
			
			// 处理WebSocket错误
			handleWsError(error) {
				console.error('WebSocket错误:', error);
				this.syncStatus = 'unsynced';
			},
			
			// 生成请求ID
			generateRequestId() {
				return 'req_' + Date.now() + '_' + Math.floor(Math.random() * 1000);
			},
			
			// 从本地存储加载任务 - 增强的持久化实现
			loadLocalTasks() {
				try {
					// 使用新的存储键名，包含版本信息
					const STORAGE_KEY = 'todo_app_tasks_v1';
					const localDataStr = uni.getStorageSync(STORAGE_KEY);
					
					if (localDataStr) {
						try {
							// 尝试解压缩数据（如果支持）
							let localData;
							try {
								// 尝试正常解析
								localData = JSON.parse(localDataStr);
							} catch (e) {
								// 如果解析失败，可能是压缩的数据，尝试恢复（这里可以后续实现压缩逻辑）
								localData = JSON.parse(localDataStr);
							}
							
							// 数据版本兼容性检查
							if (localData.version && localData.version >= 1) {
								// 验证数据结构
								if (Array.isArray(localData.tasks)) {
									this.localTasks = localData.tasks;
									this.tasks = [...this.localTasks];
									console.log('成功从本地存储加载了', this.tasks.length, '个任务');
									
									// 更新最后加载时间
									this.lastLoadTime = localData.lastSyncTime || Date.now();
									
									// 检查是否有需要同步的任务
									const hasUnsyncedTasks = this.tasks.some(task => task.needsSync);
									if (hasUnsyncedTasks) {
										this.syncStatus = 'unsynced';
									}
								} else {
									console.error('本地任务数据格式错误，应为数组');
									this.tasks = [];
									// 尝试从旧格式恢复
									this._attemptDataRecovery(localDataStr);
								}
							} else {
								// 旧版本数据，需要升级
								console.log('检测到旧版本数据，需要升级');
								this._upgradeData(localData);
							}
						} catch (parseError) {
							console.error('解析本地任务数据失败:', parseError);
							// 尝试数据恢复
							this._attemptDataRecovery(localDataStr);
							// 如果恢复失败，创建备份并清空损坏的数据
							if (this.tasks.length === 0) {
								this._backupCorruptedData(localDataStr);
								uni.removeStorageSync(STORAGE_KEY);
							}
						}
					} else {
						console.log('本地存储中没有任务数据');
						// 尝试从旧版本存储键恢复
						this._migrateFromOldStorage();
					}
				} catch (e) {
					console.error('加载本地任务失败:', e);
					// 出错时确保有默认的空任务列表
					this.tasks = [];
				}
			},
			
			// 尝试数据恢复
			_attemptDataRecovery(corruptedData) {
				try {
					console.log('尝试恢复损坏的数据...');
					// 简单的数据清理尝试
					const cleanedData = corruptedData.trim();
					// 尝试移除可能的无效字符
					const fixedData = cleanedData.replace(/([^{]*)\{/g, '{').replace(/\}([^}]*)\}$/g, '}');
					const parsedData = JSON.parse(fixedData);
					if (Array.isArray(parsedData)) {
						this.tasks = parsedData;
						this.localTasks = parsedData;
						console.log('数据恢复成功，加载了', parsedData.length, '个任务');
					} else if (parsedData && Array.isArray(parsedData.tasks)) {
						this.tasks = parsedData.tasks;
						this.localTasks = parsedData.tasks;
						console.log('数据恢复成功，加载了', parsedData.tasks.length, '个任务');
					}
				} catch (e) {
					console.error('数据恢复失败:', e);
				}
			},
			
			// 备份损坏的数据
			_backupCorruptedData(corruptedData) {
				try {
					const backupKey = `todo_app_corrupted_${Date.now()}`;
					// 只备份合理大小的数据
					if (corruptedData.length < 100000) { // 100KB 限制
						uni.setStorageSync(backupKey, corruptedData);
						console.log('损坏的数据已备份到:', backupKey);
					}
				} catch (e) {
					console.error('备份损坏数据失败:', e);
				}
			},
			
			// 数据版本升级
			_upgradeData(oldData) {
				try {
					console.log('执行数据版本升级...');
					// 如果是旧格式的直接任务数组
					if (Array.isArray(oldData)) {
						// 转换为新格式并添加必要字段
						this.localTasks = oldData.map(task => ({
							id: String(task.id || this.generateTempId()),
							title: task.title || '',
							content: task.content || '',
							category: task.category || '任务',
							completed: !!task.completed,
							needsSync: !!task.needsSync,
							createdAt: task.createdAt || new Date().toISOString()
						}));
					} else if (oldData && typeof oldData === 'object') {
						// 处理其他可能的旧格式
						this.localTasks = oldData.tasks || [];
					}
					this.tasks = [...this.localTasks];
					this.saveLocalTasks(); // 以新格式保存
					console.log('数据版本升级成功');
				} catch (e) {
					console.error('数据版本升级失败:', e);
				}
			},
			
			// 从旧版本存储键迁移
			_migrateFromOldStorage() {
				try {
					const oldKey = 'todo_local_tasks';
					const oldData = uni.getStorageSync(oldKey);
					if (oldData) {
						console.log('检测到旧存储格式，开始迁移...');
						// 尝试解析并迁移旧数据
						const parsedOldData = JSON.parse(oldData);
						if (Array.isArray(parsedOldData)) {
							this.localTasks = parsedOldData;
							this.tasks = [...this.localTasks];
							this.saveLocalTasks(); // 以新格式保存
							// 迁移成功后删除旧数据
							uni.removeStorageSync(oldKey);
							console.log('数据迁移成功，旧数据已清理');
						}
					}
				} catch (e) {
					console.error('数据迁移失败:', e);
				}
			},
			// 保存任务到本地存储 - 增强的持久化实现
			saveLocalTasks() {
				try {
					// 使用新的存储键名，包含版本信息
					const STORAGE_KEY = 'todo_app_tasks_v1';
					const MAX_STORAGE_SIZE = 500000; // 500KB 限制
					const MAX_TASKS_LIMIT = 1000; // 最大任务数量限制
					
					// 确保任务数据有效
					if (!Array.isArray(this.tasks)) {
						console.error('任务数据不是有效的数组');
						return;
					}
					
					// 任务数量限制检查
					let tasksToSave = [...this.tasks];
					if (tasksToSave.length > MAX_TASKS_LIMIT) {
						console.warn(`任务数量超过限制(${MAX_TASKS_LIMIT})，保留最近的任务`);
						// 按创建时间排序，保留最近的任务
						tasksToSave = tasksToSave
							.sort((a, b) => {
								const dateA = new Date(a.createdAt || 0).getTime();
								const dateB = new Date(b.createdAt || 0).getTime();
								return dateB - dateA;
							})
							.slice(0, MAX_TASKS_LIMIT);
					}
					
					// 清理无效任务，确保每个任务都有必要的字段
					const validTasks = tasksToSave.filter(task => 
						task && typeof task === 'object' && (task.content || task.title)
					).map(task => ({
						id: String(task.id || this.generateTempId()),
						title: task.title || '',
						content: task.content || '',
						category: task.category || '任务',
						completed: !!task.completed,
						needsSync: !!task.needsSync,
						createdAt: task.createdAt || new Date().toISOString(),
						updatedAt: new Date().toISOString()
					}));
					
					this.localTasks = [...validTasks];
					
					// 构建完整的存储对象，包含版本和元数据
					const storageData = {
						version: 1,
						tasks: this.localTasks,
						lastSyncTime: Date.now(),
						lastSaveTime: Date.now(),
						taskCount: this.localTasks.length
					};
					
					// 序列化数据
					const jsonData = JSON.stringify(storageData);
					
					// 存储大小检查
					if (jsonData.length > MAX_STORAGE_SIZE) {
						console.warn('存储数据过大，尝试压缩...');
						// 尝试精简数据
						const reducedData = this._reduceStorageData(storageData, MAX_STORAGE_SIZE);
						if (reducedData) {
							this._saveToStorage(STORAGE_KEY, reducedData);
						} else {
							console.error('无法将数据压缩到存储限制内');
							// 尝试紧急模式，只保留必要数据
							this._emergencySave(STORAGE_KEY);
						}
					} else {
						// 正常保存
						this._saveToStorage(STORAGE_KEY, jsonData);
					}
					
					// 更新同步状态
					if (this.syncStatus === 'synced') {
						this.syncStatus = 'unsynced';
					}
				} catch (e) {
					console.error('保存本地任务失败:', e);
					// 尝试紧急保存
					try {
						this._emergencySave('todo_app_tasks_v1');
					} catch (emergencyError) {
						console.error('紧急保存也失败了:', emergencyError);
					}
				}
			},
			
			// 保存到存储
			_saveToStorage(key, data) {
				try {
					uni.setStorageSync(key, data);
					console.log('成功保存了', this.localTasks.length, '个任务到本地存储');
					// 记录存储统计
					const storageSize = typeof data === 'string' ? data.length : JSON.stringify(data).length;
					console.log(`存储大小: ${Math.round(storageSize / 1024)}KB`);
				} catch (storageError) {
					console.error('保存到本地存储失败:', storageError);
					// 检查是否是存储满了
					if (storageError.message && storageError.message.includes('full')) {
						console.log('存储已满，尝试清理不必要的数据');
						this._cleanupStorage();
						// 再次尝试保存
						try {
							uni.setStorageSync(key, data);
						} catch (retryError) {
							console.error('再次保存失败:', retryError);
						}
					}
				}
			},
			
			// 精简存储数据
			_reduceStorageData(storageData, maxSize) {
				try {
					// 创建数据副本
					const reducedData = { ...storageData };
					
					// 第一级精简：移除已完成的旧任务
					const now = Date.now();
					const ONE_MONTH = 30 * 24 * 60 * 60 * 1000;
					
					reducedData.tasks = reducedData.tasks.filter(task => {
						// 保留未完成的任务
						if (!task.completed) return true;
						// 保留最近一个月内完成的任务
						const taskDate = new Date(task.updatedAt || task.createdAt || 0).getTime();
						return now - taskDate < ONE_MONTH;
					});
					
					// 第二级精简：移除不必要的字段
					reducedData.tasks = reducedData.tasks.map(task => ({
						id: task.id,
						title: task.title,
						content: task.content,
						category: task.category,
						completed: task.completed,
						needsSync: task.needsSync
					}));
					
					const reducedJson = JSON.stringify(reducedData);
					if (reducedJson.length <= maxSize) {
						return reducedJson;
					}
					
					// 第三级精简：减少任务数量
					const targetSize = Math.floor(maxSize * 0.9); // 留10%余量
					let taskCount = reducedData.tasks.length;
					
					while (taskCount > 10) { // 至少保留10个任务
						taskCount = Math.floor(taskCount * 0.8); // 每次减少20%
						const smallerTasks = reducedData.tasks.slice(0, taskCount);
						const testData = { ...reducedData, tasks: smallerTasks };
						const testJson = JSON.stringify(testData);
						
						if (testJson.length <= targetSize) {
							reducedData.tasks = smallerTasks;
							return testJson;
						}
					}
					
					return null; // 无法满足大小要求
				} catch (e) {
					console.error('精简数据失败:', e);
					return null;
				}
			},
			
			// 紧急保存模式
			_emergencySave(key) {
				try {
					// 只保存核心数据，最小化存储
					const emergencyData = {
						version: 1,
						tasks: this.tasks
							.filter(task => !task.completed || task.needsSync) // 只保留未完成或需要同步的任务
							.map(task => ({
								id: task.id,
								title: task.title || '',
								content: task.content || '',
								category: task.category || '任务',
								completed: !!task.completed,
								needsSync: !!task.needsSync
							}))
					};
					
					const emergencyJson = JSON.stringify(emergencyData);
					uni.setStorageSync(key, emergencyJson);
					console.log('紧急保存完成，保留了关键任务数据');
				} catch (e) {
					console.error('紧急保存失败:', e);
				}
			},
			
			// 清理存储
			_cleanupStorage() {
				try {
					// 清理旧版本的数据
					const oldKeys = ['todo_local_tasks'];
					oldKeys.forEach(key => {
						try {
							uni.removeStorageSync(key);
							console.log('清理旧存储键:', key);
						} catch (e) {
							// 忽略错误
						}
					});
					
					// 清理备份的损坏数据（如果有）
					const backupKeys = [];
					try {
						const keys = uni.getStorageInfoSync().keys;
						keys.forEach(key => {
							if (key.startsWith('todo_app_corrupted_')) {
								backupKeys.push(key);
							}
						});
						// 只保留最近的3个备份
						backupKeys.sort().slice(0, -3).forEach(key => {
							uni.removeStorageSync(key);
							console.log('清理旧备份:', key);
						});
					} catch (e) {
						console.error('清理备份失败:', e);
					}
				} catch (e) {
					console.error('清理存储失败:', e);
				}
			},
			
			switchCategory(category) {
				this.currentCategory = category;
			},
			toggleCompleted() {
				this.showCompleted = !this.showCompleted;
			},
			// 打开添加任务弹窗
			openAddTask() {
				this.editingTask = false;
				this.currentTask = {
					id: null,
					title: '',
					content: '',
					category: this.currentCategory
				};
				this.showTaskDialog = true;
			},
			// 获取任务列表 (WebSocket版本)
			fetchTasks() {
				this.syncStatus = 'syncing';
				uni.showLoading({ title: '加载中...' });
				
				// 使用WebSocket发送获取任务请求
				websocketManager.send('fetch_tasks');
				
				// 设置超时处理
				setTimeout(() => {
					if (this.syncStatus === 'syncing') {
						console.warn('获取任务超时，使用本地数据');
						// 超时后使用本地数据
						if (this.localTasks && this.localTasks.length > 0) {
							this.tasks = [...this.localTasks];
						}
						this.syncStatus = 'unsynced';
						try {
							uni.hideLoading();
						} catch (e) {
							// 忽略可能的重复调用错误
						}
					}
				}, 5000);
			},
			
			// 启动自动同步检查
			startAutoSyncCheck() {
				// 避免重复设置定时器
				if (this.syncCheckTimer) {
					return;
				}
				
				// 每5秒检查一次后端连接状态
				this.syncCheckTimer = setInterval(() => {
					this.checkBackendConnection();
				}, 5000);
				console.log('自动同步检查已启动');
			},
			
			// 停止自动同步检查
			stopAutoSyncCheck() {
				if (this.syncCheckTimer) {
					clearInterval(this.syncCheckTimer);
					this.syncCheckTimer = null;
					console.log('自动同步检查已停止');
				}
			},
			
			// 检查后端连接状态 (WebSocket版本)
			checkBackendConnection() {
				// 使用WebSocket连接状态检查
				if (this.syncStatus === 'unsynced' && 
					this.tasks.some(task => task.needsSync) && 
					this.wsConnected) {
					// WebSocket已连接，尝试同步未同步的任务
					this.syncUnsyncedTasks();
				}
			},
			
			// 同步所有未同步的任务
			syncUnsyncedTasks() {
				// 只有当状态不是正在同步时才开始同步
				if (this.syncStatus === 'syncing') {
					return;
				}
				
				const unsyncedTasks = this.tasks.filter(task => task.needsSync);
				if (unsyncedTasks.length === 0) {
					this.syncStatus = 'synced';
					return;
				}
				
				console.log(`开始同步${unsyncedTasks.length}个未同步任务`);
				this.syncStatus = 'syncing';
				
				// 逐个同步任务，避免并发请求过多
				let syncIndex = 0;
				const syncNext = () => {
					if (syncIndex >= unsyncedTasks.length) {
						// 所有任务同步完成
						console.log('所有任务同步完成');
						this.syncStatus = 'synced';
						this.saveLocalTasks();
						return;
					}
					
					const task = unsyncedTasks[syncIndex];
					syncIndex++;
					
					// 确定是新增还是更新操作，确保task.id是字符串类型
					const taskId = String(task.id);
					const method = taskId.startsWith('temp_') ? 'POST' : 'PUT';
					this.syncTaskToServer(task, method).then(() => {
						// 延迟100ms同步下一个任务
						setTimeout(syncNext, 100);
					}).catch(() => {
						// 单个任务同步失败，继续尝试下一个
						setTimeout(syncNext, 100);
					});
				};
				
				// 开始同步第一个任务
				syncNext();
			},
			// 关闭任务弹窗
			closeTaskDialog() {
				this.showTaskDialog = false;
				this.editingTask = false;
				this.currentTask = {
					id: null,
					title: '',
					content: '',
					category: this.currentCategory
				};
			},
			// 编辑任务
			editTask(task) {
				this.editingTask = true;
				this.currentTask = {
					id: task.id,
					title: task.title || '',
					content: task.content,
					category: task.category
				};
				this.showTaskDialog = true;
			},
			// 保存任务（添加或更新）- 离线优先策略
			saveTask() {
				// 验证内容
				if (!this.currentTask.content.trim()) {
					uni.showToast({
						title: '内容不能为空',
						icon: 'none'
					});
					return;
				}
				
				const isEdit = this.editingTask;
				const taskData = {
					title: this.currentTask.title.trim(),
					content: this.currentTask.content.trim(),
					category: isEdit ? this.currentTask.category : this.currentCategory,
					completed: isEdit ? this.tasks.find(t => t.id === this.currentTask.id)?.completed : false,
					// 添加同步状态标记
					needsSync: true
				};
				
				uni.showLoading({ title: isEdit ? '更新中...' : '添加中...' });
				
				try {
					if (isEdit) {
						// 更新任务 - 先更新本地
						const index = this.tasks.findIndex(t => t.id === this.currentTask.id);
						if (index !== -1) {
							this.tasks[index] = {
								...this.tasks[index],
								...taskData
							};
							this.saveLocalTasks(); // 立即保存到本地存储
							
							// 然后尝试同步到后端
							this.syncTaskToServer(this.tasks[index], 'PUT');
						}
					} else {
						// 添加任务 - 先生成临时ID并保存到本地
						const newTask = {
							...taskData,
							id: this.generateTempId(), // 生成临时ID
							createdAt: new Date().toISOString()
						};
						this.tasks.push(newTask);
						this.saveLocalTasks(); // 立即保存到本地存储
						
						// 然后尝试同步到后端
						this.syncTaskToServer(newTask, 'POST');
					}
					
					uni.showToast({
						title: isEdit ? '任务已更新（可能需要稍后同步）' : '任务已添加（可能需要稍后同步）',
						icon: 'success'
					});
					this.closeTaskDialog();
				} catch (error) {
					console.error('保存任务失败:', error);
					uni.showToast({
						title: '保存失败',
						icon: 'none'
					});
				} finally {
					uni.hideLoading();
				}
			},
			
			// 生成临时ID
			generateTempId() {
				return 'temp_' + Date.now() + '_' + Math.floor(Math.random() * 1000);
			},
			
			// 同步任务到服务器 (WebSocket版本)
			syncTaskToServer(task, method) {
				return new Promise((resolve, reject) => {
					// 确保task.id是字符串类型
					const taskId = String(task.id);
					
					// 过滤掉不需要发送到服务器的字段
					const taskToSend = {
						title: task.title,
						content: task.content,
						category: task.category,
						completed: task.completed
					};
					
					// 生成请求ID
					const requestId = this.generateRequestId();
					// 记录挂起的请求
					this.pendingRequests[requestId] = taskId;
					
					// 使用WebSocket发送请求
					if (method === 'POST') {
						websocketManager.send('create_task', { task: taskToSend }, requestId);
					} else if (method === 'PUT') {
						// 对于更新操作，需要移除临时前缀
						const serverTaskId = taskId.replace('temp_', '');
						websocketManager.send('update_task', {
							id: serverTaskId,
							task: taskToSend
						}, requestId);
					}
					
					// 设置超时处理
					setTimeout(() => {
						if (this.pendingRequests[requestId]) {
							console.error(`任务${taskId}同步超时`);
							delete this.pendingRequests[requestId];
							this.syncStatus = 'unsynced';
							reject(new Error('Sync timeout'));
						}
					}, 5000);
					
					// WebSocket版本中，实际的成功/失败处理在相应的事件监听器中
					resolve();
				});
			},
			// 切换任务完成状态 - 离线优先策略
			toggleComplete(task) {
				const newCompletedState = !task.completed;
				uni.showLoading({ title: '更新中...' });
				
				// 先更新本地状态
				try {
					const index = this.tasks.findIndex(t => t.id === task.id);
					if (index !== -1) {
						this.tasks[index] = {
							...this.tasks[index],
							completed: newCompletedState,
							needsSync: true
						};
						this.saveLocalTasks(); // 立即保存到本地存储
						
						// 然后尝试同步到后端
						this.syncTaskCompletionToServer(task.id, newCompletedState);
					}
					
					uni.showToast({
						title: '任务状态已更新（可能需要稍后同步）',
						icon: 'success'
					});
				} catch (error) {
					console.error('更新任务状态失败:', error);
					uni.showToast({
						title: '更新失败',
						icon: 'none'
					});
				} finally {
					uni.hideLoading();
				}
			},
			
			// 同步任务完成状态到服务器 (WebSocket版本)
			syncTaskCompletionToServer(taskId, completed) {
				// 确保taskId是字符串类型
				const taskIdStr = String(taskId);
				
				// 生成请求ID
				const requestId = this.generateRequestId();
				// 记录挂起的请求
				this.pendingRequests[requestId] = taskIdStr;
				
				// 使用WebSocket发送请求，移除临时前缀
				const serverTaskId = taskIdStr.replace('temp_', '');
				websocketManager.send('update_task_completed', {
					id: serverTaskId,
					completed: completed
				}, requestId);
				
				// 设置超时处理
				setTimeout(() => {
					if (this.pendingRequests[requestId]) {
						console.error(`任务完成状态更新超时: ${taskIdStr}`);
						delete this.pendingRequests[requestId];
						this.syncStatus = 'unsynced';
					}
				}, 5000);
			},
			// 删除任务 - 离线优先策略
			deleteTask(taskId) {
				uni.showModal({
					title: '确认删除',
					content: '确定要删除这个任务吗？',
					confirmText: '删除',
					confirmColor: '#ee0a24',
					cancelText: '取消',
					success: (res) => {
						if (res.confirm) {
							uni.showLoading({ title: '删除中...' });
							
							// 先从本地删除
							try {
								// 找到要删除的任务，以便尝试从服务器删除
								const taskToDelete = this.tasks.find(task => task.id === taskId);
								
								// 立即从本地移除
								this.tasks = this.tasks.filter(task => task.id !== taskId);
								this.saveLocalTasks(); // 保存到本地存储
								
								// 然后尝试从服务器删除（如果不是临时任务ID）
								if (taskToDelete && !taskToDelete.id.startsWith('temp_')) {
									this.syncTaskDeletionToServer(taskId);
								}
								
								uni.showToast({
									title: '任务已删除（可能需要稍后同步）',
									icon: 'success'
								});
							} catch (error) {
								console.error('删除任务失败:', error);
								uni.showToast({
									title: '删除失败',
									icon: 'none'
								});
							} finally {
								uni.hideLoading();
							}
						}
					}
				});
			},
			
			// 同步任务删除到服务器 (WebSocket版本)
			syncTaskDeletionToServer(taskId) {
				// 确保taskId是字符串类型
				const taskIdStr = String(taskId);
				
				// 生成请求ID
				const requestId = this.generateRequestId();
				// 记录挂起的请求
				this.pendingRequests[requestId] = taskIdStr;
				
				// 使用WebSocket发送请求，移除临时前缀
				const serverTaskId = taskIdStr.replace('temp_', '');
				websocketManager.send('delete_task', {
					id: serverTaskId
				}, requestId);
				
				// 设置超时处理
				setTimeout(() => {
					if (this.pendingRequests[requestId]) {
						console.error(`任务删除超时: ${taskIdStr}`);
						delete this.pendingRequests[requestId];
						this.syncStatus = 'unsynced';
					}
				}, 5000);
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
	}
	.sync-status {
		position: fixed;
		left: 20rpx;
		top: 20rpx;
		z-index: 1000;
		display: flex;
		align-items: center;
		padding: 8rpx 16rpx;
		border-radius: 20rpx;
		background-color: #f5f5f5;
		font-size: 24rpx;
	}
	.sync-status.synced {
		background-color: #e6f7e9;
	}
	.sync-status.syncing {
		background-color: #e6f4ff;
	}
	.sync-status.unsynced {
		background-color: #fff7e6;
	}
	.status-icon {
		margin-right: 8rpx;
		font-size: 28rpx;
	}
	.sync-status.synced .status-icon {
		color: #52c41a;
	}
	.sync-status.syncing .status-icon {
		color: #1890ff;
		animation: rotate 1.5s linear infinite;
	}
	.sync-status.unsynced .status-icon {
		color: #faad14;
	}
	.status-text {
		font-size: 24rpx;
	}
	@keyframes rotate {
		from { transform: rotate(0deg); }
		to { transform: rotate(360deg); }
	}

	.page-title {
		font-size: 44rpx;
		font-weight: bold;
		color: #333;
	}

	.category-tabs {
		display: flex;
		background-color: #fff;
		border-radius: 12rpx;
		padding: 10rpx;
		margin-bottom: 20rpx;
	}

	.tab {
		flex: 1;
		text-align: center;
		padding: 20rpx;
		border-radius: 8rpx;
		color: #666;
		font-size: 32rpx;
	}

	.tab.active {
		background-color: #07c160;
		color: #fff;
	}

	.task-list {
		background-color: #fff;
		border-radius: 12rpx;
		padding: 20rpx;
		min-height: 60vh;
	}

	.task-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 20rpx 0;
		border-bottom: 1rpx solid #f0f0f0;
	}

	.task-item:last-child {
		border-bottom: none;
	}

	.task-item.completed .task-text,
	.task-item.completed .task-title {
		text-decoration: line-through;
		color: #999;
	}

	.task-content {
		flex: 1;
		padding-right: 20rpx;
	}

	.task-title {
		display: block;
		font-size: 32rpx;
		font-weight: bold;
		color: #333;
		margin-bottom: 8rpx;
	}

	.task-text {
		display: block;
		font-size: 28rpx;
		color: #666;
		word-break: break-all;
	}

	.task-actions {
		display: flex;
		align-items: center;
		gap: 20rpx;
	}
	
	.icon-btn {
		width: 40rpx;
		height: 40rpx;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 32rpx;
	}
	
	.check-btn {
		color: #ccc;
		border: 2rpx solid #ccc;
		border-radius: 50%;
		width: 44rpx;
		height: 44rpx;
	}
	
	.check-btn.checked {
		color: #fff;
		background-color: #07c160;
		border-color: #07c160;
	}
	
	.edit-btn {
		color: #1989fa;
	}
	
	.delete-btn {
		color: #ee0a24;
	}

	.completed-section {
		margin-top: 20rpx;
	}

	.completed-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 20rpx 0;
		color: #666;
		font-size: 28rpx;
		border-top: 2rpx dashed #e0e0e0;
	}
	
	.arrow-icon {
		font-size: 24rpx;
		color: #666;
	}

	.completed-tasks {
		margin-top: 10rpx;
	}

	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 100rpx 0;
		color: #ccc;
	}

	.empty-text {
		margin-top: 20rpx;
		font-size: 32rpx;
	}
	
	.empty-hint {
		margin-top: 10rpx;
		font-size: 28rpx;
		color: #999;
	}
	
	.empty-icon {
		font-size: 80rpx;
		margin-bottom: 20rpx;
	}

	.add-btn {
		position: fixed;
		bottom: 50rpx;
		right: 50rpx;
		width: 100rpx;
		height: 100rpx;
		background-color: #07c160;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		box-shadow: 0 4rpx 16rpx rgba(7, 193, 96, 0.4);
		font-size: 60rpx;
		color: #fff;
		z-index: 999;
		cursor: pointer;
	}

	/* 弹窗样式 */
	.popup-mask {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background-color: rgba(0, 0, 0, 0.5);
		z-index: 9998;
	}
	
	.popup {
		position: fixed;
		bottom: 0;
		left: 0;
		right: 0;
		z-index: 9999;
		animation: slideIn 0.3s ease-out;
	}
	
	@keyframes slideIn {
		from {
			transform: translateY(100%);
		}
		to {
			transform: translateY(0);
		}
	}
	
	.popup-content {
		background-color: #fff;
		border-radius: 20rpx 20rpx 0 0;
		padding: 30rpx;
	}
	
	.close-btn {
		font-size: 32rpx;
		color: #666;
		padding: 10rpx;
	}

	.popup-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 30rpx;
	}

	.popup-title {
		font-size: 36rpx;
		font-weight: bold;
		color: #333;
	}

	.input-item {
		margin-bottom: 30rpx;
		padding: 20rpx;
		border: 2rpx solid #e0e0e0;
		border-radius: 8rpx;
		font-size: 32rpx;
	}
	
	.input-item.textarea {
		min-height: 200rpx;
		padding: 20rpx;
		resize: none;
	}

	.btn-group {
		display: flex;
		gap: 20rpx;
		margin-top: 30rpx;
	}

	.cancel-btn,
	.confirm-btn {
		flex: 1;
		border-radius: 8rpx;
		padding: 20rpx;
		font-size: 32rpx;
		border: none;
	}
	
	.cancel-btn {
			background-color: #f0f0f0;
			color: #666;
		}

		.confirm-btn {
			background-color: #07c160;
			color: #fff;
		}
</style>
