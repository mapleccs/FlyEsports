<template>
  <div class="tournament-media-upload">
    <!-- 调试信息 -->
    <div
      style="
        background: #fff2e8;
        padding: 8px;
        margin-bottom: 16px;
        border-radius: 4px;
        font-size: 12px;
      "
    >
      <strong>调试信息:</strong> TournamentMediaUpload组件已加载
    </div>

    <div class="step-header">
      <h2 class="step-title">图片上传</h2>
      <p class="step-description">上传赛事Logo和横幅图片，让您的赛事更加吸引人（可选步骤）</p>
    </div>

    <div class="form-section">
      <!-- Logo上传 -->
      <div class="upload-group">
        <h3 class="group-title">
          <picture-outlined />
          赛事Logo
        </h3>
        <p class="group-desc">建议尺寸：200x200像素，支持JPG、PNG格式，文件大小不超过2MB</p>

        <div class="upload-container">
          <a-upload
            v-model:file-list="logoFileList"
            list-type="picture-card"
            class="logo-uploader"
            :show-upload-list="false"
            :before-upload="beforeLogoUpload"
            :custom-request="handleLogoUpload"
            accept="image/*"
          >
            <div v-if="localData.logo_url" class="uploaded-image">
              <img :src="localData.logo_url" alt="赛事Logo" />
              <div class="image-overlay">
                <div class="overlay-actions">
                  <eye-outlined @click.stop="previewImage(localData.logo_url, '赛事Logo')" />
                  <delete-outlined @click.stop="removeLogo" />
                </div>
              </div>
            </div>
            <div v-else class="upload-placeholder">
              <loading-outlined v-if="logoUploading" />
              <plus-outlined v-else />
              <div class="upload-text">
                {{ logoUploading ? '上传中...' : '上传Logo' }}
              </div>
            </div>
          </a-upload>
        </div>
      </div>

      <!-- 横幅上传 -->
      <div class="upload-group">
        <h3 class="group-title">
          <file-image-outlined />
          赛事横幅
        </h3>
        <p class="group-desc">建议尺寸：1200x400像素，支持JPG、PNG格式，文件大小不超过5MB</p>

        <div class="upload-container banner-container">
          <a-upload
            v-model:file-list="bannerFileList"
            list-type="picture-card"
            class="banner-uploader"
            :show-upload-list="false"
            :before-upload="beforeBannerUpload"
            :custom-request="handleBannerUpload"
            accept="image/*"
          >
            <div v-if="localData.banner_url" class="uploaded-banner">
              <img :src="localData.banner_url" alt="赛事横幅" />
              <div class="image-overlay">
                <div class="overlay-actions">
                  <eye-outlined @click.stop="previewImage(localData.banner_url, '赛事横幅')" />
                  <delete-outlined @click.stop="removeBanner" />
                </div>
              </div>
            </div>
            <div v-else class="upload-placeholder banner-placeholder">
              <loading-outlined v-if="bannerUploading" />
              <plus-outlined v-else />
              <div class="upload-text">
                {{ bannerUploading ? '上传中...' : '上传横幅' }}
              </div>
            </div>
          </a-upload>
        </div>
      </div>

      <!-- 预设图片库 -->
      <div class="preset-gallery">
        <h3 class="gallery-title">
          <appstore-outlined />
          预设图片库
        </h3>
        <p class="gallery-desc">选择我们提供的预设图片，或者上传您自己的图片</p>

        <a-tabs v-model:active-key="galleryTab" size="small">
          <a-tab-pane key="logos" tab="Logo图标">
            <a-spin :spinning="presetsLoading" tip="加载预设素材中...">
              <div class="preset-grid">
                <div
                  v-for="preset in presetLogos"
                  :key="preset.id"
                  class="preset-item"
                  :class="{ active: localData.logo_url === preset.url }"
                  @click="selectPresetLogo(preset)"
                >
                  <img :src="preset.url" :alt="preset.name" />
                  <div class="preset-name">{{ preset.name }}</div>
                </div>

                <div v-if="!presetsLoading && presetLogos.length === 0" class="empty-preset">
                  <picture-outlined />
                  <span>暂无预设Logo</span>
                </div>
              </div>
            </a-spin>
          </a-tab-pane>

          <a-tab-pane key="banners" tab="横幅背景">
            <a-spin :spinning="presetsLoading" tip="加载预设素材中...">
              <div class="preset-grid banner-grid">
                <div
                  v-for="preset in presetBanners"
                  :key="preset.id"
                  class="preset-item banner-item"
                  :class="{ active: localData.banner_url === preset.url }"
                  @click="selectPresetBanner(preset)"
                >
                  <img :src="preset.url" :alt="preset.name" />
                  <div class="preset-name">{{ preset.name }}</div>
                </div>

                <div v-if="!presetsLoading && presetBanners.length === 0" class="empty-preset">
                  <file-image-outlined />
                  <span>暂无预设横幅</span>
                </div>
              </div>
            </a-spin>
          </a-tab-pane>
        </a-tabs>
      </div>

      <!-- 预览效果 -->
      <div v-if="hasImages" class="media-preview">
        <h3 class="preview-title">
          <eye-outlined />
          效果预览
        </h3>

        <div class="preview-card">
          <div class="card-banner">
            <img
              v-if="localData.banner_url"
              :src="localData.banner_url"
              alt="横幅预览"
              class="preview-banner"
            />
            <div v-else class="preview-banner-placeholder">
              <picture-outlined />
              <span>暂无横幅图片</span>
            </div>
            <div class="banner-overlay"></div>

            <div class="card-content">
              <div class="card-logo">
                <img
                  v-if="localData.logo_url"
                  :src="localData.logo_url"
                  alt="Logo预览"
                  class="preview-logo"
                />
                <div v-else class="preview-logo-placeholder">
                  <trophy-outlined />
                </div>
              </div>

              <div class="card-info">
                <h4 class="card-title">{{ props.modelValue.name || '赛事名称' }}</h4>
                <div class="card-meta">
                  <a-tag color="blue">{{ typeText }}</a-tag>
                  <span class="participant-info">16/32 支队伍</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 图片预览模态框 -->
    <a-modal
      v-model:open="previewVisible"
      :title="previewTitle"
      :footer="null"
      width="80%"
      style="max-width: 800px"
    >
      <img :src="previewUrl" :alt="previewTitle" style="width: 100%; height: auto" />
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { message } from 'ant-design-vue'
import {
  PictureOutlined,
  FileImageOutlined,
  PlusOutlined,
  LoadingOutlined,
  EyeOutlined,
  DeleteOutlined,
  AppstoreOutlined,
  TrophyOutlined,
} from '@ant-design/icons-vue'
import type { TournamentCreateRequest } from '@/shared/types/tournament'
import {
  uploadTournamentMedia,
  getTournamentMediaPresets,
  validateFileSize,
  validateFileType,
  formatFileSize,
  type PresetMediaItem,
} from '@/shared/api/files'

