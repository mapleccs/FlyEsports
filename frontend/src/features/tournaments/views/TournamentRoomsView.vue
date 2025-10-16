<template>
  <layout-default>
    <div class="tournament-rooms">
      <!-- 页面加载状态 -->
      <div v-if="loading" class="loading-container">
        <a-spin size="large" />
        <p>加载赛事房间中...</p>
      </div>

      <!-- 赛事不存在 -->
      <div v-else-if="!tournament" class="not-found-container">
        <a-result status="404" title="赛事不存在" sub-title="您访问的赛事可能已被删除或不存在">
          <template #extra>
            <router-link to="/hall">
              <a-button type="primary">返回比赛大厅</a-button>
            </router-link>
          </template>
        </a-result>
      </div>

      <!-- 赛事房间内容 -->
      <div v-else class="rooms-content">
        <!-- 赛事头部信息 -->
        <div class="tournament-header">
          <div class="header-background">
            <img 
              v-if="tournament.banner_url" 
              :src="tournament.banner_url" 
              :alt="tournament.name"
              class="header-image"
            />
            <div v-else class="header-placeholder"></div>
            <div class="header-overlay"></div>
          </div>
          
          <div class="header-content">
            <div class="tournament-info">
              <div class="tournament-logo">
                <img v-if="tournament.logo_url" :src="tournament.logo_url" :alt="tournament.name" />
                <trophy-outlined v-else class="logo-placeholder" />
              </div>
              <div class="tournament-details">
                <h1 class="tournament-name">{{ tournament.name }}</h1>
                <div class="tournament-meta">
                  <a-tag :color="statusConfig.color" class="status-tag">
                    {{ statusConfig.text }}
                  </a-tag>
                  <a-tag color="blue">{{ typeConfig.text }}</a-tag>
                  <span class="tournament-time">
                    {{ formatDate(tournament.tournament_start) }} 开始
                  </span>
                </div>
                <p v-if="tournament.description" class="tournament-description">
                  {{ tournament.description }}
                </p>
              </div>
            </div>
            
            <div class="header-actions">
              <a-button @click="$router.go(-1)" size="large">
                <ArrowLeftOutlined />
                返回
              </a-button>
              <a-button v-if="canManageTournament" type="primary" size="large" @click="showManageModal = true">
                <SettingOutlined />
                管理赛事
              </a-button>
            </div>
          </div>
        </div>

        <!-- 比赛房间列表 -->
        <div class="rooms-main">
          <div class="rooms-header">
            <div class="header-left">
              <h2>比赛房间</h2>
              <p class="rooms-desc">选择房间观看或参与比赛</p>
            </div>
            <div class="header-right">
              <a-space>
                <a-select 
                  v-model:value="filterStatus" 
                  placeholder="筛选状态" 
                  allowClear 
                  style="width: 120px"
                  @change="handleFilterChange"
                >
                  <a-select-option value="">全部状态</a-select-option>
                  <a-select-option value="scheduled">待开始</a-select-option>
                  <a-select-option value="waiting_for_checkin">等待签到</a-select-option>
                  <a-select-option value="checking_in">签到中</a-select-option>
                  <a-select-option value="in_progress">进行中</a-select-option>
                  <a-select-option value="completed">已完成</a-select-option>
                </a-select>
                <a-select 
                  v-model:value="filterRound" 
                  placeholder="筛选轮次" 
                  allowClear 
                  style="width: 120px"
                  @change="handleFilterChange"
                >
                  <a-select-option value="">全部轮次</a-select-option>
                  <a-select-option v-for="round in availableRounds" :key="round" :value="round">
                    第{{ round }}轮
                  </a-select-option>
                </a-select>
                <a-button @click="handleRefresh" :loading="refreshing">
                  <ReloadOutlined />
                  刷新
                </a-button>
              </a-space>
            </div>
          </div>

          <!-- 比赛列表 -->
          <div v-if="matchesLoading" class="matches-loading">
            <a-spin size="large" />
            <p>加载比赛数据中...</p>
          </div>

          <div v-else-if="filteredMatches.length === 0" class="matches-empty">
            <a-empty 
              description="暂无比赛房间" 
              :image="Empty.PRESENTED_IMAGE_SIMPLE"
            >
              <template #description>
                <span>{{ getEmptyDescription() }}</span>
              </template>
            </a-empty>
          </div>

          <div v-else class="matches-grid">
            <a-row :gutter="[16, 16]">
              <a-col 
                v-for="match in filteredMatches" 
                :key="match.id" 
                :xs="24" 
                :sm="12" 
                :lg="8" 
                :xl="6"
              >
                <a-card 
                  class="match-card" 
                  hoverable
                  @click="handleMatchClick(match)"
                  :loading="false"
                >
                  <template #title>
                    <div class="match-title">
                      <span class="round-text">第{{ match.round_number }}轮</span>
                      <a-tag :color="getMatchStatusColor(match.status)" size="small">
                        {{ getMatchStatusText(match.status) }}
                      </a-tag>
                    </div>
                  </template>

                  <!-- 对阵信息 -->
                  <div class="match-vs">
                    <div class="team blue-team">
                      <div class="team-name">{{ getParticipantName(match.blue_side_id, match) || 'TBD' }}</div>
                      <div style="font-size: 10px; color: #999;">调试: {{ match.blue_side_id }} -> {{ match.blue_side_name }}</div>
                      <div class="team-side">蓝方</div>
                    </div>
                    
                    <div class="vs-divider">
                      <span class="vs-text">VS</span>
                    </div>
                    
                    <div class="team red-team">
                      <div class="team-name">{{ getParticipantName(match.red_side_id, match) || 'TBD' }}</div>
                      <div style="font-size: 10px; color: #999;">调试: {{ match.red_side_id }} -> {{ match.red_side_name }}</div>
                      <div class="team-side">红方</div>
                    </div>
                  </div>

                  <!-- 比赛信息 -->
                  <div class="match-info">
                    <div class="info-item">
                      <ClockCircleOutlined />
                      <span>{{ formatTime(match.scheduled_time) }}</span>
                    </div>
                    
                    <div v-if="match.started_at" class="info-item">
                      <PlayCircleOutlined />
                      <span>{{ formatTime(match.started_at) }} 开始</span>
                    </div>
                    
                    <div v-if="match.completed_at" class="info-item">
                      <CheckCircleOutlined />
                      <span>{{ formatTime(match.completed_at) }} 完成</span>
                    </div>

                    <div v-if="match.winner_id" class="info-item winner">
                      <TrophyOutlined />
                      <span>获胜者: {{ getParticipantName(match.winner_id, match) }}</span>
                    </div>
                  </div>

                  <!-- 房间操作 -->
                  <template #actions>
                    <div class="match-actions">
                      <a-button
                        type="primary"
                        size="small"
                        @click.stop="handleEnterRoom(match)"
                        :disabled="!canEnterRoom(match)"
                      >
                        {{ getRoomButtonText(match) }}
                      </a-button>

                      <a-button
                        v-if="match.status === 'in_progress' || match.status === 'completed'"
                        size="small"
                        @click.stop="handleWatchMatch(match)"
                      >
                        <EyeOutlined />
                        观战
                      </a-button>

                      <a-button
                        v-if="canManageTournament && (match.status === 'scheduled' || match.status === 'waiting_for_checkin')"
                        size="small"
                        @click.stop="handleEditMatch(match)"
                      >
                        <EditOutlined />
                        编辑
                      </a-button>

                      <a-button
                        v-if="canManageTournament && (match.status === 'scheduled' || match.status === 'waiting_for_checkin')"
                        size="small"
                        danger
                        @click.stop="handleDeleteMatch(match)"
                      >
                        <DeleteOutlined />
                        删除
                      </a-button>
                    </div>
                  </template>
                </a-card>
              </a-col>
            </a-row>
          </div>
        </div>
      </div>

      <!-- 管理赛事模态框 -->
      <a-modal
        v-model:open="showManageModal"
        title="管理赛事"
        width="600px"
        @ok="showManageModal = false"
        @cancel="showManageModal = false"
      >
        <div class="manage-content">
          <a-space direction="vertical" style="width: 100%">
            <a-button type="primary" block @click="handleGenerateBracket">
              <ThunderboltOutlined />
              生成赛程对阵表
            </a-button>
            <a-button block @click="handleManageRegistrations">
              <TeamOutlined />
              管理报名名单
            </a-button>
            <a-button block @click="showCreateMatchModal = true">
              <PlusOutlined />
              创建新比赛房间
            </a-button>
            <a-button block @click="handleExportData">
              <DownloadOutlined />
              导出比赛数据
            </a-button>
          </a-space>
        </div>
      </a-modal>

      <!-- 编辑比赛模态框 -->
      <a-modal
        v-model:open="showEditMatchModal"
        title="编辑比赛"
        width="600px"
        @ok="handleUpdateMatch"
        @cancel="showEditMatchModal = false"
        :ok-button-props="{ loading: loading }"
      >
        <a-form ref="editFormRef" :model="editMatchForm" layout="vertical">
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="蓝方参赛者ID" name="blue_side_id">
                <a-input v-model:value="editMatchForm.blue_side_id" placeholder="请输入蓝方参赛者ID" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="红方参赛者ID" name="red_side_id">
                <a-input v-model:value="editMatchForm.red_side_id" placeholder="请输入红方参赛者ID" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="轮次" name="round_number">
                <a-input-number
                  v-model:value="editMatchForm.round_number"
                  :min="1"
                  style="width: 100%"
                  placeholder="请输入轮次"
                />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="预定时间" name="scheduled_time">
                <a-date-picker
                  v-model:value="editMatchForm.scheduled_time"
                  show-time
                  style="width: 100%"
                  placeholder="选择比赛时间"
                />
              </a-form-item>
            </a-col>
          </a-row>
        </a-form>
      </a-modal>

      <!-- 创建比赛模态框 -->
      <a-modal
        v-model:open="showCreateMatchModal"
        title="创建新比赛"
        width="600px"
        @ok="handleCreateMatch"
        @cancel="showCreateMatchModal = false"
        :ok-button-props="{ loading: loading }"
      >
        <a-form ref="createFormRef" :model="createMatchForm" layout="vertical">
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item
                label="蓝方参赛者ID"
                name="blue_side_id"
                :rules="[{ required: true, message: '请输入蓝方参赛者ID' }]"
              >
                <a-input v-model:value="createMatchForm.blue_side_id" placeholder="请输入蓝方参赛者ID" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item
                label="红方参赛者ID"
                name="red_side_id"
                :rules="[{ required: true, message: '请输入红方参赛者ID' }]"
              >
                <a-input v-model:value="createMatchForm.red_side_id" placeholder="请输入红方参赛者ID" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item
                label="轮次"
                name="round_number"
                :rules="[{ required: true, message: '请输入轮次' }]"
              >
                <a-input-number
                  v-model:value="createMatchForm.round_number"
                  :min="1"
                  style="width: 100%"
                  placeholder="请输入轮次"
                />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="预定时间" name="scheduled_time">
                <a-date-picker
                  v-model:value="createMatchForm.scheduled_time"
                  show-time
                  style="width: 100%"
                  placeholder="选择比赛时间"
                />
              </a-form-item>
            </a-col>
          </a-row>
        </a-form>
      </a-modal>
    </div>
  </layout-default>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message, Empty, Modal } from 'ant-design-vue'
