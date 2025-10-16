<template>
  <div class="player-registration-form">
    <a-form ref="formRef" :model="formData" :rules="rules" layout="vertical" @finish="handleSubmit">
      <!-- Region Selection -->
      <a-form-item label="选择赛区" name="region_id" required>
        <a-select
          v-model:value="formData.region_id"
          placeholder="请选择要加入的赛区"
          :loading="playerStore.loading"
        >
          <a-select-option
            v-for="region in playerStore.activeRegions"
            :key="region.region_id"
            :value="region.region_id"
          >
            {{ region.region_name }} ({{ region.active_players }} 名选手)
          </a-select-option>
        </a-select>
      </a-form-item>

      <!-- Player Name -->
      <a-form-item label="选手名称" name="player_name" required>
        <a-input
          v-model:value="formData.player_name"
          placeholder="请输入您的选手名称"
          :maxlength="100"
          show-count
        />
      </a-form-item>

      <!-- Summoner Name -->
      <a-form-item label="召唤师名称" name="summoner_name" required>
        <a-input
          v-model:value="formData.summoner_name"
          placeholder="请输入您的LOL召唤师名称"
          :maxlength="50"
          show-count
          @blur="checkSummonerAvailability"
        />
        <div v-if="summonerCheckResult" class="summoner-check-result">
          <a-alert
            v-if="!summonerCheckResult.available"
            message="召唤师名称已被使用"
            description="请尝试其他召唤师名称"
            type="error"
            show-icon
          />
          <a-alert v-else message="召唤师名称可用" type="success" show-icon />
        </div>
      </a-form-item>

      <!-- Position -->
      <a-form-item label="主要位置" name="position" required>
        <a-radio-group v-model:value="formData.position">
          <a-radio-button
            v-for="position in POSITIONS"
            :key="position.value"
            :value="position.value"
          >
            {{ position.label }}
          </a-radio-button>
        </a-radio-group>
        <div v-if="formData.position" class="position-description">
          {{ getPositionInfo(formData.position).description }}
        </div>
      </a-form-item>

      <!-- Rank Information -->
      <a-divider>段位信息 (可选)</a-divider>

      <a-row :gutter="16">
        <a-col :span="12">
          <a-form-item label="段位" name="rank_tier">
            <a-select
              v-model:value="formData.rank_tier"
              placeholder="请选择您的段位"
              allow-clear
              @change="handleRankTierChange"
            >
              <a-select-option v-for="tier in RANK_TIERS" :key="tier.value" :value="tier.value">
                <span :style="{ color: tier.color, fontWeight: 'bold' }">
                  {{ tier.label }}
                </span>
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>

        <a-col :span="12">
          <a-form-item label="段位等级" name="rank_division" v-if="needsDivision">
            <a-select
              v-model:value="formData.rank_division"
              placeholder="请选择段位等级"
              allow-clear
            >
              <a-select-option
                v-for="division in RANK_DIVISIONS"
                :key="division.value"
                :value="division.value"
              >
                {{ division.label }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <!-- League Points -->
      <a-form-item label="胜点 (LP)" name="league_points" v-if="formData.rank_tier">
        <a-input-number
          v-model:value="formData.league_points"
          placeholder="请输入当前LP"
          :min="0"
          :max="10000"
          style="width: 100%"
        />
      </a-form-item>

      <!-- Description -->
      <a-form-item label="个人简介" name="description">
        <a-textarea
          v-model:value="formData.description"
          placeholder="请输入个人简介 (可选)"
          :maxlength="500"
          show-count
          :rows="4"
        />
      </a-form-item>

      <!-- Submit Button -->
      <a-form-item>
        <a-button
          type="primary"
          html-type="submit"
          :loading="playerStore.loading"
          :disabled="!isFormValid"
          block
          size="large"
        >
          注册为选手
        </a-button>
      </a-form-item>
    </a-form>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { message } from 'ant-design-vue'
import { usePlayerStore } from '@/shared/stores/player'
import { POSITIONS, RANK_TIERS, RANK_DIVISIONS, getPositionInfo } from '@/shared/types/player'
import type {
  PlayerRegistrationData,
  Position,
  RankTier,
  RankDivision,
} from '@/shared/types/player'
import type { SummonerAvailabilityResponse } from '@/shared/api/players'

const emit = defineEmits<{
  success: [result: any]
}>()

const playerStore = usePlayerStore()
const formRef = ref()

// Form data
const formData = reactive<PlayerRegistrationData>({
  region_id: 0,
  player_name: '',
  summoner_name: '',
  position: 'TOP' as Position,
  rank_tier: undefined,
  rank_division: undefined,
  league_points: undefined,
  description: '',
})

// Summoner availability check
const summonerCheckResult = ref<SummonerAvailabilityResponse | null>(null)

// Computed
const needsDivision = computed(() => {
  return formData.rank_tier && !['MASTER', 'GRANDMASTER', 'CHALLENGER'].includes(formData.rank_tier)
})

const isFormValid = computed(() => {
  return (
    formData.region_id &&
    formData.player_name &&
    formData.summoner_name &&
    formData.position &&
    (!summonerCheckResult.value || summonerCheckResult.value.available)
  )
})

// Form validation rules
const rules = {
  region_id: [{ required: true, message: '请选择赛区', trigger: 'change' }],
  player_name: [
    { required: true, message: '请输入选手名称', trigger: 'blur' },
    { min: 2, max: 100, message: '选手名称长度为 2-100 个字符', trigger: 'blur' },
  ],
  summoner_name: [
    { required: true, message: '请输入召唤师名称', trigger: 'blur' },
    { min: 2, max: 50, message: '召唤师名称长度为 2-50 个字符', trigger: 'blur' },
  ],
  position: [{ required: true, message: '请选择主要位置', trigger: 'change' }],
}

// Methods
async function checkSummonerAvailability() {
  if (!formData.summoner_name || !formData.region_id) {
    summonerCheckResult.value = null
    return
  }

  try {
    const available = await playerStore.checkSummonerAvailability(
      formData.summoner_name,
      formData.region_id
    )
    summonerCheckResult.value = {
      available,
      summoner_name: formData.summoner_name,
      region_id: formData.region_id,
    }
  } catch (error) {
    console.error('Failed to check summoner availability:', error)
  }
}

function handleRankTierChange() {
  // Clear division when changing tier
  if (needsDivision.value) {
    formData.rank_division = undefined
  }
}

async function handleSubmit() {
  try {
    const result = await playerStore.registerPlayer(formData)
    message.success('选手注册成功!')
    emit('success', result)
  } catch (error) {
    // Error is handled in the store
  }
}

// Watch for region/summoner changes to recheck availability
watch([() => formData.region_id, () => formData.summoner_name], () => {
  summonerCheckResult.value = null
})
</script>

<style scoped>
.player-registration-form {
  .position-description {
    color: var(--ant-color-text-secondary);
    font-size: 12px;
    margin-top: 4px;
  }

  .summoner-check-result {
    margin-top: 8px;
  }
}
</style>
