<template>
  <div class="audio-viewer">
    <div class="audio-header">
      <div class="file-info">
        <el-icon><Microphone /></el-icon>
        <span>{{ filename }}</span>
      </div>
    </div>
    
    <div class="audio-content">
      <div class="audio-player-container">
        <audio
          ref="audioRef"
          :src="src"
          controls
          class="audio-player"
          @loadedmetadata="onAudioLoad"
          @error="onAudioError"
        >
          Your browser does not support the audio tag.
        </audio>
      </div>
      
      <div class="audio-info">
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
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Microphone } from '@element-plus/icons-vue'

interface Props {
  src: string
  filename: string
}

const props = defineProps<Props>()

// State
const audioRef = ref<HTMLAudioElement>()

// Methods
const onAudioLoad = () => {
  console.log('Audio loaded successfully')
}

const onAudioError = () => {
  console.error('Failed to load audio')
}
</script>

<style scoped>
.audio-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 400px;
}

.audio-header {
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
</style>
