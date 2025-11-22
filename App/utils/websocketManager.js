/**
 * WebSocket管理器
 * 负责WebSocket连接的建立、维护和消息通信
 */
class WebSocketManager {
  constructor() {
    this.socket = null;
    this.isConnected = false;
    this.reconnectTimer = null;
    this.heartbeatTimer = null;
    this.reconnectInterval = 5000; // 重连间隔5秒
    this.heartbeatInterval = 30000; // 心跳间隔30秒
    this.messageQueue = []; // 未发送的消息队列
    this.listeners = {}; // 事件监听器
    this.url = ''; // WebSocket服务器地址
    // #ifdef H5
    this.isH5 = true;
    // #endif
    // #ifndef H5
    this.isH5 = false;
    // #endif
  }

  /**
   * 初始化WebSocket连接
   * @param {string} serverUrl - WebSocket服务器地址
   */
  init(serverUrl) {
    if (!serverUrl) {
      console.error('WebSocket服务器地址不能为空');
      return;
    }
    
    this.url = serverUrl;
    this.connect();
  }

  /**
   * 建立WebSocket连接
   */
  connect() {
    try {
      // 关闭现有的连接
      if (this.socket) {
        this.socket.close();
        this.socket = null;
      }

      console.log('尝试连接WebSocket服务器:', this.url);
      
      if (this.isH5) {
        // H5环境：尝试使用Socket.IO客户端
        this.connectSocketIO();
      } else {
        // 非H5环境：使用原生WebSocket
        this.connectNativeWebSocket();
      }
    } catch (e) {
      console.error('创建WebSocket连接失败:', e);
      this.handleReconnect();
    }
  }

  /**
   * 使用Socket.IO客户端连接（H5环境）
   */
  connectSocketIO() {
    try {
      // 动态加载Socket.IO客户端库
      if (typeof io === 'undefined') {
        this.loadSocketIOScript(() => {
          this.initSocketIOConnection();
        });
      } else {
        this.initSocketIOConnection();
      }
    } catch (e) {
      console.error('Socket.IO连接失败:', e);
      this.fallbackToNativeWebSocket();
    }
  }

  /**
   * 加载Socket.IO客户端库
   */
  loadSocketIOScript(callback) {
    // #ifdef H5
    const script = document.createElement('script');
    script.src = 'https://cdn.socket.io/4.7.2/socket.io.min.js';
    script.onload = callback;
    script.onerror = () => {
      console.error('加载Socket.IO客户端库失败，回退到原生WebSocket');
      this.fallbackToNativeWebSocket();
    };
    document.head.appendChild(script);
    // #endif
    
    // #ifndef H5
    // App 环境下不支持动态加载脚本，直接使用原生WebSocket
    console.log('App环境，使用原生WebSocket');
    this.fallbackToNativeWebSocket();
    // #endif
  }

  /**
   * 初始化Socket.IO连接
   */
  initSocketIOConnection() {
    try {
      this.socket = io(this.url, {
        transports: ['websocket', 'polling'],
        timeout: 5000,
        forceNew: true
      });

      this.socket.on('connect', () => {
        console.log('Socket.IO连接已建立');
        this.isConnected = true;
        this.emit('connected', { message: '连接成功' });
        this.startHeartbeat();
        this.flushMessageQueue();
      });

      this.socket.on('disconnect', () => {
        console.log('Socket.IO连接已断开');
        this.isConnected = false;
        this.emit('disconnected', { message: '连接已断开' });
        this.stopHeartbeat();
        this.handleReconnect();
      });

      this.socket.on('connect_error', (err) => {
        console.error('Socket.IO连接错误:', err);
        this.isConnected = false;
        this.emit('error', { error: err.message });
        this.handleReconnect();
      });

      // 监听Socket.IO事件
      this.setupSocketIOEvents();
    } catch (e) {
      console.error('初始化Socket.IO连接失败:', e);
      this.fallbackToNativeWebSocket();
    }
  }

