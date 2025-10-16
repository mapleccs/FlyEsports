/**
 * 文件管理 API
 */

import { apiClient } from './client'

export interface FileUploadResponse {
  file_id: string
  filename: string
  url: string
  size: number
  content_type: string
  width: number
  height: number
  format: string
  hash: string
}

export interface FileDeleteResponse {
  success: boolean
  message: string
}

export interface PresetMediaItem {
  id: string
  name: string
  url: string
  thumbnail?: string
}

export interface PresetMediaResponse {
  logos: PresetMediaItem[]
  banners: PresetMediaItem[]
}

/**
 * 上传赛事媒体文件
 */
export const uploadTournamentMedia = async (
  file: File,
  mediaType: 'logo' | 'banner',
  tournamentId?: string
): Promise<FileUploadResponse> => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('media_type', mediaType)
  if (tournamentId) {
    formData.append('tournament_id', tournamentId)
  }

  const response = await apiClient.post<FileUploadResponse>(
    '/files/tournament-media/upload',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  )

  return response.data
}

/**
 * 删除文件
 */
export const deleteFile = async (filePath: string): Promise<FileDeleteResponse> => {
  const response = await apiClient.delete<FileDeleteResponse>(`/files/${filePath}`)
  return response.data
}

/**
 * 获取文件URL
 */
export const getFileUrl = (filePath: string): string => {
  return `${apiClient.defaults.baseURL}/files/${filePath}`
}

/**
 * 获取预设媒体素材
 */
export const getTournamentMediaPresets = async (): Promise<PresetMediaResponse> => {
  try {
    const response = await apiClient.get<PresetMediaResponse>('/files/tournament-media/presets')
    return response.data
  } catch (error) {
    console.warn('获取预设素材失败，使用默认数据', error)

    // 返回默认预设数据
    return {
      logos: [
        { id: 'default-logo-1', name: '经典奖杯', url: '/images/presets/trophy-1.png' },
        { id: 'default-logo-2', name: '电竞徽章', url: '/images/presets/esports-1.png' },
        { id: 'default-logo-3', name: '战队盾牌', url: '/images/presets/shield-1.png' },
        { id: 'default-logo-4', name: '游戏手柄', url: '/images/presets/gamepad-1.png' },
        { id: 'default-logo-5', name: '王者之冠', url: '/images/presets/crown-1.png' },
        { id: 'default-logo-6', name: '雷电之力', url: '/images/presets/thunder-1.png' },
      ],
      banners: [
        { id: 'default-banner-1', name: '科技蓝', url: '/images/presets/banner-tech-blue.jpg' },
        { id: 'default-banner-2', name: '霓虹紫', url: '/images/presets/banner-neon-purple.jpg' },
        { id: 'default-banner-3', name: '火焰红', url: '/images/presets/banner-fire-red.jpg' },
        { id: 'default-banner-4', name: '森林绿', url: '/images/presets/banner-forest-green.jpg' },
        { id: 'default-banner-5', name: '黄金色', url: '/images/presets/banner-golden.jpg' },
        { id: 'default-banner-6', name: '银河系', url: '/images/presets/banner-galaxy.jpg' },
      ],
    }
  }
}

/**
 * 验证文件大小
 */
export const validateFileSize = (file: File, maxSizeMB: number): boolean => {
  const maxSizeBytes = maxSizeMB * 1024 * 1024
  return file.size <= maxSizeBytes
}

/**
 * 验证文件类型
 */
export const validateFileType = (file: File, allowedTypes: string[]): boolean => {
  return allowedTypes.some(type => {
    if (type === 'image/*') {
      return file.type.startsWith('image/')
    }
    return file.type === type
  })
}

/**
 * 格式化文件大小
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'

  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}
