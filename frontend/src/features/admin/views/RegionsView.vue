<template>
  <div class="regions-management">
    <a-card>
      <template #title>
        <div class="flex justify-between items-center">
          <span>赛区管理</span>
          <a-button type="primary" @click="createRegion">
            <template #icon><PlusOutlined /></template>
            创建赛区
          </a-button>
        </div>
      </template>

      <a-table
        :columns="columns"
        :data-source="regions"
        :loading="loading"
        row-key="id"
        size="small"
      >
        <template #bodyCell="{ column, record, index }">
          <template v-if="column.dataIndex === 'index'">
            {{ index + 1 }}
          </template>
          <template v-else-if="column.dataIndex === 'status'">
            <a-tag :color="record.is_active ? 'green' : 'red'">
              {{ record.is_active ? '活跃' : '停用' }}
            </a-tag>
          </template>
          <template v-else-if="column.dataIndex === 'actions'">
            <a-button-group size="small">
              <a-button @click="editRegion(record)">
                <EditOutlined />
                编辑
              </a-button>
              <a-button @click="manageUsers(record)">
                <TeamOutlined />
                成员管理
              </a-button>
            </a-button-group>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined, EditOutlined, TeamOutlined } from '@ant-design/icons-vue'

const regions = ref([
  {
    id: 1,
    name: '华北赛区',
    description: '覆盖北京、天津、河北等地区',
    is_active: true,
    created_at: '2024-01-01',
  },
  {
    id: 2,
    name: '华东赛区',
    description: '覆盖上海、江苏、浙江等地区',
    is_active: true,
    created_at: '2024-01-02',
  },
  {
    id: 3,
    name: '华南赛区',
    description: '覆盖广东、福建、广西等地区',
    is_active: true,
    created_at: '2024-01-03',
  },
])

const loading = ref(false)

const columns = [
  { title: '#', dataIndex: 'index', width: 60 },
  { title: '赛区名称', dataIndex: 'name', key: 'name' },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 120 },
  { title: '操作', dataIndex: 'actions', key: 'actions', width: 160 },
]

const createRegion = () => {
  message.info('创建赛区功能开发中')
}

const editRegion = (region: any) => {
  message.info(`编辑赛区：${region.name}`)
}

const manageUsers = (region: any) => {
  message.info(`管理赛区成员：${region.name}`)
}

onMounted(() => {
  // 初始化数据
})
</script>

<style scoped>
.regions-management {
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
</style>
