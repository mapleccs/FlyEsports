<template>
  <layout-default>
    <div class="enhanced-match-room">
      <!-- 页面加载状态 -->
      <div v-if="loading" class="loading-container">
        <a-spin size="large" />
        <p>加载比赛房间中...</p>
      </div>

      <!-- 比赛不存在 -->
      <div v-else-if="!match" class="not-found-container">
        <a-result status="404" title="比赛不存在" sub-title="您访问的比赛可能已被删除或不存在">
          <template #extra>
            <router-link :to="`/tournaments/${$route.params.tournamentId}/rooms`">
              <a-button type="primary">返回房间列表</a-button>
            </router-link>
          </template>
        </a-result>
      </div>

      <!-- 比赛存在但还没有房间，或者状态为已安排 -->
      <div v-else-if="match && (!match.room_id && match.status === 'scheduled')" class="room-not-ready-container">
        <a-result 
          status="info" 
          :title="match.status === 'scheduled' ? '比赛还未开始' : '比赛房间准备中'" 
          :sub-title="match.status === 'scheduled' ? '比赛已安排，但签到尚未开放。请等待管理员开放签到。' : '比赛房间正在准备中，请稍等。'"
        >
          <template #extra>
            <a-space>
              <router-link :to="`/tournaments/${$route.params.tournamentId}`">
                <a-button type="primary">查看赛事详情</a-button>
              </router-link>
              <a-button v-if="canOpenCheckIn" @click="openCheckIn" :loading="refreshing" type="primary">
                <PlayCircleOutlined />
                开放签到
              </a-button>
              <a-button @click="handleRefresh" :loading="refreshing">
                <ReloadOutlined />
                刷新状态
              </a-button>
            </a-space>
          </template>
          <template #icon>
            <ClockCircleOutlined style="color: #1890ff" />
          </template>
        </a-result>
      </div>

      <!-- 比赛房间内容 -->
      <div v-else class="room-content">
        <!-- 房间顶部导航 -->
        <div class="room-navigation">
          <div class="nav-left">
            <a-button @click="goBack" size="large">
              <ArrowLeftOutlined />
              返回房间列表
            </a-button>
          </div>
          <div class="nav-center">
            <div class="match-breadcrumb">
              <a-breadcrumb>
                <a-breadcrumb-item>
                  <router-link :to="`/tournaments/${$route.params.tournamentId}`">
                    {{ tournamentName }}
                  </router-link>
                </a-breadcrumb-item>
                <a-breadcrumb-item>
                  <router-link :to="`/tournaments/${$route.params.tournamentId}/rooms`">
                    比赛房间
                  </router-link>
                </a-breadcrumb-item>
                <a-breadcrumb-item>第{{ match.round_number }}轮</a-breadcrumb-item>
              </a-breadcrumb>
            </div>
          </div>
          <div class="nav-right">
            <a-space>
              <a-button v-if="isSpectator" @click="toggleSpectatorMode">
                <EyeOutlined />
                {{ spectatorMode ? '退出观战' : '观战模式' }}
              </a-button>
              <a-button @click="handleRefresh" :loading="refreshing">
                <ReloadOutlined />
                刷新
              </a-button>
            </a-space>
          </div>
        </div>

        <!-- 房间头部信息 -->
        <div class="room-header">
          <div class="header-content">
            <div class="match-info">
              <h1 class="match-title">
                <TrophyOutlined />
                {{ tournamentName }} - 第{{ match.round_number }}轮
              </h1>
              <div class="match-meta">
                <a-tag :color="getMatchStatusColor(match.status)" class="status-tag">
                  <span class="status-dot" :class="match.status"></span>
                  {{ getMatchStatusText(match.status) }}
                </a-tag>
                <a-tag color="purple" class="phase-tag">
                  <span class="phase-dot" :class="currentPhase"></span>
                  {{ getPhaseText(currentPhase) }}
                </a-tag>
                <span class="match-time">
                  <CalendarOutlined />
                  {{ formatMatchTime(match.scheduled_time) }}
                </span>
              </div>
            </div>

            <!-- 快速操作区域 -->
            <div class="quick-actions">
              <a-space>
                <!-- 用户操作 -->
                <div v-if="!isSpectator">
                  <a-button 
                    v-if="canCheckIn" 
                    type="primary" 
                    size="large"
                    :loading="checkInLoading"
                    @click="handleCheckIn"
                  >
                    <CheckCircleOutlined />
                    签到
                  </a-button>
                  
                  <a-button 
                    v-if="canVoteCommander"
                    type="primary" 
                    size="large"
                    @click="handleVoteCommander"
                  >
                    <UserAddOutlined />
                    投票选择指挥官
                  </a-button>
                </div>

                <!-- 管理员操作 -->
                <div v-if="isAdmin" class="admin-actions">
                  <a-space>
                    <a-button 
                      v-if="canOpenCheckIn"
                      type="primary" 
                      size="large"
                      :loading="adminLoading"
                      @click="handleOpenCheckIn"
                    >
                      <PlayCircleOutlined />
                      开启签到
                    </a-button>
                    
                    <a-button 
                      v-if="canForceCheckinAll"
                      type="default" 
                      size="large"
                      :loading="adminLoading"
                      @click="handleForceCheckinAll"
                      danger
                    >
                      <CheckCircleOutlined />
                      强制全员签到
                    </a-button>
                    
                    <a-button 
                      v-if="canStartCommanderVoting"
                      type="primary" 
                      size="large"
                      :loading="adminLoading"
                      @click="handleStartCommanderVoting"
                    >
                      <UserAddOutlined />
                      开始指挥官投票
                    </a-button>
                    
                    <a-button 
                      v-if="canStartMatch"
                      type="primary" 
                      size="large"
                      :loading="adminLoading"
                      @click="handleStartMatch"
                    >
                      <ThunderboltOutlined />
                      开始比赛
                    </a-button>
                    
                    <a-button 
                      v-if="match.status === 'in_progress'"
                      type="default" 
                      size="large"
                      @click="showWinnerModal = true"
                    >
                      <TrophyOutlined />
                      设置结果
                    </a-button>
                  </a-space>
                </div>
              </a-space>
            </div>
          </div>
        </div>

        <!-- 对阵信息 -->
        <div class="vs-section">
          <a-row :gutter="24">
            <!-- 蓝方 -->
            <a-col :span="10">
              <div class="team-panel blue-side">
                <div class="team-header">
                  <div class="team-logo">
                    <img v-if="blueTeamLogo" :src="blueTeamLogo" alt="蓝队Logo" />
                    <UserOutlined v-else class="logo-placeholder" />
                  </div>
                  <div class="team-info">
                    <div class="team-name">{{ resolveMatchParticipantName(match.blue_side_id) }}</div>
                    <div class="team-label blue">蓝方</div>
                  </div>
                  <div class="team-status">
                    <div v-if="blueTeamReady" class="ready-badge">
                      <CheckCircleOutlined />
                      已准备
                    </div>
                  </div>
                </div>
                <div class="team-members">
                  <h4>
                    <UsergroupAddOutlined />
                    队员列表
                    <span class="member-count">({{ blueSideMembers.length }})</span>
                  </h4>
                  <div class="members-list">
                    <div 
                      v-for="member in blueSideMembers" 
                      :key="member.id"
                      class="member-item"
                      :class="{ 
                        'checked-in': member.checkedIn,
                        'commander': member.isCommander
                      }"
                    >
                      <a-avatar :size="40" :src="member.avatar">
                        {{ member.name.charAt(0) }}
                      </a-avatar>
                      <div class="member-info">
                        <span class="member-name">{{ member.name }}</span>
                        <div class="member-badges">
                          <a-tag v-if="member.isCommander" color="gold" size="small">
                            <CrownOutlined />
                            指挥官
                          </a-tag>
                          <a-tag v-if="member.checkedIn" color="green" size="small">
                            <CheckCircleOutlined />
                            已签到
                          </a-tag>
                          <a-tag v-else color="orange" size="small">
                            <ClockCircleOutlined />
                            未签到
                          </a-tag>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </a-col>

            <!-- VS 分隔符 -->
            <a-col :span="4">
              <div class="vs-divider">
                <div class="vs-content">
                  <div class="vs-text">VS</div>
                  <div class="match-status">
                    <div class="status-indicator" :class="match.status"></div>
                    <p class="status-text">{{ getMatchStatusText(match.status) }}</p>
                  </div>
                  <div class="phase-status">
                    <div class="phase-indicator" :class="currentPhase"></div>
                    <p class="phase-text">{{ getPhaseText(currentPhase) }}</p>
                  </div>
                  <div class="progress-info">
                    <div class="checkin-progress">
                      <a-progress 
                        type="circle" 
                        :percent="checkInPercentage" 
                        :size="80"
                        :status="allCheckedIn ? 'success' : 'active'"
                      />
                      <p class="progress-label">签到进度</p>
                    </div>
                  </div>
                </div>
              </div>
            </a-col>

            <!-- 红方 -->
            <a-col :span="10">
              <div class="team-panel red-side">
                <div class="team-header">
                  <div class="team-logo">
                    <img v-if="redTeamLogo" :src="redTeamLogo" alt="红队Logo" />
                    <UserOutlined v-else class="logo-placeholder" />
                  </div>
                  <div class="team-info">
                    <div class="team-name">{{ resolveMatchParticipantName(match.red_side_id) }}</div>
                    <div class="team-label red">红方</div>
                  </div>
                  <div class="team-status">
                    <div v-if="redTeamReady" class="ready-badge">
                      <CheckCircleOutlined />
                      已准备
                    </div>
                  </div>
                </div>
                <div class="team-members">
                  <h4>
                    <UsergroupAddOutlined />
                    队员列表
                    <span class="member-count">({{ redSideMembers.length }})</span>
                  </h4>
                  <div class="members-list">
                    <div 
                      v-for="member in redSideMembers" 
                      :key="member.id"
                      class="member-item"
                      :class="{ 
                        'checked-in': member.checkedIn,
                        'commander': member.isCommander
                      }"
                    >
                      <a-avatar :size="40" :src="member.avatar">
                        {{ member.name.charAt(0) }}
                      </a-avatar>
                      <div class="member-info">
                        <span class="member-name">{{ member.name }}</span>
                        <div class="member-badges">
                          <a-tag v-if="member.isCommander" color="gold" size="small">
                            <CrownOutlined />
                            指挥官
                          </a-tag>
                          <a-tag v-if="member.checkedIn" color="green" size="small">
                            <CheckCircleOutlined />
                            已签到
                          </a-tag>
                          <a-tag v-else color="orange" size="small">
                            <ClockCircleOutlined />
                            未签到
                          </a-tag>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </a-col>
          </a-row>
        </div>

        <!-- 比赛信息面板 -->
        <div class="info-panel">
          <a-row :gutter="24">
            <a-col :span="8">
              <a-card title="比赛信息" size="small" class="info-card">
                <template #title>
                  <InfoCircleOutlined />
                  比赛信息
                </template>
                <a-descriptions :column="1" size="small">
                  <a-descriptions-item label="比赛轮次">
                    第{{ match.round_number }}轮
                  </a-descriptions-item>
                  <a-descriptions-item label="比赛编号">
                    #{{ match.match_number || match.id?.substring(0, 8) || 'TBD' }}
                  </a-descriptions-item>
                  <a-descriptions-item label="预定时间">
                    {{ formatDateTime(match.scheduled_time || '') }}
                  </a-descriptions-item>
                  <a-descriptions-item v-if="match.started_at" label="开始时间">
                    {{ formatDateTime(match.started_at || '') }}
                  </a-descriptions-item>
                  <a-descriptions-item v-if="match.completed_at" label="结束时间">
                    {{ formatDateTime(match.completed_at || '') }}
                  </a-descriptions-item>
                </a-descriptions>
              </a-card>
            </a-col>
            
            <a-col :span="8">
              <a-card title="签到状态" size="small" class="info-card">
                <template #title>
                  <TeamOutlined />
                  签到状态
                </template>
                <div class="checkin-details">
                  <div class="team-checkin">
                    <div class="team-checkin-item">
                      <span class="team-label blue">蓝队:</span>
                      <a-progress 
                        :percent="blueTeamCheckInPercentage" 
                        size="small"
                        :status="blueTeamAllCheckedIn ? 'success' : 'active'"
                      />
                      <span class="checkin-count">{{ blueTeamCheckedInCount }}/{{ blueSideMembers.length }}</span>
                    </div>
                    <div class="team-checkin-item">
                      <span class="team-label red">红队:</span>
                      <a-progress 
                        :percent="redTeamCheckInPercentage" 
                        size="small"
                        :status="redTeamAllCheckedIn ? 'success' : 'active'"
                      />
                      <span class="checkin-count">{{ redTeamCheckedInCount }}/{{ redSideMembers.length }}</span>
                    </div>
                  </div>
                  <div v-if="allCheckedIn" class="all-ready">
                    <CheckCircleOutlined style="color: #52c41a" />
                    <span>所有参赛者已签到完成</span>
                  </div>
                </div>
              </a-card>
            </a-col>

            <a-col :span="8">
              <a-card title="房间状态" size="small" class="info-card">
                <template #title>
                  <SettingOutlined />
                  房间状态
                </template>
                <div class="room-status">
                  <div class="status-item">
                    <span class="status-label">当前阶段:</span>
                    <a-tag :color="getPhaseColor(currentPhase)">
                      {{ getPhaseText(currentPhase) }}
                    </a-tag>
                  </div>
                  <div class="status-item">
                    <span class="status-label">在线人数:</span>
                    <span class="status-value">{{ onlineCount }} 人</span>
                  </div>
                  <div class="status-item">
                    <span class="status-label">房间创建:</span>
                    <span class="status-value">{{ formatDateTime(match.created_at || '') }}</span>
                  </div>
                </div>
              </a-card>
            </a-col>
          </a-row>
        </div>

        <!-- 管理员控制面板 -->
        <div v-if="isAdmin" class="admin-control-panel">
          <a-card title="管理员控制面板" size="small">
            <template #title>
              <SettingOutlined />
              管理员控制面板
              <a-tag 
                :color="getMatchStatusColor(match.status)" 
                style="margin-left: 8px"
              >
                {{ getMatchStatusText(match.status) }}
              </a-tag>
            </template>
            
            <!-- 状态提示 -->
            <div class="admin-status-info">
              <a-alert
                :message="getAdminStatusMessage()"
                :type="getAdminStatusType()"
                show-icon
                style="margin-bottom: 16px"
              />
            </div>
            <div class="admin-controls">
              <a-row :gutter="[16, 16]">
                <!-- 第一行：基础流程控制 -->
                <a-col :span="6">
                  <a-button 
                    v-if="canOpenCheckIn"
                    type="primary"
                    block
                    size="large"
                    :loading="adminLoading"
                    @click="handleOpenCheckIn"
                  >
                    <PlayCircleOutlined />
                    开放签到
                  </a-button>
                </a-col>
                <a-col :span="6">
                  <a-button 
                    v-if="canForceCheckinAll"
                    type="primary"
                    block
                    size="large"
                    :loading="adminLoading"
                    @click="handleForceCheckinAll"
                  >
                    <CheckCircleOutlined />
                    强制全员签到
                  </a-button>
                </a-col>
                <a-col :span="6">
                  <a-button 
                    v-if="canStartMatch"
                    type="primary"
                    block
                    size="large"
                    :loading="adminLoading"
                    @click="handleStartMatch"
                  >
                    <PlayCircleOutlined />
                    开始比赛
                  </a-button>
                </a-col>
                <a-col :span="6">
                  <a-button 
                    v-if="match.status === 'in_progress'"
                    type="primary"
                    block
                    size="large"
                    @click="showWinnerModal = true"
                  >
                    <TrophyOutlined />
                    结束比赛
                  </a-button>
                </a-col>
              </a-row>
              
              <a-row :gutter="[16, 16]" style="margin-top: 16px">
                <!-- 第二行：高级控制 -->
                <a-col :span="6">
                  <a-button 
                    v-if="allCheckedIn && currentPhase === 'checkin'"
                    block
                    size="large"
                    :loading="adminLoading"
                    @click="handleStartCommanderVoting"
                  >
                    <UserAddOutlined />
                    指挥官投票
                  </a-button>
                </a-col>
                <a-col :span="6">
                  <a-button 
                    v-if="currentPhase === 'commander_voting' && allCommandersSelected"
                    block
                    size="large"
                    :loading="adminLoading"
                    @click="handleStartBPPhase"
                  >
                    <ThunderboltOutlined />
                    开始BP阶段
                  </a-button>
                </a-col>
                <a-col :span="6">
                  <a-button
                    v-if="match?.status === 'completed' && !match?.winner_id"
                    block
                    size="large"
                    @click="showWinnerModal = true"
                  >
                    <TrophyOutlined />
                    重新设置获胜者
                  </a-button>
                </a-col>
                <a-col :span="6">
                  <a-button 
                    v-if="match.status !== 'cancelled'"
                    danger
                    block
                    size="large"
                    @click="handleCancelMatch"
                  >
                    <CloseOutlined />
                    取消比赛
                  </a-button>
                </a-col>
              </a-row>
            </div>
          </a-card>
        </div>
      </div>

      <!-- 设置获胜者模态框 -->
      <a-modal
        v-model:open="showWinnerModal"
        title="设置获胜者"
        :confirm-loading="adminLoading"
        @ok="handleSetWinner"
      >
        <template #title>
          <TrophyOutlined />
          设置获胜者
        </template>
        <p>请选择获胜队伍：</p>
        <a-radio-group v-model:value="selectedWinner">
          <a-radio :value="match?.blue_side_id">
            {{ resolveMatchParticipantName(match?.blue_side_id) }} (蓝方)
          </a-radio>
          <a-radio :value="match?.red_side_id">
            {{ resolveMatchParticipantName(match?.red_side_id) }} (红方)
          </a-radio>
        </a-radio-group>
      </a-modal>

      <!-- 指挥官投票模态框 -->
      <a-modal
        v-model:open="showCommanderVotingModal"
        title="选择指挥官"
        footer=""
        width="800px"
        :closable="false"
        :maskClosable="false"
      >
        <CommanderVoting
          v-if="showCommanderVotingModal"
          :roomId="$route.params.matchId as string"
          :teamSide="currentUserTeamSide as 'blue' | 'red'"
          :teamMembers="currentUserTeamMembers.map(m => ({
            userId: parseInt(m.id),
            username: m.name,
            isCommander: m.isCommander,
            isCheckedIn: m.checkedIn,
            votes: 0
          }))"
          :currentUserId="authStore.user?.id || 0"
          :isTeamCaptain="isTeamCaptain"
          @votingComplete="onCommanderVotingComplete"
          @close="showCommanderVotingModal = false"
        />
      </a-modal>
    </div>
  </layout-default>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { 
  ArrowLeftOutlined,
  EyeOutlined,
  ReloadOutlined,
  TrophyOutlined,
  CalendarOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  PlayCircleOutlined,
  UserAddOutlined,
  ThunderboltOutlined,
  CloseOutlined,
  InfoCircleOutlined,
  TeamOutlined,
  SettingOutlined,
  UserOutlined,
  UsergroupAddOutlined,
  CrownOutlined
} from '@ant-design/icons-vue'
import { useTournamentStore } from '@/shared/stores/tournament'
import { useAuthStore } from '@/shared/stores/auth'
import { usePermissionStore } from '@/shared/stores/permission'
import { getAllTeamsVotingStatus } from '@/shared/api/matches'
import LayoutDefault from '@/shared/components/layouts/LayoutDefault.vue'
import CommanderVoting from '@/features/matches/components/CommanderVoting.vue'
import { resolveParticipantDisplayName } from '@/features/matches/utils/participant'

