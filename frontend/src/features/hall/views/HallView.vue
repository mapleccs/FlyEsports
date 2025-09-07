<template>
  <layout-default>
    <div class="hall-container">
      <div class="hall-header">
        <a-page-header
          title="比赛大厅"
          sub-title="参与赛事报名，查看比赛进度"
        >
          <template #extra>
            <a-space>
              <a-button @click="$router.push('/tournaments/create')">
                <PlusOutlined />
                创建赛事
              </a-button>
              <a-button type="primary" @click="handleMyMatches">
                <TrophyOutlined />
                我的比赛
              </a-button>
            </a-space>
          </template>
        </a-page-header>
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
                    <div class="nav-title">赛事报名</div>
                    <div class="nav-desc">{{ openTournaments.length }}个赛事开放报名</div>
                  </div>
                </div>
              </a-card>
            </a-col>
            <a-col :xs="12" :sm="6">
              <a-card class="nav-card" hoverable @click="activeTab = 'ongoing'">
                <div class="nav-item">
                  <PlayCircleOutlined class="nav-icon ongoing" />
                  <div class="nav-text">
                    <div class="nav-title">进行中</div>
                    <div class="nav-desc">{{ ongoingMatches.length }}场比赛进行中</div>
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
                    <div class="nav-title">比赛结果</div>
                    <div class="nav-desc">查看历史比赛结果</div>
                  </div>
                </div>
              </a-card>
            </a-col>
          </a-row>
        </div>

        <!-- 标签页内容 -->
        <div class="hall-tabs">
          <a-tabs v-model:activeKey="activeTab" size="large">
            <!-- 赛事报名 -->
            <a-tab-pane key="registration" tab="赛事报名">
              <div class="registration-section">
                <a-row :gutter="[16, 16]">
                  <a-col :xs="24" :sm="12" :xl="8" v-for="tournament in openTournaments" :key="tournament.id">
                    <a-card 
                      class="tournament-card"
                      hoverable
                      @click="handleTournamentClick(tournament)"
                    >
                      <template #cover>
                        <div class="tournament-cover">
                          <img :src="tournament.banner" :alt="tournament.name" />
                          <div class="tournament-status">
                            <a-tag color="green">报名中</a-tag>
                          </div>
                        </div>
                      </template>
                      
                      <a-card-meta :title="tournament.name" :description="tournament.description" />
                      
                      <div class="tournament-info">
                        <div class="info-item">
                          <CalendarOutlined />
                          <span>{{ formatDate(tournament.startDate) }} 开始</span>
                        </div>
                        <div class="info-item">
                          <TeamOutlined />
                          <span>{{ tournament.participantCount }} / {{ tournament.maxParticipants }} 支队伍</span>
                        </div>
                        <div class="info-item">
                          <DollarOutlined />
                          <span>奖金池: {{ tournament.prizePool }}</span>
                        </div>
                        <div class="info-item">
                          <ClockCircleOutlined />
                          <span>报名截止: {{ formatDate(tournament.registrationDeadline) }}</span>
                        </div>
                      </div>
                      
                      <div class="tournament-actions">
                        <a-button 
                          type="primary" 
                          block
                          @click.stop="handleRegister(tournament)"
                          :disabled="!canRegister(tournament)"
                        >
                          {{ getRegisterButtonText(tournament) }}
                        </a-button>
                      </div>
                    </a-card>
                  </a-col>
                </a-row>
              </div>
            </a-tab-pane>

            <!-- 进行中的比赛 -->
            <a-tab-pane key="ongoing" tab="进行中">
              <div class="ongoing-section">
                <a-list
                  :data-source="ongoingMatches"
                  :pagination="false"
                  item-layout="horizontal"
                >
                  <template #renderItem="{ item: match }">
                    <a-list-item class="match-item" @click="handleMatchClick(match)">
                      <template #actions>
                        <a-space>
                          <a-button type="primary" @click.stop="handleWatchLive(match)">
                            <PlayCircleOutlined />
                            观看直播
                          </a-button>
                          <a-button @click.stop="handleViewDetails(match)">
                            查看详情
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
                              <span class="score">{{ match.score?.teamA || 0 }} : {{ match.score?.teamB || 0 }}</span>
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
                  <a-timeline-item
                    v-for="match in upcomingMatches"
                    :key="match.id"
                    color="blue"
                  >
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

            <!-- 比赛结果 -->
            <a-tab-pane key="results" tab="比赛结果">
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
                        <span class="score">{{ record.finalScore.teamA }} : {{ record.finalScore.teamB }}</span>
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
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  PlusOutlined,
  TrophyOutlined,
  FormOutlined,
  PlayCircleOutlined,
  ClockCircleOutlined,
  CalendarOutlined,
  TeamOutlined,
  DollarOutlined,
  BellOutlined
} from '@ant-design/icons-vue'
import LayoutDefault from '@/shared/components/layouts/LayoutDefault.vue'

