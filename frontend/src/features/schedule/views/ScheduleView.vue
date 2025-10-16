<template>
  <layout-default>
    <div class="schedule-container">
      <div class="schedule-header">
        <a-page-header title="赛程中心" sub-title="查看所有赛事的详细赛程安排">
          <template #extra>
            <a-space>
              <a-button @click="handleExportSchedule">
                <DownloadOutlined />
                导出赛程
              </a-button>
              <a-button type="primary" @click="handleSubscribeSchedule">
                <BellOutlined />
                订阅提醒
              </a-button>
            </a-space>
          </template>
        </a-page-header>
      </div>

      <div class="schedule-content">
        <!-- 筛选器 -->
        <div class="schedule-filters">
          <a-row :gutter="16">
            <a-col :xs="24" :sm="12" :md="6">
              <a-select
                v-model:value="selectedTournament"
                placeholder="选择赛事"
                style="width: 100%"
                @change="handleTournamentChange"
              >
                <a-select-option value="">全部赛事</a-select-option>
                <a-select-option
                  v-for="tournament in tournaments"
                  :key="tournament.id"
                  :value="tournament.id"
                >
                  {{ tournament.name }}
                </a-select-option>
              </a-select>
            </a-col>
            <a-col :xs="24" :sm="12" :md="6">
              <a-select
                v-model:value="selectedStatus"
                placeholder="比赛状态"
                style="width: 100%"
                @change="handleStatusChange"
              >
                <a-select-option value="">全部状态</a-select-option>
                <a-select-option value="upcoming">即将开始</a-select-option>
                <a-select-option value="live">进行中</a-select-option>
                <a-select-option value="ended">已结束</a-select-option>
              </a-select>
            </a-col>
            <a-col :xs="24" :sm="12" :md="6">
              <a-date-picker
                v-model:value="selectedDate"
                placeholder="选择日期"
                style="width: 100%"
                @change="handleDateChange"
              />
            </a-col>
            <a-col :xs="24" :sm="12" :md="6">
              <a-button @click="handleResetFilters" style="width: 100%"> 重置筛选 </a-button>
            </a-col>
          </a-row>
        </div>

        <!-- 日历视图切换 -->
        <div class="view-controls">
          <a-radio-group v-model:value="viewMode" @change="handleViewModeChange">
            <a-radio-button value="list">列表视图</a-radio-button>
            <a-radio-button value="calendar">日历视图</a-radio-button>
          </a-radio-group>
        </div>

        <!-- 列表视图 -->
        <div v-if="viewMode === 'list'" class="schedule-list">
          <a-timeline mode="left">
            <a-timeline-item
              v-for="match in filteredMatches"
              :key="match.id"
              :color="getMatchColor(match.status)"
            >
              <template #label>
                <div class="timeline-label">
                  <div class="match-time">{{ formatDateTime(match.startTime) }}</div>
                  <a-tag :color="getMatchColor(match.status)">
                    {{ getStatusText(match.status) }}
                  </a-tag>
                </div>
              </template>

              <a-card class="match-card" hoverable @click="handleMatchClick(match)">
                <div class="match-info">
                  <div class="match-header">
                    <span class="tournament-name">{{ match.tournament.name }}</span>
                    <span class="match-round">{{ match.round }}</span>
                  </div>

                  <div class="teams-section">
                    <div class="team-info">
                      <a-avatar :src="match.teamA.logo" :alt="match.teamA.name" />
                      <span class="team-name">{{ match.teamA.name }}</span>
                    </div>

                    <div class="vs-section">
                      <span class="vs-text">VS</span>
                      <div v-if="match.score" class="score">
                        {{ match.score.teamA }} : {{ match.score.teamB }}
                      </div>
                    </div>

                    <div class="team-info">
                      <a-avatar :src="match.teamB.logo" :alt="match.teamB.name" />
                      <span class="team-name">{{ match.teamB.name }}</span>
                    </div>
                  </div>

                  <div class="match-actions">
                    <a-space>
                      <a-button
                        v-if="match.status === 'live'"
                        type="primary"
                        size="small"
                        @click.stop="handleWatchLive(match)"
                      >
                        <PlayCircleOutlined />
                        观看直播
                      </a-button>
                      <a-button size="small" @click.stop="handleViewDetails(match)">
                        查看详情
                      </a-button>
                      <a-button
                        v-if="match.status === 'upcoming'"
                        size="small"
                        @click.stop="handleAddReminder(match)"
                      >
                        <BellOutlined />
                        添加提醒
                      </a-button>
                    </a-space>
                  </div>
                </div>
              </a-card>
            </a-timeline-item>
          </a-timeline>
        </div>

        <!-- 日历视图 -->
        <div v-if="viewMode === 'calendar'" class="schedule-calendar">
          <a-calendar v-model:value="calendarValue" @select="handleCalendarSelect">
            <template #dateCellRender="{ current }">
              <div class="calendar-matches">
                <div
                  v-for="match in getMatchesForDate(current)"
                  :key="match.id"
                  class="calendar-match"
                  :class="`status-${match.status}`"
                  @click="handleMatchClick(match)"
                >
                  <div class="match-time">{{ formatTime(match.startTime) }}</div>
                  <div class="match-teams">
                    {{ match.teamA.shortName }} vs {{ match.teamB.shortName }}
                  </div>
                </div>
              </div>
            </template>
          </a-calendar>
        </div>

        <!-- 空状态 -->
        <a-empty
          v-if="filteredMatches.length === 0"
          description="暂无赛程安排"
          :image="Empty.PRESENTED_IMAGE_SIMPLE"
        >
          <a-button type="primary" @click="$router.push('/tournaments')"> 查看赛事 </a-button>
        </a-empty>
      </div>
    </div>
  </layout-default>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Empty } from 'ant-design-vue'
