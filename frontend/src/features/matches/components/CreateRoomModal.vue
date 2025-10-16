<template>
  <a-modal
    v-model:visible="modalVisible"
    title="创建BP房间"
    width="600px"
    :confirm-loading="loading"
    @ok="handleCreate"
    @cancel="handleCancel"
  >
    <a-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      layout="vertical"
      :label-col="{ span: 24 }"
    >
      <!-- 基本信息 -->
      <div class="form-section">
        <h4 class="section-title">基本信息</h4>
        
        <a-form-item
          label="房间名称"
          name="name"
          :rules="[{ required: true, message: '请输入房间名称' }]"
        >
          <a-input
            v-model:value="formData.name"
            placeholder="请输入房间名称"
            :maxlength="50"
            show-count
          />
        </a-form-item>

        <a-form-item label="房间描述" name="description">
          <a-textarea
            v-model:value="formData.description"
            placeholder="请输入房间描述（可选）"
            :rows="3"
            :maxlength="200"
            show-count
          />
        </a-form-item>

        <a-form-item label="房间类型" name="room_type">
          <a-select v-model:value="formData.room_type" placeholder="选择房间类型">
            <a-select-option value="custom">自定义房间</a-select-option>
            <a-select-option value="practice">练习房间</a-select-option>
            <a-select-option value="ranked">排位练习</a-select-option>
          </a-select>
        </a-form-item>
      </div>

      <!-- BP配置 -->
      <div class="form-section">
        <h4 class="section-title">BP配置</h4>
        
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="Ban位数量" name="ban_count">
              <a-input-number
                v-model:value="formData.bp_config.ban_count"
                :min="0"
                :max="10"
                style="width: 100%"
                placeholder="Ban位数量"
              />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="Pick位数量" name="pick_count">
              <a-input-number
                v-model:value="formData.bp_config.pick_count"
                :min="1"
                :max="10"
                style="width: 100%"
                placeholder="Pick位数量"
              />
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="Ban时间(秒)" name="ban_time">
              <a-input-number
                v-model:value="formData.bp_config.ban_time"
                :min="10"
                :max="120"
                style="width: 100%"
                placeholder="Ban阶段时间"
              />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="Pick时间(秒)" name="pick_time">
              <a-input-number
                v-model:value="formData.bp_config.pick_time"
                :min="10"
                :max="120"
                style="width: 100%"
                placeholder="Pick阶段时间"
              />
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item label="边路选择" name="side_selection">
          <a-radio-group v-model:value="formData.bp_config.side_selection">
            <a-radio value="random">随机分配</a-radio>
            <a-radio value="blue_first">蓝色方优先</a-radio>
            <a-radio value="red_first">红色方优先</a-radio>
          </a-radio-group>
        </a-form-item>

        <a-form-item>
          <a-space direction="vertical">
            <a-checkbox v-model:checked="formData.bp_config.enable_swap">
              允许英雄交换
            </a-checkbox>
            <a-checkbox v-model:checked="formData.bp_config.enable_chat">
              启用房间聊天
            </a-checkbox>
          </a-space>
        </a-form-item>
      </div>

      <!-- 预设配置 -->
      <div class="form-section">
        <h4 class="section-title">快速配置</h4>
        <a-space wrap>
          <a-button 
            v-for="preset in presets"
            :key="preset.name"
            size="small"
            @click="applyPreset(preset)"
          >
            {{ preset.name }}
          </a-button>
        </a-space>
      </div>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import type { FormInstance } from 'ant-design-vue'
import { useBPRoomStore } from '@/shared/stores/bp_room'
import type { CreateBPRoomRequest, BPConfig, BPRoom } from '@/shared/api/bp_rooms'

// Props
interface Props {
  visible: boolean
}

const props = defineProps<Props>()

// Events
const emit = defineEmits<{
  'update:visible': [visible: boolean]
  created: [room: BPRoom]
}>()

// Store
const bpRoomStore = useBPRoomStore()

// 响应式数据
const formRef = ref<FormInstance>()
const loading = ref(false)

const modalVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
})

// 表单数据
const formData = reactive<CreateBPRoomRequest>({
  name: '',
  description: '',
  room_type: 'custom',
  bp_config: {
    ban_count: 5,
    pick_count: 5,
    ban_time: 30,
    pick_time: 30,
    side_selection: 'random',
    enable_swap: true,
    enable_chat: true
  }
})

// 表单验证规则
const rules = {
  name: [
    { required: true, message: '请输入房间名称', trigger: 'blur' },
    { min: 2, max: 50, message: '房间名称长度为2-50个字符', trigger: 'blur' }
  ],
  description: [
    { max: 200, message: '房间描述不能超过200个字符', trigger: 'blur' }
  ],
  room_type: [
    { required: true, message: '请选择房间类型', trigger: 'change' }
  ]
}

// 预设配置
const presets = [
  {
    name: '标准5V5',
    config: {
      ban_count: 5,
      pick_count: 5,
      ban_time: 30,
      pick_time: 30,
      side_selection: 'random',
      enable_swap: true,
      enable_chat: true
    }
  },
  {
    name: '快速模式',
    config: {
      ban_count: 3,
      pick_count: 5,
      ban_time: 15,
      pick_time: 20,
      side_selection: 'random',
      enable_swap: true,
      enable_chat: true
    }
  },
  {
    name: '训练模式',
    config: {
      ban_count: 0,
      pick_count: 5,
      ban_time: 10,
      pick_time: 60,
      side_selection: 'blue_first',
      enable_swap: true,
      enable_chat: true
    }
  },
  {
    name: '全Ban模式',
    config: {
      ban_count: 10,
      pick_count: 5,
      ban_time: 45,
      pick_time: 30,
      side_selection: 'random',
      enable_swap: false,
      enable_chat: true
    }
  }
]

// 方法
const resetForm = () => {
  formData.name = ''
  formData.description = ''
  formData.room_type = 'custom'
  formData.bp_config = {
    ban_count: 5,
    pick_count: 5,
    ban_time: 30,
    pick_time: 30,
    side_selection: 'random',
    enable_swap: true,
    enable_chat: true
  }
  formRef.value?.clearValidate()
}

const applyPreset = (preset: { name: string; config: Partial<BPConfig> }) => {
  Object.assign(formData.bp_config, preset.config)
}

const handleCreate = async () => {
  try {
    loading.value = true
    
    // 表单验证
    await formRef.value?.validate()

    // 创建房间
    const room = await bpRoomStore.createRoom(formData)
    
    if (room) {
      emit('created', room)
      resetForm()
    }
  } catch (error) {
    console.error('创建房间失败:', error)
  } finally {
    loading.value = false
  }
}

const handleCancel = () => {
  resetForm()
  modalVisible.value = false
}

// 监听对话框打开，重置表单
watch(() => props.visible, (visible) => {
  if (visible) {
    resetForm()
  }
})
</script>

<style scoped>
.form-section {
  margin-bottom: 24px;
}

.form-section:last-child {
  margin-bottom: 0;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 16px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid #e5e7eb;
}

:deep(.ant-form-item) {
  margin-bottom: 16px;
}

:deep(.ant-form-item-label > label) {
  font-weight: 500;
  color: #374151;
}

:deep(.ant-input-number) {
  width: 100%;
}

:deep(.ant-radio-group) {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

:deep(.ant-checkbox-wrapper) {
  color: #374151;
}

/* 响应式设计 */
@media (max-width: 768px) {
  :deep(.ant-modal) {
    margin: 0;
    max-width: 100vw;
    padding: 0;
  }
  
  :deep(.ant-modal-content) {
    border-radius: 0;
  }
}
</style>