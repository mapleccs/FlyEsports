<template>
  <layout-default>
    <div class="hall-container">
      <div class="hall-header">
        <div class="hall-page-header">
          <div class="header-content">
            <h1 class="page-title">比赛大厅</h1>
            <p class="page-description">参与精彩赛事，展示你的实力</p>
          </div>
          <div class="header-actions">
            <a-space>
              <a-button type="primary" @click="handleMyMatches" size="large">
                <TrophyOutlined />
                我的比赛
              </a-button>
              <a-button @click="handleMyTeam" size="large">
                <TeamOutlined />
                我的战队
              </a-button>
              <a-button @click="handlePlayerProfile" size="large"> 个人资料 </a-button>
            </a-space>
          </div>
        </div>
      </div>

      <div class="hall-content">
        <!-- 快捷导航 -->
        <div class="quick-nav">
          <a-row :gutter="16">
            <a-col :xs="12" :sm="6">
              <a-card class="nav-card" hoverable @click="activeTab = 'registration'">
                <div class="nav-item">
                  <FormOutlined class="nav-icon" />
                  <div class="nav-text">
                    <div class="nav-title">可参与赛事</div>
                    <div class="nav-desc">{{ openTournaments.length }}个赛事等你参加</div>
                  </div>
                </div>
              </a-card>
            </a-col>
            <a-col :xs="12" :sm="6">
              <a-card class="nav-card" hoverable @click="activeTab = 'ongoing'">
                <div class="nav-item">
                  <PlayCircleOutlined class="nav-icon ongoing" />
                  <div class="nav-text">
                    <div class="nav-title">直播中</div>
                    <div class="nav-desc">{{ ongoingMatches.length }}场比赛正在直播</div>
                  </div>
                </div>
              </a-card>
            </a-col>
            <a-col :xs="12" :sm="6">
              <a-card class="nav-card" hoverable @click="activeTab = 'upcoming'">
                <div class="nav-item">
                  <ClockCircleOutlined class="nav-icon upcoming" />
                  <div class="nav-text">
                    <div class="nav-title">即将开始</div>
                    <div class="nav-desc">{{ upcomingMatches.length }}场比赛即将开始</div>
                  </div>
                </div>
              </a-card>
            </a-col>
            <a-col :xs="12" :sm="6">
              <a-card class="nav-card" hoverable @click="activeTab = 'results'">
                <div class="nav-item">
                  <TrophyOutlined class="nav-icon completed" />
                  <div class="nav-text">
                    <div class="nav-title">赛事结果</div>
                    <div class="nav-desc">查看精彩赛事回顾</div>
                  </div>
                </div>
              </a-card>
            </a-col>
          </a-row>
        </div>

        <!-- 标签页内容 -->
        <div class="hall-tabs">
          <a-tabs v-model:activeKey="activeTab" size="large">
            <!-- 可参与赛事 -->
            <a-tab-pane key="registration" tab="可参与赛事">
              <div class="registration-section">
                <div v-if="loading" class="loading-container">
                  <a-spin size="large" />
                  <p>加载赛事中...</p>
                </div>

                <div v-else-if="openTournaments.length === 0" class="empty-container">
                  <a-empty description="暂无可参与的赛事" />
                </div>

                <a-row v-else :gutter="[16, 16]">
                  <a-col
                    :xs="24"
                    :sm="12"
                    :xl="8"
                    v-for="tournament in openTournaments"
                    :key="tournament.id"
                  >
                    <a-card
                      class="tournament-card"
                      hoverable
                      @click="handleTournamentClick(tournament)"
                      :loading="loading"
                    >
                      <template #cover>
                        <div class="tournament-cover">
                          <img
                            :src="tournament.banner_url || '/default-tournament-banner.svg'"
                            :alt="tournament.name"
                          />
                          <div class="tournament-status">
                            <a-tag :color="getStatusColor(tournament.status)">
                              {{ getStatusText(tournament.status) }}
                            </a-tag>
                          </div>
                        </div>
                      </template>

                      <a-card-meta :title="tournament.name" :description="tournament.description" />

                      <div class="tournament-info">
                        <div class="info-item">
                          <CalendarOutlined />
                          <span>{{ formatDate(tournament.tournament_start) }} 开始</span>
                        </div>
                        <div class="info-item">
                          <component :is="getParticipantIcon(tournament)" />
                          <span>
                            {{ getDisplayedRegistrationCount(tournament) }}
                            / {{ tournament.max_participants }}
                            {{ getParticipantUnit(tournament) }} | 还差
                            {{ getRemainingSlots(tournament) }}
                            {{ getParticipantUnit(tournament) }}
                          </span>
                        </div>
                        <div class="info-item">
                          <DollarOutlined />
                          <span>奖金池 待公布</span>
                        </div>
                        <div class="info-item">
                          <ClockCircleOutlined />
                          <span>报名截止: {{ formatDate(tournament.registration_end) }}</span>
                        </div>
                      </div>

                      <div class="tournament-actions">
                        <a-space direction="vertical" style="width: 100%">
                          <a-button
                            type="primary"
                            block
                            size="large"
                            @click.stop="handleTournamentAction(tournament)"
                            :disabled="!canInteract(tournament)"
                          >
                            {{ getRegisterButtonText(tournament) }}
                          </a-button>
                          <a-button block @click.stop="handleViewTournamentDetails(tournament)">
                            查看详情
                          </a-button>
                        </a-space>
                      </div>
                    </a-card>
                  </a-col>
                </a-row>
              </div>
            </a-tab-pane>

            <!-- 精彩直播 -->
            <a-tab-pane key="ongoing" tab="精彩直播">
              <div class="ongoing-section">
                <a-list :data-source="ongoingMatches" :pagination="false" item-layout="horizontal">
                  <template #renderItem="{ item: match }">
                    <a-list-item class="match-item" @click="handleMatchClick(match)">
                      <template #actions>
                        <a-space>
                          <a-button
                            type="primary"
                            size="large"
                            @click.stop="handleWatchLive(match)"
                          >
                            <PlayCircleOutlined />
                            观看直播
                          </a-button>
                          <a-button @click.stop="handleViewDetails(match)"> 比赛详情 </a-button>
                          <a-button @click.stop="handleAddToFavorites(match)">
                            <HeartOutlined />
                            收藏
                          </a-button>
                        </a-space>
                      </template>

                      <a-list-item-meta>
                        <template #title>
                          <div class="match-title">
                            <span class="tournament-name">{{ match.tournament.name }}</span>
                            <span class="match-round">{{ match.round }}</span>
                            <a-tag color="red">直播中</a-tag>
                          </div>
                        </template>

                        <template #description>
                          <div class="match-teams">
                            <div class="team-section">
                              <a-avatar :src="match.teamA.logo" :alt="match.teamA.name" />
                              <span class="team-name">{{ match.teamA.name }}</span>
                            </div>
                            <div class="vs-section">
                              <span class="score"
                                >{{ match.score?.teamA || 0 }} : {{ match.score?.teamB || 0 }}</span
                              >
                            </div>
                            <div class="team-section">
                              <a-avatar :src="match.teamB.logo" :alt="match.teamB.name" />
                              <span class="team-name">{{ match.teamB.name }}</span>
                            </div>
                          </div>
                        </template>

                        <template #avatar>
                          <div class="live-indicator">
                            <div class="live-dot"></div>
                            <span>LIVE</span>
                          </div>
                        </template>
                      </a-list-item-meta>
                    </a-list-item>
                  </template>
                </a-list>
              </div>
            </a-tab-pane>

            <!-- 即将开始 -->
            <a-tab-pane key="upcoming" tab="即将开始">
              <div class="upcoming-section">
                <a-timeline>
                  <a-timeline-item v-for="match in upcomingMatches" :key="match.id" color="blue">
                    <template #label>
                      <div class="timeline-time">
                        {{ formatDateTime(match.startTime) }}
                      </div>
                    </template>

                    <a-card class="upcoming-match-card" hoverable @click="handleMatchClick(match)">
                      <div class="match-header">
                        <span class="tournament-name">{{ match.tournament.name }}</span>
                        <span class="match-round">{{ match.round }}</span>
                      </div>

                      <div class="upcoming-teams">
                        <div class="team-info">
                          <a-avatar :src="match.teamA.logo" :alt="match.teamA.name" />
                          <span class="team-name">{{ match.teamA.name }}</span>
                        </div>
                        <div class="vs-text">VS</div>
                        <div class="team-info">
                          <a-avatar :src="match.teamB.logo" :alt="match.teamB.name" />
                          <span class="team-name">{{ match.teamB.name }}</span>
                        </div>
                      </div>

                      <div class="match-countdown">
                        <ClockCircleOutlined />
                        <span>{{ getCountdown(match.startTime) }}</span>
                      </div>

                      <div class="upcoming-actions">
                        <a-space>
                          <a-button size="small" @click.stop="handleAddReminder(match)">
                            <BellOutlined />
                            设置提醒
                          </a-button>
                          <a-button size="small" @click.stop="handleViewDetails(match)">
                            查看详情
                          </a-button>
                        </a-space>
                      </div>
                    </a-card>
                  </a-timeline-item>
                </a-timeline>
              </div>
            </a-tab-pane>

            <!-- 赛事结果 -->
            <a-tab-pane key="results" tab="赛事结果">
              <div class="results-section">
                <a-table
                  :columns="resultColumns"
                  :data-source="completedMatches"
                  :pagination="{ pageSize: 10 }"
                  @row-click="handleMatchClick"
                >
                  <template #bodyCell="{ column, record }">
                    <template v-if="column.key === 'teams'">
                      <div class="result-teams">
                        <span class="team" :class="{ winner: record.winner === 'teamA' }">
                          {{ record.teamA.name }}
                        </span>
                        <span class="score"
                          >{{ record.finalScore.teamA }} : {{ record.finalScore.teamB }}</span
                        >
                        <span class="team" :class="{ winner: record.winner === 'teamB' }">
                          {{ record.teamB.name }}
                        </span>
                      </div>
                    </template>

                    <template v-if="column.key === 'tournament'">
                      {{ record.tournament.name }}
                    </template>

                    <template v-if="column.key === 'date'">
                      {{ formatDate(record.endTime) }}
                    </template>

                    <template v-if="column.key === 'duration'">
                      {{ formatDuration(record.duration) }}
                    </template>
                  </template>
                </a-table>
              </div>
            </a-tab-pane>
          </a-tabs>
        </div>
      </div>
    </div>
  </layout-default>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useTournamentStore } from '@/shared/stores/tournament'
