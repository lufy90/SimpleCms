<template>
  <div class="file-icon" :style="{ width: size + 'px', height: size + 'px' }">
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
    <el-icon
      v-else
      :size="size"
      :color="iconColor"
      class="fallback-icon"
    >
      <Folder v-if="file.item_type === 'directory'" />
      <Document v-else />
    </el-icon>
    
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
import { Folder, Document, Loading } from '@element-plus/icons-vue'
import { filesAPI } from '@/services/api'

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
  storage?: {
    mime_type?: string
  }
}

interface Props {
  file: FileItem
  size?: number
  showThumbnail?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  size: 32,
  showThumbnail: true
})

// Reactive state
const thumbnailUrl = ref<string | null>(null)
const loadingThumbnail = ref(false)
const thumbnailError = ref(false)

// Computed properties
const iconColor = computed(() => {
  if (props.file.item_type === 'directory') return '#409eff'
  return '#909399'
})

const shouldShowThumbnail = computed(() => {
  return props.showThumbnail && 
         props.file.item_type === 'file' && 
         props.file.thumbnail && 
         !thumbnailError.value
})

// Methods
const loadThumbnail = async () => {
  if (!shouldShowThumbnail.value) return
  
  try {
    loadingThumbnail.value = true
    thumbnailError.value = false
    
    // Use thumbnail URL if available, otherwise fetch from API
    if (props.file.thumbnail?.url) {
      thumbnailUrl.value = props.file.thumbnail.url
    } else {
      // Fallback to API call
      const response = await filesAPI.getThumbnail(props.file.id)
      const blob = new Blob([response.data], { type: 'image/jpeg' })
      thumbnailUrl.value = URL.createObjectURL(blob)
    }
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
watch(() => props.file, () => {
  if (shouldShowThumbnail.value) {
    loadThumbnail()
  } else {
    thumbnailUrl.value = null
    thumbnailError.value = false
  }
}, { deep: true })

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
</style>
