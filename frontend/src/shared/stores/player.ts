/**
 * Player store for state management
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { playersApi, regionsApi } from '@/shared/api'
import type { PlayerProfile, PlayerRegistrationData, RegionSummary } from '@/shared/types/player'

export const usePlayerStore = defineStore('player', () => {
  // State
  const profiles = ref<PlayerProfile[]>([])
  const regions = ref<RegionSummary[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const hasProfiles = computed(() => profiles.value.length > 0)
  const activeRegions = computed(() => regions.value.filter(region => region.is_active))

  // Actions
  async function fetchMyProfiles() {
    loading.value = true
    error.value = null

    try {
      const data = await playersApi.getMyProfiles()
      profiles.value = data
    } catch (err: any) {
      error.value = err.response?.data?.detail || '获取选手档案失败'
      console.error('Failed to fetch profiles:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchRegions(activeOnly: boolean = true) {
    loading.value = true
    error.value = null

    try {
      const response = await regionsApi.getRegions(activeOnly)
      regions.value = response.regions
    } catch (err: any) {
      error.value = err.response?.data?.detail || '获取赛区列表失败'
      console.error('Failed to fetch regions:', err)
    } finally {
      loading.value = false
    }
  }

  async function registerPlayer(data: PlayerRegistrationData) {
    loading.value = true
    error.value = null

    try {
      const result = await playersApi.registerPlayer(data)

      // Refresh profiles after successful registration
      await fetchMyProfiles()

      return result
    } catch (err: any) {
      error.value = err.response?.data?.detail || '选手注册失败'
      console.error('Failed to register player:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function checkSummonerAvailability(summonerName: string, regionId: number) {
    try {
      const result = await playersApi.checkSummonerAvailability({
        summoner_name: summonerName,
        region_id: regionId,
      })
      return result.available
    } catch (err: any) {
      console.error('Failed to check summoner availability:', err)
      return false
    }
  }

  function getProfileByRegion(regionId: number): PlayerProfile | undefined {
    return profiles.value.find(profile => profile.region_id === regionId)
  }

  function clearError() {
    error.value = null
  }

  return {
    // State
    profiles,
    regions,
    loading,
    error,

    // Computed
    hasProfiles,
    activeRegions,

    // Actions
    fetchMyProfiles,
    fetchRegions,
    registerPlayer,
    checkSummonerAvailability,
    getProfileByRegion,
    clearError,
  }
})
