<template>
  <div class="code-viewer">
    <div class="code-header">
      <div class="file-info">
        <el-icon><Document /></el-icon>
        <span>{{ filename }}</span>
        <el-tag size="small" type="info">{{ language }}</el-tag>
      </div>
      <div class="code-controls">
        <el-button-group>
          <el-button @click="toggleLineNumbers">
            <el-icon><List /></el-icon>
            {{ showLineNumbers ? 'Hide Lines' : 'Show Lines' }}
          </el-button>
          <el-button @click="copyToClipboard">
            <el-icon><CopyDocument /></el-icon>
            Copy
          </el-button>
        </el-button-group>
      </div>
    </div>
    
    <div class="code-content" :class="{ 'with-line-numbers': showLineNumbers }">
      <div v-if="showLineNumbers" class="line-numbers">
        <div
          v-for="lineNum in lineCount"
          :key="lineNum"
          class="line-number"
        >
          {{ lineNum }}
        </div>
      </div>
      
      <div class="code-body">
        <pre><code :class="`language-${language}`">{{ content }}</code></pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Document, List, CopyDocument } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

interface Props {
  content: string
  filename: string
  language: string
}

const props = defineProps<Props>()

// State
const showLineNumbers = ref(true)

// Computed
const lineCount = computed(() => {
  return props.content.split('\n').length
})

// Methods
const toggleLineNumbers = () => {
  showLineNumbers.value = !showLineNumbers.value
}

const copyToClipboard = async () => {
  try {
    await navigator.clipboard.writeText(props.content)
    ElMessage.success('Code copied to clipboard')
  } catch (err) {
    console.error('Failed to copy to clipboard:', err)
    ElMessage.error('Failed to copy to clipboard')
  }
}
</script>

<style scoped>
.code-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 500px;
  max-height: 80vh;
}

.code-header {
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

.code-controls {
  display: flex;
  gap: 12px;
}

.code-content {
  flex: 1;
  display: flex;
  overflow: auto;
  background: #1e1e1e;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}

.code-content.with-line-numbers {
  background: #1e1e1e;
}

.line-numbers {
  background: #2d2d30;
  border-right: 1px solid #3e3e42;
  padding: 12px 8px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  color: #858585;
  user-select: none;
  min-width: 50px;
  text-align: right;
}

.line-number {
  line-height: 1.5;
  height: 1.5em;
}

.code-body {
  flex: 1;
  overflow: auto;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  line-height: 1.5;
  color: #d4d4d4;
}

.code-body pre {
  margin: 0;
  padding: 12px;
  background: transparent;
  color: inherit;
  font-family: inherit;
  font-size: inherit;
  line-height: inherit;
  overflow-x: auto;
}

.code-body code {
  background: transparent;
  color: inherit;
  font-family: inherit;
  font-size: inherit;
  line-height: inherit;
}

/* Basic syntax highlighting for common languages */
:deep(.language-javascript),
:deep(.language-js) {
  color: #d4d4d4;
}

:deep(.language-typescript),
:deep(.language-ts) {
  color: #d4d4d4;
}

:deep(.language-python) {
  color: #d4d4d4;
}

:deep(.language-html) {
  color: #d4d4d4;
}

:deep(.language-css) {
  color: #d4d4d4;
}

:deep(.language-json) {
  color: #d4d4d4;
}

/* You could integrate a proper syntax highlighting library like Prism.js or highlight.js here */
</style>
