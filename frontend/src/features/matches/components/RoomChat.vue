<template>
  <div class="room-chat">
    <!-- 聊天头部 -->
    <div class="chat-header">
      <div class="header-title">
        <MessageOutlined />
        <span>房间聊天</span>
      </div>
      <div class="chat-controls">
        <a-tooltip title="清空聊天记录">
          <a-button type="text" size="small" @click="clearChat">
            <template #icon>
              <ClearOutlined />
            </template>
          </a-button>
        </a-tooltip>
        <a-tooltip title="聊天设置">
          <a-button type="text" size="small" @click="showSettings = true">
            <template #icon>
              <SettingOutlined />
            </template>
          </a-button>
        </a-tooltip>
      </div>
    </div>

    <!-- 聊天消息列表 -->
    <div class="chat-messages" ref="messagesContainer">
      <div v-if="messages.length === 0" class="empty-messages">
        <CommentOutlined />
        <p>暂无聊天消息</p>
        <p class="tip">发送第一条消息开始对话吧</p>
      </div>
      
      <div
        v-for="message in messages"
        :key="message.id || message.timestamp"
        class="message-item"
        :class="{
          'own-message': isOwnMessage(message),
          'system-message': message.message_type === 'system'
        }"
      >
        <!-- 系统消息 -->
        <div v-if="message.message_type === 'system'" class="system-content">
          <RobotOutlined />
          <span>{{ message.message }}</span>
          <time>{{ formatMessageTime(message.timestamp) }}</time>
        </div>

        <!-- 用户消息 -->
        <div v-else class="user-message">
          <div class="message-header" v-if="!isOwnMessage(message)">
            <a-avatar :size="24" :src="getUserAvatar(message.sender_id)">
              {{ message.sender_name?.[0] || '?' }}
            </a-avatar>
            <span class="sender-name">{{ message.sender_name }}</span>
            <a-tag v-if="getSenderRole(message.sender_id)" :color="getRoleColor(getSenderRole(message.sender_id))" size="small">
              {{ getRoleText(getSenderRole(message.sender_id)) }}
            </a-tag>
            <time class="message-time">{{ formatMessageTime(message.timestamp) }}</time>
          </div>
          
          <div class="message-content" :class="{ 'own-content': isOwnMessage(message) }">
            <div class="message-bubble">
              <p>{{ message.message }}</p>
            </div>
            <time v-if="isOwnMessage(message)" class="own-time">{{ formatMessageTime(message.timestamp) }}</time>
          </div>
        </div>
      </div>
    </div>

    <!-- 聊天输入框 -->
    <div class="chat-input" v-if="canSendMessage">
      <div class="input-container">
        <a-input
          v-model:value="inputMessage"
          placeholder="输入消息..."
          :maxlength="500"
          @keydown.enter="handleSendMessage"
          @keydown.ctrl.enter="handleSendMessage"
          :disabled="sending"
          class="message-input"
        />
        
        <div class="input-actions">
          <a-tooltip title="Ctrl+Enter 发送">
            <a-button
              type="primary"
              @click="handleSendMessage"
              :loading="sending"
              :disabled="!inputMessage.trim()"
            >
              <template #icon>
                <SendOutlined />
              </template>
            </a-button>
          </a-tooltip>
        </div>
      </div>
      
      <div class="input-footer">
        <span class="char-count" :class="{ warning: inputMessage.length > 400 }">
          {{ inputMessage.length }}/500
        </span>
        <span class="input-hint">按 Ctrl+Enter 发送消息</span>
      </div>
    </div>

    <!-- 聊天被禁用提示 -->
    <div v-else class="chat-disabled">
      <LockOutlined />
      <span>聊天功能已被管理员禁用</span>
    </div>

    <!-- 聊天设置模态框 -->
    <a-modal
      v-model:visible="showSettings"
      title="聊天设置"
      :footer="null"
      width="400px"
    >
      <div class="chat-settings">
        <div class="setting-item">
          <label>消息显示数量:</label>
          <a-slider
            v-model:value="maxMessages"
            :min="10"
            :max="100"
            :step="10"
            :marks="{ 10: '10', 50: '50', 100: '100' }"
          />
        </div>
        
        <div class="setting-item">
          <label>
            <a-checkbox v-model:checked="autoScroll">
              自动滚动到最新消息
            </a-checkbox>
          </label>
        </div>
        
        <div class="setting-item">
          <label>
            <a-checkbox v-model:checked="showTimestamp">
              显示详细时间戳
            </a-checkbox>
          </label>
        </div>
        
        <div class="setting-item">
          <label>
            <a-checkbox v-model:checked="enableSound">
              新消息提示音
            </a-checkbox>
          </label>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import {
  MessageOutlined,
  ClearOutlined,
  SettingOutlined,
  CommentOutlined,
  RobotOutlined,
  SendOutlined,
  LockOutlined
} from '@ant-design/icons-vue'
import { Modal, message } from 'ant-design-vue'
import { useWebSocketStore } from '@/shared/stores/websocket'
import { useAuthStore } from '@/shared/stores/auth'
import dayjs from 'dayjs'

