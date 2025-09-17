<template>
  <div class="video-viewer">
    <div class="video-content">
      <!-- Floating Controls Overlay -->
      <div class="video-controls-overlay">
        <el-button-group>
          <el-button @click="toggleFullscreen" size="small">
            <el-icon><FullScreen /></el-icon>
            Fullscreen
          </el-button>
          <el-button @click="toggleStreaming" size="small" :type="useStreaming ? 'primary' : 'default'">
            <el-icon><VideoPlay /></el-icon>
            {{ useStreaming ? 'Streaming' : 'Download' }}
          </el-button>
        </el-button-group>
      </div>
      <video
        ref="videoRef"
        :src="videoSrc"
        controls
        class="video-player"
        @loadedmetadata="onVideoLoad"
        @error="onVideoError"
        @loadstart="onVideoLoadStart"
        @progress="onVideoProgress"
      >
        Your browser does not support the video tag.
      </video>
      
      <!-- Loading indicator -->
      <div v-if="isLoading" class="loading-overlay">
        <el-icon class="is-loading">
          <Loading />
        </el-icon>
        <span>Loading video...</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { VideoPlay, FullScreen, Loading } from '@element-plus/icons-vue'
import { filesAPI } from '@/services/api'

interface Props {
  src: string
  filename: string | 'File'
  fileId?: number
}

const props = defineProps<Props>()

// State
const videoRef = ref<HTMLVideoElement>()
const useStreaming = ref(true)
const isLoading = ref(false)
const streamUrl = ref<string | null>(null)

// Computed
const videoSrc = computed(() => {
  if (useStreaming.value && props.fileId && streamUrl.value) {
    return streamUrl.value
  }
  return props.src
})

// Methods
const toggleFullscreen = () => {
  if (videoRef.value) {
    if (videoRef.value.requestFullscreen) {
      videoRef.value.requestFullscreen()
    }
  }
}

const toggleStreaming = () => {
  useStreaming.value = !useStreaming.value
  if (useStreaming.value && props.fileId) {
    loadStreamUrl()
  }
}

const loadStreamUrl = async () => {
  if (!props.fileId) return
  
  try {
    isLoading.value = true
    const response = await filesAPI.stream(props.fileId)
    
    // Create blob URL for streaming
    const blob = new Blob([response.data], { type: 'video/mp4' })
    streamUrl.value = URL.createObjectURL(blob)
    
    console.log('Stream URL created for video streaming')
  } catch (error) {
    console.error('Failed to load stream URL:', error)
    // Fallback to regular download
    useStreaming.value = false
  } finally {
    isLoading.value = false
  }
}

const onVideoLoad = () => {
  console.log('Video loaded successfully')
  isLoading.value = false
}

const onVideoError = (error: Event) => {
  console.error('Failed to load video:', error)
  isLoading.value = false
  
  // If streaming fails, try fallback to download
  if (useStreaming.value) {
    console.log('Streaming failed, falling back to download')
    useStreaming.value = false
  }
}

const onVideoLoadStart = () => {
  console.log('Video load started')
  isLoading.value = true
}

const onVideoProgress = () => {
  console.log('Video progress updated')
}

// Lifecycle
onMounted(() => {
  if (props.fileId && useStreaming.value) {
    loadStreamUrl()
  }
})

// Watch for fileId changes
watch(() => props.fileId, (newFileId) => {
  if (newFileId && useStreaming.value) {
    loadStreamUrl()
  }
})

// Cleanup blob URL on unmount
import { onUnmounted } from 'vue'
onUnmounted(() => {
  if (streamUrl.value) {
    URL.revokeObjectURL(streamUrl.value)
  }
})
</script>

<style scoped>
.video-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.video-content {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.video-controls-overlay {
  position: absolute;
  top: 12px;
  right: 12px;
  opacity: 0;
  transform: translateY(-10px);
  transition: all 0.2s ease;
  z-index: 10;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 6px;
  padding: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.video-content:hover .video-controls-overlay {
  opacity: 1;
  transform: translateY(0);
}

.video-player {
  max-width: 100%;
  max-height: 100%;
  width: auto;
  height: auto;
}

.loading-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: white;
  background: rgba(0, 0, 0, 0.7);
  padding: 20px;
  border-radius: 8px;
  z-index: 20;
}

.loading-overlay .el-icon {
  font-size: 24px;
}

.loading-overlay span {
  font-size: 14px;
  font-weight: 500;
}
</style>
