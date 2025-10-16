<template>
  <div class="champion-pool">
    <!-- 搜索和筛选栏 -->
    <div class="filter-bar">
      <div class="search-container">
        <div class="search-wrapper">
          <div class="search-icon">
            <SearchOutlined />
          </div>
          <input
            v-model="searchQuery"
            placeholder="搜索英雄名称或称号..."
            class="search-input-custom"
            @keyup.enter="handleSearch"
            @focus="onSearchFocus"
            @blur="onSearchBlur"
          />
          <div 
            v-if="searchQuery" 
            @click="clearSearch"
            class="clear-icon-custom"
          >
            <CloseOutlined />
          </div>
        </div>
        <div class="search-glow" :class="{ active: isSearchFocused }"></div>
      </div>
      
      <div class="position-container">
        <div class="position-wrapper">
          <div class="position-icon">
            <span class="position-symbol">⚔</span>
          </div>
          <select
            v-model="selectedPosition"
            class="position-select-custom"
            @change="handlePositionChange"
            @focus="onPositionFocus"
            @blur="onPositionBlur"
          >
            <option value="all">全部位置</option>
            <option value="top">🛡 上单</option>
            <option value="jungle">🌲 打野</option>
            <option value="mid">⚡ 中单</option>
            <option value="adc">🏹 ADC</option>
            <option value="support">💎 辅助</option>
          </select>
        </div>
        <div class="position-glow" :class="{ active: isPositionFocused }"></div>
      </div>
      
      <div class="filter-stats">
        <div class="results-count">
          <span class="count-number">{{ filteredChampions.length }}</span>
          <span class="count-label">英雄</span>
        </div>
      </div>
    </div>
    
    <!-- 英雄网格 -->
    <div class="champion-grid" ref="championGridRef">
      <BPChampionCard
        v-for="champion in filteredChampions"
        :key="champion.id"
        :champion="champion"
        :is-banned="bannedIds.includes(champion.id)"
        :is-picked="pickedIds.includes(champion.id)"
        :is-selected="selectedChampionId === champion.id"
        @select="handleChampionSelect"
      />
    </div>
    
    <!-- 无结果提示 -->
    <div v-if="filteredChampions.length === 0" class="no-results">
      <InboxOutlined />
      <p>没有找到匹配的英雄</p>
      <a-button @click="clearFilters" type="link">
        清除筛选条件
      </a-button>
    </div>
    
    <!-- 加载状态 -->
    <div v-if="championStore.loading" class="loading-state">
      <a-spin size="large" />
      <p>加载英雄数据中...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { 
  SearchOutlined, 
  CloseOutlined, 
  InboxOutlined 
} from '@ant-design/icons-vue'
import BPChampionCard from './BPChampionCard.vue'
import { useChampionStore, type Champion } from '@/shared/stores/champion'

// Props
interface Props {
  champions: Champion[]
  bannedIds: number[]
  pickedIds: number[]
  selectedChampionId: number | null
}

const props = defineProps<Props>()

// Emits
interface Emits {
  championSelect: [champion: Champion]
}

const emit = defineEmits<Emits>()

// 状态管理
const championStore = useChampionStore()

// 响应式数据
const searchQuery = ref('')
const selectedPosition = ref('all')
const championGridRef = ref<HTMLElement>()
const isSearchFocused = ref(false)
const isPositionFocused = ref(false)

// 计算属性
const filteredChampions = computed(() => {
  let champions = props.champions
  
  // 按位置筛选
  if (selectedPosition.value !== 'all') {
    champions = champions.filter(c => 
      c.position.some(p => p.toLowerCase() === selectedPosition.value.toLowerCase())
    )
  }
  
  // 按搜索关键词筛选
  if (searchQuery.value.trim()) {
    const searchTerm = searchQuery.value.toLowerCase()
    champions = champions.filter(c =>
      c.name.toLowerCase().includes(searchTerm) ||
      c.title.toLowerCase().includes(searchTerm)
    )
  }
  
  return champions
})

// 方法
const handleChampionSelect = (champion: Champion) => {
  // 检查英雄是否可选
  if (props.bannedIds.includes(champion.id) || props.pickedIds.includes(champion.id)) {
    return
  }
  
  emit('championSelect', champion)
  
  // 滚动到选中的英雄（如果需要）
  scrollToChampion(champion.id)
}

const handleSearch = () => {
  // 搜索时滚动到顶部
  if (championGridRef.value) {
    championGridRef.value.scrollTop = 0
  }
}

const handlePositionChange = () => {
  // 位置改变时滚动到顶部
  if (championGridRef.value) {
    championGridRef.value.scrollTop = 0
  }
}

const clearSearch = () => {
  searchQuery.value = ''
  if (championGridRef.value) {
    championGridRef.value.scrollTop = 0
  }
}

const clearFilters = () => {
  searchQuery.value = ''
  selectedPosition.value = 'all'
  if (championGridRef.value) {
    championGridRef.value.scrollTop = 0
  }
}

