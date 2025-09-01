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

          <!-- Bulk actions for directories -->
          <div
            v-if="file?.item_type === 'directory' && currentPermissions.length > 1"
            class="bulk-actions"
          >
            <el-divider />
            <div class="bulk-actions-content">
              <el-text size="small" type="info"> Bulk actions for directory: </el-text>
              <div class="bulk-buttons">
                <el-button
                  size="small"
                  type="danger"
                  @click="revokeAllPermissions"
                  :loading="revokingAll"
                >
                  <el-icon><Delete /></el-icon>
                  Revoke All Permissions
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

          <!-- Recursive sharing option for directories -->
          <el-form-item v-if="file?.item_type === 'directory'" label="Recursive Sharing">
            <el-checkbox v-model="shareForm.recursive">
              Share this directory and all its contents recursively
            </el-checkbox>
            <div class="recursive-help">
              <el-text size="small" type="info">
                When enabled, all files and subdirectories within this directory will be shared with
                the same permissions.
              </el-text>
            </div>
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
            <el-button type="primary" @click="shareFile" :loading="sharing" :disabled="!canShare">
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
import { permissionsAPI, filesAPI } from '@/services/api'
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
  recursive: boolean
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
const revokingAll = ref(false)

const shareForm = ref<ShareForm>({
  shareType: 'user',
  targetId: null,
  permissions: ['read'],
  expiresAt: null,
  recursive: false,
})

// Computed properties
const canShare = computed(() => {
  return shareForm.value.targetId && shareForm.value.permissions.length > 0
})

// Watch for dialog visibility changes
watch(
  () => props.visible,
  (newVal) => {
    dialogVisible.value = newVal
    if (newVal && props.file) {
      loadCurrentPermissions()
    }
  },
)

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
    const response = await permissionsAPI.searchUsers({ query })
    availableUsers.value = response.data.results || response.data || []
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
    const response = await permissionsAPI.searchGroups({ query })
    availableGroups.value = response.data.results || response.data || []
  } catch (error) {
    console.error('Failed to search groups:', error)
  } finally {
    searchingGroups.value = false
  }
}

const shareFile = async () => {
  if (!props.file || !shareForm.value.targetId) return

  // Validate that we have the correct combination
  if (shareForm.value.shareType === 'user' && !shareForm.value.targetId) {
    ElMessage.error('Please select a user to share with')
    return
  }

  if (shareForm.value.shareType === 'group' && !shareForm.value.targetId) {
    ElMessage.error('Please select a group to share with')
    return
  }

  sharing.value = true
  try {
    // Check if this is recursive directory sharing
    if (props.file.item_type === 'directory' && shareForm.value.recursive) {
      // Use recursive sharing API
      const response = await filesAPI.shareRecursively(props.file.id, {
        share_type: shareForm.value.shareType,
        target_id: shareForm.value.targetId,
        permission_types: shareForm.value.permissions,
        expires_at: shareForm.value.expiresAt || undefined,
      })

      ElMessage.success(`Directory shared recursively: ${response.data.message}`)
    } else {
      // Use regular permission creation for single files or non-recursive sharing
      const permissionPromises = shareForm.value.permissions.map((permissionType) => {
        const permissionData = {
          file: props.file!.id,
          permission_type: permissionType,
          expires_at: shareForm.value.expiresAt || undefined,
        }

        if (shareForm.value.shareType === 'user') {
          return permissionsAPI.create({
            ...permissionData,
            user: shareForm.value.targetId!,
            group: null, // Explicitly set group to null when sharing with user
          })
        } else {
          return permissionsAPI.create({
            ...permissionData,
            user: null, // Explicitly set user to null when sharing with group
            group: shareForm.value.targetId!,
          })
        }
      })

      await Promise.all(permissionPromises)
      ElMessage.success('File shared successfully')
    }

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
        type: 'warning',
      },
    )

    revokingPermission.value = permissionId
    
    // Find the permission to get its details
    const permission = currentPermissions.value.find(p => p.id === permissionId)
    if (!permission) {
      throw new Error('Permission not found')
    }
    
    // Check if this is a directory and we should offer recursive unsharing
    if (props.file?.item_type === 'directory') {
      const shouldRecursive = await ElMessageBox.confirm(
        'This is a directory. Do you want to revoke permissions for all files and subdirectories within it as well?',
        'Recursive Unsharing',
        {
          confirmButtonText: 'Yes, revoke recursively',
          cancelButtonText: 'No, just this directory',
          type: 'warning',
        },
      ).then(() => true).catch(() => false)
      
      if (shouldRecursive) {
        // Use recursive unsharing
        const shareType = permission.user ? 'user' : 'group'
        const targetId = permission.user?.id || permission.group?.id
        
        if (!targetId) {
          throw new Error('Invalid permission target')
        }
        
        await filesAPI.unshareRecursively(props.file.id, {
          share_type: shareType,
          target_id: targetId,
          permission_types: [permission.permission_type],
        })
        
        ElMessage.success('Directory permissions revoked recursively')
      } else {
        // Use regular permission deletion
        await permissionsAPI.delete(permissionId)
        ElMessage.success('Permission revoked successfully')
      }
    } else {
      // Regular permission deletion for files
      await permissionsAPI.delete(permissionId)
      ElMessage.success('Permission revoked successfully')
    }

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

const revokeAllPermissions = async () => {
  try {
    await ElMessageBox.confirm(
      'Are you sure you want to revoke all permissions for this file?',
      'Confirm Revocation',
      {
        confirmButtonText: 'Revoke All',
        cancelButtonText: 'Cancel',
        type: 'warning',
      },
    )

    // Revoke all permissions one by one
    for (const permission of currentPermissions.value) {
      await permissionsAPI.delete(permission.id)
    }
    ElMessage.success('All permissions revoked successfully')
    await loadCurrentPermissions()
    emit('permissions-updated')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to revoke all permissions:', error)
      ElMessage.error('Failed to revoke all permissions')
    }
  }
}

const resetForm = () => {
  shareForm.value = {
    shareType: 'user',
    targetId: null,
    permissions: ['read'],
    expiresAt: null,
    recursive: false,
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
    admin: 'danger',
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
