<template>
  <div class="team-management-panel">
    <!-- 招募状态管理 -->
    <a-card title="招募管理" class="management-card">
      <a-form layout="vertical" :model="recruitmentForm" @finish="updateRecruitmentStatus">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="招募状态">
              <a-select v-model:value="recruitmentForm.status" size="large">
                <a-select-option value="open">正在招募</a-select-option>
                <a-select-option value="closed">暂不招募</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="">
              <a-button
                type="primary"
                html-type="submit"
                :loading="loading.recruitment"
                size="large"
                style="margin-top: 30px"
              >
                更新状态
              </a-button>
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item label="招募说明">
          <a-textarea
            v-model:value="recruitmentForm.note"
            placeholder="可以说明需要的位置、要求等（选填）"
            :rows="3"
            :maxlength="200"
            show-count
          />
        </a-form-item>
      </a-form>
    </a-card>

    <!-- 入队申请管理 -->
    <a-card class="management-card">
      <template #title>
        <div class="card-title-with-badge">
          <span>入队申请</span>
          <a-badge
            :count="pendingApplications.length"
            :number-style="{ backgroundColor: '#52c41a' }"
          />
        </div>
      </template>

      <a-list
        :data-source="applications"
        :loading="loading.applications"
        :locale="{ emptyText: '暂无申请' }"
      >
        <template #renderItem="{ item }">
          <a-list-item>
            <template #actions>
              <a-space v-if="item.status === 'pending'">
                <a-button
                  type="primary"
                  size="small"
                  @click="handleApplication(item.id, 'approve')"
                  :loading="loading.handleApplication"
                >
                  批准
                </a-button>
                <a-button
                  danger
                  size="small"
                  @click="handleApplication(item.id, 'reject')"
                  :loading="loading.handleApplication"
                >
                  拒绝
                </a-button>
              </a-space>
              <a-tag v-else :color="item.status === 'approved' ? 'green' : 'red'" size="small">
                {{ getApplicationStatusText(item.status) }}
              </a-tag>
            </template>

            <a-list-item-meta>
              <template #avatar>
                <a-avatar :src="item.avatar">
                  {{ item.username.charAt(0) }}
                </a-avatar>
              </template>

              <template #title>
                <div class="application-header">
                  <span class="applicant-name">{{ item.username }}</span>
                  <span class="application-time">
                    {{ formatDate(item.submitted_at) }}
                  </span>
                </div>
              </template>

              <template #description>
                <div class="application-message">
                  {{ item.message || '无申请理由' }}
                </div>
              </template>
            </a-list-item-meta>
          </a-list-item>
        </template>
      </a-list>
    </a-card>

    <!-- 成员管理 -->
    <a-card title="成员管理" class="management-card">
      <a-table
        :columns="memberColumns"
        :data-source="team?.members || []"
        :pagination="false"
        :loading="loading.members"
        size="small"
        :locale="{ emptyText: '暂无成员' }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'avatar'">
            <a-avatar :src="record.avatar" :size="32">
              {{ record.username.charAt(0) }}
            </a-avatar>
          </template>

          <template v-if="column.key === 'role'">
            <a-tag :color="getRoleColor(record.role)" size="small">
              {{ getRoleText(record.role) }}
            </a-tag>
          </template>

          <template v-if="column.key === 'joined_at'">
            {{ formatDate(record.joined_at) }}
          </template>

          <template v-if="column.key === 'actions'">
            <a-space v-if="canManageMember(record)">
              <a-dropdown v-if="canChangeRole(record)">
                <a-button size="small" type="link"> 角色 <down-outlined /> </a-button>
                <template #overlay>
                  <a-menu @click="handleMenuClick($event, record)">
                    <a-menu-item v-if="record.role !== 'captain'" key="captain">
                      任命为队长
                    </a-menu-item>
                    <a-menu-item v-if="record.role === 'captain'" key="member">
                      罢免队长
                    </a-menu-item>
                  </a-menu>
                </template>
              </a-dropdown>

              <a-popconfirm title="确定要移除此成员吗？" @confirm="removeMember(record)">
                <a-button size="small" type="link" danger :loading="loading.removeMember">
                  移除
                </a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 邀请玩家 -->
    <a-card title="邀请玩家" class="management-card">
      <a-form :model="inviteForm" @finish="sendInvitation" layout="vertical">
        <a-form-item
          label="玩家用户名"
          name="username"
          :rules="[{ required: true, message: '请输入玩家用户名' }]"
        >
          <a-auto-complete
            v-model:value="inviteForm.username"
            :options="playerSearchOptions"
            placeholder="输入用户名搜索玩家"
            @search="searchPlayers"
            @select="selectPlayer"
          >
            <template #option="{ value, username, avatar }">
              <div class="search-option">
                <a-avatar :src="avatar" :size="24">
                  {{ username.charAt(0) }}
                </a-avatar>
                <span>{{ username }}</span>
              </div>
            </template>
          </a-auto-complete>
        </a-form-item>

        <a-form-item label="邀请消息">
          <a-textarea
            v-model:value="inviteForm.message"
            placeholder="可以说明邀请理由、队伍需求等（选填）"
            :rows="3"
            :maxlength="200"
            show-count
          />
        </a-form-item>

        <a-form-item>
          <a-button type="primary" html-type="submit" :loading="loading.invite" size="large">
            发送邀请
          </a-button>
        </a-form-item>
      </a-form>
    </a-card>

    <!-- 已发邀请列表 -->
    <a-card title="已发邀请" class="management-card">
      <a-list
        :data-source="sentInvitations"
        :loading="loading.invitations"
        :locale="{ emptyText: '暂无邀请记录' }"
        size="small"
      >
        <template #renderItem="{ item }">
          <a-list-item>
            <a-list-item-meta>
              <template #title>
                <div class="invitation-header">
                  <span>{{ item.username }}</span>
                  <a-tag :color="getInvitationStatusColor(item.status)" size="small">
                    {{ getInvitationStatusText(item.status) }}
                  </a-tag>
                </div>
              </template>

              <template #description>
                <div class="invitation-info">
                  <div>邀请时间: {{ formatDate(item.created_at) }}</div>
                  <div v-if="item.message">消息: {{ item.message }}</div>
                  <div v-if="item.status !== 'pending'">
                    处理时间: {{ formatDate(item.responded_at) }}
                  </div>
                </div>
              </template>
            </a-list-item-meta>
          </a-list-item>
        </template>
      </a-list>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { DownOutlined } from '@ant-design/icons-vue'