import { DownloadOutlined, BellOutlined, PlayCircleOutlined } from '@ant-design/icons-vue'
import LayoutDefault from '@/shared/components/layouts/LayoutDefault.vue'
import { formatDate, createDateInstance } from '@/utils/dateUtils'
import type { DateInstance } from '@/utils/dateUtils'

const router = useRouter()

// 筛选状态
const selectedTournament = ref('')
const selectedStatus = ref('')
const selectedDate = ref<DateInstance>()
const viewMode = ref('list')
const calendarValue = ref(createDateInstance())

// 数据
const tournaments = ref([
  { id: 1, name: 'FlyEsports 春季赛' },
  { id: 2, name: 'FlyEsports 夏季赛' },
])

const matches = ref([
  {
    id: 1,
    tournament: { id: 1, name: 'FlyEsports 春季赛' },
    round: '半决赛',
    startTime: new Date(),
    status: 'live',
    teamA: {
      id: 1,
      name: 'Thunder Hawks',
      shortName: 'TH',
      logo: 'https://via.placeholder.com/40x40?text=TH',
    },
    teamB: {
      id: 2,
      name: 'Lightning Wolves',
      shortName: 'LW',
      logo: 'https://via.placeholder.com/40x40?text=LW',
    },
    score: { teamA: 1, teamB: 0 },
  },
  {
    id: 2,
    tournament: { id: 1, name: 'FlyEsports 春季赛' },
    round: '决赛',
    startTime: new Date(Date.now() + 24 * 60 * 60 * 1000),
    status: 'upcoming',
    teamA: {
      id: 3,
      name: 'Storm Eagles',
      shortName: 'SE',
      logo: 'https://via.placeholder.com/40x40?text=SE',
    },
    teamB: {
      id: 4,
      name: 'Fire Dragons',
      shortName: 'FD',
      logo: 'https://via.placeholder.com/40x40?text=FD',
    },
  },
])

const filteredMatches = computed(() => {
  return matches.value.filter(match => {
    if (selectedTournament.value && match.tournament.id !== Number(selectedTournament.value))
      return false
    if (selectedStatus.value && match.status !== selectedStatus.value) return false
    if (selectedDate.value) {
      const matchDate = formatDate(match.startTime, 'YYYY-MM-DD')
      const filterDate = selectedDate.value.format('YYYY-MM-DD')
      if (matchDate !== filterDate) return false
    }
    return true
  })
})