  /**
   * 设置Socket.IO事件监听
   */
  setupSocketIOEvents() {
    const events = [
      'tasks_data', 'task_created', 'task_updated', 
      'task_deleted', 'task_completed_updated', 
      'sync_completed', 'error', 'sync_notification', 'pong'
    ];

    events.forEach(event => {
      this.socket.on(event, (data) => {
        this.emit(event, data);
      });
    });
  }

  /**
   * 回退到原生WebSocket
   */
  fallbackToNativeWebSocket() {
    console.log('回退到原生WebSocket');
    this.connectNativeWebSocket();
  }

  /**
   * 使用原生WebSocket连接
   */
  connectNativeWebSocket() {
    let wsUrl = this.url.replace('http://', 'ws://').replace('https://', 'wss://');
    if (wsUrl.includes(':5000')) {
      wsUrl = wsUrl.replace(':5000', ':5001'); // 使用原生WebSocket端口
    }
    
    console.log('使用原生WebSocket:', wsUrl);
    
    // #ifdef H5
    // H5环境使用浏览器WebSocket API
    this.socket = new WebSocket(wsUrl);
    
    this.socket.onopen = () => {
      console.log('WebSocket连接已建立');
      this.isConnected = true;
      this.emit('connected', { message: '连接成功' });
      this.startHeartbeat();
      this.flushMessageQueue();
    };
    
    this.socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        this.handleNativeMessage(message);
      } catch (e) {
        console.error('解析WebSocket消息失败:', e);
      }
    };
    
    this.socket.onclose = () => {
      console.log('WebSocket连接已关闭');
      this.isConnected = false;
      this.emit('disconnected', { message: '连接已关闭' });
      this.stopHeartbeat();
      this.handleReconnect();
    };
    
    this.socket.onerror = (err) => {
      console.error('WebSocket连接错误:', err);
      this.isConnected = false;
      this.emit('error', { error: err.message });
    };
    // #endif
    
    // #ifndef H5
    // App环境使用uni-app WebSocket API
    this.socket = uni.connectSocket({
      url: wsUrl,
      success: () => {
        console.log('WebSocket连接请求已发送');
      },
      fail: (err) => {
        console.error('WebSocket连接失败:', err);
        this.handleReconnect();
      }
    });

    // 监听连接打开
    this.socket.onOpen(() => {
      console.log('WebSocket连接已建立');
      this.isConnected = true;
      this.emit('connected', { message: '连接成功' });
      this.startHeartbeat();
      this.flushMessageQueue();
    });

    // 监听消息接收
    this.socket.onMessage((res) => {
      try {
        const message = JSON.parse(res.data);
        this.handleNativeMessage(message);
      } catch (e) {
        console.error('解析WebSocket消息失败:', e);
      }
    });

    // 监听连接关闭
    this.socket.onClose(() => {
      console.log('WebSocket连接已关闭');
      this.isConnected = false;
      this.emit('disconnected', { message: '连接已关闭' });
      this.stopHeartbeat();
      this.handleReconnect();
    });

    // 监听连接错误
    this.socket.onError((err) => {
      console.error('WebSocket连接错误:', err);
      this.isConnected = false;
      this.emit('error', { error: err });
    });
    // #endif
  }

  /**
   * 处理原生WebSocket消息
   */
  handleNativeMessage(message) {
    const { type, data } = message;
    
    console.log('收到原生WebSocket消息:', type, data);
    
    // 处理心跳响应
    if (type === 'pong') {
      console.log('接收到心跳响应');
      return;
    }
    
    // 触发对应的事件监听器，传递完整的数据
    this.emit(type, data);
  }

  /**
   * 发送消息
   * @param {string} type - 消息类型
   * @param {object} payload - 消息数据
   * @param {string} requestId - 请求ID（可选）
   */
  send(type, payload = {}, requestId = null) {
    if (this.isH5 && this.socket && this.socket.io) {
      // Socket.IO发送
      this.socket.emit(type, payload, requestId ? requestId : null);
      console.log('Socket.IO消息发送成功:', type);
    } else if (this.socket) {
      // 原生WebSocket发送
      const message = {
        type,
        data: payload,
        requestId
      };

      if (this.isConnected && this.socket.send) {
        const messageStr = JSON.stringify(message);
        
        // #ifdef H5
        this.socket.send(messageStr);
        console.log('WebSocket消息发送成功:', type);
        // #endif
        
        // #ifndef H5
        this.socket.send({
          data: messageStr,
          success: () => {
            console.log('WebSocket消息发送成功:', type);
          },
          fail: (err) => {
            console.error('WebSocket消息发送失败:', err);
            this.queueMessage(message);
          }
        });
        // #endif
      } else {
        console.log('WebSocket未连接，将消息加入队列');
        this.queueMessage(message);
      }
    } else {
      console.log('Socket未初始化，将消息加入队列');
      this.queueMessage({ type, payload, requestId });
    }
  }

  /**
   * 将消息加入队列
   * @param {object} message - 消息对象
   */
  queueMessage(message) {
    this.messageQueue.push(message);
  }

  /**
   * 发送队列中的所有消息
   */
  flushMessageQueue() {
    if (!this.isConnected || !this.messageQueue.length) {
      return;
    }

    const sendNext = () => {
      if (this.messageQueue.length === 0 || !this.isConnected) {
        return;
      }

      const message = this.messageQueue.shift();
      
      if (this.isH5 && this.socket && this.socket.io) {
        // Socket.IO发送队列消息
        this.socket.emit(message.type, message.payload, message.requestId);
        console.log('队列消息发送成功:', message.type);
        sendNext();
      } else if (this.socket && this.socket.send) {
        // 原生WebSocket发送队列消息
        const messageStr = JSON.stringify(message);
        
        // #ifdef H5
        this.socket.send(messageStr);
        console.log('队列消息发送成功:', message.type);
        sendNext();
        // #endif
        
        // #ifndef H5
        this.socket.send({
          data: messageStr,
          success: () => {
            console.log('队列消息发送成功:', message.type);
            sendNext();
          },
          fail: (err) => {
            console.error('队列消息发送失败:', err);
            this.messageQueue.unshift(message);
          }
        });
        // #endif
      }
    };

    sendNext();
  }

  /**
   * 开始心跳检测
   */
  startHeartbeat() {
    this.stopHeartbeat();
    
    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected) {
        this.send('ping');
      }
    }, this.heartbeatInterval);
  }

  /**
   * 停止心跳检测
   */
  stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  /**
   * 处理重连
   */
  handleReconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    
    this.reconnectTimer = setTimeout(() => {
      if (!this.isConnected) {
        console.log('尝试重新连接WebSocket...');
        this.connect();
      }
    }, this.reconnectInterval);
  }

  /**
   * 添加事件监听器
   * @param {string} event - 事件类型
   * @param {function} callback - 回调函数
   */
  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }

  /**
   * 移除事件监听器
   * @param {string} event - 事件类型
   * @param {function} callback - 回调函数（可选，不传则移除所有该事件的监听器）
   */
  off(event, callback) {
    if (!this.listeners[event]) return;
    
    if (callback) {
      this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    } else {
      delete this.listeners[event];
    }
  }

  /**
   * 触发事件
   * @param {string} event - 事件类型
   * @param {object} data - 事件数据
   */
  emit(event, data) {
    if (!this.listeners[event]) return;
    
    this.listeners[event].forEach(callback => {
      try {
        callback(data);
      } catch (e) {
        console.error(`处理事件 ${event} 时出错:`, e);
      }
    });
  }

  /**
   * 关闭WebSocket连接
   */
  close() {
    this.stopHeartbeat();
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    if (this.socket) {
      if (this.isH5 && this.socket.io) {
        // Socket.IO关闭
        this.socket.disconnect();
      } else if (this.socket.close) {
        // 原生WebSocket关闭
        this.socket.close();
      }
      this.socket = null;
    }
    
    this.isConnected = false;
    this.messageQueue = [];
    
    console.log('WebSocket连接已手动关闭');
  }
}

// 导出单例实例
export default new WebSocketManager();