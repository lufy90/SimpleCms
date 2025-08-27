import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { filesAPI, uploadAPI, operationsAPI } from '@/services/api'
import { toast } from 'vue3-toastify'

export interface FileSystemItem {
  id: number
  name: string
  path: string
  item_type: 'file' | 'directory'
  parent?: number
  size?: number
  mime_type?: string
  extension?: string
  created_at: string
  updated_at: string
  last_modified?: string
  owner: {
    id: number
    username: string
    email: string
    first_name: string
    last_name: string
  }
  visibility: 'private' | 'user' | 'group' | 'public'
  shared_users: Array<{
    id: number
    username: string
    email: string
    first_name: string
    last_name: string
  }>
  shared_groups: Array<{
    id: number
    name: string
  }>
  children_count: number
  tags: Array<{
    id: number
    tag: {
      id: number
      name: string
      color: string
      created_at: string
    }
    created_at: string
  }>
  file_info?: {
    size: number
    created: number
    modified: number
    accessed: number
    permissions: string
  }
  permissions: string[]
  can_read: boolean
  can_write: boolean
  can_delete: boolean
  can_share: boolean
  can_admin: boolean
  effective_permissions: string[]
}

export interface DirectoryTreeItem {
  id?: number
  name: string
  path: string
  item_type: 'file' | 'directory'
  children?: DirectoryTreeItem[]
  size?: number
  mime_type?: string
  extension?: string
  last_modified?: string
  visibility?: string
}

export interface PaginationInfo {
  count: number
  next: string | null
  previous: string | null
  page_size: number
  current_page: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}

