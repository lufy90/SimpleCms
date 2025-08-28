<template>
  <div class="files-view">
    <div class="page-header">
      <div class="header-left">
        <h1>{{ currentDirectory ? currentDirectory.name : 'Files' }}</h1>
      </div>
      <div class="header-actions">
        <!-- File input for multiple files -->
        <input
          ref="fileInputRef"
          type="file"
          multiple
          style="display: none"
          @change="handleFileSelection"
        />
        <!-- Directory input for directory structure -->
        <input
          ref="dirInputRef"
          type="file"
          webkitdirectory
          style="display: none"
          @change="handleDirectorySelection"
        />
        <el-dropdown @command="handleUploadCommand" trigger="click">
          <el-button type="primary">
            <el-icon><Upload /></el-icon>
            Upload
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="files">
                <el-icon><Document /></el-icon>
                Multiple Files
              </el-dropdown-item>
              <el-dropdown-item command="directory">
                <el-icon><Folder /></el-icon>
                Directory Structure
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button type="success" @click="showCreateDirectoryDialog">
          <el-icon><FolderAdd /></el-icon>
          New Folder
        </el-button>
        <el-button @click="refreshFiles">
          <el-icon><Refresh /></el-icon>
          Refresh
        </el-button>
        <el-button 
          v-if="currentDirectory" 
          @click="navigateToRoot"
          type="info"
        >
          <el-icon><Back /></el-icon>
          Back to Root
        </el-button>
      </div>
    </div>

    <!-- View Type Toggle -->
    <div class="view-controls">
      <el-button-group>
        <el-button
          :type="viewType === 'grid' ? 'primary' : 'default'"
          @click="setViewType('grid')"
        >
          <el-icon><Grid /></el-icon>
          Grid
        </el-button>
        <el-button
          :type="viewType === 'list' ? 'primary' : 'default'"
          @click="setViewType('list')"
        >
          <el-icon><List /></el-icon>
          List
        </el-button>
      </el-button-group>
    </div>

    <!-- Bulk Operations Toolbar -->
    <div v-if="selectedFileIds.size > 0" class="bulk-operations-toolbar">
      <div class="bulk-info">
        <span>{{ selectedFileIds.size }} item(s) selected</span>
      </div>
      <div class="bulk-actions">
        <el-button @click="showCopyDialog" type="primary" size="small">
          <el-icon><CopyDocument /></el-icon>
          Copy
        </el-button>
        <el-button @click="showMoveDialog" type="warning" size="small">
          <el-icon><Position /></el-icon>
          Move
        </el-button>
        <el-button @click="confirmDelete" type="danger" size="small">
          <el-icon><Delete /></el-icon>
          Delete
        </el-button>
        <el-button @click="clearSelection" size="small">
          <el-icon><Close /></el-icon>
          Clear
        </el-button>
      </div>
    </div>

    <!-- Breadcrumb Navigation -->
    <div class="breadcrumb-container">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item @click="handleBreadcrumbClick({ id: null, name: 'root', path: '/' })">
          root
        </el-breadcrumb-item>
        <el-breadcrumb-item 
          v-for="(item, index) in breadcrumbPath.filter(item => item.id !== null)" 
          :key="index"
          @click="handleBreadcrumbClick(item)"
        >
          {{ item.name }}
        </el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <!-- Search and Filters -->
    <div class="search-bar">
      <el-input
        v-model="searchQuery"
        placeholder="Search files..."
        prefix-icon="Search"
        clearable
        @input="handleSearch"
        style="width: 300px"
      />
    </div>

    <!-- File List -->
    <div class="file-content">
      <el-empty
        v-if="filteredFiles.length === 0 && !isLoading"
        description="No files found"
      >
        <el-button type="primary" @click="openUpload">
          Upload Files
        </el-button>
      </el-empty>

      <!-- Grid View -->
      <div v-else-if="viewType === 'grid'" class="grid-view">
        <div
          v-for="file in filteredFiles"
          :key="file.id"
          class="file-card"
        >
          <div class="file-selection">
            <el-checkbox
              :model-value="selectedFileIds.has(file.id)"
              @change="(checked: boolean) => toggleFileSelection(file.id, checked)"
              @click.stop
            />
          </div>
          <div class="file-content" @click="handleFileClick(file)">
            <div class="file-icon">
              <el-icon size="32" :color="getFileIconColor(file)">
                <Folder v-if="file.item_type === 'directory'" />
                <Document v-else />
              </el-icon>
            </div>
            <div class="file-name">{{ file.name }}</div>
            <div class="file-meta">
              <span v-if="file.size">{{ formatFileSize(file.size) }}</span>
              <span>{{ file.item_type }}</span>
            </div>
          </div>
          <div class="file-actions">
            <el-dropdown @command="(command: string) => handleFileAction(command, file)" trigger="click">
              <el-button type="text" size="small" @click.stop>
                <el-icon><More /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="copy">
                    <el-icon><CopyDocument /></el-icon>
                    Copy
                  </el-dropdown-item>
                  <el-dropdown-item command="move">
                    <el-icon><Position /></el-icon>
                    Move
                  </el-dropdown-item>
                  <el-dropdown-item command="delete" divided>
                    <el-icon><Delete /></el-icon>
                    Delete
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>

      <!-- List View -->
      <el-table
        v-else
        :data="filteredFiles"
        @row-click="handleListRowClick"
        class="list-view"
        @selection-change="handleListSelectionChange"
        ref="listTableRef"
      >
        <!-- Selection Column -->
        <el-table-column type="selection" width="55" />
        
        <el-table-column prop="name" label="Name" min-width="200">
          <template #default="{ row }">
            <div class="file-name-cell">
              <el-icon :color="getFileIconColor(row)">
                <Folder v-if="row.item_type === 'directory'" />
                <Document v-else />
              </el-icon>
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="size" label="Size" width="120">
          <template #default="{ row }">
            <span v-if="row.size">{{ formatFileSize(row.size) }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="item_type" label="Type" width="100" />
        <el-table-column prop="visibility" label="Visibility" width="120">
          <template #default="{ row }">
            <el-tag :type="getVisibilityTagType(row.visibility)" size="small">
              {{ row.visibility }}
            </el-tag>
          </template>
        </el-table-column>
        
        <!-- Actions Column -->
        <el-table-column label="Actions" width="280" fixed="right">
          <template #default="{ row }">
            <div class="list-actions">
              <el-button 
                type="primary" 
                size="small" 
                @click.stop="handleFileAction('copy', row)"
                title="Copy"
              >
                <el-icon><CopyDocument /></el-icon>
                Copy
              </el-button>
              <el-button 
                type="warning" 
                size="small" 
                @click.stop="handleFileAction('move', row)"
                title="Move"
              >
                <el-icon><Position /></el-icon>
                Move
              </el-button>
              <el-button 
                type="danger" 
                size="small" 
                @click.stop="handleFileAction('delete', row)"
                title="Delete"
              >
                <el-icon><Delete /></el-icon>
                Delete
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>



    <!-- Upload Dialog -->
    <el-dialog
      v-model="uploadDialogVisible"
      title="Upload Files"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form :model="uploadForm" label-width="120px">
        <el-form-item label="Visibility">
          <el-select v-model="uploadForm.visibility" placeholder="Select visibility">
            <el-option label="Private" value="private" />
            <el-option label="User Shared" value="user" />
            <el-option label="Group Shared" value="group" />
            <el-option label="Public" value="public" />
          </el-select>
        </el-form-item>

        <!-- File Upload Section -->
        <el-form-item label="Files">
          <el-upload
            ref="uploadRef"
            :action="uploadAction"
            :headers="uploadHeaders"
            :data="uploadData"
            :on-success="handleUploadSuccess"
            :on-error="handleUploadError"
            :before-upload="beforeUpload"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            :on-progress="handleUploadProgress"
            :on-exceed="handleFileExceed"
            :limit="20"
            multiple
            drag
            class="upload-area"
            :auto-upload="false"
            :show-file-list="true"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              Drop files here or <em>click to upload</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                Support for multiple files. Drag and drop or click to select.
                <div v-if="selectedFiles.length > 0" style="margin-top: 8px; color: #409eff; font-weight: 500;">
                  {{ selectedFiles.length }} file(s) selected
                </div>
              </div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="closeUploadDialog">Cancel</el-button>
          <el-button 
            type="primary" 
            @click="handleUpload" 
            :loading="isUploading"
            :disabled="!hasFilesToUpload"
          >
            Upload Files {{ selectedFiles.length > 0 ? `(${selectedFiles.length})` : '' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>

  <!-- Upload Progress Display -->
  <div v-if="uploadProgress.length > 0" class="upload-progress-overlay">
    <div class="upload-progress-panel">
      <div class="progress-header">
        <h3>Upload Progress</h3>
        <el-button 
          v-if="!isUploading" 
          @click="uploadProgress = []" 
          size="small" 
          type="text"
        >
          Close
        </el-button>
      </div>
      <div class="progress-list">
        <div 
          v-for="(progress, index) in uploadProgress" 
          :key="index" 
          class="progress-item"
        >
          <div class="progress-item-header">
            <span class="filename">{{ progress.filename }}</span>
            <span class="status" :class="progress.status">{{ progress.status }}</span>
          </div>
          <el-progress 
            v-if="progress.status === 'uploading'" 
            :percentage="progress.percentage" 
            :status="progress.error ? 'exception' : undefined"
            :stroke-width="4"
          />
          <div v-if="progress.error" class="error-message">
            {{ progress.error }}
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Copy Dialog -->
  <el-dialog
    v-model="copyDialogVisible"
    title="Copy Files"
    width="600px"
    :close-on-click-modal="false"
  >
    <el-form>
      <el-form-item label="Destination Directory">
        <el-tree
          ref="copyTreeRef"
          :data="directoryTreeData"
          :props="treeProps"
          :expand-on-click-node="false"
          :highlight-current="true"
          @node-click="handleDirectorySelect"
          style="max-height: 300px; overflow-y: auto; border: 1px solid #dcdfe6; border-radius: 4px; padding: 8px;"
        >
          <template #default="{ node, data }">
            <span class="custom-tree-node">
              <el-icon><Folder /></el-icon>
              <span style="margin-left: 8px;">{{ node.label }}</span>
              <span v-if="data.path" style="margin-left: 8px; color: #909399; font-size: 12px;">
                ({{ data.path }})
              </span>
            </span>
          </template>
        </el-tree>
        <div v-if="operationDestination" style="margin-top: 12px; padding: 8px; background-color: #f0f9ff; border-radius: 4px; border: 1px solid #bae6fd;">
          <strong>Selected:</strong> {{ getSelectedDirectoryName() }}
        </div>
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="copyDialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="executeOperation" :disabled="operationDestination === undefined">Copy Files</el-button>
      </div>
    </template>
  </el-dialog>

  <!-- Move Dialog -->
  <el-dialog
    v-model="moveDialogVisible"
    title="Move Files"
    width="600px"
    :close-on-click-modal="false"
  >
    <el-form>
      <el-form-item label="Destination Directory">
        <el-tree
          ref="moveTreeRef"
          :data="directoryTreeData"
          :props="treeProps"
          :expand-on-click-node="false"
          :highlight-current="true"
          @node-click="handleDirectorySelect"
          style="max-height: 300px; overflow-y: auto; border: 1px solid #dcdfe6; border-radius: 4px; padding: 8px;"
        >
          <template #default="{ node, data }">
            <span class="custom-tree-node">
              <el-icon><Folder /></el-icon>
              <span style="margin-left: 8px;">{{ node.label }}</span>
              <span v-if="data.path" style="margin-left: 8px; color: #909399; font-size: 12px;">
                ({{ data.path }})
              </span>
            </span>
          </template>
        </el-tree>
        <div v-if="operationDestination !== undefined" style="margin-top: 12px; padding: 8px; background-color: #fff7ed; border-radius: 4px; border: 1px solid #fed7aa;">
          <strong>Selected:</strong> {{ getSelectedDirectoryName() }}
        </div>
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="moveDialogVisible = false">Cancel</el-button>
        <el-button type="warning" @click="executeOperation" :disabled="operationDestination === undefined">Move Files</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useFilesStore } from '@/stores/files'
import { uploadAPI } from '@/services/api'
import { Grid, List, Document, Folder, Upload, Refresh, Back, UploadFilled, ArrowDown, CopyDocument, Position, Delete, Close, More } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const filesStore = useFilesStore()
const authStore = useAuthStore()

// State
const viewType = ref<'grid' | 'list'>('grid')
const searchQuery = ref('')
const uploadDialogVisible = ref(false)
const uploadForm = ref({
  visibility: 'private',
})
const fileInputRef = ref<HTMLInputElement>()
const dirInputRef = ref<HTMLInputElement>()
const uploadRef = ref()
const selectedFiles = ref<Array<File>>([])
const selectedFileIds = ref<Set<number>>(new Set())
const uploadProgress = ref<Array<{ filename: string; status: 'uploading' | 'success' | 'error'; percentage: number; error?: string }>>([])
const isUploading = ref(false)

// Operation dialogs
const copyDialogVisible = ref(false)
const moveDialogVisible = ref(false)
const operationDestination = ref<number | undefined>(undefined)
const operationType = ref<'copy' | 'move'>('copy')

// Tree selector configuration
const treeProps = {
  children: 'children',
  label: 'name'
}

// Directory tree data for copy/move operations
const directoryTreeData = computed(() => {
  return filesStore.directoryTree.filter(item => item.item_type === 'directory')
})

// Tree refs
const copyTreeRef = ref()
const moveTreeRef = ref()
const listTableRef = ref()

// Upload configuration
const uploadAction = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8002'}/api/upload/`
const uploadHeaders = computed(() => {
  const token = document.cookie.split('; ').find(row => row.startsWith('access_token='))?.split('=')[1]
  return {
    Authorization: `Bearer ${token}`
  }
})
const uploadData = computed(() => ({
  parent_id: currentDirectory.value?.id,
  visibility: uploadForm.value.visibility
}))

// Computed
const files = computed(() => filesStore.files)
const filteredFiles = computed(() => filesStore.filteredFiles)
const isLoading = computed(() => filesStore.isLoading)
const pagination = computed(() => filesStore.pagination)
const currentDirectory = computed(() => filesStore.currentDirectory)

// Computed for upload functionality
const hasFilesToUpload = computed(() => {
  return selectedFiles.value.length > 0
})

// Directory upload functionality removed - now handled by file upload with relative paths

// Breadcrumb state - maintains the full navigation path
const breadcrumbPath = ref<Array<{id: number | null, name: string, path: string}>>([
  { id: null, name: 'root', path: '/' }
])

// Update breadcrumb when directory changes
const updateBreadcrumb = async () => {
  console.log('updateBreadcrumb called, currentDirectory:', currentDirectory.value)
  
  if (!currentDirectory.value) {
    console.log('No current directory, setting root breadcrumb')
    breadcrumbPath.value = [{ id: null, name: 'root', path: '/' }]
    return
  }
  
  // Debug: Log the complete current directory object
  console.log('Current directory full object:', JSON.stringify(currentDirectory.value, null, 2))
  console.log('Parents attribute:', currentDirectory.value.parents)
  console.log('Parents type:', typeof currentDirectory.value.parents)
  console.log('Parents is array:', Array.isArray(currentDirectory.value.parents))
  
  // Build breadcrumb using the parents attribute from the API
  const newBreadcrumb = []
  
  // Always start with root
  newBreadcrumb.push({
    id: null,
    name: 'root',
    path: '/'
  })
  
  // Add all parent directories from the parents array (if available)
  if (currentDirectory.value.parents && Array.isArray(currentDirectory.value.parents) && currentDirectory.value.parents.length > 0) {
    console.log('Adding parents from API:', currentDirectory.value.parents)
    
    currentDirectory.value.parents.forEach(parent => {
      newBreadcrumb.push({
        id: parent.id,
        name: parent.name,
        path: parent.relative_path
      })
    })
  } else {
    console.log('No parents attribute available, breadcrumb will only show root and current directory')
  }
  
  // Add current directory at the end
  newBreadcrumb.push({
    id: currentDirectory.value.id,
    name: currentDirectory.value.name,
    path: currentDirectory.value.path
  })
  
  console.log('Built complete breadcrumb:', newBreadcrumb)
  breadcrumbPath.value = newBreadcrumb
}

// Watch for directory changes to update breadcrumb
watch(currentDirectory, (newDir, oldDir) => {
  console.log('currentDirectory changed:', { old: oldDir, new: newDir })
  updateBreadcrumb()
}, { immediate: true })

// Watch for selected files changes
watch(selectedFiles, (newFiles, oldFiles) => {
  console.log('selectedFiles changed:', { 
    old: oldFiles?.length || 0, 
    new: newFiles?.length || 0,
    files: newFiles?.map(f => f.name) || []
  })
}, { deep: true })

// Methods
const setViewType = (type: 'grid' | 'list') => {
  viewType.value = type
}

const triggerFileSelection = () => {
  fileInputRef.value?.click()
}

const triggerDirectorySelection = () => {
  dirInputRef.value?.click()
}

const handleUploadCommand = (command: string) => {
  if (command === 'files') {
    triggerFileSelection()
  } else if (command === 'directory') {
    triggerDirectorySelection()
  }
}

const handleFileSelection = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const files = Array.from(target.files || [])
  
  if (files.length === 0) return
  
  // Reset progress
  uploadProgress.value = []
  isUploading.value = true
  
  try {
    // Process files and create directory structure
    await processAndUploadFiles(files)
  } catch (error: any) {
    ElMessage.error(`Upload failed: ${error.message || error}`)
  } finally {
    isUploading.value = false
    // Reset file input
    if (target) target.value = ''
  }
}

const handleDirectorySelection = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const files = Array.from(target.files || [])
  
  if (files.length === 0) return
  
  // Reset progress
  uploadProgress.value = []
  isUploading.value = true
  
  try {
    // Process directory files with relative paths
    await processAndUploadFiles(files)
  } catch (error: any) {
    ElMessage.error(`Upload failed: ${error.message || error}`)
  } finally {
    isUploading.value = false
    // Reset directory input
    if (target) target.value = ''
  }
}