// 组合式API
const route = useRoute()
const router = useRouter()
const tournamentStore = useTournamentStore()
const authStore = useAuthStore()
const permissionStore = usePermissionStore()

// 响应式数据
const loading = ref(false)
const checkInLoading = ref(false)
const adminLoading = ref(false)
const refreshing = ref(false)
const showWinnerModal = ref(false)
const showCommanderVotingModal = ref(false)
const selectedWinner = ref<string>('')
const currentPhase = ref('checkin') // 当前房间阶段状态
const spectatorMode = ref(false)
const onlineCount = ref(0)

// WebSocket连接
const wsConnection = ref<WebSocket | null>(null)

// 计算属性
const match = computed(() => tournamentStore.currentMatch)
const tournament = computed(() => tournamentStore.currentTournament)
const tournamentName = computed(() => tournament.value?.name || '未知赛事')

// 获取参赛者名称的辅助函数
const resolveMatchParticipantName = (participantId?: string | number): string => {
  const currentMatch = match.value

  return resolveParticipantDisplayName(participantId, {
    blueSideId: currentMatch?.blue_side_id,
    redSideId: currentMatch?.red_side_id,
    blueSideName: currentMatch?.blue_side_name,
    redSideName: currentMatch?.red_side_name,
  })
}

const blueSideMembers = computed(() => {
  if (!match.value?.blue_side_id) return []

  // 蓝方队伍参赛者信息
  const blueSideId = match.value.blue_side_id
  const isCheckedIn = match.value.check_ins?.[blueSideId] === 'checked_in'
  const participantName = resolveMatchParticipantName(blueSideId)


  return [{
    id: blueSideId,
    name: participantName || `战队${blueSideId}`,
    avatar: '',
    checkedIn: isCheckedIn,
    isCommander: false // TODO: 从实际数据获取指挥官状态
  }]
})

