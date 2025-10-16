/**
 * 战队相关API服务
 */

import type {
  Team,
  TeamApplication,
  TeamDetailResponse,
  TeamListResponse,
  CreateTeamForm,
  TeamSearchFilters,
  JoinApplication,
  TeamInvitation,
  ApplicationStatus,
} from '@/shared/types/team'

import { api } from '@/shared/api/index'

/**
 * 战队API服务类
 */
export class TeamsApi {
  /**
   * 获取战队列表
   */
  static async getTeams(filters?: TeamSearchFilters): Promise<TeamListResponse> {
    const params = new URLSearchParams()

    if (filters?.region_id) params.append('region_id', filters.region_id)
    if (filters?.recruitment_status) params.append('recruitment_status', filters.recruitment_status)
    if (filters?.keyword) params.append('keyword', filters.keyword)
    if (filters?.page) params.append('page', filters.page.toString())
    if (filters?.limit) params.append('limit', filters.limit.toString())

    const response = await api.get(`/teams?${params.toString()}`)
    return response.data
  }

  /**
   * 获取战队详情
   */
  static async getTeamDetail(teamId: string): Promise<TeamDetailResponse> {
    const response = await api.get(`/teams/${teamId}`)
    return response.data
  }

  /**
   * 创建战队申请
   */
  static async createTeamApplication(formData: CreateTeamForm): Promise<TeamApplication> {
    const data = new FormData()
    data.append('name', formData.name)
    data.append('tag', formData.tag)
    if (formData.description) data.append('description', formData.description)
    if (formData.logo) data.append('logo', formData.logo)

    const response = await api.post('/teams/applications', data, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  }

  /**
   * 获取用户的战队申请状态
   */
  static async getUserTeamApplication(): Promise<TeamApplication | null> {
    try {
      const response = await api.get('/teams/applications/me')
      return response.data
    } catch (error: any) {
      if (error.response?.status === 404) {
        return null
      }
      throw error
    }
  }

  /**
   * 撤销战队创建申请
   */
  static async cancelTeamApplication(): Promise<void> {
    await api.delete('/teams/applications/me')
  }

  /**
   * 申请加入战队
   */
  static async applyToJoinTeam(teamId: string, message?: string): Promise<JoinApplication> {
    const response = await api.post(`/teams/${teamId}/applications`, {
      message: message || '',
    })
    return response.data
  }

  /**
   * 获取战队的入队申请列表（队长/所有者）
   */
  static async getTeamApplications(teamId: string): Promise<JoinApplication[]> {
    const response = await api.get(`/teams/${teamId}/applications`)
    return response.data
  }

  /**
   * 处理入队申请（队长/所有者）
   */
  static async handleJoinApplication(
    teamId: string,
    applicationId: string,
    action: 'approve' | 'reject'
  ): Promise<void> {
    await api.patch(`/teams/${teamId}/applications/${applicationId}`, {
      action,
    })
  }

  /**
   * 邀请玩家加入战队
   */
  static async invitePlayer(
    teamId: string,
    username: string,
    message?: string
  ): Promise<TeamInvitation> {
    const response = await api.post(`/teams/${teamId}/invitations`, {
      username,
      message: message || '',
    })
    return response.data
  }

  /**
   * 获取用户收到的邀请列表
   */
  static async getUserInvitations(): Promise<TeamInvitation[]> {
    const response = await api.get('/teams/invitations/me')
    return response.data
  }

  /**
   * 处理战队邀请
   */
  static async handleInvitation(invitationId: string, action: 'accept' | 'decline'): Promise<void> {
    await api.patch(`/teams/invitations/${invitationId}`, {
      action,
    })
  }

  /**
   * 获取战队发出的邀请列表（队长/所有者）
   */
  static async getTeamInvitations(teamId: string): Promise<TeamInvitation[]> {
    const response = await api.get(`/teams/${teamId}/invitations`)
    return response.data
  }

  /**
   * 移除战队成员（队长/所有者）
   */
  static async removeMember(teamId: string, userId: string): Promise<void> {
    await api.delete(`/teams/${teamId}/members/${userId}`)
  }

  /**
   * 任命队长（所有者）
   */
  static async appointCaptain(teamId: string, userId: string): Promise<void> {
    await api.patch(`/teams/${teamId}/members/${userId}/role`, {
      role: 'captain',
    })
  }

  /**
   * 罢免队长（所有者）
   */
  static async dismissCaptain(teamId: string, userId: string): Promise<void> {
    await api.patch(`/teams/${teamId}/members/${userId}/role`, {
      role: 'member',
    })
  }

  /**
   * 更新战队招募状态
   */
  static async updateRecruitmentStatus(
    teamId: string,
    status: 'open' | 'closed',
    note?: string
  ): Promise<void> {
    await api.patch(`/teams/${teamId}/recruitment`, {
      recruitment_status: status,
      recruitment_note: note || '',
    })
  }

  /**
   * 搜索玩家（用于邀请功能）
   */
  static async searchPlayers(keyword: string): Promise<
    Array<{
      id: string
      username: string
      avatar?: string
    }>
  > {
    const response = await api.get(`/players/search?keyword=${encodeURIComponent(keyword)}`)
    return response.data
  }

  /**
   * 检查用户是否可以创建战队
   */
  static async canCreateTeam(): Promise<{
    canCreate: boolean
    reason?: string
  }> {
    const response = await api.get('/teams/can-create')
    return response.data
  }

  /**
   * 检查用户是否可以申请加入指定战队
   */
  static async canJoinTeam(teamId: string): Promise<{
    canJoin: boolean
    reason?: string
  }> {
    const response = await api.get(`/teams/${teamId}/can-join`)
    return response.data
  }

  /**
   * 退出战队
   */
  static async leaveTeam(teamId: string): Promise<void> {
    await api.delete(`/teams/${teamId}/leave`)
  }
}

export default TeamsApi
