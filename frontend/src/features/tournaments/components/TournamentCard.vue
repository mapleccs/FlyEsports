<template>
  <div class="tournament-card">
    <a-card :hoverable="true" class="card-container" :body-style="{ padding: 0 }">
      <!-- 赛事横幅/图片 -->
      <div class="card-banner">
        <img
          v-if="tournament.banner_url"
          :src="tournament.banner_url"
          :alt="tournament.name"
          class="banner-image"
        />
        <div v-else class="banner-placeholder">
          <trophy-outlined class="banner-icon" />
        </div>

        <!-- 状态标签 -->
        <div class="status-badge">
          <a-tag :color="statusConfig.color" class="status-tag">
            {{ statusConfig.text }}
          </a-tag>
        </div>

        <!-- 赛事类型标签 -->
        <div class="type-badge">
          <a-tag :color="typeConfig.color" class="type-tag">
            {{ typeConfig.text }}
          </a-tag>
        </div>
      </div>

      <!-- 卡片内容 -->
      <div class="card-content">
        <!-- 赛事标题和Logo -->
        <div class="title-section">
          <div class="title-with-logo">
            <img
              v-if="tournament.logo_url"
              :src="tournament.logo_url"
              :alt="tournament.name"
              class="tournament-logo"
            />
            <h3 class="tournament-title" :title="tournament.name">
              {{ tournament.name }}
            </h3>
          </div>
        </div>

        <!-- 赛事描述 -->
        <div v-if="tournament.description" class="description">
          <p class="description-text">{{ truncatedDescription }}</p>
        </div>

        <!-- 赛事信息 -->
        <div class="tournament-info">
          <div class="info-row">
            <team-outlined class="info-icon" />
            <span class="info-text">
              {{ tournament.registered_count }} / {{ tournament.max_participants }}
              {{ tournament.tournament_type === 'team_based' ? '支队伍' : '名选手' }}
            </span>
          </div>

          <div v-if="tournament.min_rank || tournament.max_rank" class="info-row">
            <star-outlined class="info-icon" />
            <span class="info-text"> 段位要求: {{ rankRequirement }} </span>
          </div>

          <div class="info-row">
            <calendar-outlined class="info-icon" />
            <span class="info-text">
              {{ formatTime(tournament.tournament_start) }}
            </span>
          </div>
        </div>

        <!-- 报名进度条 -->
        <div class="progress-section">
          <a-progress
            :percent="registrationPercent"
            :show-info="false"
            :stroke-color="progressColor"
            :trail-color="'#f0f0f0'"
            stroke-width="6"
          />
          <div class="progress-text">
            <span class="progress-label">报名进度</span>
            <span class="progress-value">{{ registrationPercent }}%</span>
          </div>
        </div>

        <!-- 行动按钮 -->
        <div class="action-section">
          <a-button
            v-if="showRegisterButton"
            type="primary"
            block
            size="large"
            :loading="isRegistering"
            @click="handleRegister"
          >
            立即报名
          </a-button>

          <a-button
            v-else-if="showUnregisterButton"
            block
            size="large"
            :loading="isRegistering"
            @click="handleUnregister"
          >
            取消报名
          </a-button>

          <a-button
            v-else
            block
            size="large"
            :disabled="!canViewDetails"
            @click="handleViewDetails"
          >
            {{ actionButtonText }}
          </a-button>
        </div>

        <!-- 快捷操作 -->
        <div class="quick-actions">
          <a-button type="text" size="small" @click="handleViewDetails" class="quick-action-btn">
            查看详情
          </a-button>

          <a-button
            v-if="showShareButton"
            type="text"
            size="small"
            @click="handleShare"
            class="quick-action-btn"
          >
            分享赛事
          </a-button>
        </div>
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { computed, defineEmits, defineProps } from 'vue'
import { TrophyOutlined, TeamOutlined, StarOutlined, CalendarOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { useAuthStore } from '@/shared/stores/auth'
import type { Tournament } from '@/shared/types/tournament'

// Props
interface Props {
  tournament: Tournament
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
})

// Emits
const emit = defineEmits<{
  register: [tournament: Tournament]
  unregister: [tournament: Tournament]
  viewDetails: [tournament: Tournament]
}>()

// 组合式API
const authStore = useAuthStore()

// 计算属性
const statusConfig = computed(() => {
  const statusMap = {
    draft: { color: 'default', text: '草稿' },
    upcoming: { color: 'blue', text: '即将开始' },
    registration_open: { color: 'green', text: '正在报名' },
    registration_closed: { color: 'orange', text: '报名结束' },
    ongoing: { color: 'purple', text: '进行中' },
    completed: { color: 'gray', text: '已完成' },
    cancelled: { color: 'red', text: '已取消' },
  }

  return statusMap[props.tournament.status] || statusMap.draft
})

const typeConfig = computed(() => {
  const typeMap = {
    team_based: { color: 'blue', text: '战队赛' },
    solo_based: { color: 'green', text: '个人赛' },
  }

  return typeMap[props.tournament.tournament_type] || typeMap.team_based
})

const truncatedDescription = computed(() => {
  if (!props.tournament.description) return ''
  const maxLength = 100
  return props.tournament.description.length > maxLength
    ? `${props.tournament.description.substring(0, maxLength)}...`
    : props.tournament.description
})

