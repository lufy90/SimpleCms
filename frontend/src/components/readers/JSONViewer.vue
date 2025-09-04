<template>
  <div class="json-viewer">
    <div class="json-header">
      <div class="file-info">
        <el-icon><Document /></el-icon>
        <span>{{ filename }}</span>
      </div>
      <div class="json-controls">
        <el-button-group>
          <el-button @click="toggleFormat">
            <el-icon><DocumentCopy /></el-icon>
            {{ formatted ? 'Minify' : 'Format' }}
          </el-button>
          <el-button @click="copyToClipboard">
            <el-icon><CopyDocument /></el-icon>
            Copy
          </el-button>
        </el-button-group>
      </div>
    </div>
    
    <div class="json-content">
      <div v-if="error" class="error-message">
        <el-icon color="#f56c6c"><Warning /></el-icon>
        <span>Invalid JSON: {{ error }}</span>
      </div>
      
      <div v-else class="json-body">
        <pre v-if="formatted" class="formatted-json">{{ formattedJson }}</pre>
        <pre v-else class="minified-json">{{ minifiedJson }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Document, DocumentCopy, CopyDocument, Warning } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

interface Props {
  content: string
  filename: string
}

const props = defineProps<Props>()

// State
const formatted = ref(true)
const error = ref<string | null>(null)

// Computed
const parsedJson = computed(() => {
  try {
    error.value = null
    return JSON.parse(props.content)
  } catch (err: any) {
    error.value = err.message
    return null
  }
})

const formattedJson = computed(() => {
  if (!parsedJson.value) return props.content
  return JSON.stringify(parsedJson.value, null, 2)
})

const minifiedJson = computed(() => {
  if (!parsedJson.value) return props.content
  return JSON.stringify(parsedJson.value)
})

// Methods
const toggleFormat = () => {
  formatted.value = !formatted.value
}

const copyToClipboard = async () => {
  try {
    const textToCopy = formatted.value ? formattedJson.value : minifiedJson.value
    await navigator.clipboard.writeText(textToCopy)
    ElMessage.success('JSON copied to clipboard')
  } catch (err) {
    console.error('Failed to copy to clipboard:', err)
    ElMessage.error('Failed to copy to clipboard')
  }
}
</script>

<style scoped>
.json-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 500px;
  max-height: 80vh;
}

.json-header {
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

.json-controls {
  display: flex;
  gap: 12px;
}

.json-content {
  flex: 1;
  overflow: auto;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}

.error-message {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px;
  color: #f56c6c;
  background: #fef0f0;
  border-radius: 8px;
  margin: 16px;
}

.json-body {
  padding: 16px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  line-height: 1.5;
  color: #212529;
}

.formatted-json {
  margin: 0;
  white-space: pre;
  overflow-x: auto;
}

.minified-json {
  margin: 0;
  white-space: pre;
  word-break: break-all;
  overflow-x: auto;
}

/* JSON syntax highlighting */
.formatted-json {
  color: #212529;
}

/* Basic JSON syntax highlighting */
:deep(.formatted-json) {
  color: #212529;
}

/* You could add more sophisticated syntax highlighting here using a library like Prism.js */
</style>
