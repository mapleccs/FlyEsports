<template>
  <div class="team-display" :class="{ compact: compactMode }">
    <!-- 队伍头部 (非紧凑模式下显示) -->
    <div v-if="!compactMode" class="team-header" :class="side === 'blue' ? 'blue-header' : 'red-header'">
      <div class="team-info">
        <div class="team-logo">
          <img :src="teamLogoUrl" :alt="teamData.name" @error="handleLogoError" />
        </div>
        <div class="team-details">
          <div class="team-name">{{ teamData.name }}</div>
          <div class="team-status">{{ getTeamStatus() }}</div>
        </div>
      </div>

      <!-- 禁用英雄区域 -->
      <div class="bans-section">
        <div class="bans-label">禁用英雄</div>
        <div class="bans-container">
          <div v-for="(ban, i) in displayBans" :key="i" class="ban-slot">
            <div class="ban-placeholder" v-if="!ban">
              <StopOutlined />
            </div>
            <div v-else class="ban-champion">
              <img :src="ban.iconUrl" :alt="ban.name" @error="handleBanImageError" />
              <div class="ban-overlay">
                <StopOutlined />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 禁用英雄区域 (紧凑模式下单独显示) -->
    <div v-if="compactMode" class="compact-bans-section" :class="side === 'blue' ? 'blue-section' : 'red-section'">
      <div class="bans-header">
        <div class="bans-label">禁用英雄</div>
        <div class="bans-count">{{ bansCount }}/{{ maxBans }}</div>
      </div>
      <div class="bans-container">
        <div v-for="(ban, i) in displayBans" :key="i" class="ban-slot">
          <div class="ban-placeholder" v-if="!ban">
            <StopOutlined />
          </div>
          <div v-else class="ban-champion">
            <img :src="ban.iconUrl" :alt="ban.name" @error="handleBanImageError" />
            <div class="ban-overlay">
              <StopOutlined />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 选手列表 -->
    <div class="players-container">
      <div class="players-header">
        <div class="header-title">队伍阵容</div>
        <div class="header-indicator" :class="side">
          {{ side === 'blue' ? '蓝方' : '红方' }}
        </div>
      </div>
      
      <div
        v-for="(player, index) in teamData.players"
        :key="player.userId"
        class="player-display"
        :class="{
          current: isCurrentPlayer(player.userId),
          commander: player.isCommander,
          [getPositionClass(index)]: true
        }"
      >
        <!-- 位置标识 -->
        <div class="player-position">
          <div class="position-icon">{{ getPositionText(index) }}</div>
          <div class="position-line" :class="getPositionClass(index)"></div>
        </div>
        
        <!-- 玩家信息 -->
        <div class="player-info">
          <div class="player-name">
            {{ player.username }}
            <CrownOutlined v-if="player.isCommander" class="commander-icon" />
          </div>
          <div class="player-meta">
            <div class="player-rank">{{ player.rank || '钻石' }}</div>
            <div class="player-role">{{ getPositionName(index) }}</div>
          </div>
        </div>
        
        <!-- 选择的英雄 -->
        <div class="picked-champion">
          <div class="champion-container">
            <div class="champion-placeholder" v-if="!getPickForPlayer(player.userId)">
              <UserOutlined />
            </div>
            <div v-else class="champion-picked">
              <img 
                :src="getPickForPlayer(player.userId)!.iconUrl" 
                :alt="getPickForPlayer(player.userId)!.name"
                @error="handleChampionImageError"
              />
              <div class="champion-name-overlay">
                {{ getPickForPlayer(player.userId)!.name }}
              </div>
            </div>
            
            <!-- 当前选择状态 -->
            <div class="player-status" v-if="isCurrentPlayer(player.userId)">
              <div class="status-indicator"></div>
              <div class="status-text">选择中</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- BP进度时间轴 -->
    <div class="bp-timeline">
      <div class="timeline-header">
        <div class="timeline-title">BP进度</div>
        <div class="timeline-phase">{{ getCurrentPhase() }}</div>
      </div>
      <div class="timeline-content">
        <div class="phase-indicator">
          <div class="phase-step" :class="{ active: getCurrentStep() >= 1, completed: getCurrentStep() > 6 }">
            <div class="step-number">1</div>
            <div class="step-label">禁用阶段</div>
          </div>
          <div class="phase-connector" :class="{ active: getCurrentStep() > 6 }"></div>
          <div class="phase-step" :class="{ active: getCurrentStep() > 6 }">
            <div class="step-number">2</div>
            <div class="step-label">选择阶段</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 扩展统计信息 -->
    <div class="team-stats-extended">
      <div class="stats-header">
        <div class="stats-title">队伍数据</div>
      </div>
      <div class="stats-grid">
        <div class="stat-item">
          <div class="stat-icon">🚫</div>
          <div class="stat-content">
            <div class="stat-value">{{ bansCount }}/{{ maxBans }}</div>
            <div class="stat-label">禁用</div>
          </div>
        </div>
        <div class="stat-item">
          <div class="stat-icon">⚔️</div>
          <div class="stat-content">
            <div class="stat-value">{{ picksCount }}/5</div>
            <div class="stat-label">选择</div>
          </div>
        </div>
        <div class="stat-item">
          <div class="stat-icon">👑</div>
          <div class="stat-content">
            <div class="stat-value">{{ getCommanderName() }}</div>
            <div class="stat-label">指挥官</div>
          </div>
        </div>
        <div class="stat-item">
          <div class="stat-icon">⏱️</div>
          <div class="stat-content">
            <div class="stat-value">{{ getAverageRank() }}</div>
            <div class="stat-label">平均段位</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 战术笔记区域 -->
    <div class="tactical-notes">
      <div class="notes-header">
        <div class="notes-title">战术备忘</div>
        <div class="notes-indicator" :class="side"></div>
      </div>
      <div class="notes-content">
        <div class="note-item">
          <div class="note-icon">💡</div>
          <div class="note-text">重点关注对方{{ getBanTarget() }}</div>
        </div>
        <div class="note-item">
          <div class="note-icon">🎯</div>
          <div class="note-text">推荐选择强势组合英雄</div>
        </div>
        <div class="note-item">
          <div class="note-icon">⚡</div>
          <div class="note-text">注意阵容平衡性</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { 
  StopOutlined, 
  CrownOutlined, 
  UserOutlined 
} from '@ant-design/icons-vue'
import type { Champion } from '@/shared/stores/champion'

