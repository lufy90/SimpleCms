<template>
  <div class="main-layout">
    <!-- Sidebar -->
    <aside
      class="sidebar"
      :class="{
        'sidebar-collapsed': sidebarCollapsed,
        'sidebar-open': !sidebarCollapsed,
        'sidebar-resizing': isResizing,
      }"
      :style="sidebarStyle"
    >
      <div class="sidebar-header">
        <div class="header-content">
          <h3 class="logo">
            <el-icon><Folder /></el-icon>
            {{ $t('files.fileManager') }}
          </h3>
          <el-button
            type="text"
            size="large"
            @click="toggleSidebar"
            class="sidebar-toggle"
            :title="$t('navigation.hideSidebar')"
          >
            <el-icon><Fold /></el-icon>
          </el-button>
        </div>
      </div>

      <!-- Directory Tree -->
      <div class="sidebar-content">
        <div class="tree-header">
          <h4>{{ $t('files.directoryTree') }}</h4>
          <div class="tree-actions">
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
            <div
              class="tree-node"
              :class="{
                'virtual-root':
                  data.is_virtual ||
                  data.is_home ||
                  data.space === 'shared_to_me' ||
                  data.space === 'group_spaces',
              }"
            >
              <FileIcon :file="data" :size="16" :show-thumbnail="true" />
              <span class="node-label" :title="treeNodeLabel(data)">
                {{ treeNodeLabel(data) }}
              </span>
            </div>
          </template>
        </el-tree>
      </div>

      <!-- Dustbin Section -->
      <div class="dustbin-section">
        <el-badge
          :value="deletedFilesCount"
          :hidden="deletedFilesCount === 0"
          class="dustbin-badge"
        >
          <el-button
            type="text"
            size="large"
            @click="navigateToDustbin"
            class="dustbin-button"
            :title="$t('navigation.deletedFiles')"
          >
            <el-icon><Delete /></el-icon>
            <span>{{ $t('navigation.deletedFiles') }}</span>
          </el-button>
        </el-badge>
      </div>

      <div
        v-if="!sidebarCollapsed"
        class="sidebar-resizer"
        @mousedown="startResize"
      />
    </aside>

    <!-- Main Content -->
    <div class="main-content">
      <!-- Top Navigation -->
      <header class="top-nav">
        <div class="nav-left">
          <el-button
            v-if="sidebarCollapsed"
            type="text"
            size="large"
            @click="toggleSidebar"
            class="sidebar-toggle sidebar-show-toggle"
            :title="$t('navigation.showSidebar')"
          >
            <el-icon><Expand /></el-icon>
          </el-button>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/files' }">{{
              $t('navigation.files')
            }}</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentPath">{{ currentPath }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="nav-right">
          <!-- Search -->
          <el-input
            v-model="searchQuery"
            :placeholder="$t('files.placeholders.searchFiles')"
            prefix-icon="Search"
            clearable
            @input="handleSearch"
            class="search-input"
          />

          <!-- Language Switcher -->
          <LanguageSwitcher />

          <!-- Theme Toggle -->
          <ThemeToggle />

          <!-- User Menu -->
          <el-dropdown @command="handleUserCommand">
            <el-avatar :size="32" class="user-avatar">
              {{ userInitials }}
            </el-avatar>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon>
                  {{ $t('navigation.profile') }}
                </el-dropdown-item>
                <el-dropdown-item command="settings">
                  <el-icon><Setting /></el-icon>
                  {{ $t('navigation.settings') }}
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  {{ $t('navigation.logout') }}
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
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { useFilesStore } from '@/stores/files'
import { useDeletedFilesStore } from '@/stores/deletedFiles'
import LanguageSwitcher from '@/components/LanguageSwitcher.vue'
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
  Delete,
  UserFilled,
} from '@element-plus/icons-vue'
import { filesAPI } from '@/services/api'
import FileIcon from '@/components/FileIcon.vue'
import ThemeToggle from '@/components/ThemeToggle.vue'

const router = useRouter()
const { t } = useI18n()
const authStore = useAuthStore()
const filesStore = useFilesStore()
const deletedFilesStore = useDeletedFilesStore()

const SIDEBAR_WIDTH_KEY = 'simplecms.sidebarWidth'
const SIDEBAR_WIDTH_DEFAULT = 280
const SIDEBAR_WIDTH_MIN = 180
const SIDEBAR_WIDTH_MAX = 600

