<template>
  <div class="deleted-files-view">
    <div class="view-header">
      <h1>Dustbin</h1>
      <p class="subtitle">Manage deleted files and directories</p>
    </div>

    <div class="view-content">
      <!-- Actions Bar -->
      <div class="actions-bar">
        <div class="left-actions">
          <el-button
            type="primary"
            :disabled="selectedFiles.length === 0"
            @click="handleRestore"
            :loading="deletedFilesStore.isLoading"
          >
            <el-icon><RefreshLeft /></el-icon>
            Restore Selected ({{ selectedFiles.length }})
          </el-button>
          
          <el-button
            type="danger"
            :disabled="selectedFiles.length === 0"
            @click="handleHardDelete"
            :loading="deletedFilesStore.isLoading"
          >
            <el-icon><Delete /></el-icon>
            Permanently Delete ({{ selectedFiles.length }})
          </el-button>
        </div>
        
        <div class="right-actions">
          <el-button @click="refreshDeletedFiles" :loading="deletedFilesStore.isLoading">
            <el-icon><Refresh /></el-icon>
            Refresh
          </el-button>
        </div>
      </div>

      <!-- Deleted Files Table -->
      <el-card class="files-table-card">
        <el-table
          :data="deletedFilesStore.deletedFiles"
          @selection-change="handleSelectionChange"
          @sort-change="handleSortChange"
          v-loading="deletedFilesStore.isLoading"
          class="deleted-files-table"
          default-sort="{prop: 'deleted_at', order: 'descending'}"
        >
          <el-table-column type="selection" width="55" />
          
          <el-table-column 
            label="Name" 
            min-width="200"
            sortable
            :sort-method="sortByName"
          >
            <template #default="{ row }">
              <div class="file-info">
                <el-icon class="file-icon">
                  <Folder v-if="row.item_type === 'directory'" />
                  <Document v-else />
                </el-icon>
                <span class="file-name">{{ row.name }}</span>
              </div>
            </template>
          </el-table-column>
          
          <el-table-column 
            label="Type" 
            width="100"
            sortable
          >
            <template #default="{ row }">
              <el-tag :type="row.item_type === 'directory' ? 'warning' : 'info'">
                {{ row.item_type === 'directory' ? 'Directory' : 'File' }}
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column 
            label="Size" 
            width="120" 
            v-if="hasFiles"
            sortable
            :sort-method="sortBySize"
          >
            <template #default="{ row }">
              <span v-if="row.item_type === 'file'">
                {{ formatFileSize(row.size || 0) }}
              </span>
              <span v-else>-</span>
            </template>
          </el-table-column>
          
          <el-table-column 
            label="Original Location" 
            min-width="200"
            sortable
            :sort-method="sortByLocation"
          >
            <template #default="{ row }">
              <span v-if="row.original_parent">
                {{ row.original_parent.name }}
              </span>
              <span v-else>Root</span>
            </template>
          </el-table-column>
          
          <el-table-column 
            label="Deleted By" 
            width="150"
            sortable
            :sort-method="sortByDeletedBy"
          >
            <template #default="{ row }">
              <span>{{ getUserDisplayName(row.deleted_by) }}</span>
            </template>
          </el-table-column>
          
          <el-table-column 
            label="Deleted At" 
            width="180"
            sortable
            :sort-method="sortByDeletedAt"
          >
            <template #default="{ row }">
              <span>{{ formatDate(row.deleted_at) }}</span>
            </template>
          </el-table-column>
          
          <el-table-column label="Actions" width="200" fixed="right">
            <template #default="{ row }">
              <div class="action-buttons">
                <el-button
                  type="primary"
                  size="small"
                  @click="handleRestoreSingle(row.id)"
                  :loading="deletedFilesStore.isLoading"
                >
                  <el-icon><RefreshLeft /></el-icon>
                  Restore
                </el-button>
                <el-button
                  type="danger"
                  size="small"
                  @click="handleHardDeleteSingle(row.id, row.name)"
                  :loading="deletedFilesStore.isLoading"
                >
                  <el-icon><Delete /></el-icon>
                  Delete
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
        <!-- Stats Summary -->
        <p class="summary-text">
          Total: <strong>{{ deletedFilesStore.deletedFilesCount }}</strong> items
          ({{ deletedFilesStore.deletedFilesByType.files.length }} files, 
          {{ deletedFilesStore.deletedFilesCount - deletedFilesStore.deletedFilesByType.files.length }} directories)
        </p>
      </el-card>
    </div>

    <!-- Confirmation Dialogs -->
    <el-dialog
      v-model="restoreDialogVisible"
      title="Confirm Restore"
      width="400px"
    >
      <p>Are you sure you want to restore the selected {{ selectedFiles.length }} item(s)?</p>
      <template #footer>
        <el-button @click="restoreDialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="confirmRestore" :loading="deletedFilesStore.isLoading">
          Restore
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="hardDeleteDialogVisible"
      title="Confirm Permanent Deletion"
      width="400px"
    >
      <p class="warning-text">
        <el-icon><Warning /></el-icon>
        This action cannot be undone. The selected {{ selectedFiles.length }} item(s) will be permanently deleted.
      </p>
      <template #footer>
        <el-button @click="hardDeleteDialogVisible = false">Cancel</el-button>
        <el-button type="danger" @click="confirmHardDelete" :loading="deletedFilesStore.isLoading">
          Permanently Delete
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useDeletedFilesStore, type DeletedFileItem } from '@/stores/deletedFiles'
import {
  Delete,
  Document,
  Folder,
  RefreshLeft,
  Refresh,
  Warning
} from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'

