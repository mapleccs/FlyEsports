<template>
  <div class="tournament-rules-config">
    <!-- 调试信息 -->
    <div
      style="
        background: #f6ffed;
        padding: 8px;
        margin-bottom: 16px;
        border-radius: 4px;
        font-size: 12px;
      "
    >
      <strong>调试信息:</strong> TournamentRulesConfig组件已加载
    </div>

    <div class="step-header">
      <h2 class="step-title">比赛规则设置</h2>
      <p class="step-description">配置赛制格式、参与限制和其他比赛规则</p>
    </div>

    <div class="form-section">
      <!-- 赛制格式 -->
      <div class="rule-group">
        <h3 class="group-title">
          <setting-outlined />
          赛制格式
        </h3>

        <a-form-item
          name="format"
          :rules="[{ required: true, message: '请选择赛制格式', trigger: 'change' }]"
        >
          <a-radio-group v-model:value="localData.format" size="large" @change="validateStep">
            <div class="format-options">
              <a-radio-button value="single_elimination" class="format-option">
                <div class="option-content">
                  <div class="option-title">单败淘汰赛</div>
                  <div class="option-desc">败者直接淘汰，胜者继续</div>
                </div>
              </a-radio-button>

              <a-radio-button value="double_elimination" class="format-option">
                <div class="option-content">
                  <div class="option-title">双败淘汰赛</div>
                  <div class="option-desc">败者进入败者组，有复活机会</div>
                </div>
              </a-radio-button>

              <a-radio-button value="round_robin" class="format-option">
                <div class="option-content">
                  <div class="option-title">循环赛</div>
                  <div class="option-desc">所有队伍互相对战</div>
                </div>
              </a-radio-button>

              <a-radio-button value="swiss" class="format-option">
                <div class="option-content">
                  <div class="option-title">瑞士轮</div>
                  <div class="option-desc">多轮配对，积分排名</div>
                </div>
              </a-radio-button>
            </div>
          </a-radio-group>
        </a-form-item>

        <div v-if="formatDescription" class="format-description">
          <info-circle-outlined />
          {{ formatDescription }}
        </div>
      </div>

      <!-- 参与限制 -->
      <div class="rule-group">
        <h3 class="group-title">
          <team-outlined />
          参与设置
        </h3>

        <a-row :gutter="24">
          <a-col :xs="24" :md="12">
            <a-form-item
              label="最大参与数"
              name="max_participants"
              :rules="[
                { required: true, message: '请设置最大参与数', trigger: 'blur' },
                {
                  type: 'number',
                  min: 2,
                  max: 1000,
                  message: '参与数应在2-1000之间',
                  trigger: 'blur',
                },
              ]"
            >
              <a-input-number
                v-model:value="localData.max_participants"
                :min="2"
                :max="1000"
                :step="formatStep"
                size="large"
                style="width: 100%"
                :addon-after="participantUnit"
                @change="validateStep"
              />
            </a-form-item>
          </a-col>

          <a-col :xs="24" :md="12" v-if="props.modelValue.tournament_type === 'team_based'">
            <a-form-item
              label="队伍人数"
              name="team_size"
              :rules="[
                {
                  type: 'number',
                  min: 1,
                  max: 10,
                  message: '队伍人数应在1-10之间',
                  trigger: 'blur',
                },
              ]"
            >
              <a-input-number
                v-model:value="localData.team_size"
                :min="1"
                :max="10"
                size="large"
                style="width: 100%"
                addon-after="人"
                placeholder="5"
                @change="validateStep"
              />
            </a-form-item>
          </a-col>
        </a-row>
      </div>

      <!-- 段位限制 -->
      <div class="rule-group">
        <h3 class="group-title">
          <crown-outlined />
          段位限制
        </h3>

        <a-row :gutter="16">
          <a-col :xs="24" :md="12">
            <a-form-item label="最低段位要求">
              <a-select
                v-model:value="localData.min_rank"
                placeholder="无限制"
                size="large"
                allow-clear
                @change="handleRankChange"
              >
                <a-select-option
                  v-for="rank in rankOptions"
                  :key="rank.value"
                  :value="rank.value"
                  :disabled="maxRankValue && rank.order > maxRankValue"
                >
                  {{ rank.label }}
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>

          <a-col :xs="24" :md="12">
            <a-form-item label="最高段位限制">
              <a-select
                v-model:value="localData.max_rank"
                placeholder="无限制"
                size="large"
                allow-clear
                @change="handleRankChange"
              >
                <a-select-option
                  v-for="rank in rankOptions"
                  :key="rank.value"
                  :value="rank.value"
                  :disabled="minRankValue && rank.order < minRankValue"
                >
                  {{ rank.label }}
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <div v-if="rankRequirement" class="rank-info">
          <star-outlined />
          段位要求：{{ rankRequirement }}
        </div>
      </div>

      <!-- 规则预览 -->
      <div class="rules-preview">
        <h3 class="preview-title">
          <eye-outlined />
          规则预览
        </h3>

        <a-descriptions :column="1" bordered size="small">
          <a-descriptions-item label="赛制格式">
            <a-tag :color="formatConfig.color">{{ formatConfig.text }}</a-tag>
          </a-descriptions-item>

          <a-descriptions-item label="参与规模">
            {{ localData.max_participants }} {{ participantUnit }}
          </a-descriptions-item>

          <a-descriptions-item
            v-if="props.modelValue.tournament_type === 'team_based'"
            label="队伍规模"
          >
            {{ localData.team_size || 5 }} 人/队
          </a-descriptions-item>

          <a-descriptions-item label="段位要求">
            {{ rankRequirement || '无限制' }}
          </a-descriptions-item>

          <a-descriptions-item label="预计比赛轮数">
            <span class="highlight">{{ estimatedRounds }}</span>
          </a-descriptions-item>

          <a-descriptions-item label="预计比赛场次">
            <span class="highlight">{{ estimatedMatches }}</span>
          </a-descriptions-item>
        </a-descriptions>
      </div>

      <!-- 建议设置 -->
      <div class="suggestions">
        <h3 class="suggestions-title">
          <bulb-outlined />
          建议设置
        </h3>

        <div class="suggestion-cards">
          <a-card
            v-for="suggestion in suggestions"
            :key="suggestion.title"
            size="small"
            class="suggestion-card"
            @click="applySuggestion(suggestion)"
          >
            <template #title>
              <div class="suggestion-header">
                <component :is="suggestion.icon" />
                {{ suggestion.title }}
              </div>
            </template>

            <p class="suggestion-desc">{{ suggestion.description }}</p>
            <div class="suggestion-rules">
              <div v-for="rule in suggestion.rules" :key="rule" class="rule-item">
                <check-outlined />
                {{ rule }}
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
  SettingOutlined,
  TeamOutlined,
  CrownOutlined,
  EyeOutlined,
  InfoCircleOutlined,
  StarOutlined,
  BulbOutlined,
  CheckOutlined,
  TrophyOutlined,
  ThunderboltOutlined,
  FireOutlined,
} from '@ant-design/icons-vue'
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