const scrollToChampion = async (championId: number) => {
  await nextTick()
  
  if (!championGridRef.value) return
  
  const championElement = championGridRef.value.querySelector(
    `[data-champion-id="${championId}"]`
  ) as HTMLElement
  
  if (championElement) {
    championElement.scrollIntoView({
      behavior: 'smooth',
      block: 'center'
    })
  }
}

// 新增：搜索框焦点状态处理
const onSearchFocus = () => {
  isSearchFocused.value = true
}

const onSearchBlur = () => {
  isSearchFocused.value = false
}

// 新增：位置选择框焦点状态处理
const onPositionFocus = () => {
  isPositionFocused.value = true
}

const onPositionBlur = () => {
  isPositionFocused.value = false
}

// 监听选中英雄变化，自动滚动
watch(() => props.selectedChampionId, (newId) => {
  if (newId) {
    scrollToChampion(newId)
  }
})
</script>

<style scoped>
.champion-pool {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #0f3460 0%, #16213e 100%);
  overflow: hidden;
}

/* 搜索和筛选栏 - 现代化设计 */
.filter-bar {
  background: linear-gradient(135deg, rgba(22, 33, 62, 0.95) 0%, rgba(15, 52, 96, 0.95) 100%);
  padding: 20px;
  border-bottom: 1px solid rgba(52, 152, 219, 0.2);
  display: flex;
  gap: 16px;
  align-items: center;
  backdrop-filter: blur(20px);
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
  position: relative;
  overflow: hidden;
}

.filter-bar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent 0%, rgba(52, 152, 219, 0.5) 50%, transparent 100%);
}

/* 搜索框容器 */
.search-container {
  flex: 1;
  max-width: 350px;
  position: relative;
}

.search-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  background: rgba(26, 26, 46, 0.7);
  border: 2px solid rgba(52, 152, 219, 0.3);
  border-radius: 16px;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(10px);
}

.search-wrapper:hover {
  border-color: rgba(52, 152, 219, 0.5);
  background: rgba(26, 26, 46, 0.8);
  transform: translateY(-1px);
  box-shadow: 0 8px 25px rgba(52, 152, 219, 0.15);
}

.search-icon {
  padding: 0 16px;
  color: rgba(52, 152, 219, 0.7);
  font-size: 18px;
  transition: all 0.3s ease;
}

.search-input-custom {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: #ecf0f1;
  font-size: 15px;
  font-weight: 500;
  padding: 14px 0;
  letter-spacing: 0.5px;
}

.search-input-custom::placeholder {
  color: rgba(236, 240, 241, 0.5);
  font-weight: 400;
}

.clear-icon-custom {
  padding: 0 16px;
  color: rgba(231, 76, 60, 0.7);
  cursor: pointer;
  font-size: 16px;
  transition: all 0.3s ease;
  border-radius: 50%;
}

.clear-icon-custom:hover {
  color: #e74c3c;
  background: rgba(231, 76, 60, 0.1);
  transform: scale(1.1);
}

