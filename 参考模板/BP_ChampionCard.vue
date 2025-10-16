<template>
  <div
      class="champion-card"
      :class="{ banned: isBanned, picked: isPicked, selected: isSelected }"
      @click="$emit('select', champion)"
  >
    <img :src="champion.iconUrl" :alt="champion.name">
    <div class="champion-name">{{ champion.name }}</div>
  </div>
</template>

<script setup>
defineProps({
  champion: {type: Object, required: true},
  isBanned: {type: Boolean, default: false},
  isPicked: {type: Boolean, default: false},
  isSelected: {type: Boolean, default: false}
});
defineEmits(['select']);
</script>

<style scoped>
.champion-card {
  position: relative;
  border-radius: clamp(6px, 1vw, 10px);
  overflow: hidden;
  cursor: pointer;
  aspect-ratio: 1/1.2;
  background: #16213e;
  border: 2px solid #2c3e50;
  transform: scale(1);
  transition: all 0.3s ease;
  min-width: clamp(50px, 5vw, 80px);
  min-height: clamp(60px, 6vw, 96px);
}

.champion-card:hover {
  transform: scale(1.08);
  border-color: #3498db;
  box-shadow: 0 4px 12px rgba(52, 152, 219, 0.3);
  z-index: 10;
}

.champion-card img {
  width: 100%;
  height: 75%;
  object-fit: cover;
  transition: filter 0.3s ease;
}

.champion-name {
  height: 25%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: clamp(9px, 1vw, 13px);
  text-align: center;
  padding: clamp(1px, 0.5vw, 3px);
  background: linear-gradient(180deg, rgba(22, 33, 62, 0.9) 0%, #0f3460 100%);
  color: #ecf0f1;
  font-weight: 500;
  line-height: 1.2;
}

/* 状态样式 */
.champion-card.banned {
  opacity: 0.35;
  filter: grayscale(1);
  border-color: #e94560;
  position: relative;
}

.champion-card.banned::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, transparent 45%, #e94560 50%, transparent 55%);
  pointer-events: none;
  z-index: 1;
}

.champion-card.picked {
  opacity: 0.6;
  filter: brightness(0.7);
  border-color: #95a5a6;
}

.champion-card.selected {
  border-color: #3498db;
  box-shadow: 0 0 20px rgba(52, 152, 219, 0.6);
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 20px rgba(52, 152, 219, 0.6);
  }
  50% {
    box-shadow: 0 0 30px rgba(52, 152, 219, 0.8);
  }
  100% {
    box-shadow: 0 0 20px rgba(52, 152, 219, 0.6);
  }
}

/* 状态指示器 */
.champion-card::after {
  content: '';
  position: absolute;
  top: clamp(3px, 0.5vw, 6px);
  right: clamp(3px, 0.5vw, 6px);
  width: clamp(8px, 1vw, 12px);
  height: clamp(8px, 1vw, 12px);
  border-radius: 50%;
  background: transparent;
  z-index: 2;
}

.champion-card.banned::after {
  background: #e94560;
  box-shadow: 0 0 6px #e94560;
}

.champion-card.picked::after {
  background: #95a5a6;
  box-shadow: 0 0 4px #95a5a6;
}

.champion-card.selected::after {
  background: #3498db;
  box-shadow: 0 0 10px #3498db;
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

/* 响应式断点调整 */
@media (max-width: 768px) {
  .champion-card {
    min-width: 45px;
    min-height: 54px;
  }
  
  .champion-name {
    font-size: 9px;
  }
}

@media (min-width: 1441px) {
  .champion-card:hover {
    transform: scale(1.12);
  }
}

@media (min-width: 2561px) {
  .champion-card {
    min-width: 85px;
    min-height: 102px;
    border-radius: 12px;
  }
  
  .champion-card:hover {
    transform: scale(1.15);
  }
}
</style>