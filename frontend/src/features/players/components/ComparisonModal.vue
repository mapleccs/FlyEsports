<template>
  <a-modal
    v-model:open="visible"
    title="选手对比分析"
    width="1000px"
    :footer="null"
    @cancel="handleCancel"
  >
    <div v-if="loading" class="loading-container">
      <a-spin size="large">
        <div class="loading-text">正在分析选手数据...</div>
      </a-spin>
    </div>

    <div v-else-if="comparison" class="comparison-content">
      <!-- 选手基本信息对比 -->
      <div class="players-header">
        <div class="header-title">选手基本信息对比</div>
        <div class="players-row">
          <div
            v-for="(player, index) in comparison.players"
            :key="player.id"
            class="player-column"
          >
            <div class="player-card">
              <a-avatar
                :size="60"
                :src="player.avatar_url"
                :style="{ backgroundColor: getTierColor(player.rating.current_score) }"
              >
                {{ player.display_name?.[0] || player.username[0] }}
              </a-avatar>

              <div class="player-info">
                <div class="player-name">
                  {{ player.display_name || player.username }}
                </div>
                <div class="player-details">
                  <a-tag color="blue">
                    {{ getPositionName(player.primary_position) }}
                  </a-tag>
                  <div class="rating">
                    {{ Math.round(player.rating.current_score) }}分
                  </div>
                </div>
                <div class="tier-info">
                  {{ getRatingTier(player.rating.current_score) }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 基础统计对比 -->
      <div class="comparison-section">
        <div class="section-title">基础统计对比</div>
        <div class="stats-table">
          <div class="stats-row header-row">
            <div class="stat-label">统计项目</div>
            <div
              v-for="(player, index) in comparison.players"
              :key="`header-${index}`"
              class="stat-value"
            >
              {{ player.display_name || player.username }}
            </div>
          </div>

          <div class="stats-row">
            <div class="stat-label">总场次</div>
            <div
              v-for="(value, index) in comparison.comparison.basic_stats.total_matches"
              :key="`matches-${index}`"
              class="stat-value"
              :class="{ 'best-value': isBestValue(comparison.comparison.basic_stats.total_matches, value) }"
            >
              {{ value }}
            </div>
          </div>

          <div class="stats-row">
            <div class="stat-label">胜率</div>
            <div
              v-for="(value, index) in comparison.comparison.basic_stats.win_rate"
              :key="`winrate-${index}`"
              class="stat-value"
              :class="{ 'best-value': isBestValue(comparison.comparison.basic_stats.win_rate, value) }"
            >
              {{ value.toFixed(1) }}%
            </div>
          </div>
        </div>
      </div>

      <!-- 评分对比 -->
      <div class="comparison-section">
        <div class="section-title">评分对比</div>
        <div class="stats-table">
          <div class="stats-row">
            <div class="stat-label">当前评分</div>
            <div
              v-for="(value, index) in comparison.comparison.ratings.current_rating"
              :key="`rating-${index}`"
              class="stat-value"
              :class="{ 'best-value': isBestValue(comparison.comparison.ratings.current_rating, value) }"
            >
              {{ Math.round(value) }}
            </div>
          </div>

          <div class="stats-row">
            <div class="stat-label">置信度</div>
            <div
              v-for="(value, index) in comparison.comparison.ratings.confidence_level"
              :key="`confidence-${index}`"
              class="stat-value"
              :class="{ 'best-value': isBestValue(comparison.comparison.ratings.confidence_level, value) }"
            >
              {{ (value * 100).toFixed(1) }}%
            </div>
          </div>

          <div class="stats-row">
            <div class="stat-label">评分状态</div>
            <div
              v-for="(value, index) in comparison.comparison.ratings.is_locked"
              :key="`locked-${index}`"
              class="stat-value"
            >
              <a-tag :color="value ? 'red' : 'green'">
                {{ value ? '锁定' : '活跃' }}
              </a-tag>
            </div>
          </div>
        </div>
      </div>

      <!-- 六维能力对比 -->
      <div class="comparison-section">
        <div class="section-title">六维能力对比</div>
        <div class="dimensions-comparison">
          <div class="dimensions-chart">
            <div
              v-for="(dimension, key) in dimensionLabels"
              :key="key"
              class="dimension-row"
            >
              <div class="dimension-label">{{ dimension }}</div>
              <div class="dimension-bars">
                <div
                  v-for="(value, index) in comparison.comparison.dimensions[key]"
                  :key="`${key}-${index}`"
                  class="dimension-bar-container"
                >
                  <div
                    class="dimension-bar"
                    :style="{
                      width: `${value}%`,
                      backgroundColor: getDimensionColor(value)
                    }"
                  />
                  <span class="dimension-value">{{ Math.round(value) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 优势劣势分析 -->
      <div class="comparison-section">
        <div class="section-title">优势劣势分析</div>
        <div class="strengths-weaknesses">
          <div
            v-for="(player, index) in comparison.players"
            :key="`sw-${index}`"
            class="player-analysis"
          >
            <div class="analysis-header">
              <a-avatar
                :size="32"
                :src="player.avatar_url"
                :style="{ backgroundColor: getTierColor(player.rating.current_score) }"
              >
                {{ player.display_name?.[0] || player.username[0] }}
              </a-avatar>
              <span class="player-name">
                {{ player.display_name || player.username }}
              </span>
            </div>

            <div class="analysis-content">
              <div class="strengths">
                <div class="analysis-title">
                  <CheckCircleOutlined class="icon success" />
                  优势能力
                </div>
                <div class="ability-tags">
                  <a-tag
                    v-for="strength in comparison.comparison.strengths_weaknesses[`player_${index}`]?.strengths || []"
                    :key="`strength-${index}-${strength}`"
                    color="green"
                  >
                    {{ getDimensionName(strength) }}
                  </a-tag>
                </div>
              </div>

              <div class="weaknesses">
                <div class="analysis-title">
                  <ExclamationCircleOutlined class="icon warning" />
                  待提升
                </div>
                <div class="ability-tags">
                  <a-tag
                    v-for="weakness in comparison.comparison.strengths_weaknesses[`player_${index}`]?.weaknesses || []"
                    :key="`weakness-${index}-${weakness}`"
                    color="orange"
                  >
                    {{ getDimensionName(weakness) }}
                  </a-tag>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 分析结论 -->
      <div class="comparison-section">
        <div class="section-title">分析结论</div>
        <div class="analysis-summary">
          <a-alert
            message="对比分析完成"
            :description="`本次对比分析了${comparison.players.length}名选手的综合能力。数据生成时间：${formatDate(comparison.generated_at)}`"
            type="info"
            show-icon
          />
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <a-empty description="暂无对比数据" />
    </div>

    <!-- 操作按钮 -->
    <div class="modal-actions">
      <a-space>
        <a-button @click="handleExport" :disabled="!comparison">
          导出报告
        </a-button>
        <a-button @click="handleCancel">
          关闭
        </a-button>
      </a-space>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { message } from 'ant-design-vue'
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons-vue'
import type { PlayerComparison } from '@/shared/api/player-pool'
import { playerPoolUtils } from '@/shared/api/player-pool'

interface Props {
  visible: boolean
  comparison: PlayerComparison | null
  loading?: boolean
}

interface Emits {
  (e: 'update:visible', visible: boolean): void
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})

const emit = defineEmits<Emits>()

// 维度标签映射
const dimensionLabels = {
  kda: 'KDA',
  damage: '输出',
  economy: '发育',
  vision: '视野',
  objective: '团控',
  teamfight: '团战'
}

// 计算属性：visible的双向绑定
const visible = computed({
  get: () => props.visible,
  set: (value: boolean) => emit('update:visible', value)
})

// 工具函数
const getTierColor = (rating: number) => playerPoolUtils.getTierColor(rating)
const getRatingTier = (rating: number) => playerPoolUtils.getRatingTier(rating)

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
  return dimensionLabels[key as keyof typeof dimensionLabels] || key
}

