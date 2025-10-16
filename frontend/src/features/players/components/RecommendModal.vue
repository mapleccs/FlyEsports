<template>
  <a-modal
    v-model:open="visible"
    title="推荐选手"
    width="700px"
    :footer="null"
    @cancel="handleCancel"
  >
    <div class="recommend-content">
      <a-form
        ref="formRef"
        :model="formData"
        layout="vertical"
        @finish="handleSubmit"
      >
        <a-row :gutter="16">
          <!-- 需求位置 -->
          <a-col :span="24">
            <a-form-item
              label="需要的位置"
              name="positions_needed"
              :rules="[{ required: true, message: '请选择至少一个位置' }]"
            >
              <a-checkbox-group v-model:value="formData.team_needs.positions_needed">
                <a-checkbox value="TOP">上单</a-checkbox>
                <a-checkbox value="JUNGLE">打野</a-checkbox>
                <a-checkbox value="MIDDLE">中单</a-checkbox>
                <a-checkbox value="BOTTOM">下路</a-checkbox>
                <a-checkbox value="UTILITY">辅助</a-checkbox>
              </a-checkbox-group>
            </a-form-item>
          </a-col>

          <!-- 评分要求 -->
          <a-col :span="12">
            <a-form-item label="最低评分要求" name="min_rating">
              <a-input-number
                v-model:value="formData.team_needs.min_rating"
                placeholder="最低评分"
                :min="0"
                :max="5000"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>

          <a-col :span="12">
            <a-form-item label="最高评分范围" name="max_rating">
              <a-input-number
                v-model:value="formData.team_needs.max_rating"
                placeholder="最高评分"
                :min="0"
                :max="5000"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>

          <!-- 经验水平 -->
          <a-col :span="12">
            <a-form-item label="经验水平要求" name="experience_level">
              <a-select
                v-model:value="formData.team_needs.experience_level"
                placeholder="选择经验水平"
                allow-clear
              >
                <a-select-option value="rookie">新手 (0-20场)</a-select-option>
                <a-select-option value="intermediate">中级 (20-100场)</a-select-option>
                <a-select-option value="veteran">老手 (100+场)</a-select-option>
                <a-select-option value="any">不限</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>

          <!-- 合同状态要求 -->
          <a-col :span="12">
            <a-form-item label="合同状态要求" name="contract_status">
              <a-select
                v-model:value="formData.team_needs.contract_status"
                placeholder="选择合同状态"
                allow-clear
              >
                <a-select-option value="free_agent">仅自由选手</a-select-option>
                <a-select-option value="trial">可试训</a-select-option>
                <a-select-option value="all">不限制</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>

          <!-- 预算范围 -->
          <a-col :span="12">
            <a-form-item label="预算下限 (万元)" name="budget_min">
              <a-input-number
                v-model:value="budgetRange[0]"
                placeholder="最低预算"
                :min="0"
                :precision="1"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>

          <a-col :span="12">
            <a-form-item label="预算上限 (万元)" name="budget_max">
              <a-input-number
                v-model:value="budgetRange[1]"
                placeholder="最高预算"
                :min="0"
                :precision="1"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>

          <!-- 偏好风格 -->
          <a-col :span="24">
            <a-form-item label="偏好游戏风格" name="preferred_playstyle">
              <a-checkbox-group v-model:value="formData.team_needs.preferred_playstyle">
                <a-checkbox value="aggressive">激进型</a-checkbox>
                <a-checkbox value="defensive">稳健型</a-checkbox>
                <a-checkbox value="support">团队型</a-checkbox>
                <a-checkbox value="carry">核心型</a-checkbox>
                <a-checkbox value="flexible">灵活型</a-checkbox>
              </a-checkbox-group>
            </a-form-item>
          </a-col>

          <!-- 推荐数量 -->
          <a-col :span="12">
            <a-form-item label="推荐数量" name="max_recommendations">
              <a-slider
                v-model:value="formData.max_recommendations"
                :min="1"
                :max="20"
                :marks="{ 5: '5', 10: '10', 15: '15', 20: '20' }"
              />
            </a-form-item>
          </a-col>

          <!-- 地区限制 -->
          <a-col :span="12">
            <a-form-item label="地区限制" name="region_id">
              <a-select
                v-model:value="formData.region_id"
                placeholder="选择地区"
                allow-clear
              >
                <a-select-option :value="1">华北赛区</a-select-option>
                <a-select-option :value="2">华南赛区</a-select-option>
                <a-select-option :value="3">华东赛区</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <!-- 操作按钮 -->
        <div class="recommend-actions">
          <a-space>
            <a-button @click="handleCancel">取消</a-button>
            <a-button @click="handleReset">重置</a-button>
            <a-button
              type="primary"
              html-type="submit"
              :loading="loading"
            >
              开始推荐
            </a-button>
          </a-space>
        </div>
      </a-form>
    </div>

    <!-- 推荐结果展示 -->
    <div v-if="recommendations.length > 0" class="recommendations-section">
      <a-divider>推荐结果</a-divider>

      <div class="recommendations-list">
        <div
          v-for="recommendation in recommendations"
          :key="recommendation.player.id"
          class="recommendation-item"
        >
          <div class="player-basic">
            <a-avatar
              :size="40"
              :src="recommendation.player.avatar_url"
              :style="{ backgroundColor: getTierColor(recommendation.player.rating.current_score) }"
            >
              {{ recommendation.player.display_name?.[0] || recommendation.player.username[0] }}
            </a-avatar>

            <div class="player-info">
              <div class="player-name">
                {{ recommendation.player.display_name || recommendation.player.username }}
              </div>
              <div class="player-details">
                <a-tag color="blue">
                  {{ getPositionName(recommendation.player.primary_position) }}
                </a-tag>
                <span class="rating">{{ Math.round(recommendation.player.rating.current_score) }}分</span>
              </div>
            </div>
          </div>

          <div class="recommendation-details">
            <div class="fit-score">
              <a-progress
                type="circle"
                :width="50"
                :percent="recommendation.fit_score"
                :stroke-color="getFitScoreColor(recommendation.fit_score)"
              />
              <div class="fit-label">匹配度</div>
            </div>

            <div class="fit-reasons">
              <div class="reasons-title">推荐理由:</div>
              <ul class="reasons-list">
                <li v-for="reason in recommendation.fit_reasons" :key="reason">
                  {{ reason }}
                </li>
              </ul>
            </div>

            <div class="availability">
              <a-tag :color="getAvailabilityColor(recommendation.availability_status)">
                {{ recommendation.availability_status }}
              </a-tag>
              <span v-if="recommendation.estimated_cost" class="estimated-cost">
                预估: {{ recommendation.estimated_cost }}万
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { message } from 'ant-design-vue'
import type { RecommendPlayersRequest, PlayerRecommendation } from '@/shared/api/player-pool'
import { playerPoolUtils } from '@/shared/api/player-pool'

