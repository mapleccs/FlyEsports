<template>
  <div class="bp-room-detail">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <a-spin size="large" />
    </div>

    <!-- 房间不存在 -->
    <div v-else-if="!room" class="not-found-container">
      <a-result
        status="404"
        title="房间不存在"
        sub-title="请检查房间ID是否正确，或房间已被删除"
      >
        <template #extra>
          <a-button type="primary" @click="router.push('/matches/bp-rooms')">
            返回房间列表
          </a-button>
        </template>
      </a-result>
    </div>

    <!-- 房间详情 -->
    <div v-else class="room-content">
      <!-- 房间头部 -->
      <div class="room-header">
        <div class="header-left">
          <a-button @click="router.back()" class="back-button">
            <template #icon>
              <ArrowLeftOutlined />
            </template>
            返回
          </a-button>
          <div class="room-title-section">
            <h1 class="room-title">{{ room.name }}</h1>
            <div class="room-meta">
              <a-tag :color="statusColor" class="status-tag">
                {{ statusText }}
              </a-tag>
              <a-tag color="blue">{{ roomTypeText }}</a-tag>
              <span class="room-id">ID: {{ room.id }}</span>
            </div>
          </div>
        </div>
        
        <div class="header-actions">
          <!-- 房间管理员操作 -->
          <template v-if="isCreator">
            <a-button
              v-if="canStart"
              type="primary"
              size="large"
              @click="handleStartRoom"
              :loading="actionLoading"
            >
              <template #icon>
                <PlayCircleOutlined />
              </template>
              开始BP
            </a-button>
            
            <a-button
              v-if="room.status === 'waiting'"
              danger
              @click="handleDeleteRoom"
              :loading="actionLoading"
            >
              <template #icon>
                <DeleteOutlined />
              </template>
              删除房间
            </a-button>
          </template>

          <!-- 参与者操作 -->
          <template v-else-if="isParticipant">
            <a-button
              danger
              @click="handleLeaveRoom"
              :loading="actionLoading"
            >
              <template #icon>
                <LogoutOutlined />
              </template>
              离开房间
            </a-button>
          </template>

          <!-- 非参与者操作 -->
          <template v-else-if="canJoin">
            <a-button
              type="primary"
              size="large"
              @click="router.push(`/matches/bp-room/${roomId}/join`)"
            >
              <template #icon>
                <LoginOutlined />
              </template>
              加入房间
            </a-button>
          </template>
        </div>
      </div>

      <!-- 房间信息卡片 -->
      <div class="room-info-grid">
        <!-- 基本信息 -->
        <a-card title="房间信息" class="info-card">
          <div class="info-content">
            <div v-if="room.description" class="info-item">
              <strong>描述：</strong>
              <p>{{ room.description }}</p>
            </div>
            
            <div class="info-item">
              <strong>创建者：</strong>
              <span>{{ room.creator?.username || '未知' }}</span>
            </div>
            
            <div class="info-item">
              <strong>创建时间：</strong>
              <span>{{ formatTime(room.created_at) }}</span>
            </div>
            
            <div v-if="room.started_at" class="info-item">
              <strong>开始时间：</strong>
              <span>{{ formatTime(room.started_at) }}</span>
            </div>
            
            <div v-if="room.completed_at" class="info-item">
              <strong>完成时间：</strong>
              <span>{{ formatTime(room.completed_at) }}</span>
            </div>
          </div>
        </a-card>

        <!-- BP配置 -->
        <a-card title="BP配置" class="info-card">
          <div class="config-content">
            <div class="config-row">
              <div class="config-item">
                <div class="config-label">Ban轮数</div>
                <div class="config-value">{{ room.bp_config.ban_count }}</div>
              </div>
              <div class="config-item">
                <div class="config-label">Pick轮数</div>
                <div class="config-value">{{ room.bp_config.pick_count }}</div>
              </div>
            </div>
            
            <div class="config-row">
              <div class="config-item">
                <div class="config-label">Ban时间</div>
                <div class="config-value">{{ room.bp_config.ban_time }}秒</div>
              </div>
              <div class="config-item">
                <div class="config-label">Pick时间</div>
                <div class="config-value">{{ room.bp_config.pick_time }}秒</div>
              </div>
            </div>
            
            <div class="config-row">
              <div class="config-item">
                <div class="config-label">边路选择</div>
                <div class="config-value">{{ sideSelectionText }}</div>
              </div>
            </div>
            
            <div class="config-features">
              <a-tag v-if="room.bp_config.enable_swap" color="green">允许交换</a-tag>
              <a-tag v-else color="red">禁止交换</a-tag>
              
              <a-tag v-if="room.bp_config.enable_chat" color="green">启用聊天</a-tag>
              <a-tag v-else color="red">禁用聊天</a-tag>
            </div>
          </div>
        </a-card>
      </div>

      <!-- 参与者管理 -->
      <a-card title="参与者管理" class="participants-card">
        <div class="participants-header">
          <div class="participants-count">
            <TeamOutlined />
            <span>当前参与者 ({{ activeParticipants.length }}/10)</span>
          </div>
          
          <div class="participants-actions">
            <a-button @click="refreshRoom" :loading="loading">
              <template #icon>
                <ReloadOutlined />
              </template>
              刷新
            </a-button>
          </div>
        </div>

        <div class="teams-container">
          <!-- 蓝色方 -->
          <div class="team-section blue-team">
            <div class="team-header">
              <h3>蓝色方 ({{ blueSideParticipants.length }}/5)</h3>
              <div class="team-actions" v-if="isCreator">
                <a-button size="small" @click="balanceTeams">
                  <template #icon>
                    <SwapOutlined />
                  </template>
                  平衡队伍
                </a-button>
              </div>
            </div>
            
            <div class="team-members">
              <ParticipantItem
                v-for="participant in blueSideParticipants"
                :key="participant.id"
                :participant="participant"
                :is-creator="isCreator"
                :current-user-id="authStore.user?.id"
                @update-participant="handleUpdateParticipant"
                @remove-participant="handleRemoveParticipant"
              />
              
              <!-- 空位展示 -->
              <div
                v-for="i in (5 - blueSideParticipants.length)"
                :key="`blue-empty-${i}`"
                class="empty-slot"
              >
                <UserAddOutlined />
                <span>等待加入</span>
              </div>
            </div>
          </div>

          <!-- 红色方 -->
          <div class="team-section red-team">
            <div class="team-header">
              <h3>红色方 ({{ redSideParticipants.length }}/5)</h3>
            </div>
            
            <div class="team-members">
              <ParticipantItem
                v-for="participant in redSideParticipants"
                :key="participant.id"
                :participant="participant"
                :is-creator="isCreator"
                :current-user-id="authStore.user?.id"
                @update-participant="handleUpdateParticipant"
                @remove-participant="handleRemoveParticipant"
              />
              
              <!-- 空位展示 -->
              <div
                v-for="i in (5 - redSideParticipants.length)"
                :key="`red-empty-${i}`"
                class="empty-slot"
              >
                <UserAddOutlined />
                <span>等待加入</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 观战者 -->
        <div v-if="observers.length > 0" class="observers-section">
          <h4>观战者 ({{ observers.length }})</h4>
          <div class="observers-list">
            <ParticipantItem
              v-for="observer in observers"
              :key="observer.id"
              :participant="observer"
              :is-creator="isCreator"
              :current-user-id="authStore.user?.id"
              @update-participant="handleUpdateParticipant"
              @remove-participant="handleRemoveParticipant"
            />
          </div>
        </div>
      </a-card>

      <!-- 房间聊天 -->
      <div v-if="room.bp_config.enable_chat" class="chat-section">
        <a-card title="房间聊天" class="chat-card">
          <RoomChat
            :room-id="roomId"
            :can-send-message="isParticipant && room.bp_config.enable_chat"
            :participants="activeParticipants"
            @message-sent="handleChatMessageSent"
          />
        </a-card>
      </div>

      <!-- 进入BP界面按钮 -->
      <div v-if="room.status === 'bp_active'" class="bp-action-section">
        <a-card>
          <div class="bp-action-content">
            <div class="bp-action-info">
              <PlayCircleOutlined class="bp-icon" />
              <div>
                <h3>BP阶段进行中</h3>
                <p>点击下方按钮进入BP界面进行英雄选择</p>
              </div>
            </div>
            <a-button
              type="primary"
              size="large"
              @click="enterBPInterface"
              class="enter-bp-button"
            >
              进入BP界面
            </a-button>
          </div>
        </a-card>
      </div>
    </div>

    <!-- 通知中心 -->
    <NotificationCenter ref="notificationCenter" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  ArrowLeftOutlined,
  PlayCircleOutlined,
  DeleteOutlined,
  LogoutOutlined,
  LoginOutlined,
  TeamOutlined,
  ReloadOutlined,
  SwapOutlined,
  UserAddOutlined
} from '@ant-design/icons-vue'
import { Modal, message } from 'ant-design-vue'
import { useBPRoomStore } from '@/shared/stores/bp_room'
import { useAuthStore } from '@/shared/stores/auth'
import type { BPRoom, BPRoomParticipant, UpdateParticipantRequest } from '@/shared/api/bp_rooms'
import ParticipantItem from '../components/ParticipantItem.vue'
import RoomChat from '../components/RoomChat.vue'
import NotificationCenter from '@/shared/components/NotificationCenter.vue'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'

