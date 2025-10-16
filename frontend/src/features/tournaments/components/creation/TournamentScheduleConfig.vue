<template>
  <div class="tournament-schedule-config">
    <!-- 调试信息 -->
    <div
      style="
        background: #f0f2ff;
        padding: 8px;
        margin-bottom: 16px;
        border-radius: 4px;
        font-size: 12px;
      "
    >
      <strong>调试信息:</strong> TournamentScheduleConfig组件已加载，使用 dayjs | 当前时间:
      {{ dayjs().format('YYYY-MM-DD HH:mm:ss') }}
    </div>

    <div class="step-header">
      <h2 class="step-title">时间安排设置</h2>
      <p class="step-description">设置报名时间和比赛时间，确保时间安排合理</p>
    </div>

    <div class="form-section">
      <!-- 报名时间段 -->
      <div class="time-group">
        <h3 class="group-title">
          <user-add-outlined />
          报名时间安排
        </h3>

        <a-row :gutter="16">
          <a-col :xs="24" :md="12">
            <a-form-item
              label="报名开始时间"
              name="registration_start"
              :rules="[{ required: true, message: '请选择报名开始时间', trigger: 'change' }]"
            >
              <a-date-picker
                :value="localData.registration_start ? dayjs(localData.registration_start) : null"
                show-time
                placeholder="选择报名开始时间"
                size="large"
                style="width: 100%"
                :disabled-date="disabledRegistrationStartDate"
                @change="handleRegistrationStartChange"
              />
            </a-form-item>
          </a-col>

          <a-col :xs="24" :md="12">
            <a-form-item
              label="报名结束时间"
              name="registration_end"
              :rules="[{ required: true, message: '请选择报名结束时间', trigger: 'change' }]"
            >
              <a-date-picker
                :value="localData.registration_end ? dayjs(localData.registration_end) : null"
                show-time
                placeholder="选择报名结束时间"
                size="large"
                style="width: 100%"
                :disabled-date="disabledRegistrationEndDate"
                @change="handleRegistrationEndChange"
              />
            </a-form-item>
          </a-col>
        </a-row>

        <div v-if="registrationDuration" class="duration-info">
          <clock-circle-outlined />
          报名持续时间：{{ registrationDuration }}
        </div>
      </div>

      <!-- 比赛时间段 -->
      <div class="time-group">
        <h3 class="group-title">
          <trophy-outlined />
          比赛时间安排
        </h3>

        <a-row :gutter="16">
          <a-col :xs="24" :md="12">
            <a-form-item
              label="比赛开始时间"
              name="tournament_start"
              :rules="[{ required: true, message: '请选择比赛开始时间', trigger: 'change' }]"
            >
              <a-date-picker
                :value="localData.tournament_start ? dayjs(localData.tournament_start) : null"
                show-time
                placeholder="选择比赛开始时间"
                size="large"
                style="width: 100%"
                :disabled-date="disabledTournamentStartDate"
                @change="handleTournamentStartChange"
              />
            </a-form-item>
          </a-col>

          <a-col :xs="24" :md="12">
            <a-form-item
              label="比赛结束时间"
              name="tournament_end"
              :rules="[{ required: true, message: '请选择比赛结束时间', trigger: 'change' }]"
            >
              <a-date-picker
                :value="localData.tournament_end ? dayjs(localData.tournament_end) : null"
                show-time
                placeholder="选择比赛结束时间"
                size="large"
                style="width: 100%"
                :disabled-date="disabledTournamentEndDate"
                @change="handleTournamentEndChange"
              />
            </a-form-item>
          </a-col>
        </a-row>

        <div v-if="tournamentDuration" class="duration-info">
          <clock-circle-outlined />
          比赛持续时间：{{ tournamentDuration }}
        </div>
      </div>

      <!-- 时间轴预览 -->
      <div v-if="hasValidTimes" class="timeline-preview">
        <h3 class="preview-title">
          <eye-outlined />
          时间安排预览
        </h3>

        <a-timeline class="schedule-timeline">
          <a-timeline-item color="blue">
            <template #dot>
              <user-add-outlined class="timeline-icon" />
            </template>
            <div class="timeline-content">
              <div class="timeline-title">报名开始</div>
              <div class="timeline-time">{{ formatTime(localData.registration_start) }}</div>
            </div>
          </a-timeline-item>

          <a-timeline-item color="orange">
            <template #dot>
              <stop-outlined class="timeline-icon" />
            </template>
            <div class="timeline-content">
              <div class="timeline-title">报名结束</div>
              <div class="timeline-time">{{ formatTime(localData.registration_end) }}</div>
            </div>
          </a-timeline-item>

          <a-timeline-item color="green">
            <template #dot>
              <play-circle-outlined class="timeline-icon" />
            </template>
            <div class="timeline-content">
              <div class="timeline-title">比赛开始</div>
              <div class="timeline-time">{{ formatTime(localData.tournament_start) }}</div>
            </div>
          </a-timeline-item>

          <a-timeline-item color="gray">
            <template #dot>
              <trophy-outlined class="timeline-icon" />
            </template>
            <div class="timeline-content">
              <div class="timeline-title">比赛结束</div>
              <div class="timeline-time">{{ formatTime(localData.tournament_end) }}</div>
            </div>
          </a-timeline-item>
        </a-timeline>
      </div>

      <!-- 快捷时间设置 -->
      <div class="quick-setup">
        <h3 class="quick-title">
          <thunderbolt-outlined />
          快捷设置
        </h3>
        <div class="quick-buttons">
          <a-button @click="setQuickTime('tomorrow')"> 明天开始报名 </a-button>
          <a-button @click="setQuickTime('next_week')"> 下周开始报名 </a-button>
          <a-button @click="setQuickTime('next_month')"> 下月开始比赛 </a-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { message } from 'ant-design-vue'
