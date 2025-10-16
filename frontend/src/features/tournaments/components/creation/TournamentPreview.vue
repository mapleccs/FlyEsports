<template>
  <div class="tournament-preview">
    <!-- 调试信息 -->
    <div
      style="
        background: #f9f0ff;
        padding: 8px;
        margin-bottom: 16px;
        border-radius: 4px;
        font-size: 12px;
      "
    >
      <strong>调试信息:</strong> TournamentPreview组件已加载
    </div>

    <div class="step-header">
      <h2 class="step-title">预览确认</h2>
      <p class="step-description">最后检查一下赛事信息，确认无误后即可创建赛事</p>
    </div>

    <div class="preview-content">
      <!-- 赛事卡片预览 -->
      <div class="tournament-card-preview">
        <div class="card-header">
          <div class="banner-section">
            <img
              v-if="data.banner_url"
              :src="data.banner_url"
              alt="赛事横幅"
              class="banner-image"
            />
            <div v-else class="banner-placeholder">
              <picture-outlined />
              <span>暂无横幅图片</span>
            </div>
            <div class="banner-overlay"></div>

            <div class="card-title-section">
              <div class="logo-container">
                <img
                  v-if="data.logo_url"
                  :src="data.logo_url"
                  alt="赛事Logo"
                  class="tournament-logo"
                />
                <div v-else class="logo-placeholder">
                  <trophy-outlined />
                </div>
              </div>

              <div class="title-info">
                <h1 class="tournament-title">{{ data.name }}</h1>
                <div class="tournament-meta">
                  <a-tag :color="typeConfig.color" class="type-tag">
                    {{ typeConfig.text }}
                  </a-tag>
                  <span class="region-info">
                    <environment-outlined />
                    {{ regionName }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="card-content">
          <div class="description-section">
            <h3 class="section-title">赛事简介</h3>
            <p v-if="data.description" class="description-text">
              {{ data.description }}
            </p>
            <p v-else class="no-description">
              <em>暂无赛事简介</em>
            </p>
          </div>
        </div>
      </div>

      <!-- 详细信息面板 -->
      <div class="details-panels">
        <!-- 基本信息 -->
        <a-card title="基本信息" class="info-panel">
          <div class="info-grid">
            <div class="info-item">
              <label>赛事名称</label>
              <span>{{ data.name }}</span>
            </div>
            <div class="info-item">
              <label>赛事类型</label>
              <span>{{ typeConfig.text }}</span>
            </div>
            <div class="info-item">
              <label>所属赛区</label>
              <span>{{ regionName }}</span>
            </div>
          </div>
        </a-card>

        <!-- 时间安排 -->
        <a-card title="时间安排" class="info-panel">
          <div class="info-grid">
            <div class="info-item">
              <label>报名开始时间</label>
              <span>{{ formatDateTime(data.registration_start) }}</span>
            </div>
            <div class="info-item">
              <label>报名结束时间</label>
              <span>{{ formatDateTime(data.registration_end) }}</span>
            </div>
            <div class="info-item">
              <label>比赛开始时间</label>
              <span>{{ formatDateTime(data.tournament_start) }}</span>
            </div>
            <div class="info-item">
              <label>比赛结束时间</label>
              <span>{{ formatDateTime(data.tournament_end) }}</span>
            </div>
          </div>

          <div class="timeline-preview">
            <a-timeline size="small">
              <a-timeline-item color="blue">
                <template #dot>
                  <calendar-outlined />
                </template>
                <div class="timeline-content">
                  <strong>报名阶段</strong>
                  <div class="timeline-time">
                    {{ formatDateTime(data.registration_start) }} -
                    {{ formatDateTime(data.registration_end) }}
                  </div>
                </div>
              </a-timeline-item>
              <a-timeline-item color="green">
                <template #dot>
                  <trophy-outlined />
                </template>
                <div class="timeline-content">
                  <strong>比赛阶段</strong>
                  <div class="timeline-time">
                    {{ formatDateTime(data.tournament_start) }} -
                    {{ formatDateTime(data.tournament_end) }}
                  </div>
                </div>
              </a-timeline-item>
            </a-timeline>
          </div>
        </a-card>

        <!-- 规则设置 -->
        <a-card title="比赛规则" class="info-panel">
          <div class="info-grid">
            <div class="info-item">
              <label>比赛赛制</label>
              <span>{{ formatConfig.text }}</span>
            </div>
            <div class="info-item">
              <label>最大参与数</label>
              <span>{{ data.max_participants }} {{ participantUnit }}</span>
            </div>
            <div v-if="data.tournament_type === 'team_based'" class="info-item">
              <label>队伍规模</label>
              <span>{{ data.team_size }} 人/队</span>
            </div>
            <div v-if="data.min_rank || data.max_rank" class="info-item">
              <label>段位限制</label>
              <span>{{ rankRangeText }}</span>
            </div>
          </div>
        </a-card>

        <!-- 媒体资源 -->
        <a-card v-if="hasMedia" title="媒体资源" class="info-panel">
          <div class="media-grid">
            <div v-if="data.logo_url" class="media-item">
              <label>赛事Logo</label>
              <div class="media-preview">
                <img :src="data.logo_url" alt="Logo预览" />
                <div class="media-actions">
                  <a-button
                    type="text"
                    size="small"
                    @click="previewImage(data.logo_url, '赛事Logo')"
                  >
                    <eye-outlined />
                    预览
                  </a-button>
                </div>
              </div>
            </div>
            <div v-if="data.banner_url" class="media-item">
              <label>赛事横幅</label>
              <div class="media-preview banner-preview">
                <img :src="data.banner_url" alt="横幅预览" />
                <div class="media-actions">
                  <a-button
                    type="text"
                    size="small"
                    @click="previewImage(data.banner_url, '赛事横幅')"
                  >
                    <eye-outlined />
                    预览
                  </a-button>
                </div>
              </div>
            </div>
          </div>
        </a-card>
      </div>

      <!-- 数据完整性检查 -->
      <div class="data-validation-section">
        <a-card title="数据完整性检查" class="validation-card">
          <div class="validation-list">
            <div
              v-for="item in validationChecks"
              :key="item.key"
              class="validation-item"
              :class="{ 'validation-error': !item.valid, 'validation-warning': item.warning }"
            >
              <div class="validation-icon">
                <check-circle-filled v-if="item.valid && !item.warning" class="icon-success" />
                <exclamation-circle-filled v-else-if="item.warning" class="icon-warning" />
                <close-circle-filled v-else class="icon-error" />
              </div>
              <div class="validation-content">
                <div class="validation-title">{{ item.title }}</div>
                <div v-if="item.message" class="validation-message">{{ item.message }}</div>
              </div>
            </div>
          </div>
        </a-card>
      </div>

      <!-- 确认提示 -->
      <div class="confirmation-section">
        <a-alert
          message="确认创建赛事"
          description="请仔细检查以上信息，确认无误后点击「创建赛事」按钮。赛事创建后，某些信息将无法修改。"
          type="info"
          show-icon
        />

        <div class="confirmation-checklist">
          <a-checkbox v-model:checked="confirmBasicInfo">
            <span class="checklist-text">
              基本信息无误（赛事名称、类型、赛区）
              <a-tooltip title="包括赛事名称、赛事类型、所属赛区和赛事简介">
                <question-circle-outlined class="info-icon" />
              </a-tooltip>
            </span>
          </a-checkbox>
          <a-checkbox v-model:checked="confirmSchedule">
            <span class="checklist-text">
              时间安排合理（报名和比赛时间）
              <a-tooltip title="确保报名时间在比赛时间之前，且时间间隔合理">
                <question-circle-outlined class="info-icon" />
              </a-tooltip>
            </span>
          </a-checkbox>
          <a-checkbox v-model:checked="confirmRules">
            <span class="checklist-text">
              比赛规则设置正确（赛制、参与数、段位限制）
              <a-tooltip title="包括比赛赛制、最大参与数量、队伍规模和段位限制">
                <question-circle-outlined class="info-icon" />
              </a-tooltip>
            </span>
          </a-checkbox>
          <a-checkbox v-model:checked="confirmMediaRights">
            <span class="checklist-text">
              媒体资源使用权限确认
              <a-tooltip title="确认上传的Logo和横幅图片拥有使用权，不涉及版权纠纷">
                <question-circle-outlined class="info-icon" />
              </a-tooltip>
            </span>
          </a-checkbox>
          <a-checkbox v-model:checked="confirmResponsibility">
            <span class="checklist-text">
              我将负责任地组织和管理这个赛事
              <a-tooltip title="作为赛事创建者，您需要确保赛事的正常进行和参与者的良好体验">
                <question-circle-outlined class="info-icon" />
              </a-tooltip>
            </span>
          </a-checkbox>
          <a-checkbox v-model:checked="confirmTerms">
            <span class="checklist-text">
              我已阅读并同意《赛事创建协议》
              <a href="#" @click.prevent="showTermsModal = true" class="terms-link">
                查看协议内容
              </a>
            </span>
          </a-checkbox>
        </div>
      </div>
    </div>

    <!-- 图片预览模态框 -->
    <a-modal
      v-model:open="previewVisible"
      :title="previewTitle"
      :footer="null"
      width="80%"
      style="max-width: 800px"
    >
      <img :src="previewUrl" :alt="previewTitle" style="width: 100%; height: auto" />
    </a-modal>

    <!-- 赛事创建协议模态框 -->
    <a-modal v-model:open="showTermsModal" title="赛事创建协议" width="800px" :footer="null">
      <div class="terms-content">
        <h3>一、赛事创建者责任</h3>
        <p>1. 赛事创建者应确保提供的赛事信息真实、准确、完整。</p>
        <p>2. 赛事创建者有义务按照设定的时间和规则组织比赛。</p>
        <p>3. 赛事创建者应公平公正地处理比赛相关事务。</p>

        <h3>二、媒体资源使用</h3>
        <p>1. 上传的Logo和横幅图片必须拥有合法使用权。</p>
        <p>2. 不得使用他人享有版权的图片，否则承担相应法律责任。</p>
        <p>3. 平台有权对不合适的图片进行审核和删除。</p>

        <h3>三、比赛管理</h3>
        <p>1. 赛事创建者应维护良好的比赛秩序和氛围。</p>
        <p>2. 对于违规行为，赛事创建者有权采取相应措施。</p>
        <p>3. 重大争议应及时上报平台管理员处理。</p>

        <h3>四、平台权利</h3>
        <p>1. 平台有权对不符合规范的赛事进行监管。</p>
        <p>2. 对于恶意创建、虚假信息等行为，平台有权暂停或删除赛事。</p>
        <p>3. 平台保留最终解释权。</p>

        <div class="terms-footer">
          <a-button type="primary" @click="showTermsModal = false">
            我已阅读并理解协议内容
          </a-button>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import {
  PictureOutlined,
  TrophyOutlined,
  EnvironmentOutlined,
  CalendarOutlined,
  EyeOutlined,
  CheckCircleFilled,
  ExclamationCircleFilled,
  CloseCircleFilled,
  QuestionCircleOutlined,
} from '@ant-design/icons-vue'
import { regionsApi } from '@/shared/api/regions'
import type { TournamentCreateRequest } from '@/shared/types/tournament'

// Props & Emits
interface Props {
  data: Partial<TournamentCreateRequest>
}

const props = defineProps<Props>()
const emit = defineEmits<{
  validate: [isValid: boolean]
}>()

// 响应式数据
const availableRegions = ref<any[]>([])
const confirmBasicInfo = ref(false)
const confirmSchedule = ref(false)
const confirmRules = ref(false)
const confirmMediaRights = ref(false)
const confirmResponsibility = ref(false)
const confirmTerms = ref(false)
const showTermsModal = ref(false)

// 预览模态框
const previewVisible = ref(false)
const previewUrl = ref('')
const previewTitle = ref('')

// 计算属性
const typeConfig = computed(() => {
  const typeMap = {
    team_based: { color: 'blue', text: '战队赛' },
    solo_based: { color: 'green', text: '个人赛' },
  }
  return typeMap[props.data.tournament_type as keyof typeof typeMap] || typeMap.team_based
})

const formatConfig = computed(() => {
  const formatMap = {
    single_elimination: { text: '单败淘汰制' },
    double_elimination: { text: '双败淘汰制' },
    round_robin: { text: '循环积分制' },
    swiss: { text: '瑞士轮制' },
  }
  return formatMap[props.data.format as keyof typeof formatMap] || formatMap.single_elimination
})

const regionName = computed(() => {
  const region = availableRegions.value.find(r => r.region_id === props.data.region_id)
  return region?.region_name || '未知赛区'
})

const participantUnit = computed(() => {
  return props.data.tournament_type === 'team_based' ? '支队伍' : '名玩家'
})

const rankRangeText = computed(() => {
  if (props.data.min_rank && props.data.max_rank) {
    return `${props.data.min_rank} - ${props.data.max_rank}`
  } else if (props.data.min_rank) {
    return `${props.data.min_rank} 及以上`
  } else if (props.data.max_rank) {
    return `${props.data.max_rank} 及以下`
  }
  return '无限制'
})

const hasMedia = computed(() => {
  return !!(props.data.logo_url || props.data.banner_url)
})

// 数据验证检查
const validationChecks = computed(() => {
  const checks = []

  // 基本信息检查
  checks.push({
    key: 'basic-name',
    title: '赛事名称',
    valid: !!props.data.name,
    message: props.data.name ? '✓ 已设置' : '✗ 未设置赛事名称',
  })

  checks.push({
    key: 'basic-type',
    title: '赛事类型',
    valid: !!props.data.tournament_type,
    message: props.data.tournament_type ? '✓ 已设置' : '✗ 未选择赛事类型',
  })

  checks.push({
    key: 'basic-region',
    title: '所属赛区',
    valid: !!props.data.region_id,
    message: props.data.region_id ? `✓ 已选择：${regionName.value}` : '✗ 未选择赛区',
  })

  // 时间安排检查
  const registrationValid = props.data.registration_start && props.data.registration_end
  const tournamentValid = props.data.tournament_start && props.data.tournament_end

  checks.push({
    key: 'schedule-registration',
    title: '报名时间',
    valid: registrationValid,
    message: registrationValid ? '✓ 已设置报名开始和结束时间' : '✗ 未完整设置报名时间',
  })

  checks.push({
    key: 'schedule-tournament',
    title: '比赛时间',
    valid: tournamentValid,
    message: tournamentValid ? '✓ 已设置比赛开始和结束时间' : '✗ 未完整设置比赛时间',
  })

  // 时间逻辑检查
  if (registrationValid && tournamentValid) {
    const regEnd = new Date(props.data.registration_end!)
    const tournStart = new Date(props.data.tournament_start!)
    const timeGap = (tournStart.getTime() - regEnd.getTime()) / (1000 * 60 * 60) // 小时

    checks.push({
      key: 'schedule-logic',
      title: '时间安排逻辑',
      valid: timeGap >= 1,
      warning: timeGap < 24 && timeGap >= 1,
      message:
        timeGap >= 24
          ? '✓ 报名结束到比赛开始有充足准备时间'
          : timeGap >= 1
            ? '⚠ 报名结束到比赛开始间隔较短，建议至少24小时'
            : '✗ 比赛开始时间必须在报名结束之后',
    })
  }

  // 规则设置检查
  checks.push({
    key: 'rules-format',
    title: '比赛赛制',
    valid: !!props.data.format,
    message: props.data.format ? `✓ 已选择：${formatConfig.value.text}` : '✗ 未选择比赛赛制',
  })

  checks.push({
    key: 'rules-participants',
    title: '参与数量',
    valid: !!props.data.max_participants && props.data.max_participants > 0,
    message: props.data.max_participants
      ? `✓ 最多 ${props.data.max_participants} ${participantUnit.value}`
      : '✗ 未设置最大参与数量',
  })

  if (props.data.tournament_type === 'team_based') {
    checks.push({
      key: 'rules-team-size',
      title: '队伍规模',
      valid: !!props.data.team_size && props.data.team_size > 0,
      message: props.data.team_size ? `✓ ${props.data.team_size} 人/队` : '✗ 未设置队伍规模',
    })
  }

  // 可选检查项
  const hasDescription = !!props.data.description
  const hasMedia = !!(props.data.logo_url || props.data.banner_url)

  checks.push({
    key: 'optional-description',
    title: '赛事简介',
    valid: true,
    warning: !hasDescription,
    message: hasDescription ? '✓ 已设置赛事简介' : '⚠ 建议添加赛事简介以吸引更多参与者',
  })

  checks.push({
    key: 'optional-media',
    title: '媒体资源',
    valid: true,
    warning: !hasMedia,
    message: hasMedia ? '✓ 已上传Logo或横幅图片' : '⚠ 建议上传Logo或横幅图片以提升赛事形象',
  })

  return checks
})

const isDataValid = computed(() => {
  return validationChecks.value.filter(check => !check.valid).length === 0
})

const isStepValid = computed(() => {
  return (
    confirmBasicInfo.value &&
    confirmSchedule.value &&
    confirmRules.value &&
    confirmMediaRights.value &&
    confirmResponsibility.value &&
    confirmTerms.value &&
    isDataValid.value
  )
})

// 方法
const formatDateTime = (dateTime: string | undefined) => {
  if (!dateTime) return '未设置'
  try {
    const date = new Date(dateTime)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch (error) {
    return dateTime
  }
}

const previewImage = (url: string, title: string) => {
  previewUrl.value = url
  previewTitle.value = title
  previewVisible.value = true
}

const loadRegions = async () => {
  try {
    const response = await regionsApi.getRegions(true)
    availableRegions.value = response.regions || []
  } catch (error) {
    console.error('加载赛区列表失败:', error)
  }
}

const validateStep = () => {
  setTimeout(() => {
    emit('validate', isStepValid.value)
  }, 0)
}

// 监听器
watch(isStepValid, valid => {
  emit('validate', valid)
})

watch(
  [
    confirmBasicInfo,
    confirmSchedule,
    confirmRules,
    confirmMediaRights,
    confirmResponsibility,
    confirmTerms,
  ],
  () => {
    validateStep()
  }
)

watch(
  () => props.data,
  () => {
    validateStep()
  },
  { deep: true }
)

// 生命周期
onMounted(() => {
  loadRegions()
  validateStep()
})
</script>

<style scoped>
.tournament-preview {
  max-width: 1000px;
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

.preview-content {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.tournament-card-preview {
  border: 1px solid #d9d9d9;
  border-radius: 12px;
  overflow: hidden;
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.card-header {
  position: relative;
}

.banner-section {
  position: relative;
  height: 200px;
  overflow: hidden;
}

.banner-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.banner-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-size: 16px;
}

.banner-placeholder span {
  margin-top: 8px;
}

.banner-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.4);
}

.card-title-section {
  position: absolute;
  bottom: 20px;
  left: 20px;
  right: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  color: white;
}

.logo-container {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
}

.tournament-logo {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.logo-placeholder {
  color: white;
  font-size: 24px;
}

.title-info {
  flex: 1;
}

.tournament-title {
  font-size: 2rem;
  font-weight: 700;
  margin: 0 0 8px 0;
  color: white;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
}

.tournament-meta {
  display: flex;
  align-items: center;
  gap: 16px;
}

.type-tag {
  font-weight: 500;
}

.region-info {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  opacity: 0.9;
}

.card-content {
  padding: 24px;
}

.description-section {
  margin-bottom: 0;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #262626;
  margin: 0 0 12px 0;
}

.description-text {
  color: #595959;
  font-size: 15px;
  line-height: 1.6;
  margin: 0;
}

.no-description {
  color: #bfbfbf;
  font-style: italic;
  margin: 0;
}

.details-panels {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.info-panel {
  border-radius: 8px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item label {
  font-size: 13px;
  color: #666;
  font-weight: 500;
}

.info-item span {
  font-size: 14px;
  color: #262626;
}

.timeline-preview {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.timeline-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.timeline-time {
  font-size: 13px;
  color: #666;
}

.media-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.media-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.media-item label {
  font-size: 14px;
  color: #666;
  font-weight: 500;
}

.media-preview {
  position: relative;
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  overflow: hidden;
  background: #f5f5f5;
}

.media-preview img {
  width: 100%;
  height: 120px;
  object-fit: cover;
}

.banner-preview img {
  height: 80px;
}

.media-actions {
  position: absolute;
  top: 8px;
  right: 8px;
  opacity: 0;
  transition: opacity 0.3s;
}

.media-preview:hover .media-actions {
  opacity: 1;
}

.confirmation-section {
  padding: 24px;
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  background: #fafafa;
}

.confirmation-checklist {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.confirmation-checklist .ant-checkbox-wrapper {
  font-size: 14px;
  color: #595959;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .tournament-preview {
    max-width: 100%;
  }

  .step-header {
    margin-bottom: 32px;
  }

  .step-title {
    font-size: 1.3rem;
  }

  .preview-content {
    gap: 24px;
  }

  .banner-section {
    height: 160px;
  }

  .tournament-title {
    font-size: 1.5rem;
  }

  .card-title-section {
    bottom: 16px;
    left: 16px;
    right: 16px;
    gap: 12px;
  }

  .logo-container {
    width: 48px;
    height: 48px;
  }

  .card-content {
    padding: 20px 16px;
  }

  .details-panels {
    gap: 20px;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }

  .media-grid {
    grid-template-columns: 1fr;
  }

  .confirmation-section {
    padding: 20px 16px;
  }
}

/* 数据验证样式 */
.data-validation-section {
  margin-bottom: 24px;
}

.validation-card .ant-card-body {
  padding: 20px;
}

.validation-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.validation-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  border-radius: 6px;
  background: #f9f9f9;
  border: 1px solid #e8e8e8;
}

.validation-item.validation-error {
  background: #fff2f0;
  border-color: #ffccc7;
}

.validation-item.validation-warning {
  background: #fffbe6;
  border-color: #ffe58f;
}

.validation-icon {
  margin-top: 2px;
}

.icon-success {
  color: #52c41a;
}

.icon-warning {
  color: #faad14;
}

.icon-error {
  color: #ff4d4f;
}

.validation-content {
  flex: 1;
}

.validation-title {
  font-weight: 500;
  color: #262626;
  margin-bottom: 4px;
}

.validation-message {
  font-size: 13px;
  color: #666;
}

/* 确认清单样式增强 */
.checklist-text {
  display: flex;
  align-items: center;
  gap: 6px;
}

.info-icon {
  color: #bfbfbf;
  font-size: 12px;
}

.info-icon:hover {
  color: #1890ff;
}

.terms-link {
  color: #1890ff;
  text-decoration: underline;
  margin-left: 8px;
}

.terms-link:hover {
  color: #40a9ff;
}

/* 协议模态框样式 */
.terms-content {
  max-height: 500px;
  overflow-y: auto;
  padding: 0 8px;
}

.terms-content h3 {
  color: #262626;
  font-size: 16px;
  font-weight: 600;
  margin: 20px 0 12px 0;
}

.terms-content h3:first-child {
  margin-top: 0;
}

.terms-content p {
  color: #595959;
  font-size: 14px;
  line-height: 1.6;
  margin: 8px 0;
  padding-left: 12px;
}

.terms-footer {
  text-align: center;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}
</style>