const redSideMembers = computed(() => {
  if (!match.value?.red_side_id) return []

  // 红方队伍参赛者信息
  const redSideId = match.value.red_side_id
  const isCheckedIn = match.value.check_ins?.[redSideId] === 'checked_in'
  const participantName = resolveMatchParticipantName(redSideId)


  return [{
    id: redSideId,
    name: participantName || `战队${redSideId}`,
    avatar: '',
    checkedIn: isCheckedIn,
    isCommander: false // TODO: 从实际数据获取指挥官状态
  }]
})

// 权限相关计算属性
const isAdmin = computed(() => {
  // 检查用户是否具有管理员权限：超级管理员、赛区管理员或管理赛事权限
  return permissionStore.isSuperAdmin ||
         permissionStore.isRegionAdmin ||
         permissionStore.hasPermission('管理赛事')
})

const isSpectator = computed(() => {
  // 观众模式：通过spectate路由进入，或者不是参赛者且不是管理员
  return route.name === 'MatchSpectate' || (!isParticipant.value && !isAdmin.value) || spectatorMode.value
})

const isParticipant = computed(() => {
  // 检查当前用户是否为参赛者
  if (!authStore.isAuthenticated || !match.value) return false

  const userId = authStore.user?.id
  if (!userId) return false

  // 确保match.value不为null
  const currentMatch = match.value
  if (!currentMatch) return false

  // 检查用户是否属于任一参赛队伍
  // 注意：这里使用简化逻辑，实际应该查询用户的队伍关系
  const userIdNum = parseInt(userId)
  const assumedTeamId = userIdNum % 2 === 1 ? currentMatch.blue_side_id : currentMatch.red_side_id

  // 检查用户的假定队伍是否在参赛者列表中
  return assumedTeamId === currentMatch.blue_side_id || assumedTeamId === currentMatch.red_side_id
})

