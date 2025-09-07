<template>
  <layout-default>
    <div class="home-container">
      <!-- 欢迎横幅 -->
      <div class="welcome-banner">
        <a-card class="banner-card">
          <div class="banner-content">
            <h1 class="banner-title">欢迎来到 FlyEsports</h1>
            <p class="banner-subtitle">专业的电竞赛事管理平台，让每一场比赛都精彩纷呈</p>
            <div class="banner-actions">
              <a-space size="large">
                <a-button type="primary" size="large" @click="$router.push('/tournaments')">
                  <CalendarOutlined />
                  探索赛事
                </a-button>
                <a-button size="large" @click="$router.push('/live')">
                  <PlayCircleOutlined />
                  观看直播
                </a-button>
              </a-space>
            </div>
          </div>
        </a-card>
      </div>

      <!-- 功能导航卡片 -->
      <div class="feature-grid">
        <a-row :gutter="[16, 16]">
          <a-col :xs="24" :sm="12" :lg="8">
            <a-card hoverable class="feature-card" @click="$router.push('/live')">
              <div class="feature-content">
                <div class="feature-icon live">
                  <PlayCircleOutlined />
                </div>
                <h3>赛事直播</h3>
                <p>观看正在进行的精彩比赛，体验实时竞技魅力</p>
                <div class="feature-stats">
                  <a-tag color="red">2场直播中</a-tag>
                </div>
              </div>
            </a-card>
          </a-col>
          
          <a-col :xs="24" :sm="12" :lg="8">
            <a-card hoverable class="feature-card" @click="$router.push('/schedule')">
              <div class="feature-content">
                <div class="feature-icon schedule">
                  <CalendarOutlined />
                </div>
                <h3>赛程中心</h3>
                <p>查看详细的赛事安排，不错过任何精彩对决</p>
                <div class="feature-stats">
                  <a-tag color="blue">5场即将开始</a-tag>
                </div>
              </div>
            </a-card>
          </a-col>
          
          <a-col :xs="24" :sm="12" :lg="8">
            <a-card hoverable class="feature-card" @click="$router.push('/teams')">
              <div class="feature-content">
                <div class="feature-icon teams">
                  <TeamOutlined />
                </div>
                <h3>战队管理</h3>
                <p>创建或加入战队，与队友一起征战赛场</p>
                <div class="feature-stats">
                  <a-tag color="green">16支活跃战队</a-tag>
                </div>
              </div>
            </a-card>
          </a-col>
          
          <a-col :xs="24" :sm="12" :lg="8">
            <a-card hoverable class="feature-card" @click="$router.push('/players')">
              <div class="feature-content">
                <div class="feature-icon players">
                  <UserOutlined />
                </div>
                <h3>选手中心</h3>
                <p>浏览优秀选手资料，发现潜在队友</p>
                <div class="feature-stats">
                  <a-tag color="purple">128名注册选手</a-tag>
                </div>
              </div>
            </a-card>
          </a-col>
          
          <a-col :xs="24" :sm="12" :lg="8">
            <a-card hoverable class="feature-card" @click="$router.push('/recruitment')">
              <div class="feature-content">
                <div class="feature-icon recruitment">
                  <BulbOutlined />
                </div>
                <h3>招募专区</h3>
                <p>发布招募信息，寻找志同道合的队友</p>
                <div class="feature-stats">
                  <a-tag color="orange">12条招募信息</a-tag>
                </div>
              </div>
            </a-card>
          </a-col>
          
          <a-col :xs="24" :sm="12" :lg="8">
            <a-card hoverable class="feature-card" @click="$router.push('/hall')">
              <div class="feature-content">
                <div class="feature-icon hall">
                  <TrophyOutlined />
                </div>
                <h3>比赛大厅</h3>
                <p>参与赛事报名，查看比赛进度和结果</p>
                <div class="feature-stats">
                  <a-tag color="gold">3项赛事报名中</a-tag>
                </div>
              </div>
            </a-card>
          </a-col>
        </a-row>
      </div>

      <!-- 最新动态 -->
      <div class="news-section">
        <a-card title="最新动态" class="news-card">
          <a-list
            :data-source="newsData"
            item-layout="horizontal"
          >
            <template #renderItem="{ item: news }">
              <a-list-item>
                <a-list-item-meta :description="formatTime(news.time)">
                  <template #title>
                    <a @click="handleNewsClick(news)">{{ news.title }}</a>
                  </template>
                  <template #avatar>
                    <a-avatar :style="{ backgroundColor: news.color }">
                      <component :is="news.icon" />
                    </a-avatar>
                  </template>
                </a-list-item-meta>
              </a-list-item>
            </template>
          </a-list>
        </a-card>
      </div>
    </div>
  </layout-default>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import LayoutDefault from '@/shared/components/layouts/LayoutDefault.vue'
