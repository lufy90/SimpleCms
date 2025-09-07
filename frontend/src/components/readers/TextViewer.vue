<template>
  <div class="text-viewer">
    <div class="text-content" :class="{ 'with-line-numbers': showLineNumbers }">
      <!-- Floating Controls Overlay -->
      <div class="text-controls-overlay">
        <el-button-group>
          <el-button @click="toggleEditMode" size="small" :type="isEditing ? 'primary' : 'default'">
            <el-icon><Edit /></el-icon>
            {{ isEditing ? 'View' : 'Edit' }}
          </el-button>
          <el-button @click="wrapText = !wrapText" size="small" v-if="!isEditing">
            <el-icon><DocumentCopy /></el-icon>
            {{ wrapText ? 'No Wrap' : 'Wrap' }}
          </el-button>
          <el-button @click="showLineNumbers = !showLineNumbers" size="small" v-if="!isEditing">
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
      <div v-if="isEditing" class="text-edit-mode" :class="{ 'with-line-numbers': showLineNumbers }">
        <div v-if="showLineNumbers" class="line-numbers">
          <div
            v-for="lineNum in editLineCount"
            :key="lineNum"
            class="line-number"
          >
            {{ lineNum }}
          </div>
        </div>
        
        <div class="text-edit-container">
          <textarea
            ref="textEditor"
            v-model="editedContent"
            class="text-editor"
            :placeholder="`Edit ${filename}...`"
            @keydown="handleKeyDown"
            @input="adjustEditorHeight"
          ></textarea>
        </div>
      </div>
      
      <!-- View Mode -->
      <div v-else class="text-view-mode" :class="{ 'with-line-numbers': showLineNumbers }">
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { Document, DocumentCopy, List, Edit, Check, Close, CopyDocument } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { filesAPI } from '@/services/api'

interface Props {
  content: string
  filename: string
  mimeType?: string
  fileId?: number
}

const props = defineProps<Props>()

// Emits
const emit = defineEmits<{
  contentUpdated: [content: string]
}>()

// State
const wrapText = ref(true)
const showLineNumbers = ref(false)
const isEditing = ref(false)
const isSaving = ref(false)
const editedContent = ref('')
const textEditor = ref<HTMLTextAreaElement | null>(null)

// Computed
const lineCount = computed(() => {
  return props.content.split('\n').length
})

const editLineCount = computed(() => {
  return editedContent.value.split('\n').length
})

// Watch for content changes
watch(() => props.content, (newContent) => {
  editedContent.value = newContent
}, { immediate: true })

// Methods
const adjustEditorHeight = () => {
  if (textEditor.value) {
    // Reset height to auto to get the correct scrollHeight
    textEditor.value.style.height = 'auto'
    // Set height to match content
    textEditor.value.style.height = textEditor.value.scrollHeight + 'px'
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

const copyToClipboard = async () => {
  try {
    await navigator.clipboard.writeText(props.content)
    ElMessage.success('Text copied to clipboard')
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
    const blob = new Blob([editedContent.value], { type: props.mimeType || 'text/plain' })
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
        }
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

.text-edit-mode,
.text-view-mode {
  flex: 1;
  display: flex;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  overflow: visible;
}

.text-edit-mode.with-line-numbers,
.text-view-mode.with-line-numbers {
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

/* Edit mode styles */
.text-edit-container {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.text-editor {
  width: 100%;
  min-height: 1.5em;
  padding: 12px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  line-height: 1.5;
  color: #212529;
  background: #f8f9fa;
  border: 1px solid #e4e7ed;
  outline: none;
  resize: none;
  border-radius: 8px;
  margin: 0;
  box-sizing: border-box;
  overflow: hidden;
}

.text-editor:focus {
  outline: 2px solid #409eff;
  outline-offset: -2px;
  border-color: #409eff;
}

.text-editor::placeholder {
  color: #6c757d;
}
</style>
