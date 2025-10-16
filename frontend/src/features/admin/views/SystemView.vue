<template>
  <div class="system-management">
    <a-row :gutter="24">
      <a-col :span="12">
        <a-card title="系统配置">
          <a-form layout="vertical">
            <a-form-item label="系统名称">
              <a-input v-model:value="systemConfig.name" />
            </a-form-item>
            <a-form-item label="系统描述">
              <a-textarea v-model:value="systemConfig.description" :rows="3" />
            </a-form-item>
            <a-form-item label="维护模式">
              <a-switch v-model:checked="systemConfig.maintenance_mode" />
            </a-form-item>
            <a-form-item>
              <a-button type="primary" @click="saveConfig"> 保存配置 </a-button>
            </a-form-item>
          </a-form>
        </a-card>
      </a-col>

      <a-col :span="12">
        <a-card title="系统日志">
          <div class="log-container">
            <a-list size="small" :data-source="systemLogs" :pagination="{ pageSize: 10 }">
              <template #renderItem="{ item }">
                <a-list-item>
                  <a-list-item-meta>
                    <template #title>
                      <a-tag :color="getLogColor(item.level)">{{ item.level }}</a-tag>
                      {{ item.message }}
                    </template>
                    <template #description>
                      {{ item.timestamp }}
                    </template>
                  </a-list-item-meta>
                </a-list-item>
              </template>
            </a-list>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <a-card title="系统监控" class="mt-6">
      <a-row :gutter="24">
        <a-col :span="8">
          <a-statistic
            title="CPU使用率"
            :value="systemStatus.cpu_usage"
            suffix="%"
            :value-style="{ color: systemStatus.cpu_usage > 80 ? '#cf1322' : '#3f8600' }"
          />
        </a-col>
        <a-col :span="8">
          <a-statistic
            title="内存使用率"
            :value="systemStatus.memory_usage"
            suffix="%"
            :value-style="{ color: systemStatus.memory_usage > 80 ? '#cf1322' : '#3f8600' }"
          />
        </a-col>
        <a-col :span="8">
          <a-statistic
            title="磁盘使用率"
            :value="systemStatus.disk_usage"
            suffix="%"
            :value-style="{ color: systemStatus.disk_usage > 80 ? '#cf1322' : '#3f8600' }"
          />
        </a-col>
      </a-row>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'

const systemConfig = ref({
  name: 'FlyEsports',
  description: '电竞赛事管理平台',
  maintenance_mode: false,
})

const systemStatus = ref({
  cpu_usage: 35,
  memory_usage: 62,
  disk_usage: 45,
})

const systemLogs = ref([
  {
    level: 'INFO',
    message: '用户登录成功',
    timestamp: '2024-01-10 10:30:15',
  },
  {
    level: 'WARN',
    message: '权限验证失败',
    timestamp: '2024-01-10 10:25:32',
  },
  {
    level: 'ERROR',
    message: '数据库连接异常',
    timestamp: '2024-01-10 10:20:45',
  },
])

const getLogColor = (level: string): string => {
  const colors: Record<string, string> = {
    INFO: 'blue',
    WARN: 'orange',
    ERROR: 'red',
    DEBUG: 'green',
  }
  return colors[level] || 'default'
}

const saveConfig = () => {
  message.success('配置保存成功')
}

onMounted(() => {
  // 定期更新系统状态
  setInterval(() => {
    systemStatus.value = {
      cpu_usage: Math.floor(Math.random() * 100),
      memory_usage: Math.floor(Math.random() * 100),
      disk_usage: Math.floor(Math.random() * 100),
    }
  }, 5000)
})
</script>

<style scoped>
.system-management {
  padding: 24px;
}

.log-container {
  max-height: 400px;
  overflow-y: auto;
}

.mt-6 {
  margin-top: 24px;
}
</style>
