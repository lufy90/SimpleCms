<template>
  <div class="office-document-viewer">
    <!-- Always render the editor container, but conditionally show content -->
    <div
      ref="documentEditorRef"
      id="documentEditor"
      class="document-editor"
      :style="{ height: editorHeight }"
    >
      <div v-if="loading" class="loading-container">
        <el-icon class="is-loading">
          <Loading />
        </el-icon>
        <span>Loading document editor...</span>
      </div>

      <div v-else-if="error" class="error-container">
        <el-alert :title="error" type="error" :closable="false" show-icon />
        <el-button @click="retry" type="primary" style="margin-top: 16px"> Retry </el-button>
      </div>

      <div v-else class="document-container">
        <div class="document-header">
          <div class="document-info">
            <h3>{{ file?.name }}</h3>
            <span class="document-type">{{ getDocumentType() }}</span>
          </div>
          <div class="document-actions">
            <el-button @click="downloadDocument" type="primary" size="small">
              <el-icon><Download /></el-icon>
              Download
            </el-button>
            <el-button @click="refreshDocument" size="small">
              <el-icon><Refresh /></el-icon>
              Refresh
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading, Download, Refresh } from '@element-plus/icons-vue'
import { filesAPI } from '@/services/api'
import api from '@/services/api'
import { useOfficeConfig } from '@/services/officeConfig'
import { tokenStorage } from '@/utils/storage'
import { electronUtils } from '@/utils/electron'

interface Props {
  file: any
  mode?: 'view' | 'edit'
  height?: string
}

const props = withDefaults(defineProps<Props>(), {
  mode: 'edit',
  height: '600px',
})

const emit = defineEmits<{
  documentReady: []
  documentSaved: [document: any]
  error: [error: string]
}>()

// Refs
const documentEditorRef = ref<HTMLElement>()
const loading = ref(true)
const error = ref<string | null>(null)
const documentEditor = ref<any>(null)
const isInitialized = ref(false)
const iframeHeight = ref('600px')

// Services
const officeConfig = useOfficeConfig()

// Computed
const editorHeight = computed(() => props.height)

// Methods
const getDocumentType = () => {
  if (!props.file) return 'Document'

  const extension =
    props.file.extension ||
    props.file.file_info?.extension ||
    props.file.name.split('.').pop()?.toLowerCase() ||
    ''

  const typeMap: Record<string, string> = {
    docx: 'Word Document',
    doc: 'Word Document',
    xlsx: 'Excel Spreadsheet',
    xls: 'Excel Spreadsheet',
    pptx: 'PowerPoint Presentation',
    ppt: 'PowerPoint Presentation',
    odt: 'OpenDocument Text',
    ods: 'OpenDocument Spreadsheet',
    odp: 'OpenDocument Presentation',
    rtf: 'Rich Text Document',
    txt: 'Text Document',
  }

  return typeMap[extension] || 'Office Document'
}

const getOfficeConfig = async () => {
  try {
    const response = await api.get(`/api/office/config/${props.file.id}/`)
    return response.data
  } catch (err) {
    throw new Error('Failed to get office configuration')
  }
}

const initializeDocumentEditor = async () => {
  if (!documentEditorRef.value || !props.file || isInitialized.value) {
    return
  }

  try {
    loading.value = true
    error.value = null

    // Ensure OnlyOffice settings are loaded
    await officeConfig.ensureSettingsLoaded()

    // Check if OnlyOffice is available
    if (!officeConfig.isOnlyOfficeAvailable.value) {
      throw new Error(
        'OnlyOffice document editor is not available. Please use the regular file viewer instead.',
      )
    }

    // Get configuration from backend (includes JWT token)
    const officeResponse = await getOfficeConfig()

    if (!officeResponse.config) {
      throw new Error('Invalid configuration received from backend')
    }

    const config = officeResponse.config
    const token = officeResponse.token

    // Initialize OnlyOffice Document Editor
    if ((window as any).DocsAPI) {
      // Double-check that the ref is still available
      if (!documentEditorRef.value) {
        throw new Error('Document editor container not available')
      }

      // Add token to config if available
      if (token) {
        config.token = token
      }

      const editorId = documentEditorRef.value.id || 'documentEditor'

      documentEditor.value = new (window as any).DocsAPI.DocEditor(editorId, config)

      isInitialized.value = true

      // Wait for document to be ready
      setTimeout(() => {
        loading.value = false
        emit('documentReady')

        // Update iframe height after OnlyOffice is fully loaded and stable
        setTimeout(() => {
          updateIframeHeight()
        }, 2000) // Wait longer for OnlyOffice to be stable
      }, 1000)
    } else {
      throw new Error('OnlyOffice Document Editor not loaded')
    }
  } catch (err: any) {
    error.value = err.message || 'Failed to load document editor'
    loading.value = false
    emit('error', error.value || 'Unknown error')
  }
}

