/**
 * WebSocket状态管理
 * 管理WebSocket连接状态、消息处理和事件分发
 */

import { defineStore } from 'pinia'
import { ref, computed, watch, readonly } from 'vue'
import { useAuthStore } from './auth'
import { 
  BPWebSocketService, 
  GeneralWebSocketService, 
  type WebSocketMessage 
} from '@/shared/services/websocket'

interface ConnectionState {
  status: 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'failed'
  lastConnected: Date | null
  reconnectAttempts: number
  error: string | null
}

interface BPRoomState {
  roomId: string
  status: string
  config: any
  state: any
  participants: any[]
  teams: {
    team_a: any
    team_b: any
  }
}

export type MessageHandler = (data: any) => void

export interface RoomEventHandlers {
  onRoomStatusChanged?: (data: any) => void
  onParticipantJoined?: (data: any) => void
  onParticipantLeft?: (data: any) => void
  onParticipantUpdated?: (data: any) => void
  onRoomDeleted?: (data: any) => void
  onChatMessage?: (data: any) => void
  onNotification?: (data: any) => void
}

export const useWebSocketStore = defineStore('websocket', () => {
  // 连接状态
  const generalConnection = ref<ConnectionState>({
    status: 'disconnected',
    lastConnected: null,
    reconnectAttempts: 0,
    error: null
  })

  const bpConnection = ref<ConnectionState>({
    status: 'disconnected',
    lastConnected: null,
    reconnectAttempts: 0,
    error: null
  })

  // WebSocket服务实例
  const generalWS = ref<GeneralWebSocketService | null>(null)
  const bpWS = ref<BPWebSocketService | null>(null)

  // BP房间状态
  const bpRoomState = ref<BPRoomState | null>(null)

  // 消息历史
  const messageHistory = ref<WebSocketMessage[]>([])
  const chatMessages = ref<any[]>([])

  // 事件回调注册
  const eventHandlers = ref<Map<string, Function[]>>(new Map())
  
  // 房间事件处理器
  const roomEventHandlers = ref<RoomEventHandlers>({})

  // 旧的订阅管理（保持兼容性）
  const subscriptions = ref<Map<string, Set<MessageHandler>>>(new Map())
  const messageQueue = ref<WebSocketMessage[]>([])

  // 计算属性
  const isConnected = computed(() => generalConnection.value.status === 'connected')
  const isConnecting = computed(() => generalConnection.value.status === 'connecting')
  const hasError = computed(() => generalConnection.value.status === 'failed')
  const lastError = computed(() => generalConnection.value.error)
  const reconnectAttempts = computed(() => generalConnection.value.reconnectAttempts)

  const isGeneralConnected = computed(() => generalConnection.value.status === 'connected')
  const isBPConnected = computed(() => bpConnection.value.status === 'connected')
  const isAnyConnected = computed(() => isGeneralConnected.value || isBPConnected.value)

  const connectionStatus = computed(() => {
    if (isGeneralConnected.value) return 'connected'
    if (generalConnection.value.status === 'connecting') return 'connecting'
    if (generalConnection.value.status === 'failed') return 'error'
    return 'disconnected'
  })

  /**
   * 注册事件处理器
   */
  function on(event: string, handler: Function): void {
    if (!eventHandlers.value.has(event)) {
      eventHandlers.value.set(event, [])
    }
    eventHandlers.value.get(event)!.push(handler)
  }

  /**
   * 移除事件处理器
   */
  function off(event: string, handler?: Function): void {
    if (!eventHandlers.value.has(event)) return
    
    if (handler) {
      const handlers = eventHandlers.value.get(event)!
      const index = handlers.indexOf(handler)
      if (index > -1) {
        handlers.splice(index, 1)
      }
    } else {
      eventHandlers.value.delete(event)
    }
  }

  /**
   * 触发事件
   */
  function emit(event: string, ...args: any[]): void {
    const handlers = eventHandlers.value.get(event)
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(...args)
        } catch (error) {
          console.error(`事件处理器执行失败 [${event}]:`, error)
        }
      })
    }
  }

  /**
   * 添加消息到历史记录
   */
  function addToHistory(message: WebSocketMessage): void {
    messageHistory.value.push(message)
    
    // 限制历史记录数量
    if (messageHistory.value.length > 100) {
      messageHistory.value.shift()
    }
  }

  /**
   * 连接通用WebSocket
   */
  function connect(): void {
    connectGeneral()
  }

  function connectGeneral(): void {
    const authStore = useAuthStore()
    
    if (!authStore.isAuthenticated || !authStore.token) {
      console.warn('用户未认证，无法连接WebSocket')
      return
    }

    if (generalWS.value) {
      console.warn('通用WebSocket已存在')
      return
    }

    generalConnection.value.status = 'connecting'
    generalConnection.value.error = null

    generalWS.value = new GeneralWebSocketService(authStore.token, {
      onOpen: (event) => {
        console.log('通用WebSocket连接成功')
        generalConnection.value.status = 'connected'
        generalConnection.value.lastConnected = new Date()
        generalConnection.value.reconnectAttempts = 0
        
        // 处理离线消息队列
        processMessageQueue()
        
        emit('general:connected', event)
      },

      onMessage: (message) => {
        addToHistory(message)
        handleGeneralMessage(message)
        emit('general:message', message)
      },

      onClose: (event) => {
        console.log('通用WebSocket连接关闭')
        generalConnection.value.status = 'disconnected'
        emit('general:disconnected', event)
      },

      onError: (event) => {
        console.error('通用WebSocket连接错误')
        generalConnection.value.status = 'failed'
        generalConnection.value.error = '连接失败'
        emit('general:error', event)
      },

      onReconnect: (attempt) => {
        console.log(`通用WebSocket重连尝试: ${attempt}`)
        generalConnection.value.status = 'reconnecting'
        generalConnection.value.reconnectAttempts = attempt
        emit('general:reconnecting', attempt)
      },

      onReconnectFailed: () => {
        console.error('通用WebSocket重连失败')
        generalConnection.value.status = 'failed'
        generalConnection.value.error = '重连失败'
        emit('general:reconnect-failed')
      }
    })

    generalWS.value.connect()
  }

  /**
   * 连接BP WebSocket
   */
  function connectBP(roomId: string): void {
    const authStore = useAuthStore()
    
    if (!authStore.isAuthenticated || !authStore.token) {
      console.warn('用户未认证，无法连接BP WebSocket')
      return
    }

    if (bpWS.value) {
      console.warn('BP WebSocket已存在')
      return
    }

    bpConnection.value.status = 'connecting'
    bpConnection.value.error = null

    bpWS.value = new BPWebSocketService(roomId, authStore.token, {
      onOpen: (event) => {
        console.log('BP WebSocket连接成功')
        bpConnection.value.status = 'connected'
        bpConnection.value.lastConnected = new Date()
        bpConnection.value.reconnectAttempts = 0
        emit('bp:connected', event)
        
        // 连接成功后请求房间状态
        setTimeout(() => {
          bpWS.value?.requestRoomState()
        }, 500)
      },

      onMessage: (message) => {
        addToHistory(message)
        handleBPMessage(message)
        emit('bp:message', message)
      },

      onClose: (event) => {
        console.log('BP WebSocket连接关闭')
        bpConnection.value.status = 'disconnected'
        emit('bp:disconnected', event)
      },

      onError: (event) => {
        console.error('BP WebSocket连接错误')
        bpConnection.value.status = 'failed'
        bpConnection.value.error = '连接失败'
        emit('bp:error', event)
      },

      onReconnect: (attempt) => {
        console.log(`BP WebSocket重连尝试: ${attempt}`)
        bpConnection.value.status = 'reconnecting'
        bpConnection.value.reconnectAttempts = attempt
        emit('bp:reconnecting', attempt)
      },

      onReconnectFailed: () => {
        console.error('BP WebSocket重连失败')
        bpConnection.value.status = 'failed'
        bpConnection.value.error = '重连失败'
        emit('bp:reconnect-failed')
      }
    })

    bpWS.value.connect()
  }

  /**
   * 处理通用WebSocket消息
   */
  function handleGeneralMessage(message: WebSocketMessage): void {
    // 同时处理旧格式的消息（兼容性）
    handleMessage(message as any)

    switch (message.type) {
      case 'connection_established':
        console.log('WebSocket连接已建立:', message.data)
        break

      case 'subscribed':
        console.log('频道订阅成功:', message.data?.channel)
        emit('channel:subscribed', message.data?.channel)
        break

      case 'unsubscribed':
        console.log('频道取消订阅成功:', message.data?.channel)
        emit('channel:unsubscribed', message.data?.channel)
        break

      case 'user_joined':
        console.log('用户加入:', message.data)
        emit('user:joined', message.data)
        break

      case 'user_left':
        console.log('用户离开:', message.data)
        emit('user:left', message.data)
        break

      default:
        console.log('未处理的通用消息类型:', message.type)
        break
    }
  }

  /**
   * 处理BP WebSocket消息
   */
  function handleBPMessage(message: WebSocketMessage): void {
    switch (message.type) {
      case 'room_state':
        console.log('收到房间状态:', message.data)
        bpRoomState.value = message.data
        emit('bp:room-state-updated', message.data)
        break

      case 'room_stats':
        console.log('收到房间统计:', message.data)
        emit('bp:room-stats-updated', message.data)
        break

      case 'connection_confirmed':
        console.log('BP连接确认:', message.data)
        emit('bp:connection-confirmed', message.data)
        break

      case 'user_joined':
        console.log('用户加入BP房间:', message.data)
        emit('bp:user-joined', message.data)
        break

      case 'user_left':
        console.log('用户离开BP房间:', message.data)
        emit('bp:user-left', message.data)
        break

      case 'bp_action_update':
        console.log('BP操作更新:', message.data)
        emit('bp:action-updated', message.data)
        break

      case 'champion_banned':
        console.log('英雄被禁用:', message.data)
        emit('bp:champion-banned', message.data)
        break

      case 'champion_picked':
        console.log('英雄被选择:', message.data)
        emit('bp:champion-picked', message.data)
        break

      case 'timer_update':
        console.log('计时器更新:', message.data)
        emit('bp:timer-updated', message.data)
        break

      case 'action_timeout':
        console.log('操作超时:', message.data)
        emit('bp:action-timeout', message.data)
        break

      case 'user_ready_changed':
        console.log('用户准备状态变更:', message.data)
        emit('bp:user-ready-changed', message.data)
        break

      // === 房间管理事件 ===
      case 'room_status_changed':
        console.log('房间状态变更:', message.data)
        roomEventHandlers.value.onRoomStatusChanged?.(message.data)
        emit('bp:room-status-changed', message.data)
        break

      case 'participant_joined':
        console.log('参与者加入:', message.data)
        roomEventHandlers.value.onParticipantJoined?.(message.data)
        emit('bp:participant-joined', message.data)
        break

      case 'participant_left':
        console.log('参与者离开:', message.data)
        roomEventHandlers.value.onParticipantLeft?.(message.data)
        emit('bp:participant-left', message.data)
        break

      case 'participant_updated':
        console.log('参与者信息更新:', message.data)
        roomEventHandlers.value.onParticipantUpdated?.(message.data)
        emit('bp:participant-updated', message.data)
        break

      case 'participant_ready_changed':
        console.log('参与者准备状态变更:', message.data)
        roomEventHandlers.value.onParticipantUpdated?.({
          participant: message.data.participant,
          changes: { is_ready: message.data.is_ready }
        })
        emit('bp:participant-ready-changed', message.data)
        break

      case 'room_chat_message':
        console.log('房间聊天消息:', message.data)
        chatMessages.value.push({
          ...message.data,
          timestamp: new Date()
        })
        // 限制聊天消息数量
        if (chatMessages.value.length > 50) {
          chatMessages.value.shift()
        }
        roomEventHandlers.value.onChatMessage?.(message.data)
        emit('bp:room-chat-message', message.data)
        break

      case 'room_notification':
        console.log('房间通知:', message.data)
        roomEventHandlers.value.onNotification?.(message.data)
        emit('bp:room-notification', message.data)
        break

      case 'participants_sync':
        console.log('参与者状态同步:', message.data)
        emit('bp:participants-sync', message.data)
        break

      case 'room_state_sync':
        console.log('房间状态同步:', message.data)
        bpRoomState.value = message.data.room
        emit('bp:room-state-sync', message.data)
        break

      case 'room_deleted':
        console.log('房间被删除:', message.data)
        roomEventHandlers.value.onRoomDeleted?.(message.data)
        emit('bp:room-deleted', message.data)
        break

      case 'join_room_success':
        console.log('加入房间成功:', message.data)
        emit('bp:join-room-success', message.data)
        break

      case 'room_created':
        console.log('房间创建成功:', message.data)
        emit('bp:room-created', message.data)
        break

      case 'chat_message':
        console.log('聊天消息:', message.data)
        chatMessages.value.push({
          ...message.data,
          timestamp: new Date()
        })
        // 限制聊天消息数量
        if (chatMessages.value.length > 50) {
          chatMessages.value.shift()
        }
        emit('bp:chat-message', message.data)
        break

      case 'bp_complete':
        console.log('BP阶段完成:', message.data)
        emit('bp:complete', message.data)
        break

      case 'error':
        console.error('BP WebSocket错误:', message.data)
        emit('bp:error-message', message.data)
        break

      default:
        console.log('未处理的BP消息类型:', message.type)
        break
    }
  }

  /**
   * 断开通用WebSocket
   */
  function disconnect(): void {
    disconnectGeneral()
  }

  function disconnectGeneral(): void {
    if (generalWS.value) {
      generalWS.value.close()
      generalWS.value = null
    }
    generalConnection.value.status = 'disconnected'
  }

  /**
   * 断开BP WebSocket
   */
  function disconnectBP(): void {
    if (bpWS.value) {
      bpWS.value.close()
      bpWS.value = null
    }
    bpConnection.value.status = 'disconnected'
    bpRoomState.value = null
    chatMessages.value = []
  }

  /**
   * 断开所有连接
   */
  function disconnectAll(): void {
    disconnectGeneral()
    disconnectBP()
  }

  // 旧的兼容性方法
  function reconnect(): void {
    if (generalWS.value) {
      disconnectGeneral()
      setTimeout(() => connectGeneral(), 1000)
    }
  }

  function send(message: any): boolean {
    if (generalWS.value?.isWebSocketConnected()) {
      return generalWS.value.send(message)
    } else {
      console.warn('WebSocket未连接，消息已加入队列')
      messageQueue.value.push(message)
      return false
    }
  }

  function subscribe(channel: string, handler: MessageHandler): void {
    if (!subscriptions.value.has(channel)) {
      subscriptions.value.set(channel, new Set())
    }
    
    subscriptions.value.get(channel)!.add(handler)
    
    // 发送订阅消息到服务器
    if (generalWS.value) {
      generalWS.value.subscribeChannel(channel)
    }
    
    console.log(`已订阅频道: ${channel}`)
  }

  function unsubscribe(channel: string, handler?: MessageHandler): void {
    if (!subscriptions.value.has(channel)) return
    
    if (handler) {
      subscriptions.value.get(channel)!.delete(handler)
      
      // 如果没有处理器了，删除整个频道订阅
      if (subscriptions.value.get(channel)!.size === 0) {
        subscriptions.value.delete(channel)
        if (generalWS.value) {
          generalWS.value.unsubscribeChannel(channel)
        }
      }
    } else {
      // 取消整个频道的订阅
      subscriptions.value.delete(channel)
      if (generalWS.value) {
        generalWS.value.unsubscribeChannel(channel)
      }
    }
    
    console.log(`已取消订阅频道: ${channel}`)
  }

  function handleMessage(message: any): void {
    console.log('收到WebSocket消息:', message)
    
    const channel = message.channel
    if (subscriptions.value.has(channel)) {
      const handlers = subscriptions.value.get(channel)!
      handlers.forEach(handler => {
        try {
          handler(message.data)
        } catch (error) {
          console.error(`处理频道 ${channel} 消息时出错:`, error)
        }
      })
    }
  }

  function processMessageQueue(): void {
    if (messageQueue.value.length === 0) return
    
    console.log(`处理 ${messageQueue.value.length} 条离线消息`)
    
    const messages = [...messageQueue.value]
    messageQueue.value = []
    
    messages.forEach(message => {
      send(message)
    })
  }

  function sendBPMessage(roomId: string, type: string, data: any): boolean {
    return send({
      type: 'bp_message',
      channel: `bp_room_${roomId}`,
      data: {
        type,
        ...data
      }
    })
  }

  function getConnectionStats() {
    return {
      isConnected: isConnected.value,
      reconnectAttempts: reconnectAttempts.value,
      subscriptionsCount: subscriptions.value.size,
      queuedMessagesCount: messageQueue.value.length,
      lastError: lastError.value
    }
  }

  /**
   * 连接BP房间WebSocket
   */
  function connectBPRoom(roomId: string) {
    return connectBP(roomId)
  }

  /**
   * 断开BP房间WebSocket
   */
  function disconnectBPRoom() {
    disconnectBP()
    roomEventHandlers.value = {}
  }

  /**
   * 设置房间事件处理器
   */
  function setRoomEventHandlers(handlers: RoomEventHandlers) {
    roomEventHandlers.value = handlers
  }

  /**
   * 发送房间消息
   */
  function sendRoomMessage(message: { type: string; data: any }) {
    return bpWS.value?.send(message) || false
  }

  // BP相关操作方法
  const bpActions = {
    sendBPAction: (actionType: 'ban' | 'pick', championId: number, team: 'blue' | 'red', championName?: string) => {
      return bpWS.value?.sendBPAction(actionType, championId, team, championName) || false
    },

    toggleReady: (isReady: boolean) => {
      return bpWS.value?.toggleReady(isReady) || false
    },

    sendChatMessage: (message: string) => {
      return bpWS.value?.sendChatMessage(message) || false
    },

    requestRoomState: () => {
      return bpWS.value?.requestRoomState() || false
    },

    updateParticipant: (updates: { team_side?: 'blue' | 'red' | null; role?: string; is_ready?: boolean }) => {
      return bpWS.value?.updateParticipant(updates) || false
    },

    requestParticipantsSync: () => {
      return bpWS.value?.requestParticipantsSync() || false
    }
  }

  // 通用WebSocket操作方法
  const generalActions = {
    subscribeChannel: (channel: string) => {
      return generalWS.value?.subscribeChannel(channel) || false
    },

    unsubscribeChannel: (channel: string) => {
      return generalWS.value?.unsubscribeChannel(channel) || false
    }
  }

  // 监听认证状态变化
  const authStore = useAuthStore()
  watch(
    () => authStore.isAuthenticated,
    (isAuthenticated) => {
      if (!isAuthenticated) {
        // 用户登出，断开所有连接
        disconnectAll()
      }
    }
  )

  // 监听token变化
  watch(
    () => authStore.token,
    (newToken, oldToken) => {
      if (newToken && newToken !== oldToken) {
        // Token更新，重新连接
        if (generalWS.value) {
          generalWS.value.updateToken(newToken)
        }
        if (bpWS.value) {
          bpWS.value.updateToken(newToken)
        }
      }
    }
  )

  return {
    // 状态
    generalConnection,
    bpConnection,
    bpRoomState,
    messageHistory,
    chatMessages,

    // 旧的兼容性状态
    isConnected,
    isConnecting,
    hasError,
    lastError,
    reconnectAttempts,

    // 计算属性
    isGeneralConnected,
    isBPConnected,
    isAnyConnected,
    connectionStatus,

    // 连接方法
    connect,
    connectGeneral,
    connectBP,
    disconnect,
    disconnectGeneral,
    disconnectBP,
    disconnectAll,
    reconnect,

    // 旧的兼容性方法
    send,
    subscribe,
    unsubscribe,
    sendBPMessage,
    getConnectionStats,

    // 事件管理
    on,
    off,
    emit,

    // 操作方法
    bp: bpActions,
    general: generalActions,

    // 房间管理方法
    connectBPRoom,
    disconnectBPRoom,
    setRoomEventHandlers,
    sendRoomMessage
  }
})

export default useWebSocketStore