const getDimensionColor = (value: number): string => {
  if (value >= 80) return '#52c41a'
  if (value >= 60) return '#1890ff'
  if (value >= 40) return '#faad14'
  return '#f5222d'
}

const isBestValue = (values: number[], currentValue: number): boolean => {
  const maxValue = Math.max(...values)
  return currentValue === maxValue && values.filter(v => v === maxValue).length === 1
}

const formatDate = (dateStr: string): string => {
  return new Date(dateStr).toLocaleString('zh-CN')
}

// 事件处理
const handleExport = () => {
  if (!props.comparison) {
    message.error('没有可导出的数据')
    return
  }

  // 简单的数据导出实现
  const exportData = {
    ...props.comparison,
    export_time: new Date().toISOString()
  }

  const dataStr = JSON.stringify(exportData, null, 2)
  const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr)

  const exportFileDefaultName = `player-comparison-${Date.now()}.json`

  const linkElement = document.createElement('a')
  linkElement.setAttribute('href', dataUri)
  linkElement.setAttribute('download', exportFileDefaultName)
  linkElement.click()

  message.success('对比报告已导出')
}

const handleCancel = () => {
  visible.value = false
}
</script>

<style scoped>
.loading-container {
  text-align: center;
  padding: 60px 0;
}

.loading-text {
  margin-top: 16px;
  color: #6b7280;
}

