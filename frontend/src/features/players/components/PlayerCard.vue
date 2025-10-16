<template>
  <div
    class="player-card"
    :class="{ selected, 'free-agent': player.contract_status === 'free_agent' }"
    @click="handleSelect"
  >
    <!-- 选择checkbox -->
    <div class="select-checkbox">
      <a-checkbox :checked="selected" @click.stop />
    </div>

    <!-- 合同状态标签 -->
    <div class="contract-badge">
      <a-tag :color="getContractColor(player.contract_status)">
        {{ getContractLabel(player.contract_status) }}
      </a-tag>
    </div>

    <!-- 选手头像和基本信息 -->
    <div class="player-header">
      <div class="avatar-section">
        <a-avatar
          :size="60"
          :src="player.avatar_url"
          :style="{ backgroundColor: getTierColor(player.rating.current_score) }"
        >
          {{ player.display_name?.[0] || player.username[0] }}
        </a-avatar>
        <div class="rating-tier">
          {{ getRatingTier(player.rating.current_score) }}
        </div>
      </div>

      <div class="player-info">
        <h3 class="player-name">{{ player.display_name || player.username }}</h3>
        <div class="username">@{{ player.username }}</div>
        <div class="positions">
          <a-tag color="blue">{{ getPositionName(player.primary_position) }}</a-tag>
          <a-tag v-if="player.secondary_position" color="cyan">
            {{ getPositionName(player.secondary_position) }}
          </a-tag>
        </div>
      </div>
    </div>

    <!-- 评分信息 -->
    <div class="rating-section">
      <div class="current-rating">
        <div class="rating-value">
          {{ Math.round(player.rating.current_score) }}
          <span class="rating-label">分</span>
        </div>
        <div class="confidence">
          置信度: {{ (player.rating.confidence_level * 100).toFixed(1) }}%
        </div>
      </div>

      <div class="rating-progress">
        <a-progress
          :percent="getRatingPercent(player.rating.current_score)"
          :stroke-color="getTierColor(player.rating.current_score)"
          :show-info="false"
          size="small"
        />
      </div>
    </div>

    <!-- 六维度雷达图 -->
    <div class="dimensions-section">
      <div class="dimensions-title">六维能力</div>
      <div class="dimensions-grid">
        <div
          v-for="(value, key) in player.rating.six_dimensions"
          :key="key"
          class="dimension-item"
        >
          <div class="dimension-name">{{ getDimensionName(key) }}</div>
          <div class="dimension-value">
            <a-progress
              :percent="value"
              size="small"
              :stroke-color="getDimensionColor(value)"
              :show-info="false"
            />
            <span class="value-text">{{ Math.round(value) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 统计信息 -->
    <div class="stats-section">
      <div class="stat-item">
        <div class="stat-value">{{ player.total_matches }}</div>
        <div class="stat-label">总场次</div>
      </div>
      <div class="stat-item">
        <div class="stat-value">{{ player.total_wins }}</div>
        <div class="stat-label">胜场</div>
      </div>
      <div class="stat-item">
        <div class="stat-value">{{ player.win_rate.toFixed(1) }}%</div>
        <div class="stat-label">胜率</div>
      </div>
      <div class="stat-item">
        <div class="stat-value">{{ formatLastActive(player.last_active_at) }}</div>
        <div class="stat-label">最近活跃</div>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="actions-section">
      <a-button type="text" @click.stop="handleViewDetail">
        查看详情
      </a-button>
      <a-button type="text" @click.stop="handleContact">
        联系选手
      </a-button>
    </div>

    <!-- 特殊成就标记 -->
    <div v-if="player.achievements && player.achievements.length > 0" class="achievements">
      <a-tooltip
        v-for="achievement in player.achievements.slice(0, 3)"
        :key="achievement"
        :title="achievement"
      >
        <a-tag color="gold" size="small">🏆</a-tag>
      </a-tooltip>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { PlayerPoolProfile } from '@/shared/api/player-pool'
import { playerPoolUtils } from '@/shared/api/player-pool'

interface Props {
  player: PlayerPoolProfile
  selected?: boolean
}

interface Emits {
  (e: 'select', playerId: string): void
  (e: 'view-detail', playerId: string): void
  (e: 'contact', playerId: string): void
}

const props = withDefaults(defineProps<Props>(), {
  selected: false
})

const emit = defineEmits<Emits>()

// 工具函数
const getRatingTier = (rating: number) => playerPoolUtils.getRatingTier(rating)
const getTierColor = (rating: number) => playerPoolUtils.getTierColor(rating)
const formatLastActive = (date?: string) => playerPoolUtils.formatLastActive(date)

const getPositionName = (position: string): string => {
  const names: Record<string, string> = {
    'TOP': '上单',
    'JUNGLE': '打野',
    'MIDDLE': '中单',
    'BOTTOM': '下路',
    'UTILITY': '辅助'
  }
  return names[position] || position
}

const getDimensionName = (key: string): string => {
  const names: Record<string, string> = {
    'kda': 'KDA',
    'damage': '输出',
    'economy': '发育',
    'vision': '视野',
    'objective': '团控',
    'teamfight': '团战'
  }
  return names[key] || key
}

const getContractLabel = (status: string): string => {
  const labels: Record<string, string> = {
    'free_agent': '自由选手',
    'contracted': '已签约',
    'locked': '锁定',
    'trial': '试训'
  }
  return labels[status] || status
}

const getContractColor = (status: string): string => {
  const colors: Record<string, string> = {
    'free_agent': 'green',
    'contracted': 'blue',
    'locked': 'red',
    'trial': 'orange'
  }
  return colors[status] || 'default'
}

const getDimensionColor = (value: number): string => {
  if (value >= 80) return '#52c41a'
  if (value >= 60) return '#1890ff'
  if (value >= 40) return '#faad14'
  return '#f5222d'
}

const getRatingPercent = (rating: number): number => {
  // 将评分映射到0-100的进度条
  const maxRating = 3000 // Challenger门槛
  return Math.min((rating / maxRating) * 100, 100)
}

// 事件处理
const handleSelect = () => {
  emit('select', props.player.id)
}

const handleViewDetail = () => {
  emit('view-detail', props.player.id)
}

const handleContact = () => {
  emit('contact', props.player.id)
}
</script>

<style scoped>
.player-card {
  background: white;
  border: 2px solid #f0f0f0;
  border-radius: 12px;
  padding: 20px;
  position: relative;
  cursor: pointer;
  transition: all 0.3s ease;
  overflow: hidden;
}

.player-card:hover {
  border-color: #1890ff;
  box-shadow: 0 4px 16px rgba(24, 144, 255, 0.15);
  transform: translateY(-2px);
}

.player-card.selected {
  border-color: #1890ff;
  background: #f6ffed;
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.2);
}

.player-card.free-agent::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 4px;
  background: linear-gradient(90deg, #52c41a, #73d13d);
}

.select-checkbox {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 2;
}

.contract-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 2;
}