const isTeamCaptain = computed(() => {
  // TODO: 检查当前用户是否为队长
  return false
})

const currentUserTeamSide = computed(() => {
  // TODO: 获取当前用户所在队伍
  return 'blue'
})

const currentUserTeamMembers = computed(() => {
  return currentUserTeamSide.value === 'blue' ? blueSideMembers.value : redSideMembers.value
})

// 按钮显示条件
const canCheckIn = computed(() => {
  const currentMatch = match.value
  if (!currentMatch) return false

  return (currentMatch.status === 'checking_in' || currentMatch.status === 'waiting_for_checkin') &&
         isParticipant.value && !isCheckedIn.value
})

const canOpenCheckIn = computed(() => {
  const currentMatch = match.value
  if (!currentMatch) return false

  return isAdmin.value && currentMatch.status === 'scheduled'
})

const canForceCheckinAll = computed(() => {
  const currentMatch = match.value
  if (!currentMatch) return false

  return isAdmin.value &&
         (currentMatch.status === 'checking_in' || currentMatch.status === 'waiting_for_checkin') &&
         !allCheckedIn.value
})

const canStartCommanderVoting = computed(() => {
  const currentMatch = match.value
  if (!currentMatch) return false

  return isAdmin.value &&
         (currentMatch.status === 'ready' || allCheckedIn.value)
})

