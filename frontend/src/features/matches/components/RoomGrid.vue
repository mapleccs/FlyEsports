<template>
  <div class="room-grid">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <a-spin size="large" />
    </div>

    <!-- 空状态 -->
    <div v-else-if="rooms.length === 0" class="empty-container">
      <a-empty>
        <template #description>
          <span>暂无房间</span>
        </template>
      </a-empty>
    </div>

    <!-- 房间列表 -->
    <div v-else class="room-cards">
      <RoomCard
        v-for="room in rooms"
        :key="room.id"
        :room="room"
        :show-manage="showManage"
        @join-room="$emit('joinRoom', room)"
        @view-room="$emit('viewRoom', room)"
        @leave-room="$emit('leaveRoom', room)"
        @delete-room="$emit('deleteRoom', room)"
        @start-room="$emit('startRoom', room)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { BPRoom } from '@/shared/api/bp_rooms'
import RoomCard from './RoomCard.vue'

// Props
interface Props {
  rooms: BPRoom[]
  loading?: boolean
  showManage?: boolean
}

defineProps<Props>()

// Events
defineEmits<{
  joinRoom: [room: BPRoom]
  viewRoom: [room: BPRoom]
  leaveRoom: [room: BPRoom]
  deleteRoom: [room: BPRoom]
  startRoom: [room: BPRoom]
}>()
</script>

<style scoped>
.room-grid {
  padding: 24px;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}

.empty-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
}

.room-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .room-cards {
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 16px;
  }
}

@media (max-width: 768px) {
  .room-grid {
    padding: 16px;
  }
  
  .room-cards {
    grid-template-columns: 1fr;
    gap: 16px;
  }
}
</style>