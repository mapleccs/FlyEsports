import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiClient } from '@/shared/api/client'

export interface Champion {
  id: number
  name: string
  title: string
  iconUrl: string
  splashUrl?: string
  position: string[]
  difficulty: number
  tags: string[]
  stats: {
    hp: number
    mp: number
    armor: number
    spellblock: number
    attackrange: number
    hpperlevel: number
    mpperlevel: number
    armorperlevel: number
    spellblockperlevel: number
    attackdamage: number
    attackdamageperlevel: number
    attackspeedperlevel: number
    movespeed: number
  }
}

export const useChampionStore = defineStore('champion', () => {
  // 状态
  const champions = ref<Champion[]>([])
  const loading = ref(false)
  const lastUpdated = ref<Date | null>(null)
  
  // 计算属性
  const allChampions = computed(() => champions.value)
  
  const championsByPosition = computed(() => {
    const positions: Record<string, Champion[]> = {
      top: [],
      jungle: [],
      mid: [],
      adc: [],
      support: []
    }
    
    champions.value.forEach(champion => {
      champion.position.forEach(pos => {
        if (positions[pos.toLowerCase()]) {
          positions[pos.toLowerCase()].push(champion)
        }
      })
    })
    
    return positions
  })
  
  const getChampionById = computed(() => {
    return (id: number) => champions.value.find(c => c.id === id)
  })
  
  const getChampionsByName = computed(() => {
    return (name: string) => {
      const searchTerm = name.toLowerCase()
      return champions.value.filter(c => 
        c.name.toLowerCase().includes(searchTerm) ||
        c.title.toLowerCase().includes(searchTerm)
      )
    }
  })
  
  // 方法
  const loadChampions = async (force = false) => {
    // 如果数据已存在且不强制刷新，直接返回
    if (champions.value.length > 0 && !force) {
      return champions.value
    }
    
    try {
      loading.value = true
      
      // 调用后端API获取英雄数据
      const response = await apiClient.get('/lobby/champions')
      
      if (response.data.success) {
        champions.value = response.data.champions
        lastUpdated.value = new Date()
        console.log(`已加载 ${champions.value.length} 个英雄数据`)
      } else {
        throw new Error(response.data.message || '获取英雄数据失败')
      }
      
      return champions.value
    } catch (error) {
      console.error('加载英雄数据失败:', error)
      
      // 如果API失败，使用本地模拟数据
      champions.value = generateMockChampions()
      lastUpdated.value = new Date()
      
      throw error
    } finally {
      loading.value = false
    }
  }
  
  const refreshChampions = async () => {
    return await loadChampions(true)
  }
  
  const searchChampions = (query: string, position?: string) => {
    let results = champions.value
    
    // 按位置筛选
    if (position && position !== 'all') {
      results = results.filter(c => 
        c.position.some(p => p.toLowerCase() === position.toLowerCase())
      )
    }
    
    // 按名称搜索
    if (query.trim()) {
      const searchTerm = query.toLowerCase()
      results = results.filter(c =>
        c.name.toLowerCase().includes(searchTerm) ||
        c.title.toLowerCase().includes(searchTerm) ||
        c.tags.some(tag => tag.toLowerCase().includes(searchTerm))
      )
    }
    
    return results
  }
  
  // 生成模拟数据（当API不可用时使用）
  const generateMockChampions = (): Champion[] => {
    const mockChampions = [
      {
        id: 1,
        name: '艾希',
        title: '寒冰射手',
        iconUrl: '/images/champions/ashe.jpg',
        splashUrl: '/images/champions/ashe_splash.jpg',
        position: ['ADC'],
        difficulty: 4,
        tags: ['Marksman', 'Support'],
        stats: {
          hp: 539,
          mp: 280,
          armor: 26,
          spellblock: 30,
          attackrange: 600,
          hpperlevel: 85,
          mpperlevel: 35,
          armorperlevel: 3.4,
          spellblockperlevel: 0.5,
          attackdamage: 59,
          attackdamageperlevel: 2.96,
          attackspeedperlevel: 3.33,
          movespeed: 325
        }
      },
      {
        id: 2,
        name: '盖伦',
        title: '德玛西亚之力',
        iconUrl: '/images/champions/garen.jpg',
        splashUrl: '/images/champions/garen_splash.jpg',
        position: ['Top'],
        difficulty: 5,
        tags: ['Fighter', 'Tank'],
        stats: {
          hp: 616,
          mp: 0,
          armor: 36,
          spellblock: 32,
          attackrange: 175,
          hpperlevel: 84,
          mpperlevel: 0,
          armorperlevel: 3,
          spellblockperlevel: 1.25,
          attackdamage: 66,
          attackdamageperlevel: 4.5,
          attackspeedperlevel: 2.9,
          movespeed: 340
        }
      },
      {
        id: 3,
        name: '亚索',
        title: '疾风剑豪',
        iconUrl: '/images/champions/yasuo.jpg',
        splashUrl: '/images/champions/yasuo_splash.jpg',
        position: ['Mid', 'Top'],
        difficulty: 10,
        tags: ['Fighter', 'Assassin'],
        stats: {
          hp: 490,
          mp: 100,
          armor: 30,
          spellblock: 32,
          attackrange: 175,
          hpperlevel: 87,
          mpperlevel: 0,
          armorperlevel: 3.2,
          spellblockperlevel: 1.25,
          attackdamage: 60,
          attackdamageperlevel: 3.2,
          attackspeedperlevel: 2.5,
          movespeed: 345
        }
      },
      {
        id: 4,
        name: '锤石',
        title: '魂锁典狱长',
        iconUrl: '/images/champions/thresh.jpg',
        splashUrl: '/images/champions/thresh_splash.jpg',
        position: ['Support'],
        difficulty: 7,
        tags: ['Support', 'Fighter'],
        stats: {
          hp: 560,
          mp: 274,
          armor: 28,
          spellblock: 30,
          attackrange: 450,
          hpperlevel: 95,
          mpperlevel: 44,
          armorperlevel: 0.7,
          spellblockperlevel: 0.5,
          attackdamage: 56,
          attackdamageperlevel: 2.2,
          attackspeedperlevel: 3.5,
          movespeed: 335
        }
      },
      {
        id: 5,
        name: '盲僧',
        title: '李青',
        iconUrl: '/images/champions/leesin.jpg',
        splashUrl: '/images/champions/leesin_splash.jpg',
        position: ['Jungle'],
        difficulty: 6,
        tags: ['Fighter', 'Assassin'],
        stats: {
          hp: 570,
          mp: 200,
          armor: 33,
          spellblock: 32,
          attackrange: 125,
          hpperlevel: 85,
          mpperlevel: 50,
          armorperlevel: 3.2,
          spellblockperlevel: 1.25,
          attackdamage: 68,
          attackdamageperlevel: 3.7,
          attackspeedperlevel: 3,
          movespeed: 345
        }
      }
    ]
    
    // 复制更多英雄来填充列表
    const expandedChampions: Champion[] = []
    for (let i = 0; i < 20; i++) {
      mockChampions.forEach((champion, index) => {
        expandedChampions.push({
          ...champion,
          id: champion.id + (i * mockChampions.length),
          name: `${champion.name}${i > 0 ? i + 1 : ''}`,
          title: champion.title
        })
      })
    }
    
    return expandedChampions
  }
  
  return {
    // 状态
    champions,
    loading,
    lastUpdated,
    
    // 计算属性
    allChampions,
    championsByPosition,
    getChampionById,
    getChampionsByName,
    
    // 方法
    loadChampions,
    refreshChampions,
    searchChampions
  }
})