dayjs.extend(relativeTime)
dayjs.locale('zh-cn')

// Stores & Router
const bpRoomStore = useBPRoomStore()
const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()

// 响应式数据
const loading = ref(false)
const actionLoading = ref(false)
const refreshInterval = ref<number | null>(null)
const wsConnected = ref(false)
const wsReconnecting = ref(false)
const reconnectAttempts = ref(0)
const notificationCenter = ref()

const roomId = computed(() => route.params.roomId as string)
const room = computed(() => bpRoomStore.currentRoom)

// 计算属性
const activeParticipants = computed(() => 
  room.value?.participants.filter(p => p.is_active) || []
)

const blueSideParticipants = computed(() =>
  activeParticipants.value.filter(p => p.team_side === 'blue')
)

const redSideParticipants = computed(() =>
  activeParticipants.value.filter(p => p.team_side === 'red')
)

const observers = computed(() =>
  activeParticipants.value.filter(p => p.role === 'observer')
)

const isCreator = computed(() =>
  authStore.user && room.value && room.value.creator_user_id === authStore.user.id
)

const isParticipant = computed(() =>
  authStore.user && activeParticipants.value.some(p => p.user_id === authStore.user!.id)
)

const canJoin = computed(() => {
  if (!room.value) return false
  return ['waiting', 'ready'].includes(room.value.status) && activeParticipants.value.length < 10
})

