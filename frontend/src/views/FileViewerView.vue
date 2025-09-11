<template>
  <div class="file-viewer">
    <div v-if="loading" class="loading-container">
      <el-icon class="is-loading" size="32">
        <Loading />
      </el-icon>
      <p>Loading file...</p>
    </div>

    <div v-else-if="error" class="error-container">
      <el-icon size="48" color="#f56c6c">
        <Warning />
      </el-icon>
      <h3>Error Loading File</h3>
      <p>{{ error }}</p>
      <el-button @click="retry" type="primary">Retry</el-button>
    </div>

    <div v-else-if="file" class="file-content">
      <!-- File Header -->
      <div class="file-header" v-show="fileType !== 'office'">
        <div class="file-info">
          <el-icon><Document /></el-icon>
          <span class="file-name">{{ file.name }}</span>
          <el-tag v-if="file.file_info?.size" size="small">
            {{ formatFileSize(file.file_info.size) }}
          </el-tag>
        </div>
        <div class="file-actions">
          <el-button @click="downloadFile" :loading="downloading">
            <el-icon><Download /></el-icon>
            Download
          </el-button>
        </div>
      </div>

      <!-- File Content -->
      <div class="file-display">
        <!-- Image Viewer -->
        <ImageViewer
          v-if="fileType === 'image' && fileContent"
          :src="fileContent"
          :alt="file?.name || ''"
        />

        <!-- PDF Viewer -->
        <PDFViewer
          v-else-if="fileType === 'pdf' && fileContent"
          :src="fileContent"
          :filename="file?.name || ''"
        />

        <!-- Text Viewer -->
        <TextViewer
          v-else-if="fileType === 'text' && textContent"
          :content="textContent"
          :filename="file?.name || ''"
          :file-id="file?.id"
          @content-updated="handleContentUpdated"
        />

        <!-- JSON Viewer -->
        <JSONViewer
          v-else-if="fileType === 'json' && textContent"
          :content="textContent"
          :filename="file?.name || ''"
          :file-id="file?.id"
          @content-updated="handleContentUpdated"
        />

        <!-- Code Viewer -->
        <CodeViewer
          v-else-if="fileType === 'code' && textContent"
          :content="textContent"
          :filename="file?.name || ''"
          :language="detectLanguage(file?.name || '')"
          :file-id="file?.id"
          @content-updated="handleContentUpdated"
        />

        <!-- Video Viewer -->
        <VideoViewer
          v-else-if="fileType === 'video' && fileContent"
          :src="fileContent"
          :filename="file?.name || ''"
        />

        <!-- Audio Viewer -->
        <AudioViewer
          v-else-if="fileType === 'audio' && fileContent"
          :src="fileContent"
          :filename="file?.name || ''"
        />

        <!-- Office Document Viewer -->
        <OfficeDocumentViewerSimple
          v-else-if="fileType === 'office'"
          :file="file"
          mode="edit"
          height="600px"
          @document-ready="handleDocumentReady"
          @document-saved="handleDocumentSaved"
          @error="handleDocumentError"
        />

        <!-- Unsupported File -->
        <UnsupportedViewer v-else :file="file" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { Document, Download, Loading, Warning } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { filesAPI } from '@/services/api'
import { useOfficeConfig } from '@/services/officeConfig'
import ImageViewer from '@/components/readers/ImageViewer.vue'
import PDFViewer from '@/components/readers/PDFViewer.vue'
import TextViewer from '@/components/readers/TextViewer.vue'
import JSONViewer from '@/components/readers/JSONViewer.vue'
import CodeViewer from '@/components/readers/CodeViewer.vue'
import VideoViewer from '@/components/readers/VideoViewer.vue'
import AudioViewer from '@/components/readers/AudioViewer.vue'
import OfficeDocumentViewerSimple from '@/components/readers/OfficeDocumentViewerSimple.vue'
import UnsupportedViewer from '@/components/readers/UnsupportedViewer.vue'

// Props
interface FileItem {
  id: number
  name: string
  item_type: 'file' | 'directory'
  storage?: {
    mime_type?: string
    extension?: string
  }
  file_info?: {
    size?: number
  }
}

// State
const route = useRoute()
const file = ref<FileItem | null>(null)
const fileContent = ref<string | null>(null)
const textContent = ref<string | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const downloading = ref(false)

// Services
const officeConfig = useOfficeConfig()

