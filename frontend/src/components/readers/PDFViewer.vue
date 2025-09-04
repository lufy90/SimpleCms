<template>
  <div class="pdf-viewer">
    <div class="pdf-header">
      <div class="file-info">
        <el-icon><Document /></el-icon>
        <span>{{ filename }}</span>
      </div>
      <div class="pdf-controls">
        <el-button-group>
          <el-button @click="zoomOut" :disabled="scale <= 0.5">
            <el-icon><ZoomOut /></el-icon>
          </el-button>
          <el-button @click="resetZoom">
            {{ Math.round(scale * 100) }}%
          </el-button>
          <el-button @click="zoomIn" :disabled="scale >= 3">
            <el-icon><ZoomIn /></el-icon>
          </el-button>
        </el-button-group>
      </div>
    </div>
    
    <div class="pdf-content">
      <div v-if="error" class="error-message">
        <el-icon color="#f56c6c"><Warning /></el-icon>
        <span>{{ error }}</span>
        <el-button @click="openInNewTab" type="primary">
          Open in New Tab
        </el-button>
      </div>
      
      <div v-else class="pdf-container">
        <iframe
          :src="pdfUrl"
          class="pdf-iframe"
          :style="{ transform: `scale(${scale})` }"
          @load="onPdfLoad"
          @error="onPdfError"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Document, ZoomIn, ZoomOut, Warning } from '@element-plus/icons-vue'

interface Props {
  src: string
  filename: string
}

const props = defineProps<Props>()

// State
const scale = ref(1)
const error = ref<string | null>(null)

// Computed
const pdfUrl = computed(() => {
  return `${props.src}#toolbar=1&navpanes=1&scrollbar=1`
})

// Methods
const zoomIn = () => {
  if (scale.value < 3) {
    scale.value = Math.min(scale.value * 1.2, 3)
  }
}

const zoomOut = () => {
  if (scale.value > 0.5) {
    scale.value = Math.max(scale.value / 1.2, 0.5)
  }
}

const resetZoom = () => {
  scale.value = 1
}

const openInNewTab = () => {
  window.open(props.src, '_blank')
}

const onPdfLoad = () => {
  error.value = null
}

const onPdfError = () => {
  error.value = 'Failed to load PDF. Your browser may not support PDF viewing.'
}
</script>

<style scoped>
.pdf-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 500px;
  max-height: 80vh;
}

.pdf-header {
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

.pdf-controls {
  display: flex;
  gap: 12px;
}

.pdf-content {
  flex: 1;
  overflow: auto;
  background: #f5f5f5;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  position: relative;
}

.error-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 40px;
  color: #f56c6c;
  text-align: center;
  min-height: 300px;
}

.pdf-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100%;
  padding: 20px;
}

.pdf-iframe {
  width: 100%;
  height: 600px;
  border: none;
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform-origin: center center;
  transition: transform 0.2s ease;
}
</style>