import {
  CalendarOutlined,
  PlayCircleOutlined,
  TeamOutlined,
  UserOutlined,
  BulbOutlined,
  TrophyOutlined,
  FireOutlined,
  NotificationOutlined,
  StarOutlined
} from '@ant-design/icons-vue'

// 新闻数据
const newsData = ref([
  {
    id: 1,
    title: 'FlyEsports春季赛决赛即将开始',
    time: new Date(Date.now() - 30 * 60 * 1000), // 30分钟前
    icon: 'FireOutlined',
    color: '#f50'
  },
  {
    id: 2,
    title: 'Thunder Hawks成功晋级半决赛',
    time: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2小时前
    icon: 'TrophyOutlined',
    color: '#52c41a'
  },
  {
    id: 3,
    title: '新的招募信息已发布',
    time: new Date(Date.now() - 4 * 60 * 60 * 1000), // 4小时前
    icon: 'NotificationOutlined',
    color: '#1890ff'
  },
  {
    id: 4,
    title: '本周精彩集锦已更新',
    time: new Date(Date.now() - 24 * 60 * 60 * 1000), // 1天前
    icon: 'StarOutlined',
    color: '#fa8c16'
  }
])

const handleNewsClick = (news: any) => {
  console.log('点击新闻:', news.title)
}

const formatTime = (time: Date) => {
  const now = Date.now()
  const diff = now - time.getTime()
  const minutes = Math.floor(diff / (1000 * 60))
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (minutes < 60) {
    return `${minutes}分钟前`
  } else if (hours < 24) {
    return `${hours}小时前`
  } else {
    return `${days}天前`
  }
}
</script>

<style scoped>
.home-container {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

/* 欢迎横幅 */
.welcome-banner {
  margin-bottom: 32px;
}

.banner-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 12px;
  overflow: hidden;
}

.banner-card :deep(.ant-card-body) {
  padding: 48px 32px;
}

.banner-content {
  text-align: center;
  color: white;
}

.banner-title {
  font-size: 36px;
  font-weight: bold;
  margin-bottom: 16px;
  color: white;
}

.banner-subtitle {
  font-size: 18px;
  margin-bottom: 32px;
  opacity: 0.9;
}

.banner-actions {
  margin-top: 24px;
}

/* 功能导航卡片 */
.feature-grid {
  margin-bottom: 32px;
}

.feature-card {
  height: 100%;
  border-radius: 8px;
  transition: all 0.3s ease;
  cursor: pointer;
}

.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.feature-content {
  text-align: center;
  padding: 16px 0;
}

.feature-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
  font-size: 28px;
  color: white;
}

.feature-icon.live {
  background: linear-gradient(135deg, #f50 0%, #ff7875 100%);
}

.feature-icon.schedule {
  background: linear-gradient(135deg, #1890ff 0%, #40a9ff 100%);
}

.feature-icon.teams {
  background: linear-gradient(135deg, #52c41a 0%, #73d13d 100%);
}

.feature-icon.players {
  background: linear-gradient(135deg, #722ed1 0%, #9254de 100%);
}

.feature-icon.recruitment {
  background: linear-gradient(135deg, #fa8c16 0%, #ffa940 100%);
}

.feature-icon.hall {
  background: linear-gradient(135deg, #faad14 0%, #ffd666 100%);
}

.feature-content h3 {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #262626;
}

.feature-content p {
  color: #666;
  margin-bottom: 16px;
  line-height: 1.5;
}

.feature-stats {
  display: flex;
  justify-content: center;
}

/* 最新动态 */
.news-section {
  margin-bottom: 32px;
}

.news-card {
  border-radius: 8px;
}

.news-card :deep(.ant-card-head-title) {
  font-size: 18px;
  font-weight: 600;
}

.news-card a {
  color: #262626;
  text-decoration: none;
  font-weight: 500;
}

.news-card a:hover {
  color: #1890ff;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .home-container {
    padding: 16px;
  }

  .banner-card :deep(.ant-card-body) {
    padding: 32px 16px;
  }

  .banner-title {
    font-size: 28px;
  }

  .banner-subtitle {
    font-size: 16px;
  }

  .banner-actions .ant-space {
    display: block;
  }

  .banner-actions .ant-btn {
    display: block;
    width: 100%;
    margin-bottom: 8px;
  }

  .feature-icon {
    width: 48px;
    height: 48px;
    font-size: 20px;
  }

  .feature-content h3 {
    font-size: 16px;
  }

  .feature-content p {
    font-size: 14px;
  }
}

@media (max-width: 480px) {
  .banner-title {
    font-size: 24px;
  }

  .banner-subtitle {
    font-size: 14px;
  }
}
</style>