// 段位选项
const rankOptions = [
  { label: '坚韧黑铁', value: 'Iron', order: 1 },
  { label: '英勇黄铜', value: 'Bronze', order: 2 },
  { label: '不屈白银', value: 'Silver', order: 3 },
  { label: '荣耀黄金', value: 'Gold', order: 4 },
  { label: '华贵铂金', value: 'Platinum', order: 5 },
  { label: '璀璨钻石', value: 'Diamond', order: 6 },
  { label: '超凡大师', value: 'Master', order: 7 },
  { label: '傲世宗师', value: 'Grandmaster', order: 8 },
  { label: '最强王者', value: 'Challenger', order: 9 },
]

// 计算属性
const formatConfig = computed(() => {
  const formatMap = {
    single_elimination: { text: '单败淘汰赛', color: 'blue' },
    double_elimination: { text: '双败淘汰赛', color: 'green' },
    round_robin: { text: '循环赛', color: 'orange' },
    swiss: { text: '瑞士轮', color: 'purple' },
  }
  return formatMap[localData.value.format as keyof typeof formatMap] || formatMap.single_elimination
})

const formatDescription = computed(() => {
  const descriptions = {
    single_elimination: '最经典的淘汰赛制，败者直接出局，比赛节奏快，适合大规模赛事。',
    double_elimination: '给败者一次复活机会，比赛更加公平，但耗时较长。',
    round_robin: '每支队伍都要与其他队伍交战一次，最公平但耗时最长。',
    swiss: '根据积分和胜负记录进行配对，平衡公平性和效率。',
  }
  return descriptions[localData.value.format as keyof typeof descriptions] || ''
})

const participantUnit = computed(() => {
  return props.modelValue.tournament_type === 'team_based' ? '支队伍' : '名选手'
})

const formatStep = computed(() => {
  // 根据赛制推荐的参与数增量
  const steps = {
    single_elimination: 2, // 2的幂次
    double_elimination: 2,
    round_robin: 1,
    swiss: 1,
  }
  return steps[localData.value.format as keyof typeof steps] || 1
})

const minRankValue = computed(() => {
  if (!localData.value.min_rank) return null
  return rankOptions.find(r => r.value === localData.value.min_rank)?.order || null
})

const maxRankValue = computed(() => {
  if (!localData.value.max_rank) return null
  return rankOptions.find(r => r.value === localData.value.max_rank)?.order || null
})

const rankRequirement = computed(() => {
  const { min_rank, max_rank } = localData.value
  if (min_rank && max_rank) {
    const minLabel = rankOptions.find(r => r.value === min_rank)?.label
    const maxLabel = rankOptions.find(r => r.value === max_rank)?.label
    return `${minLabel} - ${maxLabel}`
  } else if (min_rank) {
    const minLabel = rankOptions.find(r => r.value === min_rank)?.label
    return `${minLabel} 以上`
  } else if (max_rank) {
    const maxLabel = rankOptions.find(r => r.value === max_rank)?.label
    return `${maxLabel} 以下`
  }
  return null
})

