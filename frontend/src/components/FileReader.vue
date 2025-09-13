<template>
  <el-dialog
    v-model="visible"
    :title="`${file?.name} - File Viewer`"
    width="90%"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <el-icon class="is-loading" size="48">
        <Loading />
      </el-icon>
      <p>Loading file...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <el-icon size="48" color="#f56c6c">
        <Warning />
      </el-icon>
      <p>{{ error }}</p>
      <el-button @click="retryLoad">Retry</el-button>
    </div>

    <!-- File Content -->
    <div v-else-if="fileContent">
      <!-- Image Viewer -->
      <ImageViewer v-if="fileType === 'image'" :src="fileContent" :alt="file?.name || 'File'" />

      <!-- PDF Viewer -->
      <PDFViewer
        v-else-if="fileType === 'pdf'"
        :src="fileContent"
        :filename="file?.name || 'File'"
      />

      <!-- Text Viewer -->
      <TextViewer
        v-else-if="fileType === 'text' && fileContent !== null"
        :content="fileContent"
        :filename="file?.name || 'File'"
        :mime-type="file?.storage?.mime_type"
        :file-id="file?.id"
        @content-updated="handleContentUpdated"
      />

      <!-- JSON Viewer -->
      <JSONViewer
        v-else-if="fileType === 'json' && fileContent !== null"
        :content="fileContent"
        :filename="file?.name || 'File'"
        :file-id="file?.id"
        @content-updated="handleContentUpdated"
      />

      <!-- Code Viewer -->
      <CodeViewer
        v-else-if="fileType === 'code' && fileContent !== null"
        :content="fileContent"
        :filename="file?.name || 'File'"
        :language="detectedLanguage"
        :file-id="file?.id"
        @content-updated="handleContentUpdated"
      />

      <!-- Video Viewer -->
      <VideoViewer
        v-else-if="fileType === 'video'"
        :src="fileContent"
        :filename="file?.name || 'File'"
      />

      <!-- Audio Viewer -->
      <AudioViewer
        v-else-if="fileType === 'audio'"
        :src="fileContent"
        :filename="file?.name || 'File'"
      />

      <!-- Office Document Viewer -->
      <OfficeDocumentViewer
        v-else-if="fileType === 'office'"
        :file="file"
        mode="edit"
        height="600px"
        @document-ready="handleDocumentReady"
        @document-saved="handleDocumentSaved"
        @error="handleDocumentError"
      />

      <!-- Unsupported File Type -->
      <UnsupportedViewer v-else :file="file" @download="handleDownload" />
    </div>

    <template #footer>
      <div class="footer-actions">
        <el-button @click="handleDownload" :disabled="loading">
          <el-icon><Download /></el-icon>
          Download
        </el-button>
        <el-button @click="handleOpenInNewTab" :disabled="loading">
          <el-icon><Share /></el-icon>
          Open in New Tab
        </el-button>
        <el-button type="primary" @click="visible = false"> Close </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { Loading, Warning, Download, Share } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { filesAPI } from '@/services/api'
import { useOfficeConfig } from '@/services/officeConfig'

// Import individual viewers
import ImageViewer from './readers/ImageViewer.vue'
import PDFViewer from './readers/PDFViewer.vue'
import TextViewer from './readers/TextViewer.vue'
import JSONViewer from './readers/JSONViewer.vue'
import CodeViewer from './readers/CodeViewer.vue'
import VideoViewer from './readers/VideoViewer.vue'
import AudioViewer from './readers/AudioViewer.vue'
import OfficeDocumentViewer from './readers/OfficeDocumentViewer.vue'
import UnsupportedViewer from './readers/UnsupportedViewer.vue'

interface FileItem {
  id: number
  name: string
  item_type: 'file' | 'directory'
  storage?: {
    mime_type?: string
  }
  file_info?: {
    size?: number
  }
}

interface Props {
  file: FileItem | null
  modelValue: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  close: []
}>()

// Services
const officeConfig = useOfficeConfig()

// State
const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const fileContent = ref<string | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

// Computed properties
const fileType = computed(() => {
  if (!props.file) return null

  // Check for office documents first - but only if OnlyOffice is available
  if (officeConfig.isOfficeDocument(props.file) && officeConfig.isOnlyOfficeAvailable.value) {
    return 'office'
  }

  const mimeType = props.file.storage?.mime_type || ''
  const fileName = props.file.name.toLowerCase()

  // Image types
  if (mimeType.startsWith('image/') || /\.(jpg|jpeg|png|gif|webp|svg|bmp)$/i.test(fileName)) {
    return 'image'
  }

  // PDF
  if (mimeType === 'application/pdf' || fileName.endsWith('.pdf')) {
    return 'pdf'
  }

  // Video
  if (mimeType.startsWith('video/') || /\.(mp4|webm|ogg|avi|mov)$/i.test(fileName)) {
    return 'video'
  }

  // Audio
  if (mimeType.startsWith('audio/') || /\.(mp3|wav|ogg|m4a)$/i.test(fileName)) {
    return 'audio'
  }

  // JSON
  if (mimeType === 'application/json' || fileName.endsWith('.json')) {
    return 'json'
  }

  // Code files
  if (
    /\.(js|ts|jsx|tsx|py|java|cpp|c|cs|php|rb|go|rs|swift|kt|scala|sh|bash|sql|html|css|scss|less|xml|yaml|yml|toml|ini|conf)$/i.test(
      fileName,
    )
  ) {
    return 'code'
  }

  // Text files
  if (mimeType.startsWith('text/') || /\.(txt|md|log|csv)$/i.test(fileName)) {
    return 'text'
  }

  return 'unsupported'
})

