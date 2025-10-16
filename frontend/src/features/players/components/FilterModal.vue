<template>
  <a-modal
    v-model:open="visible"
    title="筛选选手"
    width="800px"
    :footer="null"
    @cancel="handleCancel"
  >
    <div class="filter-content">
      <a-form
        ref="formRef"
        :model="localFilters"
        layout="vertical"
        @finish="handleSubmit"
      >
        <a-row :gutter="16">
          <!-- 位置筛选 -->
          <a-col :span="12">
            <a-form-item label="位置" name="position">
              <a-select
                v-model:value="localFilters.position"
                placeholder="选择位置"
                allow-clear
              >
                <a-select-option value="TOP">上单</a-select-option>
                <a-select-option value="JUNGLE">打野</a-select-option>
                <a-select-option value="MIDDLE">中单</a-select-option>
                <a-select-option value="BOTTOM">下路</a-select-option>
                <a-select-option value="UTILITY">辅助</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>

          <!-- 合同状态 -->
          <a-col :span="12">
            <a-form-item label="合同状态" name="contract_status">
              <a-select
                v-model:value="localFilters.contract_status"
                placeholder="选择合同状态"
                allow-clear
              >
                <a-select-option value="free_agent">自由选手</a-select-option>
                <a-select-option value="contracted">已签约</a-select-option>
                <a-select-option value="locked">锁定</a-select-option>
                <a-select-option value="trial">试训</a-select-option>
                <a-select-option value="all">全部</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>

          <!-- 评分范围 -->
          <a-col :span="12">
            <a-form-item label="最低评分" name="min_rating">
              <a-input-number
                v-model:value="localFilters.min_rating"
                placeholder="最低评分"
                :min="0"
                :max="5000"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>

          <a-col :span="12">
            <a-form-item label="最高评分" name="max_rating">
              <a-input-number
                v-model:value="localFilters.max_rating"
                placeholder="最高评分"
                :min="0"
                :max="5000"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>

          <!-- 置信度范围 -->
          <a-col :span="12">
            <a-form-item label="最低置信度" name="min_confidence">
              <a-slider
                v-model:value="localFilters.min_confidence"
                :min="0.5"
                :max="0.95"
                :step="0.05"
                :tip-formatter="(value) => `${(value * 100).toFixed(0)}%`"
              />
            </a-form-item>
          </a-col>

          <a-col :span="12">
            <a-form-item label="最高置信度" name="max_confidence">
              <a-slider
                v-model:value="localFilters.max_confidence"
                :min="0.5"
                :max="0.95"
                :step="0.05"
                :tip-formatter="(value) => `${(value * 100).toFixed(0)}%`"
              />
            </a-form-item>
          </a-col>

          <!-- 比赛场次范围 -->
          <a-col :span="12">
            <a-form-item label="最少比赛场次" name="min_matches">
              <a-input-number
                v-model:value="localFilters.min_matches"
                placeholder="最少场次"
                :min="0"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>

          <a-col :span="12">
            <a-form-item label="最多比赛场次" name="max_matches">
              <a-input-number
                v-model:value="localFilters.max_matches"
                placeholder="最多场次"
                :min="0"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>

          <!-- 活跃度 -->
          <a-col :span="12">
            <a-form-item label="最近活跃天数" name="last_active_days">
              <a-select
                v-model:value="localFilters.last_active_days"
                placeholder="选择活跃度"
                allow-clear
              >
                <a-select-option :value="1">今天</a-select-option>
                <a-select-option :value="7">一周内</a-select-option>
                <a-select-option :value="30">一月内</a-select-option>
                <a-select-option :value="90">三月内</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>

          <a-col :span="12">
            <a-form-item name="include_inactive">
              <a-checkbox v-model:checked="localFilters.include_inactive">
                包含不活跃选手
              </a-checkbox>
            </a-form-item>
          </a-col>
        </a-row>

        <!-- 六维度筛选 -->
        <a-divider>六维能力筛选</a-divider>

        <a-row :gutter="16">
          <a-col
            v-for="(dimension, key) in dimensionLabels"
            :key="key"
            :span="8"
          >
            <a-form-item :label="`${dimension}最低值`">
              <a-slider
                v-model:value="localFilters.dimension_filters[key]"
                :min="0"
                :max="100"
                :step="5"
                :tip-formatter="(value) => `${value}%`"
              />
            </a-form-item>
          </a-col>
        </a-row>

        <!-- 搜索条件 -->
        <a-divider>搜索条件</a-divider>

        <a-row :gutter="16">
          <a-col :span="24">
            <a-form-item label="关键词搜索" name="search_query">
              <a-input
                v-model:value="localFilters.search_query"
                placeholder="输入选手用户名、显示名称等关键词"
                allow-clear
              />
            </a-form-item>
          </a-col>
        </a-row>

        <!-- 操作按钮 -->
        <div class="filter-actions">
          <a-space>
            <a-button @click="handleReset">重置筛选</a-button>
            <a-button @click="handleCancel">取消</a-button>
            <a-button type="primary" html-type="submit">
              应用筛选
            </a-button>
          </a-space>
        </div>
      </a-form>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, reactive, watch, computed } from 'vue'