const estimatedRounds = computed(() => {
  const participants = localData.value.max_participants || 16
  const format = localData.value.format

  switch (format) {
    case 'single_elimination':
      return `${Math.ceil(Math.log2(participants))} 轮`
    case 'double_elimination':
      return `${Math.ceil(Math.log2(participants)) + 2} 轮`
    case 'round_robin':
      return `${participants - 1} 轮`
    case 'swiss':
      return `${Math.ceil(Math.log2(participants))} 轮`
    default:
      return '待确定'
  }
})

const estimatedMatches = computed(() => {
  const participants = localData.value.max_participants || 16
  const format = localData.value.format

  switch (format) {
    case 'single_elimination':
      return `${participants - 1} 场`
    case 'double_elimination':
      return `${participants * 2 - 3} 场`
    case 'round_robin':
      return `${(participants * (participants - 1)) / 2} 场`
    case 'swiss':
      return `${(participants * Math.ceil(Math.log2(participants))) / 2} 场`
    default:
      return '待确定'
  }
})

const suggestions = computed(() => [
  {
    title: '新手友好赛',
    icon: TrophyOutlined,
    description: '适合新手参与的小规模赛事',
    rules: ['16支队伍单败淘汰', '最高段位限制：黄金', '5人队伍标准配置'],
    config: {
      format: 'single_elimination',
      max_participants: 16,
      team_size: 5,
      min_rank: '',
      max_rank: 'Gold',
    },
  },
  {
    title: '竞技精英赛',
    icon: ThunderboltOutlined,
    description: '高水平玩家的激烈对抗',
    rules: ['32支队伍双败淘汰', '最低段位要求：钻石', '5人队伍标准配置'],
    config: {
      format: 'double_elimination',
      max_participants: 32,
      team_size: 5,
      min_rank: 'Diamond',
      max_rank: '',
    },
  },
  {
    title: '大型联赛',
    icon: FireOutlined,
    description: '大规模长期联赛制',
    rules: ['64支队伍瑞士轮', '无段位限制', '5人队伍标准配置'],
    config: {
      format: 'swiss',
      max_participants: 64,
      team_size: 5,
      min_rank: '',
      max_rank: '',
    },
  },
])

const isStepValid = computed(() => {
  return !!(
    localData.value.format &&
    localData.value.max_participants &&
    localData.value.max_participants >= 2 &&
    localData.value.max_participants <= 1000 &&
    (!localData.value.team_size ||
      (localData.value.team_size >= 1 && localData.value.team_size <= 10))
  )
})

// 方法
const handleRankChange = () => {
  validateStep()
}

const applySuggestion = (suggestion: any) => {
  Object.assign(localData.value, suggestion.config)
  validateStep()
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
  // 设置默认值
  if (!localData.value.format) {
    localData.value.format = 'single_elimination'
  }
  if (!localData.value.max_participants) {
    localData.value.max_participants = 16
  }
  if (!localData.value.team_size && props.modelValue.tournament_type === 'team_based') {
    localData.value.team_size = 5
  }

  validateStep()
})
</script>

<style scoped>
.tournament-rules-config {
  max-width: 800px;
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

.rule-group {
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

.format-options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.format-option {
  height: auto !important;
  padding: 16px !important;
  border-radius: 8px !important;
}

.option-content {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.option-title {
  font-weight: 500;
  font-size: 14px;
}

.option-desc {
  font-size: 12px;
  color: #666;
  line-height: 1.4;
}

.format-description {
  margin-top: 12px;
  padding: 12px;
  background: #e6f7ff;
  border-radius: 4px;
  color: #1890ff;
  font-size: 13px;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  line-height: 1.5;
}

.rank-info,
.highlight {
  color: #1890ff;
  font-weight: 500;
}

.rank-info {
  margin-top: 8px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.rules-preview {
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

.suggestions {
  padding: 24px;
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  background: white;
}

.suggestions-title {
  font-size: 16px;
  font-weight: 500;
  color: #262626;
  margin: 0 0 20px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.suggestion-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
}

.suggestion-card {
  cursor: pointer;
  transition: all 0.3s;
  border: 2px solid transparent;
}

.suggestion-card:hover {
  border-color: #1890ff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.15);
}

.suggestion-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.suggestion-desc {
  color: #666;
  font-size: 13px;
  margin: 0 0 12px 0;
}

.suggestion-rules {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.rule-item {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #52c41a;
  font-size: 12px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .tournament-rules-config {
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

  .rule-group,
  .rules-preview,
  .suggestions {
    padding: 20px 16px;
  }

  .format-options {
    grid-template-columns: 1fr;
  }

  .suggestion-cards {
    grid-template-columns: 1fr;
  }
}
</style>