const processAndUploadFiles = async (files: File[]) => {
  // Upload all files with their relative paths
  await uploadAllFiles(files)
  
  // Refresh file list
  await refreshFiles()
  ElMessage.success(`Upload completed: ${files.length} files processed`)
}

// Directory creation now handled by backend during file upload

const uploadAllFiles = async (files: File[]) => {
  const batchSize = 3
  let uploadedCount = 0
  let failedCount = 0
  
  // Initialize progress for all files
  files.forEach(file => {
    uploadProgress.value.push({
      filename: file.webkitRelativePath,
      status: 'uploading',
      percentage: 0
    })
  })
  
  for (let i = 0; i < files.length; i += batchSize) {
    const batch = files.slice(i, i + batchSize)
    
    const batchPromises = batch.map(async (file, batchIndex) => {
      const globalIndex = i + batchIndex
      try {
        // Get the relative path for this file
        const pathParts = file.webkitRelativePath.split('/')
        const fileName = pathParts.pop()! // Remove filename
        const relativePath = pathParts.join('/') // Keep directory path
        
        // Create FormData for upload
        const formData = new FormData()
        formData.append('file', file)
        formData.append('visibility', uploadForm.value.visibility)
        if (currentDirectory.value?.id) {
          formData.append('parent_id', currentDirectory.value.id.toString())
        }
        if (relativePath) {
          formData.append('relative_path', relativePath)
        }
        
        // Upload the file - backend will handle directory creation
        await uploadAPI.upload(formData)
        
        // Update progress
        uploadProgress.value[globalIndex].status = 'success'
        uploadProgress.value[globalIndex].percentage = 100
        uploadedCount++
        
        return true
      } catch (error: any) {
        // Update progress with error
        uploadProgress.value[globalIndex].status = 'error'
        uploadProgress.value[globalIndex].error = error.response?.data?.error || error.message || 'Upload failed'
        failedCount++
        return false
      }
    })
    
    // Wait for batch to complete
    await Promise.all(batchPromises)
    
    // Small delay between batches
    if (i + batchSize < files.length) {
      await new Promise(resolve => setTimeout(resolve, 500))
      }
    }
  
  // Show final results
  if (failedCount === 0) {
    ElMessage.success(`All ${files.length} files uploaded successfully!`)
  } else {
    ElMessage.warning(`${uploadedCount} files uploaded, ${failedCount} failed.`)
  }
}