// Props
interface Props {
  teamData: {
    id: string
    name: string
    logo?: string
    players: Array<{
      userId: number
      username: string
      position?: string
      rank?: string
      isCommander: boolean
    }>
  }
  side: 'blue' | 'red'
  picks: Array<{ champion: Champion; playerId: number }>
  bans: Champion[]
  actions: Array<{
    id: string
    order: number
    type: 'ban' | 'pick'
    team: 'blue' | 'red'
    actorId?: number
    championId?: number
    champion?: Champion
    completed: boolean
  }>
  currentAction: {
    id: string
    order: number
    type: 'ban' | 'pick'
    team: 'blue' | 'red'
    actorId?: number
    championId?: number
    champion?: Champion
    completed: boolean
  } | null
  compactMode?: boolean
}

const props = defineProps<Props>()

// 位置映射
const positions = ['top', 'jungle', 'mid', 'adc', 'support']
const maxBans = 5 // 每队最多5个ban位

// 计算属性
const teamLogoUrl = computed(() => {
  return props.teamData.logo || 'https://zhihuiss2024.oss-cn-nanjing.aliyuncs.com/img/default-logo.png'
})

const displayBans = computed(() => {
  const bans = [...props.bans]
  // 补齐到最大ban数
  while (bans.length < maxBans) {
    bans.push(null as any)
  }
  return bans.slice(0, maxBans)
})

const picksCount = computed(() => props.picks.length)
const bansCount = computed(() => props.bans.length)

// 方法
const getPositionText = (index: number) => {
  const positionMap = {
    0: '上',
    1: '野',
    2: '中',
    3: 'AD',
    4: '辅'
  }
  return positionMap[index as keyof typeof positionMap] || (index + 1).toString()
}

