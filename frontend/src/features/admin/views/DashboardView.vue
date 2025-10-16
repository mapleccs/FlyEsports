<template>
  <div class="admin-dashboard">
    <a-row :gutter="24" class="mb-6">
      <a-col :span="6">
        <a-card>
          <a-statistic
            title="总用户数"
            :value="stats.total_users"
            :loading="statsLoading"
            value-style="color: #3f8600"
          >
            <template #prefix>
              <UserOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic
            title="活跃用户"
            :value="stats.active_users"
            :loading="statsLoading"
            value-style="color: #1890ff"
          >
            <template #prefix>
              <TeamOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic
            title="战队数量"
            :value="stats.total_teams"
            :loading="statsLoading"
            value-style="color: #722ed1"
          >
            <template #prefix>
              <CrownOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic
            title="比赛场次"
            :value="stats.total_matches"
            :loading="statsLoading"
            value-style="color: #eb2f96"
          >
            <template #prefix>
              <TrophyOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="24">
      <a-col :span="12">
        <a-card title="快速操作" class="h-full">
          <div class="quick-actions">
            <a-button-group>
              <a-button type="primary" @click="$router.push('/admin/users')" v-can="'管理用户'">
                <UserOutlined />
                用户管理
              </a-button>
              <a-button @click="$router.push('/admin/roles')" v-can="'管理角色'">
                <SafetyOutlined />
                角色权限
              </a-button>
              <a-button @click="$router.push('/admin/regions')" v-can="'管理赛区'">
                <EnvironmentOutlined />
                赛区管理
              </a-button>
            </a-button-group>
          </div>
        </a-card>
      </a-col>
      <a-col :span="12">
        <a-card title="系统状态">
          <div class="system-status">
            <a-descriptions :column="1" bordered size="small">
              <a-descriptions-item label="系统状态">
                <a-tag :color="stats.system_health === 'healthy' ? 'green' : 'red'">
                  {{ stats.system_health === 'healthy' ? '正常' : '异常' }}
                </a-tag>
              </a-descriptions-item>
              <a-descriptions-item label="权限系统">
                <a-tag color="green">已启用</a-tag>
              </a-descriptions-item>
              <a-descriptions-item label="当前权限">
                <a-tag v-for="role in userRoles" :key="role.id" color="blue" class="mr-1">
                  {{ role.name }}
                </a-tag>
              </a-descriptions-item>
            </a-descriptions>
          </div>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import {
  UserOutlined,
  TeamOutlined,
  CrownOutlined,
  TrophyOutlined,
  SafetyOutlined,
  EnvironmentOutlined,
} from '@ant-design/icons-vue'
import { permissionApi, type SystemStats } from '@/shared/api/permission'
import { usePermissions } from '@/shared/composables/usePermissions'
import { message } from 'ant-design-vue'

const { userRoles } = usePermissions()

const stats = ref<SystemStats>({
  total_users: 0,
  active_users: 0,
  total_teams: 0,
  total_tournaments: 0,
  total_matches: 0,
  system_health: 'healthy',
})

const statsLoading = ref(false)

const loadStats = async () => {
  statsLoading.value = true
  try {
    const data = await permissionApi.getSystemStats()
    stats.value = data
  } catch (error) {
    console.error('Failed to load system stats:', error)
    message.error('加载系统统计失败')
  } finally {
    statsLoading.value = false
  }
}

onMounted(() => {
  loadStats()
})
</script>

<style scoped>
.admin-dashboard {
  padding: 24px;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.system-status {
  min-height: 200px;
}

.mb-6 {
  margin-bottom: 24px;
}

.h-full {
  height: 100%;
}

.mr-1 {
  margin-right: 4px;
}
</style>
