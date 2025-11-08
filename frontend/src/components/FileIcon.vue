<template>
  <div
    class="file-icon"
    :style="{ width: size + 'px', height: size + 'px' }"
    :class="{ 'not-owned': !isOwnedByCurrentUser }"
  >
    <!-- Thumbnail for image files -->
    <img
      v-if="showThumbnail && thumbnailUrl"
      :src="thumbnailUrl"
      :alt="file.name"
      class="thumbnail-image"
      @error="onThumbnailError"
      @load="onThumbnailLoad"
    />

    <!-- Fallback icon -->
    <el-icon v-else :size="size" :color="iconColor" class="fallback-icon">
      <Folder v-if="fileType === 'directory'" />
      <Picture v-else-if="fileType === 'image'" />
      <VideoPlay v-else-if="fileType === 'video'" />
      <Microphone v-else-if="fileType === 'audio'" />
      <Reading v-else-if="fileType === 'pdf'" />
      <Document v-else-if="fileType === 'word'" />
      <Document v-else-if="fileType === 'excel'" />
      <Document v-else-if="fileType === 'powerpoint'" />
      <Tools v-else-if="fileType === 'code'" />
      <DataLine v-else-if="fileType === 'json'" />
      <Document v-else-if="fileType === 'text'" />
      <Files v-else-if="fileType === 'archive'" />
      <Document v-else />
    </el-icon>

    <!-- Ownership indicator badge -->
    <div
      v-if="!isOwnedByCurrentUser"
      class="ownership-badge"
      :title="`Owned by ${file.owner?.username || 'Unknown'}`"
    >
      <el-icon :size="Math.max(6, size * 0.2)">
        <User />
      </el-icon>
    </div>

    <!-- Loading indicator for thumbnail -->
    <div v-if="loadingThumbnail" class="thumbnail-loading">
      <el-icon class="is-loading">
        <Loading />
      </el-icon>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import {
  Folder,
  Document,
  Loading,
  VideoPlay,
  Microphone,
  Picture,
  Files,
  VideoCamera,
  DocumentCopy,
  DataLine,
  Setting,
  Tools,
  Collection,
  Reading,
  Monitor,
  User,
} from '@element-plus/icons-vue'
import { filesAPI } from '@/services/api'
import { useOfficeConfig } from '@/services/officeConfig'
import { useAuthStore } from '@/stores/auth'

interface FileItem {
  id: number
  name: string
  item_type: 'file' | 'directory'
  thumbnail?: {
    uuid: string
    thumbnail_size: string
    width: number
    height: number
    file_size: number
    created_at: string
    url: string
  } | null
  mime_type?: string
  extension?: string
  file_info?: {
    mime_type?: string
  }
  owner?: {
    id: number
    username: string
    email: string
    first_name: string
    last_name: string
  }
}

interface Props {
  file: FileItem
  size?: number
  showThumbnail?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  size: 32,
  showThumbnail: true,
})

// Services
const officeConfig = useOfficeConfig()
const authStore = useAuthStore()

// Reactive state
const thumbnailUrl = ref<string | null>(null)
const loadingThumbnail = ref(false)
const thumbnailError = ref(false)

// File type detection
const detectFileType = (file: FileItem) => {
  if (file.item_type === 'directory') return 'directory'

  // Check for office documents first
  if (officeConfig.isOfficeDocument(file)) {
    const docType = officeConfig.getDocumentType(file)
    return docType || 'office'
  }

  const mimeType = file.mime_type || file.file_info?.mime_type || ''
  const fileName = file.name.toLowerCase()

  // Image types
  if (
    mimeType.startsWith('image/') ||
    /\.(jpg|jpeg|png|gif|webp|svg|bmp|ico|tiff)$/i.test(fileName)
  ) {
    return 'image'
  }

  // Video types
  if (
    mimeType.startsWith('video/') ||
    /\.(mp4|webm|ogg|avi|mov|mkv|flv|wmv|m4v)$/i.test(fileName)
  ) {
    return 'video'
  }

  // Audio types
  if (mimeType.startsWith('audio/') || /\.(mp3|wav|ogg|m4a|aac|flac|wma)$/i.test(fileName)) {
    return 'audio'
  }

  // PDF
  if (mimeType === 'application/pdf' || fileName.endsWith('.pdf')) {
    return 'pdf'
  }

  // Word documents
  if (
    mimeType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
    mimeType === 'application/msword' ||
    /\.(docx|doc)$/i.test(fileName)
  ) {
    return 'word'
  }

  // Excel spreadsheets
  if (
    mimeType === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
    mimeType === 'application/vnd.ms-excel' ||
    /\.(xlsx|xls)$/i.test(fileName)
  ) {
    return 'excel'
  }

  // PowerPoint presentations
  if (
    mimeType === 'application/vnd.openxmlformats-officedocument.presentationml.presentation' ||
    mimeType === 'application/vnd.ms-powerpoint' ||
    /\.(pptx|ppt)$/i.test(fileName)
  ) {
    return 'powerpoint'
  }

  // Code files
  if (
    /\.(js|ts|jsx|tsx|py|java|cpp|c|cs|php|rb|go|rs|swift|kt|scala|sh|bash|sql|html|css|scss|less|xml|yaml|yml|toml|ini|conf|vue|svelte)$/i.test(
      fileName,
    )
  ) {
    return 'code'
  }

  // JSON
  if (mimeType === 'application/json' || fileName.endsWith('.json')) {
    return 'json'
  }

  // Text files
  if (mimeType.startsWith('text/') || /\.(txt|md|log|csv|rtf)$/i.test(fileName)) {
    return 'text'
  }

  // Archive files
  if (/\.(zip|rar|7z|tar|gz|bz2)$/i.test(fileName)) {
    return 'archive'
  }

  return 'file'
}