const getPositionClass = (index: number) => {
  return positions[index] || 'unknown'
}

const getPickForPlayer = (userId: number) => {
  const pick = props.picks.find(p => p.playerId === userId)
  return pick ? pick.champion : null
}

const isCurrentPlayer = (userId: number) => {
  return props.currentAction?.actorId === userId && !props.currentAction?.completed
}

const getTeamStatus = () => {
  if (props.currentAction && props.currentAction.team === props.side) {
    return props.currentAction.type === 'ban' ? '正在禁用' : '正在选择'
  }
  return '等待中'
}

const handleLogoError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.src = 'https://zhihuiss2024.oss-cn-nanjing.aliyuncs.com/img/default-logo.png'
}

const handleBanImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.src = '/images/default-champion.png'
}

const handleChampionImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.src = '/images/default-champion.png'
}

// 新增方法：获取位置全称
const getPositionName = (index: number) => {
  const positionNames = ['上单', '打野', '中单', 'ADC', '辅助']
  return positionNames[index] || '未知'
}

// 新增方法：获取当前BP阶段
const getCurrentPhase = () => {
  if (!props.currentAction) return 'BP准备'
  return props.currentAction.type === 'ban' ? '禁用阶段' : '选择阶段'
}

// 新增方法：获取当前步骤
const getCurrentStep = () => {
  if (!props.currentAction) return 0
  return props.currentAction.order
}

// 新增方法：获取指挥官名称
const getCommanderName = () => {
  const commander = props.teamData.players.find(p => p.isCommander)
  return commander ? commander.username : '未设置'
}

// 新增方法：获取平均段位
const getAverageRank = () => {
  // 简化实现，实际应该有段位计算逻辑
  return '钻石'
}

// 新增方法：获取Ban位目标建议
const getBanTarget = () => {
  const banTargets = ['ADC英雄', '中单法师', '打野英雄', '上单坦克', '辅助英雄']
  return banTargets[Math.floor(Math.random() * banTargets.length)]
}
</script>

<style scoped>
.team-display {
  background: rgba(22, 33, 62, 0.95);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
  height: 100%;
  display: flex;
  flex-direction: column;
  backdrop-filter: blur(10px);
}

.team-display.compact {
  background: rgba(22, 33, 62, 0.8);
}

/* 紧凑模式下的禁用英雄区域 */
.compact-bans-section {
  padding: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(15, 52, 96, 0.3);
}

.compact-bans-section.blue-section {
  background: linear-gradient(135deg, rgba(52, 152, 219, 0.2) 0%, rgba(41, 128, 185, 0.05) 100%);
  border-bottom-color: rgba(52, 152, 219, 0.3);
}

.compact-bans-section.red-section {
  background: linear-gradient(135deg, rgba(231, 76, 60, 0.05) 0%, rgba(192, 57, 43, 0.2) 100%);
  border-bottom-color: rgba(231, 76, 60, 0.3);
}

.bans-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.bans-header .bans-label {
  font-size: 13px;
  font-weight: 600;
  opacity: 0.9;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #ecf0f1;
}

.bans-count {
  font-size: 12px;
  color: rgba(236, 240, 241, 0.7);
  background: rgba(255, 255, 255, 0.1);
  padding: 2px 8px;
  border-radius: 12px;
}

