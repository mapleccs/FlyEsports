<template>
  <a-card class="room-card" :class="`status-${room.status}`">
    <!-- 房间头部 -->
    <template #title>
      <div class="room-header">
        <div class="room-title">
          <h3>{{ room.name }}</h3>
          <a-tag :color="statusColor" class="status-tag">
            {{ statusText }}
          </a-tag>
        </div>
        <div class="room-type">
          <a-tag color="blue">{{ roomTypeText }}</a-tag>
        </div>
      </div>
    </template>

    <template #extra>
      <a-dropdown v-if="showManage && isCreator" placement="bottomRight">
        <a-button type="text" size="small">
          <template #icon>
            <MoreOutlined />
          </template>
        </a-button>
        <template #overlay>
          <a-menu>
            <a-menu-item key="start" v-if="canStart" @click="$emit('startRoom')">
              <PlayCircleOutlined />
              开始房间
            </a-menu-item>
            <a-menu-item key="delete" @click="handleDelete">
              <DeleteOutlined />
              删除房间
            </a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>
    </template>

    <!-- 房间信息 -->
    <div class="room-content">
      <!-- 描述 -->
      <div v-if="room.description" class="room-description">
        <p>{{ room.description }}</p>
      </div>

      <!-- 创建者信息 -->
      <div class="room-creator">
        <UserOutlined />
        <span>创建者：{{ room.creator?.username || '未知' }}</span>
      </div>

      <!-- 参与者信息 -->
      <div class="participants-section">
        <div class="participants-header">
          <TeamOutlined />
          <span>参与者 ({{ activeParticipants.length }}/10)</span>
        </div>
        
        <div class="teams-grid">
          <!-- 蓝色方 -->
          <div class="team-side blue-side">
            <div class="team-header">
              <div class="team-label">蓝色方</div>
              <div class="team-count">({{ blueSideParticipants.length }}/5)</div>
            </div>
            <div class="team-members">
              <div
                v-for="participant in blueSideParticipants"
                :key="participant.id"
                class="member-item"
                :class="{ ready: participant.is_ready }"
              >
                <a-avatar size="small" :src="getUserAvatar(participant.user)">
                  {{ participant.user?.username?.[0] || '?' }}
                </a-avatar>
                <span class="member-name">{{ participant.user?.username || '未知' }}</span>
                <a-tag size="small" :color="getRoleColor(participant.role)">
                  {{ getRoleText(participant.role) }}
                </a-tag>
              </div>
            </div>
          </div>

          <!-- 红色方 -->
          <div class="team-side red-side">
            <div class="team-header">
              <div class="team-label">红色方</div>
              <div class="team-count">({{ redSideParticipants.length }}/5)</div>
            </div>
            <div class="team-members">
              <div
                v-for="participant in redSideParticipants"
                :key="participant.id"
                class="member-item"
                :class="{ ready: participant.is_ready }"
              >
                <a-avatar size="small" :src="getUserAvatar(participant.user)">
                  {{ participant.user?.username?.[0] || '?' }}
                </a-avatar>
                <span class="member-name">{{ participant.user?.username || '未知' }}</span>
                <a-tag size="small" :color="getRoleColor(participant.role)">
                  {{ getRoleText(participant.role) }}
                </a-tag>
              </div>
            </div>
          </div>
        </div>

        <!-- 观战者 -->
        <div v-if="observers.length > 0" class="observers-section">
          <div class="observers-header">
            <EyeOutlined />
            <span>观战者 ({{ observers.length }})</span>
          </div>
          <div class="observers-list">
            <a-avatar-group :max-count="5">
              <a-avatar
                v-for="observer in observers"
                :key="observer.id"
                size="small"
                :src="getUserAvatar(observer.user)"
              >
                {{ observer.user?.username?.[0] || '?' }}
              </a-avatar>
            </a-avatar-group>
          </div>
        </div>
      </div>

      <!-- 房间配置 -->
      <div class="room-config">
        <div class="config-item">
          <ClockCircleOutlined />
          <span>Ban: {{ room.bp_config.ban_time }}s / Pick: {{ room.bp_config.pick_time }}s</span>
        </div>
        <div class="config-item">
          <SettingOutlined />
          <span>{{ room.bp_config.ban_count }}Ban {{ room.bp_config.pick_count }}Pick</span>
        </div>
      </div>

      <!-- 时间信息 -->
      <div class="room-time">
        <div class="time-item">
          <CalendarOutlined />
          <span>创建：{{ formatTime(room.created_at) }}</span>
        </div>
        <div v-if="room.started_at" class="time-item">
          <PlayCircleOutlined />
          <span>开始：{{ formatTime(room.started_at) }}</span>
        </div>
      </div>
    </div>

    <!-- 操作按钮 -->
    <template #actions>
      <div class="room-actions">
        <a-button @click="$emit('viewRoom')" size="small">
          <template #icon>
            <EyeOutlined />
          </template>
          查看详情
        </a-button>

        <a-button
          v-if="!isParticipant && canJoin"
          type="primary"
          @click="$emit('joinRoom')"
          size="small"
        >
          <template #icon>
            <LoginOutlined />
          </template>
          加入房间
        </a-button>

        <a-button
          v-if="isParticipant && !isCreator"
          danger
          @click="$emit('leaveRoom')"
          size="small"
        >
          <template #icon>
            <LogoutOutlined />
          </template>
          离开房间
        </a-button>
      </div>
    </template>
  </a-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Modal } from 'ant-design-vue'
