<template>
  <div class="participant-item" :class="{ ready: participant.is_ready, self: isSelf }">
    <div class="participant-main">
      <!-- 用户头像和信息 -->
      <div class="user-info">
        <a-avatar :size="40" :src="getUserAvatar()">
          {{ participant.user?.username?.[0] || '?' }}
        </a-avatar>
        
        <div class="user-details">
          <div class="username">
            {{ participant.user?.username || '未知用户' }}
            <a-tag v-if="isSelf" size="small" color="blue">我</a-tag>
          </div>
          <div class="user-meta">
            <a-tag :color="getRoleColor(participant.role)" size="small">
              {{ getRoleText(participant.role) }}
            </a-tag>
            <span class="join-time">{{ formatJoinTime() }}</span>
          </div>
        </div>
      </div>

      <!-- 状态指示器 -->
      <div class="status-indicators">
        <a-tooltip title="准备状态">
          <div class="ready-indicator" :class="{ ready: participant.is_ready }">
            <CheckCircleOutlined v-if="participant.is_ready" />
            <ClockCircleOutlined v-else />
          </div>
        </a-tooltip>
      </div>
    </div>

    <!-- 操作按钮 (仅管理员或自己) -->
    <div v-if="showActions" class="participant-actions">
      <a-dropdown placement="bottomRight" :trigger="['click']">
        <a-button type="text" size="small">
          <template #icon>
            <MoreOutlined />
          </template>
        </a-button>
        
        <template #overlay>
          <a-menu>
            <!-- 自己的操作 -->
            <template v-if="isSelf">
              <a-menu-item key="ready" @click="toggleReady">
                <CheckCircleOutlined />
                {{ participant.is_ready ? '取消准备' : '准备' }}
              </a-menu-item>
              
              <a-menu-item key="change-role" @click="showRoleModal = true">
                <UserSwitchOutlined />
                更改角色
              </a-menu-item>
              
              <a-menu-item key="change-team" @click="showTeamModal = true">
                <SwapOutlined />
                更换队伍
              </a-menu-item>
            </template>

            <!-- 管理员对其他人的操作 -->
            <template v-if="isCreator && !isSelf">
              <a-menu-item key="set-role" @click="showRoleModal = true">
                <UserSwitchOutlined />
                设置角色
              </a-menu-item>
              
              <a-menu-item key="move-team" @click="showTeamModal = true">
                <SwapOutlined />
                移动队伍
              </a-menu-item>
              
              <a-menu-item key="kick" @click="confirmKick" danger>
                <UserDeleteOutlined />
                踢出房间
              </a-menu-item>
            </template>
          </a-menu>
        </template>
      </a-dropdown>
    </div>

    <!-- 角色选择模态框 -->
    <a-modal
      v-model:visible="showRoleModal"
      title="选择角色"
      :footer="null"
      width="400px"
    >
      <div class="role-selection">
        <a-radio-group v-model:value="selectedRole" @change="handleRoleChange">
          <a-space direction="vertical">
            <a-radio value="commander">
              <CrownOutlined />
              指挥 - 负责BP决策
            </a-radio>
            <a-radio value="player">
              <UserOutlined />
              选手 - 参与比赛
            </a-radio>
            <a-radio value="observer">
              <EyeOutlined />
              观战 - 仅观看
            </a-radio>
          </a-space>
        </a-radio-group>
      </div>
    </a-modal>

    <!-- 队伍选择模态框 -->
    <a-modal
      v-model:visible="showTeamModal"
      title="选择队伍"
      :footer="null"
      width="400px"
    >
      <div class="team-selection">
        <a-radio-group v-model:value="selectedTeam" @change="handleTeamChange">
          <a-space direction="vertical">
            <a-radio value="blue">
              <div class="team-option blue">
                <div class="team-color"></div>
                蓝色方
              </div>
            </a-radio>
            <a-radio value="red">
              <div class="team-option red">
                <div class="team-color"></div>
                红色方
              </div>
            </a-radio>
            <a-radio :value="null">
              <div class="team-option observer">
                <EyeOutlined />
                观战席
              </div>
            </a-radio>
          </a-space>
        </a-radio-group>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Modal, message } from 'ant-design-vue'
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  MoreOutlined,
  UserSwitchOutlined,
  SwapOutlined,
  UserDeleteOutlined,
  CrownOutlined,
  UserOutlined,
  EyeOutlined
} from '@ant-design/icons-vue'
import type { BPRoomParticipant, UpdateParticipantRequest } from '@/shared/api/bp_rooms'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'