const clampSidebarWidth = (width: number) => {
  const maxWidth = Math.min(SIDEBAR_WIDTH_MAX, Math.floor(window.innerWidth * 0.45))
  return Math.min(Math.max(width, SIDEBAR_WIDTH_MIN), Math.max(SIDEBAR_WIDTH_MIN, maxWidth))
}

const loadSidebarWidth = () => {
  const stored = localStorage.getItem(SIDEBAR_WIDTH_KEY)
  if (!stored) return SIDEBAR_WIDTH_DEFAULT
  const parsed = Number.parseInt(stored, 10)
  if (Number.isNaN(parsed)) return SIDEBAR_WIDTH_DEFAULT
  return clampSidebarWidth(parsed)
}

// Sidebar state
const sidebarCollapsed = ref(false)
const sidebarWidth = ref(loadSidebarWidth())
const isResizing = ref(false)
let resizeStartX = 0
let resizeStartWidth = 0

const sidebarStyle = computed(() => {
  if (sidebarCollapsed.value) {
    return { width: '0px', minWidth: '0px', maxWidth: '0px' }
  }
  const width = `${sidebarWidth.value}px`
  return { width, minWidth: width, maxWidth: width }
})

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
  if (currentRoute.value.name === 'Files') {
    const parentId = currentRoute.value.query.parent_id
    if (parentId) {
      return String(parentId)
    }
    const space = currentRoute.value.query.space
    if (space === 'shared_to_me') {
      return 'shared_to_me'
    }
    if (space === 'group_spaces') {
      return 'group_spaces'
    }
    return authStore.user?.home_id || filesStore.directoryTree[0]?.id || null
  }

  const paramsId = currentRoute.value.params.id
  return paramsId ? String(paramsId) : null
})

const treeNodeLabel = (data: any) => {
  if (data.is_home) return t('files.myFiles')
  if (data.space === 'shared_to_me' || data.id === 'shared_to_me') return t('files.sharedWithMe')
  if (data.space === 'group_spaces' || data.id === 'group_spaces') return t('files.groupSpaces')
  return data.name
}

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

const onResizeMove = (event: MouseEvent) => {
  if (!isResizing.value) return
  const deltaX = event.clientX - resizeStartX
  sidebarWidth.value = clampSidebarWidth(resizeStartWidth + deltaX)
}

const stopResize = () => {
  if (!isResizing.value) return
  isResizing.value = false
  document.body.classList.remove('sidebar-resizing')
  document.removeEventListener('mousemove', onResizeMove)
  document.removeEventListener('mouseup', stopResize)
  localStorage.setItem(SIDEBAR_WIDTH_KEY, String(sidebarWidth.value))
}

const startResize = (event: MouseEvent) => {
  event.preventDefault()
  isResizing.value = true
  resizeStartX = event.clientX
  resizeStartWidth = sidebarWidth.value
  document.body.classList.add('sidebar-resizing')
  document.addEventListener('mousemove', onResizeMove)
  document.addEventListener('mouseup', stopResize)
}

const refreshTree = async () => {
  treeRefreshKey.value++ // Increment key to force re-render
  await filesStore.fetchDirectoryTree()
}

const loadNode = async (node: any, resolve: (data: any[]) => void) => {
  if (node.level === 0) {
    resolve(directoryTree.value)
  } else if (node.data.space === 'shared_to_me' || node.data.id === 'shared_to_me') {
    const response = await filesAPI.listChildren(undefined, 'shared_to_me')
    resolve(response.data.children || [])
  } else if (node.data.space === 'group_spaces' || node.data.id === 'group_spaces') {
    const groups = authStore.user?.groups || []
    resolve(
      groups
        .filter((g) => g.space_id)
        .map((g) => ({
          id: g.space_id as string,
          name: g.name,
          item_type: 'directory',
          is_group_space: true,
        })),
    )
  } else if (node.data.is_home || (node.data.is_virtual && !node.data.space)) {
    const response = await filesAPI.listChildren()
    resolve(response.data.children || [])
  } else {
    const children = await filesStore.fetchTreeChildren(node.data.id)
    resolve(children)
  }
}

