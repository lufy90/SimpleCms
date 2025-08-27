<template>
  <div class="files-view">
    <div class="page-header">
      <div class="header-left">
        <h1>{{ currentDirectory ? currentDirectory.name : 'Files' }}</h1>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="openUpload">
          <el-icon><Upload /></el-icon>
          Upload
        </el-button>
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
          @click="handleFileClick(file)"
        >
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
      </div>

      <!-- List View -->
      <el-table
        v-else
        :data="filteredFiles"
        @row-click="handleFileClick"
        class="list-view"
      >
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
      </el-table>
    </div>

    <!-- Pagination -->
    <div v-if="pagination" class="pagination">
      <el-pagination
        v-model:current-page="pagination.current_page"
        v-model:page-size="pagination.page_size"
        :page-sizes="[10, 25, 50, 100]"
        :total="pagination.count"
        layout="total, sizes, prev, pager, next"
        @size-change="handlePageSizeChange"
        @current-change="handlePageChange"
      />
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

        <el-form-item label="Files">
          <el-upload
            ref="uploadRef"
            :action="uploadAction"
            :headers="uploadHeaders"
            :data="uploadData"
            :on-success="handleUploadSuccess"
            :on-error="handleUploadError"
            :before-upload="beforeUpload"
            multiple
            drag
            class="upload-area"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              Drop file here or <em>click to upload</em>
            </div>
          </el-upload>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="uploadDialogVisible = false">Cancel</el-button>
          <el-button type="primary" @click="handleUpload" :loading="isUploading">
            Upload Files
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useFilesStore } from '@/stores/files'
import { Grid, List, Document, Folder, Upload, Refresh, Back, FolderAdd, UploadFilled } from '@element-plus/icons-vue'
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
const isUploading = ref(false)
const uploadRef = ref()

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

// Methods
const setViewType = (type: 'grid' | 'list') => {
  viewType.value = type
}

const openUpload = () => {
  uploadDialogVisible.value = true
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
    uploadRef.value.submit()
  }
}

const handleUploadSuccess = (response: any, file: any) => {
  ElMessage.success(`${file.name} uploaded successfully`)
  // Refresh the file list to show the new file
  refreshFiles()
}

const handleUploadError = (error: any, file: any) => {
  ElMessage.error(`${file.name} upload failed`)
}

const beforeUpload = (file: any) => {
  return true
}

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

const handlePageSizeChange = (size: number) => {
  filesStore.fetchFiles({ page_size: size, page: 1 })
}

const handlePageChange = (page: number) => {
  filesStore.fetchFiles({ page })
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

.view-controls {
  margin-bottom: 24px;
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
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: center;
}

.file-card:hover {
  border-color: #409eff;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.1);
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

.pagination {
  display: flex;
  justify-content: center;
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
</style>