.player-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
  margin-top: 8px;
}

.avatar-section {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.rating-tier {
  font-size: 11px;
  font-weight: 600;
  color: #666;
  margin-top: 4px;
  text-align: center;
}

.player-info {
  flex: 1;
}

.player-name {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 4px 0;
  line-height: 1.2;
}

.username {
  color: #6b7280;
  font-size: 13px;
  margin-bottom: 8px;
}

.positions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.rating-section {
  margin-bottom: 20px;
}

.current-rating {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.rating-value {
  font-size: 24px;
  font-weight: 700;
  color: #1f2937;
}

.rating-label {
  font-size: 14px;
  font-weight: 400;
  color: #6b7280;
}

.confidence {
  font-size: 12px;
  color: #6b7280;
}

.rating-progress {
  margin-bottom: 4px;
}

.dimensions-section {
  margin-bottom: 20px;
}

.dimensions-title {
  font-size: 14px;
  font-weight: 600;
  color: #4b5563;
  margin-bottom: 12px;
}

.dimensions-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.dimension-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.dimension-name {
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
}

.dimension-value {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dimension-value :deep(.ant-progress) {
  flex: 1;
}

.value-text {
  font-size: 12px;
  font-weight: 600;
  color: #374151;
  min-width: 20px;
  text-align: right;
}

.stats-section {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 16px;
  padding: 12px;
  background: #fafafa;
  border-radius: 6px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  line-height: 1.2;
}

.stat-label {
  font-size: 11px;
  color: #6b7280;
  margin-top: 2px;
}

.actions-section {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.actions-section .ant-btn {
  flex: 1;
  height: 32px;
  font-size: 13px;
}

.achievements {
  position: absolute;
  bottom: 12px;
  right: 12px;
  display: flex;
  gap: 4px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .player-card {
    padding: 16px;
  }

  .player-header {
    gap: 12px;
    margin-bottom: 16px;
  }

  .rating-value {
    font-size: 20px;
  }

  .dimensions-grid {
    grid-template-columns: 1fr;
    gap: 6px;
  }

  .stats-section {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
}
</style>