<template>
  <div class="image-viewer">
    <div class="image-container">
      <img :src="src" :alt="alt" class="image" @load="onImageLoad" @error="onImageError" />
    </div>

    <!-- Image Controls -->
    <div class="image-controls">
      <el-button-group>
        <el-button @click="zoomIn" :disabled="scale >= maxScale">
          <el-icon><ZoomIn /></el-icon>
        </el-button>
        <el-button @click="zoomOut" :disabled="scale <= minScale">
          <el-icon><ZoomOut /></el-icon>
        </el-button>
        <el-button @click="resetZoom">
          <el-icon><Refresh /></el-icon>
        </el-button>
        <el-button @click="toggleFit">
          <el-icon><FullScreen /></el-icon>
        </el-button>
      </el-button-group>

      <div class="zoom-info">{{ Math.round(scale * 100) }}%</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ZoomIn, ZoomOut, Refresh, FullScreen } from '@element-plus/icons-vue'

interface Props {
  src: string
  alt: string
}

const props = defineProps<Props>()

// State
const scale = ref(1)
const fitToContainer = ref(true)
const minScale = 0.1
const maxScale = 5

// Computed
const imageStyle = computed(() => {
  if (fitToContainer.value) {
    return {
      maxWidth: '100%',
      maxHeight: '100%',
      objectFit: 'contain',
    }
  }

  return {
    transform: `scale(${scale.value})`,
    transformOrigin: 'center center',
  }
})

// Methods
const zoomIn = () => {
  if (scale.value < maxScale) {
    scale.value = Math.min(scale.value * 1.2, maxScale)
    fitToContainer.value = false
  }
}

const zoomOut = () => {
  if (scale.value > minScale) {
    scale.value = Math.max(scale.value / 1.2, minScale)
    fitToContainer.value = false
  }
}

const resetZoom = () => {
  scale.value = 1
  fitToContainer.value = true
}

const toggleFit = () => {
  fitToContainer.value = !fitToContainer.value
  if (fitToContainer.value) {
    scale.value = 1
  }
}

const onImageLoad = () => {
  console.log('Image loaded successfully')
}

const onImageError = () => {
  console.error('Failed to load image')
}
</script>

<style scoped>
.image-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.image-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
  border-radius: 8px;
  padding: 20px;
  overflow: visible;
}

.image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s ease;
}

.image-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 0;
  border-top: 1px solid #e4e7ed;
  margin-top: 16px;
}

.zoom-info {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}
</style>
