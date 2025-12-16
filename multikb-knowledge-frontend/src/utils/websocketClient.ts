import { ElMessage } from 'element-plus'

export interface WebSocketMessage {
  type: string
  [key: string]: any
}

export class WebSocketClient {
  private ws: WebSocket | null = null
  private url: string
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private heartbeatInterval: number | null = null
  private reconnectTimer: number | null = null
  private listeners: Map<string, (data: any) => void> = new Map()
  private onConnectCallback: (() => void) | null = null
  private onDisconnectCallback: (() => void) | null = null
  private onErrorCallback: ((error: Error) => void) | null = null

  constructor(url: string) {
    this.url = url
  }

  /**
   * 连接到WebSocket服务器
   * 自动添加认证token（如果有）
   */
  connect(): void {
    try {
      // 获取token并添加到URL
      const token = localStorage.getItem('access_token')
      let finalUrl = this.url
      
      if (token) {
        // 检查URL是否已有查询参数
        const separator = this.url.includes('?') ? '&' : '?'
        finalUrl = `${this.url}${separator}token=${encodeURIComponent(token)}`
      }
      
      this.ws = new WebSocket(finalUrl)
      this.setupEventHandlers()
    } catch (error) {
      this.handleError(new Error('连接失败'))
    }
  }

  /**
   * 设置事件处理器
   */
  private setupEventHandlers(): void {
    if (!this.ws) return

    // 连接打开
    this.ws.onopen = () => {
      this.reconnectAttempts = 0
      this.startHeartbeat()
      if (this.onConnectCallback) {
        this.onConnectCallback()
      }
    }

    // 接收消息
    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        this.handleMessage(data)
      } catch (error) {
        // 消息解析失败，忽略
      }
    }

    // 错误处理
    this.ws.onerror = (error) => {
      console.error('WebSocket错误:', error)
      // 检查是否是认证失败（403），如果是则跳转到登录页
      // 注意：onerror 事件中无法直接获取状态码，需要在 onclose 中处理
      this.handleError(new Error('WebSocket错误'))
    }

    // 连接关闭
    this.ws.onclose = (event) => {
      this.stopHeartbeat()
      
      console.log('WebSocket关闭:', {
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean
      })
      
      // 检查关闭代码和原因，如果是认证失败，跳转到登录页
      // WebSocket 关闭代码：
      // 1008 = Policy Violation (通常用于认证失败)
      // 1002 = Protocol Error (协议错误，也可能用于认证问题)
      // 1006 = Abnormal Closure (异常关闭，可能是连接被拒绝)
      const isAuthFailure = 
        event.code === 1008 || 
        event.code === 1002 || 
        event.code === 1006 ||
        (event.reason && (
          event.reason.includes('缺少认证令牌') ||
          event.reason.includes('认证令牌无效') ||
          event.reason.includes('认证失败') ||
          event.reason.includes('Missing authentication token') ||
          event.reason.includes('Invalid authentication token')
        ))
      
      if (isAuthFailure) {
        console.warn('WebSocket认证失败，跳转到登录页:', {
          code: event.code,
          reason: event.reason
        })
        // 认证失败，清除本地token并跳转到登录页
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        
        // 停止重连
        this.reconnectAttempts = this.maxReconnectAttempts
        
        // 延迟跳转，避免在组件卸载时跳转
        setTimeout(() => {
          window.location.href = '/login'
        }, 100)
        return
      }
      
      // 尝试重连
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnect()
      } else {
        if (this.onDisconnectCallback) {
          this.onDisconnectCallback()
        }
      }
    }
  }

  /**
   * 处理接收到的消息
   */
  private handleMessage(data: any): void {
    const type = data.type

    // 处理心跳响应
    if (type === 'pong') {
      return
    }

    // 触发对应的监听器
    if (this.listeners.has(type)) {
      const listener = this.listeners.get(type)
      if (listener) {
        listener(data)
      }
    }

    // 触发通用监听器
    if (this.listeners.has('*')) {
      const listener = this.listeners.get('*')
      if (listener) {
        listener(data)
      }
    }
  }

  /**
   * 发送消息
   */
  send(data: any): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      ElMessage.warning('WebSocket未连接')
      return
    }

    try {
      this.ws.send(JSON.stringify(data))
    } catch (error) {
      this.handleError(new Error('发送消息失败'))
    }
  }

  /**
   * 订阅消息
   */
  subscribe(type: string, listener: (data: any) => void): void {
    this.listeners.set(type, listener)
  }

  /**
   * 取消订阅
   */
  unsubscribe(type: string): void {
    this.listeners.delete(type)
  }

  /**
   * 设置连接回调
   */
  onConnect(callback: () => void): void {
    this.onConnectCallback = callback
  }

  /**
   * 设置断开回调
   */
  onDisconnect(callback: () => void): void {
    this.onDisconnectCallback = callback
  }

  /**
   * 设置错误回调
   */
  onError(callback: (error: Error) => void): void {
    this.onErrorCallback = callback
  }

  /**
   * 开始心跳
   */
  private startHeartbeat(): void {
    this.stopHeartbeat()
    
    this.heartbeatInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }))
      }
    }, 30000) as any // 每30秒心跳一次
  }

  /**
   * 停止心跳
   */
  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }

  /**
   * 重连
   */
  private reconnect(): void {
    this.reconnectAttempts++
    
    // 清除之前的重连定时器
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
    }

    // 延迟重连（指数退避）
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), 30000)
    this.reconnectTimer = setTimeout(() => {
      this.connect()
    }, delay) as any
  }

  /**
   * 处理错误
   */
  private handleError(error: Error): void {
    if (this.onErrorCallback) {
      this.onErrorCallback(error)
    }
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this.stopHeartbeat()
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }

    this.reconnectAttempts = this.maxReconnectAttempts // 停止重连
  }

  /**
   * 获取连接状态
   */
  getReadyState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED
  }

  /**
   * 是否已连接
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}
