/**
 * 战队状态管理Store
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  Team,
  TeamDetailResponse,
  TeamListResponse,
  TeamApplication,
  CreateTeamForm,
  TeamSearchFilters,
  JoinApplication,
  TeamInvitation,
} from '@/shared/types/team'
import TeamsApi from '@/shared/api/teams'

export const useTeamStore = defineStore('team', () => {
  // 状态
  const teams = ref<Team[]>([])
  const currentTeam = ref<TeamDetailResponse | null>(null)
  const userTeamApplication = ref<TeamApplication | null>(null)
  const userInvitations = ref<TeamInvitation[]>([])
  const teamApplications = ref<JoinApplication[]>([])
  const teamInvitations = ref<TeamInvitation[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // 分页信息
  const pagination = ref({
    total: 0,
    page: 1,
    limit: 10,
    hasNext: false,
    hasPrev: false,
  })

  // 计算属性
  const hasUserTeam = computed(() => !!currentTeam.value)
  const isTeamOwner = computed(() => {
    if (!currentTeam.value) return false
    return currentTeam.value.owner.user_id === getCurrentUserId()
  })
  const isTeamCaptain = computed(() => {
    if (!currentTeam.value) return false
    return currentTeam.value.captain?.user_id === getCurrentUserId()
  })
  const canManageTeam = computed(() => isTeamOwner.value || isTeamCaptain.value)
  const pendingApplicationCount = computed(
    () => teamApplications.value.filter(app => app.status === 'pending').length
  )

  // 辅助方法：获取当前用户ID（应从auth store获取）
  function getCurrentUserId(): string {
    // TODO: 从auth store获取当前用户ID
    return ''
  }

  // Actions

  /**
   * 获取战队列表
   */
  async function fetchTeams(filters?: TeamSearchFilters) {
    loading.value = true
    error.value = null

    try {
      const response = await TeamsApi.getTeams(filters)
      teams.value = response.teams
      pagination.value = {
        total: response.total,
        page: response.page,
        limit: response.limit,
        hasNext: response.has_next,
        hasPrev: response.has_prev,
      }
    } catch (err: any) {
      error.value = err.message || '获取战队列表失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取战队详情
   */
  async function fetchTeamDetail(teamId: string) {
    loading.value = true
    error.value = null

    try {
      const team = await TeamsApi.getTeamDetail(teamId)
      currentTeam.value = team
      return team
    } catch (err: any) {
      error.value = err.message || '获取战队详情失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 创建战队申请
   */
  async function createTeamApplication(formData: CreateTeamForm) {
    loading.value = true
    error.value = null

    try {
      const application = await TeamsApi.createTeamApplication(formData)
      userTeamApplication.value = application
      return application
    } catch (err: any) {
      error.value = err.message || '提交战队申请失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取用户战队申请状态
   */
  async function fetchUserTeamApplication() {
    try {
      const application = await TeamsApi.getUserTeamApplication()
      userTeamApplication.value = application
      return application
    } catch (err: any) {
      error.value = err.message || '获取申请状态失败'
      throw err
    }
  }

  /**
   * 撤销战队创建申请
   */
  async function cancelTeamApplication() {
    loading.value = true
    error.value = null

    try {
      await TeamsApi.cancelTeamApplication()
      userTeamApplication.value = null
    } catch (err: any) {
      error.value = err.message || '撤销申请失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 申请加入战队
   */
  async function applyToJoinTeam(teamId: string, message?: string) {
    loading.value = true
    error.value = null

    try {
      const application = await TeamsApi.applyToJoinTeam(teamId, message)
      return application
    } catch (err: any) {
      error.value = err.message || '申请加入失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取战队的入队申请列表
   */
  async function fetchTeamApplications(teamId: string) {
    loading.value = true
    error.value = null

    try {
      const applications = await TeamsApi.getTeamApplications(teamId)
      teamApplications.value = applications
      return applications
    } catch (err: any) {
      error.value = err.message || '获取申请列表失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 处理入队申请
   */
  async function handleJoinApplication(
    teamId: string,
    applicationId: string,
    action: 'approve' | 'reject'
  ) {
    loading.value = true
    error.value = null

    try {
      await TeamsApi.handleJoinApplication(teamId, applicationId, action)
      // 重新获取申请列表
      await fetchTeamApplications(teamId)
      // 如果是当前战队，重新获取详情
      if (currentTeam.value?.id === teamId) {
        await fetchTeamDetail(teamId)
      }
    } catch (err: any) {
      error.value = err.message || '处理申请失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 邀请玩家
   */
  async function invitePlayer(teamId: string, username: string, message?: string) {
    loading.value = true
    error.value = null

    try {
      const invitation = await TeamsApi.invitePlayer(teamId, username, message)
      return invitation
    } catch (err: any) {
      error.value = err.message || '发送邀请失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取用户收到的邀请
   */
  async function fetchUserInvitations() {
    try {
      const invitations = await TeamsApi.getUserInvitations()
      userInvitations.value = invitations
      return invitations
    } catch (err: any) {
      error.value = err.message || '获取邀请列表失败'
      throw err
    }
  }

  /**
   * 处理邀请
   */
  async function handleInvitation(invitationId: string, action: 'accept' | 'decline') {
    loading.value = true
    error.value = null

    try {
      await TeamsApi.handleInvitation(invitationId, action)
      // 重新获取邀请列表
      await fetchUserInvitations()
    } catch (err: any) {
      error.value = err.message || '处理邀请失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 移除队员
   */
  async function removeMember(teamId: string, userId: string) {
    loading.value = true
    error.value = null

    try {
      await TeamsApi.removeMember(teamId, userId)
      // 重新获取战队详情
      await fetchTeamDetail(teamId)
    } catch (err: any) {
      error.value = err.message || '移除队员失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 任命队长
   */
  async function appointCaptain(teamId: string, userId: string) {
    loading.value = true
    error.value = null

    try {
      await TeamsApi.appointCaptain(teamId, userId)
      // 重新获取战队详情
      await fetchTeamDetail(teamId)
    } catch (err: any) {
      error.value = err.message || '任命队长失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 罢免队长
   */
  async function dismissCaptain(teamId: string, userId: string) {
    loading.value = true
    error.value = null

    try {
      await TeamsApi.dismissCaptain(teamId, userId)
      // 重新获取战队详情
      await fetchTeamDetail(teamId)
    } catch (err: any) {
      error.value = err.message || '罢免队长失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 更新招募状态
   */
  async function updateRecruitmentStatus(teamId: string, status: 'open' | 'closed', note?: string) {
    loading.value = true
    error.value = null

    try {
      await TeamsApi.updateRecruitmentStatus(teamId, status, note)
      // 重新获取战队详情
      await fetchTeamDetail(teamId)
    } catch (err: any) {
      error.value = err.message || '更新招募状态失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 退出战队
   */
  async function leaveTeam(teamId: string) {
    loading.value = true
    error.value = null

    try {
      await TeamsApi.leaveTeam(teamId)
      // 清空当前战队信息
      currentTeam.value = null
    } catch (err: any) {
      error.value = err.message || '退出战队失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 检查是否可以创建战队
   */
  async function checkCanCreateTeam() {
    try {
      const result = await TeamsApi.canCreateTeam()
      return result
    } catch (err: any) {
      error.value = err.message || '检查创建权限失败'
      throw err
    }
  }

  /**
   * 检查是否可以加入指定战队
   */
  async function checkCanJoinTeam(teamId: string) {
    try {
      const result = await TeamsApi.canJoinTeam(teamId)
      return result
    } catch (err: any) {
      error.value = err.message || '检查加入权限失败'
      throw err
    }
  }

  /**
   * 清空错误信息
   */
  function clearError() {
    error.value = null
  }

  /**
   * 获取战队发出的邀请列表
   */
  async function fetchTeamInvitations(teamId: string) {
    loading.value = true
    error.value = null

    try {
      const invitations = await TeamsApi.getTeamInvitations(teamId)
      teamInvitations.value = invitations
      return invitations
    } catch (err: any) {
      error.value = err.message || '获取邀请列表失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 搜索玩家
   */
  async function searchPlayers(keyword: string) {
    try {
      const players = await TeamsApi.searchPlayers(keyword)
      return players
    } catch (err: any) {
      error.value = err.message || '搜索玩家失败'
      throw err
    }
  }

  /**
   * 重置状态
   */
  function resetState() {
    teams.value = []
    currentTeam.value = null
    userTeamApplication.value = null
    userInvitations.value = []
    teamApplications.value = []
    teamInvitations.value = []
    loading.value = false
    error.value = null
    pagination.value = {
      total: 0,
      page: 1,
      limit: 10,
      hasNext: false,
      hasPrev: false,
    }
  }

  return {
    // 状态
    teams,
    currentTeam,
    userTeamApplication,
    userInvitations,
    teamApplications,
    teamInvitations,
    loading,
    error,
    pagination,

    // 计算属性
    hasUserTeam,
    isTeamOwner,
    isTeamCaptain,
    canManageTeam,
    pendingApplicationCount,

    // Actions
    fetchTeams,
    fetchTeamDetail,
    createTeamApplication,
    fetchUserTeamApplication,
    cancelTeamApplication,
    applyToJoinTeam,
    fetchTeamApplications,
    handleJoinApplication,
    invitePlayer,
    fetchUserInvitations,
    fetchTeamInvitations,
    handleInvitation,
    removeMember,
    appointCaptain,
    dismissCaptain,
    updateRecruitmentStatus,
    leaveTeam,
    checkCanCreateTeam,
    checkCanJoinTeam,
    searchPlayers,
    clearError,
    resetState,
  }
})
