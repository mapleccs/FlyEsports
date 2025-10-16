/**
 * BP房间管理API接口
 */

import { apiClient } from './client'

// 类型定义
export interface BPRoom {
  id: string
  name: string
  description?: string
  room_type: 'custom' | 'tournament' | 'ranked' | 'practice'
  status: 'waiting' | 'ready' | 'bp_active' | 'completed' | 'archived'
  creator_user_id: number
  team_a_id?: number
  team_b_id?: number
  bp_config: BPConfig
  participants: BPRoomParticipant[]
  creator?: User
  team_a?: Team
  team_b?: Team
  created_at: string
  started_at?: string
  completed_at?: string
}

export interface BPConfig {
  ban_count: number
  pick_count: number
  ban_time: number
  pick_time: number
  side_selection: 'random' | 'blue_first' | 'red_first'
  enable_swap: boolean
  enable_chat: boolean
}

export interface BPRoomParticipant {
  id: string
  room_id: string
  user_id: number
  team_side?: 'blue' | 'red'
  role: 'admin' | 'commander' | 'player' | 'observer'
  is_active: boolean
  is_ready: boolean
  joined_at: string
  left_at?: string
  user?: User
}

export interface User {
  id: number
  username: string
  email: string
  is_active: boolean
}

export interface Team {
  id: number
  name: string
  captain_id: number
}

// 请求类型
export interface CreateBPRoomRequest {
  name: string
  description?: string
  room_type?: 'custom' | 'tournament' | 'ranked' | 'practice'
  bp_config?: Partial<BPConfig>
  team_a_id?: number
  team_b_id?: number
}

export interface JoinRoomRequest {
  team_side?: 'blue' | 'red'
  role?: 'commander' | 'player' | 'observer'
}

export interface UpdateParticipantRequest {
  team_side?: 'blue' | 'red'
  role?: 'commander' | 'player' | 'observer'
  is_ready?: boolean
}

// 响应类型
export interface BPRoomListResponse {
  rooms: BPRoom[]
  total: number
  page: number
  per_page: number
}

export interface BPRoomResponse {
  room: BPRoom
  message?: string
}

export interface ParticipantResponse {
  participant: BPRoomParticipant
  message?: string
}

/**
 * BP房间API客户端类
 */
export class BPRoomsApi {
  constructor(private client: typeof apiClient) {}

  /**
   * 创建BP房间
   */
  async createRoom(data: CreateBPRoomRequest): Promise<BPRoomResponse> {
    return this.client.post<BPRoomResponse>('/bp/rooms', data)
  }

  /**
   * 获取房间详情
   */
  async getRoom(roomId: string): Promise<BPRoomResponse> {
    return this.client.get<BPRoomResponse>(`/bp/rooms/${roomId}`)
  }

  /**
   * 更新房间信息
   */
  async updateRoom(roomId: string, data: Partial<CreateBPRoomRequest>): Promise<BPRoomResponse> {
    return this.client.put<BPRoomResponse>(`/bp/rooms/${roomId}`, data)
  }

  /**
   * 删除房间
   */
  async deleteRoom(roomId: string): Promise<{ message: string }> {
    return this.client.delete<{ message: string }>(`/bp/rooms/${roomId}`)
  }

  /**
   * 获取公开房间列表
   */
  async getPublicRooms(params: {
    page?: number
    per_page?: number
    room_type?: string
  } = {}): Promise<BPRoomListResponse> {
    const searchParams = new URLSearchParams()
    if (params.page) searchParams.set('page', params.page.toString())
    if (params.per_page) searchParams.set('per_page', params.per_page.toString())
    if (params.room_type) searchParams.set('room_type', params.room_type)
    
    const url = searchParams.toString() 
      ? `/bp/rooms/public?${searchParams}` 
      : '/bp/rooms/public'
    
    return this.client.get<BPRoomListResponse>(url)
  }

  /**
   * 获取我创建的房间
   */
  async getMyRooms(): Promise<BPRoomListResponse> {
    return this.client.get<BPRoomListResponse>('/bp/rooms/my')
  }

  /**
   * 获取我参与的房间
   */
  async getMyActiveRooms(): Promise<BPRoomListResponse> {
    return this.client.get<BPRoomListResponse>('/bp/rooms/active')
  }

  /**
   * 加入房间
   */
  async joinRoom(roomId: string, data: JoinRoomRequest): Promise<ParticipantResponse> {
    return this.client.post<ParticipantResponse>(`/bp/rooms/${roomId}/join`, data)
  }

  /**
   * 离开房间
   */
  async leaveRoom(roomId: string): Promise<{ message: string }> {
    return this.client.post<{ message: string }>(`/bp/rooms/${roomId}/leave`, {})
  }

  /**
   * 更新参与者信息
   */
  async updateParticipant(
    roomId: string, 
    userId: number, 
    data: UpdateParticipantRequest
  ): Promise<ParticipantResponse> {
    return this.client.put<ParticipantResponse>(
      `/bp/rooms/${roomId}/participants/${userId}`, 
      data
    )
  }

  /**
   * 移除参与者
   */
  async removeParticipant(roomId: string, userId: number): Promise<{ message: string }> {
    return this.client.delete<{ message: string }>(`/bp/rooms/${roomId}/participants/${userId}`)
  }

  /**
   * 开始房间BP阶段
   */
  async startRoom(roomId: string): Promise<BPRoomResponse> {
    return this.client.post<BPRoomResponse>(`/bp/rooms/${roomId}/start`, {})
  }

  /**
   * 结束房间BP阶段
   */
  async completeRoom(roomId: string): Promise<BPRoomResponse> {
    return this.client.post<BPRoomResponse>(`/bp/rooms/${roomId}/complete`, {})
  }

  /**
   * 重置房间状态
   */
  async resetRoom(roomId: string): Promise<BPRoomResponse> {
    return this.client.post<BPRoomResponse>(`/bp/rooms/${roomId}/reset`, {})
  }
}

// 导出API实例
export const bpRoomsApi = new BPRoomsApi(apiClient)