<template>
  <div class="text-viewer">
    <div class="text-content" :class="{ 'with-line-numbers': showLineNumbers }">
      <!-- Floating Controls Overlay -->
      <div class="text-controls-overlay">
        <el-button-group>
          <el-button @click="wrapText = !wrapText" size="small">
            <el-icon><DocumentCopy /></el-icon>
            {{ wrapText ? 'No Wrap' : 'Wrap' }}
          </el-button>
          <el-button @click="showLineNumbers = !showLineNumbers" size="small">
            <el-icon><List /></el-icon>
            {{ showLineNumbers ? 'Hide Lines' : 'Show Lines' }}
          </el-button>
        </el-button-group>
      </div>
      <div v-if="showLineNumbers" class="line-numbers">
        <div
          v-for="lineNum in lineCount"
          :key="lineNum"
          class="line-number"
        >
          {{ lineNum }}
        </div>
      </div>
      
      <div class="text-body" :class="{ 'no-wrap': !wrapText }">
        <pre v-if="!wrapText">{{ content }}</pre>
        <div v-else class="wrapped-text">{{ content }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Document, DocumentCopy, List } from '@element-plus/icons-vue'

interface Props {
  content: string
  filename: string
  mimeType?: string
}

const props = defineProps<Props>()

// State
const wrapText = ref(true)
const showLineNumbers = ref(false)

// Computed
const lineCount = computed(() => {
  return props.content.split('\n').length
})
</script>

<style scoped>
.text-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.text-content {
  flex: 1;
  position: relative;
  display: flex;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  overflow: visible;
}

.text-controls-overlay {
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

.text-content:hover .text-controls-overlay {
  opacity: 1;
  transform: translateY(0);
}

.text-content.with-line-numbers {
  background: #fafafa;
}

.line-numbers {
  background: #e9ecef;
  border-right: 1px solid #dee2e6;
  padding: 12px 8px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  color: #6c757d;
  user-select: none;
  min-width: 50px;
  text-align: right;
}

.line-number {
  line-height: 1.5;
  height: 1.5em;
}

.text-body {
  flex: 1;
  padding: 12px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  line-height: 1.5;
  color: #212529;
}

.text-body.no-wrap {
  white-space: pre;
}

.wrapped-text {
  white-space: pre-wrap;
  word-break: break-word;
}

pre {
  margin: 0;
  font-family: inherit;
  font-size: inherit;
  line-height: inherit;
  color: inherit;
}
</style>