const downloadDocument = async () => {
  try {
    // Use Electron utility for download
    await electronUtils.downloadFile(props.file.id, props.file.name, true)
    ElMessage.success('Document download started')
  } catch (err: any) {
    ElMessage.error('Failed to download document')
  }
}

const refreshDocument = () => {
  if (documentEditor.value) {
    documentEditor.value.refresh()
  }
}

const updateIframeHeight = () => {
  if (documentEditorRef.value) {
    const containerHeight = documentEditorRef.value.offsetHeight
    // Only update if we have a valid height and it's reasonable
    if (containerHeight > 100 && containerHeight < 2000) {
      iframeHeight.value = `${containerHeight}px`
    }
  }
}

const retry = () => {
  initializeDocumentEditor()
}

const cleanup = () => {
  if (documentEditor.value) {
    try {
      documentEditor.value.destroyEditor()
    } catch (err) {
      console.warn('Error destroying document editor:', err)
    }
    documentEditor.value = null
  }
  isInitialized.value = false
}

// Watch for file changes
watch(
  () => props.file,
  () => {
    if (props.file) {
      cleanup()
      // Don't initialize immediately - let the loading watcher handle it
      loading.value = true
    }
  },
  { immediate: true },
)

// Watch for loading state changes to initialize editor when DOM is ready
watch(
  () => loading.value,
  async (newLoading, oldLoading) => {
    // Only initialize when loading changes from true to false, and only once
    if (
      oldLoading === true &&
      newLoading === false &&
      !error.value &&
      props.file &&
      (window as any).DocsAPI
    ) {
      // Wait for DOM to be ready
      await nextTick()

      // The ref should always be available now since it's always rendered
      if (documentEditorRef.value) {
        initializeDocumentEditor()
      } else {
        error.value = 'Document editor container not available'
      }
    }
  },
)

// Watch for container height changes and update iframe height
watch(
  () => documentEditorRef.value?.offsetHeight,
  (newHeight, oldHeight) => {
    if (newHeight && newHeight > 0 && newHeight !== oldHeight) {
      // Only update if the height change is significant (more than 50px difference)
      const heightDiff = Math.abs(newHeight - (oldHeight || 0))
      if (heightDiff > 50) {
        iframeHeight.value = `${newHeight}px`
      }
    }
  },
)

// Lifecycle
onMounted(() => {
  // Load OnlyOffice script if not already loaded
  if (!(window as any).DocsAPI) {
    const script = document.createElement('script')
    script.src = `${officeConfig.documentServerUrl.value}/web-apps/apps/api/documents/api.js`

    // Add timeout to prevent infinite loading
    const timeout = setTimeout(() => {
      error.value =
        'OnlyOffice Document Editor loading timeout. Please check your network connection and proxy settings.'
      loading.value = false
    }, 10000) // 10 second timeout

    script.onload = () => {
      clearTimeout(timeout)
      loading.value = false
    }

    script.onerror = (err) => {
      clearTimeout(timeout)
      error.value =
        'Failed to load OnlyOffice Document Editor. Please check if the document server is accessible.'
      loading.value = false
    }

    document.head.appendChild(script)
  } else {
    loading.value = false
  }
})

onUnmounted(() => {
  cleanup()
})
</script>

<style scoped>
.office-document-viewer {
  width: 100%;
  height: 900px;
  display: flex;
  flex-direction: column;
}

.loading-container .el-icon {
  font-size: 32px;
}

.document-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: #f8f9fa;
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;
}

.document-info h3 {
  margin: 0 0 4px 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.document-type {
  font-size: 14px;
  color: #606266;
}

.document-actions {
  display: flex;
  gap: 8px;
}

.document-editor {
  flex: 1;
  width: 100%;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}

.loading-container,
.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 40px;
}

.document-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* Dark mode styles */
.dark .document-header {
  background: #2a2a2a;
  border-bottom-color: #3c3c3c;
}

.dark .document-info h3 {
  color: #e5e5e5;
}

.dark .document-type {
  color: #a8a8a8;
}

.dark .document-editor {
  border-color: #3c3c3c;
}

:deep(iframe) {
  width: 100% !important;
  height: v-bind(iframeHeight) !important;
  min-height: 600px !important;
  border: none !important;
}

/* Responsive design */
@media (max-width: 768px) {
  .document-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .document-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
