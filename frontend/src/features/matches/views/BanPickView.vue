<template>
  <layout-default>
    <div class="bp-room" v-if="match">
      <!-- 顶部队伍信息条 -->
      <div class="teams-header">
        <div class="team-info-card blue-card">
          <div class="team-logo">
            <img :src="blueTeam?.logo || 'https://zhihuiss2024.oss-cn-nanjing.aliyuncs.com/img/default-logo.png'" 
                 :alt="blueTeam?.name" />
          </div>
          <div class="team-name">{{ blueTeam?.name || '蓝队' }}</div>
          <div class="team-status" :class="{ active: bpStore.currentAction?.team === 'blue' }">
            {{ getTeamStatusText('blue') }}
          </div>
        </div>
        
        <div class="versus-section">
          <div class="vs-text">VS</div>
          <div class="match-info">
            <div class="current-phase">{{ getCurrentPhaseText() }}</div>
          </div>
        </div>
        
        <div class="team-info-card red-card">
          <div class="team-status" :class="{ active: bpStore.currentAction?.team === 'red' }">
            {{ getTeamStatusText('red') }}
          </div>
          <div class="team-name">{{ redTeam?.name || '红队' }}</div>
          <div class="team-logo">
            <img :src="redTeam?.logo || 'https://zhihuiss2024.oss-cn-nanjing.aliyuncs.com/img/default-logo.png'" 
                 :alt="redTeam?.name" />
          </div>
        </div>
      </div>

      <!-- BP主布局 -->
      <div class="bp-layout">
        <!-- 左侧：蓝队BP区域 -->
        <div class="team-section blue-team">
          <BPTeamDisplay
            :team-data="blueTeam"
            side="blue"
            :picks="bpStore.bluePicks"
            :bans="bpStore.blueBans"
            :actions="bpStore.actions || []"
            :current-action="bpStore.currentAction"
            :compact-mode="true"
          />
        </div>

        <!-- 中间：英雄选择区域 -->
        <div class="champion-section">
          <BPChampionGrid
            :champions="championStore.allChampions"
            :banned-ids="bpStore.bannedIds"
            :picked-ids="bpStore.pickedIds"
            :selected-champion-id="bpStore.selectedChampionId"
            @champion-select="handleChampionSelect"
          />
        </div>

        <!-- 右侧：红队BP区域 -->
        <div class="team-section red-team">
          <BPTeamDisplay
            :team-data="redTeam"
            side="red"
            :picks="bpStore.redPicks"
            :bans="bpStore.redBans"
            :actions="bpStore.actions || []"
            :current-action="bpStore.currentAction"
            :compact-mode="true"
          />
        </div>
      </div>

      <!-- 底部：操作栏 -->
      <div class="bp-footer">
        <BPActionBar
          :is-connected="websocketStore.isConnected"
          :is-connecting="websocketStore.isConnecting"
          :has-error="websocketStore.hasError"
          @lock-selection="handleLockSelection"
        />
      </div>

      <!-- BP阶段时间倒计时 -->
      <div class="timer-overlay" v-if="bpStore.timeLeft > 0">
        <div class="timer-circle">
          <div class="timer-text">{{ bpStore.timeLeft }}s</div>
          <svg class="timer-ring" width="80" height="80">
            <circle
              cx="40"
              cy="40"
              r="35"
              stroke="#3498db"
              stroke-width="6"
              fill="transparent"
              :stroke-dasharray="timerCircumference"
              :stroke-dashoffset="timerOffset"
              class="timer-progress"
            />
          </svg>
        </div>
      </div>
    </div>

    <!-- 比赛未找到 -->
    <div v-else-if="!loading" class="not-found">
      <a-result
        status="404"
        title="比赛不存在"
        sub-title="未找到指定的比赛或BP阶段尚未开始"
      >
        <template #extra>
          <a-button type="primary" @click="$router.go(-1)">
            返回上一页
          </a-button>
        </template>
      </a-result>
    </div>

    <!-- 加载状态 -->
    <div v-else class="loading-container">
      <a-spin size="large" />
      <p>加载BP界面中...</p>
    </div>
  </layout-default>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import LayoutDefault from '@/shared/components/layouts/LayoutDefault.vue'
