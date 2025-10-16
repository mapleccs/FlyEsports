<template>
  <layout-default>
    <div class="recruitment-container">
      <div class="recruitment-header">
        <a-page-header title="招募专区" sub-title="发布招募信息，寻找志同道合的队友">
          <template #extra>
            <a-space>
              <a-button @click="$router.push('/recruitment/create')">
                <PlusOutlined />
                发布招募
              </a-button>
              <a-button type="primary" @click="handleMyRecruitments">
                <UserOutlined />
                我的招募
              </a-button>
            </a-space>
          </template>
        </a-page-header>
      </div>

      <div class="recruitment-content">
        <!-- 筛选器 -->
        <div class="recruitment-filters">
          <a-row :gutter="16">
            <a-col :xs="24" :sm="12" :md="6">
              <a-select
                v-model:value="selectedType"
                placeholder="招募类型"
                style="width: 100%"
                @change="handleTypeChange"
              >
                <a-select-option value="">全部类型</a-select-option>
                <a-select-option value="player">招募队员</a-select-option>
                <a-select-option value="team">寻找战队</a-select-option>
                <a-select-option value="substitute">招募替补</a-select-option>
              </a-select>
            </a-col>
            <a-col :xs="24" :sm="12" :md="6">
              <a-select
                v-model:value="selectedPosition"
                placeholder="游戏位置"
                style="width: 100%"
                @change="handlePositionChange"
              >
                <a-select-option value="">全部位置</a-select-option>
                <a-select-option value="top">上单</a-select-option>
                <a-select-option value="jungle">打野</a-select-option>
                <a-select-option value="mid">中单</a-select-option>
                <a-select-option value="adc">ADC</a-select-option>
                <a-select-option value="support">辅助</a-select-option>
              </a-select>
            </a-col>
            <a-col :xs="24" :sm="12" :md="6">
              <a-select
                v-model:value="selectedRank"
                placeholder="段位要求"
                style="width: 100%"
                @change="handleRankChange"
              >
                <a-select-option value="">全部段位</a-select-option>
                <a-select-option value="bronze">青铜</a-select-option>
                <a-select-option value="silver">白银</a-select-option>
                <a-select-option value="gold">黄金</a-select-option>
                <a-select-option value="platinum">铂金</a-select-option>
                <a-select-option value="diamond">钻石</a-select-option>
                <a-select-option value="master">大师</a-select-option>
              </a-select>
            </a-col>
            <a-col :xs="24" :sm="12" :md="6">
              <a-input
                v-model:value="searchKeyword"
                placeholder="搜索关键词"
                @pressEnter="handleSearch"
              >
                <template #suffix>
                  <SearchOutlined @click="handleSearch" />
                </template>
              </a-input>
            </a-col>
          </a-row>
        </div>

        <!-- 招募列表 -->
        <div class="recruitment-list">
          <a-row :gutter="[16, 16]">
            <a-col
              :xs="24"
              :sm="12"
              :xl="8"
              v-for="recruitment in filteredRecruitments"
              :key="recruitment.id"
            >
              <a-card class="recruitment-card" hoverable @click="handleCardClick(recruitment)">
                <template #title>
                  <div class="card-title">
                    <a-tag :color="getTypeColor(recruitment.type)">
                      {{ getTypeText(recruitment.type) }}
                    </a-tag>
                    <span class="recruitment-title">{{ recruitment.title }}</span>
                  </div>
                </template>

                <template #extra>
                  <a-dropdown>
                    <a @click.prevent.stop>
                      <MoreOutlined />
                    </a>
                    <template #overlay>
                      <a-menu @click="handleMenuClick($event, recruitment)">
                        <a-menu-item key="contact">联系发布者</a-menu-item>
                        <a-menu-item key="share">分享招募</a-menu-item>
                        <a-menu-item key="report">举报</a-menu-item>
                      </a-menu>
                    </template>
                  </a-dropdown>
                </template>

                <div class="recruitment-content-body">
                  <!-- 发布者信息 -->
                  <div class="publisher-info">
                    <a-space>
                      <a-avatar
                        :src="recruitment.publisher.avatar"
                        :alt="recruitment.publisher.username"
                      />
                      <div>
                        <div class="publisher-name">{{ recruitment.publisher.username }}</div>
                        <div class="publish-time">{{ formatTime(recruitment.createdAt) }}</div>
                      </div>
                    </a-space>
                  </div>

                  <!-- 招募详情 -->
                  <div class="recruitment-details">
                    <p class="description">{{ recruitment.description }}</p>

                    <div class="requirements">
                      <a-row :gutter="8">
                        <a-col :span="12" v-if="recruitment.position">
                          <div class="requirement-item">
                            <span class="label">位置:</span>
                            <a-tag size="small">{{ getPositionText(recruitment.position) }}</a-tag>
                          </div>
                        </a-col>
                        <a-col :span="12" v-if="recruitment.rankRequirement">
                          <div class="requirement-item">
                            <span class="label">段位:</span>
                            <a-tag size="small" color="gold">{{
                              getRankText(recruitment.rankRequirement)
                            }}</a-tag>
                          </div>
                        </a-col>
                        <a-col :span="12" v-if="recruitment.experience">
                          <div class="requirement-item">
                            <span class="label">经验:</span>
                            <span class="value">{{ recruitment.experience }}年</span>
                          </div>
                        </a-col>
                        <a-col :span="12" v-if="recruitment.availableTime">
                          <div class="requirement-item">
                            <span class="label">时间:</span>
                            <span class="value">{{ recruitment.availableTime }}</span>
                          </div>
                        </a-col>
                      </a-row>
                    </div>

                    <!-- 联系方式 -->
                    <div class="contact-info" v-if="recruitment.contact">
                      <ContactsOutlined />
                      <span>{{ recruitment.contact.type }}: {{ recruitment.contact.value }}</span>
                    </div>
                  </div>

                  <!-- 操作按钮 -->
                  <div class="recruitment-actions">
                    <a-space>
                      <a-button
                        type="primary"
                        size="small"
                        @click.stop="handleApply(recruitment)"
                        :disabled="recruitment.status === 'closed'"
                      >
                        <SendOutlined />
                        {{ recruitment.type === 'team' ? '申请加入' : '推荐自己' }}
                      </a-button>
                      <a-button size="small" @click.stop="handleContact(recruitment)">
                        <MessageOutlined />
                        私信
                      </a-button>
                      <a-button
                        size="small"
                        @click.stop="handleFavorite(recruitment)"
                        :class="{ favorited: recruitment.isFavorited }"
                      >
                        <HeartOutlined :style="{ color: recruitment.isFavorited ? '#f50' : '' }" />
                        {{ recruitment.favoriteCount || 0 }}
                      </a-button>
                    </a-space>
                  </div>

                  <!-- 状态标签 -->
                  <div class="status-badge" v-if="recruitment.status === 'closed'">
                    <a-tag color="red">已结束</a-tag>
                  </div>
                </div>
              </a-card>
            </a-col>
          </a-row>
        </div>

        <!-- 加载更多 -->
        <div class="load-more" v-if="hasMore">
          <a-button :loading="loading" @click="handleLoadMore" block> 加载更多 </a-button>
        </div>

        <!-- 空状态 -->
        <a-empty
          v-if="filteredRecruitments.length === 0 && !loading"
          description="暂无招募信息"
          :image="Empty.PRESENTED_IMAGE_SIMPLE"
        >
          <a-button type="primary" @click="$router.push('/recruitment/create')">
            发布招募
          </a-button>
        </a-empty>
      </div>
    </div>
  </layout-default>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Empty, message } from 'ant-design-vue'
