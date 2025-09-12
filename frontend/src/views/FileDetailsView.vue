<template>
  <div class="file-details-view">
    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <el-icon class="is-loading" size="48">
        <Loading />
      </el-icon>
      <p>Loading file...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-container">
      <el-icon size="48" color="#f56c6c">
        <Warning />
      </el-icon>
      <h2>Error Loading File</h2>
      <p>{{ error }}</p>
      <el-button @click="retryLoad">Retry</el-button>
      <el-button @click="goBack">Go Back</el-button>
    </div>

    <!-- File Content -->
    <div v-else-if="file" class="file-content">
      <!-- File Header -->
      <div class="file-header" v-if="fileType !== 'office'">
        <div class="file-info">
          <h1>{{ file.name }}</h1>
          <div class="file-meta">
            <el-tag :type="getFileTypeTagType(file.item_type)" size="small">
              {{ file.item_type }}
            </el-tag>
            <span v-if="file.file_info?.size" class="file-size">
              {{ formatFileSize(file.file_info.size) }}
            </span>
            <span class="file-date">
              {{ formatDate(file.created_at) }}
            </span>
          </div>
        </div>
        <div class="file-actions">
          <el-button-group>
            <el-button @click="handleDownload" :disabled="loading">
              <el-icon><Download /></el-icon>
              Download
            </el-button>
            <el-button @click="handleOpenInNewTab" :disabled="loading">
              <el-icon><Share /></el-icon>
              Open in New Tab
            </el-button>
            <el-button @click="goBack">
              <el-icon><ArrowLeft /></el-icon>
              Back
            </el-button>
          </el-button-group>
        </div>
      </div>

      <!-- File Reader Content -->
      <div class="file-reader-content">
        <!-- Image Viewer -->
        <ImageViewer
          v-if="fileType === 'image' && fileContent"
          :src="fileContent"
          :alt="file.name"
        />

        <!-- PDF Viewer -->
        <PDFViewer
          v-else-if="fileType === 'pdf' && fileContent"
          :src="fileContent"
          :filename="file.name"
        />

        <!-- Text Viewer -->
        <TextViewer
          v-else-if="fileType === 'text' && fileContent !== null"
          :content="fileContent"
          :filename="file.name"
          :mime-type="file.storage?.mime_type"
          :file-id="file.id"
          @content-updated="handleContentUpdated"
        />

        <!-- JSON Viewer -->
        <JSONViewer
          v-else-if="fileType === 'json' && fileContent !== null"
          :content="fileContent"
          :filename="file.name"
          :file-id="file.id"
          @content-updated="handleContentUpdated"
        />

        <!-- Code Viewer -->
        <CodeViewer
          v-else-if="fileType === 'code' && fileContent !== null"
          :content="fileContent"
          :filename="file.name"
          :language="detectedLanguage"
          :file-id="file.id"
          @content-updated="handleContentUpdated"
        />

        <!-- Video Viewer -->
        <VideoViewer
          v-else-if="fileType === 'video' && fileContent"
          :src="fileContent"
          :filename="file.name"
        />

        <!-- Audio Viewer -->
        <AudioViewer
          v-else-if="fileType === 'audio' && fileContent"
          :src="fileContent"
          :filename="file.name"
        />

        <!-- Office Document Viewer -->
        <OfficeDocumentViewer
          v-else-if="fileType === 'office'"
          :file="file"
          mode="edit"
          height="100%"
          @document-ready="handleDocumentReady"
          @document-saved="handleDocumentSaved"
          @error="handleDocumentError"
        />

        <!-- Unsupported File Type -->
        <UnsupportedViewer v-else :file="file" @download="handleDownload" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Loading, Warning, Download, Share, ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { filesAPI } from '@/services/api'
import { useOfficeConfig } from '@/services/officeConfig'

// Import individual viewers
import ImageViewer from '@/components/readers/ImageViewer.vue'
import PDFViewer from '@/components/readers/PDFViewer.vue'
import TextViewer from '@/components/readers/TextViewer.vue'
import JSONViewer from '@/components/readers/JSONViewer.vue'
import CodeViewer from '@/components/readers/CodeViewer.vue'
import VideoViewer from '@/components/readers/VideoViewer.vue'
import AudioViewer from '@/components/readers/AudioViewer.vue'
import OfficeDocumentViewer from '@/components/readers/OfficeDocumentViewer.vue'
import UnsupportedViewer from '@/components/readers/UnsupportedViewer.vue'

