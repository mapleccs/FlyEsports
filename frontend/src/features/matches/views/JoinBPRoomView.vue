<template>
  <div class="join-bp-room">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <a-spin size="large" />
    </div>

    <!-- 房间不存在或无法加入 -->
    <div v-else-if="!room || !canJoin" class="error-container">
      <a-result
        :status="!room ? '404' : 'warning'"
        :title="!room ? '房间不存在' : '无法加入房间'"
        :sub-title="!room ? '请检查房间ID是否正确' : getJoinErrorMessage()"
      >
        <template #extra>
          <a-space>
            <a-button @click="router.back()">返回</a-button>
            <a-button type="primary" @click="router.push('/matches/bp-rooms')">
              房间列表
            </a-button>
          </a-space>
        </template>
      </a-result>
    </div>

    <!-- 加入房间表单 -->
    <div v-else class="join-form-container">
      <div class="join-form-card">
        <!-- 房间信息预览 -->
        <div class="room-preview">
          <div class="room-header">
            <h2>{{ room.name }}</h2>
            <div class="room-meta">
              <a-tag :color="statusColor">{{ statusText }}</a-tag>
              <a-tag color="blue">{{ roomTypeText }}</a-tag>
            </div>
          </div>
          
          <div v-if="room.description" class="room-description">
            <p>{{ room.description }}</p>
          </div>
          
          <div class="room-stats">
            <div class="stat-item">
              <TeamOutlined />
              <span>{{ activeParticipants.length }}/10 参与者</span>
            </div>
            <div class="stat-item">
              <UserOutlined />
              <span>创建者：{{ room.creator?.username }}</span>
            </div>
          </div>
        </div>

        <!-- 加入选项表单 -->
        <div class="join-form">
          <h3>选择你的参与方式</h3>
          
          <a-form
            ref="formRef"
            :model="joinForm"
            layout="vertical"
            @finish="handleJoin"
          >
            <!-- 队伍选择 -->
            <a-form-item label="选择队伍" name="team_side">
              <div class="team-selection">
                <div class="team-options">
                  <div
                    class="team-option"
                    :class="{ 
                      selected: joinForm.team_side === 'blue',
                      disabled: blueSideParticipants.length >= 5
                    }"
                    @click="selectTeam('blue')"
                  >
                    <div class="team-header">
                      <div class="team-color blue"></div>
                      <span class="team-name">蓝色方</span>
                      <span class="team-count">({{ blueSideParticipants.length }}/5)</span>
                    </div>
                    
                    <div class="team-members">
                      <a-avatar-group :max-count="5" size="small">
                        <a-avatar
                          v-for="participant in blueSideParticipants"
                          :key="participant.id"
                          :title="participant.user?.username"
                        >
                          {{ participant.user?.username?.[0] || '?' }}
                        </a-avatar>
                      </a-avatar-group>
                    </div>
                    
                    <div v-if="blueSideParticipants.length >= 5" class="team-full">
                      队伍已满
                    </div>
                  </div>

                  <div
                    class="team-option"
                    :class="{ 
                      selected: joinForm.team_side === 'red',
                      disabled: redSideParticipants.length >= 5
                    }"
                    @click="selectTeam('red')"
                  >
                    <div class="team-header">
                      <div class="team-color red"></div>
                      <span class="team-name">红色方</span>
                      <span class="team-count">({{ redSideParticipants.length }}/5)</span>
                    </div>
                    
                    <div class="team-members">
                      <a-avatar-group :max-count="5" size="small">
                        <a-avatar
                          v-for="participant in redSideParticipants"
                          :key="participant.id"
                          :title="participant.user?.username"
                        >
                          {{ participant.user?.username?.[0] || '?' }}
                        </a-avatar>
                      </a-avatar-group>
                    </div>
                    
                    <div v-if="redSideParticipants.length >= 5" class="team-full">
                      队伍已满
                    </div>
                  </div>

                  <div
                    class="team-option observer"
                    :class="{ selected: joinForm.team_side === null }"
                    @click="selectTeam(null)"
                  >
                    <div class="team-header">
                      <EyeOutlined />
                      <span class="team-name">观战席</span>
                      <span class="team-count">({{ observers.length }})</span>
                    </div>
                    
                    <div class="observer-description">
                      仅观看BP过程，不参与选择
                    </div>
                  </div>
                </div>
              </div>
            </a-form-item>

            <!-- 角色选择 -->
            <a-form-item label="选择角色" name="role">
              <a-radio-group v-model:value="joinForm.role">
                <div class="role-options">
                  <a-radio 
                    value="commander" 
                    :disabled="!joinForm.team_side || hasCommander"
                  >
                    <div class="role-option">
                      <CrownOutlined />
                      <div class="role-info">
                        <div class="role-name">指挥</div>
                        <div class="role-desc">负责BP决策和指挥</div>
                      </div>
                    </div>
                  </a-radio>
                  
                  <a-radio value="player" :disabled="!joinForm.team_side">
                    <div class="role-option">
                      <UserOutlined />
                      <div class="role-info">
                        <div class="role-name">选手</div>
                        <div class="role-desc">参与比赛的队员</div>
                      </div>
                    </div>
                  </a-radio>
                  
                  <a-radio value="observer">
                    <div class="role-option">
                      <EyeOutlined />
                      <div class="role-info">
                        <div class="role-name">观战</div>
                        <div class="role-desc">观看BP过程</div>
                      </div>
                    </div>
                  </a-radio>
                </div>
              </a-radio-group>
            </a-form-item>

            <!-- 提示信息 -->
            <div class="join-tips">
              <a-alert
                type="info"
                show-icon
                message="加入提示"
                description="加入房间后，你可以随时更改角色和队伍。指挥角色每队只能有一人。"
              />
            </div>

            <!-- 操作按钮 -->
            <div class="form-actions">
              <a-space size="large">
                <a-button size="large" @click="router.back()">
                  取消
                </a-button>
                <a-button
                  type="primary"
                  size="large"
                  html-type="submit"
                  :loading="joinLoading"
                  :disabled="!isFormValid"
                >
                  加入房间
                </a-button>
              </a-space>
            </div>
          </a-form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  TeamOutlined,
  UserOutlined,
  EyeOutlined,
  CrownOutlined
} from '@ant-design/icons-vue'
import type { FormInstance } from 'ant-design-vue'
import { message } from 'ant-design-vue'
import { useBPRoomStore } from '@/shared/stores/bp_room'
import { useAuthStore } from '@/shared/stores/auth'
import type { BPRoom, JoinRoomRequest } from '@/shared/api/bp_rooms'