.search-glow {
  position: absolute;
  top: -2px;
  left: -2px;
  right: -2px;
  bottom: -2px;
  background: linear-gradient(45deg, #3498db, #2ecc71, #3498db);
  border-radius: 18px;
  opacity: 0;
  transition: opacity 0.3s ease;
  z-index: -1;
  animation: searchGlow 3s ease-in-out infinite;
}

.search-glow.active {
  opacity: 0.6;
}

@keyframes searchGlow {
  0%, 100% { background: linear-gradient(45deg, #3498db, #2ecc71, #3498db); }
  50% { background: linear-gradient(45deg, #2ecc71, #3498db, #2ecc71); }
}

/* 位置选择框容器 */
.position-container {
  position: relative;
  min-width: 160px;
}

.position-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  background: rgba(26, 26, 46, 0.7);
  border: 2px solid rgba(52, 152, 219, 0.3);
  border-radius: 16px;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(10px);
}

.position-wrapper:hover {
  border-color: rgba(52, 152, 219, 0.5);
  background: rgba(26, 26, 46, 0.8);
  transform: translateY(-1px);
  box-shadow: 0 8px 25px rgba(52, 152, 219, 0.15);
}

.position-icon {
  padding: 0 16px;
  color: rgba(241, 196, 15, 0.8);
  font-size: 16px;
  transition: all 0.3s ease;
}

.position-symbol {
  font-weight: bold;
  text-shadow: 0 0 10px rgba(241, 196, 15, 0.5);
}

.position-select-custom {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: #ecf0f1;
  font-size: 14px;
  font-weight: 500;
  padding: 14px 16px 14px 0;
  cursor: pointer;
  appearance: none;
  position: relative;
}

.position-select-custom option {
  background: rgba(26, 26, 46, 0.95);
  color: #ecf0f1;
  padding: 10px;
  border: none;
  font-weight: 500;
}

.position-glow {
  position: absolute;
  top: -2px;
  left: -2px;
  right: -2px;
  bottom: -2px;
  background: linear-gradient(45deg, #f1c40f, #e67e22, #f1c40f);
  border-radius: 18px;
  opacity: 0;
  transition: opacity 0.3s ease;
  z-index: -1;
  animation: positionGlow 3s ease-in-out infinite;
}

.position-glow.active {
  opacity: 0.5;
}

@keyframes positionGlow {
  0%, 100% { background: linear-gradient(45deg, #f1c40f, #e67e22, #f1c40f); }
  50% { background: linear-gradient(45deg, #e67e22, #f1c40f, #e67e22); }
}

/* 筛选统计 */
.filter-stats {
  display: flex;
  align-items: center;
  gap: 16px;
}

.results-count {
  background: rgba(52, 152, 219, 0.15);
  border: 1px solid rgba(52, 152, 219, 0.3);
  border-radius: 12px;
  padding: 8px 16px;
  display: flex;
  align-items: center;
  gap: 6px;
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
}

.results-count:hover {
  background: rgba(52, 152, 219, 0.2);
  border-color: rgba(52, 152, 219, 0.5);
  transform: scale(1.02);
}

.count-number {
  color: #3498db;
  font-weight: 700;
  font-size: 16px;
  text-shadow: 0 0 10px rgba(52, 152, 219, 0.5);
}

.count-label {
  color: rgba(236, 240, 241, 0.8);
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 1px;
}

/* 英雄网格 - LOL客户端风格 */
.champion-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(74px, 1fr));
  gap: 8px;
  padding: 16px;
  overflow-y: auto;
  background: linear-gradient(180deg, #0f1419 0%, #1e2328 50%, #0f1419 100%);
  position: relative;
  border-top: 1px solid rgba(200, 170, 110, 0.2);
}

/* 自定义滚动条 - LOL风格 */
.champion-grid::-webkit-scrollbar {
  width: 14px;
}

.champion-grid::-webkit-scrollbar-track {
  background: linear-gradient(180deg, #1e2328 0%, #0f1419 100%);
  border-radius: 0;
  border: 1px solid #463714;
}

.champion-grid::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, #c8aa6e 0%, #96621d 100%);
  border-radius: 0;
  transition: all 0.3s ease;
  border: 1px solid #463714;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.champion-grid::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, #f0e6d2 0%, #c8aa6e 100%);
  box-shadow: 
    inset 0 1px 0 rgba(255, 255, 255, 0.3),
    0 0 8px rgba(200, 170, 110, 0.4);
}

/* 无结果提示 */
.no-results {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: rgba(236, 240, 241, 0.6);
  padding: 40px;
  text-align: center;
}

.no-results .anticon {
  font-size: 48px;
  margin-bottom: 16px;
  color: rgba(52, 152, 219, 0.4);
}

.no-results p {
  font-size: 16px;
  margin-bottom: 16px;
}

.no-results .ant-btn {
  color: #3498db;
}

.no-results .ant-btn:hover {
  color: #5dade2;
}

/* 加载状态 */
.loading-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #ecf0f1;
  padding: 40px;
}

.loading-state p {
  margin-top: 16px;
  font-size: 16px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .filter-bar {
    padding: 16px 12px;
    flex-direction: column;
    gap: 12px;
  }
  
  .search-container {
    max-width: none;
    width: 100%;
  }
  
  .position-container {
    width: 100%;
    min-width: auto;
  }
  
  .filter-stats {
    align-self: flex-end;
  }
  
  .search-wrapper,
  .position-wrapper {
    border-radius: 12px;
  }
  
  .search-input-custom,
  .position-select-custom {
    padding: 12px 0;
    font-size: 14px;
  }
  
  .search-icon,
  .position-icon {
    padding: 0 12px;
    font-size: 16px;
  }
  
  .champion-grid {
    grid-template-columns: repeat(auto-fill, minmax(58px, 1fr));
    gap: 6px;
    padding: 12px;
  }
  
  .champion-grid::-webkit-scrollbar {
    width: 8px;
  }
}

@media (max-width: 480px) {
  .filter-bar {
    padding: 8px;
  }
  
  .champion-grid {
    grid-template-columns: repeat(auto-fill, minmax(50px, 1fr));
    gap: 4px;
    padding: 8px;
  }
  
  .no-results {
    padding: 20px;
  }
  
  .no-results .anticon {
    font-size: 36px;
  }
  
  .no-results p {
    font-size: 14px;
  }
}

/* 大屏幕优化 */
@media (min-width: 1441px) {
  .champion-grid {
    grid-template-columns: repeat(auto-fill, minmax(82px, 1fr));
    gap: 10px;
    padding: 20px;
  }
}

@media (min-width: 2561px) {
  .filter-bar {
    padding: 20px;
  }
  
  .champion-grid {
    grid-template-columns: repeat(auto-fill, minmax(102px, 1fr));
    gap: 12px;
    padding: 24px;
  }
}
</style>