const handleNodeClick = (data: any) => {
  if (data.space === 'group_spaces' || data.id === 'group_spaces') {
    router.push({ name: 'Files', query: { space: 'group_spaces' } })
  } else if (data.space === 'shared_to_me' || data.id === 'shared_to_me') {
    router.push({ name: 'Files', query: { space: 'shared_to_me' } })
  } else if (data.is_home || (data.is_virtual && !data.space && !data.is_group_space)) {
    router.push({ name: 'Files', query: {} })
  } else if (data.item_type === 'directory') {
    router.push({ name: 'Files', query: { parent_id: data.id } })
  } else {
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

const handleUserCommand = async (command: string) => {
  switch (command) {
    case 'profile':
      router.push('/profile')
      break
    case 'settings':
      router.push('/settings')
      break
    case 'logout':
      await authStore.logout()
      await router.push('/login')
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

onUnmounted(() => {
  stopResize()
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
  position: relative;
  width: 280px;
  background: #f5f7fa;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  transition:
    width 0.3s ease,
    min-width 0.3s ease,
    max-width 0.3s ease,
    opacity 0.2s ease,
    border-color 0.2s ease;
  flex-shrink: 0;
  overflow: hidden;
}

.sidebar-collapsed {
  width: 0 !important;
  min-width: 0 !important;
  max-width: 0 !important;
  opacity: 0;
  border-right: none;
  pointer-events: none;
}

.sidebar-resizing {
  transition: none;
}

.sidebar-resizer {
  position: absolute;
  top: 0;
  right: -3px;
  width: 6px;
  height: 100%;
  cursor: col-resize;
  z-index: 10;
}

.sidebar-resizer:hover,
.sidebar-resizing .sidebar-resizer {
  background: rgba(64, 158, 255, 0.35);
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #e4e7ed;
  min-width: 180px;
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
  white-space: nowrap;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  min-width: 180px;
}

.dustbin-section {
  padding: 12px 16px;
  border-top: 1px solid #e4e7ed;
  background: #fafafa;
  display: flex;
  justify-content: flex-start;
  align-items: center;
  min-width: 180px;
}

.dustbin-badge {
  display: flex;
  align-items: center;
}

.dustbin-button {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #909399;
  font-size: 14px;
  padding: 8px 12px;
}

.dustbin-button:hover {
  color: var(--el-color-primary);
  background-color: var(--el-color-primary-light-9);
}

.dustbin-button .el-icon {
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
  background-color: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  font-weight: 600;
}

:deep(.el-tree-node.is-current > .el-tree-node__content .node-icon) {
  color: var(--el-color-primary);
}

:deep(.el-tree-node.is-current > .el-tree-node__content .node-label) {
  color: var(--el-color-primary);
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

.sidebar-toggle .el-icon {
  font-size: 22px;
}

.sidebar-toggle:hover {
  color: #409eff;
}

.sidebar-show-toggle {
  margin-right: 8px;
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
  gap: 4px;
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
    bottom: 0;
    z-index: 1000;
    height: 100vh;
    transform: translateX(-100%);
    opacity: 1;
    pointer-events: auto;
    box-shadow: 2px 0 8px rgba(0, 0, 0, 0.15);
  }

  .sidebar.sidebar-open {
    transform: translateX(0);
  }

  .sidebar.sidebar-collapsed {
    width: 280px !important;
    min-width: 280px !important;
    max-width: 80vw !important;
    opacity: 1;
    border-right: 1px solid #e4e7ed;
    pointer-events: none;
    transform: translateX(-100%);
  }

  .sidebar-resizer {
    display: none;
  }

  .search-input {
    width: 200px;
  }
}

/* Dark mode styles */
.dark .sidebar {
  background: #1f1f1f;
  border-right-color: #3c3c3c;
}

.dark .sidebar-header {
  border-bottom-color: #3c3c3c;
}

.dark .logo {
  color: #e5e5e5;
}

.dark .tree-header h4 {
  color: #e5e5e5;
}

.dark .dustbin-section {
  background: #2a2a2a;
  border-top-color: #3c3c3c;
}

.dark .dustbin-button {
  color: #a8a8a8;
}

.dark .dustbin-button:hover {
  color: #409eff;
  background-color: #2a2a2a;
}

.dark .node-label {
  color: #e5e5e5;
}

.dark .sidebar-toggle {
  color: #a8a8a8;
}

.dark .sidebar-toggle:hover {
  color: #409eff;
}

.dark .top-nav {
  background: #1f1f1f;
  border-bottom-color: #3c3c3c;
}

.dark .page-content {
  background: #141414;
}
</style>

<style>
body.sidebar-resizing {
  cursor: col-resize;
  user-select: none;
}
</style>
