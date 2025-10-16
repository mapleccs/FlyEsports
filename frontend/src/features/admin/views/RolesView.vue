<template>
  <div class="roles-management">
    <a-card>
      <template #title>
        <div class="flex justify-between items-center">
          <span>角色权限管理</span>
          <a-button type="primary" @click="refreshRoles" :loading="loading">
            <template #icon><ReloadOutlined /></template>
            刷新
          </a-button>
        </div>
      </template>

      <a-table
        :columns="columns"
        :data-source="roles"
        :loading="loading"
        row-key="id"
        size="small"
        :pagination="{ pageSize: 20 }"
      >
        <template #bodyCell="{ column, record, index }">
          <template v-if="column.dataIndex === 'index'">
            {{ index + 1 }}
          </template>
          <template v-else-if="column.dataIndex === 'level'">
            <a-tag :color="getRoleColor(record.level)">
              {{ record.level }}
            </a-tag>
          </template>
          <template v-else-if="column.dataIndex === 'is_system'">
            <a-tag :color="record.is_system ? 'blue' : 'green'">
              {{ record.is_system ? '系统角色' : '自定义角色' }}
            </a-tag>
          </template>
          <template v-else-if="column.dataIndex === 'actions'">
            <a-button-group size="small">
              <a-button @click="showPermissions(record)">
                <EyeOutlined />
                查看权限
              </a-button>
              <a-button v-if="!record.is_system" @click="editRole(record)" type="primary">
                <EditOutlined />
                编辑
              </a-button>
            </a-button-group>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 权限详情弹窗 -->
    <a-modal
      v-model:open="permissionModalVisible"
      :title="`角色权限：${selectedRole?.name}`"
      :footer="null"
      width="800px"
    >
      <div v-if="selectedRole">
        <a-descriptions :column="3" bordered class="mb-4">
          <a-descriptions-item label="角色名称">{{ selectedRole.name }}</a-descriptions-item>
          <a-descriptions-item label="权限级别">{{ selectedRole.level }}</a-descriptions-item>
          <a-descriptions-item label="角色类型">
            {{ selectedRole.is_system ? '系统角色' : '自定义角色' }}
          </a-descriptions-item>
          <a-descriptions-item label="描述" :span="3">
            {{ selectedRole.description || '暂无描述' }}
          </a-descriptions-item>
        </a-descriptions>

        <a-divider>权限列表</a-divider>
        <div v-if="rolePermissions.length > 0">
          <div class="permission-categories">
            <div
              v-for="category in permissionCategories"
              :key="category.name"
              class="permission-category mb-4"
            >
              <h4>{{ category.name }}</h4>
              <div class="permission-tags">
                <a-tag
                  v-for="permission in category.permissions"
                  :key="permission.id"
                  color="blue"
                  class="mb-2 mr-2"
                >
                  {{ permission.name }}
                </a-tag>
              </div>
            </div>
          </div>
        </div>
        <a-empty v-else description="该角色暂无权限" />
      </div>
    </a-modal>

    <!-- 编辑角色弹窗 -->
    <a-modal
      v-model:open="editModalVisible"
      :title="editingRole ? '编辑角色' : '创建角色'"
      :confirm-loading="editLoading"
      @ok="handleEditSubmit"
      width="600px"
    >
      <a-form ref="editFormRef" :model="editForm" :rules="editFormRules" layout="vertical">
        <a-form-item name="name" label="角色名称">
          <a-input
            v-model:value="editForm.name"
            placeholder="请输入角色名称"
            :disabled="editingRole?.is_system"
          />
        </a-form-item>

        <a-form-item name="description" label="角色描述">
          <a-textarea v-model:value="editForm.description" placeholder="请输入角色描述" :rows="3" />
        </a-form-item>

        <a-form-item name="level" label="权限级别">
          <a-slider
            v-model:value="editForm.level"
            :min="1"
            :max="99"
            :marks="levelMarks"
            :disabled="editingRole?.is_system"
          />
        </a-form-item>

        <a-form-item name="permissions" label="权限选择">
          <a-transfer
            v-model:target-keys="editForm.permissionIds"
            :data-source="allPermissions"
            :titles="['可选权限', '已选权限']"
            :render="(item: any) => item.name"
            :disabled="editingRole?.is_system"
            show-search
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { ReloadOutlined, EyeOutlined, EditOutlined } from '@ant-design/icons-vue'
import { permissionApi, type RoleInfo, type PermissionInfo } from '@/shared/api/permission'

const roles = ref<RoleInfo[]>([])
const allPermissions = ref<PermissionInfo[]>([])
const rolePermissions = ref<PermissionInfo[]>([])
const loading = ref(false)
const selectedRole = ref<RoleInfo | null>(null)
const permissionModalVisible = ref(false)
const editModalVisible = ref(false)
const editLoading = ref(false)
const editingRole = ref<RoleInfo | null>(null)

const editForm = ref({
  name: '',
  description: '',
  level: 10,
  permissionIds: [] as string[],
})

const editFormRules = {
  name: [
    { required: true, message: '请输入角色名称' },
    { min: 2, max: 20, message: '角色名称长度为2-20个字符' },
  ],
  level: [{ required: true, message: '请设置权限级别' }],
}

const levelMarks = {
  10: '普通用户',
  30: '选手',
  50: '队长',
  80: '赛区管理员',
  99: '高级管理员',
}