import {
  PlusOutlined,
  UserOutlined,
  SearchOutlined,
  MoreOutlined,
  ContactsOutlined,
  SendOutlined,
  MessageOutlined,
  HeartOutlined,
} from '@ant-design/icons-vue'
import LayoutDefault from '@/shared/components/layouts/LayoutDefault.vue'

const router = useRouter()

// 筛选状态
const selectedType = ref('')
const selectedPosition = ref('')
const selectedRank = ref('')
const searchKeyword = ref('')

// 加载状态
const loading = ref(false)
const hasMore = ref(true)

// 模拟数据
const recruitments = ref([
  {
    id: 1,
    type: 'player',
    title: '寻找黄金段位ADC选手',
    description:
      '我们是一支以友谊为基础的业余战队，目前缺少一名ADC选手。希望你有良好的游戏态度和团队合作精神。',
    position: 'adc',
    rankRequirement: 'gold',
    experience: 2,
    availableTime: '晚上19:00-22:00',
    publisher: {
      id: 1,
      username: 'TeamLeader',
      avatar: 'https://via.placeholder.com/40x40?text=TL',
    },
    contact: {
      type: 'QQ',
      value: '123456789',
    },
    status: 'open',
    createdAt: new Date(Date.now() - 2 * 60 * 60 * 1000),
    favoriteCount: 5,
    isFavorited: false,
  },
  {
    id: 2,
    type: 'team',
    title: '钻石打野寻找战队',
    description: '本人钻石段位打野，有3年比赛经验，熟悉版本节奏，寻找一支有志于参加比赛的战队。',
    position: 'jungle',
    rankRequirement: 'diamond',
    experience: 3,
    availableTime: '周末全天',
    publisher: {
      id: 2,
      username: 'JungleKing',
      avatar: 'https://via.placeholder.com/40x40?text=JK',
    },
    contact: {
      type: '微信',
      value: 'jungleking2024',
    },
    status: 'open',
    createdAt: new Date(Date.now() - 5 * 60 * 60 * 1000),
    favoriteCount: 12,
    isFavorited: true,
  },
])

