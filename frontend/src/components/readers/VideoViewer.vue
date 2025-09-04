<template>
  <div class="video-viewer">
    <div class="video-header">
      <div class="file-info">
        <el-icon><VideoPlay /></el-icon>
        <span>{{ filename }}</span>
      </div>
      <div class="video-controls">
        <el-button-group>
          <el-button @click="toggleFullscreen">
            <el-icon><FullScreen /></el-icon>
            Fullscreen
          </el-button>
        </el-button-group>
      </div>
    </div>
    
    <div class="video-content">
      <video
        ref="videoRef"
        :src="src"
        controls
        class="video-player"
        @loadedmetadata="onVideoLoad"
        @error="onVideoError"
      >
        Your browser does not support the video tag.
      </video>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { VideoPlay, FullScreen } from '@element-plus/icons-vue'

interface Props {
  src: string
  filename: string
}

const props = defineProps<Props>()

// State
const videoRef = ref<HTMLVideoElement>()

// Methods
const toggleFullscreen = () => {
  if (videoRef.value) {
    if (videoRef.value.requestFullscreen) {
      videoRef.value.requestFullscreen()
    }
  }
}

const onVideoLoad = () => {
  console.log('Video loaded successfully')
}

const onVideoError = () => {
  console.error('Failed to load video')
}
</script>

<style scoped>
.video-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 400px;
}

.video-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 0;
  border-bottom: 1px solid #e4e7ed;
  margin-bottom: 16px;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  color: #303133;
}

.video-controls {
  display: flex;
  gap: 12px;
}

.video-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.video-player {
  max-width: 100%;
  max-height: 100%;
  width: auto;
  height: auto;
}
</style>
