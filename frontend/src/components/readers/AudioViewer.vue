<template>
  <div class="audio-viewer">
    <div class="audio-content">
      <div class="audio-player-container">
        <audio
          ref="audioRef"
          :src="audioSrc"
          controls
          class="audio-player"
          @loadedmetadata="onAudioLoad"
          @error="onAudioError"
          @loadstart="onAudioLoadStart"
          @progress="onAudioProgress"
        >
          Your browser does not support the audio tag.
        </audio>
      </div>

      <div class="audio-info">
        <div class="audio-controls">
          <el-button-group>
            <el-button @click="toggleStreaming" size="small" :type="useStreaming ? 'primary' : 'default'">
              <el-icon><Microphone /></el-icon>
              {{ useStreaming ? 'Streaming' : 'Download' }}
            </el-button>
          </el-button-group>
        </div>
        
        <div class="audio-visualizer">
          <div class="waveform">
            <div
              v-for="i in 20"
              :key="i"
              class="wave-bar"
              :style="{ height: `${Math.random() * 100}%` }"
            />
          </div>
        </div>
      </div>
      
      <!-- Loading indicator -->
      <div v-if="isLoading" class="loading-overlay">
        <el-icon class="is-loading">
          <Loading />
        </el-icon>
        <span>Loading audio...</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { Microphone, Loading } from '@element-plus/icons-vue'
import { filesAPI } from '@/services/api'

interface Props {
  src: string
  filename: string
  fileId?: number
}

const props = defineProps<Props>()

// State
const audioRef = ref<HTMLAudioElement>()
const useStreaming = ref(true)
const isLoading = ref(false)
const streamUrl = ref<string | null>(null)

// Computed
const audioSrc = computed(() => {
  if (useStreaming.value && props.fileId && streamUrl.value) {
    return streamUrl.value
  }
  return props.src
})

// Methods
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
    const blob = new Blob([response.data], { type: 'audio/mpeg' })
    streamUrl.value = URL.createObjectURL(blob)
    
    console.log('Stream URL created for audio streaming')
  } catch (error) {
    console.error('Failed to load stream URL:', error)
    // Fallback to regular download
    useStreaming.value = false
  } finally {
    isLoading.value = false
  }
}

const onAudioLoad = () => {
  console.log('Audio loaded successfully')
  isLoading.value = false
}

const onAudioError = (error: Event) => {
  console.error('Failed to load audio:', error)
  isLoading.value = false
  
  // If streaming fails, try fallback to download
  if (useStreaming.value) {
    console.log('Streaming failed, falling back to download')
    useStreaming.value = false
  }
}

const onAudioLoadStart = () => {
  console.log('Audio load started')
  isLoading.value = true
}

const onAudioProgress = () => {
  console.log('Audio progress updated')
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
.audio-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* Audio header removed since controls are built into HTML5 audio element */

.audio-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 32px;
  background: #f8f9fa;
  border-radius: 8px;
  padding: 40px;
}

.audio-player-container {
  width: 100%;
  max-width: 500px;
}

.audio-player {
  width: 100%;
  height: 60px;
}

.audio-info {
  width: 100%;
  max-width: 500px;
}

.audio-controls {
  display: flex;
  justify-content: center;
  margin-bottom: 20px;
}

.audio-visualizer {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100px;
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.waveform {
  display: flex;
  align-items: end;
  gap: 2px;
  height: 60px;
}

.wave-bar {
  width: 4px;
  background: linear-gradient(to top, #409eff, #67c23a);
  border-radius: 2px;
  transition: height 0.1s ease;
  animation: wave 1s ease-in-out infinite alternate;
}

.wave-bar:nth-child(odd) {
  animation-delay: 0.1s;
}

.wave-bar:nth-child(even) {
  animation-delay: 0.2s;
}

@keyframes wave {
  0% {
    opacity: 0.3;
  }
  100% {
    opacity: 1;
  }
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
  color: #606266;
  background: rgba(255, 255, 255, 0.9);
  padding: 20px;
  border-radius: 8px;
  z-index: 20;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.loading-overlay .el-icon {
  font-size: 24px;
}

.loading-overlay span {
  font-size: 14px;
  font-weight: 500;
}
</style>
