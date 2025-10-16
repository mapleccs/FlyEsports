<template>
  <div class="permission-test">
    <a-card title="权限系统测试页面" class="mb-4">
      <a-descriptions :column="2" bordered>
        <a-descriptions-item label="用户名">{{
          authStore.user?.username || '未登录'
        }}</a-descriptions-item>
        <a-descriptions-item label="认证状态">
          <a-tag :color="authStore.isAuthenticated ? 'green' : 'red'">
            {{ authStore.isAuthenticated ? '已登录' : '未登录' }}
          </a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="最高权限级别">{{
          permissions.highestRoleLevel
        }}</a-descriptions-item>
        <a-descriptions-item label="权限初始化">
          <a-tag :color="permissionStore.initialized ? 'green' : 'orange'">
            {{ permissionStore.initialized ? '已初始化' : '未初始化' }}
          </a-tag>
        </a-descriptions-item>
      </a-descriptions>
    </a-card>

    <a-row :gutter="16">
      <a-col :span="12">
        <a-card title="用户角色" class="mb-4">
          <div v-if="permissions.userRoles.value.length > 0">
            <a-tag
              v-for="role in permissions.userRoles.value"
              :key="role.id"
              :color="getRoleColor(role.level)"
              class="mb-2 mr-2"
            >
              {{ role.name }} (级别: {{ role.level }})
            </a-tag>
          </div>
          <a-empty v-else description="暂无角色" size="small" />
        </a-card>

        <a-card title="用户权限">
          <div v-if="permissions.userPermissions.value.length > 0" class="permission-list">
            <a-tag
              v-for="permission in permissions.userPermissions.value"
              :key="permission.id"
              color="blue"
              class="mb-2 mr-2"
            >
              {{ permission.name }}
            </a-tag>
          </div>
          <a-empty v-else description="暂无权限" size="small" />
        </a-card>
      </a-col>

      <a-col :span="12">
        <a-card title="权限测试" class="mb-4">
          <a-space direction="vertical" size="middle" style="width: 100%">
            <div>
              <h4>角色检查</h4>
              <a-space wrap>
                <a-tag :color="permissions.isSuperAdmin ? 'red' : 'default'">
                  超级管理员: {{ permissions.isSuperAdmin ? '是' : '否' }}
                </a-tag>
                <a-tag :color="permissions.isRegionAdmin ? 'orange' : 'default'">
                  赛区管理员: {{ permissions.isRegionAdmin ? '是' : '否' }}
                </a-tag>
                <a-tag :color="permissions.isTeamCaptain ? 'blue' : 'default'">
                  队长: {{ permissions.isTeamCaptain ? '是' : '否' }}
                </a-tag>
                <a-tag :color="permissions.isPlayer ? 'green' : 'default'">
                  选手: {{ permissions.isPlayer ? '是' : '否' }}
                </a-tag>
              </a-space>
            </div>

            <div>
              <h4>功能权限</h4>
              <a-space wrap>
                <a-tag :color="permissions.canAccessAdminPanel ? 'red' : 'default'">
                  管理后台: {{ permissions.canAccessAdminPanel ? '可访问' : '不可访问' }}
                </a-tag>
                <a-tag :color="permissions.canManageUsers ? 'orange' : 'default'">
                  用户管理: {{ permissions.canManageUsers ? '可管理' : '不可管理' }}
                </a-tag>
                <a-tag :color="permissions.canCreateTeam ? 'blue' : 'default'">
                  创建战队: {{ permissions.canCreateTeam ? '可创建' : '不可创建' }}
                </a-tag>
                <a-tag :color="permissions.canCreateTournament ? 'green' : 'default'">
                  创建赛事: {{ permissions.canCreateTournament ? '可创建' : '不可创建' }}
                </a-tag>
              </a-space>
            </div>
          </a-space>
        </a-card>

        <a-card title="指令测试">
          <div class="directive-tests">
            <div v-auth class="test-item success">✓ v-auth: 需要登录才能看到此内容</div>
            <div v-admin class="test-item admin">✓ v-admin: 需要管理员权限才能看到此内容</div>
            <div v-role="['超级管理员', '赛区管理员']" class="test-item warning">
              ✓ v-role: 需要管理员角色才能看到此内容
            </div>
            <div v-can="['管理用户', '管理系统']" class="test-item info">
              ✓ v-can: 需要用户管理或系统管理权限
            </div>
            <div v-permission="{ permissions: ['管理赛区'], any: true }" class="test-item primary">
              ✓ v-permission: 复杂权限控制
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <a-card title="权限操作测试" class="mt-4">
      <a-space>
        <a-button @click="refreshPermissions" :loading="loading" type="primary">
          刷新权限
        </a-button>
        <a-button @click="testPermissionApi" :loading="apiTesting"> 测试API权限 </a-button>
        <a-button @click="simulateRoleChange" type="dashed"> 模拟角色变更 </a-button>
        <a-button @click="clearPermissions" danger> 清除权限 </a-button>
      </a-space>
    </a-card>

    <a-card title="测试日志" class="mt-4" v-if="testLogs.length > 0">
      <a-list size="small" :data-source="testLogs">
        <template #renderItem="{ item }">
          <a-list-item>
            <a-tag
              :color="item.type === 'success' ? 'green' : item.type === 'error' ? 'red' : 'blue'"
            >
              {{ item.timestamp }}
            </a-tag>
            {{ item.message }}
          </a-list-item>
        </template>
      </a-list>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/shared/stores/auth'