const rankRequirement = computed(() => {
  const { min_rank, max_rank } = props.tournament
  if (min_rank && max_rank) {
    return `${min_rank} - ${max_rank}`
  } else if (min_rank) {
    return `${min_rank} 以上`
  } else if (max_rank) {
    return `${max_rank} 以下`
  } else {
    return '无限制'
  }
})

const registrationPercent = computed(() => {
  const { registered_count, registration_count, max_participants } = props.tournament
  const count = registered_count || registration_count || 0
  return Math.round((count / max_participants) * 100)
})

const progressColor = computed(() => {
  const percent = registrationPercent.value
  if (percent >= 90) return '#ff4d4f'
  if (percent >= 70) return '#faad14'
  return '#52c41a'
})

const isRegistering = computed(() => props.loading)

const showRegisterButton = computed(() => {
  return (
    authStore.isAuthenticated &&
    props.tournament.status === 'registration_open' &&
    props.tournament.can_register &&
    (props.tournament.registered_count || props.tournament.registration_count || 0) <
      props.tournament.max_participants
  )
})

const showUnregisterButton = computed(() => {
  return (
    authStore.isAuthenticated &&
    props.tournament.status === 'registration_open' &&
    !props.tournament.can_register
  ) // 用户已经报名
})

const canViewDetails = computed(() => true)

const showShareButton = computed(() => {
  return props.tournament.status !== 'draft' && props.tournament.status !== 'cancelled'
})

const actionButtonText = computed(() => {
  switch (props.tournament.status) {
    case 'draft':
      return '草稿状态'
    case 'upcoming':
      return '等待开始'
    case 'registration_closed':
      return '报名已结束'
    case 'ongoing':
      return '查看比赛'
    case 'completed':
      return '查看结果'
    case 'cancelled':
      return '赛事取消'
    default:
      return '查看详情'
  }
})

// 方法
const formatTime = (timeString: string) => {
  const date = new Date(timeString)
  return date.toLocaleString('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const handleRegister = () => {
  if (!authStore.isAuthenticated) {
    message.warning('请先登录')
    return
  }
  emit('register', props.tournament)
}

const handleUnregister = () => {
  emit('unregister', props.tournament)
}

const handleViewDetails = () => {
  emit('viewDetails', props.tournament)
}

const handleShare = () => {
  const url = `${window.location.origin}/tournaments/${props.tournament.id}`

  if (navigator.share) {
    navigator
      .share({
        title: props.tournament.name,
        text: `来参加 ${props.tournament.name} 赛事吧！`,
        url,
      })
      .catch(err => console.log('分享失败:', err))
  } else {
    navigator.clipboard
      .writeText(url)
      .then(() => {
        message.success('链接已复制到剪贴板')
      })
      .catch(() => {
        message.error('复制链接失败')
      })
  }
}
</script>

<style scoped>
.tournament-card {
  height: 100%;
}

.card-container {
  height: 100%;
  transition: all 0.3s ease;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.card-container:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

.card-banner {
  position: relative;
  height: 160px;
  overflow: hidden;
}

.banner-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.card-container:hover .banner-image {
  transform: scale(1.05);
}

.banner-placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.banner-icon {
  font-size: 48px;
  color: white;
  opacity: 0.8;
}

.status-badge {
  position: absolute;
  top: 12px;
  right: 12px;
}

.status-tag {
  font-weight: 500;
  border: none;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
}

.type-badge {
  position: absolute;
  top: 12px;
  left: 12px;
}

.type-tag {
  font-weight: 500;
  border: none;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
}

.card-content {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: calc(100% - 160px);
}

.title-section {
  flex-shrink: 0;
}

.title-with-logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.tournament-logo {
  width: 32px;
  height: 32px;
  border-radius: 4px;
  object-fit: cover;
  flex-shrink: 0;
}

.tournament-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #262626;
  line-height: 1.4;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.description {
  flex-shrink: 0;
}

.description-text {
  margin: 0;
  font-size: 14px;
  color: #666;
  line-height: 1.5;
}

.tournament-info {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-icon {
  color: #666;
  font-size: 14px;
  flex-shrink: 0;
}

.info-text {
  font-size: 14px;
  color: #666;
  line-height: 1.4;
}

.progress-section {
  flex-shrink: 0;
  margin-top: auto;
}

.progress-text {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 6px;
}

.progress-label {
  font-size: 12px;
  color: #999;
}

.progress-value {
  font-size: 12px;
  font-weight: 500;
  color: #262626;
}

.action-section {
  flex-shrink: 0;
  margin-top: 8px;
}

.quick-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
}

.quick-action-btn {
  padding: 0;
  height: auto;
  color: #666;
  font-size: 12px;
}

.quick-action-btn:hover {
  color: #1890ff;
}

/* 响应式设计 */
@media (max-width: 480px) {
  .card-content {
    padding: 16px;
    gap: 12px;
  }

  .tournament-title {
    font-size: 16px;
  }

  .banner-placeholder {
    height: 140px;
  }

  .card-banner {
    height: 140px;
  }

  .card-content {
    height: calc(100% - 140px);
  }
}
</style>
