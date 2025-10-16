import { apiClient } from './client'
import type {
  Tournament,
  TournamentCreateRequest,
  TournamentListParams,
  TournamentListResponse,
  TournamentRegistration,
  TournamentRegistrationRequest,
  Match,
  MatchCheckInRequest,
} from '@/shared/types/tournament'

export const tournamentApi = {
  /**
   * 获取赛事列表
   */
  async getTournaments(params?: TournamentListParams): Promise<TournamentListResponse> {
    const response = await apiClient.get('/tournaments/', { params })
    return response.data
  },

  /**
   * 获取赛事详情
   */
  async getTournament(id: string): Promise<Tournament> {
    const response = await apiClient.get(`/tournaments/${id}`)
    return response.data
  },

  /**
   * 创建赛事（管理员权限）
   */
  async createTournament(data: TournamentCreateRequest): Promise<Tournament> {
    const response = await apiClient.post('/tournaments/', data)
    return response.data
  },

  /**
   * 更新赛事（管理员权限）
   */
  async updateTournament(id: string, data: Partial<TournamentCreateRequest>): Promise<Tournament> {
    const response = await apiClient.put(`/tournaments/${id}`, data)
    return response.data
  },

  /**
   * 删除赛事（管理员权限）
   */
  async deleteTournament(id: string): Promise<void> {
    await apiClient.delete(`/tournaments/${id}`)
  },

  /**
   * 发布赛事（管理员权限）
   */
  async publishTournament(id: string): Promise<Tournament> {
    const response = await apiClient.post(`/tournaments/${id}/publish`)
    return response.data
  },

  /**
   * 取消赛事（管理员权限）
   */
  async cancelTournament(id: string): Promise<Tournament> {
    const response = await apiClient.post(`/tournaments/${id}/cancel`)
    return response.data
  },

  /**
   * 报名参赛
   */
  async registerForTournament(
    tournamentId: string,
    data: TournamentRegistrationRequest
  ): Promise<TournamentRegistration> {
    const response = await apiClient.post(`/tournaments/${tournamentId}/register`, data)
    return response.data
  },

  /**
   * 取消报名
   */
  async unregisterFromTournament(tournamentId: string): Promise<void> {
    await apiClient.delete(`/tournaments/${tournamentId}/register`)
  },

  /**
   * 获取赛事报名列表（管理员权限）
   */
  async getTournamentRegistrations(tournamentId: string): Promise<TournamentRegistration[]> {
    const response = await apiClient.get(`/tournaments/${tournamentId}/registrations`)
    // 后端返回格式是 {registrations: [...]}
    return response.data.registrations || []
  },

  /**
   * 管理员指定参赛（管理员权限）
   */
  async directRegisterParticipant(
    tournamentId: string,
    data: TournamentRegistrationRequest
  ): Promise<TournamentRegistration> {
    const response = await apiClient.post(`/tournaments/${tournamentId}/direct-register`, data)
    return response.data
  },

  /**
   * 生成赛程对阵表（管理员权限）
   */
  async generateBracket(tournamentId: string, autoAssignByes: boolean = true): Promise<{ matches: Match[], total: number }> {
    const response = await apiClient.post(`/tournaments/${tournamentId}/generate-bracket?auto_assign_byes=${autoAssignByes}`)
    return response.data
  },

  /**
   * 获取赛事比赛列表
   */
  async getTournamentMatches(tournamentId: string, roundNumber?: number, status?: string): Promise<{ matches: Match[], total: number }> {
    const params = new URLSearchParams()
    if (roundNumber) params.append('round_number', roundNumber.toString())
    if (status) params.append('status', status)

    const response = await apiClient.get(`/tournaments/${tournamentId}/matches?${params.toString()}`)
    return response.data
  },

  /**
   * 获取全局比赛列表
   */
  async getAllMatches(status?: string, limit: number = 50, offset: number = 0): Promise<{ matches: Match[], total: number }> {
    const params = new URLSearchParams()
    if (status) params.append('status', status)
    params.append('limit', limit.toString())
    params.append('offset', offset.toString())

    const response = await apiClient.get(`/matches/?${params.toString()}`)
    return response.data
  },

  /**
   * 获取比赛详情
   */
  async getMatch(matchId: string): Promise<Match> {
    const response = await apiClient.get(`/tournaments/matches/${matchId}`)
    return response.data
  },

  /**
   * 开放比赛签到（管理员权限）
   */
  async openMatchCheckIn(matchId: string): Promise<Match> {
    const response = await apiClient.post(`/tournaments/matches/${matchId}/open-checkin`)
    return response.data
  },

  /**
   * 参赛者签到
   */
  async checkInForMatch(matchId: string, data: MatchCheckInRequest): Promise<any> {
    const response = await apiClient.post(`/tournaments/matches/${matchId}/checkin`, data)
    return response.data
  },

  /**
   * 开始比赛（管理员权限）
   */
  async startMatch(matchId: string): Promise<Match> {
    const response = await apiClient.post(`/tournaments/matches/${matchId}/start`)
    return response.data
  },

  /**
   * 完成比赛并设置获胜者（管理员权限）
   */
  async completeMatch(matchId: string, winnerId: string): Promise<Match> {
    const response = await apiClient.post(`/tournaments/matches/${matchId}/complete`, { winner_id: winnerId })
    return response.data
  },

  /**
   * 管理员强制全员签到（管理员权限）
   */
  async forceCheckinAll(matchId: string): Promise<Match> {
    const response = await apiClient.post(`/tournaments/matches/${matchId}/force-checkin-all`)
    return response.data
  },

  /**
   * 推进获胜者到下一轮（管理员权限）
   */
  async advanceWinner(matchId: string, winnerId: string): Promise<Match> {
    const response = await apiClient.post(`/tournaments/matches/${matchId}/advance-winner?winner_id=${winnerId}`)
    return response.data
  },

  /**
   * 更新比赛信息（管理员权限）
   */
  async updateMatch(tournamentId: string, matchId: string, data: {
    blue_side_id?: string
    red_side_id?: string
    scheduled_time?: string
    round_number?: number
  }): Promise<Match> {
    const response = await apiClient.put(`/tournaments/${tournamentId}/matches/${matchId}`, data)
    return response.data
  },

  /**
   * 创建新比赛（管理员权限）
   */
  async createMatch(tournamentId: string, data: {
    tournament_id: string
    blue_side_id: string
    red_side_id: string
    round_number: number
    scheduled_time?: string
  }): Promise<Match> {
    const response = await apiClient.post(`/tournaments/${tournamentId}/matches`, data)
    return response.data
  },

  /**
   * 确认单个报名（管理员权限）
   */
  async confirmRegistration(tournamentId: string, registrationId: string): Promise<TournamentRegistration> {
    const response = await apiClient.patch(`/tournaments/${tournamentId}/registrations/${registrationId}/confirm`)
    return response.data
  },

  /**
   * 批量确认报名（管理员权限）
   */
  async confirmRegistrationsBatch(tournamentId: string, registrationIds: string[]): Promise<{
    confirmed_count: number
    failed_count: number
    errors?: string[]
  }> {
    const response = await apiClient.post(`/tournaments/${tournamentId}/registrations/confirm-batch`, {
      registration_ids: registrationIds
    })
    return response.data
  },

  /**
   * 拒绝单个报名（管理员权限）
   */
  async rejectRegistration(tournamentId: string, registrationId: string, reason?: string): Promise<TournamentRegistration> {
    const response = await apiClient.patch(`/tournaments/${tournamentId}/registrations/${registrationId}/reject`, {
      reason
    })
    return response.data
  },

  /**
   * 删除比赛（管理员权限）
   */
  async deleteMatch(tournamentId: string, matchId: string): Promise<void> {
    await apiClient.delete(`/tournaments/${tournamentId}/matches/${matchId}`)
  },
}
