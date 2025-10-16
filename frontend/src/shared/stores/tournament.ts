import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { tournamentApi } from '@/shared/api/tournaments'
import { apiClient } from '@/shared/api/client'
import type {
  Tournament,
  TournamentListParams,
  TournamentCreateRequest,
  TournamentRegistration,
  Match,
  TournamentStatus,
  TournamentType,
} from '@/shared/types/tournament'
import { message } from 'ant-design-vue'
import { useAuthStore } from '@/shared/stores/auth'
export const useTournamentStore = defineStore('tournament', () => {
  // State
  const tournaments = ref<Tournament[]>([])
  const currentTournament = ref<Tournament | null>(null)
  const registrations = ref<TournamentRegistration[]>([])
  const matches = ref<Match[]>([])
  const currentMatch = ref<Match | null>(null)
  const loading = ref(false)
  const listLoading = ref(false)
  const registrationLoading = ref(false)
  const getTournamentRegistrationCount = (tournament: Tournament | null | undefined): number => {
    if (!tournament) return 0
    const baseCount = tournament.registration_count ?? tournament.registered_count ?? 0
    if (tournament.tournament_type === 'team_based') {
      return tournament.team_registration_count ?? baseCount
    }
    return tournament.player_registration_count ?? baseCount
  }
  const adjustTournamentRegistrationCount = (tournament: Tournament | null | undefined, delta: number) => {
    if (!tournament) return
    const baseRegistration = tournament.registration_count ?? tournament.registered_count ?? 0
    const nextRegistration = Math.max(0, baseRegistration + delta)
    tournament.registration_count = nextRegistration
    const currentRegistered = tournament.registered_count ?? baseRegistration
    tournament.registered_count = Math.max(0, currentRegistered + delta)
    if (tournament.tournament_type === 'team_based') {
      const baseTeam = tournament.team_registration_count ?? baseRegistration
      tournament.team_registration_count = Math.max(0, baseTeam + delta)
    } else {
      const basePlayer = tournament.player_registration_count ?? baseRegistration
      tournament.player_registration_count = Math.max(0, basePlayer + delta)
    }
  }
  // 分页状态
  const pagination = ref({
    current: 1,
    pageSize: 12,
    total: 0,
    showSizeChanger: true,
    showQuickJumper: true,
    pageSizeOptions: ['12', '24', '36', '48'],
  })
  // Getters
  const activeTournaments = computed(() => tournaments.value.filter(t => t.status !== 'cancelled'))
  const registrationOpenTournaments = computed(() =>
    tournaments.value.filter(t => t.status === 'registration_open')
  )
  const upcomingTournaments = computed(() => tournaments.value.filter(t => t.status === 'upcoming'))
  const inProgressTournaments = computed(() =>
    tournaments.value.filter(t => t.status === 'ongoing')
  )
  const completedTournaments = computed(() =>
    tournaments.value.filter(t => t.status === 'completed')
  )
  // Actions
  const fetchTournaments = async (params?: TournamentListParams) => {
    try {
      listLoading.value = true
      const requestParams = {
        page: pagination.value.current,
        limit: pagination.value.pageSize,
        ...params,
      }
      const response = await tournamentApi.getTournaments(requestParams)
      // Debug: 打印API返回的数据
      console.log('API返回的赛事数据', response.tournaments.map(t => ({
        id: t.id,
        name: t.name,
        user_registered: t.user_registered,
        user_registration_status: t.user_registration_status
      })))
      // 初始化每个赛事的 can_register 和 user_registered 字段
      tournaments.value = response.tournaments.map(tournament => ({
        ...tournament,
        can_register: tournament.can_register ?? (
          tournament.status === 'registration_open' &&
          new Date() <= new Date(tournament.registration_end) &&
          getTournamentRegistrationCount(tournament) < tournament.max_participants
        ),
        user_registered: tournament.user_registered ?? false
      }))
      pagination.value.total = response.total
      pagination.value.current = response.page
      return response
    } catch (error) {
      console.error('获取赛事列表失败:', error)
      message.error('获取赛事列表失败')
      throw error
    } finally {
      listLoading.value = false
    }
  }
  const fetchTournament = async (id: string) => {
    try {
      loading.value = true
      const tournament = await tournamentApi.getTournament(id)

      // 初始化 can_register 和 user_registered 字段
      currentTournament.value = {
        ...tournament,
        can_register: tournament.can_register ?? (
          tournament.status === 'registration_open' &&
          new Date() <= new Date(tournament.registration_end) &&
          getTournamentRegistrationCount(tournament) < tournament.max_participants
        ),
        user_registered: tournament.user_registered ?? false
      }
      return currentTournament.value
    } catch (error) {
      console.error('获取赛事详情失败:', error)
      message.error('获取赛事详情失败')
      throw error
    } finally {
      loading.value = false
    }
  }
  const createTournament = async (data: TournamentCreateRequest) => {
    try {
      loading.value = true
      const tournament = await tournamentApi.createTournament(data)
      // 添加到列表开头
      tournaments.value.unshift(tournament)
      currentTournament.value = tournament
      message.success('赛事创建成功')
      return tournament
    } catch (error) {
      console.error('创建赛事失败:', error)
      message.error('创建赛事失败')
      throw error
    } finally {
      loading.value = false
    }
  }
  const updateTournament = async (id: string, data: Partial<TournamentCreateRequest>) => {
    try {
      loading.value = true
      const tournament = await tournamentApi.updateTournament(id, data)
      // 更新列表中的赛事
      const index = tournaments.value.findIndex(t => t.id === id)
      if (index !== -1) {
        tournaments.value[index] = tournament
      }
      if (currentTournament.value?.id === id) {
        currentTournament.value = tournament
      }
      message.success('赛事更新成功')
      return tournament
    } catch (error) {
      console.error('更新赛事失败:', error)
      message.error('更新赛事失败')
      throw error
    } finally {
      loading.value = false
    }
  }
  const publishTournament = async (id: string) => {
    try {
      const tournament = await tournamentApi.publishTournament(id)
      // 更新列表中的赛事状态
      const index = tournaments.value.findIndex(t => t.id === id)
      if (index !== -1) {
        tournaments.value[index] = tournament
      }
      if (currentTournament.value?.id === id) {
        currentTournament.value = tournament
      }
      message.success('赛事发布成功')
      return tournament
    } catch (error) {
      console.error('发布赛事失败:', error)
      message.error('发布赛事失败')
      throw error
    }
  }
  const registerForTournament = async (
    tournamentId: string,
    participantType: 'team' | 'player'
  ) => {
    try {
      registrationLoading.value = true
      const authStore = useAuthStore()
      console.log('Auth store state:', {
        isAuthenticated: authStore.isAuthenticated,
        user: authStore.user,
        userId: authStore.user?.id
      })
      if (!authStore.user?.id) {
        throw new Error('用户未登录')
      }
      let participantId: string
      if (participantType === 'player') {
        // 对于个人赛，需要获取用户的PlayerProfile ID
        const { playersApi } = await import('@/shared/api/players')
        const playerProfiles = await playersApi.getMyProfiles()
        if (!playerProfiles || playerProfiles.length === 0) {
          throw new Error('您还没有创建选手资料，请先创建选手资料后再报名')
        }
        // 使用第一个选手资料的ID (后续可以让用户选择具体的资料)
        participantId = playerProfiles[0].profile_id
        console.log('Using player profile ID:', participantId)
      } else {
        // 对于战队赛，这里应该是战队ID，暂时使用用户ID的字符串形式作为占位符
        // TODO: 实现战队系统后，应该获取用户所在战队的ID
        participantId = authStore.user.id
        console.log('Using team ID (placeholder):', participantId)
      }
      const requestData = {
        participant_type: participantType,
        participant_id: participantId,
      }
      console.log('Registration request data:', requestData)
      const registration = await tournamentApi.registerForTournament(tournamentId, requestData)
      // 更新赛事的报名状态
      const tournament = tournaments.value.find(t => t.id === tournamentId)
      if (tournament) {
        adjustTournamentRegistrationCount(tournament, 1)
        tournament.can_register = false
        tournament.user_registered = true
      }
      if (currentTournament.value?.id === tournamentId) {
        adjustTournamentRegistrationCount(currentTournament.value, 1)
        currentTournament.value.can_register = false
        currentTournament.value.user_registered = true
      }
      message.success('报名成功')
      return registration
    } catch (error) {
      console.error('报名失败:', error)
      // 错误提示由 apiClient 拦截器统一处理，避免重复提示
      throw error
    } finally {
      registrationLoading.value = false
    }
  }
  const unregisterFromTournament = async (tournamentId: string) => {
    try {
      registrationLoading.value = true
      await tournamentApi.unregisterFromTournament(tournamentId)
      // 更新赛事的报名状态
      const tournament = tournaments.value.find(t => t.id === tournamentId)
      if (tournament) {
        adjustTournamentRegistrationCount(tournament, -1)
        tournament.can_register = Boolean(tournament.is_registration_open) &&
          getTournamentRegistrationCount(tournament) < tournament.max_participants
        tournament.user_registered = false
      }
      if (currentTournament.value?.id === tournamentId) {
        adjustTournamentRegistrationCount(currentTournament.value, -1)
        currentTournament.value.can_register = Boolean(currentTournament.value.is_registration_open) &&
          getTournamentRegistrationCount(currentTournament.value) < (currentTournament.value?.max_participants ?? Infinity)
        currentTournament.value.user_registered = false
      }
      message.success('取消报名成功')
    } catch (error) {
      console.error('取消报名失败:', error)
      // 错误提示由 apiClient 拦截器统一处理，避免重复提示
      throw error
    } finally {
      registrationLoading.value = false
    }
  }
  const fetchTournamentRegistrations = async (tournamentId: string) => {
    try {
      registrations.value = await tournamentApi.getTournamentRegistrations(tournamentId)
      return registrations.value
    } catch (error) {
      console.error('获取报名列表失败:', error)
      message.error('获取报名列表失败')
      throw error
    }
  }
  const fetchMatches = async (tournamentId: string, roundNumber?: number, status?: string) => {
    try {
      loading.value = true
      const response = await tournamentApi.getTournamentMatches(tournamentId, roundNumber, status)
      matches.value = response.matches
      return response
    } catch (error) {
      console.error('获取比赛列表失败:', error)
      message.error('获取比赛列表失败')
      throw error
    } finally {
      loading.value = false
    }
  }
  const generateBracket = async (tournamentId: string, autoAssignByes: boolean = true) => {
    try {
      loading.value = true
      const response = await tournamentApi.generateBracket(tournamentId, autoAssignByes)
      matches.value = response.matches

      message.success('赛程生成成功')
      return response
    } catch (error) {
      console.error('生成赛程失败:', error)
      message.error('生成赛程失败')
      throw error
    } finally {
      loading.value = false
    }
  }
  const fetchMatch = async (matchId: string) => {
    try {
      currentMatch.value = await tournamentApi.getMatch(matchId)
      return currentMatch.value
    } catch (error) {
      console.error('获取比赛详情失败:', error)
      message.error('获取比赛详情失败')
      throw error
    }
  }
  const updateTournamentStatus = async (id: string, status: TournamentStatus) => {
    try {
      // 使用新的PATCH状态更新端点
      const response = await apiClient.patch(`/tournaments/${id}/status`, { status })
      const tournament = response.data
      // 更新列表中的赛事状态
      const index = tournaments.value.findIndex(t => t.id === id)
      if (index !== -1) {
        tournaments.value[index] = tournament
      }
      if (currentTournament.value?.id === id) {
        currentTournament.value = tournament
      }
      message.success('赛事状态更新成功')
      return tournament
    } catch (error) {
      console.error('更新赛事状态失败', error)
      message.error('更新赛事状态失败')
      throw error
    }
  }
  const deleteTournament = async (id: string) => {
    try {
      await tournamentApi.deleteTournament(id)
      // 从列表中移除赛事
      const index = tournaments.value.findIndex(t => t.id === id)
      if (index !== -1) {
        tournaments.value.splice(index, 1)
        pagination.value.total = Math.max(0, pagination.value.total - 1)
      }
      if (currentTournament.value?.id === id) {
        currentTournament.value = null
      }
      message.success('赛事删除成功')
    } catch (error) {
      console.error('删除赛事失败:', error)
      message.error('删除赛事失败')
      throw error
    }
  }
  const duplicateTournament = async (id: string) => {
    try {
      loading.value = true
      // 先获取原赛事信息
      const originalTournament = await tournamentApi.getTournament(id)
      // 创建副本数据
      const duplicateData: TournamentCreateRequest = {
        name: `${originalTournament.name} - 副本`,
        description: originalTournament.description,
        tournament_type: originalTournament.tournament_type,
        region_id: originalTournament.region_id,
        registration_start: originalTournament.registration_start,
        registration_end: originalTournament.registration_end,
        tournament_start: originalTournament.tournament_start,
        tournament_end: originalTournament.tournament_end,
        format: originalTournament.format,
        max_participants: originalTournament.max_participants,
        team_size: originalTournament.team_size,
        min_rank: originalTournament.min_rank,
        max_rank: originalTournament.max_rank,
        logo_url: originalTournament.logo_url,
        banner_url: originalTournament.banner_url,
        status: 'draft', // 副本默认为草稿状态
      }
      const newTournament = await tournamentApi.createTournament(duplicateData)
      // 添加到列表开头
      tournaments.value.unshift(newTournament)
      pagination.value.total = pagination.value.total + 1
      message.success('赛事复制成功')
      return newTournament
    } catch (error) {
      console.error('复制赛事失败:', error)
      message.error('复制赛事失败')
      throw error
    } finally {
      loading.value = false
    }
  }
  const checkInForMatch = async (matchId: string, participantId?: string) => {
    try {
      const authStore = useAuthStore()
      const userId = authStore.user?.id

      // 获取比赛信息以确定用户应该签到的队伍
      const match = currentMatch.value || await fetchMatch(matchId)

      // 简化逻辑：假设奇数用户ID对应蓝方，偶数对应红方
      let teamId = participantId
      if (!teamId && userId) {
        // 根据用户ID确定队伍（这里使用简化逻辑，实际应该查询用户的队伍关系）
        const userIdNum = parseInt(userId)
        teamId = userIdNum % 2 === 1 ? match.blue_side_id : match.red_side_id
      }

      // 使用之前确定的teamId作为参赛者ID
      if (!teamId) {
        throw new Error('无法确定用户所属战队')
      }

      const checkInData = {
        participant_id: teamId,
      }

      const response = await tournamentApi.checkInForMatch(matchId, checkInData)
      // 重新获取比赛信息
      await fetchMatch(matchId)
      message.success('签到成功')
      return response
    } catch (error) {
      console.error('签到失败:', error)
      message.error('签到失败')
      throw error
    }
  }
  const openMatchCheckIn = async (matchId: string) => {
    try {
      const match = await tournamentApi.openMatchCheckIn(matchId)
      // 更新当前比赛信息
      if (currentMatch.value?.id === matchId) {
        currentMatch.value = match
      }
      // 更新比赛列表中的信息
      const index = matches.value.findIndex(m => m.id === matchId)
      if (index !== -1) {
        matches.value[index] = match
      }
      message.success('签到已开启')
      return match
    } catch (error) {
      console.error('开启签到失败', error)
      message.error('开启签到失败')
      throw error
    }
  }
  const forceCheckinAll = async (matchId: string) => {
    try {
      const match = await tournamentApi.forceCheckinAll(matchId)
      // 更新当前比赛信息
      if (currentMatch.value?.id === matchId) {
        currentMatch.value = match
      }
      // 更新比赛列表中的信息
      const index = matches.value.findIndex(m => m.id === matchId)
      if (index !== -1) {
        matches.value[index] = match
      }
      message.success('已强制全员签到')
      return match
    } catch (error) {
      console.error('强制全员签到失败:', error)
      message.error('强制全员签到失败')
      throw error
    }
  }
  const startMatch = async (matchId: string) => {
    try {
      const match = await tournamentApi.startMatch(matchId)
      // 更新当前比赛信息
      if (currentMatch.value?.id === matchId) {
        currentMatch.value = match
      }
      // 更新比赛列表中的信息
      const index = matches.value.findIndex(m => m.id === matchId)
      if (index !== -1) {
        matches.value[index] = match
      }
      message.success('比赛已开始')
      return match
    } catch (error) {
      console.error('开始比赛失败', error)
      message.error('开始比赛失败')
      throw error
    }
  }
  const advanceWinner = async (matchId: string, winnerId: string) => {
    try {
      const match = await tournamentApi.advanceWinner(matchId, winnerId)
      // 更新当前比赛信息
      if (currentMatch.value?.id === matchId) {
        currentMatch.value = match
      }
      // 更新比赛列表中的信息
      const index = matches.value.findIndex(m => m.id === matchId)
      if (index !== -1) {
        matches.value[index] = match
      }
      message.success('获胜者已推进到下一轮')
      return match
    } catch (error) {
      console.error('推进获胜者失败', error)
      message.error('推进获胜者失败')
      throw error
    }
  }
  const updateMatch = async (tournamentId: string, matchId: string, data: {
    blue_side_id?: string
    red_side_id?: string
    scheduled_time?: string
    round_number?: number
  }) => {
    try {
      loading.value = true
      const match = await tournamentApi.updateMatch(tournamentId, matchId, data)
      // 更新当前比赛信息
      if (currentMatch.value?.id === matchId) {
        currentMatch.value = match
      }
      // 更新比赛列表中的信息
      const index = matches.value.findIndex(m => m.id === matchId)
      if (index !== -1) {
        matches.value[index] = match
      }
      message.success('比赛信息更新成功')
      return match
    } catch (error) {
      console.error('更新比赛失败:', error)
      message.error('更新比赛失败')
      throw error
    } finally {
      loading.value = false
    }
  }
  const createMatch = async (tournamentId: string, data: {
    blue_side_id: string
    red_side_id: string
    round_number: number
    scheduled_time?: string
  }) => {
    try {
      loading.value = true
      const matchData = {
        tournament_id: tournamentId,
        ...data
      }
      const match = await tournamentApi.createMatch(tournamentId, matchData)
      // 添加到比赛列表
      matches.value.push(match)
      message.success('比赛创建成功')
      return match
    } catch (error) {
      console.error('创建比赛失败:', error)
      message.error('创建比赛失败')
      throw error
    } finally {
      loading.value = false
    }
  }
  // 重置状态
  const resetState = () => {
    tournaments.value = []
    currentTournament.value = null
    registrations.value = []
    matches.value = []
    currentMatch.value = null
    loading.value = false
    listLoading.value = false
    registrationLoading.value = false
    pagination.value.current = 1
    pagination.value.total = 0
  }
  const deleteMatch = async (tournamentId: string, matchId: string) => {
    try {
      loading.value = true
      await tournamentApi.deleteMatch(tournamentId, matchId)
      // 从比赛列表中移除
      const index = matches.value.findIndex(m => m.id === matchId)
      if (index !== -1) {
        matches.value.splice(index, 1)
      }
    } catch (error: any) {
      console.error('Delete match failed:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  // 过滤方法
  const filterTournamentsByStatus = (status: TournamentStatus) => {
    return tournaments.value.filter(t => t.status === status)
  }
  const filterTournamentsByType = (type: TournamentType) => {
    return tournaments.value.filter(t => t.tournament_type === type)
  }
  return {
    // State
    tournaments,
    currentTournament,
    registrations,
    matches,
    currentMatch,
    loading,
    listLoading,
    registrationLoading,
    pagination,
    // Getters
    activeTournaments,
    registrationOpenTournaments,
    upcomingTournaments,
    inProgressTournaments,
    completedTournaments,
    // Actions
    fetchTournaments,
    fetchTournament,
    createTournament,
    updateTournament,
    updateTournamentStatus,
    deleteTournament,
    duplicateTournament,
    publishTournament,
    registerForTournament,
    unregisterFromTournament,
    fetchTournamentRegistrations,
    fetchMatches,
    generateBracket,
    fetchMatch,
    checkInForMatch,
    openMatchCheckIn,
    startMatch,
    forceCheckinAll,
    advanceWinner,
    updateMatch,
    createMatch,
    deleteMatch,
    resetState,
    filterTournamentsByStatus,
    filterTournamentsByType,
  }
})