import {
  TrophyOutlined,
  ArrowLeftOutlined,
  SettingOutlined,
  ReloadOutlined,
  ClockCircleOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  EyeOutlined,
  ThunderboltOutlined,
  TeamOutlined,
  DownloadOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
} from '@ant-design/icons-vue'

import LayoutDefault from '@/shared/components/layouts/LayoutDefault.vue'
import { useTournamentStore } from '@/shared/stores/tournament'
import { useAuthStore } from '@/shared/stores/auth'
import { usePermissionStore } from '@/shared/stores/permission'
import type { Tournament, Match } from '@/shared/types/tournament'
import dayjs, { type Dayjs } from 'dayjs'

// 路由和存储
const route = useRoute()
const router = useRouter()
const tournamentStore = useTournamentStore()
const authStore = useAuthStore()
const permissionStore = usePermissionStore()

// 响应式数据
const loading = ref(false)
const matchesLoading = ref(false)
const refreshing = ref(false)
const showManageModal = ref(false)
const showEditMatchModal = ref(false)
const showCreateMatchModal = ref(false)
const filterStatus = ref('')
const filterRound = ref('')

// 表单数据
const editMatchForm = ref({
  blue_side_id: '',
  red_side_id: '',
  round_number: 1,
  scheduled_time: null as Dayjs | null,
})