// Props & Emits
interface Props {
  modelValue: Partial<TournamentCreateRequest>
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:modelValue': [value: Partial<TournamentCreateRequest>]
  validate: [isValid: boolean]
}>()

// 响应式数据
const localData = ref<Partial<TournamentCreateRequest>>({ ...props.modelValue })
const logoFileList = ref<any[]>([])
const bannerFileList = ref<any[]>([])
const logoUploading = ref(false)
const bannerUploading = ref(false)
const galleryTab = ref('logos')

// 预览模态框
const previewVisible = ref(false)
const previewUrl = ref('')
const previewTitle = ref('')

// 预设图片
const presetLogos = ref<PresetMediaItem[]>([])
const presetBanners = ref<PresetMediaItem[]>([])
const presetsLoading = ref(false)

// 计算属性
const typeText = computed(() => {
  return props.modelValue.tournament_type === 'team_based' ? '战队赛' : '个人赛'
})

const hasImages = computed(() => {
  return !!(localData.value.logo_url || localData.value.banner_url)
})

const isStepValid = computed(() => {
  // 图片上传是可选步骤，总是返回true
  return true
})

// 方法
const beforeLogoUpload = (file: File) => {
  if (!validateFileType(file, ['image/*'])) {
    message.error('只能上传图片文件！')
    return false
  }

  if (!validateFileSize(file, 2)) {
    message.error(`Logo图片大小必须小于2MB！当前大小：${formatFileSize(file.size)}`)
    return false
  }

  return true
}

