<template>
  <div class="tournament-basic-info">
    <div class="step-header">
      <h2 class="step-title">基本信息设置</h2>
      <p class="step-description">请填写赛事的基本信息，包括名称、类型和简介</p>
    </div>

    <div class="form-section">
      <!-- 赛事名称 -->
      <a-form-item
        label="赛事名称"
        name="name"
        :rules="[
          { required: true, message: '请输入赛事名称', trigger: 'blur' },
          { min: 2, max: 100, message: '赛事名称长度应在2-100字符之间', trigger: 'blur' },
        ]"
      >
        <a-input
          v-model:value="localData.name"
          placeholder="例如：第一届FlyEsports社区杯"
          size="large"
          show-count
          :maxlength="100"
          @blur="validateStep"
        />
      </a-form-item>

      <!-- 赛事类型 -->
      <a-form-item
        label="赛事类型"
        name="tournament_type"
        :rules="[{ required: true, message: '请选择赛事类型', trigger: 'change' }]"
      >
        <a-radio-group
          v-model:value="localData.tournament_type"
          size="large"
          @change="validateStep"
        >
          <a-radio-button value="team_based">
            <team-outlined />
            战队赛
          </a-radio-button>
          <a-radio-button value="solo_based">
            <user-outlined />
            个人赛
          </a-radio-button>
        </a-radio-group>
        <div class="type-description">
          <div v-if="localData.tournament_type === 'team_based'" class="type-help">
            <info-circle-outlined />
            只有战队队长可以为队伍报名参赛
          </div>
          <div v-else-if="localData.tournament_type === 'solo_based'" class="type-help">
            <info-circle-outlined />
            任何无战队身份的玩家均可报名参赛
          </div>
        </div>
      </a-form-item>

      <!-- 赛区选择 -->
      <a-form-item
        label="所属赛区"
        name="region_id"
        :rules="[{ required: true, message: '请选择所属赛区', trigger: 'change' }]"
      >
        <a-select
          v-model:value="localData.region_id"
          :placeholder="getRegionSelectPlaceholder()"
          size="large"
          :loading="regionsLoading"
          :disabled="availableRegions.length === 0 && !regionsLoading"
          @change="handleRegionChange"
        >
          <a-select-option
            v-for="region in availableRegions"
            :key="region.region_id"
            :value="region.region_id"
          >
            {{ region.region_name }}
          </a-select-option>
        </a-select>
        <div class="field-help">
          <info-circle-outlined />
          <span v-if="availableRegions.length > 0">
            您只能在有管理权限的赛区创建赛事
          </span>
          <span v-else-if="regionsLoading" style="color: #1890ff">
            正在加载赛区数据...
          </span>
          <span v-else-if="regionsLoadError" style="color: #ff4d4f">
            赛区数据加载失败: {{ regionsLoadError }}，
            <a @click="loadRegions" style="color: #1890ff">点击重试</a>
          </span>
          <span v-else style="color: #ff4d4f">
            无可用赛区，
            <a @click="loadRegions" style="color: #1890ff">点击重试</a>
          </span>
        </div>
      </a-form-item>

      <!-- 赛事简介 -->
      <a-form-item
        label="赛事简介"
        name="description"
        :rules="[{ max: 2000, message: '简介长度不能超过2000字符', trigger: 'blur' }]"
      >
        <a-textarea
          v-model:value="localData.description"
          placeholder="请描述赛事的背景、目的、奖励等信息，让玩家更好地了解这场赛事..."
          :rows="6"
          show-count
          :maxlength="2000"
          @blur="validateStep"
        />
      </a-form-item>

      <!-- 预览卡片 -->
      <div v-if="localData.name" class="preview-section">
        <h3 class="preview-title">
          <eye-outlined />
          预览效果
        </h3>
        <div class="preview-card">
          <a-card hoverable>
            <template #title>
              <div class="preview-card-title">
                <trophy-outlined class="title-icon" />
                {{ localData.name }}
              </div>
            </template>
            <template #extra>
              <a-tag :color="typeConfig.color">{{ typeConfig.text }}</a-tag>
            </template>

            <div class="preview-description">
              <p v-if="localData.description" class="description-text">
                {{ truncatedDescription }}
              </p>
              <p v-else class="no-description">
                <em>暂无赛事简介</em>
              </p>
            </div>

            <div class="preview-meta">
              <div class="meta-item">
                <environment-outlined />
                {{ selectedRegionName }}
              </div>
              <div class="meta-item">
                <calendar-outlined />
                待设置时间
              </div>
            </div>
          </a-card>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import {
  TeamOutlined,
  UserOutlined,
  InfoCircleOutlined,
  EyeOutlined,
  TrophyOutlined,
  EnvironmentOutlined,
  CalendarOutlined,
} from '@ant-design/icons-vue'
import { regionsApi } from '@/shared/api/regions'
import type { TournamentCreateRequest } from '@/shared/types/tournament'

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
const availableRegions = ref<any[]>([])
const regionsLoading = ref(false)
const regionsLoadError = ref<string | null>(null)

// 计算属性
const typeConfig = computed(() => {
  const typeMap = {
    team_based: { color: 'blue', text: '战队赛' },
    solo_based: { color: 'green', text: '个人赛' },
  }
  return typeMap[localData.value.tournament_type as keyof typeof typeMap] || typeMap.team_based
})

const selectedRegionName = computed(() => {
  const region = availableRegions.value.find(r => r.region_id === localData.value.region_id)
  return region?.region_name || '未选择赛区'
})

