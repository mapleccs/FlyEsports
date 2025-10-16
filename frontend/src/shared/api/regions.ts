/**
 * Regions API client
 */

import { apiClient } from './client'

// Types
export interface RegionSummary {
  region_id: number
  region_name: string
  status: string
  total_players: number
  active_players: number
  is_active: boolean
  created_at: string
}

export interface RegionListResponse {
  regions: RegionSummary[]
  total?: number
}

// API functions
export const regionsApi = {
  /**
   * Get all regions (public endpoint for registration)
   */
  async getRegions(activeOnly: boolean = false): Promise<RegionListResponse> {
    const startTime = Date.now()
    console.log('=== 发起赛区数据请求 ===', {
      activeOnly,
      timestamp: new Date().toISOString(),
    })

    try {
      const params = new URLSearchParams()
      if (activeOnly) {
        params.append('active_only', 'true')
      }

      const queryString = params.toString()
      const url = queryString ? `/registration/regions?${queryString}` : '/registration/regions'

      console.log('请求URL:', url)

      const response = await apiClient.get(url)
      const duration = Date.now() - startTime

      console.log('=== 赛区数据请求成功 ===', {
        url,
        duration: `${duration}ms`,
        regionsCount: response.data.regions?.length || 0,
        regions:
          response.data.regions?.map((r: any) => ({ id: r.region_id, name: r.region_name })) || [],
      })

      return response.data
    } catch (error: any) {
      const duration = Date.now() - startTime
      console.error('=== 赛区数据请求失败 ===', {
        duration: `${duration}ms`,
        error: {
          status: error.response?.status,
          message: error.message,
          code: error.code,
        },
      })

      // 不再使用模拟数据，直接抛出错误让调用方处理
      console.error('Regions API 请求失败，无法获取真实数据')
      throw error
    }
  },

  /**
   * Get all regions (authenticated endpoint)
   */
  async getRegionsAuth(activeOnly: boolean = false): Promise<RegionListResponse> {
    const params = new URLSearchParams()
    if (activeOnly) {
      params.append('active_only', 'true')
    }

    const queryString = params.toString()
    const url = queryString ? `/regions?${queryString}` : '/regions'

    const response = await apiClient.get(url)
    return response.data
  },

  /**
   * Get region by ID
   */
  async getRegion(regionId: string): Promise<RegionSummary> {
    const response = await apiClient.get(`/regions/${regionId}`)
    return response.data
  },
}