import BPTeamDisplay from '@/features/matches/components/bp/BPTeamDisplay.vue'
import BPChampionGrid from '@/features/matches/components/bp/BPChampionGrid.vue'
import BPActionBar from '@/features/matches/components/bp/BPActionBar.vue'
import { useBPStore } from '@/shared/stores/bp'
import { useChampionStore } from '@/shared/stores/champion'
import { useWebSocketStore } from '@/shared/stores/websocket'
import { useAuthStore } from '@/shared/stores/auth'
import { tournamentApi } from '@/shared/api/tournaments'

// 路由和状态管理
const route = useRoute()
const router = useRouter()
const bpStore = useBPStore()
const championStore = useChampionStore()
const websocketStore = useWebSocketStore()
const authStore = useAuthStore()

// 响应式数据
const loading = ref(true)
const match = ref(null)
const blueTeam = ref(null)
const redTeam = ref(null)

// 计算属性
const timerCircumference = computed(() => 2 * Math.PI * 35)
const timerOffset = computed(() => {
  const total = bpStore.actionTimeLimit
  const remaining = bpStore.timeLeft
  const progress = remaining / total
  return timerCircumference.value * (1 - progress)
})

// 方法
const loadMatchData = async () => {
  try {
    loading.value = true
    const matchId = route.params.matchId as string
    
    console.log('开始加载比赛数据，matchId:', matchId)
    
    // 获取比赛详情
    const matchResponse = await tournamentApi.getMatch(matchId)
    console.log('比赛API响应:', matchResponse)
    
    // API可能直接返回数据，也可能包装在data字段中
    const matchData = matchResponse.data || matchResponse
    
    if (!matchData) {
      console.error('比赛数据为空:', matchResponse)
      message.error('无法获取比赛数据')
      router.go(-1)
      return
    }
    
    match.value = matchData
    console.log('设置比赛数据:', match.value)
    
    // 检查是否为BP阶段 - 允许ready状态用于测试
    const allowedStatuses = ['in_progress', 'ready', 'bp']
    const allowedPhases = ['bp', 'commander_voting', 'ready']
    
    if (!allowedStatuses.includes(match.value.status) && !allowedPhases.includes(match.value.phase)) {
      console.log('比赛状态检查失败:', { status: match.value.status, phase: match.value.phase })
      message.warning(`当前比赛状态: ${match.value.status}, 阶段: ${match.value.phase || '未知'}`)
      // 暂时不强制跳转，允许用户查看BP界面
      // router.go(-1)
      // return
    }
    
    // 初始化队伍数据 - 根据实际的Match数据结构
    blueTeam.value = {
      id: match.value.blue_side_id,
      name: match.value.blue_side_name || '蓝队',
      logo: 'https://zhihuiss2024.oss-cn-nanjing.aliyuncs.com/img/default-logo.png',
      players: [
        // 创建5个默认选手位置
        { userId: 1, username: '上单选手', position: 'top', rank: '钻石', isCommander: false },
        { userId: 2, username: '打野选手', position: 'jungle', rank: '钻石', isCommander: true },
        { userId: 3, username: '中单选手', position: 'mid', rank: '钻石', isCommander: false },
        { userId: 4, username: 'ADC选手', position: 'adc', rank: '钻石', isCommander: false },
        { userId: 5, username: '辅助选手', position: 'support', rank: '钻石', isCommander: false }
      ]
    }
    redTeam.value = {
      id: match.value.red_side_id,
      name: match.value.red_side_name || '红队',
      logo: 'https://zhihuiss2024.oss-cn-nanjing.aliyuncs.com/img/default-logo.png',
      players: [
        // 创建5个默认选手位置
        { userId: 6, username: '上单选手', position: 'top', rank: '钻石', isCommander: false },
        { userId: 7, username: '打野选手', position: 'jungle', rank: '钻石', isCommander: true },
        { userId: 8, username: '中单选手', position: 'mid', rank: '钻石', isCommander: false },
        { userId: 9, username: 'ADC选手', position: 'adc', rank: '钻石', isCommander: false },
        { userId: 10, username: '辅助选手', position: 'support', rank: '钻石', isCommander: false }
      ]
    }
    
    // 初始化BP状态 - 使用matchId作为roomId
    await bpStore.initializeBP({
      matchId: matchId,
      roomId: matchId, // 直接使用matchId作为roomId
      blueTeam: blueTeam.value,
      redTeam: redTeam.value,
      currentUserId: authStore.user?.id
    })
    
    // 加载英雄数据
    await championStore.loadChampions()
    
  } catch (error) {
    console.error('加载BP数据失败:', error)
    message.error('加载BP数据失败')
    router.go(-1)
  } finally {
    loading.value = false
  }
}