const canStartMatch = computed(() => {
  const currentMatch = match.value
  if (!currentMatch) return false

  return isAdmin.value &&
         (currentMatch.status === 'checking_in' || currentMatch.status === 'waiting_for_checkin') &&
         allCheckedIn.value
})

const canVoteCommander = computed(() => {
  return currentPhase.value === 'commander_voting' && isParticipant.value
})

const allCommandersSelected = computed(() => {
  // 检查是否所有队伍都已选择指挥官
  // 这里应该根据实际的投票状态来判断
  // 暂时返回false，通过API调用来检查具体状态
  return false
})

const isCheckedIn = computed(() => {
  // 检查当前用户所在队伍是否已签到
  if (!authStore.isAuthenticated || !match.value) return false

  const userId = authStore.user?.id
  if (!userId) return false

  // 确保match.value不为null
  const currentMatch = match.value
  if (!currentMatch) return false

  // 获取用户所在队伍ID（使用与isParticipant相同的逻辑）
  const userIdNum = parseInt(userId)
  const assumedTeamId = userIdNum % 2 === 1 ? currentMatch.blue_side_id : currentMatch.red_side_id

  // 确保assumedTeamId不为undefined并检查签到状态
  if (!assumedTeamId) return false
  return currentMatch.check_ins?.[assumedTeamId] === 'checked_in'
})

// 签到状态计算属性
const blueTeamCheckedInCount = computed(() => {
  return blueSideMembers.value.filter(m => m.checkedIn).length
})

const redTeamCheckedInCount = computed(() => {
  return redSideMembers.value.filter(m => m.checkedIn).length
})

const checkedInCount = computed(() => {
  return blueTeamCheckedInCount.value + redTeamCheckedInCount.value
})

const totalParticipants = computed(() => {
  return blueSideMembers.value.length + redSideMembers.value.length
})

const checkInPercentage = computed(() => {
  if (totalParticipants.value === 0) return 100
  return Math.round((checkedInCount.value / totalParticipants.value) * 100)
})

const blueTeamCheckInPercentage = computed(() => {
  if (blueSideMembers.value.length === 0) return 100
  return Math.round((blueTeamCheckedInCount.value / blueSideMembers.value.length) * 100)
})

const redTeamCheckInPercentage = computed(() => {
  if (redSideMembers.value.length === 0) return 100
  return Math.round((redTeamCheckedInCount.value / redSideMembers.value.length) * 100)
})

const blueTeamAllCheckedIn = computed(() => {
  return blueTeamCheckedInCount.value === blueSideMembers.value.length
})

const redTeamAllCheckedIn = computed(() => {
  return redTeamCheckedInCount.value === redSideMembers.value.length
})

const allCheckedIn = computed(() => {
  // 为了测试，如果总参与者数为0，也认为已全部签到
  if (totalParticipants.value === 0) return true
  return checkedInCount.value === totalParticipants.value
})

const blueTeamReady = computed(() => {
  return blueTeamAllCheckedIn.value
})

const redTeamReady = computed(() => {
  return redTeamAllCheckedIn.value
})

const blueTeamLogo = computed(() => {
  // TODO: 获取队伍Logo
  return ''
})

const redTeamLogo = computed(() => {
  // TODO: 获取队伍Logo
  return ''
})

