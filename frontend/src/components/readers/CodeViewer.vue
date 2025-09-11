<template>
  <div class="code-viewer">
    <div class="code-content" :class="{ 'with-line-numbers': showLineNumbers }">
      <!-- Floating Controls Overlay -->
      <div class="code-controls-overlay">
        <el-button-group>
          <el-button @click="toggleEditMode" size="small" :type="isEditing ? 'primary' : 'default'">
            <el-icon><Edit /></el-icon>
            {{ isEditing ? 'View' : 'Edit' }}
          </el-button>
          <el-button @click="toggleLineNumbers" size="small" v-if="!isEditing">
            <el-icon><List /></el-icon>
            {{ showLineNumbers ? 'Hide Lines' : 'Show Lines' }}
          </el-button>
          <el-button @click="copyToClipboard" size="small" v-if="!isEditing">
            <el-icon><CopyDocument /></el-icon>
            Copy
          </el-button>
          <el-button @click="saveContent" size="small" v-if="isEditing" :loading="isSaving">
            <el-icon><Check /></el-icon>
            Save
          </el-button>
          <el-button @click="cancelEdit" size="small" v-if="isEditing">
            <el-icon><Close /></el-icon>
            Cancel
          </el-button>
        </el-button-group>
      </div>

      <!-- Edit Mode -->
      <div
        v-if="isEditing"
        class="code-edit-mode"
        :class="{ 'with-line-numbers': showLineNumbers }"
      >
        <div v-if="showLineNumbers" class="line-numbers">
          <div v-for="lineNum in editLineCount" :key="lineNum" class="line-number">
            {{ lineNum }}
          </div>
        </div>

        <div class="code-edit-container">
          <textarea
            ref="codeEditor"
            v-model="editedContent"
            class="code-editor"
            :placeholder="`Edit ${filename}...`"
            @keydown="handleKeyDown"
            @input="adjustEditorHeight"
          ></textarea>
        </div>
      </div>

      <!-- View Mode -->
      <div v-else class="code-view-mode" :class="{ 'with-line-numbers': showLineNumbers }">
        <div v-if="showLineNumbers" class="line-numbers">
          <div v-for="lineNum in lineCount" :key="lineNum" class="line-number">
            {{ lineNum }}
          </div>
        </div>

        <div class="code-body">
          <pre><code :class="`language-${language}`">{{ content }}</code></pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { Document, List, CopyDocument, Edit, Check, Close } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { filesAPI } from '@/services/api'

interface Props {
  content: string
  filename: string
  language: string
  fileId?: number
}

const props = defineProps<Props>()

// Emits
const emit = defineEmits<{
  contentUpdated: [content: string]
}>()

// State
const showLineNumbers = ref(true)
const isEditing = ref(false)
const isSaving = ref(false)
const editedContent = ref('')
const codeEditor = ref<HTMLTextAreaElement | null>(null)

// Computed
const lineCount = computed(() => {
  return props.content.split('\n').length
})

const editLineCount = computed(() => {
  return editedContent.value.split('\n').length
})

// Watch for content changes
watch(
  () => props.content,
  (newContent) => {
    editedContent.value = newContent
  },
  { immediate: true },
)

// Methods
const adjustEditorHeight = () => {
  if (codeEditor.value) {
    // Reset height to auto to get the correct scrollHeight
    codeEditor.value.style.height = 'auto'
    // Set height to match content
    codeEditor.value.style.height = codeEditor.value.scrollHeight + 'px'
  }
}

const toggleEditMode = () => {
  if (isEditing.value) {
    // Switching to view mode
    isEditing.value = false
  } else {
    // Switching to edit mode
    editedContent.value = props.content
    isEditing.value = true
    // Adjust height after switching to edit mode
    nextTick(() => {
      adjustEditorHeight()
    })
  }
}

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

const handleKeyDown = (event: KeyboardEvent) => {
  // Save on Ctrl+S
  if (event.ctrlKey && event.key === 's') {
    event.preventDefault()
    saveContent()
  }
  // Cancel on Escape
  if (event.key === 'Escape') {
    cancelEdit()
  }
}

const saveContent = async () => {
  if (!props.fileId) {
    ElMessage.error('File ID is required for saving')
    return
  }

  if (editedContent.value === props.content) {
    ElMessage.info('No changes to save')
    isEditing.value = false
    return
  }

  try {
    isSaving.value = true

    // Create FormData for file update
    const formData = new FormData()
    const blob = new Blob([editedContent.value], { type: 'text/plain' })
    formData.append('file', blob, props.filename)

    await filesAPI.updateContent(props.fileId, formData)

    ElMessage.success('File saved successfully')
    isEditing.value = false
    emit('contentUpdated', editedContent.value)
  } catch (error: any) {
    console.error('Failed to save file:', error)
    ElMessage.error('Failed to save file: ' + (error.response?.data?.error || error.message))
  } finally {
    isSaving.value = false
  }
}

const cancelEdit = async () => {
  if (editedContent.value !== props.content) {
    try {
      await ElMessageBox.confirm(
        'You have unsaved changes. Are you sure you want to cancel?',
        'Confirm Cancel',
        {
          confirmButtonText: 'Discard Changes',
          cancelButtonText: 'Continue Editing',
          type: 'warning',
        },
      )
    } catch {
      return // User chose to continue editing
    }
  }

  editedContent.value = props.content
  isEditing.value = false
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

.code-edit-mode,
.code-view-mode {
  flex: 1;
  display: flex;
  background: #1e1e1e;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  overflow: visible;
}

.code-edit-mode.with-line-numbers,
.code-view-mode.with-line-numbers {
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

/* Edit mode styles */
.code-edit-container {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.code-editor {
  width: 100%;
  min-height: 1.5em;
  padding: 12px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  line-height: 1.5;
  color: #d4d4d4;
  background: #1e1e1e;
  border: none;
  outline: none;
  resize: none;
  border-radius: 0;
  margin: 0;
  box-sizing: border-box;
  overflow: hidden;
}

.code-editor:focus {
  outline: 2px solid #409eff;
  outline-offset: -2px;
}

.code-editor::placeholder {
  color: #858585;
}

/* You could integrate a proper syntax highlighting library like Prism.js or highlight.js here */
</style>