const canStart = computed(() => {
  if (!room.value) return false
  return room.value.status === 'ready' || 
    (room.value.status === 'waiting' && blueSideParticipants.value.length > 0 && redSideParticipants.value.length > 0)
})

const statusText = computed(() => {
  if (!room.value) return ''
  const statusMap = {
    waiting: '等待中',
    ready: '准备中',
    bp_active: '进行中',
    completed: '已完成',
    archived: '已归档'
  }
  return statusMap[room.value.status] || room.value.status
})

const statusColor = computed(() => {
  if (!room.value) return 'default'
  const colorMap = {
    waiting: 'orange',
    ready: 'blue',
    bp_active: 'green',
    completed: 'purple',
    archived: 'default'
  }
  return colorMap[room.value.status] || 'default'
})

const roomTypeText = computed(() => {
  if (!room.value) return ''
  const typeMap = {
    custom: '自定义',
    tournament: '赛事',
    ranked: '排位',
    practice: '练习'
  }
  return typeMap[room.value.room_type] || room.value.room_type
})

const sideSelectionText = computed(() => {
  if (!room.value) return ''
  const selectionMap = {
    random: '随机分配',
    blue_first: '蓝色方优先',
    red_first: '红色方优先'
  }
  return selectionMap[room.value.bp_config.side_selection] || room.value.bp_config.side_selection
})

// 方法
const formatTime = (timeStr: string) => {
  try {
    return dayjs(timeStr).fromNow()
  } catch {
    return '未知'
  }
}

const loadRoom = async () => {
  loading.value = true
  try {
    await bpRoomStore.fetchRoom(roomId.value)
  } catch (error) {
    console.error('加载房间失败:', error)
  } finally {
    loading.value = false
  }
}

const refreshRoom = async () => {
  await loadRoom()
}

const handleStartRoom = async () => {
  actionLoading.value = true
  try {
    const success = await bpRoomStore.startRoom(roomId.value)
    if (success) {
      message.success('房间已开始')
      await refreshRoom()
    }
  } finally {
    actionLoading.value = false
  }
}