const truncatedDescription = computed(() => {
  if (!localData.value.description) return ''
  const maxLength = 150
  return localData.value.description.length > maxLength
    ? `${localData.value.description.substring(0, maxLength)}...`
    : localData.value.description
})

const isStepValid = computed(() => {
  const isValid = !!(
    localData.value.name &&
    localData.value.name.trim().length >= 2 &&
    localData.value.name.trim().length <= 100 &&
    localData.value.tournament_type &&
    typeof localData.value.region_id === 'number' &&
    localData.value.region_id > 0
  )

  console.log('TournamentBasicInfo 验证结果:', {
    name: localData.value.name,
    nameValid:
      localData.value.name &&
      localData.value.name.trim().length >= 2 &&
      localData.value.name.trim().length <= 100,
    typeValid: !!localData.value.tournament_type,
    regionId: localData.value.region_id,
    regionIdType: typeof localData.value.region_id,
    regionValid: typeof localData.value.region_id === 'number' && localData.value.region_id > 0,
    isValid,
  })

  return isValid
})

// 方法
const getRegionSelectPlaceholder = () => {
  if (regionsLoading.value) {
    return '正在加载赛区数据...'
  }
  if (regionsLoadError.value) {
    return '赛区数据加载失败，请点击重试'
  }
  if (availableRegions.value.length === 0) {
    return '无可用赛区'
  }
  return '选择赛事所属的赛区'
}

const handleRegionChange = (value: number) => {
  console.log('用户选择赛区:', value, '类型:', typeof value)
  validateStep()
}

const loadRegions = async (): Promise<void> => {
  try {
    regionsLoading.value = true
    regionsLoadError.value = null
    console.log('开始加载赛区数据...')
    const response = await regionsApi.getRegions(true)
    availableRegions.value = response.regions || []
    console.log('赛区数据加载成功:', availableRegions.value)

    // 验证当前选中的赛区是否有效
    if (localData.value.region_id && availableRegions.value.length > 0) {
      const currentRegionId = Number(localData.value.region_id)
      const isValidRegion = availableRegions.value.some(region => 
        region.region_id === currentRegionId
      )
      
      if (!isValidRegion) {
        console.warn(`当前选中的赛区ID ${currentRegionId} 不在有效列表中，重置为默认赛区`)
        const { message } = await import('ant-design-vue')
        message.warning({
          content: '当前选中的赛区已不可用，已自动切换到默认赛区',
          duration: 3,
        })
        // 重置为第一个有效赛区（确保为数字类型）
        localData.value.region_id = availableRegions.value[0].region_id
        syncData()
      }
    } else if (!localData.value.region_id && availableRegions.value.length > 0) {
      // 如果没有设置赛区，默认选择第一个（确保为数字类型）
      localData.value.region_id = availableRegions.value[0].region_id
      console.log(
        '设置默认赛区:',
        localData.value.region_id,
        '类型:',
        typeof localData.value.region_id
      )
      // 触发数据同步
      syncData()
    }
  } catch (error: any) {
    console.error('加载赛区列表失败:', error)
    
    // 设置错误信息
    regionsLoadError.value = error.response?.data?.detail || error.message || '网络连接失败'
    
    // 使用Ant Design的message组件显示错误
    const { message } = await import('ant-design-vue')
    message.error({
      content: `无法加载赛区列表: ${regionsLoadError.value}`,
      duration: 5,
    })
    
    // 清空regions数组，显示错误状态
    availableRegions.value = []
  } finally {
    regionsLoading.value = false
  }
}

const validateStep = () => {
  // 延迟一帧来确保数据已更新
  setTimeout(() => {
    const valid = isStepValid.value
    console.log('=== 验证基本信息步骤 ===', {
      name: localData.value.name,
      nameLength: localData.value.name?.trim().length,
      tournament_type: localData.value.tournament_type,
      region_id: localData.value.region_id,
      region_id_type: typeof localData.value.region_id,
      isValid: valid,
    })
    emit('validate', valid)
    console.log('发送验证结果给父组件:', valid)
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

// 同步外部数据变化
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
  { deep: true, immediate: true }
)

// 生命周期
onMounted(async () => {
  console.log('TournamentBasicInfo 组件加载', {
    initialData: localData.value,
  })

  // 先加载赛区数据
  await loadRegions()

  // 等待数据初始化完成后再验证
  setTimeout(() => {
    validateStep()
  }, 100)
})
</script>

<style scoped>
.tournament-basic-info {
  max-width: 600px;
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
  gap: 24px;
}

.type-description {
  margin-top: 8px;
}

.type-help {
  color: #666;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.field-help {
  margin-top: 6px;
  color: #666;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.preview-section {
  margin-top: 40px;
  padding-top: 24px;
  border-top: 1px solid #f0f0f0;
}

.preview-title {
  font-size: 16px;
  font-weight: 500;
  color: #262626;
  margin: 0 0 16px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.preview-card {
  max-width: 400px;
}

.preview-card-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-icon {
  color: #faad14;
}

.preview-description {
  margin-bottom: 16px;
}

.description-text {
  color: #595959;
  font-size: 14px;
  line-height: 1.6;
  margin: 0;
}

.no-description {
  color: #bfbfbf;
  font-size: 14px;
  margin: 0;
}

.preview-meta {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #666;
  font-size: 13px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .tournament-basic-info {
    max-width: 100%;
  }

  .step-header {
    margin-bottom: 32px;
  }

  .step-title {
    font-size: 1.3rem;
  }

  .form-section {
    gap: 20px;
  }

  .preview-section {
    margin-top: 32px;
    padding-top: 20px;
  }

  .preview-card {
    max-width: 100%;
  }
}
</style>