// Props
interface Props {
  roomId: string
  canSendMessage?: boolean
  participants?: any[]
}

const props = withDefaults(defineProps<Props>(), {
  canSendMessage: true,
  participants: () => []
})

// Events
const emit = defineEmits<{
  messageSent: [message: string]
}>()

// Stores
const websocketStore = useWebSocketStore()
const authStore = useAuthStore()

// 响应式数据
const messagesContainer = ref<HTMLElement>()
const inputMessage = ref('')
const sending = ref(false)
const showSettings = ref(false)

// 设置选项
const maxMessages = ref(50)
const autoScroll = ref(true)
const showTimestamp = ref(false)
const enableSound = ref(true)

// 计算属性
const messages = computed(() => {
  const chatMessages = websocketStore.chatMessages || []
  return chatMessages.slice(-maxMessages.value)
})

const currentUserId = computed(() => authStore.user?.id)

// 方法
const isOwnMessage = (msg: any) => {
  return currentUserId.value && msg.sender_id === currentUserId.value
}

const getSenderRole = (senderId: number) => {
  const participant = props.participants.find(p => p.user_id === senderId)
  return participant?.role
}

const getRoleColor = (role: string) => {
  const colorMap = {
    admin: 'red',
    commander: 'orange',
    player: 'green',
    observer: 'default'
  }
  return colorMap[role] || 'default'
}

const getRoleText = (role: string) => {
  const textMap = {
    admin: '管理员',
    commander: '指挥',
    player: '选手',
    observer: '观战'
  }
  return textMap[role] || role
}

const getUserAvatar = (userId: number) => {
  // 这里可以根据实际需求返回用户头像URL
  return undefined
}

const formatMessageTime = (timestamp: any) => {
  try {
    const time = dayjs(timestamp)
    if (showTimestamp.value) {
      return time.format('HH:mm:ss')
    }
    return time.format('HH:mm')
  } catch {
    return ''
  }
}

const scrollToBottom = () => {
  if (!autoScroll.value || !messagesContainer.value) return
  
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const handleSendMessage = async () => {
  const trimmedMessage = inputMessage.value.trim()
  if (!trimmedMessage || sending.value) return

  try {
    sending.value = true
    
    // 通过WebSocket发送消息
    const success = websocketStore.bp.sendChatMessage(trimmedMessage)
    
    if (success) {
      emit('messageSent', trimmedMessage)
      inputMessage.value = ''
      
      // 播放发送音效
      if (enableSound.value) {
        playNotificationSound()
      }
    } else {
      message.error('发送消息失败，请检查连接状态')
    }
  } catch (error) {
    console.error('发送消息失败:', error)
    message.error('发送消息失败')
  } finally {
    sending.value = false
  }
}

const clearChat = () => {
  Modal.confirm({
    title: '确认清空',
    content: '确定要清空所有聊天记录吗？此操作仅影响本地显示。',
    okText: '确认清空',
    okType: 'danger',
    cancelText: '取消',
    onOk() {
      // 清空本地聊天记录
      websocketStore.chatMessages.splice(0)
      message.success('聊天记录已清空')
    }
  })
}

const playNotificationSound = () => {
  try {
    // 创建简单的提示音
    const audioContext = new (window.AudioContext || window.webkitAudioContext)()
    const oscillator = audioContext.createOscillator()
    const gainNode = audioContext.createGain()
    
    oscillator.connect(gainNode)
    gainNode.connect(audioContext.destination)
    
    oscillator.frequency.setValueAtTime(800, audioContext.currentTime)
    gainNode.gain.setValueAtTime(0.1, audioContext.currentTime)
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1)
    
    oscillator.start(audioContext.currentTime)
    oscillator.stop(audioContext.currentTime + 0.1)
  } catch (error) {
    // 忽略音频播放错误
    console.warn('无法播放提示音:', error)
  }
}

