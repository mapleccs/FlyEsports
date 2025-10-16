<template>
  <div class="users-management">
    <a-card>
      <template #title>
        <div class="flex justify-between items-center">
          <span>用户管理</span>
          <a-button type="primary" @click="refreshUsers" :loading="loading">
            <template #icon><ReloadOutlined /></template>
            刷新
          </a-button>
        </div>
      </template>

      <div class="mb-4">
        <a-input-search
          v-model:value="searchText"
          placeholder="搜索用户名或邮箱"
          style="width: 300px"
          @search="onSearch"
          allow-clear
        />
      </div>

      <a-table
        :columns="columns"
        :data-source="filteredUsers"
        :loading="loading"
        :pagination="pagination"
        row-key="id"
        size="small"
      >
        <template #bodyCell="{ column, record, index }">
          <template v-if="column.dataIndex === 'index'">
            {{ index + 1 }}
          </template>
          <template v-else-if="column.dataIndex === 'status'">
            <a-tag :color="record.is_active ? 'green' : 'red'">
              {{ record.is_active ? '正常' : '禁用' }}
            </a-tag>
          </template>
          <template v-else-if="column.dataIndex === 'roles'">
            <a-tag
              v-for="role in getUserRoles(record.id)"
              :key="role.id"
              :color="getRoleColor(role.level)"
              class="mr-1"
            >
              {{ role.name }}
            </a-tag>
          </template>
          <template v-else-if="column.dataIndex === 'actions'">
            <a-dropdown>
              <template #overlay>
                <a-menu>
                  <a-menu-item key="roles" @click="showRoleModal(record)">
                    <SafetyOutlined />
                    管理角色
                  </a-menu-item>
                  <a-menu-item key="permissions" @click="showPermissionModal(record)">
                    <KeyOutlined />
                    查看权限
                  </a-menu-item>
                  <a-menu-divider />
                  <a-menu-item
                    key="toggle"
                    :class="record.is_active ? 'text-red-600' : 'text-green-600'"
                    @click="toggleUserStatus(record)"
                  >
                    {{ record.is_active ? '禁用用户' : '启用用户' }}
                  </a-menu-item>
                </a-menu>
              </template>
              <a-button size="small" type="text">
                操作
                <DownOutlined />
              </a-button>
            </a-dropdown>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 角色管理弹窗 -->
    <a-modal
      v-model:open="roleModalVisible"
      title="管理用户角色"
      :confirm-loading="roleModalLoading"
      @ok="handleRoleSubmit"
      width="600px"
    >
      <div v-if="selectedUser">
        <a-descriptions :column="2" bordered class="mb-4">
          <a-descriptions-item label="用户名">{{ selectedUser.username }}</a-descriptions-item>
          <a-descriptions-item label="邮箱">{{ selectedUser.email }}</a-descriptions-item>
        </a-descriptions>

        <a-divider>当前角色</a-divider>
        <div class="mb-4">
          <a-tag
            v-for="role in getUserRoles(selectedUser.id)"
            :key="role.id"
            :color="getRoleColor(role.level)"
            closable
            @close="removeRole(selectedUser.id, role.id)"
          >
            {{ role.name }}
          </a-tag>
          <span v-if="getUserRoles(selectedUser.id).length === 0" class="text-gray-500">
            暂无角色
          </span>
        </div>

        <a-divider>分配新角色</a-divider>
        <a-form layout="vertical">
          <a-form-item label="选择角色">
            <a-select
              v-model:value="selectedRoleId"
              placeholder="请选择要分配的角色"
              style="width: 100%"
            >
              <a-select-option v-for="role in availableRoles" :key="role.id" :value="role.id">
                {{ role.name }} (级别: {{ role.level }})
              </a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="赛区" v-if="selectedRoleRequiresRegion">
            <a-select v-model:value="selectedRegionId" placeholder="请选择赛区" style="width: 100%">
              <a-select-option :value="1">华北赛区</a-select-option>
              <a-select-option :value="2">华东赛区</a-select-option>
              <a-select-option :value="3">华南赛区</a-select-option>
            </a-select>
          </a-form-item>
        </a-form>
      </div>
    </a-modal>

    <!-- 权限查看弹窗 -->
    <a-modal
      v-model:open="permissionModalVisible"
      title="用户权限详情"
      :footer="null"
      width="700px"
    >
      <div v-if="selectedUser">
        <a-descriptions :column="2" bordered class="mb-4">
          <a-descriptions-item label="用户名">{{ selectedUser.username }}</a-descriptions-item>
          <a-descriptions-item label="最高级别">{{
            getMaxUserLevel(selectedUser.id)
          }}</a-descriptions-item>
        </a-descriptions>

        <a-divider>角色列表</a-divider>
        <a-list size="small" :data-source="getUserRoles(selectedUser.id)" class="mb-4">
          <template #renderItem="{ item }">
            <a-list-item>
              <a-list-item-meta>
                <template #title>
                  <a-tag :color="getRoleColor(item.level)">{{ item.name }}</a-tag>
                </template>
                <template #description>
                  级别: {{ item.level }}
                  <span v-if="item.region_id"> | 赛区: {{ item.region_id }}</span>
                </template>
              </a-list-item-meta>
            </a-list-item>
          </template>
        </a-list>

        <a-divider>权限列表</a-divider>
        <div class="permission-grid">
          <a-tag
            v-for="permission in getUserPermissions(selectedUser.id)"
            :key="permission.id"
            color="blue"
            class="mb-2"
          >
            {{ permission.name }}
          </a-tag>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { ReloadOutlined, DownOutlined, SafetyOutlined, KeyOutlined } from '@ant-design/icons-vue'
