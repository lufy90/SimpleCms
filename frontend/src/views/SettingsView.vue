<template>
  <div class="settings-container">
    <div class="settings-header">
      <h1>{{ $t('settings.title') }}</h1>
      <p>{{ $t('settings.subtitle') }}</p>
    </div>

    <el-tabs v-model="activeTab" class="settings-tabs">
      <!-- Theme Settings Tab -->
      <el-tab-pane :label="$t('settings.tabs.themeSettings')" name="theme">
        <div class="tab-content">
          <div class="section-header">
            <h2>{{ $t('settings.theme.appearance') }}</h2>
          </div>

          <div class="theme-settings">
            <div class="setting-item">
              <div class="setting-label">
                <h3>{{ $t('settings.theme.theme') }}</h3>
                <p>{{ $t('settings.theme.chooseTheme') }}</p>
              </div>
              <div class="setting-control">
                <el-radio-group v-model="themeStore.theme" @change="handleThemeChange">
                  <el-radio-button label="light">
                    <el-icon><Sunny /></el-icon>
                    {{ $t('settings.theme.light') }}
                  </el-radio-button>
                  <el-radio-button label="dark">
                    <el-icon><Moon /></el-icon>
                    {{ $t('settings.theme.dark') }}
                  </el-radio-button>
                  <el-radio-button label="auto">
                    <el-icon><Monitor /></el-icon>
                    {{ $t('settings.theme.auto') }}
                  </el-radio-button>
                </el-radio-group>
              </div>
            </div>

            <div class="theme-preview">
              <h4>{{ $t('settings.theme.preview') }}</h4>
              <div class="preview-container" :class="{ 'dark-preview': themeStore.isDarkMode }">
                <div class="preview-sidebar">
                  <div class="preview-header">{{ $t('settings.theme.fileManager') }}</div>
                  <div class="preview-tree">
                    <div class="preview-item">📁 {{ $t('settings.theme.documents') }}</div>
                    <div class="preview-item">📁 {{ $t('settings.theme.images') }}</div>
                    <div class="preview-item">📄 {{ $t('settings.theme.sampleFile') }}.txt</div>
                  </div>
                </div>
                <div class="preview-main">
                  <div class="preview-nav">{{ $t('navigation.files') }} / {{ $t('settings.theme.documents') }}</div>
                  <div class="preview-content">
                    <div class="preview-card">{{ $t('settings.theme.sampleFile') }} 1</div>
                    <div class="preview-card">{{ $t('settings.theme.sampleFile') }} 2</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- User Management Tab -->
      <el-tab-pane :label="$t('settings.tabs.userManagement')" name="users">
        <div class="tab-content">
          <div class="section-header">
            <h2>{{ $t('settings.users.title') }}</h2>
            <el-button type="primary" @click="showCreateUserDialog = true">
              <el-icon><Plus /></el-icon>
              {{ $t('settings.users.addUser') }}
            </el-button>
          </div>

          <!-- User Search and Filter -->
          <div class="search-section">
            <el-input
              v-model="userSearchQuery"
              :placeholder="$t('settings.users.searchUsers')"
              @input="searchUsers"
              clearable
              class="search-input"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </div>

          <!-- Users Table -->
          <el-table :data="filteredUsers" v-loading="usersLoading" class="users-table" stripe>
            <el-table-column prop="username" :label="$t('settings.users.username')" width="150" />
            <el-table-column prop="email" :label="$t('settings.users.email')" width="200" />
            <el-table-column prop="first_name" :label="$t('settings.users.firstName')" width="120" />
            <el-table-column prop="last_name" :label="$t('settings.users.lastName')" width="120" />
            <el-table-column :label="$t('settings.users.groups')" width="200">
              <template #default="{ row }">
                <el-tag v-for="group in row.groups" :key="group.id" size="small" class="group-tag">
                  {{ group.name }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('settings.users.actions')" width="150">
              <template #default="{ row }">
                <el-button size="small" @click="editUser(row)" type="primary" link>
                  {{ $t('settings.users.edit') }}
                </el-button>
                <el-button size="small" @click="deleteUser(row)" type="danger" link>
                  {{ $t('settings.users.delete') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- Group Management Tab -->
      <el-tab-pane :label="$t('settings.tabs.groupManagement')" name="groups">
        <div class="tab-content">
          <div class="section-header">
            <h2>{{ $t('settings.groups.title') }}</h2>
            <el-button type="primary" @click="showCreateGroupDialog = true">
              <el-icon><Plus /></el-icon>
              {{ $t('settings.groups.addGroup') }}
            </el-button>
          </div>

          <!-- Group Search and Filter -->
          <div class="search-section">
            <el-input
              v-model="groupSearchQuery"
              :placeholder="$t('settings.groups.searchGroups')"
              @input="searchGroups"
              clearable
              class="search-input"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </div>

          <!-- Groups Table -->
          <el-table :data="filteredGroups" v-loading="groupsLoading" class="groups-table" stripe>
            <el-table-column prop="name" :label="$t('settings.groups.groupName')" width="200" />
            <el-table-column :label="$t('settings.groups.members')" width="300">
              <template #default="{ row }">
                <span v-if="row.members && row.members.length > 0">
                  {{ row.members.length }} {{ $t('settings.groups.memberCount') }}
                </span>
                <span v-else class="no-members">{{ $t('settings.groups.noMembers') }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="$t('settings.groups.actions')" width="150">
              <template #default="{ row }">
                <el-button size="small" @click="editGroup(row)" type="primary" link>
                  {{ $t('settings.groups.edit') }}
                </el-button>
                <el-button size="small" @click="deleteGroup(row)" type="danger" link>
                  {{ $t('settings.groups.delete') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- Create/Edit User Dialog -->
    <el-dialog
      v-model="showCreateUserDialog"
      :title="editingUser ? $t('settings.users.editUser') : $t('settings.users.createUser')"
      width="500px"
    >
      <el-form ref="userFormRef" :model="userForm" :rules="userFormRules" label-width="100px">
        <el-form-item :label="$t('settings.users.username')" prop="username">
          <el-input v-model="userForm.username" />
        </el-form-item>
        <el-form-item :label="$t('settings.users.email')" prop="email">
          <el-input v-model="userForm.email" type="email" />
        </el-form-item>
        <el-form-item :label="$t('settings.users.firstName')" prop="first_name">
          <el-input v-model="userForm.first_name" />
        </el-form-item>
        <el-form-item :label="$t('settings.users.lastName')" prop="last_name">
          <el-input v-model="userForm.last_name" />
        </el-form-item>
        <el-form-item :label="editingUser ? $t('settings.users.newPasswordOptional') : $t('settings.users.password')" prop="password">
          <el-input
            v-model="userForm.password"
            type="password"
            show-password
            :placeholder="editingUser ? $t('settings.users.leaveBlankToKeep') : $t('settings.users.enterPassword')"
          />
        </el-form-item>
        <el-form-item :label="$t('settings.users.groups')" prop="groups">
          <el-select
            v-model="userForm.groups"
            multiple
            :placeholder="$t('settings.users.selectGroups')"
            style="width: 100%"
          >
            <el-option
              v-for="group in availableGroups"
              :key="group.id"
              :label="group.name"
              :value="group.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateUserDialog = false">{{ $t('settings.users.cancel') }}</el-button>
        <el-button type="primary" @click="saveUser">{{ $t('settings.users.save') }}</el-button>
      </template>
    </el-dialog>

    <!-- Create/Edit Group Dialog -->
    <el-dialog
      v-model="showCreateGroupDialog"
      :title="editingGroup ? $t('settings.groups.editGroup') : $t('settings.groups.createGroup')"
      width="500px"
    >
      <el-form ref="groupFormRef" :model="groupForm" :rules="groupFormRules" label-width="100px">
        <el-form-item :label="$t('settings.groups.groupName')" prop="name">
          <el-input v-model="groupForm.name" />
        </el-form-item>
        <el-form-item :label="$t('settings.groups.description')" prop="description">
          <el-input v-model="groupForm.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item :label="$t('settings.groups.members')" prop="members">
          <el-select
            v-model="groupForm.members"
            multiple
            :placeholder="$t('settings.groups.selectMembers')"
            style="width: 100%"
          >
            <el-option
              v-for="user in availableUsers"
              :key="user.id"
              :label="user.username"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateGroupDialog = false">{{ $t('settings.groups.cancel') }}</el-button>
        <el-button type="primary" @click="saveGroup">{{ $t('settings.groups.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Sunny, Moon, Monitor } from '@element-plus/icons-vue'
import { usersAPI, groupsAPI } from '@/services/api'
import { useThemeStore } from '@/stores/theme'

const { t } = useI18n()

// Types
interface User {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  groups: { id: number; name: string }[]
}

interface Group {
  id: number
  name: string
  description?: string
  members: number[]
}

// Reactive data
const activeTab = ref('users')
const usersLoading = ref(false)
const groupsLoading = ref(false)

// Theme store
const themeStore = useThemeStore()

// User management
const users = ref<User[]>([])
const filteredUsers = ref<User[]>([])
const userSearchQuery = ref('')
const showCreateUserDialog = ref(false)
const editingUser = ref<User | null>(null)
const userFormRef = ref()

const userForm = reactive({
  username: '',
  email: '',
  first_name: '',
  last_name: '',
  password: '',
  groups: [] as number[],
})

const userFormRules = computed(() => ({
  username: [{ required: true, message: t('validation.usernameRequired'), trigger: 'blur' }],
  email: [
    { required: true, message: t('validation.emailRequired'), trigger: 'blur' },
    { type: 'email', message: t('validation.emailInvalid'), trigger: 'blur' },
  ],
  password: editingUser.value
    ? [
        // For editing: password is optional, but if provided, must be at least 6 characters
        { min: 6, message: t('validation.passwordMinLength'), trigger: 'blur' },
      ]
    : [
        // For creating: password is required
        { required: true, message: t('validation.passwordRequired'), trigger: 'blur' },
        { min: 6, message: t('validation.passwordMinLength'), trigger: 'blur' },
      ],
}))

// Group management
const groups = ref<Group[]>([])
const filteredGroups = ref<Group[]>([])
const groupSearchQuery = ref('')
const showCreateGroupDialog = ref(false)
const editingGroup = ref<Group | null>(null)
const groupFormRef = ref()

const groupForm = reactive({
  name: '',
  description: '',
  members: [] as number[],
})

const groupFormRules = {
  name: [{ required: true, message: t('validation.groupNameRequired'), trigger: 'blur' }],
}

// Computed properties
const availableGroups = computed(() => groups.value)
const availableUsers = computed(() => users.value)

// Methods
const handleThemeChange = (theme: string) => {
  themeStore.setTheme(theme as 'light' | 'dark' | 'auto')
}

const loadUsers = async () => {
  try {
    usersLoading.value = true
    const response = await usersAPI.list()
    users.value = response.data.results || response.data
    filteredUsers.value = users.value
  } catch (error) {
    console.error('Failed to load users:', error)
    ElMessage.error(t('settings.users.failedToLoadUsers'))

    // Fallback to mock data for development
    users.value = [
      {
        id: 1,
        username: 'admin',
        email: 'admin@example.com',
        first_name: 'Admin',
        last_name: 'User',
        groups: [{ id: 1, name: 'Administrators' }],
      },
      {
        id: 2,
        username: 'user1',
        email: 'user1@example.com',
        first_name: 'John',
        last_name: 'Doe',
        groups: [{ id: 2, name: 'Users' }],
      },
    ]
    filteredUsers.value = users.value
  } finally {
    usersLoading.value = false
  }
}

const loadGroups = async () => {
  try {
    groupsLoading.value = true
    const response = await groupsAPI.list()
    groups.value = response.data.results || response.data
    filteredGroups.value = groups.value
  } catch (error) {
    console.error('Failed to load groups:', error)
    ElMessage.error(t('settings.groups.failedToLoadGroups'))

    // Fallback to mock data for development
    groups.value = [
      {
        id: 1,
        name: 'Administrators',
        description: 'System administrators',
        members: [1],
      },
      {
        id: 2,
        name: 'Users',
        description: 'Regular users',
        members: [2],
      },
    ]
    filteredGroups.value = groups.value
  } finally {
    groupsLoading.value = false
  }
}

const searchUsers = () => {
  if (!userSearchQuery.value) {
    filteredUsers.value = users.value
    return
  }

  const query = userSearchQuery.value.toLowerCase()
  filteredUsers.value = users.value.filter(
    (user) =>
      user.username.toLowerCase().includes(query) ||
      user.email.toLowerCase().includes(query) ||
      user.first_name.toLowerCase().includes(query) ||
      user.last_name.toLowerCase().includes(query),
  )
}

const searchGroups = () => {
  if (!groupSearchQuery.value) {
    filteredGroups.value = groups.value
    return
  }

  const query = groupSearchQuery.value.toLowerCase()
  filteredGroups.value = groups.value.filter((group) => group.name.toLowerCase().includes(query))
}

const editUser = (user: User) => {
  editingUser.value = user
  userForm.username = user.username
  userForm.email = user.email
  userForm.first_name = user.first_name
  userForm.last_name = user.last_name
  userForm.groups = user.groups.map((g: any) => g.id)
  userForm.password = ''
  showCreateUserDialog.value = true
}

const deleteUser = async (user: User) => {
  try {
    await ElMessageBox.confirm(
      t('settings.users.confirmDelete', { username: user.username }),
      t('common.confirmDelete'),
      {
        confirmButtonText: t('common.delete'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
      },
    )

    await usersAPI.delete(user.id)

    ElMessage.success(t('settings.users.userDeletedSuccessfully'))
    loadUsers()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('settings.users.failedToDeleteUser'))
    }
  }
}

const saveUser = async () => {
  try {
    await userFormRef.value.validate()

    // Prepare data for API call
    const userData = { ...userForm }

    // For updates, only include password if it's provided
    if (editingUser.value && !userData.password) {
      delete (userData as any).password
    }

    if (editingUser.value) {
      await usersAPI.update(editingUser.value.id, userData)
    } else {
      await usersAPI.create(userData)
    }

    ElMessage.success(editingUser.value ? t('settings.users.userUpdatedSuccessfully') : t('settings.users.userCreatedSuccessfully'))
    showCreateUserDialog.value = false
    resetUserForm()
    loadUsers()
  } catch (error) {
    console.error('Failed to save user:', error)
    ElMessage.error(t('settings.users.failedToSaveUser'))
  }
}

const resetUserForm = () => {
  editingUser.value = null
  userForm.username = ''
  userForm.email = ''
  userForm.first_name = ''
  userForm.last_name = ''
  userForm.password = ''
  userForm.groups = []
}

const editGroup = (group: Group) => {
  editingGroup.value = group
  groupForm.name = group.name
  groupForm.description = group.description || ''
  groupForm.members = group.members || []
  showCreateGroupDialog.value = true
}

const deleteGroup = async (group: Group) => {
  try {
    await ElMessageBox.confirm(
      t('settings.groups.confirmDelete', { name: group.name }),
      t('common.confirmDelete'),
      {
        confirmButtonText: t('common.delete'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
      },
    )

    await groupsAPI.delete(group.id)

    ElMessage.success(t('settings.groups.groupDeletedSuccessfully'))
    loadGroups()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('settings.groups.failedToDeleteGroup'))
    }
  }
}

const saveGroup = async () => {
  try {
    await groupFormRef.value.validate()

    if (editingGroup.value) {
      await groupsAPI.update(editingGroup.value.id, groupForm)
    } else {
      await groupsAPI.create(groupForm)
    }

    ElMessage.success(
      editingGroup.value ? t('settings.groups.groupUpdatedSuccessfully') : t('settings.groups.groupCreatedSuccessfully'),
    )
    showCreateGroupDialog.value = false
    resetGroupForm()
    loadGroups()
  } catch (error) {
    console.error('Failed to save group:', error)
    ElMessage.error(t('settings.groups.failedToSaveGroup'))
  }
}

const resetGroupForm = () => {
  editingGroup.value = null
  groupForm.name = ''
  groupForm.description = ''
  groupForm.members = []
}

// Lifecycle
onMounted(() => {
  loadUsers()
  loadGroups()
})
</script>

<style scoped>
.settings-container {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.settings-header {
  margin-bottom: 24px;
}

.settings-header h1 {
  margin: 0 0 8px 0;
  color: #303133;
}

.settings-header p {
  margin: 0;
  color: #606266;
}

.settings-tabs {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.tab-content {
  padding: 24px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.section-header h2 {
  margin: 0;
  color: #303133;
}

.search-section {
  margin-bottom: 24px;
}

.search-input {
  max-width: 400px;
}

.users-table,
.groups-table {
  margin-top: 16px;
}

.group-tag {
  margin-right: 8px;
  margin-bottom: 4px;
}

.no-members {
  color: #909399;
  font-style: italic;
}

/* Theme settings styles */
.theme-settings {
  max-width: 800px;
}

.setting-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px 0;
  border-bottom: 1px solid #e4e7ed;
}

.setting-item:last-child {
  border-bottom: none;
}

.setting-label h3 {
  margin: 0 0 8px 0;
  color: #303133;
  font-size: 16px;
}

.setting-label p {
  margin: 0;
  color: #606266;
  font-size: 14px;
}

.setting-control {
  flex-shrink: 0;
}

.theme-preview {
  margin-top: 32px;
}

.theme-preview h4 {
  margin: 0 0 16px 0;
  color: #303133;
  font-size: 16px;
}

.preview-container {
  display: flex;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
  height: 200px;
}

.preview-sidebar {
  width: 200px;
  background: #f5f7fa;
  border-right: 1px solid #e4e7ed;
}

.preview-header {
  padding: 12px 16px;
  background: #f0f2f5;
  border-bottom: 1px solid #e4e7ed;
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

.preview-tree {
  padding: 8px 0;
}

.preview-item {
  padding: 6px 16px;
  font-size: 13px;
  color: #606266;
  cursor: pointer;
}

.preview-item:hover {
  background: #f0f9ff;
  color: #409eff;
}

.preview-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.preview-nav {
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  font-size: 14px;
  color: #303133;
}

.preview-content {
  flex: 1;
  padding: 16px;
  display: flex;
  gap: 12px;
}

.preview-card {
  width: 120px;
  height: 80px;
  background: #f8f9fa;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #606266;
}

/* Dark preview styles */
.dark-preview {
  background: #1f1f1f;
  border-color: #3c3c3c;
}

.dark-preview .preview-sidebar {
  background: #2a2a2a;
  border-right-color: #3c3c3c;
}

.dark-preview .preview-header {
  background: #1f1f1f;
  border-bottom-color: #3c3c3c;
  color: #e5e5e5;
}

.dark-preview .preview-item {
  color: #a8a8a8;
}

.dark-preview .preview-item:hover {
  background: #2a2a2a;
  color: #409eff;
}

.dark-preview .preview-nav {
  background: #1f1f1f;
  border-bottom-color: #3c3c3c;
  color: #e5e5e5;
}

.dark-preview .preview-card {
  background: #2a2a2a;
  border-color: #3c3c3c;
  color: #a8a8a8;
}

/* Dark mode styles for settings */
.dark .settings-header h1 {
  color: #e5e5e5;
}

.dark .settings-header p {
  color: #a8a8a8;
}

.dark .setting-label h3 {
  color: #e5e5e5;
}

.dark .setting-label p {
  color: #a8a8a8;
}

.dark .setting-item {
  border-bottom-color: #3c3c3c;
}

.dark .theme-preview h4 {
  color: #e5e5e5;
}
</style>
