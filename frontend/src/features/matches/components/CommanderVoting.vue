<template>
  <div class="commander-voting">
    <div class="voting-header">
      <h3>
        <i class="fas fa-vote-yea"></i>
        选择指挥官
      </h3>
      <p class="voting-description">
        请为您的队伍投票选择BP阶段的指挥官
      </p>
      <div v-if="timeLeft > 0" class="voting-countdown">
        <i class="fas fa-clock"></i>
        剩余时间: {{ formatTime(timeLeft) }}
      </div>
    </div>
    
    <div class="team-voting-container">
      <div class="team-members">
        <div 
          v-for="member in teamMembers" 
          :key="member.userId"
          class="member-card"
          :class="{
            'voted': hasVoted && votedUserId === member.userId,
            'leading': (member.votes || 0) > 0 && isLeading(member),
            'current-commander': member.isCommander
          }"
          @click="voteForMember(member.userId)"
        >
          <div class="member-avatar">
            <i class="fas fa-user-circle"></i>
            <i v-if="member.isCommander" class="fas fa-crown commander-badge"></i>
          </div>
          
          <div class="member-info">
            <div class="member-name">{{ member.username }}</div>
            <div class="member-status">
              <span v-if="member.isCommander" class="status-badge commander">当前指挥官</span>
              <span v-else-if="member.isCheckedIn" class="status-badge checked-in">已签到</span>
              <span v-else class="status-badge">未签到</span>
            </div>
          </div>
          
          <div class="voting-info">
            <div class="vote-count">
              <i class="fas fa-thumbs-up"></i>
              <span class="vote-number">{{ member.votes || 0 }}</span>
            </div>
            <div v-if="hasVoted && votedUserId === member.userId" class="your-vote">
              <i class="fas fa-check-circle"></i>
              <span>你的选择</span>
            </div>
          </div>
        </div>
      </div>
      
      <div class="voting-summary">
        <div class="voting-stats">
          <div class="stat-item">
            <span class="stat-label">已投票:</span>
            <span class="stat-value">{{ votedCount }}/{{ teamMembers.length }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">当前领先:</span>
            <span class="stat-value">{{ leadingCandidate?.username || '暂无' }}</span>
          </div>
        </div>
        
        <div class="voting-progress">
          <div class="progress-bar">
            <div 
              class="progress-fill"
              :style="{ width: `${votingProgress}%` }"
            ></div>
          </div>
          <span class="progress-text">投票进度: {{ votingProgress }}%</span>
        </div>
      </div>
    </div>
    
    <div class="voting-actions">
      <button 
        v-if="hasVoted"
        class="btn-change-vote"
        :disabled="isSubmitting"
        @click="showChangeVoteConfirm"
      >
        <i class="fas fa-edit"></i>
        更改投票
      </button>
      <button 
        v-if="canForceComplete && isTeamCaptain"
        class="btn-force-complete"
        :disabled="isSubmitting"
        @click="forceCompleteVoting"
      >
        <i class="fas fa-gavel"></i>
        强制完成投票
      </button>
    </div>
    
    <div v-if="errorMessage" class="error-message">
      <i class="fas fa-exclamation-circle"></i>
      {{ errorMessage }}
    </div>
    
    <!-- 更改投票确认对话框 -->
    <div v-if="showChangeConfirm" class="modal-overlay" @click="hideChangeVoteConfirm">
      <div class="modal-content" @click.stop>
        <h4>确认更改投票</h4>
        <p>您当前投票给了 <strong>{{ getCurrentVoteName() }}</strong>，确定要更改投票吗？</p>
        <div class="modal-actions">
          <button class="btn-confirm" @click="confirmChangeVote">
            <i class="fas fa-check"></i>
            确认更改
          </button>
          <button class="btn-cancel" @click="hideChangeVoteConfirm">
            <i class="fas fa-times"></i>
            取消
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { message } from 'ant-design-vue'
import { voteForCommander, getVotingStatus, forceCompleteCommanderVoting } from '@/shared/api/matches'

interface TeamMember {
  userId: number
  username: string
  isCommander: boolean
  isCheckedIn: boolean
  votes?: number
}

interface Props {
  roomId: string
  teamSide: 'blue' | 'red'
  teamMembers: TeamMember[]
  currentUserId: number
  isTeamCaptain?: boolean
  votingTimeLimit?: number
}

const props = withDefaults(defineProps<Props>(), {
  isTeamCaptain: false,
  votingTimeLimit: 10
})

interface Emits {
  votingComplete: [data: {
    teamSide: string
    commanderUserId: number
    commanderUsername: string
    votingResults: Record<string, any>
  }]
  close: []
}

const emit = defineEmits<Emits>()

// 响应式数据
const hasVoted = ref(false)
const votedUserId = ref<number | null>(null)
const isSubmitting = ref(false)
const errorMessage = ref('')
const timeLeft = ref(props.votingTimeLimit)
const showChangeConfirm = ref(false)
const votingResults = ref(new Map<number, number>())

let votingTimer: NodeJS.Timeout | null = null

// 计算属性
const votedCount = computed(() => {
  return props.teamMembers.filter(member => votingResults.value.has(member.userId)).length
})

const votingProgress = computed(() => {
  if (props.teamMembers.length === 0) return 0
  return Math.round((votedCount.value / props.teamMembers.length) * 100)
})

const leadingCandidate = computed(() => {
  let maxVotes = 0
  let leader: TeamMember | null = null
  
  props.teamMembers.forEach(member => {
    const votes = member.votes || 0
    if (votes > maxVotes) {
      maxVotes = votes
      leader = member
    }
  })
  
  return leader
})

const canForceComplete = computed(() => {
  return votedCount.value >= Math.ceil(props.teamMembers.length / 2)
})

const isAllVoted = computed(() => {
  return votedCount.value === props.teamMembers.length
})

// 方法
const formatTime = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const isLeading = (member: TeamMember) => {
  return leadingCandidate.value?.userId === member.userId
}

const voteForMember = async (memberId: number) => {
  if (isSubmitting.value || !memberId) return
  
  // 如果已经投过票，需要确认更改
  if (hasVoted.value && votedUserId.value !== memberId) {
    votedUserId.value = memberId // 临时存储新的选择
    showChangeConfirm.value = true
    return
  }
  
  // 如果点击的是已投票的成员，不做任何操作
  if (hasVoted.value && votedUserId.value === memberId) {
    return
  }
  
  await submitVote(memberId)
}

const submitVote = async (memberId: number) => {
  isSubmitting.value = true
  errorMessage.value = ''
  
  try {
    const response = await voteForCommander(
      props.roomId,
      props.teamSide,
      memberId
    )
    
    const data = response.data
    if (data.success) {
      hasVoted.value = true
      votedUserId.value = memberId
      
      // 更新投票结果
      votingResults.value.set(props.currentUserId, memberId)
      
      message.success(data.message || '投票成功')
      
      // 更新成员投票数
      updateVoteCounts(data.voting_results || {})
      
      // 检查是否所有人都投票完成
      if (isAllVoted.value || data.voting_complete) {
        await completeVoting()
      }
    } else {
      errorMessage.value = data.message || '投票失败'
    }
  } catch (error: any) {
    console.error('投票失败:', error)
    errorMessage.value = error.response?.data?.detail || '投票失败，请重试'
  } finally {
    isSubmitting.value = false
  }
}

const updateVoteCounts = (votingResults: Record<string, number>) => {
  // 重置所有成员的票数
  props.teamMembers.forEach(member => {
    member.votes = 0
  })
  
  // 统计票数
  Object.values(votingResults).forEach(votedForId => {
    const member = props.teamMembers.find(m => m.userId === votedForId)
    if (member) {
      member.votes = (member.votes || 0) + 1
    }
  })
}

const showChangeVoteConfirm = () => {
  showChangeConfirm.value = true;
};

const hideChangeVoteConfirm = () => {
  showChangeConfirm.value = false
  votedUserId.value = getCurrentVoteId() || null // 恢复原来的选择
}

const confirmChangeVote = async () => {
  showChangeConfirm.value = false
  if (votedUserId.value !== null) {
    await submitVote(votedUserId.value)
  }
};

const getCurrentVoteName = () => {
  const currentVoteId = getCurrentVoteId();
  const member = props.teamMembers.find(m => m.userId === currentVoteId);
  return member?.username || '未知';
};

const getCurrentVoteId = () => {
  return votingResults.value.get(props.currentUserId)
}

const forceCompleteVoting = async () => {
  if (!canForceComplete.value || isSubmitting.value) return;
  
  try {
    isSubmitting.value = true;
    const response = await forceCompleteCommanderVoting(
      props.roomId,
      props.teamSide
    )
    
    const data = response.data
    if (data.success) {
      message.success('投票已强制完成')
      await completeVoting()
    } else {
      errorMessage.value = data.message || '强制完成投票失败'
    }
  } catch (error: any) {
    console.error('强制完成投票失败:', error)
    errorMessage.value = error.response?.data?.detail || '强制完成投票失败，请重试'
  } finally {
    isSubmitting.value = false
  }
}

const completeVoting = async () => {
  try {
    // 获取最终的投票状态
    const response = await getVotingStatus(props.roomId, props.teamSide)
    
    const data = response.data
    if (data.success) {
      // 如果有指挥官信息，使用指挥官信息
      if (data.commander) {
        emit('votingComplete', {
          teamSide: props.teamSide,
          commanderUserId: data.commander.userId,
          commanderUsername: data.commander.username,
          votingResults: data.voting_results
        })
      } else {
        // 如果没有指挥官信息，选择票数最多的候选人或随机选择
        const leadingMember = leadingCandidate.value
        if (leadingMember) {
          emit('votingComplete', {
            teamSide: props.teamSide,
            commanderUserId: leadingMember.userId,
            commanderUsername: leadingMember.username,
            votingResults: data.voting_results
          })
        } else {
          // 如果没有投票，随机选择第一个队员作为指挥官
          const firstMember = props.teamMembers[0]
          if (firstMember) {
            emit('votingComplete', {
              teamSide: props.teamSide,
              commanderUserId: firstMember.userId,
              commanderUsername: firstMember.username,
              votingResults: {}
            })
          }
        }
      }
    }
  } catch (error) {
    console.error('获取投票结果失败:', error)
    // 即使API调用失败，也要完成投票以便继续流程
    const leadingMember = leadingCandidate.value || props.teamMembers[0]
    if (leadingMember) {
      emit('votingComplete', {
        teamSide: props.teamSide,
        commanderUserId: leadingMember.userId,
        commanderUsername: leadingMember.username,
        votingResults: {}
      })
    }
  }
};

const startVotingTimer = () => {
  if (votingTimer) return;
  
  votingTimer = setInterval(() => {
    timeLeft.value--;
    
    if (timeLeft.value <= 0) {
      if (votingTimer) {
        clearInterval(votingTimer)
        votingTimer = null
      }
      
      // 投票超时，自动完成
      message.warning('投票时间已到，系统将自动选择指挥官')
      setTimeout(() => {
        completeVoting()
      }, 2000)
    }
  }, 1000);
};

const stopVotingTimer = () => {
  if (votingTimer) {
    clearInterval(votingTimer)
    votingTimer = null
  }
}

// 监听投票完成
watch(isAllVoted, (newVal) => {
  if (newVal) {
    stopVotingTimer();
    setTimeout(() => {
      completeVoting();
    }, 1000);
  }
});

// 生命周期
onMounted(() => {
  startVotingTimer();
  
  // 初始化成员投票数
  props.teamMembers.forEach(member => {
    if (!member.votes) {
      member.votes = 0;
    }
  });
});

onUnmounted(() => {
  stopVotingTimer();
});
</script>

<style scoped>
.commander-voting {
  background: #1a1a2e;
  border-radius: 12px;
  padding: 24px;
  min-width: 600px;
  max-width: 800px;
  color: #f0f0f0;
}

.voting-header {
  text-align: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #2a2a3e;
}

.voting-header h3 {
  color: #f0f0f0;
  font-size: 20px;
  margin: 0 0 8px 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.voting-header h3 i {
  color: #4a8eff;
}

.voting-description {
  color: #a0a0a0;
  font-size: 14px;
  margin: 0 0 12px 0;
}

.voting-countdown {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #ffd700;
  font-weight: 500;
  font-size: 16px;
}

.team-voting-container {
  margin-bottom: 24px;
}

.team-members {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
  max-height: 400px;
  overflow-y: auto;
}

.member-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: #16213e;
  border: 2px solid transparent;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
}

.member-card:hover {
  background: #1e2a4a;
  border-color: #3a4a6a;
}

.member-card.voted {
  background: #1e3a2a;
  border-color: #4a8eff;
  box-shadow: 0 0 10px rgba(74, 142, 255, 0.3);
}

.member-card.leading {
  border-color: #ffd700;
  box-shadow: 0 0 10px rgba(255, 215, 0, 0.3);
}

.member-card.current-commander {
  border-color: #ffd700;
  background: #2a2416;
}

.member-avatar {
  position: relative;
  font-size: 32px;
  color: #7a8a9a;
}

.commander-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  font-size: 14px;
  color: #ffd700;
}