import { useAuthStore } from '@/shared/stores/auth'
import { tournamentApi } from '@/shared/api/tournaments'
import {
  TrophyOutlined,
  FormOutlined,
  PlayCircleOutlined,
  ClockCircleOutlined,
  CalendarOutlined,
  TeamOutlined,
  UserOutlined,
  DollarOutlined,
  BellOutlined,
  HeartOutlined,
} from '@ant-design/icons-vue'
import type { Tournament } from '@/shared/types/tournament'

// 临时匹配类型定义（实际应从后端获取）
interface HallMatch {
  id: string
  tournament: { id: string; name: string }
  round: string
  startTime: Date | string
  endTime?: Date | string
  status: 'live' | 'upcoming' | 'completed'
  teamA: { id: string; name: string; logo: string }
  teamB: { id: string; name: string; logo: string }
  score?: { teamA: number; teamB: number }
  finalScore?: { teamA: number; teamB: number }
  winner?: string
  duration?: number
}
import LayoutDefault from '@/shared/components/layouts/LayoutDefault.vue'

const router = useRouter()
const tournamentStore = useTournamentStore()
const authStore = useAuthStore()

const activeTab = ref('registration')

// 使用真实数据
const matches = ref<HallMatch[]>([])

// 计算属性
const tournaments = computed(() => tournamentStore.tournaments)
const loading = computed(() => tournamentStore.listLoading)