import { useTeamStore } from '@/shared/stores/team'
import type {
  TeamDetailResponse,
  TeamMember,
  JoinApplication,
  TeamInvitation,
  TeamMemberRole,
  ApplicationStatus,
  InvitationStatus,
} from '@/shared/types/team'

interface Props {
  team: TeamDetailResponse
}

const props = defineProps<Props>()
const teamStore = useTeamStore()

// 加载状态
const loading = reactive({
  recruitment: false,
  applications: false,
  members: false,
  invite: false,
  invitations: false,
  handleApplication: false,
  removeMember: false,
})

// 招募状态表单
const recruitmentForm = reactive({
  status: props.team.recruitment_status,
  note: props.team.recruitment_note || '',
})

// 邀请表单
const inviteForm = reactive({
  username: '',
  message: '',
})

// 玩家搜索选项
const playerSearchOptions = ref<
  Array<{
    value: string
    username: string
    avatar?: string
  }>
>([])

// 申请列表
const applications = ref<JoinApplication[]>([])
const sentInvitations = ref<TeamInvitation[]>([])

// 计算属性
const pendingApplications = computed(() =>
  applications.value.filter(app => app.status === 'pending')
)

// 成员表格列定义
const memberColumns = [
  {
    title: '头像',
    key: 'avatar',
    width: 60,
  },
  {
    title: '用户名',
    dataIndex: 'username',
    key: 'username',
  },
  {
    title: '角色',
    key: 'role',
    width: 80,
  },
  {
    title: '位置',
    dataIndex: 'position',
    key: 'position',
  },
  {
    title: '加入时间',
    key: 'joined_at',
    width: 120,
  },
  {
    title: '操作',
    key: 'actions',
    width: 150,
  },
]

// 权限检查
const canManageMember = (member: TeamMember): boolean => {
  return member.role !== 'owner' && member.user_id !== getCurrentUserId()
}

const canChangeRole = (member: TeamMember): boolean => {
  return teamStore.isTeamOwner && member.role !== 'owner'
}

const getCurrentUserId = (): string => {
  // TODO: 从auth store获取当前用户ID
  return ''
}

// 更新招募状态
const updateRecruitmentStatus = async () => {
  try {
    loading.recruitment = true
    await teamStore.updateRecruitmentStatus(
      props.team.id,
      recruitmentForm.status,
      recruitmentForm.note
    )
    message.success('招募状态已更新')
  } catch (error: any) {
    message.error(error.message || '更新失败')
  } finally {
    loading.recruitment = false
  }
}

// 处理入队申请
const handleApplication = async (applicationId: string, action: 'approve' | 'reject') => {
  try {
    loading.handleApplication = true
    await teamStore.handleJoinApplication(props.team.id, applicationId, action)
    message.success(action === 'approve' ? '已批准申请' : '已拒绝申请')
    await loadApplications()
  } catch (error: any) {
    message.error(error.message || '操作失败')
  } finally {
    loading.handleApplication = false
  }
}