.compact-bans-section .bans-container {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.compact-bans-section .ban-slot {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  overflow: hidden;
  position: relative;
  border: 2px solid rgba(255, 255, 255, 0.2);
  background: rgba(15, 52, 96, 0.6);
  transition: all 0.3s ease;
}

.compact-bans-section .ban-slot:hover {
  transform: scale(1.05);
  border-color: rgba(255, 255, 255, 0.4);
}

/* 队伍头部 */
.team-header {
  padding: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: relative;
  z-index: 1;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.blue-header {
  background: linear-gradient(135deg, rgba(52, 152, 219, 0.3) 0%, rgba(41, 128, 185, 0.1) 100%);
  border-bottom-color: rgba(52, 152, 219, 0.5);
}

.red-header {
  background: linear-gradient(135deg, rgba(231, 76, 60, 0.1) 0%, rgba(192, 57, 43, 0.3) 100%);
  border-bottom-color: rgba(231, 76, 60, 0.5);
}

.team-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.team-logo {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  overflow: hidden;
  border: 2px solid rgba(255, 255, 255, 0.2);
  background: rgba(15, 52, 96, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
}

.team-logo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.team-details {
  display: flex;
  flex-direction: column;
}

.team-name {
  font-weight: 700;
  font-size: 16px;
  color: #ecf0f1;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
}

.team-status {
  font-size: 12px;
  opacity: 0.8;
  color: rgba(236, 240, 241, 0.7);
}

/* 禁用英雄区域 */
.bans-section {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.bans-label {
  font-size: 11px;
  opacity: 0.8;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: rgba(236, 240, 241, 0.6);
}

.bans-container {
  display: flex;
  gap: 6px;
}

.ban-slot {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  overflow: hidden;
  position: relative;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(15, 52, 96, 0.6);
}

.ban-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(231, 76, 60, 0.5);
  font-size: 16px;
}

.ban-champion {
  position: relative;
  width: 100%;
  height: 100%;
}

.ban-champion img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.ban-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(231, 76, 60, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 14px;
}

/* 选手列表 */
.players-container {
  padding: 0;
  display: flex;
  flex-direction: column;
}

.players-header {
  padding: 12px 16px;
  background: linear-gradient(135deg, rgba(15, 52, 96, 0.6) 0%, rgba(22, 33, 62, 0.6) 100%);
  border-bottom: 1px solid rgba(200, 170, 110, 0.2);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  color: #c8aa6e;
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.header-indicator {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 10px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.header-indicator.blue {
  background: rgba(52, 152, 219, 0.2);
  color: #3498db;
  border: 1px solid rgba(52, 152, 219, 0.4);
}

.header-indicator.red {
  background: rgba(231, 76, 60, 0.2);
  color: #e74c3c;
  border: 1px solid rgba(231, 76, 60, 0.4);
}

.player-display {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: linear-gradient(135deg, rgba(15, 52, 96, 0.3) 0%, rgba(22, 33, 62, 0.3) 100%);
  border-bottom: 1px solid rgba(200, 170, 110, 0.1);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.player-display:hover {
  background: linear-gradient(135deg, rgba(15, 52, 96, 0.5) 0%, rgba(22, 33, 62, 0.5) 100%);
}

.player-display.current {
  background: linear-gradient(135deg, rgba(52, 152, 219, 0.2) 0%, rgba(41, 128, 185, 0.2) 100%);
  border-left: 3px solid #3498db;
  box-shadow: inset 0 0 20px rgba(52, 152, 219, 0.2);
  animation: pulse-glow 1.5s infinite;
}

.player-display.commander {
  border-right: 3px solid #f1c40f;
  box-shadow: inset 0 0 15px rgba(241, 196, 15, 0.1);
}

@keyframes pulse-glow {
  0% { background: linear-gradient(135deg, rgba(52, 152, 219, 0.2) 0%, rgba(41, 128, 185, 0.2) 100%); }
  50% { background: linear-gradient(135deg, rgba(52, 152, 219, 0.3) 0%, rgba(41, 128, 185, 0.3) 100%); }
  100% { background: linear-gradient(135deg, rgba(52, 152, 219, 0.2) 0%, rgba(41, 128, 185, 0.2) 100%); }
}

.player-position {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-right: 12px;
  position: relative;
}

.position-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: linear-gradient(135deg, #c8aa6e 0%, #96621d 100%);
  color: #1e2328;
  font-weight: bold;
  font-size: 12px;
  box-shadow: 
    0 2px 8px rgba(200, 170, 110, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.position-line {
  width: 2px;
  height: 20px;
  margin-top: 4px;
  border-radius: 1px;
  opacity: 0.6;
}

.position-line.top { background: linear-gradient(to bottom, #f39c12, #d35400); }
.position-line.jungle { background: linear-gradient(to bottom, #27ae60, #16a085); }
.position-line.mid { background: linear-gradient(to bottom, #3498db, #2980b9); }
.position-line.adc { background: linear-gradient(to bottom, #e74c3c, #c0392b); }
.position-line.support { background: linear-gradient(to bottom, #9b59b6, #8e44ad); }

.player-info {
  flex: 1;
  margin-right: 12px;
}

.player-name {
  font-size: 14px;
  font-weight: 600;
  color: #c8aa6e;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.commander-icon {
  color: #f1c40f;
  font-size: 14px;
  filter: drop-shadow(0 0 4px rgba(241, 196, 15, 0.5));
}

.player-meta {
  display: flex;
  gap: 8px;
  align-items: center;
}

.player-rank {
  font-size: 10px;
  color: #0596aa;
  background: rgba(5, 150, 170, 0.2);
  padding: 2px 6px;
  border-radius: 8px;
  border: 1px solid rgba(5, 150, 170, 0.3);
  font-weight: 500;
}

.player-role {
  font-size: 10px;
  color: rgba(200, 170, 110, 0.8);
  background: rgba(200, 170, 110, 0.1);
  padding: 2px 6px;
  border-radius: 8px;
  border: 1px solid rgba(200, 170, 110, 0.2);
}

.picked-champion {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  overflow: hidden;
  border: 2px solid rgba(255, 255, 255, 0.2);
  position: relative;
  background: rgba(15, 52, 96, 0.6);
}

.champion-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(236, 240, 241, 0.3);
  font-size: 20px;
}

.champion-picked {
  position: relative;
  width: 100%;
  height: 100%;
}

.champion-picked img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.champion-name-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(0, 0, 0, 0.8);
  color: white;
  font-size: 9px;
  padding: 2px;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.player-status {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  background: rgba(52, 152, 219, 0.9);
  color: white;
  font-size: 9px;
  padding: 2px;
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
}

.status-indicator {
  width: 6px;
  height: 6px;
  background: white;
  border-radius: 50%;
  animation: blink 1.5s infinite;
}

@keyframes blink {
  0% { opacity: 0.3; }
  50% { opacity: 1; }
  100% { opacity: 0.3; }
}

/* 队伍统计 */
.team-stats {
  padding: 12px 16px;
  background: rgba(15, 52, 96, 0.3);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.stat-label {
  color: rgba(236, 240, 241, 0.7);
}

.stat-value {
  color: #ecf0f1;
  font-weight: 600;
}

/* 滚动条样式 */
.players-container::-webkit-scrollbar {
  width: 4px;
}

.players-container::-webkit-scrollbar-thumb {
  background: rgba(52, 152, 219, 0.5);
  border-radius: 2px;
}

.players-container::-webkit-scrollbar-track {
  background: rgba(15, 52, 96, 0.2);
}

/* BP时间线样式 */
.bp-timeline {
  padding: 16px;
  background: linear-gradient(135deg, rgba(15, 52, 96, 0.4) 0%, rgba(22, 33, 62, 0.4) 100%);
  border-top: 1px solid rgba(200, 170, 110, 0.2);
  border-bottom: 1px solid rgba(200, 170, 110, 0.1);
}

.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.timeline-title {
  color: #c8aa6e;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.timeline-phase {
  background: rgba(52, 152, 219, 0.2);
  color: #3498db;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 10px;
  border: 1px solid rgba(52, 152, 219, 0.4);
}

.timeline-content {
  width: 100%;
}

.phase-indicator {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.phase-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  transition: all 0.3s ease;
}

.phase-step.active .step-number {
  background: linear-gradient(135deg, #c8aa6e 0%, #96621d 100%);
  border-color: #c8aa6e;
}

.phase-step.completed .step-number {
  background: linear-gradient(135deg, #27ae60 0%, #16a085 100%);
  border-color: #27ae60;
}

.step-number {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  border: 2px solid rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: bold;
  color: #ecf0f1;
  margin-bottom: 6px;
  transition: all 0.3s ease;
}

.step-label {
  font-size: 10px;
  color: rgba(236, 240, 241, 0.7);
  text-align: center;
}

.phase-connector {
  height: 2px;
  background: rgba(255, 255, 255, 0.2);
  flex: 1;
  margin: 0 8px;
  margin-top: -20px;
  border-radius: 1px;
  transition: all 0.3s ease;
}

.phase-connector.active {
  background: linear-gradient(to right, #c8aa6e, #96621d);
}

/* 扩展统计信息样式 */
.team-stats-extended {
  padding: 16px;
  background: linear-gradient(135deg, rgba(22, 33, 62, 0.5) 0%, rgba(15, 52, 96, 0.5) 100%);
  border-top: 1px solid rgba(200, 170, 110, 0.1);
  border-bottom: 1px solid rgba(200, 170, 110, 0.1);
}

.stats-header {
  margin-bottom: 16px;
}

.stats-title {
  color: #c8aa6e;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  background: rgba(15, 52, 96, 0.3);
  border-radius: 8px;
  border: 1px solid rgba(200, 170, 110, 0.1);
  transition: all 0.3s ease;
}

.stat-item:hover {
  background: rgba(15, 52, 96, 0.5);
  border-color: rgba(200, 170, 110, 0.2);
  transform: translateY(-1px);
}

.stat-icon {
  font-size: 14px;
  width: 20px;
  text-align: center;
}

.stat-content {
  flex: 1;
}

.stat-value {
  color: #ecf0f1;
  font-weight: 600;
  font-size: 11px;
  margin-bottom: 2px;
}

.stat-label {
  color: rgba(236, 240, 241, 0.6);
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* 战术笔记样式 */
.tactical-notes {
  padding: 16px;
  background: linear-gradient(135deg, rgba(15, 52, 96, 0.6) 0%, rgba(22, 33, 62, 0.6) 100%);
  border-top: 1px solid rgba(200, 170, 110, 0.1);
  margin-top: auto;
}

.notes-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.notes-title {
  color: #c8aa6e;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.notes-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.notes-indicator.blue {
  background: linear-gradient(135deg, #3498db, #2980b9);
  box-shadow: 0 0 8px rgba(52, 152, 219, 0.5);
}

.notes-indicator.red {
  background: linear-gradient(135deg, #e74c3c, #c0392b);
  box-shadow: 0 0 8px rgba(231, 76, 60, 0.5);
}

.notes-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.note-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  background: rgba(22, 33, 62, 0.4);
  border-radius: 6px;
  border-left: 3px solid rgba(200, 170, 110, 0.3);
  transition: all 0.3s ease;
}

.note-item:hover {
  background: rgba(22, 33, 62, 0.6);
  border-left-color: #c8aa6e;
  transform: translateX(2px);
}

.note-icon {
  font-size: 12px;
  width: 16px;
  text-align: center;
}

.note-text {
  color: rgba(236, 240, 241, 0.8);
  font-size: 10px;
  line-height: 1.3;
  flex: 1;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .team-header {
    padding: 12px;
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
  
  .team-info {
    width: 100%;
  }
  
  .bans-section {
    width: 100%;
    align-items: flex-start;
  }
  
  .bans-container {
    justify-content: flex-start;
  }
  
  .ban-slot {
    width: 28px;
    height: 28px;
  }
  
  .player-display {
    padding: 6px;
  }
  
  .player-position {
    width: 28px;
    height: 28px;
    font-size: 11px;
  }
  
  .picked-champion {
    width: 36px;
    height: 36px;
  }
  
  .player-name {
    font-size: 12px;
  }
  
  .player-rank {
    font-size: 10px;
  }
  
  .team-stats {
    padding: 8px 12px;
    font-size: 11px;
  }
  
  .bp-timeline,
  .team-stats-extended,
  .tactical-notes {
    padding: 12px;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
    gap: 8px;
  }
  
  .phase-indicator {
    flex-direction: column;
    gap: 12px;
  }
  
  .phase-connector {
    width: 2px;
    height: 20px;
    margin: 0;
    margin-left: -14px;
  }
}
</style>