import {
  MoreOutlined,
  PlayCircleOutlined,
  DeleteOutlined,
  UserOutlined,
  TeamOutlined,
  EyeOutlined,
  ClockCircleOutlined,
  SettingOutlined,
  CalendarOutlined,
  LoginOutlined,
  LogoutOutlined
} from '@ant-design/icons-vue'
import { useAuthStore } from '@/shared/stores/auth'
import type { BPRoom, BPRoomParticipant, User } from '@/shared/api/bp_rooms'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'

dayjs.extend(relativeTime)
dayjs.locale('zh-cn')

// Props
interface Props {
  room: BPRoom
  showManage?: boolean
}

const props = defineProps<Props>()

// Events
defineEmits<{
  joinRoom: []
  viewRoom: []
  leaveRoom: []
  deleteRoom: []
  startRoom: []
}>()

// Stores
const authStore = useAuthStore()

// 计算属性
const activeParticipants = computed(() => 
  props.room.participants.filter(p => p.is_active)
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
  authStore.user && props.room.creator_user_id === authStore.user.id
)

const isParticipant = computed(() =>
  authStore.user && activeParticipants.value.some(p => p.user_id === authStore.user!.id)
)

const canJoin = computed(() =>
  ['waiting', 'ready'].includes(props.room.status) && activeParticipants.value.length < 10
)

const canStart = computed(() =>
  props.room.status === 'ready' || 
  (props.room.status === 'waiting' && blueSideParticipants.value.length > 0 && redSideParticipants.value.length > 0)
)

const statusText = computed(() => {
  const statusMap = {
    waiting: '等待中',
    ready: '准备中',
    bp_active: '进行中',
    completed: '已完成',
    archived: '已归档'
  }
  return statusMap[props.room.status] || props.room.status
})

const statusColor = computed(() => {
  const colorMap = {
    waiting: 'orange',
    ready: 'blue',
    bp_active: 'green',
    completed: 'purple',
    archived: 'default'
  }
  return colorMap[props.room.status] || 'default'
})

const roomTypeText = computed(() => {
  const typeMap = {
    custom: '自定义',
    tournament: '赛事',
    ranked: '排位',
    practice: '练习'
  }
  return typeMap[props.room.room_type] || props.room.room_type
})

// 方法
const getUserAvatar = (user?: User) => {
  // 这里可以根据实际需求返回用户头像URL
  return undefined
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
    admin: '管理',
    commander: '指挥',
    player: '选手',
    observer: '观战'
  }
  return textMap[role] || role
}

const formatTime = (timeStr: string) => {
  try {
    return dayjs(timeStr).fromNow()
  } catch {
    return '未知'
  }
}

const handleDelete = () => {
  Modal.confirm({
    title: '确认删除',
    content: `确定要删除房间"${props.room.name}"吗？此操作无法撤销。`,
    okText: '确认删除',
    okType: 'danger',
    cancelText: '取消',
    onOk() {
      // 触发删除事件
      return new Promise((resolve) => {
        // 这里会触发父组件的删除方法
        resolve(true)
      })
    }
  })
}
</script>

<style scoped>
.room-card {
  height: 100%;
  transition: all 0.3s ease;
  border-radius: 8px;
  overflow: hidden;
}

.room-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.room-card.status-waiting {
  border-left: 4px solid #faad14;
}

.room-card.status-ready {
  border-left: 4px solid #1890ff;
}

.room-card.status-bp_active {
  border-left: 4px solid #52c41a;
}

.room-card.status-completed {
  border-left: 4px solid #722ed1;
}

.room-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.room-title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.room-title h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}

.status-tag {
  font-size: 12px;
}

.room-type {
  flex-shrink: 0;
}

.room-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.room-description p {
  margin: 0;
  color: #6b7280;
  font-size: 14px;
  line-height: 1.4;
}

.room-creator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #6b7280;
}

.participants-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.participants-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
  color: #374151;
}

.teams-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.team-side {
  padding: 12px;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
}

.blue-side {
  border-left: 3px solid #3b82f6;
  background: #eff6ff;
}

.red-side {
  border-left: 3px solid #ef4444;
  background: #fef2f2;
}

.team-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 500;
}

.team-label {
  color: #374151;
}

.team-count {
  color: #6b7280;
}

.team-members {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.member-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  font-size: 12px;
}

.member-item.ready {
  background: rgba(34, 197, 94, 0.1);
  border-radius: 4px;
  padding: 4px 6px;
}

.member-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 80px;
}

.observers-section {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #e5e7eb;
}

.observers-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 8px;
}

.room-config {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px;
  background: #f9fafb;
  border-radius: 4px;
}

.config-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #6b7280;
}

.room-time {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.time-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #9ca3af;
}

.room-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  width: 100%;
}
</style>