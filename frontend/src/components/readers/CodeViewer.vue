<template>
  <div class="code-viewer">
    <div class="code-content" :class="{ 'with-line-numbers': showLineNumbers }">
      <!-- Floating Controls Overlay -->
      <div class="code-controls-overlay">
        <el-button-group>
          <el-button @click="toggleLineNumbers" size="small">
            <el-icon><List /></el-icon>
            {{ showLineNumbers ? 'Hide Lines' : 'Show Lines' }}
          </el-button>
          <el-button @click="copyToClipboard" size="small">
            <el-icon><CopyDocument /></el-icon>
            Copy
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
}

.code-content {
  flex: 1;
  position: relative;
  display: flex;
  background: #1e1e1e;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  overflow: visible;
}

.code-controls-overlay {
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

.code-content:hover .code-controls-overlay {
  opacity: 1;
  transform: translateY(0);
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