const createMatchForm = ref({
  blue_side_id: '',
  red_side_id: '',
  round_number: 1,
  scheduled_time: null as Dayjs | null,
})

const currentEditingMatch = ref<Match | null>(null)

// 表单引用
const editFormRef = ref()
const createFormRef = ref()

// 计算属性
const tournament = computed(() => tournamentStore.currentTournament)
const matches = computed(() => tournamentStore.matches)

const statusConfig = computed(() => {
  if (!tournament.value) return { color: 'default', text: '未知' }
  
  const statusMap = {
    draft: { color: 'default', text: '草稿' },
    upcoming: { color: 'blue', text: '即将开始' },
    registration_open: { color: 'green', text: '正在报名' },
    registration_closed: { color: 'orange', text: '报名结束' },
    ongoing: { color: 'purple', text: '进行中' },
    completed: { color: 'gray', text: '已完成' },
    cancelled: { color: 'red', text: '已取消' },
  }
  
  return statusMap[tournament.value.status] || statusMap.draft
})

const typeConfig = computed(() => {
  if (!tournament.value) return { color: 'blue', text: '未知' }
  
  const typeMap = {
    team_based: { color: 'blue', text: '战队赛' },
    solo_based: { color: 'green', text: '个人赛' },
  }
  
  return typeMap[tournament.value.tournament_type] || typeMap.team_based
})