import type { PlayerPoolFilter } from '@/shared/api/player-pool'

interface Props {
  visible: boolean
  filters: PlayerPoolFilter
}

interface Emits {
  (e: 'update:visible', visible: boolean): void
  (e: 'apply', filters: PlayerPoolFilter): void
  (e: 'reset'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const formRef = ref()

// 维度标签映射
const dimensionLabels = {
  kda: 'KDA',
  damage: '输出',
  economy: '发育',
  vision: '视野',
  objective: '团控',
  teamfight: '团战'
}

// 本地筛选条件
const localFilters = reactive<PlayerPoolFilter & { dimension_filters: Record<string, number> }>({
  position: undefined,
  contract_status: undefined,
  min_rating: undefined,
  max_rating: undefined,
  min_confidence: undefined,
  max_confidence: undefined,
  min_matches: undefined,
  max_matches: undefined,
  last_active_days: undefined,
  include_inactive: false,
  search_query: undefined,
  dimension_filters: {
    kda: undefined,
    damage: undefined,
    economy: undefined,
    vision: undefined,
    objective: undefined,
    teamfight: undefined
  }
})

// 监听props变化，同步到本地状态
watch(() => props.filters, (newFilters) => {
  Object.assign(localFilters, {
    ...newFilters,
    dimension_filters: {
      kda: undefined,
      damage: undefined,
      economy: undefined,
      vision: undefined,
      objective: undefined,
      teamfight: undefined,
      ...newFilters.dimension_filters
    }
  })
}, { immediate: true, deep: true })

// 计算属性：visible的双向绑定
const visible = computed({
  get: () => props.visible,
  set: (value: boolean) => emit('update:visible', value)
})

// 处理表单提交
const handleSubmit = () => {
  // 清理空值和默认值
  const cleanFilters: PlayerPoolFilter = {}

  Object.entries(localFilters).forEach(([key, value]) => {
    if (key === 'dimension_filters') {
      const dimensionFilters: Record<string, number> = {}
      Object.entries(value as Record<string, number>).forEach(([dimKey, dimValue]) => {
        if (dimValue !== undefined && dimValue > 0) {
          dimensionFilters[dimKey] = dimValue
        }
      })
      if (Object.keys(dimensionFilters).length > 0) {
        cleanFilters.dimension_filters = dimensionFilters
      }
    } else if (value !== undefined && value !== null && value !== '') {
      cleanFilters[key as keyof PlayerPoolFilter] = value
    }
  })

  emit('apply', cleanFilters)
}

// 重置筛选
const handleReset = () => {
  Object.keys(localFilters).forEach(key => {
    if (key === 'dimension_filters') {
      Object.keys(localFilters.dimension_filters).forEach(dimKey => {
        localFilters.dimension_filters[dimKey] = undefined
      })
    } else {
      localFilters[key as keyof PlayerPoolFilter] = undefined
    }
  })
  localFilters.include_inactive = false

  emit('reset')
}

// 取消操作
const handleCancel = () => {
  visible.value = false
}
</script>

<style scoped>
.filter-content {
  max-height: 70vh;
  overflow-y: auto;
  padding-right: 8px;
}

.filter-actions {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
  text-align: right;
}

:deep(.ant-slider) {
  margin: 8px 0;
}

:deep(.ant-divider) {
  margin: 20px 0 16px 0;
  font-weight: 600;
}

/* 自定义滚动条样式 */
.filter-content::-webkit-scrollbar {
  width: 6px;
}

.filter-content::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.filter-content::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.filter-content::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>