import { permissionApi, type RoleInfo } from '@/shared/api/permission'
import type { UserRole } from '@/shared/types/auth'

// 模拟用户数据
const users = ref([
  {
    id: 1,
    username: 'admin',
    email: 'admin@flyesports.com',
    is_active: true,
    created_at: '2024-01-01',
  },
  {
    id: 2,
    username: 'region_admin',
    email: 'region@flyesports.com',
    is_active: true,
    created_at: '2024-01-02',
  },
  {
    id: 3,
    username: 'team_captain',
    email: 'captain@flyesports.com',
    is_active: true,
    created_at: '2024-01-03',
  },
])

const userRoles = ref<Record<number, UserRole[]>>({
  1: [{ id: 1, name: '超级管理员', level: 100 }],
  2: [{ id: 2, name: '赛区管理员', level: 80, region_id: 1 }],
  3: [{ id: 3, name: '队长', level: 60, region_id: 1 }],
})

const allRoles = ref<RoleInfo[]>([])
const loading = ref(false)
const searchText = ref('')
const selectedUser = ref<any>(null)
const roleModalVisible = ref(false)
const permissionModalVisible = ref(false)
const roleModalLoading = ref(false)
const selectedRoleId = ref<number>()
const selectedRegionId = ref<number>()

const columns = [
  { title: '#', dataIndex: 'index', width: 60 },
  { title: '用户名', dataIndex: 'username', key: 'username' },
  { title: '邮箱', dataIndex: 'email', key: 'email' },
  { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
  { title: '角色', dataIndex: 'roles', key: 'roles' },
  { title: '注册时间', dataIndex: 'created_at', key: 'created_at', width: 120 },
  { title: '操作', dataIndex: 'actions', key: 'actions', width: 100 },
]

const pagination = {
  total: computed(() => filteredUsers.value.length),
  pageSize: 10,
  showSizeChanger: true,
  showQuickJumper: true,
  showTotal: (total: number) => `共 ${total} 条记录`,
}

const filteredUsers = computed(() => {
  if (!searchText.value) return users.value
  const search = searchText.value.toLowerCase()
  return users.value.filter(
    user =>
      user.username.toLowerCase().includes(search) || user.email.toLowerCase().includes(search)
  )
})

const availableRoles = computed(() => {
  return allRoles.value.filter(role => {
    if (!selectedUser.value) return true
    const currentRoles = getUserRoles(selectedUser.value.id)
    return !currentRoles.some(ur => ur.id === role.id)
  })
})

const selectedRoleRequiresRegion = computed(() => {
  if (!selectedRoleId.value) return false
  const role = allRoles.value.find(r => r.id === selectedRoleId.value)
  return role && ['赛区管理员', '队长', '队员', '选手'].includes(role.name)
})

const getUserRoles = (userId: number): UserRole[] => {
  return userRoles.value[userId] || []
}

const getUserPermissions = (userId: number) => {
  // 模拟权限数据
  return [
    { id: 1, name: '系统管理' },
    { id: 2, name: '用户管理' },
    { id: 3, name: '角色管理' },
  ]
}

const getMaxUserLevel = (userId: number): number => {
  const roles = getUserRoles(userId)
  return roles.length > 0 ? Math.max(...roles.map(r => r.level)) : 0
}

const getRoleColor = (level: number): string => {
  if (level >= 100) return 'red'
  if (level >= 80) return 'orange'
  if (level >= 60) return 'blue'
  if (level >= 40) return 'green'
  if (level >= 20) return 'cyan'
  return 'default'
}

const onSearch = () => {
  // 搜索功能已通过computed实现
}

const refreshUsers = async () => {
  loading.value = true
  try {
    // 模拟刷新
    await new Promise(resolve => setTimeout(resolve, 1000))
    message.success('刷新成功')
  } finally {
    loading.value = false
  }
}

const loadRoles = async () => {
  try {
    const roles = await permissionApi.getAllRoles()
    allRoles.value = roles
  } catch (error) {
    console.error('Failed to load roles:', error)
  }
}

const showRoleModal = (user: any) => {
  selectedUser.value = user
  selectedRoleId.value = undefined
  selectedRegionId.value = undefined
  roleModalVisible.value = true
}

const showPermissionModal = (user: any) => {
  selectedUser.value = user
  permissionModalVisible.value = true
}

const handleRoleSubmit = async () => {
  if (!selectedUser.value || !selectedRoleId.value) {
    message.error('请选择角色')
    return
  }

  roleModalLoading.value = true
  try {
    await permissionApi.assignRole(
      selectedUser.value.id,
      selectedRoleId.value,
      selectedRegionId.value
    )

    // 更新本地数据
    const role = allRoles.value.find(r => r.id === selectedRoleId.value)
    if (role) {
      if (!userRoles.value[selectedUser.value.id]) {
        userRoles.value[selectedUser.value.id] = []
      }
      userRoles.value[selectedUser.value.id].push({
        id: role.id,
        name: role.name,
        level: role.level,
        region_id: selectedRegionId.value,
      })
    }

    message.success('角色分配成功')
    roleModalVisible.value = false
  } catch (error) {
    message.error('角色分配失败')
  } finally {
    roleModalLoading.value = false
  }
}

const removeRole = async (userId: number, roleId: number) => {
  try {
    await permissionApi.revokeRole(userId, roleId)

    // 更新本地数据
    if (userRoles.value[userId]) {
      userRoles.value[userId] = userRoles.value[userId].filter(r => r.id !== roleId)
    }

    message.success('角色移除成功')
  } catch (error) {
    message.error('角色移除失败')
  }
}

const toggleUserStatus = async (user: any) => {
  // 模拟切换用户状态
  user.is_active = !user.is_active
  message.success(`用户${user.is_active ? '启用' : '禁用'}成功`)
}

onMounted(() => {
  loadRoles()
})
</script>

<style scoped>
.users-management {
  padding: 24px;
}

.flex {
  display: flex;
}

.justify-between {
  justify-content: space-between;
}

.items-center {
  align-items: center;
}

.mb-4 {
  margin-bottom: 16px;
}

.mb-2 {
  margin-bottom: 8px;
}

.mr-1 {
  margin-right: 4px;
}

.text-gray-500 {
  color: #9ca3af;
}

.text-red-600 {
  color: #dc2626;
}

.text-green-600 {
  color: #059669;
}

.permission-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
