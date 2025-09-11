<template>
  <div class="json-viewer">
    <div class="json-content">
      <!-- Floating Controls Overlay -->
      <div class="json-controls-overlay">
        <el-button-group>
          <el-button @click="toggleEditMode" size="small" :type="isEditing ? 'primary' : 'default'">
            <el-icon><Edit /></el-icon>
            {{ isEditing ? 'View' : 'Edit' }}
          </el-button>
          <el-button @click="toggleFormat" size="small" v-if="!isEditing">
            <el-icon><DocumentCopy /></el-icon>
            {{ formatted ? 'Minify' : 'Format' }}
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
      <div v-if="isEditing" class="json-edit-mode">
        <div class="json-edit-container">
          <textarea
            ref="jsonEditor"
            v-model="editedContent"
            class="json-editor"
            :placeholder="`Edit ${filename}...`"
            @keydown="handleKeyDown"
            @input="adjustEditorHeight"
            :class="{ 'json-error': editError }"
          ></textarea>
          <div v-if="editError" class="edit-error-message">
            <el-icon color="#f56c6c"><Warning /></el-icon>
            <span>Invalid JSON: {{ editError }}</span>
          </div>
        </div>
      </div>

      <!-- View Mode -->
      <div v-else class="json-view-mode">
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import {
  Document,
  DocumentCopy,
  CopyDocument,
  Warning,
  Edit,
  Check,
  Close,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { filesAPI } from '@/services/api'

interface Props {
  content: string
  filename: string
  fileId?: number
}

const props = defineProps<Props>()

// Emits
const emit = defineEmits<{
  contentUpdated: [content: string]
}>()

// State
const formatted = ref(true)
const error = ref<string | null>(null)
const isEditing = ref(false)
const isSaving = ref(false)
const editedContent = ref('')
const editError = ref<string | null>(null)
const jsonEditor = ref<HTMLTextAreaElement | null>(null)

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

// Watch for content changes
watch(
  () => props.content,
  (newContent) => {
    editedContent.value = newContent
  },
  { immediate: true },
)

// Watch for edit content changes to validate JSON
watch(editedContent, (newContent) => {
  if (isEditing.value) {
    try {
      JSON.parse(newContent)
      editError.value = null
    } catch (err: any) {
      editError.value = err.message
    }
  }
})

// Methods
const adjustEditorHeight = () => {
  if (jsonEditor.value) {
    // Reset height to auto to get the correct scrollHeight
    jsonEditor.value.style.height = 'auto'
    // Set height to match content
    jsonEditor.value.style.height = jsonEditor.value.scrollHeight + 'px'
  }
}

const toggleEditMode = () => {
  if (isEditing.value) {
    // Switching to view mode
    isEditing.value = false
    editError.value = null
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

  if (editError.value) {
    ElMessage.error('Please fix JSON syntax errors before saving')
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
    const blob = new Blob([editedContent.value], { type: 'application/json' })
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
  editError.value = null
}
</script>

<style scoped>
.json-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.json-content {
  flex: 1;
  position: relative;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  overflow: visible;
}

.json-controls-overlay {
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

.json-content:hover .json-controls-overlay {
  opacity: 1;
  transform: translateY(0);
}

.json-edit-mode,
.json-view-mode {
  flex: 1;
  display: flex;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  overflow: visible;
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
}

.minified-json {
  margin: 0;
  white-space: pre;
  word-break: break-all;
}

/* JSON syntax highlighting */
.formatted-json {
  color: #212529;
}

/* Basic JSON syntax highlighting */
:deep(.formatted-json) {
  color: #212529;
}

/* Edit mode styles */
.json-edit-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px;
}

.json-editor {
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

.json-editor:focus {
  outline: 2px solid #409eff;
  outline-offset: -2px;
  border-color: #409eff;
}

.json-editor.json-error {
  border-color: #f56c6c;
  background: #fef0f0;
}

.json-editor::placeholder {
  color: #6c757d;
}

.edit-error-message {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  margin-top: 8px;
  color: #f56c6c;
  background: #fef0f0;
  border-radius: 6px;
  font-size: 12px;
}

/* You could add more sophisticated syntax highlighting here using a library like Prism.js */
</style>