import {
  UserAddOutlined,
  TrophyOutlined,
  ClockCircleOutlined,
  EyeOutlined,
  StopOutlined,
  PlayCircleOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons-vue'
import type { TournamentCreateRequest } from '@/shared/types/tournament'
import dayjs, { type Dayjs } from 'dayjs'

// dayjs 是全局可用的，无需状态检查
const isDayjsAvailable = ref(true)

// Props & Emits
interface Props {
  modelValue: Partial<TournamentCreateRequest>
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:modelValue': [value: Partial<TournamentCreateRequest>]
  validate: [isValid: boolean]
}>()

// 响应式数据
const localData = ref<Partial<TournamentCreateRequest>>({ ...props.modelValue })

// 计算属性
const registrationDuration = computed(() => {
  try {
    if (!localData.value.registration_start || !localData.value.registration_end) return null

    const start = dayjs(localData.value.registration_start)
    const end = dayjs(localData.value.registration_end)

    if (!start.isValid() || !end.isValid()) return null

    const hours = end.diff(start, 'hour')

    if (hours < 24) {
      return `${hours} 小时`
    } else {
      const days = Math.floor(hours / 24)
      const remainingHours = hours % 24
      return remainingHours > 0 ? `${days} 天 ${remainingHours} 小时` : `${days} 天`
    }
  } catch (error) {
    console.error('Error calculating registration duration:', error)
    return null
  }
})

const tournamentDuration = computed(() => {
  try {
    if (!localData.value.tournament_start || !localData.value.tournament_end) return null

    const start = dayjs(localData.value.tournament_start)
    const end = dayjs(localData.value.tournament_end)

    if (!start.isValid() || !end.isValid()) return null

    const hours = end.diff(start, 'hour')

    if (hours < 24) {
      return `${hours} 小时`
    } else {
      const days = Math.floor(hours / 24)
      const remainingHours = hours % 24
      return remainingHours > 0 ? `${days} 天 ${remainingHours} 小时` : `${days} 天`
    }
  } catch (error) {
    console.error('Error calculating tournament duration:', error)
    return null
  }
})

const hasValidTimes = computed(() => {
  return !!(
    localData.value.registration_start &&
    localData.value.registration_end &&
    localData.value.tournament_start &&
    localData.value.tournament_end
  )
})

const isStepValid = computed(() => {
  try {
    if (!hasValidTimes.value) return false

    const regStart = dayjs(localData.value.registration_start!)
    const regEnd = dayjs(localData.value.registration_end!)
    const tourStart = dayjs(localData.value.tournament_start!)
    const tourEnd = dayjs(localData.value.tournament_end!)

    // 验证时间逻辑
    return regStart.isBefore(regEnd) && regEnd.isBefore(tourStart) && tourStart.isBefore(tourEnd)
  } catch (error) {
    console.error('Error validating step:', error)
    return false
  }
})

// 日期禁用规则 - 使用 dayjs
const disabledRegistrationStartDate = (current: Date) => {
  try {
    if (!current) return false
    // 不能选择过去的日期
    const today = dayjs().startOf('day')
    return dayjs(current).isBefore(today)
  } catch (error) {
    console.error('Error in disabledRegistrationStartDate:', error)
    return false
  }
}

const disabledRegistrationEndDate = (current: Date) => {
  try {
    if (!current) return false
    if (!localData.value.registration_start) {
      const today = dayjs().startOf('day')
      return dayjs(current).isBefore(today)
    }

    // 必须在报名开始时间之后
    const regStart = dayjs(localData.value.registration_start).add(1, 'hour')
    return dayjs(current).isBefore(regStart)
  } catch (error) {
    console.error('Error in disabledRegistrationEndDate:', error)
    return false
  }
}

const disabledTournamentStartDate = (current: Date) => {
  try {
    if (!current) return false
    if (!localData.value.registration_end) {
      const today = dayjs().startOf('day')
      return dayjs(current).isBefore(today)
    }

    // 必须在报名结束时间之后
    const regEnd = dayjs(localData.value.registration_end).add(1, 'hour')
    return dayjs(current).isBefore(regEnd)
  } catch (error) {
    console.error('Error in disabledTournamentStartDate:', error)
    return false
  }
}

const disabledTournamentEndDate = (current: Date) => {
  try {
    if (!current) return false
    if (!localData.value.tournament_start) {
      const today = dayjs().startOf('day')
      return dayjs(current).isBefore(today)
    }

    // 必须在比赛开始时间之后
    const tourStart = dayjs(localData.value.tournament_start).add(1, 'hour')
    return dayjs(current).isBefore(tourStart)
  } catch (error) {
    console.error('Error in disabledTournamentEndDate:', error)
    return false
  }
}

// 方法
const formatTime = (timeString?: string) => {
  try {
    if (!timeString) return ''
    return dayjs(timeString).format('YYYY年MM月DD日 HH:mm')
  } catch (error) {
    console.error('Error formatting time:', error)
    return timeString || ''
  }
}

const handleRegistrationStartChange = (date: Dayjs | null) => {
  try {
    if (date) {
      localData.value.registration_start = date.toISOString()
      validateStep()
    }
  } catch (error) {
    console.error('Error handling registration start change:', error)
    message.error('设置报名开始时间失败')
  }
}

const handleRegistrationEndChange = (date: Dayjs | null) => {
  try {
    if (date) {
      localData.value.registration_end = date.toISOString()
      validateStep()
    }
  } catch (error) {
    console.error('Error handling registration end change:', error)
    message.error('设置报名结束时间失败')
  }
}

const handleTournamentStartChange = (date: Dayjs | null) => {
  try {
    if (date) {
      localData.value.tournament_start = date.toISOString()
      validateStep()
    }
  } catch (error) {
    console.error('Error handling tournament start change:', error)
    message.error('设置比赛开始时间失败')
  }
}

const handleTournamentEndChange = (date: Dayjs | null) => {
  try {
    if (date) {
      localData.value.tournament_end = date.toISOString()
      validateStep()
    }
  } catch (error) {
    console.error('Error handling tournament end change:', error)
    message.error('设置比赛结束时间失败')
  }
}

const setQuickTime = (type: string) => {
  try {
    const now = dayjs()

    switch (type) {
      case 'tomorrow':
        // 明天上午10点开始报名，下午6点结束，后天上午10点开始比赛，晚上10点结束
        const tomorrow = now.add(1, 'day').hour(10).minute(0).second(0)
        const tomorrowEvening = tomorrow.hour(18)
        const dayAfterTomorrow = now.add(2, 'day').hour(10).minute(0).second(0)
        const dayAfterTomorrowEvening = dayAfterTomorrow.hour(22)

        localData.value.registration_start = tomorrow.toISOString()
        localData.value.registration_end = tomorrowEvening.toISOString()
        localData.value.tournament_start = dayAfterTomorrow.toISOString()
        localData.value.tournament_end = dayAfterTomorrowEvening.toISOString()
        break

      case 'next_week':
        // 下周一开始报名，周五结束，下周六开始比赛，周日结束
        const nextMonday = now.startOf('week').add(1, 'week').hour(10).minute(0).second(0)
        localData.value.registration_start = nextMonday.toISOString()
        localData.value.registration_end = nextMonday.add(4, 'day').toISOString()
        localData.value.tournament_start = nextMonday.add(5, 'day').toISOString()
        localData.value.tournament_end = nextMonday.add(6, 'day').toISOString()
        break

      case 'next_month':
        // 下月1号开始报名，15号结束，20号开始比赛，25号结束
        const nextMonth = now.startOf('month').add(1, 'month').hour(10).minute(0).second(0)
        localData.value.registration_start = nextMonth.toISOString()
        localData.value.registration_end = nextMonth.add(14, 'day').toISOString()
        localData.value.tournament_start = nextMonth.add(19, 'day').toISOString()
        localData.value.tournament_end = nextMonth.add(24, 'day').toISOString()
        break
    }

    validateStep()
    message.success('快捷时间设置成功')
  } catch (error) {
    console.error('Error setting quick time:', error)
    message.error('设置快捷时间失败')
  }
}

const validateStep = () => {
  setTimeout(() => {
    emit('validate', isStepValid.value)
  }, 0)
}

// 防止递归更新的标志位
const isUpdatingFromProps = ref(false)
const isUpdatingFromLocal = ref(false)

const syncData = () => {
  if (!isUpdatingFromProps.value) {
    isUpdatingFromLocal.value = true
    emit('update:modelValue', localData.value)
    nextTick(() => {
      isUpdatingFromLocal.value = false
    })
  }
}

// 监听器
watch(localData, syncData, { deep: true })
watch(isStepValid, valid => {
  emit('validate', valid)
})

watch(
  () => props.modelValue,
  newValue => {
    if (!isUpdatingFromLocal.value) {
      isUpdatingFromProps.value = true
      localData.value = { ...newValue }
      nextTick(() => {
        isUpdatingFromProps.value = false
      })
    }
  },
  { deep: true }
)

// 生命周期
onMounted(() => {
  console.log('TournamentScheduleConfig组件已加载，使用 dayjs')
  validateStep()
})
</script>

<style scoped>
.tournament-schedule-config {
  max-width: 700px;
  margin: 0 auto;
}

.step-header {
  text-align: center;
  margin-bottom: 40px;
}

.step-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #262626;
  margin: 0 0 8px 0;
}