// Directory lookup methods removed - no longer needed with simplified backend approach

const openUpload = () => {
  uploadDialogVisible.value = true
  // Reset selected files when opening upload dialog
  selectedFiles.value = []
}

const closeUploadDialog = () => {
  uploadDialogVisible.value = false
  // Reset selected files when closing upload dialog
  selectedFiles.value = []
  // Reset upload progress
  uploadProgress.value = []
}

const showCreateDirectoryDialog = () => {
  ElMessageBox.prompt('Enter folder name:', 'Create New Folder', {
    confirmButtonText: 'Create',
    cancelButtonText: 'Cancel',
    inputPattern: /^[^\/\\]+$/,
    inputErrorMessage: 'Folder name cannot contain slashes or backslashes'
  }).then(async ({ value }) => {
    if (value) {
      // Create directory within current directory
      const parentId = currentDirectory.value?.id
      const newDirectory = await filesStore.createDirectory(value, parentId)
      if (newDirectory) {
        ElMessage.success('Folder created successfully')
        // Refresh the current directory contents
        await refreshFiles()
      }
    }
  }).catch(() => {
    // User cancelled
  })
}

// Upload methods
const handleUpload = () => {
  if (uploadRef.value) {
    // Get the file list from the upload component
    const fileList = uploadRef.value.uploadFiles || []
    
    if (fileList.length === 0) {
      ElMessage.warning('Please select files to upload.')
      return
    }
    
    // Submit all files
    uploadRef.value.submit()
  }
}