// Stores & Router
const bpRoomStore = useBPRoomStore()
const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()

// 响应式数据
const formRef = ref<FormInstance>()
const loading = ref(false)
const joinLoading = ref(false)

const roomId = computed(() => route.params.roomId as string)
const room = computed(() => bpRoomStore.currentRoom)

// 表单数据
const joinForm = reactive<JoinRoomRequest>({
  team_side: undefined,
  role: 'player'
})

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

const canJoin = computed(() => {
  if (!room.value) return false
  return ['waiting', 'ready'].includes(room.value.status) && 
         activeParticipants.value.length < 10 &&
         !isAlreadyParticipant.value
})

const isAlreadyParticipant = computed(() =>
  authStore.user && activeParticipants.value.some(p => p.user_id === authStore.user!.id)
)

const hasCommander = computed(() => {
  if (!joinForm.team_side) return false
  return activeParticipants.value.some(p => 
    p.team_side === joinForm.team_side && p.role === 'commander'
  )
})

const isFormValid = computed(() => {
  if (joinForm.role === 'observer') return true
  return !!joinForm.team_side
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

// 方法
const getJoinErrorMessage = () => {
  if (!room.value) return ''
  
  if (isAlreadyParticipant.value) {
    return '你已经在这个房间中了'
  }
  
  if (!['waiting', 'ready'].includes(room.value.status)) {
    return '房间当前状态不允许加入'
  }
  
  if (activeParticipants.value.length >= 10) {
    return '房间已满员'
  }
  
  return '无法加入此房间'
}

const selectTeam = (team: 'blue' | 'red' | null) => {
  if (team === 'blue' && blueSideParticipants.value.length >= 5) return
  if (team === 'red' && redSideParticipants.value.length >= 5) return
  
  joinForm.team_side = team
  
  // 如果选择观战席，自动设置为观战角色
  if (team === null) {
    joinForm.role = 'observer'
  } else if (joinForm.role === 'observer') {
    joinForm.role = 'player'
  }
}

const handleJoin = async () => {
  try {
    joinLoading.value = true
    
    const success = await bpRoomStore.joinRoom(roomId.value, joinForm)
    
    if (success) {
      message.success('成功加入房间')
      router.push(`/matches/bp-room/${roomId.value}`)
    }
  } catch (error) {
    console.error('加入房间失败:', error)
  } finally {
    joinLoading.value = false
  }
}

// 监听队伍选择变化，自动调整角色
watch(() => joinForm.team_side, (newTeam) => {
  if (!newTeam && joinForm.role !== 'observer') {
    joinForm.role = 'observer'
  } else if (newTeam && joinForm.role === 'observer') {
    joinForm.role = 'player'
  }
})

// 生命周期
onMounted(async () => {
  if (!authStore.isAuthenticated) {
    router.push('/auth/login')
    return
  }

  loading.value = true
  try {
    await bpRoomStore.fetchRoom(roomId.value)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.join-bp-room {
  padding: 24px;
  background: #f5f5f5;
  min-height: 100vh;
}

.loading-container,
.error-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}

.join-form-container {
  max-width: 800px;
  margin: 0 auto;
}

.join-form-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.room-preview {
  padding: 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.room-header {
  margin-bottom: 16px;
}

.room-header h2 {
  font-size: 24px;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: white;
}

.room-meta {
  display: flex;
  gap: 8px;
}

.room-description p {
  margin: 0;
  font-size: 16px;
  line-height: 1.5;
  opacity: 0.9;
}

.room-stats {
  display: flex;
  gap: 24px;
  margin-top: 16px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  opacity: 0.9;
}

.join-form {
  padding: 32px;
}

.join-form h3 {
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 24px 0;
}

.team-selection {
  margin-bottom: 8px;
}

.team-options {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}

.team-option {
  padding: 20px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
}

.team-option:not(.disabled):hover {
  border-color: #3b82f6;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
}

.team-option.selected {
  border-color: #3b82f6;
  background: rgba(59, 130, 246, 0.05);
}

.team-option.disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: #f9fafb;
}

.team-option.observer {
  grid-column: 1 / -1;
  background: #f8fafc;
}

.team-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-weight: 500;
}

.team-color {
  width: 16px;
  height: 16px;
  border-radius: 50%;
}

.team-color.blue {
  background: #3b82f6;
}

.team-color.red {
  background: #ef4444;
}

.team-name {
  flex: 1;
  font-size: 16px;
}

.team-count {
  font-size: 14px;
  color: #6b7280;
}

.team-members {
  margin-bottom: 8px;
}

.team-full {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(239, 68, 68, 0.9);
  color: white;
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
}

.observer-description {
  font-size: 14px;
  color: #6b7280;
  font-style: italic;
}

.role-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.role-option {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 0;
}

.role-info {
  flex: 1;
}

.role-name {
  font-weight: 500;
  color: #1f2937;
  margin-bottom: 2px;
}

.role-desc {
  font-size: 13px;
  color: #6b7280;
}

.join-tips {
  margin: 24px 0;
}

.form-actions {
  display: flex;
  justify-content: center;
  padding-top: 24px;
  border-top: 1px solid #e5e7eb;
}

:deep(.ant-radio-wrapper) {
  width: 100%;
  padding: 12px;
  border-radius: 6px;
  border: 1px solid transparent;
  transition: all 0.2s ease;
}

:deep(.ant-radio-wrapper:hover) {
  background: #f9fafb;
  border-color: #e5e7eb;
}

:deep(.ant-radio-wrapper.ant-radio-wrapper-checked) {
  background: rgba(24, 144, 255, 0.05);
  border-color: #1890ff;
}

:deep(.ant-radio-wrapper.ant-radio-wrapper-disabled) {
  opacity: 0.5;
  background: #f5f5f5;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .join-bp-room {
    padding: 16px;
  }
  
  .team-options {
    grid-template-columns: 1fr;
  }
  
  .room-stats {
    flex-direction: column;
    gap: 12px;
  }
  
  .join-form {
    padding: 24px 16px;
  }
}
</style>