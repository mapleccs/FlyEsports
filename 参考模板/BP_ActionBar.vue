<template>
  <div class="footer-controls">
    <!-- 左侧：用户状态信息 -->
    <div class="user-status">
      <!-- 指挥官视角 -->
      <template v-if="bpStore.isCommander">
        <div class="status-info" v-if="bpStore.isMyTurn">
          <i class="fas fa-crown"></i> 
          <span>轮到你了: {{ bpStore.currentAction.type === 'ban' ? '禁用' : '选择' }}英雄</span>
        </div>
        <div class="status-info" v-else>
          <i class="fas fa-hourglass-half"></i>
          <span>等待 {{ bpStore.currentAction?.team === 'blue' ? '蓝方' : '红方' }} 操作...</span>
        </div>
      </template>
      
      <!-- 普通队员视角 -->
      <template v-else>
        <div class="status-info" v-if="bpStore.myTeam">
          <i class="fas fa-eye"></i>
          <span>观战模式 - {{ bpStore.myTeam === 'blue' ? '蓝方' : '红方' }}队员</span>
        </div>
        <div class="status-info" v-else>
          <i class="fas fa-eye"></i>
          <span>观战模式</span>
        </div>
      </template>
    </div>
    
    <!-- 中间：BP步骤指示 -->
    <div class="center-phase">
      <div class="phase-display">
        {{ currentPhaseText }}
      </div>
    </div>
    
    <!-- 右侧：连接状态和操作按钮 -->
    <div class="right-controls">
      <!-- WebSocket连接状态指示器 -->
      <div class="connection-status" :class="{
        'connected': props.isConnected,
        'connecting': props.isConnecting,
        'error': props.hasError
      }">
        <i class="fas fa-circle" v-if="props.isConnected"></i>
        <i class="fas fa-clock fa-spin" v-else-if="props.isConnecting"></i>
        <i class="fas fa-exclamation-triangle" v-else></i>
        <span>{{
          props.isConnected ? '已连接' :
          props.isConnecting ? '连接中' :
          '连接异常'
        }}</span>
      </div>
      
      <!-- 只有指挥官才显示锁定按钮 -->
      <button
          v-if="bpStore.isCommander"
          class="btn-lock"
          :disabled="!bpStore.isMyTurn || !bpStore.selectedChampionId || isLocking"
          @click="handleLockIn"
      >
        {{ isLocking ? '锁定中...' : '锁定选择' }}
      </button>
      
      <!-- 非指挥官显示提示 -->
      <div v-else class="spectator-notice">
        <i class="fas fa-info-circle"></i>
        <span>由指挥官进行BP操作</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import {ref, computed} from 'vue';
import {useBpStore} from '@/stores/bpStore';
import {ElMessage} from 'element-plus';

// 定义props
const props = defineProps({
  isConnected: {
    type: Boolean,
    default: false
  },
  isConnecting: {
    type: Boolean, 
    default: false
  },
  hasError: {
    type: Boolean,
    default: false
  }
});

const bpStore = useBpStore();
const isLocking = ref(false);

// 计算当前BP阶段文本
const currentPhaseText = computed(() => {
  const action = bpStore.currentAction;
  if (!action) return 'BP已结束';
  
  const actionOrder = action.order;
  const totalActions = bpStore.bpState?.actions?.length || 20;
  const teamName = action.team === 'blue' ? '蓝方' : '红方';
  const actionText = action.type === 'ban' ? 'BAN' : 'PICK';
  
  return `第 ${actionOrder}/${totalActions} 步 - ${teamName}${actionText}`;
});

const handleLockIn = async () => {
  if (isLocking.value) return;
  
  try {
    isLocking.value = true;
    const response = await bpStore.lockInSelection();
    
    if (response && response.success) {
      ElMessage.success(response.message);
    } else if (response) {
      ElMessage.error(response.message);
    }
  } catch (error) {
    console.error('锁定英雄失败:', error);
    ElMessage.error('锁定英雄失败，请重试');
  } finally {
    isLocking.value = false;
  }
};
</script>

<style scoped>
.footer-controls {
  background: #16213e;
  border-top: 2px solid #0f3460;
  padding: clamp(6px, 1.2vw, 12px);
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.5);
  gap: clamp(10px, 1.5vw, 15px);
  min-height: 45px;
}

/* 左侧用户状态 */
.user-status {
  display: flex;
  align-items: center;
  justify-content: flex-start;
}

.status-info {
  display: flex;
  align-items: center;
  gap: clamp(4px, 0.6vw, 8px);
  font-size: clamp(11px, 1.2vw, 14px);
  color: #ffffff;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 250px;
}

.status-info i {
  flex-shrink: 0;
  font-size: clamp(11px, 1.2vw, 14px);
}

/* 右侧控制区域 */
.right-controls {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: clamp(15px, 2vw, 20px);
}

.btn-lock {
  padding: clamp(6px, 1vw, 10px) clamp(12px, 2vw, 20px);
  background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
  color: white;
  border: none;
  border-radius: clamp(4px, 0.6vw, 8px);
  font-weight: bold;
  font-size: clamp(11px, 1.3vw, 14px);
  cursor: pointer;
  transition: all 0.3s ease;
  text-transform: uppercase;
  letter-spacing: clamp(0.5px, 0.1vw, 1px);
  box-shadow: 0 3px 8px rgba(52, 152, 219, 0.4);
  position: relative;
  overflow: hidden;
  min-width: 90px;
  white-space: nowrap;
}

.btn-lock::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s ease;
}

.btn-lock:not(:disabled):hover::before {
  left: 100%;
}