const detectedLanguage = computed(() => {
  if (!props.file) return 'text'

  const fileName = props.file.name.toLowerCase()

  // Language detection based on file extension
  const languageMap: Record<string, string> = {
    '.js': 'javascript',
    '.ts': 'typescript',
    '.jsx': 'jsx',
    '.tsx': 'tsx',
    '.py': 'python',
    '.java': 'java',
    '.cpp': 'cpp',
    '.c': 'c',
    '.cs': 'csharp',
    '.php': 'php',
    '.rb': 'ruby',
    '.go': 'go',
    '.rs': 'rust',
    '.swift': 'swift',
    '.kt': 'kotlin',
    '.scala': 'scala',
    '.sh': 'bash',
    '.bash': 'bash',
    '.sql': 'sql',
    '.html': 'html',
    '.css': 'css',
    '.scss': 'scss',
    '.less': 'less',
    '.xml': 'xml',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.toml': 'toml',
    '.ini': 'ini',
    '.conf': 'ini',
    '.md': 'markdown',
    '.json': 'json',
  }

  for (const [ext, lang] of Object.entries(languageMap)) {
    if (fileName.endsWith(ext)) {
      return lang
    }
  }

  return 'text'
})

// Methods
const loadFileContent = async () => {
  if (!props.file) return

  // For office documents, we don't need to load content as the OfficeDocumentViewer handles it
  if (fileType.value === 'office') {
    loading.value = false
    return
  }

  loading.value = true
  error.value = null
  fileContent.value = null

  console.log('fileType:',fileType.value)

  try {
    if (fileType.value === 'image' || fileType.value === 'video' || fileType.value === 'audio' || fileType.value == 'pdf') {
      // For media files, create object URL from blob
      const response = await filesAPI.download(props.file.id)
      const blob = new Blob([response.data])
      fileContent.value = URL.createObjectURL(blob)
      console.log('xxxxxxxxxxxxxxxxxxxxxxxxxurl:',fileContent.value)
    } else {
      // For text-based files, get as text
      const response = await filesAPI.download(props.file.id)
      const text = await response.data.text()
      fileContent.value = text
    }
  } catch (err: any) {
    console.error('Error loading file:', err)
    error.value = err.response?.data?.error || err.message || 'Failed to load file'
  } finally {
    loading.value = false
  }
}

const retryLoad = () => {
  loadFileContent()
}

const handleDownload = async () => {
  if (!props.file) return

  try {
    const response = await filesAPI.download(props.file.id, { download: 'true' })
    const blob = new Blob([response.data])
    const url = URL.createObjectURL(blob)

    const link = document.createElement('a')
    link.href = url
    link.download = props.file.name
    link.style.display = 'none'

    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    URL.revokeObjectURL(url)
    ElMessage.success(`Downloaded ${props.file.name}`)
  } catch (error: any) {
    console.error('Download error:', error)
    ElMessage.error('Download failed')
  }
}

const handleOpenInNewTab = () => {
  if (!props.file) return

  // Open file in new tab using the dedicated file viewer route
  const fileViewerUrl = `/view/${props.file.id}`
  window.open(fileViewerUrl, '_blank')
}

const handleContentUpdated = (newContent: string) => {
  // Update the local content when file is edited
  fileContent.value = newContent
  ElMessage.success('File content updated')
}

const handleDocumentReady = () => {
  ElMessage.success('Document editor ready')
}

const handleDocumentSaved = (document: any) => {
  ElMessage.success('Document saved successfully')
}

const handleDocumentError = (error: string) => {
  ElMessage.error(`Document error: ${error}`)
}

const handleClose = () => {
  // Clean up object URLs
  if (
    fileContent.value &&
    (fileType.value === 'image' || fileType.value === 'video' || fileType.value === 'audio')
  ) {
    URL.revokeObjectURL(fileContent.value)
  }
  fileContent.value = null
  error.value = null
  emit('close')
}

// Watch for file changes
watch(
  () => props.file,
  async (newFile) => {
    if (newFile && visible.value) {
      // Load OnlyOffice settings first
      await officeConfig.ensureSettingsLoaded()
      loadFileContent()
    }
  },
  { immediate: true },
)

// Watch for dialog visibility
watch(visible, async (newVisible) => {
  if (newVisible && props.file) {
    // Load OnlyOffice settings first
    await officeConfig.ensureSettingsLoaded()
    loadFileContent()
  } else if (!newVisible) {
    handleClose()
  }
})

// Cleanup on unmount
onMounted(() => {
  return () => {
    if (
      fileContent.value &&
      (fileType.value === 'image' || fileType.value === 'video' || fileType.value === 'audio')
    ) {
      URL.revokeObjectURL(fileContent.value)
    }
  }
})
</script>

<style scoped>
/* Minimal styles only for loading/error states */
.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  gap: 16px;
}

.error-state {
  color: #f56c6c;
}

.footer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.footer-actions .el-button {
  display: flex;
  align-items: center;
  gap: 6px;
}
</style>
