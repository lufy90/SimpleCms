<template>
  <div class="shared-to-me-view">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-left">
        <h1>Files Shared to Me</h1>
        <p class="header-description">
          Files and directories that other users have shared with you
        </p>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="refreshFiles" :loading="isLoading">
          <el-icon><Refresh /></el-icon>
          Refresh
        </el-button>
      </div>
    </div>

    <!-- Filters and Search -->
    <div class="filters-section">
      <el-row :gutter="16">
        <el-col :span="8">
          <el-input
            v-model="searchQuery"
            placeholder="Search shared files..."
            prefix-icon="Search"
            clearable
            @input="handleSearch"
          />
        </el-col>
        <el-col :span="4">
          <el-select v-model="filters.type" placeholder="Type" clearable @change="applyFilters">
            <el-option label="All" value="" />
            <el-option label="Files" value="file" />
            <el-option label="Directories" value="directory" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-select
            v-model="filters.extension"
            placeholder="Extension"
            clearable
            filterable
            @change="applyFilters"
          >
            <el-option label="All" value="" />
            <el-option v-for="ext in availableExtensions" :key="ext" :label="ext" :value="ext" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-select
            v-model="filters.owner"
            placeholder="Owner"
            clearable
            filterable
            @change="applyFilters"
          >
            <el-option label="All" value="" />
            <el-option
              v-for="owner in availableOwners"
              :key="owner.id"
              :label="owner.username"
              :value="owner.id"
            />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-select v-model="sortBy" placeholder="Sort by" @change="applySorting">
            <el-option label="Name" value="name" />
            <el-option label="Size" value="size" />
            <el-option label="Modified" value="modified" />
            <el-option label="Owner" value="owner" />
          </el-select>
        </el-col>
      </el-row>
    </div>

    <!-- File List -->
    <div class="file-content">
      <el-empty
        v-if="filteredFiles.length === 0 && !isLoading"
        description="No shared files found"
      />

      <!-- Grid View -->
      <div v-else-if="viewType === 'grid'" class="grid-view">
        <div v-for="file in filteredFiles" :key="file.id" class="file-card">
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
              <span>{{ formatDate(file.created_at) }}</span>
            </div>
            <div class="file-owner">
              <el-tag size="small" type="info"> Owner: {{ file.owner.username }} </el-tag>
            </div>
            <div class="file-permissions">
              <el-tag
                v-for="perm in file.effective_permissions"
                :key="perm"
                :type="getPermissionTagType(perm)"
                size="small"
                style="margin-right: 4px; margin-bottom: 4px"
              >
                {{ perm }}
              </el-tag>
            </div>
          </div>
          <div class="file-actions">
            <el-button
              v-if="file.can_read"
              type="text"
              size="small"
              @click.stop="downloadFile(file)"
              :disabled="file.item_type === 'directory'"
            >
              <el-icon><Download /></el-icon>
            </el-button>
            <el-button type="text" size="small" @click.stop="showFileDetails(file)">
              <el-icon><View /></el-icon>
            </el-button>
          </div>
        </div>
      </div>

      <!-- List View -->
      <div v-else class="list-view">
        <el-table :data="filteredFiles" style="width: 100%" @row-click="handleFileClick">
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
          <el-table-column prop="owner.username" label="Owner" width="150" />
          <el-table-column prop="created_at" label="Created" width="150">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column prop="effective_permissions" label="Permissions" width="200">
            <template #default="{ row }">
              <el-tag
                v-for="perm in row.effective_permissions"
                :key="perm"
                :type="getPermissionTagType(perm)"
                size="small"
                style="margin-right: 4px; margin-bottom: 4px"
              >
                {{ perm }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="Actions" width="120" fixed="right">
            <template #default="{ row }">
              <div class="action-buttons">
                <el-button
                  v-if="row.can_read"
                  type="info"
                  size="small"
                  @click.stop="downloadFile(row)"
                  :disabled="row.item_type === 'directory'"
                >
                  <el-icon><Download /></el-icon>
                </el-button>
                <el-button type="info" size="small" @click.stop="showFileDetails(row)">
                  <el-icon><View /></el-icon>
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- View Toggle -->
      <div class="view-toggle">
        <el-button-group>
          <el-button :type="viewType === 'grid' ? 'primary' : 'default'" @click="viewType = 'grid'">
            <el-icon><Grid /></el-icon>
            Grid
          </el-button>
          <el-button :type="viewType === 'list' ? 'primary' : 'default'" @click="viewType = 'list'">
            <el-icon><List /></el-icon>
            List
          </el-button>
        </el-button-group>
      </div>
    </div>

    <!-- File Details Dialog -->
    <el-dialog
      v-model="detailsDialogVisible"
      :title="`Details: ${selectedFile?.name}`"
      width="600px"
    >
      <el-descriptions :column="2" border>
        <el-descriptions-item label="Name" :span="2">
          {{ selectedFile?.name }}
        </el-descriptions-item>
        <el-descriptions-item label="Type">
          {{ selectedFile?.item_type }}
        </el-descriptions-item>
        <el-descriptions-item label="Size" v-if="selectedFile?.size">
          {{ formatFileSize(selectedFile.size) }}
        </el-descriptions-item>
        <el-descriptions-item label="Owner">
          {{ selectedFile?.owner.username }}
        </el-descriptions-item>
        <el-descriptions-item label="Created">
          {{ formatDate(selectedFile?.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="Permissions" :span="2">
          <div class="permissions-display">
            <el-tag
              v-for="perm in selectedFile?.effective_permissions"
              :key="perm"
              :type="getPermissionTagType(perm)"
              size="small"
              style="margin-right: 8px; margin-bottom: 8px"
            >
              {{ perm }}
            </el-tag>
          </div>
        </el-descriptions-item>
        <el-descriptions-item
          label="Tags"
          :span="2"
          v-if="selectedFile?.tags && selectedFile.tags.length > 0"
        >
          <div class="tags-display">
            <el-tag
              v-for="tagRel in selectedFile.tags"
              :key="tagRel.id"
              :color="tagRel.tag.color"
              size="small"
              style="margin-right: 8px; margin-bottom: 8px"
            >
              {{ tagRel.tag.name }}
            </el-tag>
          </div>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useFilesStore, type FileSystemItem } from '@/stores/files'
import { filesAPI } from '@/services/api'
import {
  Grid,
  List,
  Document,
  Folder,
  Refresh,
  Search,
  Download,
  View,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const filesStore = useFilesStore()

// State
const viewType = ref<'grid' | 'list'>('grid')
const searchQuery = ref('')
const isLoading = ref(false)
const sharedFiles = ref<FileSystemItem[]>([])
const detailsDialogVisible = ref(false)
const selectedFile = ref<FileSystemItem | null>(null)

// Filters
const filters = ref({
  type: '',
  extension: '',
  owner: '',
})

const sortBy = ref<'name' | 'size' | 'modified' | 'owner'>('name')
const sortOrder = ref<'asc' | 'desc'>('asc')

// Computed properties
const availableExtensions = computed(() => {
  const extensions = new Set<string>()
  sharedFiles.value.forEach((file) => {
    if (file.extension) {
      extensions.add(file.extension)
    }
  })
  return Array.from(extensions).sort()
})

const availableOwners = computed(() => {
  const owners = new Map<number, { id: number; username: string }>()
  sharedFiles.value.forEach((file) => {
    owners.set(file.owner.id, file.owner)
  })
  return Array.from(owners.values()).sort((a, b) => a.username.localeCompare(b.username))
})

const filteredFiles = computed(() => {
  let filtered = [...sharedFiles.value]

  // Apply search filter
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(
      (file) =>
        file.name.toLowerCase().includes(query) ||
        file.owner.username.toLowerCase().includes(query),
    )
  }

  // Apply type filter
  if (filters.value.type) {
    filtered = filtered.filter((file) => file.item_type === filters.value.type)
  }

  // Apply extension filter
  if (filters.value.extension) {
    filtered = filtered.filter((file) => file.extension === filters.value.extension)
  }

  // Apply owner filter
  if (filters.value.owner) {
    filtered = filtered.filter((file) => file.owner.id === filters.value.owner)
  }

  // Apply sorting
  filtered.sort((a, b) => {
    let aValue: any
    let bValue: any

    switch (sortBy.value) {
      case 'name':
        aValue = a.name.toLowerCase()
        bValue = b.name.toLowerCase()
        break
      case 'size':
        aValue = a.size || 0
        bValue = b.size || 0
        break
      case 'modified':
        aValue = new Date(a.updated_at).getTime()
        bValue = new Date(b.updated_at).getTime()
        break
      case 'owner':
        aValue = a.owner.username.toLowerCase()
        bValue = b.owner.username.toLowerCase()
        break
      default:
        return 0
    }

    if (sortOrder.value === 'asc') {
      return aValue < bValue ? -1 : aValue > bValue ? 1 : 0
    } else {
      return aValue > bValue ? -1 : aValue < bValue ? 1 : 0
    }
  })

  return filtered
})

// Methods
const fetchSharedFiles = async () => {
  try {
    isLoading.value = true
    const response = await filesAPI.getSharedToMe({
      page_size: 1000, // Get all shared files
    })

    if (response.data.pagination) {
      sharedFiles.value = response.data.results
    } else {
      sharedFiles.value = response.data.results || response.data
    }
  } catch (error) {
    ElMessage.error('Failed to fetch shared files')
    console.error('Error fetching shared files:', error)
  } finally {
    isLoading.value = false
  }
}

const refreshFiles = () => {
  fetchSharedFiles()
}

const handleSearch = () => {
  // Search is handled by computed property
}

const applyFilters = () => {
  // Filters are handled by computed property
}

const applySorting = () => {
  // Sorting is handled by computed property
}

const handleFileClick = (file: FileSystemItem) => {
  if (file.item_type === 'directory') {
    router.push({ name: 'Files', query: { parent_id: file.id } })
  } else {
    showFileDetails(file)
  }
}

const showFileDetails = (file: FileSystemItem) => {
  selectedFile.value = file
  detailsDialogVisible.value = true
}

const downloadFile = async (file: FileSystemItem) => {
  if (file.item_type === 'directory') return

  try {
    const response = await filesAPI.download(file.id)
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', file.name)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    ElMessage.success('Download started')
  } catch (error) {
    ElMessage.error('Failed to download file')
    console.error('Error downloading file:', error)
  }
}

// Utility methods
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleDateString()
}

const getFileIconColor = (file: FileSystemItem): string => {
  if (file.item_type === 'directory') return '#409eff'
  return '#909399'
}

const getPermissionTagType = (permission: string): string => {
  switch (permission) {
    case 'read':
      return 'info'
    case 'write':
      return 'warning'
    case 'delete':
      return 'danger'
    case 'share':
      return 'success'
    case 'admin':
      return 'danger'
    default:
      return 'info'
  }
}

// Lifecycle
onMounted(() => {
  fetchSharedFiles()
})
</script>

<style scoped>
.shared-to-me-view {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.header-left h1 {
  margin: 0 0 8px 0;
  font-size: 28px;
  font-weight: 600;
  color: #303133;
}

.header-description {
  margin: 0;
  color: #606266;
  font-size: 14px;
}

.filters-section {
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 24px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.file-content {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.grid-view {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.file-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
}

.file-card:hover {
  border-color: #409eff;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.15);
}

.file-content {
  text-align: center;
}

.file-icon {
  margin-bottom: 12px;
}

.file-name {
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
  word-break: break-word;
}

.file-meta {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.file-meta span {
  display: block;
  margin-bottom: 2px;
}

.file-owner {
  margin-bottom: 8px;
}

.file-permissions {
  margin-bottom: 8px;
}

.file-actions {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  gap: 4px;
}

.list-view {
  margin-bottom: 24px;
}

.file-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.action-buttons {
  display: flex;
  gap: 8px;
}

.view-toggle {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}

.permissions-display,
.tags-display {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

/* Responsive */
@media (max-width: 768px) {
  .filters-section .el-row {
    margin: 0;
  }

  .filters-section .el-col {
    margin-bottom: 16px;
  }

  .grid-view {
    grid-template-columns: 1fr;
  }
}
</style>
