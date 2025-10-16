<template>
  <div
    class="champion-card"
    :class="{ 
      banned: isBanned, 
      picked: isPicked, 
      selected: isSelected,
      disabled: isDisabled
    }"
    :data-champion-id="champion.id"
    @click="handleClick"
    @mouseenter="handleMouseEnter"
    @mouseleave="handleMouseLeave"
  >
    <!-- 英雄头像容器 -->
    <div class="champion-container">
      <!-- 边框装饰 -->
      <div class="champion-border">
        <div class="border-corner top-left"></div>
        <div class="border-corner top-right"></div>
        <div class="border-corner bottom-left"></div>
        <div class="border-corner bottom-right"></div>
      </div>
      
      <!-- 英雄头像 -->
      <div class="champion-avatar">
        <img 
          :src="champion.iconUrl" 
          :alt="champion.name"
          @error="handleImageError"
        />
        
        <!-- 六边形遮罩 -->
        <div class="hexagon-mask"></div>
        
        <!-- 状态遮罩 -->
        <div v-if="isBanned" class="ban-overlay">
          <div class="ban-cross">
            <div class="cross-line line-1"></div>
            <div class="cross-line line-2"></div>
          </div>
          <div class="ban-text">禁用</div>
        </div>
        
        <div v-if="isPicked" class="picked-overlay">
          <div class="picked-icon">
            <div class="check-mark"></div>
          </div>
          <div class="picked-text">已选</div>
        </div>
      </div>
      
      <!-- 选中发光效果 -->
      <div v-if="isSelected" class="selection-glow"></div>
    </div>
    
    <!-- 英雄名称（可选显示） -->
    <div v-if="showName" class="champion-name">{{ champion.name }}</div>
    
    <!-- 悬停工具提示 -->
    <div v-if="showTooltip" class="champion-tooltip">
      <div class="tooltip-content">
        <div class="tooltip-avatar">
          <img :src="champion.iconUrl" :alt="champion.name" />
        </div>
        <div class="tooltip-info">
          <div class="tooltip-name">{{ champion.name }}</div>
          <div class="tooltip-title">{{ champion.title }}</div>
          <div class="tooltip-positions">
            <span v-for="position in champion.position" :key="position" class="position-tag">
              {{ formatPosition(position) }}
            </span>
          </div>
          <div class="tooltip-difficulty">
            难度: {{ '★'.repeat(Math.min(champion.difficulty || 5, 10)) }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { StopOutlined, CheckOutlined } from '@ant-design/icons-vue'
import type { Champion } from '@/shared/stores/champion'

// Props
interface Props {
  champion: Champion
  isBanned?: boolean
  isPicked?: boolean
  isSelected?: boolean
  showName?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isBanned: false,
  isPicked: false,
  isSelected: false,
  showName: false
})

// Emits
interface Emits {
  select: [champion: Champion]
}

const emit = defineEmits<Emits>()

// 响应式数据
const showTooltip = ref(false)
const imageError = ref(false)

// 计算属性
const isDisabled = computed(() => props.isBanned || props.isPicked)

// 方法
const handleClick = () => {
  if (isDisabled.value) return
  emit('select', props.champion)
}

const handleMouseEnter = () => {
  if (!isDisabled.value) {
    showTooltip.value = true
  }
}

const handleMouseLeave = () => {
  showTooltip.value = false
}

const handleImageError = () => {
  imageError.value = true
}

const formatPosition = (position: string) => {
  const positionMap: Record<string, string> = {
    'top': '上单',
    'jungle': '打野',
    'mid': '中单',
    'adc': 'ADC',
    'support': '辅助'
  }
  return positionMap[position.toLowerCase()] || position
}
</script>

