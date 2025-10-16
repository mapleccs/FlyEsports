import type { AxiosResponse } from 'axios'
import { apiClient } from './client'

// 类型定义
export interface PlayerPoolFilter {
  region_id?: number
  position?: string
  min_rating?: number
  max_rating?: number
  min_confidence?: number
  max_confidence?: number
  min_matches?: number
  max_matches?: number
  contract_status?: 'free_agent' | 'contracted' | 'locked' | 'all'
  last_active_days?: number
  dimension_filters?: Record<string, number>
  search_query?: string
  include_inactive?: boolean
  include_statistics?: boolean
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export interface PlayerRating {
  current_score: number
  locked_score?: number
  confidence_level: number
  total_matches: number
  six_dimensions: {
    kda: number
    damage: number
    economy: number
    vision: number
    objective: number
    teamfight: number
  }
}

export interface PlayerPoolProfile {
  id: string
  username: string
  display_name: string
  primary_position: string
  secondary_position?: string
  contract_status: string
  rating: PlayerRating
  total_matches: number
  total_wins: number
  win_rate: number
  last_active_at?: string
  avatar_url?: string
  bio?: string
  achievements?: string[]
  preferred_champions?: string[]
}

export interface PlayerPoolStatistics {
  total_players: number
  active_players: number
  free_agents: number
  contracted_players: number
  position_distribution: Record<string, number>
  average_rating: number
  median_rating: number
  rating_std_deviation: number
  min_rating: number
  max_rating: number
  rating_tiers: Record<string, number>
  average_confidence: number
  high_confidence_players: number
  low_confidence_players: number
  matches_last_week: number
  matches_last_month: number
  most_active_position: string
  least_active_position: string
  highest_rated_players: Array<{
    id: string
    username: string
    rating: number
    position: string
  }>
  most_improved_players: Array<{
    id: string
    username: string
    rating_change: number
    position: string
  }>
  dimension_averages: Record<string, Record<string, number>>
  new_players_last_week: number
  new_players_last_month: number
  retention_rate_30d: number
  generated_at: string
  pool_health: string
  growth_trend: string
  competitive_balance: number
}

export interface PlayerPoolResponse {
  players: PlayerPoolProfile[]
  total_count: number
  page: number
  page_size: number
  total_pages: number
  statistics?: PlayerPoolStatistics
  query_time_ms?: number
  from_cache: boolean
  has_next_page: boolean
  has_previous_page: boolean
}

export interface RecommendPlayersRequest {
  team_needs: {
    positions_needed: string[]
    min_rating?: number
    max_rating?: number
    preferred_playstyle?: string[]
    budget_range?: [number, number]
    experience_level?: 'rookie' | 'intermediate' | 'veteran' | 'any'
    contract_status?: string
  }
  region_id?: number
  max_recommendations?: number
}

export interface PlayerRecommendation {
  player: PlayerPoolProfile
  fit_score: number
  fit_reasons: string[]
  estimated_cost?: number
  availability_status: string
}

export interface ComparePlayersRequest {
  player_ids: string[]
  comparison_aspects?: string[]
}

export interface PlayerComparison {
  players: PlayerPoolProfile[]
  comparison: {
    basic_stats: Record<string, number[]>
    ratings: Record<string, number[]>
    dimensions: Record<string, number[]>
    experience: Record<string, any[]>
    strengths_weaknesses: Record<string, {
      strengths: string[]
      weaknesses: string[]
    }>
  }
  generated_at: string
}

// API 服务类
export class PlayerPoolAPI {
  /**
   * 查询选手池
   */
  static async queryPool(
    regionId?: number,
    filters: PlayerPoolFilter = {}
  ): Promise<PlayerPoolResponse> {
    const params = new URLSearchParams()

    if (regionId !== undefined && regionId !== null) {
      params.append('region_id', regionId.toString())
    }

    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        if (typeof value === 'object' && key === 'dimension_filters') {
          Object.entries(value).forEach(([dim, score]) => {
            params.append(dim + '_min', (score as number).toString())
          })
        } else {
          params.append(key, value.toString())
        }
      }
    })

    const endpoint = '/player-pool'
    const queryString = params.toString()
    const response: AxiosResponse<PlayerPoolResponse> = await apiClient.get(
      queryString ? endpoint + '?' + queryString : endpoint
    )
    return response.data
  }

  /**
   * 获取选手池统计信息
   */
  static async getPoolStatistics(regionId?: number): Promise<PlayerPoolStatistics> {
    const params = new URLSearchParams()

    if (regionId !== undefined && regionId !== null) {
      params.append('region_id', regionId.toString())
    }

    const endpoint = '/player-pool/statistics'
    const queryString = params.toString()
    const response: AxiosResponse<PlayerPoolStatistics> = await apiClient.get(
      queryString ? endpoint + '?' + queryString : endpoint
    )
    return response.data
  }

  /**
   * 推荐选手
   */
  static async recommendPlayers(
    request: RecommendPlayersRequest
  ): Promise<PlayerRecommendation[]> {
    const response: AxiosResponse<PlayerRecommendation[]> = await apiClient.post(
      '/player-pool/recommend',
      request
    )
    return response.data
  }

  /**
   * 对比选手
   */
  static async comparePlayers(
    request: ComparePlayersRequest
  ): Promise<PlayerComparison> {
    const response: AxiosResponse<PlayerComparison> = await apiClient.post(
      '/player-pool/compare',
      request
    )
    return response.data
  }

  /**
   * 搜索选手
   */
  static async searchPlayers(
    query: string,
    filters: PlayerPoolFilter = {}
  ): Promise<PlayerPoolResponse> {
    const searchFilters = { ...filters, search_query: query }
    return this.queryPool(undefined, searchFilters)
  }

  /**
   * 获取选手详细信息
   */
  static async getPlayerDetail(playerId: string): Promise<PlayerPoolProfile> {
    const response: AxiosResponse<PlayerPoolProfile> = await apiClient.get(
      `/player-pool/players/${playerId}`
    )
    return response.data
  }
}

