<template>
  <teleport to="body">
    <div class="notification-center">
      <!-- 通知容器 -->
      <div class="notifications-container" :class="positionClass">
        <transition-group
          name="notification"
          tag="div"
          class="notifications-list"
        >
          <div
            v-for="notification in visibleNotifications"
            :key="notification.id"
            class="notification-item"
            :class="[`notification-${notification.type}`, { paused: notification.paused }]"
            @mouseenter="pauseNotification(notification.id)"
            @mouseleave="resumeNotification(notification.id)"
          >
            <!-- 通知图标 -->
            <div class="notification-icon">
              <CheckCircleOutlined v-if="notification.type === 'success'" />
              <InfoCircleOutlined v-else-if="notification.type === 'info'" />
              <ExclamationCircleOutlined v-else-if="notification.type === 'warning'" />
              <CloseCircleOutlined v-else-if="notification.type === 'error'" />
              <NotificationOutlined v-else />
            </div>

            <!-- 通知内容 -->
            <div class="notification-content">
              <div v-if="notification.title" class="notification-title">
                {{ notification.title }}
              </div>
              <div class="notification-message">
                {{ notification.message }}
              </div>
              <div v-if="notification.timestamp" class="notification-time">
                {{ formatTime(notification.timestamp) }}
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="notification-actions">
              <a-button
                v-if="notification.actionText && notification.onAction"
                type="link"
                size="small"
                @click="handleAction(notification)"
              >
                {{ notification.actionText }}
              </a-button>
              
              <a-button
                type="text"
                size="small"
                @click="removeNotification(notification.id)"
                class="close-button"
              >
                <template #icon>
                  <CloseOutlined />
                </template>
              </a-button>
            </div>

            <!-- 进度条 -->
            <div
              v-if="notification.duration"
              class="notification-progress"
              :style="{ width: getProgressWidth(notification) }"
            ></div>
          </div>
        </transition-group>
      </div>
      
      <!-- 通知中心切换按钮 -->
      <div v-if="showToggle" class="notification-toggle" @click="toggleCenter">
        <a-badge :count="unreadCount" :offset="[-8, 8]">
          <a-button type="primary" shape="circle" size="large">
            <template #icon>
              <BellOutlined />
            </template>
          </a-button>
        </a-badge>
      </div>

      <!-- 通知历史面板 -->
      <div v-if="showHistory" class="notification-history" @click.self="closeHistory">
        <div class="history-panel">
          <div class="history-header">
            <h3>通知历史</h3>
            <div class="history-actions">
              <a-button size="small" @click="clearAllHistory">
                全部清除
              </a-button>
              <a-button size="small" type="text" @click="closeHistory">
                <template #icon>
                  <CloseOutlined />
                </template>
              </a-button>
            </div>
          </div>
          
          <div class="history-content">
            <div v-if="allNotifications.length === 0" class="empty-history">
              <BellOutlined />
              <p>暂无通知记录</p>
            </div>
            
            <div
              v-for="notification in allNotifications"
              :key="notification.id"
              class="history-item"
              :class="{ unread: !notification.read }"
              @click="markAsRead(notification.id)"
            >
              <div class="history-icon">
                <CheckCircleOutlined v-if="notification.type === 'success'" />
                <InfoCircleOutlined v-else-if="notification.type === 'info'" />
                <ExclamationCircleOutlined v-else-if="notification.type === 'warning'" />
                <CloseCircleOutlined v-else-if="notification.type === 'error'" />
                <NotificationOutlined v-else />
              </div>
              
              <div class="history-content-text">
                <div v-if="notification.title" class="history-title">
                  {{ notification.title }}
                </div>
                <div class="history-message">
                  {{ notification.message }}
                </div>
                <div class="history-time">
                  {{ formatTime(notification.timestamp) }}
                </div>
              </div>
              
              <div v-if="!notification.read" class="unread-dot"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  CheckCircleOutlined,
  InfoCircleOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined,
  NotificationOutlined,
  CloseOutlined,
  BellOutlined
} from '@ant-design/icons-vue'
import dayjs from 'dayjs'

// Props
interface Props {
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left'
  maxVisible?: number
  defaultDuration?: number
  showToggle?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  position: 'top-right',
  maxVisible: 5,
  defaultDuration: 4000,
  showToggle: true
})