const handleUploadSuccess = (response: any, file: any) => {
  ElMessage.success(`${file.name} uploaded successfully`)
  // Refresh the file list to show the new file
  refreshFiles()
}

const handleUploadComplete = () => {
  // Clear selected files after all uploads are complete
  selectedFiles.value = []
}

const handleUploadError = (error: any, file: any) => {
  ElMessage.error(`${file.name} upload failed: ${error.message || 'Unknown error'}`)
}

const beforeUpload = (file: any) => {
  return true
}

const handleFileChange = (file: any, fileList: any) => {
  console.log('File changed:', file, 'File list:', fileList)
  // Update the selected files array
  selectedFiles.value = fileList.map((f: any) => f.raw || f)
}

const handleFileRemove = (file: any, fileList: any) => {
  console.log('File removed:', file, 'File list:', fileList)
  // Update the selected files array
  selectedFiles.value = fileList.map((f: any) => f.raw || f)
}

const handleUploadProgress = (event: any, file: any) => {
  console.log(`Upload progress for ${file.name}:`, event.percent)
  // You can add progress tracking logic here if needed
}

const handleFileExceed = (files: any, fileList: any) => {
  ElMessage.warning(`Maximum ${fileList.length} files allowed. Please remove some files first.`)
}

// Directory selection method removed - now handled by file input with webkitdirectory

