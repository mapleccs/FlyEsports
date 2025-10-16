/**
 * WebSocket客户端服务
 * 提供统一的WebSocket连接管理、消息处理和状态同步功能
 */

export interface WebSocketMessage {
  type: string
  data?: any
  timestamp?: string
}

export interface WebSocketConfig {
  url: string
  token?: string
  reconnectInterval?: number
  maxReconnectAttempts?: number
  heartbeatInterval?: number
}

export interface WebSocketEventHandlers {
  onOpen?: (event: Event) => void
  onMessage?: (message: WebSocketMessage) => void
  onClose?: (event: CloseEvent) => void
  onError?: (event: Event) => void
  onReconnect?: (attempt: number) => void
  onReconnectFailed?: () => void
}

export class WebSocketService {
  private ws: WebSocket | null = null
  private config: WebSocketConfig
  private handlers: WebSocketEventHandlers
  private reconnectAttempts = 0
  private heartbeatTimer: number | null = null
  private reconnectTimer: number | null = null
  private isManualClose = false
  private isConnected = false

  constructor(config: WebSocketConfig, handlers: WebSocketEventHandlers = {}) {
    this.config = {
      reconnectInterval: 3000,
      maxReconnectAttempts: 5,
      heartbeatInterval: 30000,
      ...config
    }
    this.handlers = handlers
  }

  /**
   * 建立WebSocket连接
   */
  connect(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.warn('WebSocket连接已存在')
      return
    }

    try {
      // 构建连接URL，包含认证令牌
      let connectUrl = this.config.url
      if (this.config.token) {
        const separator = connectUrl.includes('?') ? '&' : '?'
        connectUrl += `${separator}token=${encodeURIComponent(this.config.token)}`
      }

      console.log('正在连接WebSocket:', connectUrl.replace(/token=[^&]*/, 'token=***'))

      this.ws = new WebSocket(connectUrl)
      this.setupEventHandlers()
    } catch (error) {
      console.error('WebSocket连接失败:', error)
      this.handleReconnect()
    }
  }

  /**
   * 设置WebSocket事件处理器
   */
  private setupEventHandlers(): void {
    if (!this.ws) return

    this.ws.onopen = (event) => {
      console.log('WebSocket连接成功')
      this.isConnected = true
      this.isManualClose = false
      this.reconnectAttempts = 0
      
      // 启动心跳检测
      this.startHeartbeat()
      
      // 调用用户定义的onOpen处理器
      this.handlers.onOpen?.(event)
    }

    this.ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data)
        console.log('收到WebSocket消息:', message.type, message)
        
        // 处理内置消息类型
        if (message.type === 'pong') {
          // 心跳响应，不需要特殊处理
          return
        }
        
        // 调用用户定义的onMessage处理器
        this.handlers.onMessage?.(message)
      } catch (error) {
        console.error('解析WebSocket消息失败:', error, event.data)
      }
    }

    this.ws.onclose = (event) => {
      console.log('WebSocket连接关闭:', event.code, event.reason)
      this.isConnected = false
      this.stopHeartbeat()
      
      // 调用用户定义的onClose处理器
      this.handlers.onClose?.(event)
      
      // 如果不是手动关闭，尝试重连
      if (!this.isManualClose) {
        this.handleReconnect()
      }
    }

    this.ws.onerror = (event) => {
      console.error('WebSocket连接错误:', event)
      this.isConnected = false
      
      // 调用用户定义的onError处理器
      this.handlers.onError?.(event)
    }
  }

  /**
   * 发送消息
   */
  send(message: WebSocketMessage): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket未连接，无法发送消息:', message.type)
      return false
    }

    try {
      const messageString = JSON.stringify({
        ...message,
        timestamp: new Date().toISOString()
      })
      this.ws.send(messageString)
      console.log('发送WebSocket消息:', message.type, message)
      return true
    } catch (error) {
      console.error('发送WebSocket消息失败:', error)
      return false
    }
  }

  /**
   * 关闭连接
   */
  close(): void {
    this.isManualClose = true
    this.stopHeartbeat()
    this.stopReconnect()
    
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  /**
   * 检查连接状态
   */
  isWebSocketConnected(): boolean {
    return this.isConnected && this.ws?.readyState === WebSocket.OPEN
  }

  /**
   * 获取连接状态
   */
  getConnectionState(): string {
    if (!this.ws) return 'DISCONNECTED'
    
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'CONNECTING'
      case WebSocket.OPEN:
        return 'CONNECTED'
      case WebSocket.CLOSING:
        return 'CLOSING'
      case WebSocket.CLOSED:
        return 'DISCONNECTED'
      default:
        return 'UNKNOWN'
    }
  }

  /**
   * 启动心跳检测
   */
  private startHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
    }

    this.heartbeatTimer = window.setInterval(() => {
      if (this.isWebSocketConnected()) {
        this.send({
          type: 'ping',
          data: { timestamp: Date.now() }
        })
      }
    }, this.config.heartbeatInterval!)
  }

  /**
   * 停止心跳检测
   */
  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  /**
   * 处理重连逻辑
   */
  private handleReconnect(): void {
    if (this.isManualClose || this.reconnectAttempts >= this.config.maxReconnectAttempts!) {
      console.log('达到最大重连次数或手动关闭，停止重连')
      this.handlers.onReconnectFailed?.()
      return
    }

    this.reconnectAttempts++
    console.log(`WebSocket重连尝试 ${this.reconnectAttempts}/${this.config.maxReconnectAttempts}`)
    
    this.handlers.onReconnect?.(this.reconnectAttempts)

    this.reconnectTimer = window.setTimeout(() => {
      this.connect()
    }, this.config.reconnectInterval!)
  }

  /**
   * 停止重连
   */
  private stopReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.reconnectAttempts = 0
  }

  /**
   * 更新认证令牌
   */
  updateToken(token: string): void {
    this.config.token = token
    
    // 如果当前已连接，需要重新连接以使用新token
    if (this.isWebSocketConnected()) {
      console.log('更新token，重新连接WebSocket')
      this.close()
      setTimeout(() => this.connect(), 100)
    }
  }
}