// 通知接口
export interface NotificationData {
  id?: string
  type: 'success' | 'info' | 'warning' | 'error'
  title?: string
  message: string
  duration?: number
  actionText?: string
  onAction?: () => void
  data?: any
  timestamp?: Date
  read?: boolean
  paused?: boolean
  progressStartTime?: number
}

// 响应式数据
const allNotifications = ref<NotificationData[]>([])
const showHistory = ref(false)
const timers = ref<Map<string, number>>(new Map())

// 计算属性
const positionClass = computed(() => `position-${props.position}`)

const visibleNotifications = computed(() =>
  allNotifications.value
    .filter(n => !n.read)
    .slice(0, props.maxVisible)
)

const unreadCount = computed(() =>
  allNotifications.value.filter(n => !n.read).length
)

// 方法
const generateId = () => `notification-${Date.now()}-${Math.random()}`

const addNotification = (data: NotificationData) => {
  const notification: NotificationData = {
    id: generateId(),
    type: 'info',
    duration: props.defaultDuration,
    timestamp: new Date(),
    read: false,
    paused: false,
    ...data
  }

  allNotifications.value.unshift(notification)

  // 自动移除定时器
  if (notification.duration && notification.duration > 0) {
    notification.progressStartTime = Date.now()
    startRemovalTimer(notification.id!, notification.duration)
  }

  // 播放通知音效
  playNotificationSound(notification.type)

  return notification.id
}

const removeNotification = (id: string) => {
  const index = allNotifications.value.findIndex(n => n.id === id)
  if (index > -1) {
    allNotifications.value.splice(index, 1)
    clearTimer(id)
  }
}

const pauseNotification = (id: string) => {
  const notification = allNotifications.value.find(n => n.id === id)
  if (notification) {
    notification.paused = true
    clearTimer(id)
  }
}

const resumeNotification = (id: string) => {
  const notification = allNotifications.value.find(n => n.id === id)
  if (notification && notification.duration) {
    notification.paused = false
    const elapsed = Date.now() - (notification.progressStartTime || Date.now())
    const remaining = Math.max(0, notification.duration - elapsed)
    
    if (remaining > 0) {
      startRemovalTimer(id, remaining)
    } else {
      removeNotification(id)
    }
  }
}

const startRemovalTimer = (id: string, duration: number) => {
  clearTimer(id)
  const timer = window.setTimeout(() => {
    removeNotification(id)
  }, duration)
  timers.value.set(id, timer)
}

const clearTimer = (id: string) => {
  const timer = timers.value.get(id)
  if (timer) {
    clearTimeout(timer)
    timers.value.delete(id)
  }
}

const handleAction = (notification: NotificationData) => {
  if (notification.onAction) {
    notification.onAction()
  }
  removeNotification(notification.id!)
}

const markAsRead = (id: string) => {
  const notification = allNotifications.value.find(n => n.id === id)
  if (notification) {
    notification.read = true
  }
}

const toggleCenter = () => {
  showHistory.value = !showHistory.value
}

const closeHistory = () => {
  showHistory.value = false
}

const clearAllHistory = () => {
  allNotifications.value = []
  timers.value.clear()
}

const formatTime = (date: Date) => {
  return dayjs(date).format('HH:mm:ss')
}

const getProgressWidth = (notification: NotificationData) => {
  if (!notification.duration || !notification.progressStartTime || notification.paused) {
    return '100%'
  }
  
  const elapsed = Date.now() - notification.progressStartTime
  const progress = Math.max(0, 1 - elapsed / notification.duration)
  return `${progress * 100}%`
}

const playNotificationSound = (type: string) => {
  try {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)()
    const oscillator = audioContext.createOscillator()
    const gainNode = audioContext.createGain()
    
    oscillator.connect(gainNode)
    gainNode.connect(audioContext.destination)
    
    // 不同类型的通知使用不同音调
    const frequencies = {
      success: 600,
      info: 800,
      warning: 700,
      error: 400
    }
    
    oscillator.frequency.setValueAtTime(frequencies[type] || 800, audioContext.currentTime)
    gainNode.gain.setValueAtTime(0.1, audioContext.currentTime)
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2)
    
    oscillator.start(audioContext.currentTime)
    oscillator.stop(audioContext.currentTime + 0.2)
  } catch (error) {
    console.warn('无法播放通知音效:', error)
  }
}

// 暴露方法给父组件
defineExpose({
  addNotification,
  removeNotification,
  clearAllHistory
})

// 生命周期
onUnmounted(() => {
  timers.value.forEach(timer => clearTimeout(timer))
  timers.value.clear()
})
</script>