dayjs.extend(relativeTime)
dayjs.locale('zh-cn')

// Props
interface Props {
  participant: BPRoomParticipant
  isCreator: boolean
  currentUserId?: number
}

const props = defineProps<Props>()

// Events
const emit = defineEmits<{
  updateParticipant: [participant: BPRoomParticipant, updates: UpdateParticipantRequest]
  removeParticipant: [participant: BPRoomParticipant]
}>()

// 响应式数据
const showRoleModal = ref(false)
const showTeamModal = ref(false)
const selectedRole = ref(props.participant.role)
const selectedTeam = ref(props.participant.team_side)

// 计算属性
const isSelf = computed(() => 
  props.currentUserId && props.participant.user_id === props.currentUserId
)

const showActions = computed(() => 
  isSelf.value || props.isCreator
)

// 方法
const getUserAvatar = () => {
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
    admin: '管理员',
    commander: '指挥',
    player: '选手',
    observer: '观战'
  }
  return textMap[role] || role
}

const formatJoinTime = () => {
  try {
    return dayjs(props.participant.joined_at).fromNow()
  } catch {
    return '未知'
  }
}

const toggleReady = () => {
  emit('updateParticipant', props.participant, {
    is_ready: !props.participant.is_ready
  })
}

const handleRoleChange = () => {
  if (selectedRole.value !== props.participant.role) {
    emit('updateParticipant', props.participant, {
      role: selectedRole.value
    })
    showRoleModal.value = false
    message.success('角色已更新')
  }
}

const handleTeamChange = () => {
  if (selectedTeam.value !== props.participant.team_side) {
    emit('updateParticipant', props.participant, {
      team_side: selectedTeam.value || undefined
    })
    showTeamModal.value = false
    message.success('队伍已更换')
  }
}

const confirmKick = () => {
  Modal.confirm({
    title: '确认踢出',
    content: `确定要踢出 ${props.participant.user?.username} 吗？`,
    okText: '确认踢出',
    okType: 'danger',
    cancelText: '取消',
    onOk() {
      emit('removeParticipant', props.participant)
    }
  })
}
</script>

<style scoped>
.participant-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.participant-item:hover {
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.participant-item.ready {
  border-color: #52c41a;
  background: rgba(82, 196, 26, 0.05);
}

.participant-item.self {
  border-color: #1890ff;
  background: rgba(24, 144, 255, 0.05);
}

.participant-main {
  display: flex;
  align-items: center;
  flex: 1;
  gap: 12px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.user-details {
  flex: 1;
  min-width: 0;
}

.username {
  font-weight: 500;
  color: #1f2937;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.user-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.join-time {
  color: #9ca3af;
}

.status-indicators {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ready-indicator {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  background: #f3f4f6;
  color: #6b7280;
  transition: all 0.2s ease;
}

.ready-indicator.ready {
  background: #dcfce7;
  color: #16a34a;
}

.participant-actions {
  margin-left: 8px;
}

.role-selection,
.team-selection {
  padding: 16px 0;
}

.team-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.team-option .team-color {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.team-option.blue .team-color {
  background: #3b82f6;
}

.team-option.red .team-color {
  background: #ef4444;
}

:deep(.ant-radio-group) {
  width: 100%;
}

:deep(.ant-radio-wrapper) {
  width: 100%;
  padding: 8px 12px;
  border-radius: 6px;
  transition: all 0.2s ease;
}

:deep(.ant-radio-wrapper:hover) {
  background: #f9fafb;
}

:deep(.ant-radio-wrapper .ant-radio-checked) {
  border-color: #1890ff;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .participant-item {
    padding: 8px;
  }
  
  .user-info {
    gap: 8px;
  }
  
  .username {
    font-size: 14px;
  }
  
  .user-meta {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
}
</style>