const columns = [
  { title: '#', dataIndex: 'index', width: 60 },
  { title: '角色名称', dataIndex: 'name', key: 'name' },
  { title: '权限级别', dataIndex: 'level', key: 'level', width: 120 },
  { title: '角色类型', dataIndex: 'is_system', key: 'is_system', width: 120 },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '操作', dataIndex: 'actions', key: 'actions', width: 200 },
]

const permissionCategories = computed(() => {
  const categories = new Map()

  rolePermissions.value.forEach(permission => {
    const category = permission.resource || '其他'
    if (!categories.has(category)) {
      categories.set(category, {
        name: getCategoryDisplayName(category),
        permissions: [],
      })
    }
    categories.get(category).permissions.push(permission)
  })

  return Array.from(categories.values())
})

const getCategoryDisplayName = (category: string): string => {
  const displayNames: Record<string, string> = {
    SYSTEM: '系统管理',
    USER: '用户管理',
    ROLE: '角色管理',
    REGION: '赛区管理',
    TEAM: '战队管理',
    PLAYER: '选手管理',
    MATCH: '比赛管理',
    TOURNAMENT: '赛事管理',
  }
  return displayNames[category] || category
}

const getRoleColor = (level: number): string => {
  if (level >= 100) return 'red'
  if (level >= 80) return 'orange'
  if (level >= 60) return 'blue'
  if (level >= 40) return 'green'
  if (level >= 20) return 'cyan'
  return 'default'
}

const refreshRoles = async () => {
  loading.value = true
  try {
    const [rolesData, permissionsData] = await Promise.all([
      permissionApi.getAllRoles(),
      permissionApi.getAllPermissions(),
    ])
    roles.value = rolesData
    allPermissions.value = permissionsData.map(p => ({
      ...p,
      key: p.id.toString(),
      title: p.name,
    }))
    message.success('刷新成功')
  } catch (error) {
    console.error('Failed to load data:', error)
    message.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

const showPermissions = async (role: RoleInfo) => {
  selectedRole.value = role

  // 模拟获取角色权限
  const mockPermissions = getMockRolePermissions(role.level)
  rolePermissions.value = mockPermissions
  permissionModalVisible.value = true
}

const getMockRolePermissions = (level: number): PermissionInfo[] => {
  // 根据级别返回模拟权限数据
  const basePermissions = [
    { id: 1, name: '查看公开数据', description: '', resource: 'SYSTEM', action: 'READ' },
    { id: 2, name: '发表评论', description: '', resource: 'SYSTEM', action: 'CREATE' },
  ]

  if (level >= 30) {
    basePermissions.push(
      { id: 3, name: '参与比赛', description: '', resource: 'MATCH', action: 'CREATE' },
      { id: 4, name: '查看统计', description: '', resource: 'PLAYER', action: 'READ' }
    )
  }

  if (level >= 50) {
    basePermissions.push(
      { id: 5, name: '创建战队', description: '', resource: 'TEAM', action: 'CREATE' },
      { id: 6, name: '管理战队', description: '', resource: 'TEAM', action: 'MANAGE' }
    )
  }

  if (level >= 80) {
    basePermissions.push(
      { id: 7, name: '管理赛区', description: '', resource: 'REGION', action: 'MANAGE' },
      { id: 8, name: '创建赛事', description: '', resource: 'TOURNAMENT', action: 'CREATE' }
    )
  }

  if (level >= 100) {
    basePermissions.push(
      { id: 9, name: '系统管理', description: '', resource: 'SYSTEM', action: 'MANAGE' },
      { id: 10, name: '用户管理', description: '', resource: 'USER', action: 'MANAGE' }
    )
  }

  return basePermissions
}

const editRole = (role: RoleInfo) => {
  editingRole.value = role
  editForm.value = {
    name: role.name,
    description: role.description || '',
    level: role.level,
    permissionIds: getMockRolePermissions(role.level).map(p => p.id.toString()),
  }
  editModalVisible.value = true
}

const handleEditSubmit = async () => {
  editLoading.value = true
  try {
    // 模拟保存
    await new Promise(resolve => setTimeout(resolve, 1000))

    if (editingRole.value) {
      // 更新现有角色
      const index = roles.value.findIndex(r => r.id === editingRole.value!.id)
      if (index !== -1) {
        roles.value[index] = {
          ...roles.value[index],
          name: editForm.value.name,
          description: editForm.value.description,
          level: editForm.value.level,
        }
      }
      message.success('角色更新成功')
    } else {
      // 创建新角色
      const newRole: RoleInfo = {
        id: Date.now(),
        name: editForm.value.name,
        description: editForm.value.description,
        level: editForm.value.level,
        is_system: false,
      }
      roles.value.push(newRole)
      message.success('角色创建成功')
    }

    editModalVisible.value = false
    resetEditForm()
  } catch (error) {
    message.error('操作失败')
  } finally {
    editLoading.value = false
  }
}

const resetEditForm = () => {
  editingRole.value = null
  editForm.value = {
    name: '',
    description: '',
    level: 10,
    permissionIds: [],
  }
}

onMounted(() => {
  refreshRoles()
})
</script>

<style scoped>
.roles-management {
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

.mr-2 {
  margin-right: 8px;
}

.permission-categories {
  max-height: 400px;
  overflow-y: auto;
}

.permission-category h4 {
  margin-bottom: 12px;
  color: #1890ff;
  font-weight: 600;
}

.permission-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