// Directory scanning method removed - no longer needed

// Directory upload method removed - now handled by file upload with relative paths

// handleBulkFileUpload method removed - no longer needed with simplified upload approach

// Directory handle methods removed - no longer needed

const refreshFiles = async () => {
  if (currentDirectory.value) {
    await filesStore.fetchChildren(currentDirectory.value.id)
  } else {
    await filesStore.fetchChildren()
  }
  // Don't update breadcrumb here - let the navigation methods handle it
}

const handleSearch = (value: string) => {
  searchQuery.value = value
}

const handleFileClick = async (file: any) => {
  if (file.item_type === 'directory') {
    // Navigate to directory using the new API
    await navigateToDirectory(file.id)
  } else {
    // Open file details
    router.push({ name: 'FileDetails', params: { id: file.id } })
  }
}

const handleListRowClick = (row: any, column: any, event: Event) => {
  // Don't navigate if clicking on selection checkbox or actions column
  if (column.type === 'selection' || column.label === 'Actions') {
    return
  }
  handleFileClick(row)
}

const navigateToDirectory = async (directoryId: number) => {
  console.log('navigateToDirectory called with ID:', directoryId)
  await filesStore.fetchChildren(directoryId)
  console.log('After fetchChildren, currentDirectory:', currentDirectory.value)
  // Update breadcrumb with complete parent hierarchy from API
  await updateBreadcrumb()
}