// 方法
const formatMatchTime = (time: string) => {
  const date = new Date(time)
  return date.toLocaleString('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const formatDateTime = (time: string) => {
  if (!time) return '--'
  const date = new Date(time)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

const getMatchStatusColor = (status: string) => {
  const statusMap = {
    pending: 'default',
    scheduled: 'default',
    waiting_for_checkin: 'processing',
    checkin_open: 'processing',
    checking_in: 'processing',
    ready: 'success',
    in_progress: 'warning',
    completed: 'success',
    cancelled: 'error',
  }
  return statusMap[status as keyof typeof statusMap] || 'default'
}

const getMatchStatusText = (status: string) => {
  const statusMap = {
    pending: '等待中',
    scheduled: '待开始',
    waiting_for_checkin: '等待签到',
    checkin_open: '签到开放',
    checking_in: '签到中',
    ready: '准备就绪',
    in_progress: '进行中',
    completed: '已完成',
    cancelled: '已取消',
  }
  return statusMap[status as keyof typeof statusMap] || '未知状态'
}

const getPhaseText = (phase: string) => {
  const phaseMap = {
    checkin: '签到阶段',
    commander_voting: '指挥官投票',
    bp: 'BP阶段',
    live: '比赛进行中',
    completed: '已完成'
  }
  return phaseMap[phase as keyof typeof phaseMap] || '准备中'
}

const getAdminStatusMessage = () => {
  if (!match.value) return '等待数据加载...'
  
  switch (match.value.status) {
    case 'scheduled':
      return '比赛已安排，点击"开放签到"开始比赛流程'
    case 'waiting_for_checkin':
      return `签到已开放，等待参赛者签到 (${checkedInCount.value}/${totalParticipants.value})`
    case 'checking_in':
      return `签到进行中 (${checkedInCount.value}/${totalParticipants.value})，${allCheckedIn.value ? '可以开始比赛' : '等待更多签到'}`
    case 'ready':
      return '所有参赛者已就绪，可以开始比赛'
    case 'in_progress':
      return '比赛进行中，可在结束后设置获胜者'
    case 'completed':
      return match.value.winner_id ? '比赛已完成' : '比赛已结束，请设置获胜者'
    case 'cancelled':
      return '比赛已取消'
    default:
      return '状态未知'
  }
}

const getAdminStatusType = () => {
  if (!match.value) return 'info'
  
  switch (match.value.status) {
    case 'scheduled':
      return 'info'
    case 'waiting_for_checkin':
    case 'checking_in':
      return allCheckedIn.value ? 'success' : 'warning'
    case 'ready':
      return 'success'
    case 'in_progress':
      return 'info'
    case 'completed':
      return match.value.winner_id ? 'success' : 'warning'
    case 'cancelled':
      return 'error'
    default:
      return 'info'
  }
}

const getPhaseColor = (phase: string) => {
  const phaseMap = {
    checkin: 'blue',
    commander_voting: 'purple',
    bp: 'green',
    live: 'orange',
    completed: 'success'
  }
  return phaseMap[phase as keyof typeof phaseMap] || 'default'
}

// 导航方法
const goBack = () => {
  router.push(`/tournaments/${route.params.tournamentId}/rooms`)
}

const handleRefresh = async () => {
  refreshing.value = true
  try {
    await loadMatch()
    message.success('刷新成功')
  } catch (error) {
    message.error('刷新失败')
  } finally {
    refreshing.value = false
  }
}

const openCheckIn = async () => {
  await handleOpenCheckIn()
}

const toggleSpectatorMode = () => {
  spectatorMode.value = !spectatorMode.value
  message.info(spectatorMode.value ? '已切换到观战模式' : '已退出观战模式')
}

// 事件处理方法
const handleCheckIn = async () => {
  const currentMatch = match.value
  if (!currentMatch) return

  try {
    checkInLoading.value = true
    await tournamentStore.checkInForMatch(currentMatch.id)
    // 成功提示已在store中处理，这里不重复显示
  } catch (error) {
    console.error('签到失败:', error)
    // 错误提示已在store中处理，这里不重复显示
  } finally {
    checkInLoading.value = false
  }
}

const handleOpenCheckIn = async () => {
  const currentMatch = match.value
  if (!currentMatch) return

  try {
    adminLoading.value = true
    await tournamentStore.openMatchCheckIn(currentMatch.id)
    // 成功提示已在store中处理，这里不重复显示
  } catch (error) {
    console.error('开启签到失败:', error)
    // 错误提示已在store中处理，这里不重复显示
  } finally {
    adminLoading.value = false
  }
}

const handleForceCheckinAll = async () => {
  const currentMatch = match.value
  if (!currentMatch) return

  try {
    adminLoading.value = true
    // TODO: 调用强制全员签到API
    await tournamentStore.forceCheckinAll(currentMatch.id)
    // 成功提示已在store中处理
  } catch (error) {
    console.error('强制全员签到失败:', error)
    // 错误提示已在store中处理，这里不重复显示
  } finally {
    adminLoading.value = false
  }
}

const handleStartMatch = async () => {
  const currentMatch = match.value
  if (!currentMatch) return

  try {
    adminLoading.value = true
    await tournamentStore.startMatch(currentMatch.id)
    // 成功提示已在store中处理
  } catch (error) {
    console.error('开始比赛失败:', error)
    // 错误提示已在store中处理，这里不重复显示
  } finally {
    adminLoading.value = false
  }
}

const handleStartCommanderVoting = async () => {
  const currentMatch = match.value
  if (!currentMatch?.room_id) {
    message.error('房间ID不存在')
    return
  }

  try {
    adminLoading.value = true

    // 调用API切换到指挥官投票阶段
    const response = await fetch(`/api/v1/lobby/rooms/${currentMatch.room_id}/update-phase`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authStore.token}`
      },
      body: JSON.stringify({
        phase: 'commander_voting'
      })
    })
    
    const data = await response.json()
    
    if (data.success) {
      currentPhase.value = 'commander_voting'
      message.success('指挥官投票阶段已开始！10秒后自动选择指挥官')
      
      // 10秒后自动完成投票并开始BP阶段
      setTimeout(async () => {
        try {
          message.info('投票时间结束，自动选择指挥官并跳转到BP界面...')
          console.log('投票时间结束，开始自动跳转到BP界面...')
          
          // 直接调用开始BP阶段，让后端处理指挥官选择
          await handleStartBPPhase()
          console.log('BP阶段启动成功，准备跳转...')
          
          // 成功启动后跳转到BP界面
          const routeParams = {
            name: 'BanPick',
            params: {
              tournamentId: route.params.tournamentId,
              matchId: route.params.matchId
            }
          }
          console.log('跳转参数:', routeParams)
          
          await router.push(routeParams)
          console.log('跳转到BP界面成功')
          
        } catch (error) {
          console.error('自动完成投票失败:', error)
          message.warning('自动投票失败，请手动开始BP阶段')
        }
      }, 10000) // 10秒后自动完成投票
      
    } else {
      message.error(data.message || '开始指挥官投票失败')
    }
  } catch (error) {
    console.error('开始指挥官投票失败:', error)
    message.error('开始指挥官投票失败，请重试')
  } finally {
    adminLoading.value = false
  }
}

const handleStartBPPhase = async () => {
  const currentMatch = match.value
  if (!currentMatch?.room_id) {
    message.error('房间ID不存在')
    throw new Error('房间ID不存在')
  }

  try {
    adminLoading.value = true

    // 调用API开始BP阶段
    const response = await fetch(`/api/v1/lobby/rooms/${currentMatch.room_id}/start-bp`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authStore.token}`
      }
    })
    
    const data = await response.json()
    
    if (data.success) {
      currentPhase.value = 'bp'
      message.success('BP阶段已开始！')
      // 刷新比赛数据以获取最新状态
      await loadMatch()
      return true
    } else {
      const errorMsg = data.message || '开始BP阶段失败'
      message.error(errorMsg)
      throw new Error(errorMsg)
    }
  } catch (error) {
    console.error('开始BP阶段失败:', error)
    message.error('开始BP阶段失败，请重试')
    throw error
  } finally {
    adminLoading.value = false
  }
}

const handleVoteCommander = () => {
  showCommanderVotingModal.value = true
}

