/**
 * WebSocket工具
 */

import { ElMessage } from 'element-plus'

export interface WebSocketMessage {
  type: string
  data: any
  timestamp: string
}

export interface ModificationStatus {
  document_id: number
  chunk_id: number
  status: 'pending' | 'validating' | 'saving' | 'vectorizing' | 'indexing' | 'completed' | 'failed'
  progress: number
  message: string
}

export class WebSocketClient {
  private ws: WebSocket | null = null
  private url: string
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private listeners: Map<string, Function[]> = new Map()
  private heartbeatInterval: number | null = null
  private isReconnecting = false

  constructor(url: string) {
    this.url = url
  }

  /**
   * 连接WebSocket
   */
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url)

        this.ws.onopen = () => {
          console.log('WebSocket连接成功')
          this.reconnectAttempts = 0
          this.isReconnecting = false
          this.startHeartbeat()
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data)
            this.handleMessage(message)
          } catch (error) {
            console.error('解析WebSocket消息失败:', error)
          }
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket错误:', error)
          reject(error)
        }

        this.ws.onclose = () => {
          console.log('WebSocket连接关闭')
          this.stopHeartbeat()
          
          if (!this.isReconnecting && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnect()
          }
        }
      } catch (error) {
        reject(error)
      }
    })
  }

  /**
   * 断开连接
   */
  disconnect() {
    this.isReconnecting = true
    this.stopHeartbeat()
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  /**
   * 重连
   */
  private reconnect() {
    this.isReconnecting = true
    this.reconnectAttempts++
    
    console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`)
    
    setTimeout(() => {
      this.connect().catch(error => {
        console.error('重连失败:', error)
        
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          ElMessage.error('WebSocket连接失败，请刷新页面重试')
        }
      })
    }, this.reconnectDelay * this.reconnectAttempts)
  }

  /**
   * 心跳
   */
  private startHeartbeat() {
    this.heartbeatInterval = window.setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.send('ping', {})
      }
    }, 30000)
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }

  /**
   * 发送消息
   */
  send(type: string, data: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type,
        data,
        timestamp: new Date().toISOString()
      }))
    }
  }

  /**
   * 订阅消息
   */
  subscribe(event: string, callback: Function) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event)?.push(callback)
  }

  /**
   * 取消订阅
   */
  unsubscribe(event: string, callback: Function) {
    const callbacks = this.listeners.get(event)
    if (callbacks) {
      const index = callbacks.indexOf(callback)
      if (index > -1) {
        callbacks.splice(index, 1)
      }
    }
  }

  /**
   * 处理消息
   */
  private handleMessage(message: WebSocketMessage) {
    const callbacks = this.listeners.get(message.type)
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback(message.data)
        } catch (error) {
          console.error('处理WebSocket消息失败:', error)
        }
      })
    }
  }

  /**
   * 获取连接状态
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

/**
 * 创建WebSocket客户端
 */
export const createWebSocketClient = (url: string): WebSocketClient => {
  return new WebSocketClient(url)
}

/**
 * 监听文档修改状态
 */
export const subscribeToModificationStatus = (
  client: WebSocketClient,
  onStatusUpdate: (status: ModificationStatus) => void
) => {
  client.subscribe('modification_status', (data: ModificationStatus) => {
    onStatusUpdate(data)
  })

  client.subscribe('modification_progress', (data: ModificationStatus) => {
    onStatusUpdate(data)
  })

  client.subscribe('modification_completed', (data: ModificationStatus) => {
    onStatusUpdate(data)
    ElMessage.success('修改已完成')
  })

  client.subscribe('modification_failed', (data: { error: string }) => {
    ElMessage.error(`修改失败: ${data.error}`)
  })
}
