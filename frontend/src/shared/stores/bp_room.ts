/**
 * BP房间状态管理Store
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { bpRoomsApi, type BPRoom, type BPRoomParticipant, type CreateBPRoomRequest, type JoinRoomRequest } from '@/shared/api/bp_rooms'
import { useAuthStore } from './auth'
import { message } from 'ant-design-vue'

export const useBPRoomStore = defineStore('bpRoom', () => {
  // 状态
  const rooms = ref<BPRoom[]>([])
  const currentRoom = ref<BPRoom | null>(null)
  const myRooms = ref<BPRoom[]>([])
  const myActiveRooms = ref<BPRoom[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // 分页信息
  const pagination = ref({
    total: 0,
    page: 1,
    per_page: 20
  })

  // 获取认证store
  const authStore = useAuthStore()

  // 计算属性
  const publicRooms = computed(() => 
    rooms.value.filter(room => ['waiting', 'ready'].includes(room.status))
  )

  const isRoomCreator = computed(() => (roomId: string) => {
    const room = currentRoom.value || rooms.value.find(r => r.id === roomId)
    return room && authStore.user && room.creator_user_id === authStore.user.id
  })

  const isRoomParticipant = computed(() => (roomId: string) => {
    const room = currentRoom.value || rooms.value.find(r => r.id === roomId)
    return room && authStore.user && 
      room.participants.some(p => p.user_id === authStore.user!.id && p.is_active)
  })

  const currentUserParticipant = computed(() => {
    if (!currentRoom.value || !authStore.user) return null
    return currentRoom.value.participants.find(
      p => p.user_id === authStore.user!.id && p.is_active
    )
  })

  // 操作方法

  /**
   * 获取公开房间列表
   */
  async function fetchPublicRooms(params: {
    page?: number
    per_page?: number
    room_type?: string
  } = {}) {
    try {
      loading.value = true
      error.value = null
      
      const response = await bpRoomsApi.getPublicRooms({
        page: params.page || pagination.value.page,
        per_page: params.per_page || pagination.value.per_page,
        room_type: params.room_type
      })

      rooms.value = response.rooms
      pagination.value = {
        total: response.total,
        page: response.page,
        per_page: response.per_page
      }
    } catch (err: any) {
      error.value = err.message || '获取房间列表失败'
      message.error(error.value)
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取我创建的房间
   */
  async function fetchMyRooms() {
    try {
      loading.value = true
      error.value = null
      
      const response = await bpRoomsApi.getMyRooms()
      myRooms.value = response.rooms
    } catch (err: any) {
      error.value = err.message || '获取我的房间失败'
      message.error(error.value)
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取我参与的活跃房间
   */
  async function fetchMyActiveRooms() {
    try {
      loading.value = true
      error.value = null
      
      const response = await bpRoomsApi.getMyActiveRooms()
      myActiveRooms.value = response.rooms
    } catch (err: any) {
      error.value = err.message || '获取活跃房间失败'
      message.error(error.value)
    } finally {
      loading.value = false
    }
  }

  /**
   * 创建房间
   */
  async function createRoom(data: CreateBPRoomRequest): Promise<BPRoom | null> {
    try {
      loading.value = true
      error.value = null

      const response = await bpRoomsApi.createRoom(data)
      const newRoom = response.room

      // 添加到房间列表
      myRooms.value.unshift(newRoom)
      myActiveRooms.value.unshift(newRoom)
      
      // 如果是公开房间，也添加到公开列表
      if (['waiting', 'ready'].includes(newRoom.status)) {
        rooms.value.unshift(newRoom)
      }

      message.success('房间创建成功')
      return newRoom
    } catch (err: any) {
      error.value = err.message || '创建房间失败'
      message.error(error.value)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取房间详情
   */
  async function fetchRoom(roomId: string): Promise<BPRoom | null> {
    try {
      loading.value = true
      error.value = null

      const response = await bpRoomsApi.getRoom(roomId)
      currentRoom.value = response.room
      
      return response.room
    } catch (err: any) {
      error.value = err.message || '获取房间详情失败'
      message.error(error.value)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * 加入房间
   */
  async function joinRoom(roomId: string, data: JoinRoomRequest): Promise<boolean> {
    try {
      loading.value = true
      error.value = null

      const response = await bpRoomsApi.joinRoom(roomId, data)
      
      // 更新房间参与者列表
      if (currentRoom.value && currentRoom.value.id === roomId) {
        currentRoom.value.participants.push(response.participant)
      }

      // 更新列表中的房间信息
      const updateRoomInList = (roomList: BPRoom[]) => {
        const index = roomList.findIndex(r => r.id === roomId)
        if (index !== -1) {
          roomList[index].participants.push(response.participant)
        }
      }

      updateRoomInList(rooms.value)
      updateRoomInList(myRooms.value)
      updateRoomInList(myActiveRooms.value)

      message.success('成功加入房间')
      return true
    } catch (err: any) {
      error.value = err.message || '加入房间失败'
      message.error(error.value)
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * 离开房间
   */
  async function leaveRoom(roomId: string): Promise<boolean> {
    try {
      loading.value = true
      error.value = null

      await bpRoomsApi.leaveRoom(roomId)
      
      // 更新房间参与者列表
      if (currentRoom.value && currentRoom.value.id === roomId && authStore.user) {
        const participantIndex = currentRoom.value.participants.findIndex(
          p => p.user_id === authStore.user!.id
        )
        if (participantIndex !== -1) {
          currentRoom.value.participants[participantIndex].is_active = false
        }
      }

      // 从活跃房间列表中移除
      const activeIndex = myActiveRooms.value.findIndex(r => r.id === roomId)
      if (activeIndex !== -1) {
        myActiveRooms.value.splice(activeIndex, 1)
      }

      message.success('已离开房间')
      return true
    } catch (err: any) {
      error.value = err.message || '离开房间失败'
      message.error(error.value)
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * 删除房间 (仅创建者)
   */
  async function deleteRoom(roomId: string): Promise<boolean> {
    try {
      loading.value = true
      error.value = null

      await bpRoomsApi.deleteRoom(roomId)

      // 从所有列表中移除
      const removeFromList = (roomList: BPRoom[]) => {
        const index = roomList.findIndex(r => r.id === roomId)
        if (index !== -1) {
          roomList.splice(index, 1)
        }
      }

      removeFromList(rooms.value)
      removeFromList(myRooms.value)
      removeFromList(myActiveRooms.value)

      // 如果是当前房间，清空
      if (currentRoom.value && currentRoom.value.id === roomId) {
        currentRoom.value = null
      }

      message.success('房间已删除')
      return true
    } catch (err: any) {
      error.value = err.message || '删除房间失败'
      message.error(error.value)
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * 开始房间
   */
  async function startRoom(roomId: string): Promise<boolean> {
    try {
      loading.value = true
      error.value = null

      const response = await bpRoomsApi.startRoom(roomId)
      
      // 更新房间状态
      const updateRoomStatus = (roomList: BPRoom[]) => {
        const index = roomList.findIndex(r => r.id === roomId)
        if (index !== -1) {
          roomList[index] = response.room
        }
      }

      updateRoomStatus(rooms.value)
      updateRoomStatus(myRooms.value)
      updateRoomStatus(myActiveRooms.value)

      if (currentRoom.value && currentRoom.value.id === roomId) {
        currentRoom.value = response.room
      }

      message.success('房间已开始')
      return true
    } catch (err: any) {
      error.value = err.message || '开始房间失败'
      message.error(error.value)
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * 清空状态
   */
  function clearState() {
    rooms.value = []
    currentRoom.value = null
    myRooms.value = []
    myActiveRooms.value = []
    error.value = null
    pagination.value = {
      total: 0,
      page: 1,
      per_page: 20
    }
  }

  /**
   * 设置当前房间
   */
  function setCurrentRoom(room: BPRoom | null) {
    currentRoom.value = room
  }

  /**
   * 更新房间参与者状态
   */
  function updateParticipantStatus(roomId: string, userId: number, updates: Partial<BPRoomParticipant>) {
    const updateParticipant = (room: BPRoom) => {
      const participant = room.participants.find(p => p.user_id === userId)
      if (participant) {
        Object.assign(participant, updates)
      }
    }

    // 更新当前房间
    if (currentRoom.value && currentRoom.value.id === roomId) {
      updateParticipant(currentRoom.value)
    }

    // 更新列表中的房间
    const updateInList = (roomList: BPRoom[]) => {
      const room = roomList.find(r => r.id === roomId)
      if (room) {
        updateParticipant(room)
      }
    }

    updateInList(rooms.value)
    updateInList(myRooms.value)
    updateInList(myActiveRooms.value)
  }

  return {
    // 状态
    rooms,
    currentRoom,
    myRooms,
    myActiveRooms,
    loading,
    error,
    pagination,

    // 计算属性
    publicRooms,
    isRoomCreator,
    isRoomParticipant,
    currentUserParticipant,

    // 方法
    fetchPublicRooms,
    fetchMyRooms,
    fetchMyActiveRooms,
    createRoom,
    fetchRoom,
    joinRoom,
    leaveRoom,
    deleteRoom,
    startRoom,
    clearState,
    setCurrentRoom,
    updateParticipantStatus
  }
})