// 监听消息变化，自动滚动
watch(
  () => messages.value.length,
  () => {
    scrollToBottom()
    
    // 播放新消息提示音（排除自己的消息）
    if (enableSound.value && messages.value.length > 0) {
      const lastMessage = messages.value[messages.value.length - 1]
      if (!isOwnMessage(lastMessage) && lastMessage.message_type !== 'system') {
        playNotificationSound()
      }
    }
  }
)

// 生命周期
onMounted(() => {
  scrollToBottom()
})

onUnmounted(() => {
  // 清理资源
})
</script>

<style scoped>
.room-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #e5e7eb;
  background: #f9fafb;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #374151;
}

.chat-controls {
  display: flex;
  gap: 4px;
}

.chat-messages {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  max-height: 400px;
}

.empty-messages {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #9ca3af;
  text-align: center;
}

.empty-messages .anticon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-messages .tip {
  font-size: 12px;
  margin-top: 4px;
}

.message-item {
  margin-bottom: 16px;
}

.message-item:last-child {
  margin-bottom: 0;
}

.system-message .system-content {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f3f4f6;
  border-radius: 6px;
  font-size: 13px;
  color: #6b7280;
  justify-content: center;
}

.system-content time {
  font-size: 11px;
  opacity: 0.7;
  margin-left: auto;
}

.user-message {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.own-message .user-message {
  align-items: flex-end;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.sender-name {
  font-weight: 500;
  color: #374151;
  font-size: 13px;
}

.message-time {
  font-size: 11px;
  color: #9ca3af;
  margin-left: auto;
}

.message-content {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  max-width: 75%;
}

.message-content.own-content {
  align-items: flex-end;
  margin-left: auto;
}

.message-bubble {
  padding: 8px 12px;
  border-radius: 12px;
  background: #f3f4f6;
  color: #374151;
  word-wrap: break-word;
  hyphens: auto;
}

.own-content .message-bubble {
  background: #3b82f6;
  color: white;
}

.message-bubble p {
  margin: 0;
  line-height: 1.4;
}

.own-time {
  font-size: 10px;
  color: #9ca3af;
  margin-top: 2px;
}

.chat-input {
  padding: 16px;
  border-top: 1px solid #e5e7eb;
  background: #f9fafb;
}

.input-container {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.message-input {
  flex: 1;
}

.input-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  font-size: 11px;
  color: #6b7280;
}

.char-count.warning {
  color: #ef4444;
}

.input-hint {
  opacity: 0.7;
}

.chat-disabled {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px;
  background: #f3f4f6;
  color: #6b7280;
  border-top: 1px solid #e5e7eb;
}

.chat-settings {
  padding: 16px 0;
}

.setting-item {
  margin-bottom: 20px;
}

.setting-item:last-child {
  margin-bottom: 0;
}

.setting-item label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #374151;
}

/* 滚动条样式 */
.chat-messages::-webkit-scrollbar {
  width: 6px;
}

.chat-messages::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .chat-messages {
    max-height: 300px;
    padding: 12px;
  }
  
  .message-content {
    max-width: 85%;
  }
  
  .chat-input {
    padding: 12px;
  }
  
  .input-container {
    flex-direction: column;
    gap: 8px;
  }
  
  .input-actions {
    align-self: flex-end;
  }
}
</style>