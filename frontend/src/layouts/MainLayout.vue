<template>
  <div class="main-layout">
    <!-- Sidebar -->
    <aside class="sidebar" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
      <div class="sidebar-header">
        <div class="header-content">
          <h3 v-if="!sidebarCollapsed" class="logo">
            <el-icon><Folder /></el-icon>
            File Manager
          </h3>
          <el-button type="text" size="large" @click="toggleSidebar" class="sidebar-toggle">
            <el-icon v-if="sidebarCollapsed"><Expand /></el-icon>
            <el-icon v-else><Fold /></el-icon>
          </el-button>
        </div>
      </div>

      <!-- Directory Tree -->
      <div class="sidebar-content">
        <div class="tree-header" v-if="!sidebarCollapsed">
          <h4>Directory Tree</h4>
          <div class="tree-actions">
            <el-button type="text" size="small" @click="showCreateDirectoryDialog">
              <el-icon><Plus /></el-icon>
            </el-button>
            <el-button type="text" size="small" @click="refreshTree" :loading="isLoading">
              <el-icon><Refresh /></el-icon>
            </el-button>
          </div>
        </div>

        <el-tree
          :key="treeRefreshKey"
          :data="directoryTree"
          :props="treeProps"
          :expand-on-click-node="false"
          :default-expand-all="false"
          :lazy="true"
          :load="loadNode"
          :current-node-key="currentDirectoryId"
          node-key="id"
          @node-click="handleNodeClick"
          class="directory-tree"
        >
          <template #default="{ node, data }">
            <div class="tree-node" :class="{ 'virtual-root': data.is_virtual }">
              <FileIcon :file="data" :size="16" :show-thumbnail="false" />
              <span class="node-label" :title="data.name">
                {{ data.name }}
              </span>
            </div>
          </template>
        </el-tree>
      </div>



      <!-- Dustbin Section -->
      <div class="dustbin-section">
        <!-- Expanded view -->
        <div v-if="!sidebarCollapsed" class="dustbin-header">
          <h4>Dustbin</h4>
          <el-badge
            :value="deletedFilesCount"
            :hidden="deletedFilesCount === 0"
            class="dustbin-badge"
          >
            <el-button type="text" size="small" @click="navigateToDustbin" class="dustbin-button">
              <el-icon><Delete /></el-icon>
              <span>Deleted Files</span>
            </el-button>
          </el-badge>
        </div>
        
        <!-- Collapsed view -->
        <div v-else class="dustbin-collapsed">
          <el-badge
            :value="deletedFilesCount"
            :hidden="deletedFilesCount === 0"
            class="dustbin-badge-collapsed"
          >
            <el-button type="text" size="large" @click="navigateToDustbin" class="dustbin-icon-button">
              <el-icon><Delete /></el-icon>
            </el-button>
          </el-badge>
        </div>
      </div>


    </aside>

    <!-- Main Content -->
    <div class="main-content">
      <!-- Top Navigation -->
      <header class="top-nav">
        <div class="nav-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/files' }">Files</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentPath">{{ currentPath }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="nav-right">
          <!-- Search -->
          <el-input
            v-model="searchQuery"
            placeholder="Search files..."
            prefix-icon="Search"
            clearable
            @input="handleSearch"
            class="search-input"
          />

          <!-- User Menu -->
          <el-dropdown @command="handleUserCommand">
            <el-avatar :size="32" class="user-avatar">
              {{ userInitials }}
            </el-avatar>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon>
                  Profile
                </el-dropdown-item>
                <el-dropdown-item command="settings">
                  <el-icon><Setting /></el-icon>
                  Settings
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  Logout
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- Page Content -->
      <main class="page-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useFilesStore } from '@/stores/files'
import { useDeletedFilesStore } from '@/stores/deletedFiles'
import {
  Folder,
  Document,
  Expand,
  Fold,
  Refresh,
  Search,
  User,
  Setting,
  SwitchButton,
  Plus,
  Delete,
  UserFilled,
} from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { filesAPI } from '@/services/api'
import FileIcon from '@/components/FileIcon.vue'

const router = useRouter()
const authStore = useAuthStore()
const filesStore = useFilesStore()
const deletedFilesStore = useDeletedFilesStore()

// Sidebar state
const sidebarCollapsed = ref(false)
const searchQuery = ref('')
const treeRefreshKey = ref(0)

// Computed properties
const userInitials = computed(() => {
  if (!authStore.user) return ''
  const { first_name, last_name, username } = authStore.user
  if (first_name && last_name) {
    return `${first_name[0]}${last_name[0]}`.toUpperCase()
  }
  return username[0].toUpperCase()
})

const currentRoute = computed(() => router.currentRoute.value)
const currentDirectoryId = computed(() => {
  const parentId = currentRoute.value.query.parent_id
  return parentId ? Number(parentId) : null
})

const currentPath = computed(() => {
  // Extract current path from route or files store
  return ''
})

const directoryTree = computed(() => filesStore.directoryTree)
const isLoading = computed(() => filesStore.isLoading)
const deletedFilesCount = computed(() => deletedFilesStore.deletedFilesCount)

// Tree configuration
const treeProps = {
  children: 'children',
  label: 'name',
  isLeaf: (data: any) => data.item_type === 'file' && !data.is_virtual,
  hasChildren: (data: any) => data.item_type === 'directory' || data.is_virtual,
}

// Methods
const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

const refreshTree = async () => {
  treeRefreshKey.value++ // Increment key to force re-render
  await filesStore.fetchDirectoryTree()
}