/**
 * BP房间WebSocket服务
 * 专门用于BP阶段的实时通信
 */
export class BPWebSocketService extends WebSocketService {
  private roomId: string

  constructor(roomId: string, token: string, handlers: WebSocketEventHandlers = {}) {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsHost = window.location.hostname
    const wsPort = import.meta.env.VITE_WS_PORT || '8000'
    
    super(
      {
        url: `${wsProtocol}//${wsHost}:${wsPort}/ws/bp/${roomId}`,
        token,
        reconnectInterval: 2000,
        maxReconnectAttempts: 10,
        heartbeatInterval: 25000
      },
      handlers
    )
    
    this.roomId = roomId
  }

  /**
   * 发送BP操作消息
   */
  sendBPAction(actionType: 'ban' | 'pick', championId: number, team: 'blue' | 'red', championName?: string): boolean {
    return this.send({
      type: 'bp_action',
      data: {
        action_type: actionType,
        champion_id: championId,
        team,
        champion_name: championName
      }
    })
  }

  /**
   * 切换准备状态
   */
  toggleReady(isReady: boolean): boolean {
    return this.send({
      type: 'ready_toggle',
      data: { is_ready: isReady }
    })
  }

  /**
   * 发送聊天消息
   */
  sendChatMessage(message: string): boolean {
    return this.send({
      type: 'chat_message',
      data: { message: message.trim() }
    })
  }

  /**
   * 请求房间当前状态
   */
  requestRoomState(): boolean {
    return this.send({
      type: 'request_room_state',
      data: {}
    })
  }

  /**
   * 更新参与者信息
   */
  updateParticipant(updates: { team_side?: 'blue' | 'red' | null; role?: string; is_ready?: boolean }): boolean {
    return this.send({
      type: 'update_participant',
      data: updates
    })
  }

  /**
   * 请求参与者状态同步
   */
  requestParticipantsSync(): boolean {
    return this.send({
      type: 'request_participants_sync',
      data: {}
    })
  }

  /**
   * 获取房间ID
   */
  getRoomId(): string {
    return this.roomId
  }
}

/**
 * 通用WebSocket服务
 * 用于全局消息和频道订阅
 */
export class GeneralWebSocketService extends WebSocketService {
  private subscribedChannels = new Set<string>()

  constructor(token: string, handlers: WebSocketEventHandlers = {}) {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsHost = window.location.hostname
    const wsPort = import.meta.env.VITE_WS_PORT || '8000'
    
    super(
      {
        url: `${wsProtocol}//${wsHost}:${wsPort}/ws`,
        token,
        reconnectInterval: 3000,
        maxReconnectAttempts: 8
      },
      {
        ...handlers,
        onOpen: (event) => {
          // 重新订阅所有频道
          this.resubscribeChannels()
          handlers.onOpen?.(event)
        }
      }
    )
  }

  /**
   * 订阅频道
   */
  subscribeChannel(channel: string): boolean {
    const success = this.send({
      type: 'subscribe',
      data: { channel }
    })
    
    if (success) {
      this.subscribedChannels.add(channel)
    }
    
    return success
  }

  /**
   * 取消订阅频道
   */
  unsubscribeChannel(channel: string): boolean {
    const success = this.send({
      type: 'unsubscribe',
      data: { channel }
    })
    
    if (success) {
      this.subscribedChannels.delete(channel)
    }
    
    return success
  }

  /**
   * 重新订阅所有频道（用于重连后）
   */
  private resubscribeChannels(): void {
    for (const channel of this.subscribedChannels) {
      this.send({
        type: 'subscribe',
        data: { channel }
      })
    }
  }

  /**
   * 获取已订阅的频道列表
   */
  getSubscribedChannels(): string[] {
    return Array.from(this.subscribedChannels)
  }
}

export default WebSocketService