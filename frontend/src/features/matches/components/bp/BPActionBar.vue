<template>
  <div class="footer-controls">
    <!-- 左侧：用户状态信息 -->
    <div class="user-status">
      <!-- 指挥官视角 -->
      <template v-if="bpStore.isCommander">
        <div class="status-info" v-if="bpStore.isMyTurn">
          <CrownOutlined />
          <span>轮到你了: {{ bpStore.currentAction?.type === 'ban' ? '禁用' : '选择' }}英雄</span>
        </div>
        <div class="status-info" v-else>
          <ClockCircleOutlined />
          <span>等待 {{ bpStore.currentAction?.team === 'blue' ? '蓝方' : '红方' }} 操作...</span>
        </div>
      </template>
      
      <!-- 普通队员视角 -->
      <template v-else>
        <div class="status-info" v-if="bpStore.myTeam">
          <EyeOutlined />
          <span>观战模式 - {{ bpStore.myTeam === 'blue' ? '蓝方' : '红方' }}队员</span>
        </div>
        <div class="status-info" v-else>
          <EyeOutlined />
          <span>观战模式</span>
        </div>
      </template>
    </div>
    
    <!-- 中间：BP步骤指示 -->
    <div class="center-phase">
      <div class="phase-display">
        {{ bpStore.currentPhaseText }}
      </div>
    </div>
    
    <!-- 右侧：连接状态和操作按钮 -->
    <div class="right-controls">
      <!-- WebSocket连接状态指示器 -->
      <div class="connection-status" :class="{
        'connected': isConnected,
        'connecting': isConnecting,
        'error': hasError
      }">
        <CheckCircleOutlined v-if="isConnected" />
        <LoadingOutlined v-else-if="isConnecting" />
        <ExclamationCircleOutlined v-else />
        <span>{{
          isConnected ? '已连接' :
          isConnecting ? '连接中' :
          '连接异常'
        }}</span>
      </div>
      
      <!-- 只有指挥官才显示锁定按钮 -->
      <a-button
          v-if="bpStore.isCommander"
          type="primary"
          size="large"
          :disabled="!bpStore.isMyTurn || !bpStore.selectedChampionId || isLocking"
          :loading="isLocking"
          @click="handleLockIn"
      >
        {{ isLocking ? '锁定中...' : '锁定选择' }}
      </a-button>
      
      <!-- 非指挥官显示提示 -->
      <div v-else class="spectator-notice">
        <InfoCircleOutlined />
        <span>由指挥官进行BP操作</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { message } from 'ant-design-vue'
import {
  CrownOutlined,
  ClockCircleOutlined,
  EyeOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined
} from '@ant-design/icons-vue'
import { useBPStore } from '@/shared/stores/bp'

// 定义props
interface Props {
  isConnected?: boolean
  isConnecting?: boolean
  hasError?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isConnected: false,
  isConnecting: false,
  hasError: false
})

// 定义emits
interface Emits {
  lockSelection: []
}

const emit = defineEmits<Emits>()

const bpStore = useBPStore()
const isLocking = ref(false)

const handleLockIn = async () => {
  if (isLocking.value) return
  
  try {
    isLocking.value = true
    
    const response = await bpStore.lockInSelection()
    
    if (response && response.success) {
      message.success(response.message || '英雄已锁定')
      emit('lockSelection')
    } else if (response) {
      message.error(response.message || '锁定失败')
    }
  } catch (error: any) {
    console.error('锁定英雄失败:', error)
    message.error(error.message || '锁定英雄失败，请重试')
  } finally {
    isLocking.value = false
  }
}
</script>

<style scoped>
.footer-controls {
  background: linear-gradient(135deg, #16213e 0%, #0f3460 100%);
  border-top: 2px solid #3498db;
  padding: 12px 20px;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.5);
  gap: 20px;
  min-height: 80px;
  backdrop-filter: blur(10px);
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
  gap: 8px;
  font-size: 14px;
  color: #ecf0f1;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 280px;
}

.status-info .anticon {
  flex-shrink: 0;
  font-size: 16px;
}

.status-info .anticon-crown {
  color: #f1c40f;
}

.status-info .anticon-clock-circle {
  color: #e67e22;
}

.status-info .anticon-eye {
  color: #3498db;
}

/* 右侧控制区域 */
.right-controls {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 20px;
}