const openTournaments = computed(() =>
  tournaments.value.filter(t =>
    t.status === 'registration_open' ||
    t.status === 'registration_closed' ||
    t.status === 'upcoming' ||
    t.status === 'ongoing'
  )
)

const ongoingMatches = computed(() => matches.value.filter(m => m.status === 'live'))

const upcomingMatches = computed(() => matches.value.filter(m => m.status === 'upcoming'))

const completedMatches = computed(() => matches.value.filter(m => m.status === 'completed'))

const getParticipantIcon = (tournament?: Tournament) => {
  if (!tournament) return UserOutlined
  return tournament.tournament_type === 'team_based' ? TeamOutlined : UserOutlined
}

const getParticipantUnit = (tournament: Tournament) =>
  tournament.tournament_type === 'team_based' ? '支队伍' : '名选手'

const getDisplayedRegistrationCount = (tournament: Tournament) => {
  if (!tournament) return 0
  if (tournament.tournament_type === 'team_based') {
    return tournament.team_registration_count ?? tournament.registration_count ?? tournament.registered_count ?? 0
  }
  return tournament.player_registration_count ?? tournament.registration_count ?? tournament.registered_count ?? 0
}

const getRemainingSlots = (tournament: Tournament) => {
  const used = getDisplayedRegistrationCount(tournament)
  return Math.max(tournament.max_participants - used, 0)
}