export const useFilesStore = defineStore('files', () => {
  // State
  const files = ref<FileSystemItem[]>([])
  const currentDirectory = ref<FileSystemItem | null>(null)
  const directoryTree = ref<DirectoryTreeItem[]>([])
  const selectedFiles = ref<Set<number>>(new Set())
  const viewType = ref<'list' | 'grid' | 'details'>('grid')
  const sortBy = ref<'name' | 'size' | 'modified' | 'type'>('name')
  const sortOrder = ref<'asc' | 'desc'>('asc')
  const searchQuery = ref('')
  const isLoading = ref(false)
  const pagination = ref<PaginationInfo | null>(null)
  const filters = ref({
    type: '',
    visibility: '',
    extension: '',
    owner: '',
  })

  // Getters
  const sortedFiles = computed(() => {
    const sorted = [...files.value]
    
    sorted.sort((a, b) => {
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
          aValue = new Date(a.last_modified || a.updated_at).getTime()
          bValue = new Date(b.last_modified || b.updated_at).getTime()
          break
        case 'type':
          aValue = a.item_type
          bValue = b.item_type
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
    
    return sorted
  })

  const filteredFiles = computed(() => {
    let filtered = sortedFiles.value
    
    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase()
      filtered = filtered.filter(file => 
        file.name.toLowerCase().includes(query) ||
        file.path.toLowerCase().includes(query)
      )
    }
    
    if (filters.value.type) {
      filtered = filtered.filter(file => file.item_type === filters.value.type)
    }
    
    if (filters.value.visibility) {
      filtered = filtered.filter(file => file.visibility === filters.value.visibility)
    }
    
    if (filters.value.extension) {
      filtered = filtered.filter(file => 
        file.extension && file.extension.toLowerCase().includes(filters.value.extension.toLowerCase())
      )
    }
    
    return filtered
  })

  const selectedFilesList = computed(() => 
    files.value.filter(file => selectedFiles.value.has(file.id))
  )

  const canPerformBulkOperation = computed(() => {
    if (selectedFiles.value.size === 0) return false
    
    const selectedItems = selectedFilesList.value
    return selectedItems.every(item => item.can_delete)
  })

  // Actions
  const fetchFiles = async (params?: {
    page?: number
    page_size?: number
    parent?: number
    type?: string
    visibility?: string
    extension?: string
  }) => {
    try {
      isLoading.value = true
      const response = await filesAPI.list(params)
      
      if (response.data.pagination) {
        files.value = response.data.results
        pagination.value = response.data.pagination
      } else {
        files.value = response.data.results || response.data
        pagination.value = null
      }
      
      return true
    } catch (error: any) {
      toast.error('Failed to fetch files')
      return false
    } finally {
      isLoading.value = false
    }
  }

  const fetchDirectoryTree = async (root?: string) => {
    try {
      const response = await filesAPI.tree(root)
      directoryTree.value = response.data
      return true
    } catch (error: any) {
      toast.error('Failed to fetch directory tree')
      return false
    }
  }

  const fetchChildren = async (parentId?: number) => {
    try {
      isLoading.value = true
      const response = await filesAPI.listChildren(parentId)
      
      if (response.data.children) {
        files.value = response.data.children
        currentDirectory.value = response.data.parent || null
        pagination.value = null
      }
      
      return true
    } catch (error: any) {
      toast.error('Failed to fetch directory contents')
      return false
    } finally {
      isLoading.value = false
    }
  }

  const searchFiles = async (query: string, params?: { type?: string; limit?: number }) => {
    try {
      isLoading.value = true
      const response = await filesAPI.search(query, params)
      files.value = response.data.results
      return true
    } catch (error: any) {
      toast.error('Search failed')
      return false
    } finally {
      isLoading.value = false
    }
  }

  const uploadFile = async (file: File, destinationPath?: string, visibility?: string, tags?: string[]) => {
    try {
      const formData = new FormData()
      formData.append('file', file)
      
      if (destinationPath) {
        formData.append('destination_path', destinationPath)
      }
      
      if (visibility) {
        formData.append('visibility', visibility)
      }
      
      if (tags && tags.length > 0) {
        tags.forEach(tag => formData.append('tags', tag))
      }
      
      await uploadAPI.upload(formData)
      toast.success('File uploaded successfully')
      
      // Refresh file list
      await fetchFiles()
      return true
    } catch (error: any) {
      toast.error('Upload failed')
      return false
    }
  }

  const deleteFiles = async (fileIds: number[]) => {
    try {
      const paths = fileIds.map(id => {
        const file = files.value.find(f => f.id === id)
        return file?.path || ''
      }).filter(path => path)
      
      if (paths.length === 0) return false
      
      await operationsAPI.execute('delete', paths)
      toast.success('Files deleted successfully')
      
      // Remove from selection and refresh
      fileIds.forEach(id => selectedFiles.value.delete(id))
      await fetchFiles()
      return true
    } catch (error: any) {
      toast.error('Delete failed')
      return false
    }
  }

  const copyFiles = async (fileIds: number[], destinationPath: string) => {
    try {
      const paths = fileIds.map(id => {
        const file = files.value.find(f => f.id === id)
        return file?.path || ''
      }).filter(path => path)
      
      if (paths.length === 0) return false
      
      await operationsAPI.execute('copy', paths, destinationPath)
      toast.success('Files copied successfully')
      
      // Clear selection and refresh
      selectedFiles.value.clear()
      await fetchFiles()
      return true
    } catch (error: any) {
      toast.error('Copy failed')
      return false
    }
  }

  const moveFiles = async (fileIds: number[], destinationPath: string) => {
    try {
      const paths = fileIds.map(id => {
        const file = files.value.find(f => f.id === id)
        return file?.path || ''
      }).filter(path => path)
      
      if (paths.length === 0) return false
      
      await operationsAPI.execute('move', paths, destinationPath)
      toast.success('Files moved successfully')
      
      // Clear selection and refresh
      selectedFiles.value.clear()
      await fetchFiles()
      return true
    } catch (error: any) {
      toast.error('Move failed')
      return false
    }
  }

  const scanDirectory = async (path: string) => {
    try {
      isLoading.value = true
      await filesAPI.scanDirectory(path)
      toast.success('Directory scanned successfully')
      
      // Refresh tree and files
      await fetchDirectoryTree()
      await fetchFiles()
      return true
    } catch (error: any) {
      toast.error('Directory scan failed')
      return false
    } finally {
      isLoading.value = false
    }
  }

  const toggleFileSelection = (fileId: number) => {
    if (selectedFiles.value.has(fileId)) {
      selectedFiles.value.delete(fileId)
    } else {
      selectedFiles.value.add(fileId)
    }
  }

  const clearSelection = () => {
    selectedFiles.value.clear()
  }

  const selectAll = () => {
    files.value.forEach(file => selectedFiles.value.add(file.id))
  }

  const setViewType = (type: 'list' | 'grid' | 'details') => {
    viewType.value = type
  }

  const setSort = (field: 'name' | 'size' | 'modified' | 'type', order: 'asc' | 'desc') => {
    sortBy.value = field
    sortOrder.value = order
  }

  const setFilters = (newFilters: Partial<typeof filters.value>) => {
    filters.value = { ...filters.value, ...newFilters }
  }

  const resetFilters = () => {
    filters.value = {
      type: '',
      visibility: '',
      extension: '',
      owner: '',
    }
    searchQuery.value = ''
  }

  return {
    // State
    files,
    currentDirectory,
    directoryTree,
    selectedFiles,
    viewType,
    sortBy,
    sortOrder,
    searchQuery,
    isLoading,
    pagination,
    filters,
    
    // Getters
    sortedFiles,
    filteredFiles,
    selectedFilesList,
    canPerformBulkOperation,
    
    // Actions
    fetchFiles,
    fetchDirectoryTree,
    fetchChildren,
    searchFiles,
    uploadFile,
    deleteFiles,
    copyFiles,
    moveFiles,
    scanDirectory,
    toggleFileSelection,
    clearSelection,
    selectAll,
    setViewType,
    setSort,
    setFilters,
    resetFilters,
  }
})