const navigateToRoot = async () => {
  console.log('navigateToRoot called')
  console.log('Before fetchChildren, currentDirectory:', currentDirectory.value)
  await filesStore.fetchChildren()
  console.log('After fetchChildren, currentDirectory:', currentDirectory.value)
  // Reset breadcrumb to root only
  breadcrumbPath.value = [{ id: null, name: 'root', path: '/' }]
  console.log('Breadcrumb reset to root:', breadcrumbPath.value)
}

const handleBreadcrumbClick = async (item: { id: number | null, name: string, path: string }) => {
  if (item.id === null) {
    // Clicked on root
    await navigateToRoot()
  } else {
    // Clicked on a directory in the breadcrumb
    console.log('Navigating to breadcrumb directory:', item)
    
    // Navigate to this directory - the breadcrumb will be rebuilt automatically
    await navigateToDirectory(item.id)
  }
}



// File operation methods
const toggleFileSelection = (fileId: number, checked: boolean) => {
  if (checked) {
    selectedFileIds.value.add(fileId)
  } else {
    selectedFileIds.value.delete(fileId)
  }
}

const clearSelection = () => {
  selectedFileIds.value.clear()
  // Clear table selection if list view is active
  if (viewType.value === 'list' && listTableRef.value) {
    listTableRef.value.clearSelection()
  }
}

