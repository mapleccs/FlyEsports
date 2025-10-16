<template>
  <div class="player-pool">
    <!-- 页面头部 -->
    <div class="pool-header">
      <div class="header-content">
        <h1 class="pool-title">选手池</h1>
        <div class="header-actions">
          <a-button
            v-if="canCompare"
            type="primary"
            :loading="comparisonLoading"
            @click="handleCompare"
          >
            对比选手 ({{ selectedPlayers.size }})
          </a-button>
          <a-button @click="showRecommendModal = true">
            推荐选手
          </a-button>
          <a-button @click="handleRefresh" :loading="loading">
            刷新
          </a-button>
        </div>
      </div>

      <!-- 搜索和筛选 -->
      <div class="search-filters">
        <div class="search-section">
          <a-input-search
            v-model:value="searchQuery"
            placeholder="搜索选手用户名、显示名称..."
            style="width: 300px"
            @search="handleSearch"
            allow-clear
          />
        </div>

        <div class="filter-section">
          <a-button @click="showFilterModal = true">
            <template #icon><FilterOutlined /></template>
            筛选条件
            <a-badge
              v-if="hasFilters"
              :count="filterCount"
              :offset="[10, 0]"
            />
          </a-button>

          <a-select
            v-model:value="currentRegion"
            placeholder="选择赛区"
            style="width: 150px"
            allow-clear
            @change="handleRegionChange"
          >
            <a-select-option :value="undefined">全部赛区</a-select-option>
            <a-select-option :value="1">华北赛区</a-select-option>
            <a-select-option :value="2">华南赛区</a-select-option>
            <a-select-option :value="3">华东赛区</a-select-option>
          </a-select>

          <a-select
            v-model:value="sortConfig.field"
            style="width: 150px"
            @change="handleSortChange"
          >
            <a-select-option value="rating">评分</a-select-option>
            <a-select-option value="confidence">置信度</a-select-option>
            <a-select-option value="total_matches">比赛场次</a-select-option>
            <a-select-option value="last_active">最近活跃</a-select-option>
          </a-select>

          <a-button
            @click="toggleSortOrder"
            :icon="sortConfig.order === 'desc' ? h(SortDescendingOutlined) : h(SortAscendingOutlined)"
          />
        </div>
      </div>

      <!-- 统计信息概览 -->
      <div v-if="statistics" class="pool-stats">
        <a-row :gutter="16">
          <a-col :span="4">
            <a-statistic title="总选手数" :value="statistics.total_players" />
          </a-col>
          <a-col :span="4">
            <a-statistic
              title="活跃选手"
              :value="statistics.active_players"
              :value-style="{ color: '#52c41a' }"
            />
          </a-col>
          <a-col :span="4">
            <a-statistic
              title="自由选手"
              :value="statistics.free_agents"
              :value-style="{ color: '#1890ff' }"
            />
          </a-col>
          <a-col :span="4">
            <a-statistic
              title="平均评分"
              :value="Math.round(statistics.average_rating)"
              suffix="分"
            />
          </a-col>
          <a-col :span="4">
            <a-statistic
              title="置信度"
              :value="(statistics.average_confidence * 100).toFixed(1)"
              suffix="%"
            />
          </a-col>
          <a-col :span="4">
            <a-statistic
              title="池健康度"
              :value="statistics.pool_health"
              :value-style="{
                color: statistics.pool_health === 'Healthy' ? '#52c41a' : '#faad14'
              }"
            />
          </a-col>
        </a-row>
      </div>
    </div>

    <!-- 选手列表 -->
    <div class="pool-content">
      <a-spin :spinning="loading">
        <div v-if="isEmpty" class="empty-state">
          <a-empty
            description="暂无选手数据"
            image="https://gw.alipayobjects.com/zos/antfincdn/ZHrcdLPrvN/empty.svg"
          >
            <a-button type="primary" @click="handleRefresh">
              重新加载
            </a-button>
          </a-empty>
        </div>

        <div v-else class="players-grid">
          <PlayerCard
            v-for="player in players"
            :key="player.id"
            :player="player"
            :selected="selectedPlayers.has(player.id)"
            @select="handlePlayerSelect"
            @view-detail="handleViewDetail"
          />
        </div>

        <!-- 分页 -->
        <div v-if="totalPages > 1" class="pagination-wrapper">
          <a-pagination
            v-model:current="currentPage"
            v-model:page-size="pageSize"
            :total="totalCount"
            :show-size-changer="true"
            :show-quick-jumper="true"
            :show-total="(total, range) => `第 ${range[0]}-${range[1]} 项，共 ${total} 项`"
            @change="handlePageChange"
            @show-size-change="handlePageSizeChange"
          />
        </div>
      </a-spin>
    </div>

    <!-- 筛选弹窗 -->
    <FilterModal
      v-model:visible="showFilterModal"
      :filters="filters"
      @apply="handleApplyFilters"
      @reset="handleResetFilters"
    />

    <!-- 推荐弹窗 -->
    <RecommendModal
      v-model:visible="showRecommendModal"
      :loading="recommendationLoading"
      @recommend="handleRecommend"
    />

    <!-- 对比弹窗 -->
    <ComparisonModal
      v-model:visible="showComparisonModal"
      :comparison="comparisonResult"
      :loading="comparisonLoading"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { storeToRefs } from 'pinia'