const filteredRecruitments = computed(() => {
  return recruitments.value.filter(recruitment => {
    if (selectedType.value && recruitment.type !== selectedType.value) return false
    if (selectedPosition.value && recruitment.position !== selectedPosition.value) return false
    if (selectedRank.value && recruitment.rankRequirement !== selectedRank.value) return false
    if (searchKeyword.value) {
      const keyword = searchKeyword.value.toLowerCase()
      return (
        recruitment.title.toLowerCase().includes(keyword) ||
        recruitment.description.toLowerCase().includes(keyword)
      )
    }
    return true
  })
})

// 事件处理
const handleTypeChange = () => {}
const handlePositionChange = () => {}
const handleRankChange = () => {}
const handleSearch = () => {}

const handleCardClick = (recruitment: any) => {
  router.push(`/recruitment/${recruitment.id}`)
}

const handleMenuClick = ({ key }: { key: string }, recruitment: any) => {
  switch (key) {
    case 'contact':
      handleContact(recruitment)
      break
    case 'share':
      handleShare(recruitment)
      break
    case 'report':
      handleReport(recruitment)
      break
  }
}

const handleApply = (recruitment: any) => {
  message.success('申请已发送')
}

const handleContact = (recruitment: any) => {
  // 打开私信对话
  message.info('跳转到私信界面')
}

const handleFavorite = (recruitment: any) => {
  recruitment.isFavorited = !recruitment.isFavorited
  recruitment.favoriteCount += recruitment.isFavorited ? 1 : -1
}

const handleShare = (recruitment: any) => {
  message.success('链接已复制到剪贴板')
}

const handleReport = (recruitment: any) => {
  message.info('举报功能开发中')
}

const handleMyRecruitments = () => {
  router.push('/recruitment/my')
}

const handleLoadMore = () => {
  loading.value = true
  setTimeout(() => {
    loading.value = false
    hasMore.value = false
  }, 1000)
}

// 工具函数
const getTypeColor = (type: string) => {
  switch (type) {
    case 'player':
      return 'blue'
    case 'team':
      return 'green'
    case 'substitute':
      return 'orange'
    default:
      return 'default'
  }
}

const getTypeText = (type: string) => {
  switch (type) {
    case 'player':
      return '招募队员'
    case 'team':
      return '寻找战队'
    case 'substitute':
      return '招募替补'
    default:
      return '未知'
  }
}

const getPositionText = (position: string) => {
  const positions: Record<string, string> = {
    top: '上单',
    jungle: '打野',
    mid: '中单',
    adc: 'ADC',
    support: '辅助',
  }
  return positions[position] || position
}

const getRankText = (rank: string) => {
  const ranks: Record<string, string> = {
    bronze: '青铜',
    silver: '白银',
    gold: '黄金',
    platinum: '铂金',
    diamond: '钻石',
    master: '大师',
  }
  return ranks[rank] || rank
}

const formatTime = (date: Date) => {
  const now = Date.now()
  const diff = now - date.getTime()
  const hours = Math.floor(diff / (1000 * 60 * 60))

  if (hours < 1) return '刚刚'
  if (hours < 24) return `${hours}小时前`

  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}天前`

  return date.toLocaleDateString('zh-CN')
}

onMounted(() => {
  // 加载数据
})
</script>

<style scoped>
.recruitment-container {
  padding: 24px;
}

.recruitment-header {
  margin-bottom: 24px;
}

.recruitment-filters {
  margin-bottom: 24px;
  padding: 16px;
  background: #fafafa;
  border-radius: 6px;
}

.recruitment-card {
  height: 100%;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.recruitment-title {
  font-weight: 600;
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.recruitment-content-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.publisher-info {
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.publisher-name {
  font-weight: 600;
  color: #1890ff;
}

.publish-time {
  font-size: 12px;
  color: #999;
}

.description {
  margin: 0;
  color: #666;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.requirements {
  background: #f9f9f9;
  padding: 12px;
  border-radius: 4px;
}

.requirement-item {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 4px;
}

.requirement-item:last-child {
  margin-bottom: 0;
}

.label {
  font-size: 12px;
  color: #666;
  min-width: 30px;
}

.value {
  font-size: 12px;
}

.contact-info {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #666;
  font-size: 12px;
}

.recruitment-actions {
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}

.favorited {
  color: #f50 !important;
}

.status-badge {
  position: absolute;
  top: 8px;
  right: 8px;
}

.load-more {
  margin-top: 24px;
}

@media (max-width: 768px) {
  .requirements {
    font-size: 12px;
  }

  .requirement-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
  }
}
</style>