// Computed
const fileType = computed(() => {
  if (!file.value) return 'unknown'

  // Check for office documents first
  if (officeConfig.isOfficeDocument(file.value)) {
    return 'office'
  }

  const mimeType = file.value.storage?.mime_type || ''
  const extension = file.value.storage?.extension || ''
  const fileName = file.value.name.toLowerCase()

  // Image files
  if (
    mimeType.startsWith('image/') ||
    ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp'].some(
      (ext) => extension === ext || fileName.endsWith(`.${ext}`),
    )
  ) {
    return 'image'
  }

  // PDF files
  if (mimeType === 'application/pdf' || extension === 'pdf' || fileName.endsWith('.pdf')) {
    return 'pdf'
  }

  // Text files
  if (
    mimeType.startsWith('text/') ||
    ['txt', 'md', 'csv', 'log'].some((ext) => extension === ext || fileName.endsWith(`.${ext}`))
  ) {
    return 'text'
  }

  // JSON files
  if (mimeType === 'application/json' || extension === 'json' || fileName.endsWith('.json')) {
    return 'json'
  }

  // Code files
  if (
    [
      'js',
      'ts',
      'jsx',
      'tsx',
      'vue',
      'html',
      'css',
      'scss',
      'py',
      'java',
      'cpp',
      'c',
      'php',
      'rb',
      'go',
      'rs',
    ].some((ext) => extension === ext || fileName.endsWith(`.${ext}`))
  ) {
    return 'code'
  }

  // Video files
  if (
    mimeType.startsWith('video/') ||
    ['mp4', 'webm', 'ogg', 'avi', 'mov'].some(
      (ext) => extension === ext || fileName.endsWith(`.${ext}`),
    )
  ) {
    return 'video'
  }

  // Audio files
  if (
    mimeType.startsWith('audio/') ||
    ['mp3', 'wav', 'ogg', 'aac', 'flac'].some(
      (ext) => extension === ext || fileName.endsWith(`.${ext}`),
    )
  ) {
    return 'audio'
  }

  return 'unsupported'
})

// JSON formatting is now handled by JSONViewer component

// Detect programming language from filename
const detectLanguage = (filename: string) => {
  const ext = filename.toLowerCase().split('.').pop()
  const languageMap: { [key: string]: string } = {
    js: 'javascript',
    ts: 'typescript',
    jsx: 'jsx',
    tsx: 'tsx',
    vue: 'vue',
    html: 'html',
    css: 'css',
    scss: 'scss',
    py: 'python',
    java: 'java',
    cpp: 'cpp',
    c: 'c',
    php: 'php',
    rb: 'ruby',
    go: 'go',
    rs: 'rust',
    sh: 'bash',
    sql: 'sql',
    xml: 'xml',
    yaml: 'yaml',
    yml: 'yaml',
    json: 'json',
    md: 'markdown',
  }
  return languageMap[ext || ''] || 'text'
}

// Methods
const loadFile = async () => {
  const fileId = route.params.id as string

  if (!fileId) {
    error.value = 'No file ID provided'
    loading.value = false
    return
  }

  try {
    loading.value = true
    error.value = null

    // Get file metadata first
    const fileResponse = await filesAPI.getFile(parseInt(fileId))
    file.value = fileResponse.data

    // Download file content (skip for office documents)
    const currentFileType = fileType.value
    if (currentFileType !== 'office') {
      const contentResponse = await filesAPI.download(parseInt(fileId))
      const blob = new Blob([contentResponse.data])
      const objectUrl = URL.createObjectURL(blob)
      fileContent.value = objectUrl

      // For text-based files, also read the content as text
      if (['text', 'json', 'code'].includes(currentFileType)) {
        try {
          const text = await blob.text()
          textContent.value = text
        } catch (err) {
          console.error('Error reading text content:', err)
          textContent.value = 'Error reading file content'
        }
      }
    }
  } catch (err: any) {
    console.error('Error loading file:', err)
    error.value = err.response?.data?.detail || 'Failed to load file'
  } finally {
    loading.value = false
  }
}

const downloadFile = async () => {
  if (!file.value) return

  try {
    downloading.value = true
    await filesAPI.download(file.value.id, { download: 'true' }) // Force download
  } catch (err: any) {
    console.error('Download error:', err)
    ElMessage.error('Download failed')
  } finally {
    downloading.value = false
  }
}

const handleContentUpdated = (newContent: string) => {
  // Update the local content when file is edited
  textContent.value = newContent
  ElMessage.success('File content updated')
}

const retry = () => {
  loadFile()
}

const getFileType = () => {
  if (!file.value) return 'Unknown'

  const mimeType = file.value.storage?.mime_type
  if (mimeType) {
    return mimeType
  }

  const extension = file.value.storage?.extension
  if (extension) {
    return extension.toUpperCase()
  }

  const fileName = file.value.name
  const lastDot = fileName.lastIndexOf('.')
  if (lastDot > 0) {
    return fileName.substring(lastDot + 1).toUpperCase()
  }

  return 'Unknown'
}

const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 Bytes'

  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// Event handlers
const handleDocumentReady = () => {
  ElMessage.success('Document editor ready')
}

const handleDocumentSaved = (document: any) => {
  ElMessage.success('Document saved successfully')
}

const handleDocumentError = (error: string) => {
  ElMessage.error(`Document error: ${error}`)
}

// Lifecycle
onMounted(() => {
  loadFile()
})

onUnmounted(() => {
  // Clean up object URL
  if (fileContent.value) {
    URL.revokeObjectURL(fileContent.value)
  }
  // Clear text content
  textContent.value = null
})
</script>

<style scoped>
.file-viewer {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
  overflow: hidden;
}

.loading-container,
.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  gap: 16px;
}

.loading-container .el-icon {
  color: #409eff;
}

.error-container h3 {
  margin: 0;
  color: #f56c6c;
}

.file-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.file-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: white;
  border-bottom: 1px solid #ebeef5;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  flex-shrink: 0; /* Prevent header from shrinking */
}

.file-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.file-name {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.file-actions {
  display: flex;
  gap: 12px;
}

.file-display {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  min-height: 0;
}

/* Reader components will handle their own styling */
</style>