const canManageTournament = computed(() => {
  if (!authStore.user || !tournament.value) return false

  // 检查是否为赛事创建者
  if (authStore.user.id === tournament.value.created_by) return true

  // 临时：直接检查是否为管理员邮箱
  if (authStore.user.email === '468355490@qq.com') return true

  // 检查是否有管理赛事权限（超级管理员或赛区管理员）
  if (permissionStore.initialized && permissionStore.hasPermission('管理赛事')) return true

  // 检查是否为超级管理员或赛区管理员
  if (permissionStore.initialized && (permissionStore.isSuperAdmin || permissionStore.isRegionAdmin)) return true

  return false
})

const availableRounds = computed(() => {
  const rounds = new Set(matches.value.map(m => m.round_number))
  return Array.from(rounds).sort((a, b) => a - b)
})

const filteredMatches = computed(() => {
  let filtered = matches.value

  if (filterStatus.value) {
    filtered = filtered.filter(m => m.status === filterStatus.value)
  }

  if (filterRound.value) {
    filtered = filtered.filter(m => m.round_number === parseInt(filterRound.value))
  }

  return filtered.sort((a, b) => a.round_number - b.round_number)
})

// 方法
const fetchTournamentData = async () => {
  const tournamentId = route.params.id as string
  if (!tournamentId) return

  try {
    console.log('TournamentRoomsView: 开始加载数据')
    console.log('TournamentRoomsView: 当前用户:', authStore.user)
    console.log('TournamentRoomsView: 赛事ID:', tournamentId)

    loading.value = true
    await tournamentStore.fetchTournament(tournamentId)
    console.log('TournamentRoomsView: 赛事加载完成:', tournamentStore.currentTournament)

    matchesLoading.value = true
    const matchResult = await tournamentStore.fetchMatches(tournamentId)
    console.log('TournamentRoomsView: 比赛加载完成:', matchResult)
    console.log('TournamentRoomsView: 比赛数量:', tournamentStore.matches.length)
  } catch (error) {
    console.error('Failed to fetch tournament data:', error)
    message.error('加载赛事数据失败')
  } finally {
    loading.value = false
    matchesLoading.value = false
  }
}

const handleFilterChange = () => {
  // 筛选逻辑已在计算属性中处理
}