/* 中间BP步骤指示 */
.center-phase {
  display: flex;
  justify-content: center;
  align-items: center;
}

.phase-display {
  font-size: 16px;
  color: #3498db;
  font-weight: 600;
  text-align: center;
  white-space: nowrap;
  background: rgba(52, 152, 219, 0.15);
  border: 1px solid rgba(52, 152, 219, 0.4);
  border-radius: 10px;
  padding: 8px 18px;
  backdrop-filter: blur(10px);
  text-shadow: 0 0 10px rgba(52, 152, 219, 0.3);
  box-shadow: 0 2px 10px rgba(52, 152, 219, 0.2);
}

.spectator-notice {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(149, 165, 166, 0.15);
  border: 1px solid rgba(149, 165, 166, 0.4);
  border-radius: 8px;
  color: #bdc3c7;
  font-size: 13px;
  white-space: nowrap;
  min-width: 120px;
  justify-content: center;
}

.spectator-notice .anticon {
  color: #3498db;
  font-size: 14px;
}

/* WebSocket连接状态指示器样式 */
.connection-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
  white-space: nowrap;
  flex-shrink: 0;
  min-width: 80px;
  justify-content: center;
}

.connection-status.connected {
  background: rgba(46, 204, 113, 0.2);
  border: 1px solid #2ecc71;
  color: #2ecc71;
  box-shadow: 0 0 10px rgba(46, 204, 113, 0.3);
}

.connection-status.connecting {
  background: rgba(241, 196, 15, 0.2);
  border: 1px solid #f1c40f;
  color: #f1c40f;
  box-shadow: 0 0 10px rgba(241, 196, 15, 0.3);
}

.connection-status.error {
  background: rgba(231, 76, 60, 0.2);
  border: 1px solid #e74c3c;
  color: #e74c3c;
  box-shadow: 0 0 10px rgba(231, 76, 60, 0.3);
}

.connection-status .anticon {
  font-size: 12px;
  flex-shrink: 0;
}

/* 锁定按钮样式 */
.footer-controls .ant-btn {
  height: 40px;
  padding: 0 24px;
  font-size: 14px;
  font-weight: 600;
  border-radius: 8px;
  text-transform: uppercase;
  letter-spacing: 1px;
  box-shadow: 0 4px 12px rgba(52, 152, 219, 0.4);
  border: none;
  background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
  transition: all 0.3s ease;
  min-width: 120px;
}

.footer-controls .ant-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(52, 152, 219, 0.6);
  background: linear-gradient(135deg, #5dade2 0%, #3498db 100%);
}

.footer-controls .ant-btn:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(52, 152, 219, 0.4);
}

.footer-controls .ant-btn:disabled {
  background: linear-gradient(135deg, #7f8c8d 0%, #95a5a6 100%);
  opacity: 0.7;
  cursor: not-allowed;
  box-shadow: none;
  transform: none;
}

/* 响应式媒体查询 */
@media (max-width: 768px) {
  .footer-controls {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto auto;
    gap: 12px;
    padding: 12px 16px;
    text-align: center;
    min-height: 60px;
  }
  
  .user-status {
    order: 1;
    justify-content: center;
  }
  
  .center-phase {
    order: 2;
  }
  
  .phase-display {
    font-size: 14px;
    padding: 6px 12px;
  }
  
  .right-controls {
    order: 3;
    justify-content: center;
    flex-wrap: wrap;
    gap: 12px;
  }
  
  .footer-controls .ant-btn {
    min-width: 100px;
    height: 36px;
    font-size: 12px;
  }
  
  .spectator-notice {
    min-width: 100px;
    font-size: 11px;
    padding: 6px 12px;
  }

  .status-info {
    font-size: 12px;
    max-width: none;
    text-align: center;
  }
}

@media (max-width: 480px) {
  .footer-controls {
    padding: 8px 12px;
    gap: 8px;
    min-height: 50px;
  }
  
  .status-info {
    font-size: 11px;
  }
  
  .phase-display {
    font-size: 12px;
    padding: 4px 8px;
  }
  
  .connection-status {
    font-size: 10px;
    padding: 4px 8px;
    min-width: 60px;
  }
  
  .footer-controls .ant-btn {
    height: 32px;
    padding: 0 16px;
    font-size: 11px;
    min-width: 80px;
  }
  
  .spectator-notice {
    font-size: 10px;
    padding: 4px 8px;
    min-width: 80px;
  }
}
</style>