const beforeBannerUpload = (file: File) => {
  if (!validateFileType(file, ['image/*'])) {
    message.error('只能上传图片文件！')
    return false
  }

  if (!validateFileSize(file, 5)) {
    message.error(`横幅图片大小必须小于5MB！当前大小：${formatFileSize(file.size)}`)
    return false
  }

  return true
}

const handleLogoUpload = async (options: any) => {
  const { file } = options

  try {
    logoUploading.value = true

    // 调用真实的文件上传API
    const result = await uploadTournamentMedia(
      file,
      'logo',
      undefined // 创建阶段没有ID
    )

    // 更新本地数据
    localData.value.logo_url = result.url

    message.success(`Logo上传成功！尺寸：${result.width}x${result.height}`)
  } catch (error: any) {
    console.error('Logo上传失败:', error)
    message.error(error.response?.data?.detail || 'Logo上传失败，请稍后重试')
  } finally {
    logoUploading.value = false
  }
}

const handleBannerUpload = async (options: any) => {
  const { file } = options

  try {
    bannerUploading.value = true

    // 调用真实的文件上传API
    const result = await uploadTournamentMedia(
      file,
      'banner',
      undefined // 创建阶段没有ID
    )

    // 更新本地数据
    localData.value.banner_url = result.url

    message.success(`横幅上传成功！尺寸：${result.width}x${result.height}`)
  } catch (error: any) {
    console.error('横幅上传失败:', error)
    message.error(error.response?.data?.detail || '横幅上传失败，请稍后重试')
  } finally {
    bannerUploading.value = false
  }
}

// 加载预设素材
const loadPresetMedia = async () => {
  try {
    presetsLoading.value = true
    const presets = await getTournamentMediaPresets()
    presetLogos.value = presets.logos
    presetBanners.value = presets.banners
  } catch (error) {
    console.error('加载预设素材失败:', error)
    message.warning('预设素材加载失败，将使用默认素材')
  } finally {
    presetsLoading.value = false
  }
}

const removeLogo = () => {
  localData.value.logo_url = ''
  logoFileList.value = []
}

const removeBanner = () => {
  localData.value.banner_url = ''
  bannerFileList.value = []
}

const selectPresetLogo = (preset: PresetMediaItem) => {
  localData.value.logo_url = preset.url
  message.success(`已选择 ${preset.name}`)
}

const selectPresetBanner = (preset: PresetMediaItem) => {
  localData.value.banner_url = preset.url
  message.success(`已选择 ${preset.name}`)
}

const previewImage = (url: string, title: string) => {
  previewUrl.value = url
  previewTitle.value = title
  previewVisible.value = true
}

const validateStep = () => {
  setTimeout(() => {
    emit('validate', isStepValid.value)
  }, 0)
}

// 防止递归更新的标志位
const isUpdatingFromProps = ref(false)
const isUpdatingFromLocal = ref(false)

const syncData = () => {
  if (!isUpdatingFromProps.value) {
    isUpdatingFromLocal.value = true
    emit('update:modelValue', localData.value)
    nextTick(() => {
      isUpdatingFromLocal.value = false
    })
  }
}

// 监听器
watch(localData, syncData, { deep: true })
watch(isStepValid, valid => {
  emit('validate', valid)
})

watch(
  () => props.modelValue,
  newValue => {
    if (!isUpdatingFromLocal.value) {
      isUpdatingFromProps.value = true
      localData.value = { ...newValue }
      nextTick(() => {
        isUpdatingFromProps.value = false
      })
    }
  },
  { deep: true }
)

// 生命周期
onMounted(() => {
  validateStep()
  loadPresetMedia()
})
</script>

<style scoped>
.tournament-media-upload {
  max-width: 800px;
  margin: 0 auto;
}

.step-header {
  text-align: center;
  margin-bottom: 40px;
}

.step-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #262626;
  margin: 0 0 8px 0;
}

