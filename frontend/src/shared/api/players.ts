/**
 * Players API client
 */

import { apiClient } from './client'

// Types
export interface PlayerRegistrationRequest {
  region_id: number
  player_name: string
  summoner_name: string
  position: 'TOP' | 'JUNGLE' | 'MIDDLE' | 'BOTTOM' | 'UTILITY'
  rank_tier?:
    | 'IRON'
    | 'BRONZE'
    | 'SILVER'
    | 'GOLD'
    | 'PLATINUM'
    | 'EMERALD'
    | 'DIAMOND'
    | 'MASTER'
    | 'GRANDMASTER'
    | 'CHALLENGER'
  rank_division?: 'I' | 'II' | 'III' | 'IV'
  league_points?: number
  description?: string
}

export interface PlayerProfile {
  profile_id: string
  player_name: string
  summoner_name: string
  position: string
  current_rating: number
  effective_rating: number
  rank_display: string
  contract_status: string
  current_team_id?: string
  total_matches: number
  win_rate: number
  region_id: number
  created_at: string
  last_active?: string
}

export interface PlayerRegistrationResponse {
  profile_id: string
  player_name: string
  summoner_name: string
  position: string
  current_rating: number
  region_id: number
  created_at: string
}

export interface SummonerAvailabilityRequest {
  summoner_name: string
  region_id: number
  exclude_profile_id?: string
}

export interface SummonerAvailabilityResponse {
  available: boolean
  summoner_name: string
  region_id: number
}

export interface PlayerListResponse {
  players: PlayerProfile[]
  total?: number
  page?: number
  per_page?: number
}

// API functions
export const playersApi = {
  /**
   * Register player to region
   */
  async registerPlayer(data: PlayerRegistrationRequest): Promise<PlayerRegistrationResponse> {
    const response = await apiClient.post('/players/register', data)
    return response.data
  },

  /**
   * Get current user's player profiles
   */
  async getMyProfiles(): Promise<PlayerProfile[]> {
    const response = await apiClient.get('/players/me')
    return response.data
  },

  /**
   * Get player profile by ID
   */
  async getPlayerProfile(profileId: string): Promise<PlayerProfile> {
    const response = await apiClient.get(`/players/${profileId}`)
    return response.data
  },

  /**
   * Get players in a region
   */
  async getRegionPlayers(params: {
    regionId: number
    page?: number
    perPage?: number
    position?: string
    freeOnly?: boolean
  }): Promise<PlayerListResponse> {
    const { regionId, ...queryParams } = params
    const searchParams = new URLSearchParams()

    if (queryParams.page) searchParams.set('page', queryParams.page.toString())
    if (queryParams.perPage) searchParams.set('per_page', queryParams.perPage.toString())
    if (queryParams.position) searchParams.set('position', queryParams.position)
    if (queryParams.freeOnly) searchParams.set('free_only', queryParams.freeOnly.toString())

    const response = await apiClient.get(`/players/region/${regionId.toString()}?${searchParams.toString()}`)
    return response.data
  },

  /**
   * Check summoner name availability
   */
  async checkSummonerAvailability(
    data: SummonerAvailabilityRequest
  ): Promise<SummonerAvailabilityResponse> {
    const response = await apiClient.post('/players/check-summoner', data)
    return response.data
  },
}
