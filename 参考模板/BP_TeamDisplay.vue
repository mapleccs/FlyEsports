<template>
  <div class="team-display">
    <div class="team-header" :class="side === 'blue' ? 'blue-header' : 'red-header'">
      <div class="team-info">
        <div class="team-logo">
          <img :src="teamLogoUrl" alt="Team Logo" />
        </div>
        <div class="team-name">{{ teamData.name }}</div>
      </div>

      <div class="bans-section">
        <div class="bans-label">禁用英雄</div>
        <div class="bans-container">
          <div v-for="(ban, i) in bans" :key="i" class="ban-slot">
            <div class="ban-overlay" v-if="!ban">
              <i class="fas fa-ban"></i>
            </div>
            <img :src="ban.iconUrl" :alt="ban.name" v-if="ban">
          </div>
        </div>
      </div>
    </div>

    <div class="players-container">
      <div
        v-for="(player, index) in teamData.players"
        :key="player.userId"
        class="player-display"
        :class="{
          current: currentAction?.actorId === player.userId,
          top: positions[index] === 'TOP',
          jungle: positions[index] === 'JUNGLE',
          mid: positions[index] === 'MID',
          adc: positions[index] === 'ADC',
          support: positions[index] === 'SUPPORT'
        }"
      >
        <div class="player-position">{{ positionText(positions[index]) }}</div>
        <div class="player-info">
          <div class="player-name">{{ player.username }}</div>
          <div class="player-rank">{{ player.rank || '钻石' }}</div>
        </div>
        <div class="picked-champion">
          <div class="champion-placeholder" v-if="!getPickForPlayer(player.userId)">
            <i class="fas fa-user-alt"></i>
          </div>
          <img v-if="getPickForPlayer(player.userId)" :src="getPickForPlayer(player.userId).iconUrl"/>
          <div class="player-status" v-if="currentAction?.actorId === player.userId">
            <div class="status-indicator"></div>
            <div class="status-text">选择中</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useBpStore } from '@/stores/bpStore';

const bpStore = useBpStore();
const props = defineProps({
  teamData: {type: Object, required: true},
  side: {type: String, required: true},
  picks: {type: Array, required: true},
  bans: {type: Array, required: true},
  actions: {type: Array, required: true},
  currentAction: {type: Object, default: null}
});

// 假设玩家位置顺序
const positions = ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'];

// 获取队伍Logo URL
const teamLogoUrl = computed(() => {
  return props.teamData.logo || require('@/assets/images/default-logo.png');
});

// 位置文本转换
const positionText = (pos) => {
  const positionMap = {
    'TOP': '上单',
    'JUNGLE': '打野',
    'MID': '中单',
    'ADC': 'ADC',
    'SUPPORT': '辅助'
  };
  return positionMap[pos] || pos;
};

// 获取玩家选择的英雄
const getPickForPlayer = (userId) => {
  const pickAction = props.actions.find(a =>
    a.actorId === userId &&
    a.type === 'pick' &&
    a.completed
  );
  return pickAction ? pickAction.champion : null;
};
</script>

<style scoped>
.team-display {
  background: rgba(13, 25, 48, 0.8); /* var(--lol-card-bg) */
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
  height: 100%;
  display: flex;
  flex-direction: column;
}

.team-header {
  padding: 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: relative;
  z-index: 1;
}

.blue-header {
  background: linear-gradient(90deg, rgba(11, 196, 226, 0.3), rgba(11, 196, 226, 0.1));
  border-bottom: 2px solid #0bc4e2; /* var(--lol-blue) */
}

.red-header {
  background: linear-gradient(90deg, rgba(232, 65, 56, 0.1), rgba(232, 65, 56, 0.3));
  border-bottom: 2px solid #e84138; /* var(--lol-red) */
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
  background: #121d33;
}

.team-logo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.team-name {
  font-weight: bold;
  font-size: 1.1rem;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
}

.bans-section {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.bans-label {
  font-size: 0.8rem;
  opacity: 0.8;
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.bans-container {
  display: flex;
  gap: 8px;
}

.ban-slot {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: #121d33;
  overflow: hidden;
  position: relative;
  border: 2px solid #2a3650;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ban-slot img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.ban-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(232, 65, 56, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 18px;
}

.players-container {
  flex: 1;
  padding: 12px;
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
  overflow-y: auto;
}

.player-display {
  display: flex;
  align-items: center;
  padding: 10px;
  background: rgba(18, 29, 51, 0.7);
  border-radius: 8px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.player-display::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 4px;
  height: 100%;
}

.player-display.top::before { background: linear-gradient(to bottom, #f39c12, #d35400); }
.player-display.jungle::before { background: linear-gradient(to bottom, #27ae60, #16a085); }
.player-display.mid::before { background: linear-gradient(to bottom, #3498db, #2980b9); }
.player-display.adc::before { background: linear-gradient(to bottom, #e74c3c, #c0392b); }
.player-display.support::before { background: linear-gradient(to bottom, #9b59b6, #8e44ad); }

.player-display.current {
  transform: translateX(5px);
  box-shadow: 0 0 15px rgba(11, 196, 226, 0.4);
  animation: pulse-glow 1.5s infinite;
}

@keyframes pulse-glow {
  0% { box-shadow: 0 0 5px rgba(11, 196, 226, 0.4); }
  50% { box-shadow: 0 0 15px rgba(11, 196, 226, 0.7); }
  100% { box-shadow: 0 0 5px rgba(11, 196, 226, 0.4); }
}

.player-position {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.1);
  margin-right: 12px;
  font-weight: bold;
  font-size: 0.9rem;
}

.player-info {
  flex: 1;
}

.player-name {
  font-size: 0.95rem;
  font-weight: 500;
  margin-bottom: 4px;
}

.player-rank {
  font-size: 0.8rem;
  opacity: 0.8;
  background: rgba(255, 255, 255, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
  display: inline-block;
}

.picked-champion {
  width: 50px;
  height: 50px;
  border-radius: 8px;
  overflow: hidden;
  border: 2px solid #2a3650;
  position: relative;
}

.picked-champion img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.champion-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.3);
  font-size: 20px;
}

.player-status {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  background: rgba(11, 196, 226, 0.7);
  color: white;
  font-size: 0.7rem;
  padding: 2px;
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-indicator {
  width: 8px;
  height: 8px;
  background: white;
  border-radius: 50%;
  margin-right: 4px;
  animation: blink 1.5s infinite;
}

@keyframes blink {
  0% { opacity: 0.2; }
  50% { opacity: 1; }
  100% { opacity: 0.2; }
}

/* 滚动条样式 */
.players-container::-webkit-scrollbar {
  width: 6px;
}

.players-container::-webkit-scrollbar-thumb {
  background: rgba(11, 196, 226, 0.5);
  border-radius: 3px;
}

.players-container::-webkit-scrollbar-track {
  background: rgba(18, 29, 51, 0.3);
}
</style>