.member-info {
  flex: 1;
}

.member-name {
  color: #f0f0f0;
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 4px;
}

.member-status {
  display: flex;
  gap: 8px;
}

.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  background: #2a3a4a;
  color: #8a9aaa;
}

.status-badge.commander {
  background: #ffd700;
  color: #1a1a2e;
  font-weight: 600;
}

.status-badge.checked-in {
  background: #28a745;
  color: white;
}

.voting-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  min-width: 80px;
}

.vote-count {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(74, 142, 255, 0.2);
  border-radius: 20px;
  border: 1px solid rgba(74, 142, 255, 0.4);
}

.vote-count i {
  color: #4a8eff;
  font-size: 14px;
}

.vote-number {
  color: #4a8eff;
  font-weight: 600;
  font-size: 14px;
}

.your-vote {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #28a745;
}

.voting-summary {
  background: #16213e;
  border-radius: 8px;
  padding: 16px;
  border: 1px solid #2a3a4a;
}

.voting-stats {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stat-label {
  color: #a0a0a0;
  font-size: 14px;
}

.stat-value {
  color: #f0f0f0;
  font-weight: 500;
}

.voting-progress {
  display: flex;
  align-items: center;
  gap: 12px;
}

.progress-bar {
  flex: 1;
  height: 8px;
  background: #2a3a4a;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4a8eff, #5a9eff);
  transition: width 0.3s ease;
}

.progress-text {
  color: #a0a0a0;
  font-size: 12px;
  white-space: nowrap;
}

.voting-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.btn-change-vote,
.btn-force-complete {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-change-vote {
  background: #f39c12;
  color: white;
}

.btn-change-vote:hover:not(:disabled) {
  background: #e67e22;
}

.btn-force-complete {
  background: #e74c3c;
  color: white;
}

.btn-force-complete:hover:not(:disabled) {
  background: #c0392b;
}

.btn-change-vote:disabled,
.btn-force-complete:disabled {
  background: #3a4a5a;
  color: #6a7a8a;
  cursor: not-allowed;
}

.error-message {
  margin-top: 16px;
  padding: 12px;
  background: rgba(220, 53, 69, 0.1);
  border: 1px solid rgba(220, 53, 69, 0.3);
  border-radius: 6px;
  color: #ff6b6b;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 模态框样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: #1a1a2e;
  border-radius: 12px;
  padding: 24px;
  max-width: 400px;
  width: 90%;
  border: 1px solid #2a2a3e;
}

.modal-content h4 {
  color: #f0f0f0;
  margin: 0 0 12px 0;
  font-size: 18px;
}

.modal-content p {
  color: #a0a0a0;
  margin: 0 0 20px 0;
  line-height: 1.5;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.btn-confirm,
.btn-cancel {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 6px;
}

.btn-confirm {
  background: #4a8eff;
  color: white;
}

.btn-confirm:hover {
  background: #5a9eff;
}

.btn-cancel {
  background: #3a4a5a;
  color: #f0f0f0;
}

.btn-cancel:hover {
  background: #4a5a6a;
}

/* 滚动条样式 */
.team-members::-webkit-scrollbar {
  width: 6px;
}

.team-members::-webkit-scrollbar-track {
  background: #16213e;
  border-radius: 3px;
}

.team-members::-webkit-scrollbar-thumb {
  background: #3a4a6a;
  border-radius: 3px;
}

.team-members::-webkit-scrollbar-thumb:hover {
  background: #4a5a7a;
}
</style>