const deletedFilesStore = useDeletedFilesStore()

// State
const selectedFiles = ref<DeletedFileItem[]>([])
const restoreDialogVisible = ref(false)
const hardDeleteDialogVisible = ref(false)

// Computed
const hasFiles = computed(() => deletedFilesStore.deletedFilesByType.files.length > 0)

// Methods
const refreshDeletedFiles = () => {
  deletedFilesStore.fetchDeletedFiles()
}

const handleSelectionChange = (selection: DeletedFileItem[]) => {
  selectedFiles.value = selection
}

const handleRestore = () => {
  if (selectedFiles.value.length === 0) return
  restoreDialogVisible.value = true
}

const handleRestoreSingle = async (fileId: number) => {
  const success = await deletedFilesStore.restoreFiles([fileId])
  if (success) {
    // Refresh the list
    refreshDeletedFiles()
  }
}

const handleHardDeleteSingle = async (fileId: number, fileName: string) => {
  try {
    await ElMessageBox.confirm(
      `Are you sure you want to permanently delete "${fileName}"? This action cannot be undone.`,
      'Confirm Permanent Deletion',
      {
        confirmButtonText: 'Delete Permanently',
        cancelButtonText: 'Cancel',
        type: 'warning',
        dangerouslyUseHTMLString: false
      }
    )
    
    const success = await deletedFilesStore.hardDeleteFiles([fileId])
    if (success) {
      // Refresh the list
      refreshDeletedFiles()
    }
  } catch {
    // User cancelled the confirmation
  }
}

const confirmRestore = async () => {
  const fileIds = selectedFiles.value.map(item => item.id)
  const success = await deletedFilesStore.restoreFiles(fileIds)
  if (success) {
    restoreDialogVisible.value = false
    selectedFiles.value = []
    // Refresh the list
    refreshDeletedFiles()
  }
}

const handleHardDelete = () => {
  if (selectedFiles.value.length === 0) return
  hardDeleteDialogVisible.value = true
}

const confirmHardDelete = async () => {
  const fileIds = selectedFiles.value.map(item => item.id)
  const success = await deletedFilesStore.hardDeleteFiles(fileIds)
  if (success) {
    hardDeleteDialogVisible.value = false
    selectedFiles.value = []
    // Refresh the list
    refreshDeletedFiles()
  }
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleString()
}

