<template>
  <el-dialog
    v-model="dialogVisible"
    :title="`Share: ${file?.name}`"
    width="700px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div class="share-dialog-content">
      <!-- Current Sharing Status -->
      <div class="current-sharing-section">
        <h4>Current Sharing</h4>
        <div class="current-sharing-list">
          <div v-if="currentPermissions.length === 0" class="no-sharing">
            <el-empty description="No users or groups have access to this file" />
          </div>
          <div v-else class="permission-list">
            <div
              v-for="permission in currentPermissions"
              :key="permission.id"
              class="permission-item"
            >
              <div class="permission-info">
                <div class="target-info">
                  <el-icon v-if="permission.user" color="#409eff">
                    <User />
                  </el-icon>
                  <el-icon v-else color="#67c23a">
                    <UserFilled />
                  </el-icon>
                  <span class="target-name">
                    {{ permission.user ? permission.user.username : permission.group?.name }}
                  </span>
                  <el-tag size="small" :type="getPermissionTagType(permission.permission_type)">
                    {{ permission.permission_type }}
                  </el-tag>
                </div>
                <div class="permission-meta">
                  <span class="granted-by">Granted by {{ permission.granted_by.username }}</span>
                  <span class="granted-at">{{ formatDate(permission.granted_at) }}</span>
                  <span v-if="permission.expires_at" class="expires-at">
                    Expires: {{ formatDate(permission.expires_at) }}
                  </span>
                </div>
              </div>
              <div class="permission-actions">
                <el-button
                  size="small"
                  type="danger"
                  @click="revokePermission(permission.id)"
                  :loading="revokingPermission === permission.id"
                >
                  <el-icon><Delete /></el-icon>
                  Revoke
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Add New Sharing -->
      <div class="add-sharing-section">
        <h4>Share with New User or Group</h4>
        <el-form :model="shareForm" label-width="120px" class="share-form">
          <el-form-item label="Share Type">
            <el-radio-group v-model="shareForm.shareType">
              <el-radio label="user">User</el-radio>
              <el-radio label="group">Group</el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="Select Target">
            <el-select
              v-if="shareForm.shareType === 'user'"
              v-model="shareForm.targetId"
              placeholder="Select user"
              filterable
              remote
              :remote-method="searchUsers"
              :loading="searchingUsers"
              style="width: 100%"
            >
              <el-option
                v-for="user in availableUsers"
                :key="user.id"
                :label="`${user.username} (${user.email})`"
                :value="user.id"
              />
            </el-select>
            <el-select
              v-else
              v-model="shareForm.targetId"
              placeholder="Select group"
              filterable
              remote
              :remote-method="searchGroups"
              :loading="searchingGroups"
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

          <el-form-item label="Permissions">
            <el-checkbox-group v-model="shareForm.permissions">
              <el-checkbox label="read">Read</el-checkbox>
              <el-checkbox label="write">Write</el-checkbox>
              <el-checkbox label="delete">Delete</el-checkbox>
              <el-checkbox label="share">Share</el-checkbox>
              <el-checkbox label="admin">Admin</el-checkbox>
            </el-checkbox-group>
          </el-form-item>

          <el-form-item label="Expires At">
            <el-date-picker
              v-model="shareForm.expiresAt"
              type="datetime"
              placeholder="No expiration (optional)"
              style="width: 100%"
              :disabled-date="disabledDate"
            />
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              @click="shareFile"
              :loading="sharing"
              :disabled="!canShare"
            >
              <el-icon><Share /></el-icon>
              Share File
            </el-button>
            <el-button @click="resetForm">Reset</el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { User, UserFilled, Share, Delete } from '@element-plus/icons-vue'
import { permissionsAPI } from '@/services/api'
import type { FileSystemItem } from '@/stores/files'

interface Permission {
  id: number
  file: number
  user?: {
    id: number
    username: string
    email: string
  }
  group?: {
    id: number
    name: string
  }
  permission_type: string
  granted_by: {
    id: number
    username: string
  }
  granted_at: string
  expires_at?: string
  is_active: boolean
}

interface User {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
}

interface Group {
  id: number
  name: string
}

interface ShareForm {
  shareType: 'user' | 'group'
  targetId: number | null
  permissions: string[]
  expiresAt: string | null
}

const props = defineProps<{
  visible: boolean
  file: FileSystemItem | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'permissions-updated': []
}>()

// Reactive data
const dialogVisible = ref(false)
const currentPermissions = ref<Permission[]>([])
const availableUsers = ref<User[]>([])
const availableGroups = ref<Group[]>([])
const searchingUsers = ref(false)
const searchingGroups = ref(false)
const sharing = ref(false)
const revokingPermission = ref<number | null>(null)

const shareForm = ref<ShareForm>({
  shareType: 'user',
  targetId: null,
  permissions: ['read'],
  expiresAt: null
})

// Computed properties
const canShare = computed(() => {
  return shareForm.value.targetId && shareForm.value.permissions.length > 0
})