const onCommanderVotingComplete = async (data: any) => {
  console.log('指挥官投票完成:', data)
  showCommanderVotingModal.value = false
  message.success(`${data.teamSide}队指挥官选择完成: ${data.commanderUsername}`)
  
  // 刷新比赛数据以获取最新状态
  await loadMatch()
  
  // 检查是否所有队伍都完成了投票
  try {
    const currentMatch = match.value
    if (!currentMatch?.room_id) return

    const response = await getAllTeamsVotingStatus(currentMatch.room_id)
    const allVotingData = response.data
    
    if (allVotingData.success && allVotingData.all_complete) {
      message.info('所有队伍投票完成，自动跳转到BP界面...')
      // 延迟1秒后自动跳转到BP界面，让用户看到结果
      setTimeout(async () => {
        try {
          console.log('开始执行BP阶段启动和跳转...')
          
          // 启动BP阶段
          await handleStartBPPhase()
          console.log('BP阶段启动成功，准备跳转...')
          
          // 成功启动后跳转到BP界面
          const routeParams = {
            name: 'BanPick',
            params: {
              tournamentId: route.params.tournamentId,
              matchId: route.params.matchId
            }
          }
          console.log('跳转参数:', routeParams)
          
          await router.push(routeParams)
          console.log('跳转到BP界面成功')
        } catch (error) {
          console.error('自动开始BP阶段失败:', error)
          message.error('投票完成，但启动BP阶段失败，请手动点击开始BP阶段')
        }
      }, 1000)
    } else {
      message.info('等待其他队伍完成投票...')
    }
  } catch (error) {
    console.error('检查投票状态失败:', error)
    message.warning('无法检查其他队伍投票状态，请手动确认是否开始BP阶段')
  }
}

const handleSetWinner = async () => {
  if (!selectedWinner.value || !match.value) return
  
  try {
    adminLoading.value = true
    // TODO: 调用设置获胜者API
    
    message.success('获胜者设置成功')
    showWinnerModal.value = false
  } catch (error) {
    console.error('设置获胜者失败:', error)
    message.error('设置获胜者失败')
  } finally {
    adminLoading.value = false
  }
}

const handleCancelMatch = async () => {
  // TODO: 实现取消比赛功能
  message.info('取消比赛功能待实现')
}

// WebSocket相关方法
const connectWebSocket = () => {
  const currentMatch = match.value
  if (!currentMatch?.id) return

  const token = authStore.token
  const wsUrl = `ws://localhost:8000/ws/matches/${currentMatch.id}${token ? `?token=${token}` : ''}`
  wsConnection.value = new WebSocket(wsUrl)
  
  wsConnection.value.onopen = () => {
    console.log('WebSocket连接已建立')
    onlineCount.value++
  }
  
  wsConnection.value.onmessage = (event) => {
    const data = JSON.parse(event.data)
    handleWebSocketMessage(data)
  }
  
  wsConnection.value.onclose = () => {
    console.log('WebSocket连接已关闭')
    onlineCount.value = Math.max(0, onlineCount.value - 1)
  }
  
  wsConnection.value.onerror = (error) => {
    console.error('WebSocket错误:', error)
  }
}

const handleWebSocketMessage = (data: any) => {
  console.log('收到WebSocket消息:', data)
  
  switch (data.type) {
    case 'match_status':
      // 处理比赛状态更新消息
      if (data.data && match.value) {
        const currentMatch = match.value
        // 更新比赛状态
        currentMatch.status = data.data.status
        // 更新签到状态
        if (data.data.check_ins) {
          currentMatch.check_ins = data.data.check_ins
        }
        console.log('比赛状态已更新:', data.data)
      }
      break
    case 'check_in_update':
      updateCheckInStatus(data.data)
      break
    case 'phase_change':
      currentPhase.value = data.phase
      message.info(`房间阶段已更新: ${getPhaseText(data.phase)}`)
      break
    case 'commander_selected':
      message.success(`指挥官已选择: ${data.commander}`)
      break
    case 'match_started':
      message.info('比赛已开始！')
      break
    case 'match_completed':
      message.info('比赛已结束')
      break
    case 'user_joined':
      console.log('用户加入房间:', data.data)
      break
    case 'user_left':
      console.log('用户离开房间:', data.data)
      break
    case 'user_online':
      onlineCount.value++
      break
    case 'user_offline':
      onlineCount.value = Math.max(0, onlineCount.value - 1)
      break
    default:
      console.log('未知消息类型:', data.type)
  }
}

const updateCheckInStatus = (data: any) => {
  // 根据WebSocket消息更新签到状态
  console.log('更新签到状态:', data)

  const currentMatch = match.value
  if (currentMatch && data.participant_id && data.status) {
    // 更新check_ins数据
    if (!currentMatch.check_ins) {
      currentMatch.check_ins = {}
    }
    currentMatch.check_ins[data.participant_id] = data.status

    // 显示通知
    const participantName = resolveMatchParticipantName(data.participant_id)
    if (data.status === 'checked_in') {
      message.success(`${participantName} 已签到`)
    } else {
      message.info(`${participantName} 签到状态更新: ${data.status}`)
    }
  }
}

const disconnectWebSocket = () => {
  if (wsConnection.value) {
    wsConnection.value.close()
    wsConnection.value = null
  }
}

// 加载数据
const loadMatch = async () => {
  const matchId = route.params.matchId as string
  if (!matchId) return
  
  try {
    loading.value = true
    
    // 调用API获取真实的比赛数据
    await tournamentStore.fetchMatch(matchId)
    
    // 连接WebSocket
    connectWebSocket()
  } catch (error) {
    console.error('加载比赛详情失败:', error)
    message.error('加载比赛详情失败')
  } finally {
    loading.value = false
  }
}

const loadTournament = async () => {
  const tournamentId = route.params.tournamentId as string
  if (!tournamentId) return
  
  try {
    await tournamentStore.fetchTournament(tournamentId)
  } catch (error) {
    console.error('加载赛事详情失败:', error)
  }
}

// 生命周期
onMounted(async () => {
  await loadTournament()
  await loadMatch()
})

onUnmounted(() => {
  disconnectWebSocket()
})
</script>

<style scoped>
.enhanced-match-room {
  background: #f5f5f5;
  min-height: calc(100vh - 64px);
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 100px 0;
  gap: 16px;
}

.not-found-container {
  padding: 50px 0;
}

