<template>
  <div class="tournament-management-table">
    <a-table
      :columns="columns"
      :data-source="tournaments"
      :loading="loading"
      :pagination="{
        pageSize: 20,
        showSizeChanger: true,
        showQuickJumper: true,
        showTotal: (total: number, range: [number, number]) =>
          `共 ${total} 个赛事，显示 ${range[0]}-${range[1]}`,
      }"
      row-key="id"
      size="middle"
    >
      <!-- 赛事名称和状态 -->
      <template #bodyCell="{ column, record, text }">
        <template v-if="column.key === 'name'">
          <div class="tournament-name-cell">
            <div class="tournament-title">
              <a @click="handleViewDetails(record)" class="tournament-link">
                {{ record.name }}
              </a>
              <a-tag :color="getStatusColor(record.status)" class="status-tag">
                {{ getStatusText(record.status) }}
              </a-tag>
            </div>
            <div class="tournament-subtitle">
              <span class="tournament-type">{{
                getTournamentTypeText(record.tournament_type)
              }}</span>
              <span class="tournament-region" v-if="record.region">{{ record.region }}</span>
            </div>
          </div>
        </template>

        <!-- 报名情况 -->
        <template v-if="column.key === 'participants'">
          <div class="participants-info">
            <a-progress
              :percent="getParticipationPercentage(record)"
              :stroke-color="getProgressColor(record)"
              size="small"
            />
            <span class="participant-text">
              {{ record.registered_count || 0 }} / {{ record.max_participants || 0 }}
            </span>
          </div>
        </template>

        <!-- 时间信息 -->
        <template v-if="column.key === 'schedule'">
          <div class="schedule-info">
            <div class="schedule-item">
              <CalendarOutlined />
              <span>{{ formatDate(record.tournament_start) }}</span>
            </div>
            <div class="schedule-item">
              <ClockCircleOutlined />
              <span>报名截止: {{ formatDate(record.registration_end) }}</span>
            </div>
          </div>
        </template>

        <!-- 奖金池 -->
        <template v-if="column.key === 'prize'">
          <span class="prize-amount">暂未设置</span>
        </template>

        <!-- 操作按钮 -->
        <template v-if="column.key === 'actions'">
          <a-space>
            <a-tooltip title="编辑赛事">
              <a-button type="text" size="small" @click="handleEdit(record)">
                <EditOutlined />
              </a-button>
            </a-tooltip>

            <a-dropdown>
              <a-button type="text" size="small">
                <MoreOutlined />
              </a-button>
              <template #overlay>
                <a-menu @click="(e: any) => handleMenuAction(e.key, record)">
                  <a-menu-item key="duplicate">
                    <CopyOutlined />
                    复制赛事
                  </a-menu-item>
                  <a-menu-item key="change-status">
                    <SwapOutlined />
                    修改状态
                  </a-menu-item>
                  <a-menu-divider />
                  <a-menu-item key="view-participants">
                    <TeamOutlined />
                    查看参与者
                  </a-menu-item>
                  <a-menu-item key="export-data">
                    <DownloadOutlined />
                    导出数据
                  </a-menu-item>
                  <a-menu-divider />
                  <a-menu-item key="delete" class="danger-item">
                    <DeleteOutlined />
                    删除赛事
                  </a-menu-item>
                </a-menu>
              </template>
            </a-dropdown>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 状态修改模态框 -->
    <a-modal
      v-model:open="statusModalVisible"
      title="修改赛事状态"
      @ok="handleStatusChange"
      @cancel="statusModalVisible = false"
    >
      <a-form layout="vertical">
        <a-form-item label="当前赛事">
          <span>{{ currentTournament?.name }}</span>
        </a-form-item>
        <a-form-item label="新状态">
          <a-select v-model:value="newStatus" placeholder="选择新状态">
            <a-select-option value="draft">草稿</a-select-option>
            <a-select-option value="registration_open">开放报名</a-select-option>
            <a-select-option value="registration_closed">停止报名</a-select-option>
            <a-select-option value="upcoming">即将开始</a-select-option>
            <a-select-option value="ongoing">进行中</a-select-option>
            <a-select-option value="completed">已完成</a-select-option>
            <a-select-option value="cancelled">已取消</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { message } from 'ant-design-vue'
import {
  CalendarOutlined,
  ClockCircleOutlined,
  EditOutlined,
  MoreOutlined,
  CopyOutlined,
  SwapOutlined,
  TeamOutlined,
  DownloadOutlined,
  DeleteOutlined,
} from '@ant-design/icons-vue'
import type { Tournament } from '@/shared/types/tournament'

interface Props {
  tournaments: Tournament[]
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
})