// 表格列配置
const resultColumns = [
  { title: '比赛', key: 'teams', width: '40%' },
  { title: '赛事', key: 'tournament', width: '20%' },
  { title: '日期', key: 'date', width: '15%' },
  { title: '时长', key: 'duration', width: '15%' },
  { title: '轮次', dataIndex: 'round', key: 'round', width: '10%' },
]

// 事件处理
const handleTournamentClick = (tournament: any) => {
  router.push(`/hall/tournament/${tournament.id}`)
}

const handleViewTournamentDetails = (tournament: any) => {
  router.push(`/hall/tournament/${tournament.id}`)
}

const handleMatchClick = (match: any) => {
  router.push(`/matches/${match.id}`)
}

const handleTournamentAction = async (tournament: any) => {
  if (!authStore.isAuthenticated) {
    message.warning('请先登录')
    router.push('/auth/login')
    return
  }

  switch (tournament.status) {
    case 'registration_open':
      await handleRegister(tournament)
      break

    case 'upcoming':
      router.push(`/tournaments/${tournament.id}/rooms`)
      break

    case 'ongoing':
      router.push(`/tournaments/${tournament.id}/rooms`)
      break

    case 'completed':
      router.push(`/tournaments/${tournament.id}/rooms`)
      break

    default:
      router.push(`/tournaments/${tournament.id}`)
  }
}

const handleRegister = async (tournament: any) => {
  try {
    const participantType = tournament.tournament_type === 'team_based' ? 'team' : 'player'
    await tournamentStore.registerForTournament(tournament.id, participantType)
    message.success(`已成功报名参加 ${tournament.name}`)
    // 重新加载数据以更新报名状态
    await tournamentStore.fetchTournaments({})
  } catch (error) {
    console.error('报名失败:', error)
    // 错误提示由 apiClient 拦截器统一处理，避免重复提示
  }
}

const handleWatchLive = (match: any) => {
  router.push(`/live/${match.id}`)
}

const handleViewDetails = (match: any) => {
  router.push(`/matches/${match.id}`)
}

const handleAddReminder = (match: any) => {
  message.success('提醒设置成功')
}

const handleMyMatches = () => {
  router.push('/hall/my-matches')
}

const handleMyTeam = () => {
  router.push('/teams/my-team')
}

const handlePlayerProfile = () => {
  router.push('/players/profile')
}

const handleAddToFavorites = (match: any) => {
  message.success(`已将比赛 ${match.tournament.name} ${match.round} 添加到收藏`)
}

// 工具函数
const canRegister = (tournament: Tournament) => {
  if (!authStore.isAuthenticated) return false
  if (
    getDisplayedRegistrationCount(tournament) >=
    tournament.max_participants
  )
    return false
  if (new Date() > new Date(tournament.registration_end)) return false
  return tournament.can_register
}

const canInteract = (tournament: any) => {
  if (!authStore.isAuthenticated) return true // 显示"请先登录"

  switch (tournament.status) {
    case 'registration_open':
      // 如果用户已报名，按钮不可点击（显示已报名状态）
      if (tournament.user_registered) return false
      // 如果可以报名，按钮可点击
      return canRegister(tournament)
    case 'registration_closed':
      return false // 报名已截止，按钮不可用
    case 'upcoming':
    case 'ongoing':
    case 'completed':
      return true // 其他状态可以交互
    default:
      return true
  }
}