// 工具函数
export const playerPoolUtils = {
  /**
   * 获取评分等级
   */
  getRatingTier(rating: number): string {
    if (rating >= 3000) return 'Challenger'
    if (rating >= 2500) return 'Master'
    if (rating >= 2000) return 'Diamond'
    if (rating >= 1500) return 'Platinum'
    if (rating >= 1200) return 'Gold'
    if (rating >= 900) return 'Silver'
    return 'Bronze'
  },

  /**
   * 获取等级颜色
   */
  getTierColor(rating: number): string {
    const tier = this.getRatingTier(rating)
    const colors: Record<string, string> = {
      'Challenger': '#F5C842',
      'Master': '#9B59B6',
      'Diamond': '#3498DB',
      'Platinum': '#1ABC9C',
      'Gold': '#F39C12',
      'Silver': '#95A5A6',
      'Bronze': '#8B4513'
    }
    return colors[tier] || '#95A5A6'
  },

  /**
   * 格式化维度分数为百分比
   */
  formatDimensionScore(score: number): string {
    return `${Math.round(score)}%`
  },

  /**
   * 获取位置显示名称
   */
  getPositionDisplayName(position: string): string {
    const names: Record<string, string> = {
      'TOP': '上单',
      'JUNGLE': '打野',
      'MIDDLE': '中单',
      'BOTTOM': '下路',
      'UTILITY': '辅助'
    }
    return names[position] || position
  },

  /**
   * 计算胜率
   */
  calculateWinRate(wins: number, totalMatches: number): number {
    return totalMatches > 0 ? (wins / totalMatches) * 100 : 0
  },

  /**
   * 格式化最后活跃时间
   */
  formatLastActive(lastActiveAt?: string): string {
    if (!lastActiveAt) return '从未活跃'

    const date = new Date(lastActiveAt)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffDays === 0) return '今天活跃'
    if (diffDays === 1) return '昨天活跃'
    if (diffDays < 7) return `${diffDays}天前活跃`
    if (diffDays < 30) return `${Math.floor(diffDays / 7)}周前活跃`
    return `${Math.floor(diffDays / 30)}个月前活跃`
  }
}