interface FileItem {
  id: number
  name: string
  item_type: 'file' | 'directory'
  parent?: number | null
  created_at: string
  storage?: {
    mime_type?: string
  }
  file_info?: {
    size?: number
  }
}

interface Props {
  fileId: string | string[]
}

const props = defineProps<Props>()

const router = useRouter()

// State
const file = ref<FileItem | null>(null)
const fileContent = ref<string | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

// Services
const officeConfig = useOfficeConfig()

// Computed properties
const fileType = computed(() => {
  if (!file.value) return null

  // Check for office documents first - but only if OnlyOffice is available
  if (officeConfig.isOfficeDocument(file.value) && officeConfig.isOnlyOfficeAvailable.value) {
    return 'office'
  }

  const mimeType = file.value.storage?.mime_type || ''
  const fileName = file.value.name.toLowerCase()

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
  if (!file.value) return 'text'

  const fileName = file.value.name.toLowerCase()

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
const loadFile = async () => {
  if (!props.fileId) return

  loading.value = true
  error.value = null
  fileContent.value = null

  try {
    // First, get file details
    const fileResponse = await filesAPI.get(Number(props.fileId))
    file.value = fileResponse.data

    // Then load file content
    if (fileType.value === 'office') {
      // For office documents, we don't need to load content as the OfficeDocumentViewer handles it
      fileContent.value = null
    } else if (
      fileType.value === 'image' ||
      fileType.value === 'video' ||
      fileType.value === 'audio'
    ) {
      // For media files, create object URL from blob
      const response = await filesAPI.download(file.value!.id)
      const blob = new Blob([response.data])
      fileContent.value = URL.createObjectURL(blob)
    } else {
      // For text-based files, get as text
      const response = await filesAPI.download(file.value!.id)
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
  loadFile()
}

const goBack = () => {
  if (file.value?.parent) {
    // Navigate to parent directory detail view
    router.push({ path: '/files', query: { parent_id: file.value.parent } })
  } else {
    // If no parent, go to root files list
    router.push('/files')
  }
}

const handleDownload = async () => {
  if (!file.value) return

  try {
    const response = await filesAPI.download(file.value.id, { download: 'true' })
    const blob = new Blob([response.data])
    const url = URL.createObjectURL(blob)

    const link = document.createElement('a')
    link.href = url
    link.download = file.value.name
    link.style.display = 'none'

    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    URL.revokeObjectURL(url)
    ElMessage.success(`Downloaded ${file.value.name}`)
  } catch (error: any) {
    console.error('Download error:', error)
    ElMessage.error('Download failed')
  }
}

const handleOpenInNewTab = () => {
  if (!file.value) return

  // Open file in new tab using the dedicated file viewer route
  const fileViewerUrl = `/view/${file.value.id}`
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

const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 Bytes'

  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const getFileTypeTagType = (itemType: string) => {
  return itemType === 'directory' ? 'primary' : 'info'
}

// Watch for fileId changes
watch(
  () => props.fileId,
  async (newFileId) => {
    if (newFileId) {
      // Load OnlyOffice settings first
      await officeConfig.ensureSettingsLoaded()
      loadFile()
    }
  },
  { immediate: true },
)

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
.file-details-view {
  min-height: calc(100vh - 110px);
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}

.loading-container,
.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: calc(100vh - 110px);
  gap: 16px;
  text-align: center;
}

.error-container {
  color: #f56c6c;
}

.error-container h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.file-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0; /* Allow content to shrink */
}

.file-header {
  background: white;
  padding: 20px 24px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.file-info h1 {
  margin: 0 0 8px 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  word-break: break-word;
}

.file-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  color: #606266;
}

.file-size,
.file-date {
  font-size: 13px;
  color: #909399;
}

.file-actions {
  display: flex;
  gap: 12px;
}

.file-reader-content {
  flex: 1; /* Don't grow, size based on content */
  background: white;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
}

/* Let readers size naturally based on their content */
.file-reader-content > * {
  flex: 1;
  min-height: 0;
}
</style>