.step-description {
  color: #666;
  font-size: 14px;
  margin: 0;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.time-group {
  padding: 24px;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  background: #fafafa;
}

.group-title {
  font-size: 16px;
  font-weight: 500;
  color: #262626;
  margin: 0 0 20px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.duration-info {
  margin-top: 12px;
  padding: 8px 12px;
  background: #e6f7ff;
  border-radius: 4px;
  color: #1890ff;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.timeline-preview {
  padding: 24px;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  background: white;
}

.preview-title {
  font-size: 16px;
  font-weight: 500;
  color: #262626;
  margin: 0 0 20px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.schedule-timeline {
  margin-top: 16px;
}

.timeline-icon {
  font-size: 14px;
}

.timeline-content {
  margin-left: 8px;
}

.timeline-title {
  font-weight: 500;
  color: #262626;
  font-size: 14px;
}

.timeline-time {
  color: #666;
  font-size: 13px;
  margin-top: 2px;
}

.quick-setup {
  padding: 20px;
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  background: white;
}

.quick-title {
  font-size: 14px;
  font-weight: 500;
  color: #262626;
  margin: 0 0 16px 0;
  display: flex;
  align-items: center;
  gap: 6px;
}

.quick-buttons {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .tournament-schedule-config {
    max-width: 100%;
  }

  .step-header {
    margin-bottom: 32px;
  }

  .step-title {
    font-size: 1.3rem;
  }

  .form-section {
    gap: 24px;
  }

  .time-group {
    padding: 20px 16px;
  }

  .timeline-preview {
    padding: 20px 16px;
  }

  .quick-setup {
    padding: 16px;
  }

  .quick-buttons {
    flex-direction: column;
  }

  .quick-buttons .ant-btn {
    width: 100%;
  }
}
</style>
