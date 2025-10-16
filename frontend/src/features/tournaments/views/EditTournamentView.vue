<template>
  <layout-default>
    <div class="edit-tournament-container">
      <div class="edit-tournament-header">
        <a-page-header
          :title="`编辑赛事 - ${currentTournament?.name || '加载中...'}`"
          sub-title="修改赛事信息和配置"
          @back="handleGoBack"
        >
          <template #extra>
            <a-space>
              <a-button @click="handleGoBack">取消</a-button>
              <a-button
                type="primary"
                :loading="saving"
                @click="handleSave"
                :disabled="!isFormValid"
              >
                保存更改
              </a-button>
            </a-space>
          </template>
        </a-page-header>
      </div>

      <div v-if="loading" class="loading-container">
        <a-spin size="large" />
        <p>加载赛事信息中...</p>
      </div>

      <div v-else-if="currentTournament" class="edit-tournament-content">
        <!-- 步骤导航 -->
        <div class="steps-container">
          <a-steps :current="currentStep" size="small">
            <a-step title="基本信息" description="赛事名称、类型等" />
            <a-step title="时间安排" description="报名和比赛时间" />
            <a-step title="规则设置" description="比赛规则配置" />
            <a-step title="媒体资源" description="图片和媒体" />
            <a-step title="预览确认" description="确认所有信息" />
          </a-steps>
        </div>

        <!-- 步骤内容 -->
        <div class="step-content">
          <!-- 基本信息 -->
          <tournament-basic-info
            v-if="currentStep === 0"
            :model-value="formData.basicInfo"
            :is-edit-mode="true"
            @update:model-value="data => (formData.basicInfo = data)"
            @update:valid="(valid: boolean) => (stepValidations[0] = valid)"
          />

          <!-- 时间安排 -->
          <tournament-schedule-config
            v-if="currentStep === 1"
            :model-value="formData.schedule"
            @update:model-value="data => (formData.schedule = data)"
            @update:valid="(valid: boolean) => (stepValidations[1] = valid)"
          />

          <!-- 规则设置 -->
          <tournament-rules-config
            v-if="currentStep === 2"
            :model-value="formData.rules"
            @update:model-value="data => (formData.rules = data)"
            @update:valid="(valid: boolean) => (stepValidations[2] = valid)"
          />

          <!-- 媒体上传 -->
          <tournament-media-upload
            v-if="currentStep === 3"
            :model-value="formData.media"
            @update:model-value="data => (formData.media = data)"
            @update:valid="(valid: boolean) => (stepValidations[3] = valid)"
          />

          <!-- 预览确认 -->
          <tournament-preview v-if="currentStep === 4" :data="previewData" :is-edit-mode="true" />
        </div>

        <!-- 步骤导航按钮 -->
        <div class="step-actions">
          <a-space>
            <a-button v-if="currentStep > 0" @click="handlePreviousStep"> 上一步 </a-button>
            <a-button
              v-if="currentStep < 4"
              type="primary"
              @click="handleNextStep"
              :disabled="!stepValidations[currentStep]"
            >
              下一步
            </a-button>
            <a-button v-if="currentStep === 4" type="primary" :loading="saving" @click="handleSave">
              保存更改
            </a-button>
          </a-space>
        </div>
      </div>

      <div v-else class="error-container">
        <a-result status="error" title="加载失败" sub-title="无法加载赛事信息，请稍后重试">
          <template #extra>
            <a-space>
              <a-button type="primary" @click="loadTournamentData">重新加载</a-button>
              <a-button @click="handleGoBack">返回列表</a-button>
            </a-space>
          </template>
        </a-result>
      </div>
    </div>
  </layout-default>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import LayoutDefault from '@/shared/components/layouts/LayoutDefault.vue'
import TournamentBasicInfo from '../components/creation/TournamentBasicInfo.vue'
import TournamentScheduleConfig from '../components/creation/TournamentScheduleConfig.vue'
import TournamentRulesConfig from '../components/creation/TournamentRulesConfig.vue'
import TournamentMediaUpload from '../components/creation/TournamentMediaUpload.vue'
import TournamentPreview from '../components/creation/TournamentPreview.vue'
import { useTournamentStore } from '@/shared/stores/tournament'
import type { Tournament, TournamentCreateRequest } from '@/shared/types/tournament'