const getRegisterButtonText = (tournament: Tournament) => {
  if (!authStore.isAuthenticated) {
    return '请先登录'
  }

  // 根据赛事状态判断按钮文本
  switch (tournament.status) {
    case 'registration_open':
      if (getDisplayedRegistrationCount(tournament) >= tournament.max_participants) {
        return '报名已满'
      }
      if (new Date() > new Date(tournament.registration_end)) {
        return '报名已截止'
      }
      if (tournament.user_registered) {
        return '已报名'
      }
      return '立即报名'

    case 'registration_closed':
      return '报名已截止'

    case 'upcoming':
      if (tournament.can_register) {
        return '等待开始'
      }
      return '进入房间'

    case 'ongoing':
      return '观看比赛'

    case 'completed':
      return '查看结果'

    default:
      return '查看详情'
  }
}

const formatDate = (date: string | Date) => {
  const d = new Date(date)
  return d.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

const formatDateTime = (date: Date | string) => {
  const d = new Date(date)
  return d.toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const formatDuration = (seconds: number) => {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  return `${hours}h ${minutes}m`
}

const getCountdown = (startTime: Date | string) => {
  const now = new Date()
  const start = new Date(startTime)
  const diff = start.getTime() - now.getTime()

  if (diff < 0) return '已开始'

  const hours = Math.floor(diff / (1000 * 60 * 60))
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))

  if (hours > 24) {
    const days = Math.floor(hours / 24)
    return `${days}天后开始`
  }

  return `${hours}小时${minutes}分钟后开始`
}

// 状态相关工具函数
const getStatusColor = (status: string) => {
  const statusColors: Record<string, string> = {
    draft: 'default',
    upcoming: 'blue',
    registration_open: 'green',
    registration_closed: 'orange',
    ongoing: 'red',
    completed: 'purple',
    cancelled: 'gray'
  }
  return statusColors[status] || 'default'
}

const getStatusText = (status: string) => {
  const statusTexts: Record<string, string> = {
    draft: '草稿',
    upcoming: '即将开始',
    registration_open: '报名中',
    registration_closed: '停止报名',
    ongoing: '进行中',
    completed: '已完成',
    cancelled: '已取消'
  }
  return statusTexts[status] || status
}

// 监听认证状态变化，自动刷新赛事列表
watch(() => authStore.isAuthenticated, async (newValue, oldValue) => {
  // 避免初始化时的无效触发
  if (oldValue !== undefined && newValue !== oldValue) {
    console.log('认证状态变化，刷新赛事列表:', { from: oldValue, to: newValue })
    try {
      await tournamentStore.fetchTournaments({})
    } catch (error) {
      console.error('刷新赛事数据失败:', error)
    }
  }
})

// 加载比赛数据
const loadMatches = async () => {
  try {
    console.log('HallView: 开始加载比赛数据')
    console.log('HallView: 当前用户信息:', authStore.user)
    console.log('HallView: 用户角色信息:', authStore.user?.roles)

    const response = await tournamentApi.getAllMatches()
    console.log('HallView: API响应:', response)
    console.log('HallView: 比赛数量:', response.matches?.length)

    matches.value = response.matches.map(match => ({
      id: match.id,
      tournament: {
        id: match.tournament_id,
        name: match.tournament_name || '未知赛事',
      },
      teamA: {
        id: match.blue_side_id,
        name: match.blue_side_name || '未知队伍',
        logo: null
      },
      teamB: {
        id: match.red_side_id,
        name: match.red_side_name || '未知队伍',
        logo: null
      },
      status: match.status === 'scheduled' ? 'upcoming' :
              match.status === 'ready' ? 'upcoming' :
              match.status === 'checking_in' ? 'upcoming' :
              match.status === 'waiting_for_checkin' ? 'upcoming' :
              match.status === 'in_progress' ? 'live' :
              match.status === 'completed' ? 'completed' : 'upcoming',
      startTime: match.scheduled_time,
      round: `第${match.round_number}轮`,
      score: match.status === 'completed' ? {
        teamA: 1, // 需要从实际数据获取
        teamB: 0
      } : undefined
    }))
  } catch (error) {
    console.error('加载比赛数据失败:', error)
    message.error('加载比赛数据失败')
  }
}

