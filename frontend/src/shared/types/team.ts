/**
 * 战队相关类型定义
 */

/**
 * 战队状态枚举
 */
export enum TeamStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  PENDING = 'pending',
  DISBANDED = 'disbanded',
}

/**
 * 战队成员角色枚举
 */
export enum TeamMemberRole {
  OWNER = 'owner',
  CAPTAIN = 'captain',
  MEMBER = 'member',
}

/**
 * 招募状态枚举
 */
export enum RecruitmentStatus {
  OPEN = 'open',
  CLOSED = 'closed',
}

/**
 * 申请状态枚举
 */
export enum ApplicationStatus {
  PENDING = 'pending',
  APPROVED = 'approved',
  REJECTED = 'rejected',
}

/**
 * 邀请状态枚举
 */
export enum InvitationStatus {
  PENDING = 'pending',
  ACCEPTED = 'accepted',
  DECLINED = 'declined',
  EXPIRED = 'expired',
}

/**
 * 战队基础信息接口
 */
export interface Team {
  id: string
  name: string
  tag: string
  logo?: string
  description?: string
  region_id: string
  status: TeamStatus
  recruitment_status: RecruitmentStatus
  recruitment_note?: string
  created_at: string
  updated_at: string
  member_count: number
  win_rate?: number
}

/**
 * 战队成员接口
 */
export interface TeamMember {
  id: string
  team_id: string
  user_id: string
  username: string
  avatar?: string
  role: TeamMemberRole
  joined_at: string
  position?: string
}

/**
 * 战队创建申请接口
 */
export interface TeamApplication {
  id: string
  user_id: string
  username: string
  region_id: string
  team_name: string
  team_tag: string
  team_logo?: string
  team_description?: string
  status: ApplicationStatus
  rejection_reason?: string
  submitted_at: string
  reviewed_at?: string
  reviewed_by?: string
}

/**
 * 入队申请接口
 */
export interface JoinApplication {
  id: string
  team_id: string
  user_id: string
  username: string
  avatar?: string
  message?: string
  status: ApplicationStatus
  submitted_at: string
  reviewed_at?: string
  reviewed_by?: string
}

/**
 * 战队邀请接口
 */
export interface TeamInvitation {
  id: string
  team_id: string
  team_name: string
  user_id: string
  username: string
  invited_by: string
  invited_by_username: string
  status: InvitationStatus
  message?: string
  created_at: string
  expires_at: string
  responded_at?: string
}

/**
 * 创建战队表单数据接口
 */
export interface CreateTeamForm {
  name: string
  tag: string
  logo?: File
  description?: string
}

/**
 * 战队搜索筛选条件接口
 */
export interface TeamSearchFilters {
  region_id?: string
  recruitment_status?: RecruitmentStatus
  keyword?: string
  page?: number
  limit?: number
}

/**
 * 战队列表响应接口
 */
export interface TeamListResponse {
  teams: Team[]
  total: number
  page: number
  limit: number
  has_next: boolean
  has_prev: boolean
}

/**
 * 战队详情响应接口
 */
export interface TeamDetailResponse extends Team {
  members: TeamMember[]
  owner: TeamMember
  captain?: TeamMember
}