const router = useRouter()

const activeTab = ref('registration')

// 模拟数据
const tournaments = ref([
  {
    id: 1,
    name: 'FlyEsports 春季赛',
    description: '激烈的春季赛事，争夺冠军宝座',
    banner: 'https://via.placeholder.com/300x150?text=Spring+Tournament',
    startDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000),
    registrationDeadline: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000),
    participantCount: 12,
    maxParticipants: 16,
    prizePool: '￥50,000',
    status: 'registration'
  }
])

const matches = ref([
  {
    id: 1,
    tournament: { id: 1, name: 'FlyEsports 春季赛' },
    round: '半决赛',
    startTime: new Date(),
    endTime: new Date(Date.now() + 2 * 60 * 60 * 1000),
    status: 'live',
    teamA: { 
      id: 1, 
      name: 'Thunder Hawks',
      logo: 'https://via.placeholder.com/40x40?text=TH'
    },
    teamB: { 
      id: 2, 
      name: 'Lightning Wolves',
      logo: 'https://via.placeholder.com/40x40?text=LW'
    },
    score: { teamA: 1, teamB: 0 }
  },
  {
    id: 2,
    tournament: { id: 1, name: 'FlyEsports 春季赛' },
    round: '决赛',
    startTime: new Date(Date.now() + 2 * 60 * 60 * 1000),
    status: 'upcoming',
    teamA: { 
      id: 3, 
      name: 'Storm Eagles',
      logo: 'https://via.placeholder.com/40x40?text=SE'
    },
    teamB: { 
      id: 4, 
      name: 'Fire Dragons',
      logo: 'https://via.placeholder.com/40x40?text=FD'
    }
  },
  {
    id: 3,
    tournament: { id: 1, name: 'FlyEsports 冬季赛' },
    round: '决赛',
    startTime: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000),
    endTime: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000 + 2 * 60 * 60 * 1000),
    status: 'completed',
    teamA: { 
      id: 5, 
      name: 'Ice Phoenixes',
      logo: 'https://via.placeholder.com/40x40?text=IP'
    },
    teamB: { 
      id: 6, 
      name: 'Snow Leopards',
      logo: 'https://via.placeholder.com/40x40?text=SL'
    },
    finalScore: { teamA: 3, teamB: 1 },
    winner: 'teamA',
    duration: 7800 // 2小时10分钟
  }
])

// 计算属性
const openTournaments = computed(() => 
  tournaments.value.filter(t => t.status === 'registration')
)

const ongoingMatches = computed(() => 
  matches.value.filter(m => m.status === 'live')
)

const upcomingMatches = computed(() => 
  matches.value.filter(m => m.status === 'upcoming')
)

const completedMatches = computed(() => 
  matches.value.filter(m => m.status === 'completed')
)

// 表格列配置
const resultColumns = [
  { title: '比赛', key: 'teams', width: '40%' },
  { title: '赛事', key: 'tournament', width: '20%' },
  { title: '日期', key: 'date', width: '15%' },
  { title: '时长', key: 'duration', width: '15%' },
  { title: '轮次', dataIndex: 'round', key: 'round', width: '10%' }
]

// 事件处理
const handleTournamentClick = (tournament: any) => {
  router.push(`/tournaments/${tournament.id}`)
}

const handleMatchClick = (match: any) => {
  router.push(`/matches/${match.id}`)
}

const handleRegister = (tournament: any) => {
  message.success(`已成功报名参加 ${tournament.name}`)
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

// 工具函数
const canRegister = (tournament: any) => {
  return tournament.participantCount < tournament.maxParticipants &&
         new Date() < tournament.registrationDeadline
}

const getRegisterButtonText = (tournament: any) => {
  if (tournament.participantCount >= tournament.maxParticipants) {
    return '报名已满'
  }
  if (new Date() > tournament.registrationDeadline) {
    return '报名已截止'
  }
  return '立即报名'
}

const formatDate = (date: Date) => {
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

const formatDateTime = (date: Date) => {
  return date.toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatDuration = (seconds: number) => {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  return `${hours}h ${minutes}m`
}

const getCountdown = (startTime: Date) => {
  const now = new Date()
  const diff = startTime.getTime() - now.getTime()
  
  if (diff < 0) return '已开始'
  
  const hours = Math.floor(diff / (1000 * 60 * 60))
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
  
  if (hours > 24) {
    const days = Math.floor(hours / 24)
    return `${days}天后开始`
  }
  
  return `${hours}小时${minutes}分钟后开始`
}

onMounted(() => {
  // 加载数据
})
</script>

<style scoped>
.hall-container {
  padding: 24px;
}

.hall-header {
  margin-bottom: 24px;
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
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
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