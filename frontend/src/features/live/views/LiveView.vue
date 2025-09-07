<template>
  <layout-default>
    <div class="live-container">
      <div class="live-header">
        <a-page-header
          title="赛事直播"
          sub-title="观看正在进行的比赛直播"
        />
      </div>
      
      <div class="live-content">
        <!-- 直播状态筛选 -->
        <div class="live-filters">
          <a-space>
            <a-radio-group v-model:value="selectedStatus" @change="handleStatusChange">
              <a-radio-button value="all">全部</a-radio-button>
              <a-radio-button value="live">正在直播</a-radio-button>
              <a-radio-button value="upcoming">即将开始</a-radio-button>
              <a-radio-button value="ended">已结束</a-radio-button>
            </a-radio-group>
          </a-space>
        </div>

        <!-- 直播列表 -->
        <div class="live-grid">
          <a-row :gutter="[16, 16]">
            <a-col :xs="24" :sm="12" :lg="8" :xl="6" v-for="stream in filteredStreams" :key="stream.id">
              <a-card
                hoverable
                class="live-card"
                :class="{
                  'live-active': stream.status === 'live',
                  'live-upcoming': stream.status === 'upcoming',
                  'live-ended': stream.status === 'ended'
                }"
                @click="handleStreamClick(stream)"
              >
                <template #cover>
                  <div class="live-cover">
                    <img :src="stream.thumbnail" :alt="stream.title" />
                    <div class="live-status-badge" :class="`status-${stream.status}`">
                      <a-tag :color="getStatusColor(stream.status)">
                        {{ getStatusText(stream.status) }}
                      </a-tag>
                    </div>
                    <div v-if="stream.viewerCount && stream.status === 'live'" class="viewer-count">
                      <EyeOutlined />
                      {{ formatViewerCount(stream.viewerCount) }}
                    </div>
                  </div>
                </template>
                
                <a-card-meta :title="stream.title" :description="stream.description">
                  <template #avatar>
                    <a-avatar :src="stream.tournament.logo" :alt="stream.tournament.name" />
                  </template>
                </a-card-meta>
                
                <div class="live-info">
                  <div class="teams-info">
                    <span class="team">{{ stream.teamA.name }}</span>
                    <span class="vs">VS</span>
                    <span class="team">{{ stream.teamB.name }}</span>
                  </div>
                  <div class="time-info">
                    <ClockCircleOutlined />
                    <span>{{ formatTime(stream.startTime) }}</span>
                  </div>
                </div>
              </a-card>
            </a-col>
          </a-row>
        </div>

        <!-- 空状态 -->
        <a-empty 
          v-if="filteredStreams.length === 0"
          description="暂无直播内容"
          :image="Empty.PRESENTED_IMAGE_SIMPLE"
        >
          <a-button type="primary" @click="$router.push('/tournaments')">
            查看赛事安排
          </a-button>
        </a-empty>
      </div>
    </div>
  </layout-default>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Empty } from 'ant-design-vue'
import { EyeOutlined, ClockCircleOutlined } from '@ant-design/icons-vue'
import LayoutDefault from '@/shared/components/layouts/LayoutDefault.vue'

const router = useRouter()

const selectedStatus = ref('all')
const streams = ref([
  {
    id: 1,
    title: 'FlyEsports 春季赛半决赛',
    description: '激烈对战，谁能晋级决赛？',
    thumbnail: 'https://via.placeholder.com/300x200?text=Live+Stream',
    status: 'live',
    viewerCount: 15420,
    startTime: new Date(),
    tournament: {
      name: 'FlyEsports 春季赛',
      logo: 'https://via.placeholder.com/40x40?text=T'
    },
    teamA: { name: 'Thunder Hawks' },
    teamB: { name: 'Lightning Wolves' }
  },
  {
    id: 2,
    title: 'FlyEsports 春季赛决赛',
    description: '巅峰对决，冠军之争！',
    thumbnail: 'https://via.placeholder.com/300x200?text=Upcoming',
    status: 'upcoming',
    viewerCount: null,
    startTime: new Date(Date.now() + 2 * 60 * 60 * 1000), // 2小时后
    tournament: {
      name: 'FlyEsports 春季赛',
      logo: 'https://via.placeholder.com/40x40?text=T'
    },
    teamA: { name: '待定' },
    teamB: { name: '待定' }
  }
])

const filteredStreams = computed(() => {
  if (selectedStatus.value === 'all') {
    return streams.value
  }
  return streams.value.filter(stream => stream.status === selectedStatus.value)
})

const handleStatusChange = () => {
  // 状态改变时的处理逻辑
}

const handleStreamClick = (stream: any) => {
  if (stream.status === 'live') {
    // 跳转到直播页面
    router.push(`/live/${stream.id}`)
  } else if (stream.status === 'upcoming') {
    // 跳转到比赛详情页面
    router.push(`/matches/${stream.id}`)
  }
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'live': return 'red'
    case 'upcoming': return 'blue'
    case 'ended': return 'gray'
    default: return 'default'
  }
}

const getStatusText = (status: string) => {
  switch (status) {
    case 'live': return '直播中'
    case 'upcoming': return '即将开始'
    case 'ended': return '已结束'
    default: return '未知'
  }
}

const formatViewerCount = (count: number) => {
  if (count >= 10000) {
    return `${(count / 10000).toFixed(1)}万`
  }
  return count.toString()
}

const formatTime = (time: Date) => {
  return time.toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(() => {
  // 组件挂载时加载数据
})
</script>

<style scoped>
.live-container {
  padding: 24px;
}

.live-header {
  margin-bottom: 24px;
}

.live-filters {
  margin-bottom: 24px;
}

.live-grid {
  min-height: 400px;
}

.live-card {
  height: 100%;
  transition: all 0.3s ease;
}

.live-card.live-active {
  border: 2px solid #ff4d4f;
  box-shadow: 0 4px 12px rgba(255, 77, 79, 0.15);
}

.live-card.live-upcoming {
  border: 2px solid #1890ff;
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.15);
}

.live-cover {
  position: relative;
  height: 200px;
  overflow: hidden;
}

.live-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.live-status-badge {
  position: absolute;
  top: 8px;
  left: 8px;
}

.viewer-count {
  position: absolute;
  top: 8px;
  right: 8px;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.live-info {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}

.teams-info {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 8px;
  font-weight: 600;
}

.teams-info .team {
  color: #1890ff;
}

.teams-info .vs {
  margin: 0 8px;
  color: #999;
  font-size: 12px;
}

.time-info {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
  font-size: 14px;
  gap: 4px;
}
</style>