import { defineStore } from 'pinia'
import { ref, computed, reactive } from 'vue'
import { message } from 'ant-design-vue'
import {
  PlayerPoolAPI,
  type PlayerPoolFilter,
  type PlayerPoolResponse,
  type PlayerPoolProfile,
  type PlayerPoolStatistics,
  type PlayerRecommendation,
  type PlayerComparison,
  type RecommendPlayersRequest,
  type ComparePlayersRequest
} from '@/shared/api/player-pool'

export const usePlayerPoolStore = defineStore('playerPool', () => {
  // 状态
  const loading = ref(false)
  const currentRegion = ref<number | undefined>(undefined)
  const players = ref<PlayerPoolProfile[]>([])
  const totalCount = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(20)
  const totalPages = ref(1)
  const hasNextPage = ref(false)
  const hasPreviousPage = ref(false)
  const statistics = ref<PlayerPoolStatistics | null>(null)
  const queryTime = ref<number | undefined>(undefined)
  const fromCache = ref(false)

  // 筛选条件
  const filters = reactive<PlayerPoolFilter>({
    page: 1,
    page_size: 20,
    sort_by: 'rating',
    sort_order: 'desc'
  })

  // 选中的选手 (用于对比功能)
  const selectedPlayers = ref<Set<string>>(new Set())

  // 推荐结果
  const recommendations = ref<PlayerRecommendation[]>([])
  const recommendationLoading = ref(false)

  // 对比结果
  const comparisonResult = ref<PlayerComparison | null>(null)
  const comparisonLoading = ref(false)

  // Getters
  const hasFilters = computed(() => {
    return Object.keys(filters).some(key => {
      const value = filters[key as keyof PlayerPoolFilter]
      return value !== undefined && value !== null && value !== '' &&
             !(['page', 'page_size', 'sort_by', 'sort_order'].includes(key))
    })
  })

  const isEmpty = computed(() => players.value.length === 0 && !loading.value)

  const selectedPlayersList = computed(() => {
    return players.value.filter(player => selectedPlayers.value.has(player.id))
  })

  const canCompare = computed(() => selectedPlayers.value.size >= 2 && selectedPlayers.value.size <= 5)

  // Actions
  const resetFilters = () => {
    Object.keys(filters).forEach(key => {
      if (!['page', 'page_size', 'sort_by', 'sort_order'].includes(key)) {
        delete filters[key as keyof PlayerPoolFilter]
      }
    })
    filters.page = 1
  }

  const updateFilters = (newFilters: Partial<PlayerPoolFilter>) => {
    Object.assign(filters, newFilters)
    if (newFilters.page === undefined) {
      filters.page = 1
    }
  }

  const queryPool = async (regionId?: number, includeStatistics = false) => {
    loading.value = true
    try {
      const requestFilters = { ...filters }
      if (includeStatistics) {
        requestFilters.include_statistics = true
      }

      const response: PlayerPoolResponse = await PlayerPoolAPI.queryPool(regionId, requestFilters)

      players.value = response.players
      totalCount.value = response.total_count
      currentPage.value = response.page
      pageSize.value = response.page_size
      totalPages.value = response.total_pages
      hasNextPage.value = response.has_next_page
      hasPreviousPage.value = response.has_previous_page
      fromCache.value = response.from_cache
      queryTime.value = response.query_time_ms
      currentRegion.value = regionId

      if (response.statistics) {
        statistics.value = response.statistics
      }

    } catch (error) {
      console.error('Failed to query player pool:', error)
      message.error('获取选手池信息失败')
      players.value = []
      totalCount.value = 0
    } finally {
      loading.value = false
    }
  }

  const loadPage = async (page: number) => {
    updateFilters({ page })
    await queryPool(currentRegion.value)
  }

  const refreshPool = async () => {
    await queryPool(currentRegion.value, !!statistics.value)
  }

  const loadStatistics = async (regionId?: number) => {
    try {
      const stats = await PlayerPoolAPI.getPoolStatistics(regionId)
      statistics.value = stats
      return stats
    } catch (error) {
      console.error('Failed to load pool statistics:', error)
      message.error('获取统计信息失败')
      return null
    }
  }

  const searchPlayers = async (query: string) => {
    updateFilters({ search_query: query })
    await queryPool(currentRegion.value)
  }

  const togglePlayerSelection = (playerId: string) => {
    if (selectedPlayers.value.has(playerId)) {
      selectedPlayers.value.delete(playerId)
    } else {
      if (selectedPlayers.value.size >= 5) {
        message.warning('最多只能选择5个选手进行对比')
        return
      }
      selectedPlayers.value.add(playerId)
    }
  }

  const clearSelection = () => {
    selectedPlayers.value.clear()
  }

  const recommendPlayers = async (request: RecommendPlayersRequest) => {
    recommendationLoading.value = true
    try {
      const result = await PlayerPoolAPI.recommendPlayers(request)
      recommendations.value = result
      return result
    } catch (error) {
      console.error('Failed to get recommendations:', error)
      message.error('获取推荐选手失败')
      return []
    } finally {
      recommendationLoading.value = false
    }
  }

  const comparePlayers = async (playerIds?: string[]) => {
    const idsToCompare = playerIds || Array.from(selectedPlayers.value)

    if (idsToCompare.length < 2) {
      message.warning('至少需要选择2个选手进行对比')
      return null
    }

    if (idsToCompare.length > 5) {
      message.warning('最多只能对比5个选手')
      return null
    }

    comparisonLoading.value = true
    try {
      const request: ComparePlayersRequest = {
        player_ids: idsToCompare
      }

      const result = await PlayerPoolAPI.comparePlayers(request)
      comparisonResult.value = result
      return result
    } catch (error) {
      console.error('Failed to compare players:', error)
      message.error('选手对比失败')
      return null
    } finally {
      comparisonLoading.value = false
    }
  }

  const getPlayerById = (playerId: string): PlayerPoolProfile | undefined => {
    return players.value.find(player => player.id === playerId)
  }

  const updateSorting = async (sortBy: string, sortOrder: 'asc' | 'desc' = 'desc') => {
    updateFilters({ sort_by: sortBy, sort_order: sortOrder, page: 1 })
    await queryPool(currentRegion.value)
  }

  const setRegion = async (regionId?: number) => {
    currentRegion.value = regionId
    resetFilters()
    await queryPool(regionId)
  }

  const applyFilters = async (newFilters: Partial<PlayerPoolFilter>) => {
    updateFilters({ ...newFilters, page: 1 })
    await queryPool(currentRegion.value)
  }

  // 导出状态和方法
  return {
    // State
    loading,
    currentRegion,
    players,
    totalCount,
    currentPage,
    pageSize,
    totalPages,
    hasNextPage,
    hasPreviousPage,
    statistics,
    queryTime,
    fromCache,
    filters,
    selectedPlayers,
    recommendations,
    recommendationLoading,
    comparisonResult,
    comparisonLoading,

    // Getters
    hasFilters,
    isEmpty,
    selectedPlayersList,
    canCompare,

    // Actions
    resetFilters,
    updateFilters,
    queryPool,
    loadPage,
    refreshPool,
    loadStatistics,
    searchPlayers,
    togglePlayerSelection,
    clearSelection,
    recommendPlayers,
    comparePlayers,
    getPlayerById,
    updateSorting,
    setRegion,
    applyFilters
  }
})