interface Props {
  visible: boolean
  loading?: boolean
  recommendations?: PlayerRecommendation[]
}

interface Emits {
  (e: 'update:visible', visible: boolean): void
  (e: 'recommend', request: RecommendPlayersRequest): void
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  recommendations: () => []
})

const emit = defineEmits<Emits>()

const formRef = ref()
const budgetRange = ref<[number | undefined, number | undefined]>([undefined, undefined])

// 表单数据
const formData = reactive<RecommendPlayersRequest>({
  team_needs: {
    positions_needed: [],
    min_rating: undefined,
    max_rating: undefined,
    preferred_playstyle: [],
    budget_range: [undefined, undefined],
    experience_level: undefined,
    contract_status: undefined
  },
  region_id: undefined,
  max_recommendations: 10
})

const recommendations = ref<PlayerRecommendation[]>([])

// 监听推荐结果变化
watch(() => props.recommendations, (newRecommendations) => {
  recommendations.value = newRecommendations
})

// 计算属性：visible的双向绑定
const visible = computed({
  get: () => props.visible,
  set: (value: boolean) => emit('update:visible', value)
})

// 监听预算范围变化
watch(budgetRange, (newRange) => {
  formData.team_needs.budget_range = [newRange[0], newRange[1]]
}, { deep: true })