import {
  FilterOutlined,
  SortAscendingOutlined,
  SortDescendingOutlined
} from '@ant-design/icons-vue'

import { usePlayerPoolStore } from '@/shared/stores/player-pool'
import type { PlayerPoolFilter, RecommendPlayersRequest } from '@/shared/api/player-pool'

import PlayerCard from '../components/PlayerCard.vue'
import FilterModal from '../components/FilterModal.vue'
import RecommendModal from '../components/RecommendModal.vue'
import ComparisonModal from '../components/ComparisonModal.vue'

const router = useRouter()
const playerPoolStore = usePlayerPoolStore()

// 响应式数据
const searchQuery = ref('')
const showFilterModal = ref(false)
const showRecommendModal = ref(false)
const showComparisonModal = ref(false)

const sortConfig = ref({
  field: 'rating',
  order: 'desc' as 'asc' | 'desc'
})

// 使用storeToRefs保持响应性
const {
  loading,
  currentRegion,
  players,
  totalCount,
  currentPage,
  pageSize,
  totalPages,
  statistics,
  filters,
  selectedPlayers,
  recommendationLoading,
  comparisonResult,
  comparisonLoading,
  hasFilters,
  isEmpty,
  canCompare
} = storeToRefs(playerPoolStore)

const filterCount = computed(() => {
  return Object.keys(filters.value).filter(key => {
    const value = filters.value[key as keyof PlayerPoolFilter]
    return value !== undefined && value !== null && value !== '' &&
           !(['page', 'page_size', 'sort_by', 'sort_order'].includes(key))
  }).length
})

// 方法
const handleSearch = (value: string) => {
  playerPoolStore.searchPlayers(value)
}

const handleRefresh = () => {
  playerPoolStore.refreshPool()
}

const handleRegionChange = (regionId?: number) => {
  playerPoolStore.setRegion(regionId)
}

const handleSortChange = () => {
  playerPoolStore.updateSorting(sortConfig.value.field, sortConfig.value.order)
}

const toggleSortOrder = () => {
  sortConfig.value.order = sortConfig.value.order === 'desc' ? 'asc' : 'desc'
  handleSortChange()
}

const handlePageChange = (page: number) => {
  playerPoolStore.loadPage(page)
}

const handlePageSizeChange = (_current: number, size: number) => {
  playerPoolStore.updateFilters({ page_size: size, page: 1 })
  playerPoolStore.queryPool(currentRegion.value)
}

const handlePlayerSelect = (playerId: string) => {
  playerPoolStore.togglePlayerSelection(playerId)
}

const handleViewDetail = (playerId: string) => {
  router.push({ name: 'PlayerProfile', params: { id: playerId } })
}

const handleApplyFilters = (newFilters: Partial<PlayerPoolFilter>) => {
  playerPoolStore.applyFilters(newFilters)
  showFilterModal.value = false
}

const handleResetFilters = () => {
  playerPoolStore.resetFilters()
  playerPoolStore.queryPool(currentRegion.value)
  showFilterModal.value = false
}

const handleRecommend = async (request: RecommendPlayersRequest) => {
  await playerPoolStore.recommendPlayers(request)
  showRecommendModal.value = false
  message.success('推荐完成')
}

const handleCompare = async () => {
  const result = await playerPoolStore.comparePlayers()
  if (result) {
    showComparisonModal.value = true
  }
}

// 生命周期
onMounted(async () => {
  // 加载选手池数据和统计信息
  await playerPoolStore.queryPool(undefined, true)
})
</script>

<style scoped>
.player-pool {
  padding: 24px;
  min-height: 100vh;
  background: #f5f5f5;
}

.pool-header {
  background: white;
  border-radius: 8px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.pool-title {
  font-size: 28px;
  font-weight: 600;
  margin: 0;
  color: #1f2937;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.search-filters {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 24px;
  border-bottom: 1px solid #f0f0f0;
}

.filter-section {
  display: flex;
  gap: 12px;
  align-items: center;
}

.pool-stats {
  background: #fafafa;
  padding: 20px;
  border-radius: 6px;
  border: 1px solid #f0f0f0;
}

.pool-content {
  background: white;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.empty-state {
  padding: 60px 0;
  text-align: center;
}

.players-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  padding-top: 24px;
  border-top: 1px solid #f0f0f0;
}

@media (max-width: 768px) {
  .player-pool {
    padding: 16px;
  }

  .search-filters {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }

  .filter-section {
    justify-content: center;
    flex-wrap: wrap;
  }

  .players-grid {
    grid-template-columns: 1fr;
  }
}
</style>