const handleDeleteRoom = () => {
  Modal.confirm({
    title: '确认删除',
    content: '确定要删除这个房间吗？此操作无法撤销。',
    okText: '确认删除',
    okType: 'danger',
    cancelText: '取消',
    async onOk() {
      actionLoading.value = true
      try {
        const success = await bpRoomStore.deleteRoom(roomId.value)
        if (success) {
          message.success('房间已删除')
          router.push('/matches/bp-rooms')
        }
      } finally {
        actionLoading.value = false
      }
    }
  })
}

const handleLeaveRoom = () => {
  Modal.confirm({
    title: '确认离开',
    content: '确定要离开这个房间吗？',
    okText: '确认离开',
    okType: 'danger',
    cancelText: '取消',
    async onOk() {
      actionLoading.value = true
      try {
        const success = await bpRoomStore.leaveRoom(roomId.value)
        if (success) {
          message.success('已离开房间')
          router.push('/matches/bp-rooms')
        }
      } finally {
        actionLoading.value = false
      }
    }
  })
}

const handleUpdateParticipant = async (
  participant: BPRoomParticipant, 
  updates: UpdateParticipantRequest
) => {
  try {
    // TODO: 调用API更新参与者
    console.log('更新参与者:', participant, updates)
    bpRoomStore.updateParticipantStatus(roomId.value, participant.user_id, updates)
    message.success('参与者信息已更新')
  } catch (error) {
    message.error('更新参与者信息失败')
  }
}

const handleRemoveParticipant = async (participant: BPRoomParticipant) => {
  Modal.confirm({
    title: '确认移除',
    content: `确定要移除参与者 ${participant.user?.username} 吗？`,
    okText: '确认移除',
    okType: 'danger',
    cancelText: '取消',
    async onOk() {
      try {
        // TODO: 调用API移除参与者
        console.log('移除参与者:', participant)
        message.success('参与者已移除')
        await refreshRoom()
      } catch (error) {
        message.error('移除参与者失败')
      }
    }
  })
}

const balanceTeams = () => {
  // TODO: 实现队伍平衡算法
  message.info('队伍平衡功能开发中')
}

const enterBPInterface = () => {
  // 导航到BP界面
  router.push(`/tournaments/0/matches/0/bp?roomId=${roomId.value}`)
}

const handleChatMessageSent = (messageText: string) => {
  // 聊天消息已发送，这里可以做一些额外处理
  console.log('聊天消息已发送:', messageText)
}

// WebSocket初始化和事件处理
const initializeWebSocket = async () => {
  try {
    if (!authStore.token) {
      console.warn('未登录，无法建立WebSocket连接')
      return
    }

    wsReconnecting.value = true
    
    // 连接WebSocket（如果尚未连接）
    if (!websocketStore.isConnected) {
      await websocketStore.connectBPRoom(roomId.value)
    }
    
    // 设置房间事件处理器
    websocketStore.setRoomEventHandlers({
      onRoomStatusChanged: handleRoomStatusChanged,
      onParticipantJoined: handleParticipantJoined,
      onParticipantLeft: handleParticipantLeft,
      onParticipantUpdated: handleParticipantUpdated,
      onRoomDeleted: handleRoomDeleted,
      onChatMessage: handleChatMessage,
      onNotification: handleNotification
    })
    
    wsConnected.value = true
    wsReconnecting.value = false
    reconnectAttempts.value = 0
    console.log('WebSocket房间连接已建立')
    
    // 显示连接成功通知
    if (notificationCenter.value && reconnectAttempts.value > 0) {
      notificationCenter.value.addNotification({
        type: 'success',
        title: '重连成功',
        message: '实时连接已恢复',
        duration: 2000
      })
    }
    
  } catch (error) {
    console.error('WebSocket连接失败:', error)
    wsConnected.value = false
    wsReconnecting.value = false
    
    // 设置自动重连逻辑
    const maxAttempts = 5
    if (reconnectAttempts.value < maxAttempts) {
      reconnectAttempts.value++
      const delay = Math.min(3000 * reconnectAttempts.value, 15000) // 指数退避，最大15秒
      
      console.log(`WebSocket重连尝试 ${reconnectAttempts.value}/${maxAttempts}，${delay}ms后重试`)
      
      setTimeout(() => {
        if (!wsConnected.value) {
          initializeWebSocket()
        }
      }, delay)
      
      // 显示重连通知
      if (notificationCenter.value) {
        notificationCenter.value.addNotification({
          type: 'warning',
          title: '连接断开',
          message: `正在尝试重连 (${reconnectAttempts.value}/${maxAttempts})`,
          duration: 3000
        })
      }
    } else {
      // 达到最大重连次数，显示手动重连提示
      if (notificationCenter.value) {
        notificationCenter.value.addNotification({
          type: 'error',
          title: '连接失败',
          message: '无法建立实时连接，请检查网络或手动重连',
          duration: 5000,
          actionText: '手动重连',
          onAction: handleManualReconnect
        })
      }
    }
  }
}

