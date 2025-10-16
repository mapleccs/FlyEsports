/**
 * 赛事类型定义
 */

export type TournamentType = 'team_based' | 'solo_based'

export type TournamentFormat =
  | 'single_elimination'
  | 'double_elimination'
  | 'round_robin'
  | 'swiss'
  | 'custom'

export type TournamentStatus =
  | 'draft'
  | 'upcoming'
  | 'registration_open'
  | 'registration_closed'
  | 'ongoing'
  | 'completed'
  | 'cancelled'

export type MatchStatus =
  | 'pending'
  | 'scheduled'
  | 'waiting_for_checkin'
  | 'checkin_open'
  | 'checking_in'
  | 'ready'
  | 'in_progress'
  | 'completed'
  | 'cancelled'

export type CheckInStatus = 'not_checked_in' | 'checked_in' | 'no_show'

export interface TournamentRules {
  format: TournamentFormat
  max_participants: number
  min_rank?: string
  max_rank?: string
  team_size?: number
}

export interface TournamentSchedule {
  registration_start: string
  registration_end: string
  tournament_start: string
  tournament_end: string
}

export interface Tournament {
  id: string
  region_id: number // 修正为数字类型匹配后端
  name: string
  description?: string
  tournament_type: TournamentType
  status: TournamentStatus
  format: TournamentFormat
  max_participants: number
  min_rank?: string
  max_rank?: string
  team_size?: number

  // 时间字段 - 扁平化结构匹配后端
  registration_start: string
  registration_end: string
  tournament_start: string
  tournament_end: string

  logo_url?: string
  banner_url?: string
  created_by: number
  created_at: string
  updated_at: string

  // 统计字段
  registered_count?: number
  registration_count?: number
  confirmed_count?: number
  team_registration_count?: number
  player_registration_count?: number

  // 计算字段
  is_registration_open?: boolean
  can_register?: boolean
  user_registered?: boolean
}

export interface TournamentCreateRequest {
  region_id: number // 修正为数字类型匹配后端
  name: string
  description?: string
  tournament_type: TournamentType
  format: TournamentFormat
  max_participants: number
  registration_start: string
  registration_end: string
  tournament_start: string
  tournament_end: string
  logo_url?: string
  banner_url?: string
  min_rank?: string
  max_rank?: string
  team_size?: number
  status?: TournamentStatus
}

export interface TournamentListParams {
  page?: number
  limit?: number
  region_id?: number // 修正为数字类型匹配后端
  status?: TournamentStatus
  tournament_type?: TournamentType
  search?: string
}

export interface TournamentListResponse {
  tournaments: Tournament[]
  total: number
  page: number
  limit: number
  has_next: boolean
  has_prev: boolean
}

export interface TournamentRegistration {
  id: string
  tournament_id: string
  participant_id: string
  participant_type: 'team' | 'player'
  registered_at: string
  status: 'pending' | 'approved' | 'rejected' | 'cancelled'
  created_at: string

  // 参与者信息（前端展示用）
  participant_name?: string
  participant_logo?: string

  // 关联的详细信息
  team?: {
    id: string
    name: string
    logo_url?: string
    current_size?: number
    region?: {
      id: number
      name: string
    }
  }
  player?: {
    id: string
    username: string
    player_name?: string
    current_rank?: string
    region?: {
      id: number
      name: string
    }
  }
}

export interface TournamentRegistrationRequest {
  participant_type: 'team' | 'player'
  participant_id?: string // 可选，如果未提供则使用当前用户/用户的队伍
}

export interface Match {
  id: string
  tournament_id: string
  round_number: number
  match_number?: string
  blue_side_id?: string
  red_side_id?: string
  status: MatchStatus
  room_id?: string
  scheduled_time?: string
  started_at?: string
  completed_at?: string
  created_at?: string
  winner_id?: string
  check_ins: Record<string, CheckInStatus>

  // 前端展示用的计算字段
  blue_side_name?: string
  red_side_name?: string
  tournament_name?: string
  winner_name?: string
  all_checked_in?: boolean
}

export interface MatchCheckInRequest {
  participant_id: string
}

// WebSocket消息类型定义
export interface WebSocketMessage {
  type: string
  data: any
  timestamp?: string
}

export interface MatchStatusMessage extends WebSocketMessage {
  type: 'match_status'
  data: {
    match_id: string
    status: MatchStatus
    check_ins: Record<string, CheckInStatus>
    all_checked_in: boolean
    participants: string[]
  }
}

export interface CheckInUpdateMessage extends WebSocketMessage {
  type: 'checkin_update'
  data: {
    match_id: string
    participant_id: string
    status: CheckInStatus
    all_checked_in: boolean
    timestamp: string
  }
}

export interface MatchStartedMessage extends WebSocketMessage {
  type: 'match_started'
  data: {
    match_id: string
    status: MatchStatus
    started_at: string
    timestamp: string
  }
}

export interface UserJoinedMessage extends WebSocketMessage {
  type: 'user_joined'
  data: {
    user_id: number
    username: string
    match_id: string
    timestamp: string
  }
}

export interface UserLeftMessage extends WebSocketMessage {
  type: 'user_left'
  data: {
    user_id: number
    username: string
    match_id: string
    timestamp: string
  }
}

// 组合所有WebSocket消息类型
export type TournamentWebSocketMessage =
  | MatchStatusMessage
  | CheckInUpdateMessage
  | MatchStartedMessage
  | UserJoinedMessage
  | UserLeftMessage