// 搜索玩家
const searchPlayers = async (keyword: string) => {
  if (!keyword.trim()) {
    playerSearchOptions.value = []
    return
  }

  try {
    const players = await teamStore.searchPlayers(keyword)
    playerSearchOptions.value = players.map(player => ({
      value: player.username,
      username: player.username,
      avatar: player.avatar,
    }))
  } catch (error) {
    console.error('搜索玩家失败:', error)
  }
}

// 选择玩家
const selectPlayer = (username: string) => {
  inviteForm.username = username
}

// 发送邀请
const sendInvitation = async () => {
  try {
    loading.invite = true
    await teamStore.invitePlayer(props.team.id, inviteForm.username, inviteForm.message)
    message.success('邀请已发送')
    inviteForm.username = ''
    inviteForm.message = ''
    playerSearchOptions.value = []
    await loadInvitations()
  } catch (error: any) {
    message.error(error.message || '发送邀请失败')
  } finally {
    loading.invite = false
  }
}

// 菜单点击处理
const handleMenuClick = (event: { key: string }, member: TeamMember) => {
  handleRoleChange(member, event.key)
}

// 角色变更
const handleRoleChange = async (member: TeamMember, newRole: string) => {
  try {
    if (newRole === 'captain') {
      await teamStore.appointCaptain(props.team.id, member.user_id)
      message.success('已任命队长')
    } else if (newRole === 'member') {
      await teamStore.dismissCaptain(props.team.id, member.user_id)
      message.success('已罢免队长')
    }
  } catch (error: any) {
    message.error(error.message || '操作失败')
  }
}

// 移除成员
const removeMember = async (member: TeamMember) => {
  try {
    loading.removeMember = true
    await teamStore.removeMember(props.team.id, member.user_id)
    message.success('已移除成员')
  } catch (error: any) {
    message.error(error.message || '移除失败')
  } finally {
    loading.removeMember = false
  }
}

// 加载申请列表
const loadApplications = async () => {
  try {
    loading.applications = true
    const apps = await teamStore.fetchTeamApplications(props.team.id)
    applications.value = apps
  } catch (error) {
    console.error('加载申请失败:', error)
  } finally {
    loading.applications = false
  }
}

// 加载邀请列表
const loadInvitations = async () => {
  try {
    loading.invitations = true
    const invitations = await teamStore.fetchTeamInvitations(props.team.id)
    sentInvitations.value = invitations
  } catch (error) {
    console.error('加载邀请失败:', error)
  } finally {
    loading.invitations = false
  }
}

// 工具方法
const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleDateString('zh-CN')
}

const getApplicationStatusText = (status: ApplicationStatus): string => {
  const statusMap = {
    pending: '待处理',
    approved: '已批准',
    rejected: '已拒绝',
  }
  return statusMap[status] || status
}

const getInvitationStatusText = (status: InvitationStatus): string => {
  const statusMap = {
    pending: '待回应',
    accepted: '已接受',
    declined: '已拒绝',
    expired: '已过期',
  }
  return statusMap[status] || status
}

const getInvitationStatusColor = (status: InvitationStatus): string => {
  const colorMap = {
    pending: 'blue',
    accepted: 'green',
    declined: 'red',
    expired: 'gray',
  }
  return colorMap[status] || 'default'
}

const getRoleText = (role: TeamMemberRole): string => {
  const roleMap = {
    owner: '所有者',
    captain: '队长',
    member: '队员',
  }
  return roleMap[role] || role
}

const getRoleColor = (role: TeamMemberRole): string => {
  const colorMap = {
    owner: 'red',
    captain: 'orange',
    member: 'blue',
  }
  return colorMap[role] || 'default'
}

// 组件挂载时加载数据
onMounted(async () => {
  await Promise.all([loadApplications(), loadInvitations()])
})
</script>

<style scoped>
.team-management-panel {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.management-card {
  width: 100%;
}

.card-title-with-badge {
  display: flex;
  align-items: center;
  gap: 8px;
}

.application-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.applicant-name {
  font-weight: 500;
}

.application-time {
  color: #666;
  font-size: 12px;
}

.application-message {
  color: #666;
  font-size: 13px;
  line-height: 1.4;
  margin-top: 4px;
}

.search-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.invitation-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.invitation-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
  color: #666;
}

:deep(.ant-table-tbody > tr > td) {
  padding: 8px;
}

:deep(.ant-list-item-meta-title) {
  margin-bottom: 4px;
}

:deep(.ant-list-item-meta-description) {
  font-size: 12px;
}

@media (max-width: 768px) {
  .application-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .invitation-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
}
</style>
