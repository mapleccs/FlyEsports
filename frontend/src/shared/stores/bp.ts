import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiClient } from '@/shared/api/client'

export interface Champion {
  id: number
  name: string
  title: string
  iconUrl: string
  splashUrl?: string
}

export interface BPAction {
  id: string
  order: number
  type: 'ban' | 'pick'
  team: 'blue' | 'red'
  actorId?: number
  championId?: number
  champion?: Champion
  completed: boolean
  timeLimit: number
}

export interface TeamData {
  id: string
  name: string
  logo?: string
  players: Array<{
    userId: number
    username: string
    position: string
    rank?: string
    isCommander: boolean
  }>
}

export interface BPState {
  matchId: string
  roomId: string
  phase: 'ban1' | 'pick1' | 'ban2' | 'pick2' | 'completed'
  currentActionId: string | null
  actions: BPAction[]
  blueTeam: TeamData
  redTeam: TeamData
  currentUserId?: number
}

export const useBPStore = defineStore('bp', () => {
  // 状态
  const bpState = ref<BPState | null>(null)
  const selectedChampionId = ref<number | null>(null)
  const timeLeft = ref(0)
  const actionTimeLimit = ref(30) // 默认30秒每个行动
  
  // 计算属性
  const isInitialized = computed(() => !!bpState.value)
  
  const currentAction = computed(() => {
    if (!bpState.value?.currentActionId) return null
    return bpState.value.actions.find(a => a.id === bpState.value!.currentActionId) || null
  })
  
  const isMyTurn = computed(() => {
    if (!currentAction.value || !bpState.value?.currentUserId) return false
    return currentAction.value.actorId === bpState.value.currentUserId
  })
  
  const myTeam = computed(() => {
    if (!bpState.value?.currentUserId) return null
    
    const isBlueTeam = bpState.value.blueTeam.players.some(p => p.userId === bpState.value!.currentUserId)
    const isRedTeam = bpState.value.redTeam.players.some(p => p.userId === bpState.value!.currentUserId)
    
    if (isBlueTeam) return 'blue'
    if (isRedTeam) return 'red'
    return null
  })
  
  const isCommander = computed(() => {
    if (!bpState.value?.currentUserId || !myTeam.value) return false
    
    const team = myTeam.value === 'blue' ? bpState.value.blueTeam : bpState.value.redTeam
    const player = team.players.find(p => p.userId === bpState.value!.currentUserId)
    
    return player?.isCommander || false
  })
  
  const bannedIds = computed(() => {
    if (!bpState.value) return []
    return bpState.value.actions
      .filter(a => a.type === 'ban' && a.completed && a.championId)
      .map(a => a.championId!)
  })
  
  const pickedIds = computed(() => {
    if (!bpState.value) return []
    return bpState.value.actions
      .filter(a => a.type === 'pick' && a.completed && a.championId)
      .map(a => a.championId!)
  })
  
  const blueBans = computed(() => {
    if (!bpState.value) return []
    return bpState.value.actions
      .filter(a => a.type === 'ban' && a.team === 'blue' && a.completed && a.champion)
      .map(a => a.champion!)
  })
  
  const redBans = computed(() => {
    if (!bpState.value) return []
    return bpState.value.actions
      .filter(a => a.type === 'ban' && a.team === 'red' && a.completed && a.champion)
      .map(a => a.champion!)
  })
  
  const bluePicks = computed(() => {
    if (!bpState.value) return []
    return bpState.value.actions
      .filter(a => a.type === 'pick' && a.team === 'blue' && a.completed && a.champion)
      .map(a => ({ champion: a.champion!, playerId: a.actorId! }))
  })
  
  const redPicks = computed(() => {
    if (!bpState.value) return []
    return bpState.value.actions
      .filter(a => a.type === 'pick' && a.team === 'red' && a.completed && a.champion)
      .map(a => ({ champion: a.champion!, playerId: a.actorId! }))
  })
  
  const currentPhaseText = computed(() => {
    if (!currentAction.value) return 'BP已结束'
    
    const actionOrder = currentAction.value.order
    const totalActions = bpState.value?.actions.length || 20
    const teamName = currentAction.value.team === 'blue' ? '蓝方' : '红方'
    const actionText = currentAction.value.type === 'ban' ? 'BAN' : 'PICK'
    
    return `第 ${actionOrder}/${totalActions} 步 - ${teamName}${actionText}`
  })
  
  // 方法
  const initializeBP = async (initData: {
    matchId: string
    roomId: string
    blueTeam: TeamData
    redTeam: TeamData
    currentUserId?: number
  }) => {
    try {
      // 调用后端API获取BP状态
      const response = await apiClient.get(`/lobby/rooms/${initData.roomId}/bp-state`)
      
      bpState.value = {
        matchId: initData.matchId,
        roomId: initData.roomId,
        phase: response.data.phase || 'ban1',
        currentActionId: response.data.currentActionId,
        actions: response.data.actions || generateBPActions(initData.blueTeam, initData.redTeam),
        blueTeam: initData.blueTeam,
        redTeam: initData.redTeam,
        currentUserId: initData.currentUserId
      }
      
      // 设置当前行动的时间限制
      if (currentAction.value) {
        actionTimeLimit.value = currentAction.value.timeLimit
        timeLeft.value = response.data.timeLeft || actionTimeLimit.value
      }
      
      console.log('BP状态初始化完成:', bpState.value)
    } catch (error) {
      console.error('初始化BP状态失败:', error)
      throw error
    }
  }
  
  const generateBPActions = (blueTeam: TeamData, redTeam: TeamData): BPAction[] => {
    const actions: BPAction[] = []
    let order = 1
    
    // 标准BP流程：6ban + 10pick (5v5)
    // 第一轮Ban: B-R-B-R-B-R (蓝方先ban)
    for (let i = 0; i < 3; i++) {
      actions.push({
        id: `ban1_blue_${i + 1}`,
        order: order++,
        type: 'ban',
        team: 'blue',
        actorId: blueTeam.players.find(p => p.isCommander)?.userId,
        completed: false,
        timeLimit: 30
      })
      
      actions.push({
        id: `ban1_red_${i + 1}`,
        order: order++,
        type: 'ban',
        team: 'red',
        actorId: redTeam.players.find(p => p.isCommander)?.userId,
        completed: false,
        timeLimit: 30
      })
    }
    
    // 第一轮Pick: B-R-R-B-B-R-R-B-B-R (蓝方先pick)
    const positions = ['top', 'jungle', 'mid', 'adc', 'support']
    
    // 蓝方第1选
    actions.push({
      id: 'pick1_blue_1',
      order: order++,
      type: 'pick',
      team: 'blue',
      actorId: blueTeam.players[0]?.userId,
      completed: false,
      timeLimit: 30
    })
    
    // 红方第1、2选
    for (let i = 0; i < 2; i++) {
      actions.push({
        id: `pick1_red_${i + 1}`,
        order: order++,
        type: 'pick',
        team: 'red',
        actorId: redTeam.players[i]?.userId,
        completed: false,
        timeLimit: 30
      })
    }
    
    // 蓝方第2、3选
    for (let i = 1; i < 3; i++) {
      actions.push({
        id: `pick1_blue_${i + 1}`,
        order: order++,
        type: 'pick',
        team: 'blue',
        actorId: blueTeam.players[i]?.userId,
        completed: false,
        timeLimit: 30
      })
    }
    
    // 红方第3、4选
    for (let i = 2; i < 4; i++) {
      actions.push({
        id: `pick1_red_${i + 1}`,
        order: order++,
        type: 'pick',
        team: 'red',
        actorId: redTeam.players[i]?.userId,
        completed: false,
        timeLimit: 30
      })
    }
    
    // 蓝方第4、5选
    for (let i = 3; i < 5; i++) {
      actions.push({
        id: `pick1_blue_${i + 1}`,
        order: order++,
        type: 'pick',
        team: 'blue',
        actorId: blueTeam.players[i]?.userId,
        completed: false,
        timeLimit: 30
      })
    }
    
    // 红方第5选
    actions.push({
      id: 'pick1_red_5',
      order: order++,
      type: 'pick',
      team: 'red',
      actorId: redTeam.players[4]?.userId,
      completed: false,
      timeLimit: 30
    })
    
    return actions
  }
  
  const selectChampion = (champion: Champion) => {
    selectedChampionId.value = champion.id
  }
  
  const lockInSelection = async () => {
    if (!selectedChampionId.value || !currentAction.value || !bpState.value) {
      throw new Error('无效的选择状态')
    }
    
    try {
      const response = await apiClient.post(`/lobby/rooms/${bpState.value.roomId}/bp-action`, {
        actionId: currentAction.value.id,
        championId: selectedChampionId.value
      })
      
      if (response.data.success) {
        // 更新本地状态 - 实际更新会通过WebSocket接收
        selectedChampionId.value = null
        return response.data
      } else {
        throw new Error(response.data.message || '锁定失败')
      }
    } catch (error) {
      console.error('锁定选择失败:', error)
      throw error
    }
  }
  
  const updateCurrentAction = (action: BPAction) => {
    if (!bpState.value) return
    
    // 更新actions数组中的对应action
    const index = bpState.value.actions.findIndex(a => a.id === action.id)
    if (index !== -1) {
      bpState.value.actions[index] = action
    }
    
    // 更新当前action
    bpState.value.currentActionId = action.completed ? getNextActionId() : action.id
    
    // 重置选择状态
    selectedChampionId.value = null
  }
  
  const getNextActionId = (): string | null => {
    if (!bpState.value) return null
    
    const nextAction = bpState.value.actions.find(a => !a.completed)
    return nextAction?.id || null
  }
  
  const addBan = (team: 'blue' | 'red', champion: Champion) => {
    if (!currentAction.value || currentAction.value.type !== 'ban') return
    
    currentAction.value.championId = champion.id
    currentAction.value.champion = champion
    currentAction.value.completed = true
    
    updateCurrentAction(currentAction.value)
  }
  
  const addPick = (team: 'blue' | 'red', champion: Champion, playerId: number) => {
    if (!currentAction.value || currentAction.value.type !== 'pick') return
    
    currentAction.value.championId = champion.id
    currentAction.value.champion = champion
    currentAction.value.actorId = playerId
    currentAction.value.completed = true
    
    updateCurrentAction(currentAction.value)
  }
  
  const updateTimer = (newTimeLeft: number) => {
    timeLeft.value = newTimeLeft
  }
  
  const resetBP = () => {
    bpState.value = null
    selectedChampionId.value = null
    timeLeft.value = 0
    actionTimeLimit.value = 30
  }
  
  return {
    // 状态
    bpState,
    selectedChampionId,
    timeLeft,
    actionTimeLimit,
    
    // 计算属性
    isInitialized,
    currentAction,
    isMyTurn,
    myTeam,
    isCommander,
    bannedIds,
    pickedIds,
    blueBans,
    redBans,
    bluePicks,
    redPicks,
    currentPhaseText,
    
    // 方法
    initializeBP,
    selectChampion,
    lockInSelection,
    updateCurrentAction,
    addBan,
    addPick,
    updateTimer,
    resetBP
  }
})