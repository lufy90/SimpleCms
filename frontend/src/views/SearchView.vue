<template>
  <div class="search-view">
    <div class="page-header">
      <h1>Search Files</h1>
      <el-button @click="$router.go(-1)">
        <el-icon><ArrowLeft /></el-icon>
        Back
      </el-button>
    </div>

    <el-card class="search-card">
      <template #header>
        <div class="card-header">
          <span>Search</span>
        </div>
      </template>

      <el-form :model="searchForm" label-width="120px">
        <el-form-item label="Search Query">
          <el-input
            v-model="searchForm.query"
            placeholder="Enter search terms..."
            clearable
            @keyup.enter="performSearch"
          />
        </el-form-item>

        <el-form-item label="File Type">
          <el-select v-model="searchForm.type" placeholder="All types" clearable>
            <el-option label="All" value="" />
            <el-option label="Files" value="file" />
            <el-option label="Directories" value="directory" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="performSearch" :loading="isLoading">
            Search
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Search Results -->
    <div v-if="searchResults.length > 0" class="search-results">
      <h2>Search Results ({{ searchResults.length }})</h2>
      
      <el-table :data="searchResults" @row-click="handleFileClick">
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
        <el-table-column prop="path" label="Path" min-width="300" />
        <el-table-column prop="size" label="Size" width="120">
          <template #default="{ row }">
            <span v-if="row.size">{{ formatFileSize(row.size) }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="item_type" label="Type" width="100" />
      </el-table>
    </div>

    <el-empty
      v-else-if="hasSearched && !isLoading"
      description="No files found matching your search"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useFilesStore } from '@/stores/files'
import { ArrowLeft, Document, Folder } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const filesStore = useFilesStore()

// State
const isLoading = ref(false)
const hasSearched = ref(false)
const searchResults = ref([])

// Form
const searchForm = reactive({
  query: '',
  type: '',
})

// Methods
const performSearch = async () => {
  if (!searchForm.query.trim()) {
    ElMessage.warning('Please enter a search query')
    return
  }

  try {
    isLoading.value = true
    hasSearched.value = true
    
    const success = await filesStore.searchFiles(searchForm.query, {
      type: searchForm.type || undefined,
      limit: 100
    })
    
    if (success) {
      searchResults.value = filesStore.files
    }
  } catch (error) {
    ElMessage.error('Search failed')
  } finally {
    isLoading.value = false
  }
}

const handleFileClick = (file: any) => {
  if (file.item_type === 'directory') {
    router.push({ name: 'Files', query: { path: file.path } })
  } else {
    router.push({ name: 'FileDetails', params: { id: file.id } })
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

const getFileIconColor = (file: any): string => {
  if (file.item_type === 'directory') return '#409eff'
  return '#909399'
}

// Lifecycle
onMounted(() => {
  // If query parameter exists, perform search automatically
  const query = route.query.q as string
  if (query) {
    searchForm.query = query
    performSearch()
  }
})
</script>

<style scoped>
.search-view {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-header h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 600;
  color: #303133;
}

.search-card {
  margin-bottom: 24px;
  max-width: 600px;
}

.card-header {
  font-weight: 600;
  font-size: 16px;
}

.search-results {
  margin-top: 24px;
}

.search-results h2 {
  margin-bottom: 16px;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.file-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