// 工具函数
const getTierColor = (rating: number) => playerPoolUtils.getTierColor(rating)

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

const getFitScoreColor = (score: number): string => {
  if (score >= 80) return '#52c41a'
  if (score >= 60) return '#1890ff'
  if (score >= 40) return '#faad14'
  return '#f5222d'
}

const getAvailabilityColor = (status: string): string => {
  const colors: Record<string, string> = {
    '可立即签约': 'green',
    '可协商': 'blue',
    '需要谈判': 'orange',
    '暂不可用': 'red'
  }
  return colors[status] || 'default'
}

// 事件处理
const handleSubmit = async () => {
  try {
    await formRef.value.validate()

    // 验证必填字段
    if (formData.team_needs.positions_needed.length === 0) {
      message.error('请至少选择一个需要的位置')
      return
    }

    // 验证预算范围
    const [minBudget, maxBudget] = budgetRange.value
    if (minBudget !== undefined && maxBudget !== undefined && minBudget > maxBudget) {
      message.error('预算下限不能大于上限')
      return
    }

    emit('recommend', formData)
  } catch (error) {
    console.error('Form validation failed:', error)
  }
}

const handleReset = () => {
  Object.assign(formData, {
    team_needs: {
      positions_needed: [],
      min_rating: undefined,
      max_rating: undefined,
      preferred_playstyle: [],
      budget_range: [undefined, undefined],
      experience_level: undefined,
      contract_status: undefined
    },
    region_id: undefined,
    max_recommendations: 10
  })
  budgetRange.value = [undefined, undefined]
  recommendations.value = []
}

const handleCancel = () => {
  visible.value = false
}
</script>

<style scoped>
.recommend-content {
  max-height: 60vh;
  overflow-y: auto;
  padding-right: 8px;
}

.recommend-actions {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
  text-align: right;
}

.recommendations-section {
  margin-top: 24px;
  border-top: 1px solid #f0f0f0;
  padding-top: 16px;
}

.recommendations-list {
  max-height: 400px;
  overflow-y: auto;
}

.recommendation-item {
  display: flex;
  gap: 16px;
  padding: 16px;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  margin-bottom: 12px;
  background: #fafafa;
}

.player-basic {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 200px;
}

.player-info {
  flex: 1;
}

.player-name {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 4px;
}

.player-details {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rating {
  font-size: 14px;
  color: #6b7280;
  font-weight: 500;
}

.recommendation-details {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 20px;
}

.fit-score {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.fit-label {
  font-size: 12px;
  color: #6b7280;
}

.fit-reasons {
  flex: 1;
}

.reasons-title {
  font-size: 14px;
  font-weight: 600;
  color: #4b5563;
  margin-bottom: 4px;
}

.reasons-list {
  margin: 0;
  padding-left: 16px;
  font-size: 13px;
  color: #6b7280;
}

.availability {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.estimated-cost {
  font-size: 12px;
  color: #f59e0b;
  font-weight: 600;
}

:deep(.ant-slider) {
  margin: 8px 0;
}

/* 自定义滚动条样式 */
.recommend-content::-webkit-scrollbar,
.recommendations-list::-webkit-scrollbar {
  width: 6px;
}

.recommend-content::-webkit-scrollbar-track,
.recommendations-list::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.recommend-content::-webkit-scrollbar-thumb,
.recommendations-list::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.recommend-content::-webkit-scrollbar-thumb:hover,
.recommendations-list::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>