const loadNode = async (node: any, resolve: (data: any[]) => void) => {
  if (node.level === 0) {
    // Root level - already loaded with virtual root node
    resolve(directoryTree.value)
  } else if (node.data.is_virtual && node.level === 1) {
    // Virtual root node - load actual root items (no parent_id)
    const response = await filesAPI.listChildren()
    resolve(response.data.children || [])
  } else {
    // Load children for this node
    const children = await filesStore.fetchTreeChildren(node.data.id)
    resolve(children)
  }
}

const showCreateDirectoryDialog = () => {
  ElMessageBox.prompt('Enter directory name:', 'Create Directory', {
    confirmButtonText: 'Create',
    cancelButtonText: 'Cancel',
    inputPattern: /^[^\/\\]+$/,
    inputErrorMessage: 'Directory name cannot contain slashes or backslashes',
  })
    .then(async ({ value }) => {
      if (value) {
        // Create directory at root level (no parent_id)
        const newDirectory = await filesStore.createDirectory(value)
        if (newDirectory) {
          ElMessage.success('Directory created successfully')
        }
      }
    })
    .catch(() => {
      // User cancelled
    })
}

const handleNodeClick = (data: any) => {
  if (data.is_virtual) {
    // Virtual root node - navigate to root files with explicit query params
    router.push({ name: 'Files', query: {} })
  } else if (data.item_type === 'directory') {
    // Navigate to directory using parent_id for proper navigation
    router.push({ name: 'Files', query: { parent_id: data.id } })
  } else {
    // Navigate to file details
    router.push({ name: 'FileDetails', params: { id: data.id } })
  }
}

// Highlight current directory in sidebar without changing tree state
const highlightCurrentDirectory = () => {
  // This method can be used to visually highlight the current directory
  // without expanding/collapsing nodes or changing the tree state
  console.log('Current directory ID from route:', currentDirectoryId.value)
}

const handleSearch = (value: string) => {
  if (value.trim()) {
    router.push({ name: 'Search', query: { q: value } })
  }
}

const handleUserCommand = (command: string) => {
  switch (command) {
    case 'profile':
      router.push('/profile')
      break
    case 'settings':
      router.push('/settings')
      break
    case 'logout':
      authStore.logout()
      router.push('/login')
      break
  }
}

const navigateToDustbin = () => {
  router.push('/deleted-files')
}



// Lifecycle
onMounted(async () => {
  await filesStore.fetchDirectoryTree()
  await deletedFilesStore.fetchDeletedFiles()
})

// Watch for route changes to update current path
watch(
  () => router.currentRoute.value,
  (route) => {
    // Update current path based on route
    highlightCurrentDirectory()
  },
  { immediate: true },
)
</script>

<style scoped>
.main-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  width: 100%;
}

.sidebar {
  width: 280px !important;
  background: #f5f7fa;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease, min-width 0.3s ease, max-width 0.3s ease;
  min-width: 280px;
  max-width: 280px;
}

.sidebar-collapsed {
  width: 60px !important;
  min-width: 60px !important;
  max-width: 60px !important;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #e4e7ed;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.dustbin-section {
  padding: 16px;
  border-top: 1px solid #e4e7ed;
  background: #fafafa;
}

.dustbin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.dustbin-header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #606266;
}

.dustbin-badge {
  margin-left: auto;
}

.dustbin-button {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #909399;
  font-size: 12px;
  padding: 4px 8px;
}

.dustbin-button:hover {
  color: #409eff;
}

.dustbin-button .el-icon {
  font-size: 14px;
}

.dustbin-collapsed {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 16px 8px;
}

.dustbin-badge-collapsed {
  display: flex;
  justify-content: center;
  align-items: center;
}

.dustbin-icon-button {
  color: #909399;
  padding: 8px;
  width: 44px;
  height: 44px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.dustbin-icon-button:hover {
  color: #409eff;
  background-color: #f0f9ff;
}

.dustbin-icon-button .el-icon {
  font-size: 18px;
}



.tree-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.tree-header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #606266;
}

.tree-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tree-actions .el-button {
  padding: 4px 8px;
  font-size: 12px;
}

.directory-tree {
  background: transparent;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}

.tree-node.virtual-root {
  font-weight: 600;
  color: #409eff;
}

.tree-node.virtual-root .node-icon {
  color: #409eff;
}

/* Highlight current directory */
:deep(.el-tree-node.is-current > .el-tree-node__content) {
  background-color: #f0f9ff;
  color: #409eff;
  font-weight: 600;
}

:deep(.el-tree-node.is-current > .el-tree-node__content .node-icon) {
  color: #409eff;
}

:deep(.el-tree-node.is-current > .el-tree-node__content .node-label) {
  color: #409eff;
  font-weight: 600;
}

.node-icon {
  color: #909399;
  font-size: 16px;
}

.node-label {
  font-size: 14px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}



.sidebar-toggle {
  color: #909399;
  transition: color 0.2s;
}

.sidebar-toggle:hover {
  color: #409eff;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0; /* Allow flex item to shrink below content size */
}

.top-nav {
  height: 60px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.nav-left {
  display: flex;
  align-items: center;
}

.nav-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.search-input {
  width: 300px;
}

.user-avatar {
  cursor: pointer;
  background: #409eff;
  color: #fff;
  font-weight: 600;
}

.page-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background: #fafafa;
}

/* Responsive */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    z-index: 1000;
    transform: translateX(-100%);
    width: 280px !important;
    min-width: 280px !important;
    max-width: 280px !important;
  }

  .sidebar.open {
    transform: translateX(0);
  }

  .sidebar-collapsed {
    width: 60px !important;
    min-width: 60px !important;
    max-width: 60px !important;
  }

  .search-input {
    width: 200px;
  }
}
</style>
