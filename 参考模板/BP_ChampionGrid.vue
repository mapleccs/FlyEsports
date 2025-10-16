<template>
  <div class="hero-pool">
    <!-- 精简搜索栏 -->
    <div class="filter-bar">
      <input 
        type="text" 
        v-model="searchQuery" 
        placeholder="搜索英雄..." 
        class="search-bar"
        @keyup.enter="searchChampion"
      >
    </div>
    
    <!-- 英雄网格 -->
    <div class="hero-grid">
      <BP_ChampionCard
          v-for="champion in filteredChampions"
          :key="champion.id"
          :champion="champion"
          :is-banned="bpStore.bannedOrPickedIds.has(champion.id)"
          :is-picked="bpStore.bannedOrPickedIds.has(champion.id)"
          :is-selected="bpStore.selectedChampionId === champion.id"
          :is-hovering="bpStore.hoveringChampion?.id === champion.id"
          @select="handleChampionSelect"
          @hover="handleChampionHover"
          @leave="handleChampionLeave"
      />
    </div>
  </div>
</template>

<script setup>
import {ref, computed} from 'vue';
import {useBpStore} from '@/stores/bpStore';
import BP_ChampionCard from './BP_ChampionCard.vue';

const bpStore = useBpStore();
const searchQuery = ref('');

// 搜索英雄
const searchChampion = () => {
  // 可以添加搜索高亮或跳转到第一个匹配项
};

// 过滤英雄列表
const filteredChampions = computed(() => {
  let champions = bpStore.allChampions;
  
  // 按搜索关键词筛选
  if (searchQuery.value) {
    champions = champions.filter(c =>
      c.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      c.title?.toLowerCase().includes(searchQuery.value.toLowerCase())
    );
  }
  
  return champions;
});

// 处理英雄选择
const handleChampionSelect = (champion) => {
  bpStore.selectChampion(champion);
};

// 处理英雄悬停
const handleChampionHover = (champion) => {
  if (bpStore.isMyTurn) {
    bpStore.setHoveringChampion(champion);
  }
};

// 处理鼠标离开
const handleChampionLeave = () => {
  bpStore.clearHoveringChampion();
};
</script>

<style scoped>
.hero-pool {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 精简搜索栏 */
.filter-bar {
  background: #16213e;
  padding: clamp(4px, 0.8vw, 8px);
  border-bottom: 2px solid #1a1a2e;
}

.search-bar {
  width: clamp(200px, 35%, 300px);
  padding: clamp(4px, 0.8vw, 8px) clamp(8px, 1.2vw, 12px);
  background: #1a1a2e;
  border: 2px solid transparent;
  border-radius: clamp(6px, 0.8vw, 10px);
  color: #ffffff;
  font-size: clamp(10px, 1vw, 12px);
  transition: all 0.3s ease;
  margin: 0 auto;
  display: block;
}

.search-bar::placeholder {
  color: #7f8c8d;
}

.search-bar:focus {
  outline: none;
  border-color: #3498db;
  background: #1a2442;
}


/* 英雄网格 */
.hero-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(clamp(60px, 5vw, 80px), 1fr));
  gap: clamp(8px, 1.2vw, 15px);
  padding: clamp(12px, 2vw, 20px);
  overflow-y: auto;
  background: linear-gradient(180deg, #0f3460 0%, #16213e 100%);
}

/* 自定义滚动条 */
.hero-grid::-webkit-scrollbar {
  width: 10px;
}

.hero-grid::-webkit-scrollbar-track {
  background: #16213e;
  border-radius: 5px;
}

.hero-grid::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, #3498db 0%, #2980b9 100%);
  border-radius: 5px;
  transition: all 0.3s ease;
}

.hero-grid::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, #5dade2 0%, #3498db 100%);
}

/* 响应式断点调整 */
@media (max-width: 768px) {
  .filter-bar {
    padding: 3px 6px;
  }
  
  .search-bar {
    width: clamp(150px, 50%, 250px);
    padding: 4px 8px;
    font-size: 10px;
  }
  
  .hero-grid {
    grid-template-columns: repeat(auto-fill, minmax(50px, 1fr));
    gap: 8px;
    padding: 10px;
  }
}

@media (min-width: 769px) and (max-width: 1024px) {
  .search-bar {
    width: clamp(180px, 40%, 280px);
  }
  
  .hero-grid {
    grid-template-columns: repeat(auto-fill, minmax(65px, 1fr));
  }
}

@media (min-width: 1441px) {
  .search-bar {
    width: clamp(220px, 30%, 320px);
  }
  
  .hero-grid {
    grid-template-columns: repeat(auto-fill, minmax(75px, 1fr));
    gap: 15px;
  }
}

@media (min-width: 2561px) {
  .search-bar {
    width: clamp(250px, 25%, 350px);
    padding: 8px 15px;
  }
  
  .hero-grid {
    grid-template-columns: repeat(auto-fill, minmax(85px, 1fr));
    gap: 18px;
    padding: 25px;
  }
}
</style>