.step-description {
  color: #666;
  font-size: 14px;
  margin: 0;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.upload-group {
  padding: 24px;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  background: #fafafa;
}

.group-title {
  font-size: 16px;
  font-weight: 500;
  color: #262626;
  margin: 0 0 8px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.group-desc {
  color: #666;
  font-size: 13px;
  margin: 0 0 16px 0;
}

.upload-container {
  display: flex;
  justify-content: center;
}

.logo-uploader .ant-upload,
.banner-uploader .ant-upload {
  width: 200px;
  height: 200px;
  border-radius: 8px;
}

.banner-container .banner-uploader .ant-upload {
  width: 400px;
  height: 150px;
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999;
}

.banner-placeholder {
  width: 400px;
  height: 150px;
}

.upload-text {
  margin-top: 8px;
  font-size: 14px;
}

.uploaded-image,
.uploaded-banner {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  border-radius: 8px;
}

.uploaded-image img,
.uploaded-banner img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s;
}

.uploaded-image:hover .image-overlay,
.uploaded-banner:hover .image-overlay {
  opacity: 1;
}

.overlay-actions {
  display: flex;
  gap: 12px;
}

.overlay-actions .anticon {
  color: white;
  font-size: 18px;
  cursor: pointer;
  padding: 8px;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.3);
}

.overlay-actions .anticon:hover {
  background: rgba(0, 0, 0, 0.6);
}

.preset-gallery {
  padding: 24px;
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  background: white;
}

.gallery-title {
  font-size: 16px;
  font-weight: 500;
  color: #262626;
  margin: 0 0 8px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.gallery-desc {
  color: #666;
  font-size: 13px;
  margin: 0 0 16px 0;
}

.preset-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.banner-grid {
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
}

.preset-item {
  cursor: pointer;
  border: 2px solid transparent;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s;
  background: white;
}

.preset-item:hover {
  border-color: #1890ff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.preset-item.active {
  border-color: #1890ff;
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.2);
}

.preset-item img {
  width: 100%;
  height: 80px;
  object-fit: cover;
}

.banner-item img {
  height: 60px;
}

.preset-name {
  padding: 8px;
  font-size: 12px;
  text-align: center;
  color: #666;
  background: #fafafa;
}

.media-preview {
  padding: 24px;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  background: white;
}

.preview-title {
  font-size: 16px;
  font-weight: 500;
  color: #262626;
  margin: 0 0 20px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.preview-card {
  max-width: 400px;
  margin: 0 auto;
}

.card-banner {
  position: relative;
  height: 160px;
  border-radius: 12px;
  overflow: hidden;
  background: #f5f5f5;
}

.preview-banner {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.preview-banner-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #bfbfbf;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.preview-banner-placeholder span {
  margin-top: 8px;
  font-size: 14px;
}

.banner-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.3);
}

.card-content {
  position: absolute;
  bottom: 16px;
  left: 16px;
  right: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  color: white;
}

.card-logo {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-logo {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.preview-logo-placeholder {
  color: white;
  font-size: 20px;
}

.card-info {
  flex: 1;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 4px 0;
  color: white;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.participant-info {
  font-size: 13px;
  opacity: 0.9;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .tournament-media-upload {
    max-width: 100%;
  }

  .step-header {
    margin-bottom: 32px;
  }

  .step-title {
    font-size: 1.3rem;
  }

  .form-section {
    gap: 24px;
  }

  .upload-group,
  .preset-gallery,
  .media-preview {
    padding: 20px 16px;
  }

  .banner-container .banner-uploader .ant-upload,
  .banner-placeholder {
    width: 100%;
    max-width: 320px;
    height: 120px;
  }

  .preset-grid {
    grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
    gap: 12px;
  }

  .banner-grid {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  }
}

/* 空状态样式 */
.empty-preset {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #bfbfbf;
  background: #fafafa;
  border-radius: 8px;
  border: 2px dashed #e8e8e8;
}

.empty-preset .anticon {
  font-size: 48px;
  margin-bottom: 12px;
}

.empty-preset span {
  font-size: 14px;
}

/* 加载状态样式 */
.ant-spin-nested-loading {
  min-height: 200px;
}

.ant-spin-container {
  min-height: inherit;
}
</style>