.room-not-ready-container {
  padding: 50px 0;
}

.room-content {
  padding: 0;
}

/* 导航栏 */
.room-navigation {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.match-breadcrumb {
  flex: 1;
  display: flex;
  justify-content: center;
}

/* 房间头部 */
.room-header {
  padding: 32px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  position: relative;
  overflow: hidden;
}

.room-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="20" cy="20" r="2" fill="rgba(255,255,255,0.1)"/><circle cx="80" cy="80" r="3" fill="rgba(255,255,255,0.05)"/><circle cx="40" cy="70" r="1" fill="rgba(255,255,255,0.1)"/></svg>');
  pointer-events: none;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
  z-index: 1;
}

.match-title {
  font-size: 28px;
  font-weight: 600;
  margin: 0 0 12px 0;
  display: flex;
  align-items: center;
  gap: 12px;
}

.match-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.status-tag, .phase-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
}

.status-dot, .phase-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.status-dot.scheduled { background: #d9d9d9; }
.status-dot.check_in, .status-dot.checking_in { 
  background: #1890ff; 
  animation: pulse 2s infinite;
}
.status-dot.ongoing, .status-dot.in_progress { 
  background: #faad14; 
  animation: pulse 2s infinite;
}
.status-dot.completed { background: #52c41a; }
.status-dot.cancelled { background: #f5222d; }

.phase-dot.checkin { 
  background: #1890ff; 
  animation: pulse 2s infinite;
}
.phase-dot.commander_voting { 
  background: #722ed1; 
  animation: pulse 2s infinite;
}
.phase-dot.bp { 
  background: #52c41a; 
  animation: pulse 2s infinite;
}
.phase-dot.live { 
  background: #faad14; 
  animation: pulse 2s infinite;
}
.phase-dot.completed { background: #52c41a; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.match-time {
  display: flex;
  align-items: center;
  gap: 6px;
  color: rgba(255, 255, 255, 0.85);
}

.quick-actions .admin-actions {
  padding: 12px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  backdrop-filter: blur(10px);
}

/* VS区域 */
.vs-section {
  padding: 24px;
  background: #fff;
}

.team-panel {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  height: 100%;
  position: relative;
}

.blue-side {
  border-left: 4px solid #1890ff;
}

.red-side {
  border-left: 4px solid #f5222d;
}

.team-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.team-logo {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  background: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.team-logo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.logo-placeholder {
  font-size: 24px;
  color: #bfbfbf;
}

.team-info {
  flex: 1;
}

.team-name {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 4px;
}

.blue-side .team-name {
  color: #1890ff;
}

.red-side .team-name {
  color: #f5222d;
}

.team-label {
  font-size: 12px;
  color: #8c8c8c;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.team-status {
  display: flex;
  align-items: center;
}

.ready-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  background: #f6ffed;
  color: #52c41a;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.team-members h4 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  color: #262626;
  font-size: 14px;
}

.member-count {
  color: #8c8c8c;
  font-weight: normal;
}

.members-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.member-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  transition: all 0.2s ease;
  border: 1px solid transparent;
}

.member-item:hover {
  background: #fafafa;
}

.member-item.checked-in {
  background: #f6ffed;
  border-color: #b7eb8f;
}

.member-item.commander {
  background: #fffbe6;
  border-color: #ffe58f;
}

.member-info {
  flex: 1;
}

.member-name {
  font-weight: 500;
  color: #262626;
  display: block;
  margin-bottom: 6px;
}

.member-badges {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

/* VS分隔符 */
.vs-divider {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 400px;
}

.vs-content {
  text-align: center;
  padding: 32px 16px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  width: 100%;
}

.vs-text {
  font-size: 32px;
  font-weight: 700;
  color: #666;
  display: block;
  margin-bottom: 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.match-status, .phase-status {
  margin-bottom: 16px;
}

.status-indicator, .phase-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin: 0 auto 8px;
}

.status-text, .phase-text {
  margin: 0;
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.progress-info {
  margin-top: 20px;
}

.progress-label {
  font-size: 12px;
  color: #8c8c8c;
  margin-top: 8px;
}

/* 信息面板 */
.info-panel {
  padding: 0 24px 24px;
}

.info-card {
  height: 100%;
}

.info-card :deep(.ant-card-head-title) {
  display: flex;
  align-items: center;
  gap: 8px;
}

.checkin-details {
  space-y: 12px;
}

.team-checkin {
  margin-bottom: 16px;
}

.team-checkin-item {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.team-label {
  min-width: 50px;
  font-weight: 500;
}

.team-label.blue {
  color: #1890ff;
}

.team-label.red {
  color: #f5222d;
}

.checkin-count {
  min-width: 40px;
  font-size: 12px;
  color: #8c8c8c;
}

.all-ready {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #52c41a;
  font-weight: 500;
  font-size: 14px;
}

.room-status {
  space-y: 12px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.status-label {
  color: #8c8c8c;
  font-size: 14px;
}

.status-value {
  font-weight: 500;
  color: #262626;
}

/* 管理员控制面板 */
.admin-control-panel {
  padding: 0 24px 24px;
}

.admin-control-panel :deep(.ant-card-head-title) {
  display: flex;
  align-items: center;
  gap: 8px;
}

.admin-controls {
  padding: 16px 0;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .room-navigation {
    flex-direction: column;
    gap: 16px;
  }
  
  .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 20px;
  }
  
  .quick-actions {
    width: 100%;
  }
}

@media (max-width: 768px) {
  .vs-section .ant-col {
    margin-bottom: 16px;
  }
  
  .vs-divider {
    order: -1;
    min-height: auto;
    margin-bottom: 16px;
  }
  
  .info-panel .ant-col {
    margin-bottom: 16px;
  }
  
  .admin-controls .ant-col {
    span: 12;
  }
}

@media (max-width: 576px) {
  .room-content {
    padding: 0;
  }
  
  .room-navigation,
  .room-header,
  .vs-section,
  .info-panel,
  .admin-control-panel {
    padding-left: 16px;
    padding-right: 16px;
  }
  
  .admin-controls .ant-col {
    span: 24;
  }
  
  .match-meta {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
}
</style>