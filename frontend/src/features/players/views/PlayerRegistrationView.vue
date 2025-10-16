<template>
  <div class="player-registration-view">
    <a-card>
      <template #title>
        <div class="page-header">
          <h2>选手注册</h2>
          <p>注册成为选手，加入赛区开始您的竞技之旅</p>
        </div>
      </template>

      <div v-if="playerStore.error" class="error-alert">
        <a-alert
          :message="playerStore.error"
          type="error"
          show-icon
          closable
          @close="playerStore.clearError"
        />
      </div>

      <div class="registration-content">
        <!-- Existing Profiles -->
        <div
          v-if="playerStore.hasProfiles && playerStore.regions.length > 0"
          class="existing-profiles"
        >
          <h3>您的选手档案</h3>
          <div class="profiles-grid">
            <a-card
              v-for="profile in playerStore.profiles"
              :key="profile.profile_id"
              size="small"
              class="profile-card"
            >
              <template #title>
                <div class="profile-header">
                  <span class="player-name">{{ profile.player_name }}</span>
                  <div class="header-tags">
                    <a-tag :color="getRegionColor(profile.region_id)" class="region-tag">
                      {{ getRegionName(profile.region_id) }}
                    </a-tag>
                    <a-tag :color="getPositionColor(profile.position)">
                      {{ profile.position }}
                    </a-tag>
                  </div>
                </div>
              </template>

              <div class="profile-info">
                <div class="info-row">
                  <span class="label">所属赛区:</span>
                  <span class="value">{{ getRegionName(profile.region_id) }}</span>
                </div>
                <div class="info-row">
                  <span class="label">召唤师名称:</span>
                  <span class="value">{{ profile.summoner_name }}</span>
                </div>
                <div class="info-row">
                  <span class="label">当前评分:</span>
                  <span class="value">{{ Math.round(profile.current_rating) }}</span>
                </div>
                <div class="info-row">
                  <span class="label">段位:</span>
                  <span class="value">{{ profile.rank_display }}</span>
                </div>
                <div class="info-row">
                  <span class="label">胜率:</span>
                  <span class="value">{{ Math.round(profile.win_rate) }}%</span>
                </div>
              </div>
            </a-card>
          </div>

          <a-divider />
        </div>

        <!-- Registration Form -->
        <div class="registration-form-section">
          <h3>注册新的选手档案</h3>
          <PlayerRegistrationForm @success="handleRegistrationSuccess" />
        </div>
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { usePlayerStore } from '@/shared/stores/player'
import PlayerRegistrationForm from '../components/PlayerRegistrationForm.vue'

const router = useRouter()
const playerStore = usePlayerStore()

onMounted(async () => {
  // Load existing profiles and regions
  await Promise.all([playerStore.fetchMyProfiles(), playerStore.fetchRegions(true)])
})

function handleRegistrationSuccess(result: any) {
  message.success(`成功注册为选手: ${result.player_name}`)
  // Optionally navigate to profile page
  // router.push(`/players/${result.profile_id}`)
}

function getPositionColor(position: string): string {
  const colors: Record<string, string> = {
    TOP: 'blue',
    JUNGLE: 'green',
    MIDDLE: 'gold',
    BOTTOM: 'red',
    UTILITY: 'purple',
  }
  return colors[position] || 'default'
}

function getRegionName(regionId: number): string {
  // 处理两种格式的 region_id
  // 格式1: "region_26" (选手档案中的格式)
  // 格式2: "26" (赛区API返回的格式)

  const region = playerStore.regions.find(r => r.region_id === regionId)
  return region ? region.region_name : `赛区-${regionId}`
}

function getRegionColor(regionId: number): string {
  // 为不同赛区提供不同的颜色
  const colors: Record<number, string> = {
    1: 'cyan',
    2: 'geekblue',
    3: 'purple',
    4: 'magenta',
    5: 'volcano',
    6: 'orange',
    7: 'lime',
    8: 'pink',
  }

  return colors[regionId] || 'default'
}
</script>

<style scoped>
.player-registration-view {
  max-width: 800px;
  margin: 0 auto;
  padding: 24px;

  .page-header {
    text-align: center;
    margin-bottom: 16px;

    h2 {
      margin: 0;
      color: var(--ant-color-text);
    }

    p {
      margin: 8px 0 0 0;
      color: var(--ant-color-text-secondary);
    }
  }

  .error-alert {
    margin-bottom: 24px;
  }

  .registration-content {
    .existing-profiles {
      margin-bottom: 32px;

      h3 {
        color: var(--ant-color-text);
        margin-bottom: 16px;
      }

      .profiles-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 16px;
        margin-bottom: 16px;
      }

      .profile-card {
        .profile-header {
          display: flex;
          justify-content: space-between;
          align-items: center;

          .player-name {
            font-weight: 600;
            flex: 1;
            margin-right: 12px;
          }

          .header-tags {
            display: flex;
            gap: 4px;
            flex-shrink: 0;

            .region-tag {
              font-weight: 500;
              font-size: 11px;
            }
          }
        }

        .profile-info {
          .info-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;

            .label {
              color: var(--ant-color-text-secondary);
              min-width: 80px;
            }

            .value {
              font-weight: 500;
              text-align: right;
            }
          }

          .info-row:first-child {
            .label {
              font-weight: 600;
              color: var(--ant-color-primary);
            }

            .value {
              color: var(--ant-color-primary);
              font-weight: 600;
            }
          }
        }
      }
    }

    .registration-form-section {
      h3 {
        color: var(--ant-color-text);
        margin-bottom: 24px;
      }
    }
  }
}

@media (max-width: 768px) {
  .player-registration-view {
    padding: 16px;

    .profiles-grid {
      grid-template-columns: 1fr !important;
    }

    .profile-card {
      .profile-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 8px;

        .player-name {
          margin-right: 0;
        }

        .header-tags {
          align-self: flex-end;
        }
      }

      .profile-info {
        .info-row {
          .label {
            min-width: 70px;
            font-size: 12px;
          }

          .value {
            font-size: 12px;
          }
        }
      }
    }
  }
}
</style>