// 事件处理
const handleTournamentChange = () => {}
const handleStatusChange = () => {}
const handleDateChange = () => {}
const handleViewModeChange = () => {}

const handleResetFilters = () => {
  selectedTournament.value = ''
  selectedStatus.value = ''
  selectedDate.value = undefined
}

const handleMatchClick = (match: any) => {
  router.push(`/matches/${match.id}`)
}

const handleWatchLive = (match: any) => {
  router.push(`/live/${match.id}`)
}

const handleViewDetails = (match: any) => {
  router.push(`/matches/${match.id}`)
}

const handleAddReminder = (match: any) => {
  // 添加提醒功能
  console.log('Add reminder for match:', match.id)
}

const handleExportSchedule = () => {
  // 导出赛程功能
  console.log('Export schedule')
}

const handleSubscribeSchedule = () => {
  // 订阅提醒功能
  console.log('Subscribe to schedule updates')
}

const handleCalendarSelect = (date: any) => {
  selectedDate.value = createDateInstance(date)
}

// 工具函数
const getMatchColor = (status: string) => {
  switch (status) {
    case 'live':
      return 'red'
    case 'upcoming':
      return 'blue'
    case 'ended':
      return 'gray'
    default:
      return 'default'
  }
}

const getStatusText = (status: string) => {
  switch (status) {
    case 'live':
      return '进行中'
    case 'upcoming':
      return '即将开始'
    case 'ended':
      return '已结束'
    default:
      return '未知'
  }
}

const formatDateTime = (date: Date) => {
  return formatDate(date, 'MM月DD日 HH:mm')
}

const formatTime = (date: Date) => {
  return formatDate(date, 'HH:mm')
}

const getMatchesForDate = (date: any) => {
  const dateStr =
    typeof date.format === 'function' ? date.format('YYYY-MM-DD') : formatDate(date, 'YYYY-MM-DD')
  return matches.value.filter(match => formatDate(match.startTime, 'YYYY-MM-DD') === dateStr)
}

onMounted(() => {
  // 加载数据
})
</script>

<style scoped>
.schedule-container {
  padding: 24px;
}

.schedule-header {
  margin-bottom: 24px;
}

.schedule-filters {
  margin-bottom: 24px;
  padding: 16px;
  background: #fafafa;
  border-radius: 6px;
}

.view-controls {
  margin-bottom: 24px;
}

.timeline-label {
  text-align: right;
  min-width: 120px;
}

.match-time {
  font-weight: 600;
  margin-bottom: 4px;
}

.match-card {
  margin-bottom: 0;
}

.match-info {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.match-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tournament-name {
  font-weight: 600;
  color: #1890ff;
}

.match-round {
  color: #666;
  font-size: 14px;
}

.teams-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.team-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.team-name {
  font-weight: 600;
}

.vs-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin: 0 16px;
}

.vs-text {
  color: #999;
  font-size: 12px;
}

.score {
  font-size: 18px;
  font-weight: bold;
  color: #1890ff;
  margin-top: 4px;
}

.match-actions {
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}

.schedule-calendar {
  background: white;
  border-radius: 6px;
}

.calendar-matches {
  max-height: 60px;
  overflow: hidden;
}

.calendar-match {
  font-size: 11px;
  padding: 2px 4px;
  margin-bottom: 2px;
  border-radius: 2px;
  cursor: pointer;
  transition: all 0.2s;
}

.calendar-match:hover {
  opacity: 0.8;
}

.calendar-match.status-live {
  background: #ffe7e7;
  border-left: 3px solid #ff4d4f;
}

.calendar-match.status-upcoming {
  background: #e6f7ff;
  border-left: 3px solid #1890ff;
}

.calendar-match.status-ended {
  background: #f5f5f5;
  border-left: 3px solid #d9d9d9;
}

.match-teams {
  font-weight: 600;
}

@media (max-width: 768px) {
  .teams-section {
    flex-direction: column;
    gap: 12px;
  }

  .vs-section {
    margin: 0;
  }
}
</style>