const handleManualReconnect = () => {
  reconnectAttempts.value = 0
  wsConnected.value = false
  wsReconnecting.value = false
  
  if (notificationCenter.value) {
    notificationCenter.value.addNotification({
      type: 'info',
      message: '正在尝试重新连接...',
      duration: 2000
    })
  }
  
  initializeWebSocket()
}

const disconnectWebSocket = () => {
  websocketStore.disconnectBPRoom()
  wsConnected.value = false
  wsReconnecting.value = false
}

// WebSocket事件处理器
const handleRoomStatusChanged = (data: any) => {
  console.log('房间状态变更:', data)
  if (room.value) {
    room.value.status = data.new_status
  }
  
  // 使用通知中心显示状态变更
  if (notificationCenter.value) {
    const statusNames = {
      waiting: '等待中',
      ready: '准备中', 
      bp_active: '进行中',
      completed: '已完成'
    }
    
    const newStatusName = statusNames[data.new_status] || data.new_status
    notificationCenter.value.addNotification({
      type: 'info',
      title: '房间状态更新',
      message: `房间状态已更新为: ${newStatusName}`,
      duration: 3000
    })
  }
}

const handleParticipantJoined = (data: any) => {
  console.log('参与者加入:', data)
  
  // 更新本地参与者列表
  if (room.value && data.participant) {
    const existingIndex = room.value.participants.findIndex(p => p.id === data.participant.id)
    if (existingIndex >= 0) {
      room.value.participants[existingIndex] = data.participant
    } else {
      room.value.participants.push(data.participant)
    }
  }
  
  // 显示加入通知
  if (data.participant.user && notificationCenter.value) {
    notificationCenter.value.addNotification({
      type: 'success',
      title: '新成员加入',
      message: `${data.participant.user.username} 加入了房间`,
      duration: 3000
    })
  }
}

const handleParticipantLeft = (data: any) => {
  console.log('参与者离开:', data)
  
  // 更新本地参与者列表
  if (room.value && data.participant) {
    const participantIndex = room.value.participants.findIndex(p => p.id === data.participant.id)
    if (participantIndex >= 0) {
      room.value.participants[participantIndex].is_active = false
    }
  }
  
  // 显示离开通知
  if (data.participant.user && notificationCenter.value) {
    notificationCenter.value.addNotification({
      type: 'info',
      title: '成员离开',
      message: `${data.participant.user.username} 离开了房间`,
      duration: 3000
    })
  }
}

const handleParticipantUpdated = (data: any) => {
  console.log('参与者信息更新:', data)
  
  // 更新本地参与者信息
  if (room.value && data.participant) {
    const participantIndex = room.value.participants.findIndex(p => p.id === data.participant.id)
    if (participantIndex >= 0) {
      room.value.participants[participantIndex] = data.participant
    }
  }
  
  // 显示更新通知（仅显示重要变更）
  if (data.changes && notificationCenter.value) {
    const messages = []
    
    if (data.changes.team_side) {
      const teamNames = { blue: '蓝色方', red: '红色方', null: '观战席' }
      const teamName = teamNames[data.changes.team_side] || '未知队伍'
      messages.push(`移动到 ${teamName}`)
    }
    
    if (data.changes.is_ready !== undefined) {
      const readyStatus = data.changes.is_ready ? '已准备' : '取消准备'
      messages.push(readyStatus)
    }
    
    if (messages.length > 0) {
      const username = data.participant.user?.username || '参与者'
      notificationCenter.value.addNotification({
        type: 'info',
        title: '状态更新',
        message: `${username} ${messages.join(' 并 ')}`,
        duration: 3000
      })
    }
  }
}

const handleRoomDeleted = (data: any) => {
  console.log('房间被删除:', data)
  
  if (notificationCenter.value) {
    notificationCenter.value.addNotification({
      type: 'warning',
      title: '房间已删除',
      message: '当前房间已被管理员删除，即将返回房间列表',
      duration: 5000
    })
  }
  
  setTimeout(() => {
    router.push('/matches/bp-rooms')
  }, 2000)
}