// Watch for dialog visibility changes
watch(() => props.visible, (newVal) => {
  dialogVisible.value = newVal
  if (newVal && props.file) {
    loadCurrentPermissions()
  }
})

watch(dialogVisible, (newVal) => {
  emit('update:visible', newVal)
  if (!newVal) {
    resetForm()
  }
})

// Methods
const loadCurrentPermissions = async () => {
  if (!props.file) return
  
  try {
    const response = await permissionsAPI.list({ file: props.file.id })
    currentPermissions.value = response.data.results || response.data || []
  } catch (error) {
    console.error('Failed to load permissions:', error)
    ElMessage.error('Failed to load current permissions')
  }
}

const searchUsers = async (query: string) => {
  if (query.length < 2) return
  
  searchingUsers.value = true
  try {
    const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8002'}/api/users/search/?q=${query}`, {
      headers: {
        'Authorization': `Bearer ${document.cookie.split('; ').find(row => row.startsWith('access_token='))?.split('=')[1]}`
      }
    })
    if (response.ok) {
      const data = await response.json()
      availableUsers.value = data.results || data
    }
  } catch (error) {
    console.error('Failed to search users:', error)
  } finally {
    searchingUsers.value = false
  }
}

const searchGroups = async (query: string) => {
  if (query.length < 2) return
  
  searchingGroups.value = true
  try {
    const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8002'}/api/groups/search/?q=${query}`, {
      headers: {
        'Authorization': `Bearer ${document.cookie.split('; ').find(row => row.startsWith('access_token='))?.split('=')[1]}`
      }
    })
    if (response.ok) {
      const data = await response.json()
      availableGroups.value = data.results || data
    }
  } catch (error) {
    console.error('Failed to search groups:', error)
  } finally {
    searchingGroups.value = false
  }
}

const shareFile = async () => {
  if (!props.file || !shareForm.value.targetId) return
  
  sharing.value = true
  try {
    // Create permissions for each selected permission type
    const permissionPromises = shareForm.value.permissions.map(permissionType => {
      const permissionData = {
        file: props.file!.id,
        permission_type: permissionType,
        expires_at: shareForm.value.expiresAt || undefined
      }
      
      if (shareForm.value.shareType === 'user') {
        return permissionsAPI.create({
          ...permissionData,
          user: shareForm.value.targetId!
        })
      } else {
        return permissionsAPI.create({
          ...permissionData,
          group: shareForm.value.targetId!
        })
      }
    })
    
    await Promise.all(permissionPromises)
    
    ElMessage.success('File shared successfully')
    await loadCurrentPermissions()
    emit('permissions-updated')
    resetForm()
  } catch (error) {
    console.error('Failed to share file:', error)
    ElMessage.error('Failed to share file')
  } finally {
    sharing.value = false
  }
}

const revokePermission = async (permissionId: number) => {
  try {
    await ElMessageBox.confirm(
      'Are you sure you want to revoke this permission?',
      'Confirm Revocation',
      {
        confirmButtonText: 'Revoke',
        cancelButtonText: 'Cancel',
        type: 'warning'
      }
    )
    
    revokingPermission.value = permissionId
    await permissionsAPI.delete(permissionId)
    
    ElMessage.success('Permission revoked successfully')
    await loadCurrentPermissions()
    emit('permissions-updated')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to revoke permission:', error)
      ElMessage.error('Failed to revoke permission')
    }
  } finally {
    revokingPermission.value = null
  }
}

const resetForm = () => {
  shareForm.value = {
    shareType: 'user',
    targetId: null,
    permissions: ['read'],
    expiresAt: null
  }
}

const handleClose = () => {
  dialogVisible.value = false
}

const getPermissionTagType = (permissionType: string) => {
  const types: Record<string, string> = {
    read: 'info',
    write: 'warning',
    delete: 'danger',
    share: 'success',
    admin: 'danger'
  }
  return types[permissionType] || 'info'
}

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleString()
}

const disabledDate = (time: Date) => {
  return time.getTime() < Date.now()
}

// Load initial data when component mounts
onMounted(() => {
  if (props.visible && props.file) {
    loadCurrentPermissions()
  }
})
</script>

<style scoped>
.share-dialog-content {
  max-height: 70vh;
  overflow-y: auto;
}

.current-sharing-section,
.add-sharing-section {
  margin-bottom: 24px;
}

.current-sharing-section h4,
.add-sharing-section h4 {
  margin-bottom: 16px;
  color: #303133;
  font-weight: 600;
}

.permission-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.permission-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background-color: #fafafa;
}

.permission-info {
  flex: 1;
}

.target-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.target-name {
  font-weight: 500;
  color: #303133;
}

.permission-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #909399;
}

.permission-actions {
  display: flex;
  gap: 8px;
}

.share-form {
  margin-top: 16px;
}

.no-sharing {
  padding: 24px;
  text-align: center;
  color: #909399;
}

.el-checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.el-form-item:last-child {
  margin-bottom: 0;
}
</style>
