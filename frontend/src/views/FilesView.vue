<template>
  <div class="files-view">
    <div class="page-header">
      <div class="header-left">
        <h1>{{ currentDirectory ? currentDirectory.name : 'Files' }}</h1>
        <!-- Breadcrumb Navigation -->
        <div v-if="currentDirectory" class="breadcrumb">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item @click="navigateToRoot">Root</el-breadcrumb-item>
            <el-breadcrumb-item 
              v-for="(item, index) in breadcrumbItems" 
              :key="index"
              @click="navigateToDirectory(item.id)"
            >
              {{ item.name }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="openUpload">
          <el-icon><Upload /></el-icon>
          Upload
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useFilesStore } from '@/stores/files'
import { Grid, List, Document, Folder, Upload, Refresh, Back } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const filesStore = useFilesStore()

// State
const viewType = ref<'grid' | 'list'>('grid')
const searchQuery = ref('')

// Computed
const files = computed(() => filesStore.files)
const filteredFiles = computed(() => filesStore.filteredFiles)
const isLoading = computed(() => filesStore.isLoading)
const pagination = computed(() => filesStore.pagination)
const currentDirectory = computed(() => filesStore.currentDirectory)

// Breadcrumb items computed
const breadcrumbItems = computed(() => {
  if (!currentDirectory.value) return []
  
  const items = []
  let current = currentDirectory.value
  
  // Build breadcrumb path by traversing up the parent chain
  while (current && current.parent) {
    // We need to find the parent in our current context
    // For now, we'll just show the current directory name
    // In a full implementation, you might want to fetch parent info
    break
  }
  
  return items
})

// Methods
const setViewType = (type: 'grid' | 'list') => {
  viewType.value = type
}

const openUpload = () => {
  router.push('/upload')
}

const refreshFiles = async () => {
  if (currentDirectory.value) {
    await filesStore.fetchChildren(currentDirectory.value.id)
  } else {
    await filesStore.fetchChildren()
  }
  ElMessage.success('Files refreshed')
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
  await filesStore.fetchChildren(directoryId)
}

const navigateToRoot = async () => {
  await filesStore.fetchChildren()
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
  // Check if we have a parent_id in the route query
  const parentId = router.currentRoute.value.query.parent_id
  if (parentId) {
    await filesStore.fetchChildren(Number(parentId))
  } else {
    await filesStore.fetchChildren()
  }
})
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

.breadcrumb {
  margin-top: 8px;
}

.breadcrumb .el-breadcrumb__item {
  cursor: pointer;
}

.breadcrumb .el-breadcrumb__item:hover {
  color: #409eff;
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
</style>