const handleRefresh = async () => {
  refreshing.value = true
  try {
    await fetchTournamentData()
    message.success('数据已刷新')
  } finally {
    refreshing.value = false
  }
}

const handleMatchClick = (match: Match) => {
  if (canEnterRoom(match)) {
    handleEnterRoom(match)
  } else {
    handleWatchMatch(match)
  }
}

const handleEnterRoom = (match: Match) => {
  const tournamentId = route.params.id as string
  router.push(`/tournaments/${tournamentId}/matches/${match.id}/room`)
}

const handleWatchMatch = (match: Match) => {
  const tournamentId = route.params.id as string
  router.push(`/tournaments/${tournamentId}/matches/${match.id}/spectate`)
}

const canEnterRoom = (match: Match) => {
  if (!authStore.isAuthenticated) return false
  if (canManageTournament.value) return true
  
  // TODO: 检查用户是否为参赛者
  return match.status === 'waiting_for_checkin' || match.status === 'checking_in' || match.status === 'in_progress'
}

const getRoomButtonText = (match: Match) => {
  if (!authStore.isAuthenticated) return '请登录'
  if (!canEnterRoom(match)) return '观战'
  
  switch (match.status) {
    case 'scheduled':
      return '等待开始'
    case 'waiting_for_checkin':
      return '进入房间'
    case 'checking_in':
      return '进入房间'
    case 'in_progress':
      return '进入比赛'
    case 'completed':
      return '查看结果'
    default:
      return '进入房间'
  }
}

const getMatchStatusColor = (status: string) => {
  const statusMap = {
    scheduled: 'default',
    waiting_for_checkin: 'processing',
    checking_in: 'processing',
    in_progress: 'warning',
    completed: 'success',
    cancelled: 'error',
  }
  return statusMap[status as keyof typeof statusMap] || 'default'
}

const getMatchStatusText = (status: string) => {
  const statusMap = {
    scheduled: '待开始',
    waiting_for_checkin: '等待签到',
    checking_in: '签到中',
    in_progress: '进行中',
    completed: '已完成',
    cancelled: '已取消',
  }
  return statusMap[status as keyof typeof statusMap] || '未知'
}

const getParticipantName = (participantId?: string, match?: any) => {
  console.log('getParticipantName 调用:', { participantId, match })

  if (!participantId) return 'TBD'
  if (!match) return 'TBD'

  // 使用API返回的真实参赛者名称
  if (participantId === match.blue_side_id) {
    const result = match.blue_side_name || 'TBD'
    console.log('匹配蓝方:', { participantId, blue_side_name: match.blue_side_name, result })
    return result
  } else if (participantId === match.red_side_id) {
    const result = match.red_side_name || 'TBD'
    console.log('匹配红方:', { participantId, red_side_name: match.red_side_name, result })
    return result
  } else if (participantId === match.winner_id) {
    // 对于获胜者，需要确定是蓝方还是红方
    if (match.winner_id === match.blue_side_id) {
      return match.blue_side_name || 'TBD'
    } else if (match.winner_id === match.red_side_id) {
      return match.red_side_name || 'TBD'
    }
  }

  console.log('未匹配到任何情况, 返回TBD:', { participantId, match })
  return 'TBD'
}

const getEmptyDescription = () => {
  if (filterStatus.value || filterRound.value) {
    return '没有符合筛选条件的比赛'
  }
  return '该赛事还没有生成比赛对阵表'
}