// Computed properties
const fileType = computed(() => detectFileType(props.file))

const isOwnedByCurrentUser = computed(() => {
  if (!authStore.user || !props.file.owner) {
    return true // If no user or no owner info, assume owned
  }
  return props.file.owner.id === authStore.user.id
})

const iconColor = computed(() => {
  const type = fileType.value
  const colors: Record<string, string> = {
    directory: '#409eff',
    image: '#67c23a',
    video: '#e6a23c',
    audio: '#f56c6c',
    pdf: '#f56c6c',
    word: '#409eff', // Blue for Word documents
    excel: '#67c23a', // Green for Excel spreadsheets
    powerpoint: '#f56c6c', // Red for PowerPoint presentations
    office: '#409eff', // Blue for general office documents
    code: '#909399',
    json: '#e6a23c',
    text: '#606266',
    archive: '#909399',
    file: '#909399',
  }
  return colors[type] || '#909399'
})

const shouldShowThumbnail = computed(() => {
  return (
    props.showThumbnail &&
    props.file.item_type === 'file' &&
    props.file.thumbnail &&
    !thumbnailError.value &&
    (fileType.value === 'image' || fileType.value === 'video' || fileType.value === 'pdf')
  )
})

// Methods
const loadThumbnail = async () => {
  if (!shouldShowThumbnail.value) return

  try {
    loadingThumbnail.value = true
    thumbnailError.value = false

    const response = await filesAPI.getThumbnail(props.file.id)
    const blob = new Blob([response.data], { type: 'image/jpeg' })
    thumbnailUrl.value = URL.createObjectURL(blob)
  } catch (error) {
    console.warn('Failed to load thumbnail:', error)
    thumbnailError.value = true
    thumbnailUrl.value = null
  } finally {
    loadingThumbnail.value = false
  }
}

const onThumbnailError = () => {
  thumbnailError.value = true
  thumbnailUrl.value = null
}

const onThumbnailLoad = () => {
  // Thumbnail loaded successfully
}

// Lifecycle
onMounted(() => {
  if (shouldShowThumbnail.value) {
    loadThumbnail()
  }
})

// Watch for changes in file or thumbnail
watch(
  () => props.file,
  () => {
    if (shouldShowThumbnail.value) {
      loadThumbnail()
    } else {
      thumbnailUrl.value = null
      thumbnailError.value = false
    }
  },
  { deep: true },
)

// Cleanup blob URL on unmount
import { onUnmounted } from 'vue'
onUnmounted(() => {
  if (thumbnailUrl.value) {
    URL.revokeObjectURL(thumbnailUrl.value)
  }
})
</script>

<style scoped>
.file-icon {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  overflow: hidden;
  aspect-ratio: 1;
}

.thumbnail-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: 4px;
}

.fallback-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

.thumbnail-loading {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: #409eff;
}

.thumbnail-loading .el-icon {
  font-size: 16px;
}

/* Ownership indicators */
.file-icon.not-owned {
  opacity: 0.8;
  position: relative;
}

.file-icon.not-owned .fallback-icon {
  filter: grayscale(0.3);
}

.ownership-badge {
  position: absolute;
  bottom: -1px;
  right: -1px;
  background: #67c23a;
  color: white;
  border-radius: 50%;
  width: 12px;
  height: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid white;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
  z-index: 10;
}

.ownership-badge .el-icon {
  font-size: 8px;
}
</style>
