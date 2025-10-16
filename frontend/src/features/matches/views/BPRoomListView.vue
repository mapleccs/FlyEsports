<template>
  <div class="bp-room-list">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">BP房间</h1>
        <p class="page-description">加入或创建BP房间进行英雄选择练习</p>
      </div>
      <div class="header-actions">
        <a-button 
          type="primary" 
          size="large"
          @click="showCreateModal = true"
        >
          <template #icon>
            <PlusOutlined />
          </template>
          创建房间
        </a-button>
      </div>
    </div>

    <!-- 筛选区域 -->
    <div class="filter-section">
      <a-card>
        <div class="filter-content">
          <a-space size="middle">
            <a-select
              v-model:value="filters.room_type"
              placeholder="房间类型"
              style="width: 120px"
              allow-clear
              @change="handleFilterChange"
            >
              <a-select-option value="custom">自定义</a-select-option>
              <a-select-option value="tournament">赛事</a-select-option>
              <a-select-option value="ranked">排位</a-select-option>
              <a-select-option value="practice">练习</a-select-option>
            </a-select>

            <a-select
              v-model:value="filters.status"
              placeholder="房间状态"
              style="width: 120px"
              allow-clear
              @change="handleFilterChange"
            >
              <a-select-option value="waiting">等待中</a-select-option>
              <a-select-option value="ready">准备中</a-select-option>
              <a-select-option value="bp_active">进行中</a-select-option>
            </a-select>

            <a-button @click="refreshRooms">
              <template #icon>
                <ReloadOutlined />
              </template>
              刷新
            </a-button>
          </a-space>
        </div>
      </a-card>
    </div>

    <!-- 房间列表 -->
    <div class="room-list-section">
      <a-tabs v-model:activeKey="activeTab" @change="handleTabChange">
        <a-tab-pane key="public" tab="公开房间">
          <RoomGrid 
            :rooms="bpRoomStore.publicRooms"
            :loading="bpRoomStore.loading"
            @join-room="handleJoinRoom"
            @view-room="handleViewRoom"
          />
        </a-tab-pane>
        
        <a-tab-pane key="my-rooms" tab="我的房间">
          <RoomGrid 
            :rooms="bpRoomStore.myRooms"
            :loading="bpRoomStore.loading"
            show-manage
            @join-room="handleJoinRoom"
            @view-room="handleViewRoom"
            @delete-room="handleDeleteRoom"
            @start-room="handleStartRoom"
          />
        </a-tab-pane>
        
        <a-tab-pane key="active" tab="参与中">
          <RoomGrid 
            :rooms="bpRoomStore.myActiveRooms"
            :loading="bpRoomStore.loading"
            @join-room="handleJoinRoom"
            @view-room="handleViewRoom"
            @leave-room="handleLeaveRoom"
          />
        </a-tab-pane>
      </a-tabs>

      <!-- 分页 -->
      <div v-if="activeTab === 'public'" class="pagination-section">
        <a-pagination
          v-model:current="bpRoomStore.pagination.page"
          v-model:page-size="bpRoomStore.pagination.per_page"
          :total="bpRoomStore.pagination.total"
          :show-size-changer="true"
          :show-quick-jumper="true"
          :show-total="(total, range) => `${range[0]}-${range[1]} / ${total} 个房间`"
          @change="handlePageChange"
          @show-size-change="handlePageSizeChange"
        />
      </div>
    </div>

    <!-- 创建房间对话框 -->
    <CreateRoomModal 
      v-model:visible="showCreateModal"
      @created="handleRoomCreated"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import { useBPRoomStore } from '@/shared/stores/bp_room'
import { useAuthStore } from '@/shared/stores/auth'
import type { BPRoom } from '@/shared/api/bp_rooms'
import RoomGrid from '../components/RoomGrid.vue'
import CreateRoomModal from '../components/CreateRoomModal.vue'

// Stores
const bpRoomStore = useBPRoomStore()
const authStore = useAuthStore()
const router = useRouter()

// 响应式数据
const activeTab = ref('public')
const showCreateModal = ref(false)

const filters = reactive({
  room_type: undefined as string | undefined,
  status: undefined as string | undefined
})

// 方法
const refreshRooms = async () => {
  switch (activeTab.value) {
    case 'public':
      await bpRoomStore.fetchPublicRooms(filters)
      break
    case 'my-rooms':
      await bpRoomStore.fetchMyRooms()
      break
    case 'active':
      await bpRoomStore.fetchMyActiveRooms()
      break
  }
}

const handleTabChange = async (key: string) => {
  activeTab.value = key
  await refreshRooms()
}

const handleFilterChange = async () => {
  if (activeTab.value === 'public') {
    bpRoomStore.pagination.page = 1
    await bpRoomStore.fetchPublicRooms(filters)
  }
}

const handlePageChange = async (page: number, pageSize: number) => {
  await bpRoomStore.fetchPublicRooms({
    ...filters,
    page,
    per_page: pageSize
  })
}

const handlePageSizeChange = async (current: number, size: number) => {
  bpRoomStore.pagination.page = 1
  await bpRoomStore.fetchPublicRooms({
    ...filters,
    page: 1,
    per_page: size
  })
}

const handleJoinRoom = async (room: BPRoom) => {
  // 导航到加入房间页面
  router.push(`/matches/bp-room/${room.id}/join`)
}

const handleViewRoom = async (room: BPRoom) => {
  // 导航到房间详情页面
  router.push(`/matches/bp-room/${room.id}`)
}

const handleLeaveRoom = async (room: BPRoom) => {
  await bpRoomStore.leaveRoom(room.id)
  await refreshRooms()
}

const handleDeleteRoom = async (room: BPRoom) => {
  await bpRoomStore.deleteRoom(room.id)
  await refreshRooms()
}

const handleStartRoom = async (room: BPRoom) => {
  await bpRoomStore.startRoom(room.id)
  await refreshRooms()
}

const handleRoomCreated = async (room: BPRoom) => {
  showCreateModal.value = false
  // 如果创建成功，跳转到房间详情页
  router.push(`/matches/bp-room/${room.id}`)
}

// 初始化
onMounted(async () => {
  if (!authStore.isAuthenticated) {
    router.push('/auth/login')
    return
  }
  
  await refreshRooms()
})
</script>

<style scoped>
.bp-room-list {
  padding: 24px;
  background: #f5f5f5;
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  padding: 0 4px;
}

.header-content {
  flex: 1;
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 8px 0;
}

.page-description {
  font-size: 16px;
  color: #6b7280;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.filter-section {
  margin-bottom: 24px;
}

.filter-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.room-list-section {
  background: white;
  border-radius: 8px;
  overflow: hidden;
}

.pagination-section {
  padding: 24px;
  display: flex;
  justify-content: center;
  border-top: 1px solid #f0f0f0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .bp-room-list {
    padding: 16px;
  }
  
  .page-header {
    flex-direction: column;
    gap: 16px;
  }
  
  .header-actions {
    width: 100%;
    justify-content: stretch;
  }
  
  .filter-content {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }
}
</style>