onMounted(async () => {
  // 等待认证状态初始化完成，再加载赛事数据
  try {
    // 如果用户已登录，确保认证信息是最新的
    if (authStore.token) {
      await authStore.getCurrentUser()
    }
    await tournamentStore.fetchTournaments({})
    // 加载比赛数据
    await loadMatches()
  } catch (error) {
    console.error('加载数据失败:', error)
    message.error('加载数据失败')
  }
})
</script>

<style scoped>
.hall-container {
  padding: 24px;
}

.hall-header {
  margin-bottom: 24px;
}

.hall-page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 24px;
  padding: 32px 40px;
  background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
  border-radius: 12px;
  color: white;
}

.hall-page-header .header-content {
  flex: 1;
}

.hall-page-header .page-title {
  font-size: 2.5rem;
  font-weight: 700;
  margin: 0 0 8px 0;
  background: linear-gradient(45deg, #fff, #f0f0f0);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hall-page-header .page-description {
  font-size: 1.1rem;
  margin: 0;
  opacity: 0.9;
}

.hall-page-header .header-actions {
  display: flex;
  gap: 16px;
}

.quick-nav {
  margin-bottom: 32px;
}

.nav-card {
  border: 1px solid #d9d9d9;
  transition: all 0.3s;
}

.nav-card:hover {
  border-color: #1890ff;
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.15);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px;
}

.nav-icon {
  font-size: 32px;
  color: #1890ff;
}

.nav-icon.ongoing {
  color: #f50;
}

.nav-icon.upcoming {
  color: #fa8c16;
}

.nav-icon.completed {
  color: #52c41a;
}

.nav-text {
  flex: 1;
}

.nav-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 4px;
}

.nav-desc {
  color: #666;
  font-size: 12px;
}

.tournament-card {
  height: 100%;
}

.tournament-cover {
  position: relative;
  height: 150px;
  overflow: hidden;
}

.tournament-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.tournament-status {
  position: absolute;
  top: 8px;
  right: 8px;
}

.tournament-info {
  margin: 16px 0;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  color: #666;
  font-size: 14px;
}

.tournament-actions {
  margin-top: 16px;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  gap: 16px;
}

.loading-container p {
  color: #666;
  font-size: 16px;
}

.empty-container {
  display: flex;
  justify-content: center;
  padding: 80px 0;
}

.match-item {
  cursor: pointer;
  transition: background-color 0.2s;
}

.match-item:hover {
  background-color: #fafafa;
}

.match-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tournament-name {
  font-weight: 600;
  color: #1890ff;
}

.match-round {
  color: #666;
}

.match-teams {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 8px;
}

.team-section {
  display: flex;
  align-items: center;
  gap: 8px;
}

.team-name {
  font-weight: 600;
}

.vs-section {
  display: flex;
  align-items: center;
  margin: 0 16px;
}

.score {
  font-size: 18px;
  font-weight: bold;
  color: #f50;
}

.live-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #f50;
  font-weight: bold;
  font-size: 12px;
}

.live-dot {
  width: 8px;
  height: 8px;
  background-color: #f50;
  border-radius: 50%;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
  100% {
    opacity: 1;
  }
}

.upcoming-match-card {
  margin-bottom: 0;
}

.match-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.upcoming-teams {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.team-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.vs-text {
  margin: 0 16px;
  color: #999;
  font-weight: bold;
}

.match-countdown {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  color: #fa8c16;
  font-weight: 600;
  margin-bottom: 12px;
}

.upcoming-actions {
  text-align: center;
}

.timeline-time {
  text-align: right;
  font-weight: 600;
  color: #1890ff;
}

.result-teams {
  display: flex;
  align-items: center;
  gap: 8px;
}

.result-teams .team {
  font-weight: 600;
}

.result-teams .team.winner {
  color: #52c41a;
}

.result-teams .score {
  font-size: 14px;
  color: #666;
}

@media (max-width: 768px) {
  .nav-item {
    flex-direction: column;
    text-align: center;
    gap: 8px;
  }

  .nav-icon {
    font-size: 24px;
  }

  .match-teams,
  .upcoming-teams {
    flex-direction: column;
    gap: 8px;
  }

  .vs-section,
  .vs-text {
    margin: 8px 0;
  }
}
</style>

