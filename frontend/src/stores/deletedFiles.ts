import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { deletedFilesAPI } from '@/services/api'
import { ElMessage } from 'element-plus'

export interface DeletedFileItem {
  id: number
  name: string
  path: string
  item_type: 'file' | 'directory'
  size?: number
  deleted_at: string
  deleted_by: {
    id: number
    username: string
    first_name?: string
    last_name?: string
  }
  original_parent?: {
    id: number
    name: string
  }
}

export const useDeletedFilesStore = defineStore('deletedFiles', () => {
  // State
  const deletedFiles = ref<DeletedFileItem[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const deletedFilesCount = computed(() => deletedFiles.value.length)
  const deletedFilesByType = computed(() => ({
    files: deletedFiles.value.filter(item => item.item_type === 'file'),
    directories: deletedFiles.value.filter(item => item.item_type === 'directory')
  }))

  // Actions
  const fetchDeletedFiles = async () => {
    try {
      isLoading.value = true
      error.value = null
      const response = await deletedFilesAPI.list()
      deletedFiles.value = response.data
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || 'Failed to fetch deleted files'
      error.value = errorMessage
      ElMessage.error(errorMessage)
    } finally {
      isLoading.value = false
    }
  }

  const restoreFiles = async (fileIds: number[]) => {
    try {
      isLoading.value = true
      error.value = null
      await deletedFilesAPI.restore(fileIds)
      
      // Remove restored files from the list
      deletedFiles.value = deletedFiles.value.filter(item => !fileIds.includes(item.id))
      
      ElMessage.success(`Successfully restored ${fileIds.length} item(s)`)
      return true
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || 'Failed to restore files'
      error.value = errorMessage
      ElMessage.error(errorMessage)
      return false
    } finally {
      isLoading.value = false
    }
  }

  const hardDeleteFiles = async (fileIds: number[]) => {
    try {
      isLoading.value = true
      error.value = null
      await deletedFilesAPI.hardDelete(fileIds)
      
      // Remove permanently deleted files from the list
      deletedFiles.value = deletedFiles.value.filter(item => !fileIds.includes(item.id))
      
      ElMessage.success(`Successfully permanently deleted ${fileIds.length} item(s)`)
      return true
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || 'Failed to permanently delete files'
      error.value = errorMessage
      ElMessage.error(errorMessage)
      return false
    } finally {
      isLoading.value = false
    }
  }

  const clearError = () => {
    error.value = null
  }

  return {
    // State
    deletedFiles,
    isLoading,
    error,
    
    // Computed
    deletedFilesCount,
    deletedFilesByType,
    
    // Actions
    fetchDeletedFiles,
    restoreFiles,
    hardDeleteFiles,
    clearError
  }
})