<style scoped>
.notification-center {
  position: fixed;
  z-index: 9999;
  pointer-events: none;
}

.notifications-container {
  position: fixed;
  z-index: 9999;
  pointer-events: none;
  max-width: 400px;
  width: 100%;
}

.position-top-right {
  top: 20px;
  right: 20px;
}

.position-top-left {
  top: 20px;
  left: 20px;
}

.position-bottom-right {
  bottom: 20px;
  right: 20px;
}

.position-bottom-left {
  bottom: 20px;
  left: 20px;
}

.notifications-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.notification-item {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border-left: 4px solid #d1d5db;
  pointer-events: all;
  overflow: hidden;
}

.notification-success {
  border-left-color: #10b981;
}

.notification-info {
  border-left-color: #3b82f6;
}

.notification-warning {
  border-left-color: #f59e0b;
}

.notification-error {
  border-left-color: #ef4444;
}

.notification-icon {
  font-size: 20px;
  margin-top: 2px;
  flex-shrink: 0;
}

.notification-success .notification-icon {
  color: #10b981;
}

.notification-info .notification-icon {
  color: #3b82f6;
}

.notification-warning .notification-icon {
  color: #f59e0b;
}

.notification-error .notification-icon {
  color: #ef4444;
}

.notification-content {
  flex: 1;
  min-width: 0;
}

.notification-title {
  font-weight: 600;
  font-size: 14px;
  color: #111827;
  margin-bottom: 4px;
}

.notification-message {
  font-size: 13px;
  color: #4b5563;
  line-height: 1.4;
  word-wrap: break-word;
}

.notification-time {
  font-size: 11px;
  color: #9ca3af;
  margin-top: 4px;
}

.notification-actions {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  flex-shrink: 0;
}

.close-button {
  width: 20px;
  height: 20px;
  min-width: 20px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.notification-progress {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 2px;
  background: #3b82f6;
  transition: width 0.1s linear;
}

.notification-success .notification-progress {
  background: #10b981;
}

.notification-warning .notification-progress {
  background: #f59e0b;
}

.notification-error .notification-progress {
  background: #ef4444;
}

.notification-item.paused .notification-progress {
  transition: none;
}

.notification-toggle {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 9998;
  pointer-events: all;
}

.notification-history {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 9997;
  pointer-events: all;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.history-panel {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  width: 100%;
  max-width: 500px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px 16px;
  border-bottom: 1px solid #e5e7eb;
}

.history-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #111827;
}

.history-actions {
  display: flex;
  gap: 8px;
}

.history-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px 0;
}

.empty-history {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #9ca3af;
}

.empty-history .anticon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.history-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 24px;
  cursor: pointer;
  transition: background-color 0.2s ease;
  position: relative;
}

.history-item:hover {
  background: #f9fafb;
}

.history-item.unread {
  background: #eff6ff;
}

.history-icon {
  font-size: 16px;
  margin-top: 2px;
  flex-shrink: 0;
}

.history-content-text {
  flex: 1;
  min-width: 0;
}

.history-title {
  font-weight: 500;
  font-size: 13px;
  color: #111827;
  margin-bottom: 2px;
}

.history-message {
  font-size: 12px;
  color: #4b5563;
  line-height: 1.4;
  word-wrap: break-word;
}

.history-time {
  font-size: 10px;
  color: #9ca3af;
  margin-top: 2px;
}

.unread-dot {
  width: 8px;
  height: 8px;
  background: #3b82f6;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 6px;
}

/* 过渡动画 */
.notification-enter-active,
.notification-leave-active {
  transition: all 0.3s ease;
}

.notification-enter-from {
  opacity: 0;
  transform: translateX(100%) scale(0.95);
}

.notification-leave-to {
  opacity: 0;
  transform: translateX(100%) scale(0.95);
}

.notification-move {
  transition: transform 0.3s ease;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .notifications-container {
    left: 10px;
    right: 10px;
    max-width: none;
  }
  
  .position-top-right,
  .position-top-left {
    top: 10px;
  }
  
  .position-bottom-right,
  .position-bottom-left {
    bottom: 80px;
  }
  
  .notification-item {
    padding: 12px;
  }
  
  .notification-toggle {
    bottom: 10px;
    right: 10px;
  }
  
  .notification-history {
    padding: 10px;
  }
  
  .history-panel {
    max-height: 90vh;
  }
}
</style>