<style scoped>
/* LOL客户端风格英雄卡片 */
.champion-card {
  position: relative;
  cursor: pointer;
  aspect-ratio: 1;
  width: 100%;
  min-width: 64px;
  min-height: 64px;
  max-width: 120px;
  max-height: 120px;
  transform: scale(1);
  transition: all 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.champion-card:hover:not(.disabled) {
  transform: scale(1.08);
  z-index: 10;
}

.champion-card.selected {
  transform: scale(1.05);
}

.champion-card.disabled {
  cursor: not-allowed;
}

.champion-card.disabled:hover {
  transform: scale(1);
}

/* 英雄容器 */
.champion-container {
  position: relative;
  width: 100%;
  aspect-ratio: 1;
  background: linear-gradient(135deg, #1e2328 0%, #0f1419 100%);
  border: 3px solid #463714;
  border-radius: 4px;
  overflow: hidden;
  box-shadow: 
    0 0 0 1px rgba(205, 155, 29, 0.3),
    0 4px 8px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
  transition: all 0.25s ease;
}

.champion-card:hover:not(.disabled) .champion-container {
  border-color: #c8aa6e;
  box-shadow: 
    0 0 0 1px rgba(200, 170, 110, 0.8),
    0 0 20px rgba(200, 170, 110, 0.4),
    0 8px 16px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.champion-card.selected .champion-container {
  border-color: #0596aa;
  box-shadow: 
    0 0 0 1px rgba(5, 150, 170, 0.8),
    0 0 20px rgba(5, 150, 170, 0.6),
    0 8px 16px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
  animation: selectedPulse 1.5s ease-in-out infinite;
}

.champion-card.banned .champion-container {
  filter: grayscale(1) brightness(0.4);
  border-color: #c8282f;
  box-shadow: 
    0 0 0 1px rgba(200, 40, 47, 0.8),
    0 4px 8px rgba(0, 0, 0, 0.4);
}

.champion-card.picked .champion-container {
  filter: brightness(0.6) saturate(0.4);
  border-color: #0f2027;
  box-shadow: 
    0 0 0 1px rgba(15, 32, 39, 0.8),
    0 4px 8px rgba(0, 0, 0, 0.4);
}

/* 边框装饰 */
.champion-border {
  position: absolute;
  top: -3px;
  left: -3px;
  right: -3px;
  bottom: -3px;
  pointer-events: none;
  z-index: 2;
}

.border-corner {
  position: absolute;
  width: 12px;
  height: 12px;
  border: 2px solid #c8aa6e;
  background: linear-gradient(45deg, rgba(200, 170, 110, 0.3), transparent);
}

.border-corner.top-left {
  top: 0;
  left: 0;
  border-right: none;
  border-bottom: none;
  border-top-left-radius: 4px;
}

.border-corner.top-right {
  top: 0;
  right: 0;
  border-left: none;
  border-bottom: none;
  border-top-right-radius: 4px;
}

.border-corner.bottom-left {
  bottom: 0;
  left: 0;
  border-right: none;
  border-top: none;
  border-bottom-left-radius: 4px;
}

.border-corner.bottom-right {
  bottom: 0;
  right: 0;
  border-left: none;
  border-top: none;
  border-bottom-right-radius: 4px;
}

/* 英雄头像 */
.champion-avatar {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.champion-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.champion-card:hover:not(.disabled) .champion-avatar img {
  transform: scale(1.1);
}

/* 六边形遮罩效果 */
.hexagon-mask {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, transparent 0%, rgba(200, 170, 110, 0.1) 50%, transparent 100%);
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.champion-card:hover:not(.disabled) .hexagon-mask {
  opacity: 1;
}

/* 状态遮罩 - LOL风格 */
.ban-overlay,
.picked-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 3;
}

.ban-overlay {
  background: linear-gradient(135deg, rgba(200, 40, 47, 0.9) 0%, rgba(139, 0, 0, 0.9) 100%);
}

.picked-overlay {
  background: linear-gradient(135deg, rgba(0, 150, 136, 0.9) 0%, rgba(46, 125, 50, 0.9) 100%);
}

/* 禁用十字 */
.ban-cross {
  position: relative;
  width: 40px;
  height: 40px;
  margin-bottom: 8px;
}

.cross-line {
  position: absolute;
  background: #fff;
  border-radius: 2px;
  box-shadow: 0 0 8px rgba(255, 255, 255, 0.5);
}

.line-1 {
  width: 40px;
  height: 4px;
  top: 18px;
  left: 0;
  transform: rotate(45deg);
}

.line-2 {
  width: 40px;
  height: 4px;
  top: 18px;
  left: 0;
  transform: rotate(-45deg);
}

/* 已选勾选 */
.picked-icon {
  position: relative;
  width: 32px;
  height: 32px;
  margin-bottom: 8px;
  border: 3px solid #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 12px rgba(255, 255, 255, 0.6);
}

.check-mark {
  width: 12px;
  height: 6px;
  border: 3px solid #fff;
  border-top: none;
  border-right: none;
  transform: rotate(-45deg);
  margin-top: -3px;
}

.ban-text,
.picked-text {
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
  letter-spacing: 1px;
}

/* 选中发光效果 */
.selection-glow {
  position: absolute;
  top: -6px;
  left: -6px;
  right: -6px;
  bottom: -6px;
  background: radial-gradient(circle, rgba(5, 150, 170, 0.4) 0%, transparent 70%);
  border-radius: 8px;
  z-index: 1;
  animation: selectionGlow 1.5s ease-in-out infinite;
}

/* 英雄名称 */
.champion-name {
  font-size: 12px;
  font-weight: 600;
  color: #c8aa6e;
  text-align: center;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.8);
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.2;
}

/* 工具提示 - LOL风格 */
.champion-tooltip {
  position: absolute;
  bottom: calc(100% + 12px);
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  pointer-events: none;
}

.tooltip-content {
  background: linear-gradient(135deg, #1e2328 0%, #0f1419 100%);
  border: 2px solid #c8aa6e;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  gap: 12px;
  min-width: 250px;
  backdrop-filter: blur(10px);
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.6),
    0 0 0 1px rgba(200, 170, 110, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.tooltip-avatar {
  width: 48px;
  height: 48px;
  border: 2px solid #463714;
  border-radius: 4px;
  overflow: hidden;
  flex-shrink: 0;
}

.tooltip-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.tooltip-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tooltip-name {
  font-size: 16px;
  font-weight: 700;
  color: #c8aa6e;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.8);
}

.tooltip-title {
  font-size: 12px;
  color: rgba(200, 170, 110, 0.8);
  font-style: italic;
}

.tooltip-positions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 4px;
}

.position-tag {
  font-size: 10px;
  background: rgba(5, 150, 170, 0.2);
  color: #0596aa;
  padding: 2px 8px;
  border-radius: 12px;
  border: 1px solid rgba(5, 150, 170, 0.4);
  font-weight: 500;
}

.tooltip-difficulty {
  font-size: 11px;
  color: #f0e6d2;
  margin-top: 2px;
}

/* 动画 */
@keyframes selectedPulse {
  0% {
    box-shadow: 
      0 0 0 1px rgba(5, 150, 170, 0.8),
      0 0 20px rgba(5, 150, 170, 0.6),
      0 8px 16px rgba(0, 0, 0, 0.3);
  }
  50% {
    box-shadow: 
      0 0 0 1px rgba(5, 150, 170, 1),
      0 0 30px rgba(5, 150, 170, 0.8),
      0 8px 16px rgba(0, 0, 0, 0.3);
  }
  100% {
    box-shadow: 
      0 0 0 1px rgba(5, 150, 170, 0.8),
      0 0 20px rgba(5, 150, 170, 0.6),
      0 8px 16px rgba(0, 0, 0, 0.3);
  }
}

@keyframes selectionGlow {
  0% {
    opacity: 0.6;
    transform: scale(1);
  }
  50% {
    opacity: 1;
    transform: scale(1.02);
  }
  100% {
    opacity: 0.6;
    transform: scale(1);
  }
}

/* 响应式断点调整 */
@media (max-width: 768px) {
  .champion-card {
    min-width: 56px;
    gap: 4px;
  }
  
  .champion-container {
    border-width: 2px;
  }
  
  .border-corner {
    width: 8px;
    height: 8px;
    border-width: 1px;
  }
  
  .champion-name {
    font-size: 10px;
  }
  
  .ban-cross {
    width: 28px;
    height: 28px;
  }
  
  .cross-line {
    width: 28px;
    height: 3px;
    top: 12px;
  }
  
  .picked-icon {
    width: 24px;
    height: 24px;
    border-width: 2px;
  }
  
  .check-mark {
    width: 8px;
    height: 4px;
    border-width: 2px;
  }
  
  .ban-text,
  .picked-text {
    font-size: 9px;
  }
  
  .tooltip-content {
    min-width: 200px;
    padding: 8px;
    gap: 8px;
  }
  
  .tooltip-avatar {
    width: 36px;
    height: 36px;
  }
  
  .tooltip-name {
    font-size: 14px;
  }
  
  .tooltip-title {
    font-size: 10px;
  }
}

@media (max-width: 480px) {
  .champion-card {
    min-width: 48px;
    gap: 3px;
  }
  
  .champion-name {
    font-size: 9px;
  }
  
  .tooltip-content {
    min-width: 180px;
    padding: 6px;
  }
}

@media (min-width: 1441px) {
  .champion-card {
    min-width: 80px;
  }
  
  .champion-card:hover:not(.disabled) {
    transform: scale(1.1);
  }
  
  .champion-name {
    font-size: 13px;
  }
  
  .border-corner {
    width: 14px;
    height: 14px;
  }
}

@media (min-width: 2561px) {
  .champion-card {
    min-width: 100px;
    gap: 8px;
  }
  
  .champion-card:hover:not(.disabled) {
    transform: scale(1.12);
  }
  
  .champion-container {
    border-width: 4px;
  }
  
  .champion-name {
    font-size: 14px;
  }
  
  .border-corner {
    width: 16px;
    height: 16px;
    border-width: 3px;
  }
  
  .ban-cross {
    width: 50px;
    height: 50px;
  }
  
  .cross-line {
    width: 50px;
    height: 5px;
    top: 22px;
  }
  
  .picked-icon {
    width: 40px;
    height: 40px;
    border-width: 4px;
  }
  
  .check-mark {
    width: 15px;
    height: 8px;
    border-width: 4px;
  }
}
</style>