const showCopyDialog = () => {
  operationType.value = 'copy'
  operationDestination.value = undefined
  copyDialogVisible.value = true
}

const showMoveDialog = () => {
  operationType.value = 'move'
  operationDestination.value = undefined
  moveDialogVisible.value = true
}

const confirmDelete = async () => {
  try {
    await ElMessageBox.confirm(
      `Are you sure you want to delete ${selectedFileIds.value.size} item(s)? This action cannot be undone.`,
      'Confirm Delete',
      {
        confirmButtonText: 'Delete',
        cancelButtonText: 'Cancel',
        type: 'warning',
      }
    )
    
    const fileIds = Array.from(selectedFileIds.value)
    await filesStore.deleteFiles(fileIds)
    clearSelection()
  } catch (error) {
    // User cancelled
  }
}

const handleFileAction = async (command: string, file: any) => {
  if (command === 'copy') {
    selectedFileIds.value.clear()
    selectedFileIds.value.add(file.id)
    showCopyDialog()
  } else if (command === 'move') {
    selectedFileIds.value.clear()
    selectedFileIds.value.add(file.id)
    showMoveDialog()
  } else if (command === 'delete') {
    selectedFileIds.value.clear()
    selectedFileIds.value.add(file.id)
    await confirmDelete()
  }
}

const handleListSelectionChange = (selection: any[]) => {
  // Update selectedFileIds based on table selection
  selectedFileIds.value.clear()
  selection.forEach(item => {
    selectedFileIds.value.add(item.id)
  })
}

const executeOperation = async () => {
  if (operationDestination.value === undefined) {
    ElMessage.warning('Please select a destination directory')
    return
  }
  
  try {
    const fileIds = Array.from(selectedFileIds.value)
    
    if (operationType.value === 'copy') {
      await filesStore.copyFiles(fileIds, operationDestination.value)
      copyDialogVisible.value = false
    } else if (operationType.value === 'move') {
      await filesStore.moveFiles(fileIds, operationDestination.value)
      moveDialogVisible.value = false
    }
    
    operationDestination.value = undefined
    clearSelection()
  } catch (error: any) {
    ElMessage.error(`Operation failed: ${error.message || error}`)
  }
}

const handleDirectorySelect = (data: any) => {
  // Handle root directory specially - root has id 'root' but we use 0 for root
  if (data.id === 'root') {
    operationDestination.value = 0  // Use 0 as special ID for root directory
  } else {
    operationDestination.value = data.id
  }
}

const getSelectedDirectoryName = () => {
  if (operationDestination.value === undefined) return ''
  if (operationDestination.value === 0) return 'Root Directory (/)'
  const selectedDir = directoryTreeData.value.find(dir => dir.id === operationDestination.value)
  return selectedDir ? selectedDir.name : ''
}

// Utility methods
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const getFileIconColor = (file: any): string => {
  if (file.item_type === 'directory') return '#409eff'
  return '#909399'
}

const getVisibilityTagType = (visibility: string): string => {
  switch (visibility) {
    case 'public': return 'success'
    case 'group': return 'warning'
    case 'user': return 'info'
    case 'private': return 'danger'
    default: return 'info'
  }
}

// Lifecycle
onMounted(async () => {
  await filesStore.fetchDirectoryTree()
  
  // Check if we have a parent_id in the route query (from sidebar navigation)
  const parentId = router.currentRoute.value.query.parent_id
  console.log('FilesView mounted, parent_id:', parentId, 'route:', router.currentRoute.value)
  
  if (parentId) {
    console.log('Navigating to directory from sidebar:', parentId)
    await navigateToDirectory(Number(parentId))
  } else {
    console.log('No parent_id, navigating to root')
    await refreshFiles()
    // Initialize breadcrumb to root
    breadcrumbPath.value = [{ id: null, name: 'root', path: '/' }]
  }
})

// Watch for route changes to handle sidebar navigation
watch(
  () => router.currentRoute.value.query.parent_id,
  async (newParentId, oldParentId) => {
    console.log('Route parent_id changed:', { old: oldParentId, new: newParentId })
    
    if (newParentId && newParentId !== oldParentId) {
      // Navigate to specific directory
      console.log('Route parent_id changed, navigating to directory:', newParentId)
      await navigateToDirectory(Number(newParentId))
    } else if (!newParentId && oldParentId) {
      // Navigate to root (parent_id was removed)
      console.log('Route parent_id removed, navigating to root')
      await navigateToRoot()
    }
  }
)
</script>