const initializeWebSocket = async () => {
  try {
    const roomId = match.value?.id
    if (!roomId) return
    
    // 连接WebSocket
    await websocketStore.connect()
    
    // 订阅BP房间
    websocketStore.subscribe(`bp_room_${roomId}`, handleBPUpdate)
    
    console.log('WebSocket连接已建立，订阅BP房间:', roomId)
  } catch (error) {
    console.error('WebSocket连接失败:', error)
    message.error('实时连接失败，BP状态可能不会及时更新')
  }
}

const handleBPUpdate = (data: any) => {
  console.log('收到BP更新:', data)
  
  switch (data.type) {
    case 'action_update':
      bpStore.updateCurrentAction(data.action)
      break
    case 'champion_banned':
      bpStore.addBan(data.team, data.champion)
      break
    case 'champion_picked':
      bpStore.addPick(data.team, data.champion, data.player_id)
      break
    case 'timer_update':
      bpStore.updateTimer(data.time_left)
      break
    case 'bp_complete':
      handleBPComplete(data)
      break
    case 'error':
      message.error(data.message)
      break
  }
}

const handleChampionSelect = (champion: any) => {
  if (!bpStore.isMyTurn) {
    message.warning('当前不是您的操作回合')
    return
  }
  
  if (bpStore.bannedIds.includes(champion.id) || bpStore.pickedIds.includes(champion.id)) {
    message.warning('该英雄已被禁用或选择')
    return
  }
  
  bpStore.selectChampion(champion)
}

const handleLockSelection = async () => {
  if (!bpStore.selectedChampionId) {
    message.warning('请先选择一个英雄')
    return
  }
  
  try {
    await bpStore.lockInSelection()
    message.success('英雄已锁定')
  } catch (error) {
    console.error('锁定英雄失败:', error)
    message.error('锁定英雄失败，请重试')
  }
}

const handleBPComplete = (data: any) => {
  message.success('BP阶段完成！')
  
  // 延迟跳转到比赛界面
  setTimeout(() => {
    router.push({
      name: 'MatchRoom',
      params: {
        tournamentId: route.params.tournamentId,
        matchId: route.params.matchId
      }
    })
  }, 3000)
}

// 新增方法：获取队伍状态文本
const getTeamStatusText = (side: 'blue' | 'red') => {
  if (bpStore.currentAction && bpStore.currentAction.team === side) {
    return bpStore.currentAction.type === 'ban' ? '正在禁用' : '正在选择'
  }
  return '等待中'
}

// 新增方法：获取当前阶段文本
const getCurrentPhaseText = () => {
  if (!bpStore.currentAction) return 'BP准备中'
  const actionOrder = bpStore.currentAction.order
  if (actionOrder <= 6) return `禁用阶段 ${actionOrder}/6`
  return `选择阶段 ${actionOrder - 6}/10`
}

// 生命周期
onMounted(async () => {
  await loadMatchData()
  if (match.value) {
    await initializeWebSocket()
  }
})

onUnmounted(() => {
  // 清理WebSocket连接
  const roomId = match.value?.id
  if (roomId) {
    websocketStore.unsubscribe(`bp_room_${roomId}`)
  }
  
  // 清理BP状态
  bpStore.resetBP()
})

// 监听路由变化
watch(() => route.params.matchId, async (newMatchId) => {
  if (newMatchId) {
    await loadMatchData()
    if (match.value) {
      await initializeWebSocket()
    }
  }
})
</script>