const formatDate = (dateString?: string) => {
  if (!dateString) return ''
  return new Date(dateString).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

const formatTime = (dateString?: string) => {
  if (!dateString) return ''
  return new Date(dateString).toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// 管理功能
const handleGenerateBracket = async () => {
  const tournamentId = route.params.id as string
  try {
    await tournamentStore.generateBracket(tournamentId)
    await fetchTournamentData() // 重新加载数据
    showManageModal.value = false
    message.success('赛程对阵表生成成功')
  } catch (error) {
    console.error('Failed to generate bracket:', error)
    message.error('生成对阵表失败')
  }
}

const handleManageRegistrations = () => {
  const tournamentId = route.params.id as string
  router.push(`/tournaments/${tournamentId}/registrations`)
}

const handleExportData = () => {
  // TODO: 实现数据导出
  message.info('数据导出功能开发中')
}

// 比赛管理功能
const handleEditMatch = (match: Match) => {
  currentEditingMatch.value = match

  // 安全地处理日期转换为dayjs对象
  let scheduledTime: Dayjs | null = null
  if (match.scheduled_time) {
    try {
      const dayjsObj = dayjs(match.scheduled_time)
      if (dayjsObj.isValid()) {
        scheduledTime = dayjsObj
      }
    } catch (error) {
      console.warn('Invalid scheduled_time:', match.scheduled_time, error)
    }
  }

  editMatchForm.value = {
    blue_side_id: match.blue_side_id || '',
    red_side_id: match.red_side_id || '',
    round_number: match.round_number,
    scheduled_time: scheduledTime,
  }
  showEditMatchModal.value = true
}

const handleDeleteMatch = (match: Match) => {
  // 确认删除比赛
  Modal.confirm({
    title: '确认删除比赛',
    content: `您确定要删除这场比赛吗？此操作无法撤销。`,
    okText: '确认删除',
    okType: 'danger',
    cancelText: '取消',
    onOk: async () => {
      try {
        const tournamentId = route.params.id as string
        await tournamentStore.deleteMatch(tournamentId, match.id)
        await fetchTournamentData() // 重新加载数据
        message.success('比赛删除成功')
      } catch (error) {
        console.error('删除比赛失败:', error)
        message.error('删除比赛失败')
      }
    }
  })
}

const handleUpdateMatch = async () => {
  if (!currentEditingMatch.value) return

  try {
    const tournamentId = route.params.id as string
    const updateData: any = {}

    // 只包含有变化的字段
    if (editMatchForm.value.blue_side_id !== currentEditingMatch.value.blue_side_id) {
      updateData.blue_side_id = editMatchForm.value.blue_side_id
    }
    if (editMatchForm.value.red_side_id !== currentEditingMatch.value.red_side_id) {
      updateData.red_side_id = editMatchForm.value.red_side_id
    }
    if (editMatchForm.value.round_number !== currentEditingMatch.value.round_number) {
      updateData.round_number = editMatchForm.value.round_number
    }
    if (editMatchForm.value.scheduled_time) {
      try {
        updateData.scheduled_time = editMatchForm.value.scheduled_time.toISOString()
      } catch (error) {
        console.warn('Invalid scheduled_time for update:', editMatchForm.value.scheduled_time, error)
        message.error('预定时间格式无效')
        return
      }
    }

    if (Object.keys(updateData).length === 0) {
      message.info('没有检测到任何更改')
      showEditMatchModal.value = false
      return
    }

    await tournamentStore.updateMatch(tournamentId, currentEditingMatch.value.id, updateData)
    await fetchTournamentData() // 重新加载数据
    showEditMatchModal.value = false
    message.success('比赛信息更新成功')
  } catch (error) {
    console.error('更新比赛失败:', error)
    message.error('更新比赛失败')
  }
}

const handleCreateMatch = async () => {
  try {
    await createFormRef.value.validate()

    const tournamentId = route.params.id as string
    const createData = {
      blue_side_id: createMatchForm.value.blue_side_id,
      red_side_id: createMatchForm.value.red_side_id,
      round_number: createMatchForm.value.round_number,
      scheduled_time: createMatchForm.value.scheduled_time
        ? (() => {
            try {
              return createMatchForm.value.scheduled_time.toISOString()
            } catch (error) {
              console.warn('Invalid scheduled_time for create:', createMatchForm.value.scheduled_time, error)
              throw new Error('预定时间格式无效')
            }
          })()
        : undefined,
    }

    await tournamentStore.createMatch(tournamentId, createData)
    await fetchTournamentData() // 重新加载数据

    // 重置表单
    createMatchForm.value = {
      blue_side_id: '',
      red_side_id: '',
      round_number: 1,
      scheduled_time: null,
    }

    showCreateMatchModal.value = false
    showManageModal.value = false
    message.success('比赛创建成功')
  } catch (error) {
    console.error('创建比赛失败:', error)
    if (error?.response?.data?.detail) {
      message.error(error.response.data.detail)
    } else {
      message.error('创建比赛失败')
    }
  }
}

// 生命周期
onMounted(async () => {
  // 确保权限已加载
  if (authStore.isAuthenticated && !permissionStore.initialized) {
    try {
      await authStore.loadUserPermissions()
    } catch (error) {
      console.warn('Failed to load permissions:', error)
    }
  }
  await fetchTournamentData()
})

watch(() => route.params.id, () => {
  if (route.params.id) {
    fetchTournamentData()
  }
})
</script>

<style scoped>
.tournament-rooms {
  min-height: 100vh;
  background: #f5f5f5;
}

.loading-container,
.not-found-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  text-align: center;
}

.loading-container p,
.matches-loading p {
  margin-top: 16px;
  color: #666;
}

/* 赛事头部 */
.tournament-header {
  position: relative;
  height: 300px;
  margin-bottom: 24px;
  overflow: hidden;
  border-radius: 12px;
}

.header-background {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
}

.header-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.header-placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.header-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
}