.comparison-content {
  max-height: 80vh;
  overflow-y: auto;
  padding-right: 8px;
}

.players-header {
  margin-bottom: 24px;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 16px;
}

.players-row {
  display: flex;
  gap: 16px;
  justify-content: space-around;
}

.player-column {
  flex: 1;
  min-width: 0;
}

.player-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
}

.player-info {
  text-align: center;
  margin-top: 12px;
}

.player-name {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 4px;
}

.player-details {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  margin-bottom: 4px;
}

.rating {
  font-size: 14px;
  font-weight: 600;
  color: #4b5563;
}

.tier-info {
  font-size: 12px;
  color: #6b7280;
}

.comparison-section {
  margin-bottom: 32px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 16px;
  border-bottom: 2px solid #e5e7eb;
  padding-bottom: 8px;
}

.stats-table {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}

.stats-row {
  display: grid;
  grid-template-columns: 120px repeat(auto-fit, minmax(100px, 1fr));
  border-bottom: 1px solid #f0f0f0;
}

.stats-row:last-child {
  border-bottom: none;
}

.header-row {
  background: #f8fafc;
  font-weight: 600;
}

.stat-label {
  padding: 12px 16px;
  background: #f8fafc;
  font-weight: 500;
  color: #374151;
  border-right: 1px solid #e5e7eb;
}

.stat-value {
  padding: 12px 16px;
  text-align: center;
  color: #1f2937;
  border-right: 1px solid #f0f0f0;
}

.stat-value:last-child {
  border-right: none;
}

.stat-value.best-value {
  background: #f0f9ff;
  color: #1e40af;
  font-weight: 600;
}

.dimensions-comparison {
  background: white;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  padding: 20px;
}

.dimension-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.dimension-row:last-child {
  margin-bottom: 0;
}

.dimension-label {
  width: 60px;
  font-weight: 500;
  color: #374151;
  text-align: right;
}

.dimension-bars {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 8px;
}

.dimension-bar-container {
  position: relative;
  height: 24px;
  background: #f3f4f6;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  align-items: center;
}

.dimension-bar {
  height: 100%;
  border-radius: 12px;
  transition: width 0.3s ease;
}

.dimension-value {
  position: absolute;
  right: 8px;
  font-size: 12px;
  font-weight: 600;
  color: #374151;
}

.strengths-weaknesses {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
}

.player-analysis {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
}

.analysis-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;
}

.analysis-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.analysis-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 6px;
}

.icon.success {
  color: #52c41a;
}

.icon.warning {
  color: #faad14;
}

.ability-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.analysis-summary {
  margin-top: 16px;
}

.empty-state {
  text-align: center;
  padding: 60px 0;
}

.modal-actions {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
  text-align: right;
}

/* 自定义滚动条样式 */
.comparison-content::-webkit-scrollbar {
  width: 6px;
}

.comparison-content::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.comparison-content::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.comparison-content::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .players-row {
    flex-direction: column;
  }

  .stats-row {
    grid-template-columns: 100px repeat(auto-fit, minmax(80px, 1fr));
  }

  .stat-label {
    padding: 8px 12px;
  }

  .stat-value {
    padding: 8px 12px;
  }

  .dimension-bars {
    grid-template-columns: 1fr;
  }

  .strengths-weaknesses {
    grid-template-columns: 1fr;
  }
}
</style>