const getUserDisplayName = (user: { first_name?: string; last_name?: string; username: string }): string => {
  if (user.first_name && user.last_name) {
    return `${user.first_name} ${user.last_name}`
  }
  return user.username
}

// Sorting methods for table columns
const sortByName = (a: DeletedFileItem, b: DeletedFileItem): number => {
  const nameA = a.name.toLowerCase()
  const nameB = b.name.toLowerCase()
  
  // Directories first, then files
  if (a.item_type === 'directory' && b.item_type !== 'directory') return -1
  if (a.item_type !== 'directory' && b.item_type === 'directory') return 1
  
  return nameA.localeCompare(nameB)
}

const sortBySize = (a: DeletedFileItem, b: DeletedFileItem): number => {
  // Directories first (no size)
  if (a.item_type === 'directory' && b.item_type !== 'directory') return -1
  if (a.item_type !== 'directory' && b.item_type === 'directory') return 1
  
  const sizeA = a.size || 0
  const sizeB = b.size || 0
  
  return sizeA - sizeB
}

const sortByLocation = (a: DeletedFileItem, b: DeletedFileItem): number => {
  const locationA = a.original_parent?.name || 'Root'
  const locationB = b.original_parent?.name || 'Root'
  
  return locationA.localeCompare(locationB)
}

const sortByDeletedBy = (a: DeletedFileItem, b: DeletedFileItem): number => {
  const userA = getUserDisplayName(a.deleted_by)
  const userB = getUserDisplayName(b.deleted_by)
  
  return userA.localeCompare(userB)
}

const sortByDeletedAt = (a: DeletedFileItem, b: DeletedFileItem): number => {
  const dateA = new Date(a.deleted_at).getTime()
  const dateB = new Date(b.deleted_at).getTime()
  
  return dateA - dateB
}

const handleSortChange = (sortInfo: { prop: string; order: string }) => {
  console.log('Sort changed:', sortInfo)
  // The table handles sorting automatically, but we can add custom logic here if needed
}

// Lifecycle
onMounted(() => {
  refreshDeletedFiles()
})
</script>

<style scoped>
.deleted-files-view {
  padding: 24px;
}

.view-header {
  margin-bottom: 24px;
}

.view-header h1 {
  margin: 0 0 8px 0;
  font-size: 28px;
  font-weight: 600;
  color: #303133;
}

.subtitle {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.stats-summary {
  margin-top: 16px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 4px solid #409eff;
  text-align: center;
}

.summary-text {
  margin: 4px;
  font-size: 14px;
  color: #606266;
  line-height: 1.5;
}

.summary-text strong {
  color: #303133;
  font-weight: 600;
}

.actions-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  gap: 16px;
}

.left-actions {
  display: flex;
  gap: 12px;
}

.right-actions {
  display: flex;
  gap: 12px;
}

.files-table-card {
  border: none;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.deleted-files-table {
  width: 100%;
}

/* Sortable column styling */
:deep(.el-table .sortable) {
  cursor: pointer;
}

:deep(.el-table .sortable:hover) {
  background-color: #f0f9ff;
}

:deep(.el-table .sortable .cell) {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

:deep(.el-table .sortable .cell::after) {
  content: '';
  width: 0;
  height: 0;
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  margin-left: 8px;
  opacity: 0.3;
}

:deep(.el-table .sortable.ascending .cell::after) {
  border-bottom: 4px solid #409eff;
  opacity: 1;
}

:deep(.el-table .sortable.descending .cell::after) {
  border-top: 4px solid #409eff;
  opacity: 1;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-icon {
  color: #909399;
}

.file-name {
  font-weight: 500;
}

.action-buttons {
  display: flex;
  gap: 8px;
  align-items: center;
}

.action-buttons .el-button {
  flex-shrink: 0;
}

.warning-text {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #e6a23c;
  font-weight: 500;
}

.warning-text .el-icon {
  font-size: 18px;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .deleted-files-view {
    padding: 16px;
  }
  
  .actions-bar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .left-actions,
  .right-actions {
    justify-content: center;
  }
}
</style>