const handleChatMessage = (data: any) => {
  console.log('收到聊天消息:', data)
  
  // 系统消息显示为通知
  if (data.message_type === 'system' && notificationCenter.value) {
    notificationCenter.value.addNotification({
      type: 'info',
      message: data.message,
      duration: 3000
    })
  }
}

const handleNotification = (data: any) => {
  console.log('收到房间通知:', data)
  
  // 使用通知中心显示通知
  if (notificationCenter.value) {
    notificationCenter.value.addNotification({
      type: data.notification_type || 'info',
      title: data.title || '房间通知',
      message: data.message,
      duration: 5000,
      data: data.data
    })
  }
}

// 生命周期
onMounted(async () => {
  if (!authStore.isAuthenticated) {
    router.push('/auth/login')
    return
  }

  await loadRoom()
  
  // 初始化WebSocket连接
  await initializeWebSocket()

  // 设置定时刷新（作为WebSocket的备用机制）
  refreshInterval.value = window.setInterval(refreshRoom, 30000) // 30秒刷新一次，频率降低
})

onUnmounted(() => {
  // 清理定时器
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
  }
  
  // 断开WebSocket连接
  disconnectWebSocket()
})
</script>

<style scoped>
.bp-room-detail {
  padding: 24px;
  background: #f5f5f5;
  min-height: 100vh;
}

.loading-container,
.not-found-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}

.room-content {
  max-width: 1400px;
  margin: 0 auto;
}

.room-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  background: white;
  padding: 24px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.header-left {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  flex: 1;
}

.back-button {
  margin-top: 4px;
}

.room-title {
  font-size: 28px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 8px 0;
}

.room-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.room-id {
  color: #6b7280;
  font-size: 14px;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.room-info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-bottom: 24px;
}

.info-card {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.info-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.info-item strong {
  color: #374151;
  margin-right: 8px;
}

.info-item p {
  margin: 4px 0 0 0;
  color: #6b7280;
  line-height: 1.5;
}

.config-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.config-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.config-item {
  text-align: center;
  padding: 12px;
  background: #f9fafb;
  border-radius: 6px;
}

.config-label {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 4px;
}

.config-value {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.config-features {
  display: flex;
  gap: 8px;
  justify-content: center;
  flex-wrap: wrap;
}

.participants-card {
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.participants-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e5e7eb;
}

.participants-count {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  font-size: 16px;
  color: #374151;
}

.teams-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-bottom: 24px;
}

.team-section {
  padding: 20px;
  border-radius: 8px;
  border: 2px solid transparent;
}

.blue-team {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border-color: #3b82f6;
}

.red-team {
  background: linear-gradient(135deg, #fef2f2 0%, #fecaca 100%);
  border-color: #ef4444;
}

.team-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.team-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.team-members {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.empty-slot {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.5);
  border: 2px dashed #d1d5db;
  border-radius: 6px;
  color: #9ca3af;
  font-size: 14px;
}

.observers-section {
  padding-top: 24px;
  border-top: 1px solid #e5e7eb;
}

.observers-section h4 {
  font-size: 16px;
  font-weight: 600;
  color: #374151;
  margin: 0 0 16px 0;
}

.observers-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 8px;
}

.bp-action-section {
  margin-bottom: 24px;
}

.bp-action-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px;
}

.bp-action-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.bp-icon {
  font-size: 32px;
  color: #52c41a;
}

.bp-action-info h3 {
  margin: 0 0 4px 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.bp-action-info p {
  margin: 0;
  color: #6b7280;
}

.enter-bp-button {
  height: 48px;
  padding: 0 32px;
  font-size: 16px;
  font-weight: 600;
}

.participants-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.connection-status {
  display: flex;
  align-items: center;
}

.chat-section {
  margin-bottom: 24px;
}

.chat-card {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.chat-card :deep(.ant-card-body) {
  padding: 0;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .room-info-grid,
  .teams-container {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .bp-room-detail {
    padding: 16px;
  }
  
  .room-header {
    flex-direction: column;
    gap: 16px;
  }
  
  .header-left {
    flex-direction: column;
    gap: 12px;
    width: 100%;
  }
  
  .header-actions {
    width: 100%;
    justify-content: flex-end;
  }
  
  .bp-action-content {
    flex-direction: column;
    gap: 16px;
    text-align: center;
  }
}
</style>