.btn-lock:disabled {
  background: linear-gradient(135deg, #7f8c8d 0%, #95a5a6 100%);
  opacity: 0.7;
  cursor: not-allowed;
  box-shadow: none;
}

.btn-lock:not(:disabled):hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(52, 152, 219, 0.6);
  background: linear-gradient(135deg, #5dade2 0%, #3498db 100%);
}

.btn-lock:not(:disabled):active {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(52, 152, 219, 0.4);
}

/* 中间BP步骤指示 */
.center-phase {
  display: flex;
  justify-content: center;
  align-items: center;
}

.phase-display {
  font-size: clamp(12px, 1.5vw, 16px);
  color: #3498db;
  font-weight: 600;
  text-align: center;
  white-space: nowrap;
  background: rgba(52, 152, 219, 0.1);
  border: 1px solid rgba(52, 152, 219, 0.3);
  border-radius: clamp(6px, 0.8vw, 10px);
  padding: clamp(4px, 0.8vw, 8px) clamp(10px, 1.5vw, 18px);
  backdrop-filter: blur(10px);
  text-shadow: 0 0 8px rgba(52, 152, 219, 0.3);
}

.spectator-notice {
  display: flex;
  align-items: center;
  gap: clamp(6px, 0.8vw, 8px);
  padding: clamp(5px, 1vw, 8px) clamp(10px, 1.5vw, 15px);
  background: rgba(95, 165, 160, 0.1);
  border: 1px solid rgba(95, 165, 160, 0.3);
  border-radius: clamp(4px, 0.6vw, 8px);
  color: #95a5a6;
  font-size: clamp(10px, 1.2vw, 13px);
  white-space: nowrap;
  min-width: 90px;
}

.spectator-notice i {
  color: #3498db;
}



.fa-crown {
  color: #f1c40f;
}

.fa-hourglass-half {
  color: #e67e22;
}

.fa-eye {
  color: #3498db;
}

/* WebSocket连接状态指示器样式 */
.connection-status {
  display: flex;
  align-items: center;
  gap: clamp(3px, 0.6vw, 6px);
  padding: clamp(4px, 0.8vw, 6px) clamp(8px, 1.2vw, 12px);
  border-radius: clamp(12px, 1.5vw, 16px);
  font-size: clamp(9px, 1vw, 11px);
  font-weight: 500;
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
  white-space: nowrap;
  flex-shrink: 0;
}

.connection-status.connected {
  background: rgba(46, 204, 113, 0.2);
  border: 1px solid #2ecc71;
  color: #2ecc71;
}

.connection-status.connecting {
  background: rgba(241, 196, 15, 0.2);
  border: 1px solid #f1c40f;
  color: #f1c40f;
}

.connection-status.error {
  background: rgba(231, 76, 60, 0.2);
  border: 1px solid #e74c3c;
  color: #e74c3c;
}

.connection-status i {
  font-size: clamp(8px, 0.9vw, 10px);
  flex-shrink: 0;
}

/* 响应式媒体查询 */
/* 平板和小屏幕 (768px以下) */
@media (max-width: 768px) {
  .footer-controls {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto auto;
    gap: 8px;
    padding: 8px;
    text-align: center;
    min-height: 35px;
  }
  
  .user-status {
    order: 1;
    justify-content: center;
  }
  
  .center-phase {
    order: 2;
  }
  
  .phase-display {
    font-size: 13px;
    padding: 4px 10px;
  }
  
  .right-controls {
    order: 3;
    justify-content: center;
    flex-wrap: wrap;
    gap: 10px;
  }
  
  .btn-lock {
    min-width: 100px;
    padding: 6px 12px;
    font-size: 12px;
  }
  
  .spectator-notice {
    min-width: 100px;
    font-size: 11px;
  }
}

/* 大手机和小平板 (480px - 768px) */
@media (min-width: 481px) and (max-width: 768px) {
  .footer-controls {
    grid-template-columns: 1fr auto;
    grid-template-rows: auto auto;
    gap: 10px;
    min-height: 38px;
  }
  
  .user-status {
    grid-column: 1 / -1;
    order: 1;
    justify-content: center;
  }
  
  .center-phase {
    order: 2;
    justify-content: flex-start;
  }
  
  .right-controls {
    order: 3;
    justify-content: flex-end;
  }
}

/* 小手机 (480px以下) */
@media (max-width: 480px) {
  .footer-controls {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto auto;
    gap: 6px;
    padding: 6px;
    min-height: 32px;
  }
  
  .user-status {
    justify-content: center;
  }
  
  .status-info {
    font-size: 11px;
    max-width: none;
    text-align: center;
  }
  
  .phase-display {
    font-size: 11px;
    padding: 4px 8px;
  }
  
  .right-controls {
    flex-direction: column;
    align-items: center;
    gap: 6px;
  }
  
  .connection-status {
    font-size: 9px;
    padding: 3px 8px;
  }
  
  .btn-lock {
    width: 100%;
    max-width: 160px;
    padding: 6px 10px;
    font-size: 11px;
    letter-spacing: 0.5px;
  }
  
  .spectator-notice {
    font-size: 10px;
    padding: 5px 10px;
    min-width: auto;
    width: 100%;
    max-width: 160px;
    text-align: center;
  }
}

/* 超小屏幕适配 */
@media (max-width: 360px) {
  .footer-controls {
    padding: 4px;
    min-height: 28px;
  }
  
  .status-info {
    font-size: 10px;
  }
  
  .phase-display {
    font-size: 10px;
    padding: 3px 6px;
  }
  
  .connection-status {
    font-size: 8px;
    padding: 2px 6px;
  }
  
  .btn-lock {
    padding: 5px 8px;
    font-size: 10px;
    max-width: 140px;
  }
  
  .spectator-notice {
    font-size: 9px;
    padding: 4px 8px;
    max-width: 140px;
  }
}
</style>