<style scoped>
.bp-room {
  height: 100vh;
  background: linear-gradient(135deg, #0f3460 0%, #16213e 50%, #1a1a2e 100%);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 顶部队伍信息条 */
.teams-header {
  height: 80px;
  background: rgba(22, 33, 62, 0.95);
  border-bottom: 2px solid rgba(52, 152, 219, 0.3);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  flex-shrink: 0;
}

.team-info-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 20px;
  background: rgba(15, 52, 96, 0.6);
  border-radius: 12px;
  border: 2px solid transparent;
  transition: all 0.3s ease;
  min-width: 200px;
}

.blue-card {
  border-color: rgba(52, 152, 219, 0.4);
  background: linear-gradient(135deg, rgba(52, 152, 219, 0.15) 0%, rgba(41, 128, 185, 0.05) 100%);
}

.red-card {
  border-color: rgba(231, 76, 60, 0.4);
  background: linear-gradient(135deg, rgba(231, 76, 60, 0.05) 0%, rgba(192, 57, 43, 0.15) 100%);
}

.red-card .team-name {
  text-align: right;
}

.team-info-card .team-logo {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  overflow: hidden;
  border: 2px solid rgba(255, 255, 255, 0.3);
  background: rgba(15, 52, 96, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.team-info-card .team-logo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.team-info-card .team-name {
  font-weight: 700;
  font-size: 18px;
  color: #ecf0f1;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
  flex: 1;
  display: flex;
  align-items: center;
}

.team-info-card .team-status {
  font-size: 13px;
  color: rgba(236, 240, 241, 0.7);
  padding: 4px 12px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.1);
  transition: all 0.3s ease;
  white-space: nowrap;
  display: flex;
  align-items: center;
}

.team-status.active {
  background: rgba(52, 152, 219, 0.3);
  color: #3498db;
  animation: pulse-status 1.5s infinite;
}

@keyframes pulse-status {
  0% { background: rgba(52, 152, 219, 0.3); }
  50% { background: rgba(52, 152, 219, 0.5); }
  100% { background: rgba(52, 152, 219, 0.3); }
}

.versus-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.vs-text {
  font-size: 24px;
  font-weight: 900;
  color: #ecf0f1;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
  letter-spacing: 2px;
}

.match-info {
  text-align: center;
}

.current-phase {
  font-size: 14px;
  color: #3498db;
  background: rgba(52, 152, 219, 0.2);
  padding: 4px 12px;
  border-radius: 16px;
  border: 1px solid rgba(52, 152, 219, 0.3);
  font-weight: 500;
}

.bp-layout {
  flex: 1;
  display: grid;
  grid-template-columns: 300px 1fr 300px;
  gap: 16px;
  padding: 16px;
  overflow: hidden;
}

.team-section {
  background: rgba(22, 33, 62, 0.8);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.blue-team {
  border: 2px solid rgba(11, 196, 226, 0.3);
}

.red-team {
  border: 2px solid rgba(232, 65, 56, 0.3);
}

.champion-section {
  background: rgba(15, 52, 96, 0.9);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  border: 2px solid rgba(52, 152, 219, 0.2);
}

.bp-footer {
  height: 80px;
  background: rgba(22, 33, 62, 0.95);
  border-top: 2px solid rgba(52, 152, 219, 0.3);
  backdrop-filter: blur(10px);
}

.timer-overlay {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 1000;
}

.timer-circle {
  position: relative;
  width: 80px;
  height: 80px;
}

.timer-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 18px;
  font-weight: bold;
  color: #3498db;
  text-shadow: 0 0 10px rgba(52, 152, 219, 0.5);
}

.timer-ring {
  transform: rotate(-90deg);
}

.timer-progress {
  transition: stroke-dashoffset 1s linear;
  filter: drop-shadow(0 0 5px rgba(52, 152, 219, 0.6));
}

.not-found,
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  color: #ecf0f1;
}

.loading-container p {
  margin-top: 16px;
  font-size: 16px;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .bp-layout {
    grid-template-columns: 250px 1fr 250px;
    gap: 12px;
    padding: 12px;
  }
  
  .teams-header {
    padding: 0 16px;
  }
  
  .team-info-card {
    min-width: 180px;
    padding: 10px 16px;
  }
  
  .team-info-card .team-name {
    font-size: 16px;
  }
}

@media (max-width: 768px) {
  .teams-header {
    height: 140px;
    flex-direction: column;
    padding: 12px;
    gap: 12px;
  }
  
  .team-info-card {
    min-width: 160px;
    padding: 8px 12px;
    width: 100%;
    max-width: 280px;
  }
  
  .team-info-card .team-logo {
    width: 36px;
    height: 36px;
  }
  
  .team-info-card .team-name {
    font-size: 14px;
    flex: 1;
    min-width: 0;
  }
  
  .team-info-card .team-status {
    font-size: 11px;
    padding: 3px 8px;
  }
  
  .vs-text {
    font-size: 18px;
  }
  
  .current-phase {
    font-size: 12px;
    padding: 3px 8px;
  }
  
  .versus-section {
    order: -1;
    margin-bottom: 8px;
  }
  
  .bp-layout {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr auto;
    gap: 8px;
    padding: 8px;
  }
  
  .team-section {
    height: 200px;
  }
  
  .champion-section {
    min-height: 400px;
  }
  
  .timer-overlay {
    top: 140px;
    right: 10px;
  }
  
  .timer-circle {
    width: 60px;
    height: 60px;
  }
  
  .timer-text {
    font-size: 14px;
  }
}
</style>