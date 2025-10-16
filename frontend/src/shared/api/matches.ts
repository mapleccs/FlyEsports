import { apiClient } from './client'

// 比赛相关API接口

/**
 * 获取比赛详情
 */
export const getMatchDetails = (matchId: string) => {
  return apiClient.get(`/matches/${matchId}`)
}

/**
 * 签到比赛
 */
export const checkInMatch = (matchId: string) => {
  return apiClient.post(`/matches/${matchId}/checkin`)
}

/**
 * 开启比赛签到
 */
export const openMatchCheckIn = (matchId: string) => {
  return apiClient.post(`/matches/${matchId}/open-checkin`)
}

/**
 * 开始比赛
 */
export const startMatch = (matchId: string) => {
  return apiClient.post(`/matches/${matchId}/start`)
}

/**
 * 设置比赛获胜者
 */
export const setMatchWinner = (matchId: string, winnerId: string) => {
  return apiClient.post(`/matches/${matchId}/winner`, {
    winner_id: winnerId
  })
}

/**
 * 取消比赛
 */
export const cancelMatch = (matchId: string, reason?: string) => {
  return apiClient.post(`/matches/${matchId}/cancel`, {
    reason: reason || '管理员取消比赛'
  })
}

// 指挥官投票相关API

/**
 * 为队伍成员投票选择指挥官
 * @param roomId 房间ID
 * @param teamSide 队伍方向 ('blue' | 'red')
 * @param candidateUserId 候选人用户ID
 */
export const voteForCommander = (roomId: string, teamSide: string, candidateUserId: number) => {
  return apiClient.post(`/lobby/rooms/${roomId}/vote-commander`, {
    team_side: teamSide,
    candidate_user_id: candidateUserId
  })
}

/**
 * 获取指挥官投票状态
 * @param roomId 房间ID
 * @param teamSide 队伍方向 ('blue' | 'red')
 */
export const getVotingStatus = (roomId: string, teamSide: string) => {
  return apiClient.get(`/lobby/rooms/${roomId}/voting-status?team_side=${teamSide}`)
}

/**
 * 强制完成指挥官投票（队长特权）
 * @param roomId 房间ID
 * @param teamSide 队伍方向 ('blue' | 'red')
 */
export const forceCompleteCommanderVoting = (roomId: string, teamSide: string) => {
  return apiClient.post(`/lobby/rooms/${roomId}/force-complete-voting`, {
    team_side: teamSide
  })
}

/**
 * 获取房间所有队伍的投票状态
 * @param roomId 房间ID
 */
export const getAllTeamsVotingStatus = (roomId: string) => {
  return apiClient.get(`/lobby/rooms/${roomId}/all-voting-status`)
}

/**
 * 重置指挥官投票（管理员功能）
 * @param roomId 房间ID
 * @param teamSide 队伍方向（可选，不传则重置所有队伍）
 */
export const resetCommanderVoting = (roomId: string, teamSide?: string) => {
  const params = teamSide ? { team_side: teamSide } : {}
  return apiClient.post(`/lobby/rooms/${roomId}/reset-voting`, params)
}

/**
 * 开始BP阶段（所有队伍都完成指挥官选择后）
 * @param roomId 房间ID
 */
export const startBPPhase = (roomId: string) => {
  return apiClient.post(`/lobby/rooms/${roomId}/start-bp`)
}

// 房间状态相关

/**
 * 获取房间详细信息
 */
export const getRoomDetails = (roomId: string) => {
  return apiClient.get(`/lobby/rooms/${roomId}`)
}

/**
 * 更新房间状态
 */
export const updateRoomPhase = (roomId: string, phase: string) => {
  return apiClient.post(`/lobby/rooms/${roomId}/update-phase`, {
    phase: phase
  })
}