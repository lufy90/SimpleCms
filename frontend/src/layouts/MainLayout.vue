<template>
  <div class="main-layout">
    <!-- Sidebar -->
    <aside class="sidebar" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
      <div class="sidebar-header">
        <h3 v-if="!sidebarCollapsed" class="logo">
          <el-icon><Folder /></el-icon>
          File Manager
        </h3>
        <el-button
          v-else
          type="text"
          size="large"
          @click="toggleSidebar"
          class="sidebar-toggle"
        >
          <el-icon><Expand /></el-icon>
        </el-button>
      </div>

      <!-- Directory Tree -->
      <div class="sidebar-content">
        <div class="tree-header" v-if="!sidebarCollapsed">
          <h4>Directory Tree</h4>
          <el-button
            type="text"
            size="small"
            @click="refreshTree"
            :loading="isLoading"
          >
            <el-icon><Refresh /></el-icon>
          </el-button>
        </div>
        
        <el-tree
          :data="directoryTree"
          :props="treeProps"
          :expand-on-click-node="false"
          :default-expand-all="false"
          node-key="path"
          @node-click="handleNodeClick"
          class="directory-tree"
        >
          <template #default="{ node, data }">
            <div class="tree-node">
              <el-icon class="node-icon">
                <Folder v-if="data.item_type === 'directory'" />
                <Document v-else />
              </el-icon>
              <span class="node-label" :title="data.name">
                {{ data.name }}
              </span>
            </div>
          </template>
        </el-tree>
      </div>

      <!-- Sidebar Toggle Button -->
      <div class="sidebar-footer">
        <el-button
          type="text"
          size="large"
          @click="toggleSidebar"
          class="sidebar-toggle"
        >
          <el-icon v-if="sidebarCollapsed"><Expand /></el-icon>
          <el-icon v-else><Fold /></el-icon>
        </el-button>
      </div>
    </aside>

    <!-- Main Content -->
    <div class="main-content" :class="{ 'content-expanded': sidebarCollapsed }">
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
} from '@element-plus/icons-vue'

const router = useRouter()
const authStore = useAuthStore()
const filesStore = useFilesStore()

// Sidebar state
const sidebarCollapsed = ref(false)
const searchQuery = ref('')

// Computed properties
const userInitials = computed(() => {
  if (!authStore.user) return ''
  const { first_name, last_name, username } = authStore.user
  if (first_name && last_name) {
    return `${first_name[0]}${last_name[0]}`.toUpperCase()
  }
  return username[0].toUpperCase()
})

const currentPath = computed(() => {
  // Extract current path from route or files store
  return ''
})

const directoryTree = computed(() => filesStore.directoryTree)
const isLoading = computed(() => filesStore.isLoading)

// Tree configuration
const treeProps = {
  children: 'children',
  label: 'name',
}

// Methods
const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

const refreshTree = async () => {
  await filesStore.fetchDirectoryTree()
}

const handleNodeClick = (data: any) => {
  if (data.item_type === 'directory') {
    // Navigate to directory
    router.push({ name: 'Files', query: { path: data.path } })
  } else {
    // Navigate to file details
    router.push({ name: 'FileDetails', params: { id: data.id } })
  }
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

// Lifecycle
onMounted(async () => {
  await filesStore.fetchDirectoryTree()
})

// Watch for route changes to update current path
watch(
  () => router.currentRoute.value,
  (route) => {
    // Update current path based on route
  },
  { immediate: true }
)
</script>

<style scoped>
.main-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  width: 280px;
  background: #f5f7fa;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
}

.sidebar-collapsed {
  width: 60px;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #e4e7ed;
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

.directory-tree {
  background: transparent;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
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

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid #e4e7ed;
  display: flex;
  justify-content: center;
}

.sidebar-toggle {
  color: #909399;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  transition: margin-left 0.3s ease;
}

.content-expanded {
  margin-left: 0;
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
  }
  
  .sidebar.open {
    transform: translateX(0);
  }
  
  .search-input {
    width: 200px;
  }
}
</style>