const emit = defineEmits<{
  edit: [tournament: Tournament]
  delete: [tournament: Tournament]
  duplicate: [tournament: Tournament]
  'change-status': [tournament: Tournament, status: string]
  'view-details': [tournament: Tournament]
  'view-participants': [tournament: Tournament]
}>()

// 表格列配置
const columns = [
  {
    title: '赛事信息',
    key: 'name',
    width: '30%',
    sorter: (a: Tournament, b: Tournament) => a.name.localeCompare(b.name),
  },
  {
    title: '报名情况',
    key: 'participants',
    width: '15%',
    sorter: (a: Tournament, b: Tournament) => (a.registered_count || 0) - (b.registered_count || 0),
  },
  {
    title: '时间安排',
    key: 'schedule',
    width: '20%',
    sorter: (a: Tournament, b: Tournament) =>
      new Date(a.tournament_start).getTime() - new Date(b.tournament_start).getTime(),
  },
  {
    title: '奖金池',
    key: 'prize',
    width: '10%',
  },
  {
    title: '操作',
    key: 'actions',
    width: '10%',
    fixed: 'right',
  },
]

// 状态管理
const statusModalVisible = ref(false)
const currentTournament = ref<Tournament | null>(null)
const newStatus = ref('')

// 事件处理
const handleEdit = (tournament: Tournament) => {
  emit('edit', tournament)
}

const handleViewDetails = (tournament: Tournament) => {
  emit('view-details', tournament)
}

const handleMenuAction = (key: string, tournament: Tournament) => {
  switch (key) {
    case 'duplicate':
      emit('duplicate', tournament)
      break
    case 'change-status':
      currentTournament.value = tournament
      newStatus.value = tournament.status
      statusModalVisible.value = true
      break
    case 'view-participants':
      emit('view-participants', tournament)
      break
    case 'export-data':
      message.info('导出数据功能开发中')
      break
    case 'delete':
      emit('delete', tournament)
      break
  }
}

const handleStatusChange = () => {
  if (currentTournament.value && newStatus.value) {
    emit('change-status', currentTournament.value, newStatus.value)
    statusModalVisible.value = false
  }
}

// 工具函数
const getStatusColor = (status: string) => {
  const statusColors: Record<string, string> = {
    draft: 'default',
    registration_open: 'green',
    registration_closed: 'orange',
    upcoming: 'blue',
    ongoing: 'red',
    completed: 'success',
    cancelled: 'error',
  }
  return statusColors[status] || 'default'
}

const getStatusText = (status: string) => {
  const statusTexts: Record<string, string> = {
    draft: '草稿',
    registration_open: '开放报名',
    registration_closed: '停止报名',
    upcoming: '即将开始',
    ongoing: '进行中',
    completed: '已完成',
    cancelled: '已取消',
  }
  return statusTexts[status] || status
}

const getTournamentTypeText = (type: string) => {
  const typeTexts: Record<string, string> = {
    team_based: '战队赛',
    solo_based: '个人赛',
  }
  return typeTexts[type] || type
}

const getParticipationPercentage = (tournament: Tournament) => {
  const current = tournament.registered_count || 0
  const max = tournament.max_participants || 1
  return Math.round((current / max) * 100)
}

const getProgressColor = (tournament: Tournament) => {
  const percentage = getParticipationPercentage(tournament)
  if (percentage >= 90) return '#f5222d'
  if (percentage >= 70) return '#fa8c16'
  if (percentage >= 50) return '#1890ff'
  return '#52c41a'
}

const formatDate = (date: string | Date) => {
  const d = new Date(date)
  return d.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}
</script>

<style scoped>
.tournament-management-table :deep(.ant-table) {
  font-size: 14px;
}

.tournament-name-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tournament-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tournament-link {
  color: #1890ff;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
}

.tournament-link:hover {
  color: #40a9ff;
  text-decoration: underline;
}

.status-tag {
  font-size: 12px;
}

.tournament-subtitle {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #666;
  font-size: 12px;
}

.tournament-type {
  background: #f0f0f0;
  padding: 2px 6px;
  border-radius: 4px;
}

.participants-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.participant-text {
  font-size: 12px;
  color: #666;
  text-align: center;
}

.schedule-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.schedule-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #666;
}

.prize-amount {
  font-weight: 600;
  color: #f5222d;
}

.danger-item {
  color: #f5222d !important;
}

.danger-item:hover {
  background-color: #fff2f0 !important;
}

@media (max-width: 768px) {
  .tournament-management-table :deep(.ant-table) {
    font-size: 12px;
  }

  .tournament-title {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .schedule-info {
    gap: 2px;
  }

  .participants-info {
    gap: 2px;
  }
}
</style>
