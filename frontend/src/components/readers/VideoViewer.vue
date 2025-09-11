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
        </el-button-group>
      </div>
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
  filename: string | 'File'
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
</style>