<style scoped>
.files-view {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.page-header h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 600;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.header-actions .el-dropdown {
  margin-right: 0;
}

.view-controls {
  margin-bottom: 24px;
}

.bulk-operations-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding: 12px 24px;
  background-color: #f5f7fa;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}

.bulk-info {
  font-size: 16px;
  color: #303133;
  font-weight: 500;
}

.bulk-actions {
  display: flex;
  gap: 12px;
}

.breadcrumb-container {
  margin-bottom: 24px;
}

.breadcrumb-container .el-breadcrumb {
  font-size: 16px;
}

.breadcrumb-container .el-breadcrumb__item {
  cursor: pointer;
  transition: color 0.2s ease;
}

.breadcrumb-container .el-breadcrumb__item:hover {
  color: #409eff;
}

.breadcrumb-container .el-breadcrumb__item:last-child {
  color: #409eff;
  font-weight: 600;
}

.search-bar {
  margin-bottom: 24px;
}

.file-content {
  margin-bottom: 24px;
}

/* Grid View */
.grid-view {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.file-card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  transition: all 0.2s ease;
  text-align: center;
  position: relative;
}

.file-content {
  cursor: pointer;
  transition: all 0.2s ease;
}

.file-card:hover {
  border-color: #409eff;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.1);
}

.file-content:hover {
  transform: translateY(-2px);
}

.file-selection {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 1;
}

.file-actions {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 1;
}

.custom-tree-node {
  display: flex;
  align-items: center;
  width: 100%;
}

.custom-tree-node .el-icon {
  color: #409eff;
}

.file-icon {
  margin-bottom: 12px;
}

.file-name {
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-meta {
  font-size: 12px;
  color: #909399;
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}

/* List View */
.list-view {
  width: 100%;
}

.file-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* List view table styling */
:deep(.el-table) {
  border-radius: 8px;
  overflow: hidden;
}

:deep(.el-table th) {
  background-color: #f5f7fa;
  color: #606266;
  font-weight: 600;
}

:deep(.el-table td) {
  padding: 12px 0;
}

:deep(.el-table .el-table__row:hover) {
  background-color: #f5f7fa;
}

/* List actions styling */
.list-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.list-actions .el-button {
  padding: 6px 12px;
  font-size: 12px;
}

.list-actions .el-button .el-icon {
  margin-right: 4px;
}



/* Upload Dialog Styles */
.upload-area {
  width: 100%;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

:deep(.el-upload-dragger) {
  width: 100%;
  height: 120px;
}

/* Directory upload styles */
.directory-upload-area {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.directory-input {
  width: 100%;
}

.directory-preview {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 10px;
  background-color: #f9fafc;
}

.directory-preview h4 {
  margin-top: 0;
  margin-bottom: 10px;
  color: #303133;
}

.item-breakdown {
  font-size: 14px;
  font-weight: 400;
  color: #909399;
  margin-left: 8px;
}

.total-size {
  color: #409eff;
  font-weight: 500;
}

.directory-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px dashed #ebeef5;
}

.directory-item:last-child {
  border-bottom: none;
}

.item-name {
  flex-grow: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
  color: #303133;
}

.item-size {
  font-size: 12px;
  color: #909399;
}

.directory-placeholder {
  text-align: center;
  padding: 40px 20px;
  color: #c0c4cc;
}

.directory-placeholder p {
  margin: 16px 0 0 0;
  font-size: 14px;
}

.upload-progress-section {
  margin-top: 20px;
  border-top: 1px solid #e4e7ed;
  padding-top: 20px;
}

.upload-progress-section h4 {
  margin-top: 0;
  margin-bottom: 16px;
  color: #303133;
}

.upload-progress-list {
  max-height: 300px;
  overflow-y: auto;
}

.progress-item {
  margin-bottom: 16px;
  padding: 12px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background-color: #fafafa;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.filename {
  font-weight: 600;
  color: #303133;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 12px;
}

.status {
  font-size: 12px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 12px;
  text-transform: capitalize;
}

.status.uploading {
  color: #409eff;
  background-color: #ecf5ff;
}

.status.success {
  color: #67c23a;
  background-color: #f0f9ff;
}

.status.error {
  color: #f56c6c;
  background-color: #fef0f0;
}

.error-message {
  color: #f56c6c;
  font-size: 12px;
  margin-top: 8px;
  padding: 8px;
  background-color: #fef0f0;
  border-radius: 4px;
}
</style>