import { usePermissionStore } from '@/shared/stores/permission'
import { usePermissions } from '@/shared/composables/usePermissions'
import { permissionApi } from '@/shared/api/permission'
import { message } from 'ant-design-vue'

const authStore = useAuthStore()
const permissionStore = usePermissionStore()
const permissions = usePermissions()

const loading = ref(false)
const apiTesting = ref(false)
const testLogs = ref<
  Array<{
    timestamp: string
    message: string
    type: 'info' | 'success' | 'error'
  }>
>([])

const getRoleColor = (level: number): string => {
  if (level >= 100) return 'red'
  if (level >= 80) return 'orange'
  if (level >= 60) return 'blue'
  if (level >= 40) return 'green'
  if (level >= 20) return 'cyan'
  return 'default'
}

const addLog = (message: string, type: 'info' | 'success' | 'error' = 'info') => {
  testLogs.value.unshift({
    timestamp: new Date().toLocaleTimeString(),
    message,
    type,
  })

  if (testLogs.value.length > 20) {
    testLogs.value = testLogs.value.slice(0, 20)
  }
}

const refreshPermissions = async () => {
  loading.value = true
  try {
    await authStore.loadUserPermissions()
    addLog('权限信息刷新成功', 'success')
    message.success('权限信息已更新')
  } catch (error) {
    addLog(`权限刷新失败: ${error}`, 'error')
    message.error('权限信息刷新失败')
  } finally {
    loading.value = false
  }
}

const testPermissionApi = async () => {
  apiTesting.value = true
  try {
    // 测试权限检查API
    const result = await permissionApi.checkPermission('管理用户')
    addLog(`API权限检查结果: ${result ? '有权限' : '无权限'}`, 'success')

    // 测试获取系统统计
    const stats = await permissionApi.getSystemStats()
    addLog(`系统统计获取成功: ${stats.total_users} 用户`, 'success')

    message.success('API测试完成')
  } catch (error) {
    addLog(`API测试失败: ${error}`, 'error')
    message.error('API测试失败')
  } finally {
    apiTesting.value = false
  }
}

const simulateRoleChange = () => {
  // 模拟角色变更
  const mockRoles = [{ id: 999, name: '测试角色', level: 50 }]
  const mockPermissions = [
    { id: 1, name: 'test_permission', description: '测试权限', resource: 'TEST', action: 'READ' },
  ]

  permissionStore.updatePermissions(mockRoles, mockPermissions)
  addLog('模拟角色变更完成', 'info')
  message.info('已模拟角色变更')
}

const clearPermissions = () => {
  permissionStore.clearPermissions()
  addLog('权限信息已清除', 'info')
  message.info('权限信息已清除')
}

onMounted(async () => {
  addLog('权限测试页面加载完成', 'info')

  // 如果已登录但权限未初始化，尝试加载权限
  if (authStore.isAuthenticated && !permissionStore.initialized) {
    try {
      await authStore.loadUserPermissions()
      addLog('自动加载权限信息成功', 'success')
    } catch (error) {
      addLog('自动加载权限信息失败', 'error')
    }
  }
})
</script>

<style scoped>
.permission-test {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.mb-4 {
  margin-bottom: 16px;
}

.mt-4 {
  margin-top: 16px;
}

.mb-2 {
  margin-bottom: 8px;
}

.mr-2 {
  margin-right: 8px;
}

.permission-list {
  max-height: 200px;
  overflow-y: auto;
}

.directive-tests {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.test-item {
  padding: 12px;
  border-radius: 6px;
  font-weight: 500;
}

.test-item.success {
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  color: #389e0d;
}

.test-item.admin {
  background: #fff2e8;
  border: 1px solid #ffbb96;
  color: #d4380d;
}

.test-item.warning {
  background: #fffbe6;
  border: 1px solid #ffe58f;
  color: #d48806;
}

.test-item.info {
  background: #e6f7ff;
  border: 1px solid #91d5ff;
  color: #0958d9;
}

.test-item.primary {
  background: #f9f0ff;
  border: 1px solid #d3adf7;
  color: #722ed1;
}
</style>