const route = useRoute()
const router = useRouter()
const tournamentStore = useTournamentStore()

// 状态管理
const loading = ref(true)
const saving = ref(false)
const currentStep = ref(0)
const currentTournament = ref<Tournament | null>(null)

// 表单数据
const formData = reactive({
  basicInfo: {},
  schedule: {},
  rules: {},
  media: {},
})

// 步骤验证状态
const stepValidations = reactive([false, false, false, false, true])

// 计算属性
const isFormValid = computed(() => stepValidations.every(valid => valid))

const previewData = computed(() => ({
  ...formData.basicInfo,
  ...formData.schedule,
  ...formData.rules,
  ...formData.media,
}))

// 方法
const loadTournamentData = async () => {
  try {
    loading.value = true
    const tournamentId = route.params.id as string
    const tournament = await tournamentStore.fetchTournament(tournamentId)
    currentTournament.value = tournament

    // 将赛事数据填充到表单中
    formData.basicInfo = {
      name: tournament.name,
      description: tournament.description,
      tournament_type: tournament.tournament_type,
      region_id: tournament.region_id,
    }

    formData.schedule = {
      registration_start: tournament.registration_start,
      registration_end: tournament.registration_end,
      tournament_start: tournament.tournament_start,
      tournament_end: tournament.tournament_end,
    }

    formData.rules = {
      format: tournament.format,
      max_participants: tournament.max_participants,
      team_size: tournament.team_size,
      min_rank: tournament.min_rank,
      max_rank: tournament.max_rank,
    }

    formData.media = {
      logo_url: tournament.logo_url,
      banner_url: tournament.banner_url,
    }

    // 设置所有步骤为有效（因为数据已存在）
    stepValidations.fill(true)
  } catch (error) {
    console.error('加载赛事数据失败:', error)
    message.error('加载赛事数据失败')
  } finally {
    loading.value = false
  }
}

const handleGoBack = () => {
  router.push('/tournaments')
}

const handlePreviousStep = () => {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

const handleNextStep = () => {
  if (currentStep.value < 4 && stepValidations[currentStep.value]) {
    currentStep.value++
  }
}

const handleSave = async () => {
  if (!isFormValid.value || !currentTournament.value) {
    message.warning('请完善所有必填信息')
    return
  }

  try {
    saving.value = true

    const updateData: Partial<TournamentCreateRequest> = {
      ...formData.basicInfo,
      ...formData.schedule,
      ...formData.rules,
      ...formData.media,
    } as Partial<TournamentCreateRequest>

    await tournamentStore.updateTournament(currentTournament.value.id, updateData)

    message.success('赛事更新成功')
    router.push('/tournaments')
  } catch (error) {
    console.error('更新赛事失败:', error)
    message.error('更新赛事失败')
  } finally {
    saving.value = false
  }
}

// 生命周期
onMounted(() => {
  loadTournamentData()
})

// 监听路由变化
watch(
  () => route.params.id,
  () => {
    if (route.params.id) {
      loadTournamentData()
    }
  }
)
</script>

<style scoped>
.edit-tournament-container {
  padding: 24px;
  background: #f5f5f5;
  min-height: calc(100vh - 64px);
}

.edit-tournament-header {
  margin-bottom: 24px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  gap: 16px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.loading-container p {
  color: #666;
  font-size: 16px;
}

.error-container {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  padding: 40px;
}

.edit-tournament-content {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.steps-container {
  padding: 40px 40px 20px;
  border-bottom: 1px solid #f0f0f0;
}

.step-content {
  padding: 40px;
  min-height: 500px;
}

.step-actions {
  padding: 24px 40px;
  border-top: 1px solid #f0f0f0;
  background: #fafafa;
  display: flex;
  justify-content: flex-end;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .edit-tournament-container {
    padding: 16px;
  }

  .steps-container {
    padding: 20px 20px 10px;
  }

  .step-content {
    padding: 20px;
    min-height: 400px;
  }

  .step-actions {
    padding: 16px 20px;
  }
}
</style>
