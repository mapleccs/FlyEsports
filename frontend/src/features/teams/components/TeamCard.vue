<template>
  <a-card class="team-card" hoverable @click="$emit('click')">
    <template #cover>
      <div class="team-cover">
        <div class="team-logo">
          <a-avatar :size="64" :src="team.logo" class="logo-avatar">
            {{ team.name.charAt(0) }}
          </a-avatar>
        </div>
        <div class="team-status">
          <a-tag :color="team.status === 'active' ? 'green' : 'orange'" class="status-tag">
            {{ getStatusText(team.status) }}
          </a-tag>
        </div>
      </div>
    </template>

    <template #actions>
      <a-button v-if="canJoin" type="primary" size="small" @click.stop="$emit('join', team.id)">
        申请加入
      </a-button>
      <a-button v-else-if="team.recruitment_status === 'closed'" disabled size="small">
        暂不招募
      </a-button>
      <a-button v-else type="default" size="small" @click.stop="$emit('click')">
        查看详情
      </a-button>
    </template>

    <a-card-meta>
      <template #title>
        <div class="team-header">
          <span class="team-name">{{ team.name }}</span>
          <a-tag class="team-tag">{{ team.tag }}</a-tag>
        </div>
      </template>

      <template #description>
        <div class="team-info">
          <div class="team-description" v-if="team.description">
            {{ team.description }}
          </div>
          <div class="team-stats">
            <div class="stat-item">
              <team-outlined />
              <span>{{ team.member_count }}人</span>
            </div>
            <div class="stat-item" v-if="team.win_rate !== undefined">
              <trophy-outlined />
              <span>{{ (team.win_rate * 100).toFixed(1) }}%</span>
            </div>
          </div>
          <div class="recruitment-info">
            <a-tag
              :color="team.recruitment_status === 'open' ? 'blue' : 'default'"
              class="recruitment-tag"
            >
              {{ getRecruitmentText(team.recruitment_status) }}
            </a-tag>
            <span v-if="team.recruitment_note" class="recruitment-note">
              {{ team.recruitment_note }}
            </span>
          </div>
        </div>
      </template>
    </a-card-meta>
  </a-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { TeamOutlined, TrophyOutlined } from '@ant-design/icons-vue'
import type { Team, TeamStatus, RecruitmentStatus } from '@/shared/types/team'

interface Props {
  team: Team
  canJoin?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  canJoin: false,
})

defineEmits<{
  click: []
  join: [teamId: string]
}>()

// 获取状态文本
const getStatusText = (status: TeamStatus): string => {
  const statusMap = {
    active: '活跃',
    inactive: '非活跃',
    pending: '待审核',
    disbanded: '已解散',
  }
  return statusMap[status] || status
}

// 获取招募状态文本
const getRecruitmentText = (status: RecruitmentStatus): string => {
  const statusMap = {
    open: '正在招募',
    closed: '暂不招募',
  }
  return statusMap[status] || status
}
</script>

<style scoped>
.team-card {
  height: 100%;
  transition: all 0.3s ease;
  cursor: pointer;
}

.team-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.team-cover {
  position: relative;
  padding: 24px;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  text-align: center;
  min-height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.team-logo {
  position: relative;
}

.logo-avatar {
  border: 3px solid #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  background: #1890ff;
  color: #fff;
  font-weight: bold;
  font-size: 24px;
}

.team-status {
  position: absolute;
  top: 8px;
  right: 8px;
}

.status-tag {
  margin: 0;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 10px;
}

.team-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.team-name {
  font-weight: 600;
  font-size: 16px;
  color: #262626;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.team-tag {
  background: #f0f0f0;
  color: #595959;
  border: none;
  font-weight: 500;
  font-family: 'Courier New', monospace;
  margin: 0;
}

.team-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.team-description {
  color: #666;
  font-size: 13px;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

.team-stats {
  display: flex;
  gap: 16px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #8c8c8c;
  font-size: 12px;
}

.stat-item .anticon {
  font-size: 14px;
}

.recruitment-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.recruitment-tag {
  margin: 0;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 10px;
}

.recruitment-note {
  color: #8c8c8c;
  font-size: 11px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:deep(.ant-card-body) {
  padding: 16px;
}

:deep(.ant-card-actions) {
  padding: 8px 16px;
  border-top: 1px solid #f0f0f0;
}

:deep(.ant-card-actions > li) {
  margin: 0;
  padding: 0;
}

:deep(.ant-card-actions > li > span) {
  width: 100%;
}

:deep(.ant-card-meta-description) {
  margin-top: 8px;
}

@media (max-width: 768px) {
  .team-cover {
    min-height: 100px;
    padding: 16px;
  }

  .logo-avatar {
    width: 48px !important;
    height: 48px !important;
    font-size: 20px;
  }

  .team-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .team-stats {
    flex-wrap: wrap;
    gap: 12px;
  }
}
</style>