.header-content {
  position: relative;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  color: white;
  z-index: 1;
}

.tournament-info {
  display: flex;
  align-items: center;
  gap: 24px;
}

.tournament-logo {
  flex-shrink: 0;
  width: 80px;
  height: 80px;
  border-radius: 12px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
}

.tournament-logo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.logo-placeholder {
  font-size: 32px;
  color: rgba(255, 255, 255, 0.8);
}

.tournament-details {
  flex: 1;
}

.tournament-name {
  font-size: 2.5rem;
  font-weight: bold;
  margin: 0 0 12px 0;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
}

.tournament-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.tournament-time {
  opacity: 0.9;
}

.tournament-description {
  opacity: 0.8;
  margin: 8px 0 0 0;
  max-width: 600px;
  line-height: 1.5;
}

.header-actions {
  display: flex;
  gap: 12px;
}

/* 房间列表 */
.rooms-main {
  background: white;
  border-radius: 12px;
  padding: 24px;
}

.rooms-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.header-left h2 {
  margin: 0 0 4px 0;
  font-size: 1.5rem;
  color: #262626;
}

.rooms-desc {
  margin: 0;
  color: #8c8c8c;
}

.matches-loading,
.matches-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  text-align: center;
}

/* 比赛卡片 */
.match-card {
  height: 100%;
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.3s ease;
  cursor: pointer;
}

.match-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.match-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.round-text {
  font-weight: 600;
  color: #262626;
}

.match-vs {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 16px 0;
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
}

.team {
  flex: 1;
  text-align: center;
}

.team-name {
  font-weight: 600;
  color: #262626;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.team-side {
  font-size: 12px;
  color: #8c8c8c;
}

.blue-team .team-side {
  color: #1890ff;
}

.red-team .team-side {
  color: #ff4d4f;
}

.vs-divider {
  flex-shrink: 0;
  margin: 0 16px;
}

.vs-text {
  font-weight: bold;
  font-size: 14px;
  color: #8c8c8c;
}

.match-info {
  margin-top: 16px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 14px;
  color: #595959;
}

.info-item:last-child {
  margin-bottom: 0;
}

.info-item.winner {
  color: #52c41a;
  font-weight: 600;
}

.match-actions {
  display: flex;
  gap: 8px;
  width: 100%;
}

.match-actions .ant-btn {
  flex: 1;
}

/* 管理模态框 */
.manage-content {
  padding: 16px 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .tournament-header {
    height: 200px;
  }
  
  .header-content {
    padding: 0 16px;
  }
  
  .tournament-info {
    gap: 16px;
  }
  
  .tournament-logo {
    width: 60px;
    height: 60px;
  }
  
  .tournament-name {
    font-size: 1.8rem;
  }
  
  .header-actions {
    flex-direction: column;
    gap: 8px;
  }
  
  .rooms-header {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }
  
  .match-vs {
    flex-direction: column;
    gap: 8px;
  }
  
  .vs-divider {
    margin: 8px 0;
  }
}
</style>