<template>
  <el-dialog
    v-model="dialogVisible"
    :title="$t('shareDialog.title', { name: file?.name || '' })"
    width="700px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div class="share-dialog-content">
      <!-- Current Sharing Status -->
      <div class="current-sharing-section">
        <h4>{{ $t('shareDialog.currentSharing') }}</h4>
        <div class="current-sharing-list">
          <div v-if="userPermissions.length === 0" class="no-sharing">
            <span>{{ $t('shareDialog.noUsersAccess') }}</span>
          </div>
          <div v-else class="permission-list">
            <div
              v-for="permission in userPermissions"
              :key="permission.id"
              class="permission-item"
              :class="{ 'inactive-permission': !permission.is_active }"
            >
              <div class="permission-info">
                <div class="target-info">
                  <el-icon color="#409eff">
                    <User />
                  </el-icon>
                  <span class="target-name">
                    {{ permission.user?.username }}
                  </span>
                  <el-tag size="small" :type="getPermissionTagType(permission.permission_type)">
                    {{ permissionLabel(permission.permission_type) }}
                    <span v-if="!permission.is_active" class="inactive-indicator">
                      {{ $t('shareDialog.inactive') }}
                    </span>
                  </el-tag>
                </div>
                <div class="permission-meta">
                  <span class="granted-by">
                    {{ $t('shareDialog.grantedBy', { username: permission.granted_by.username }) }}
                  </span>
                  <span class="granted-at">{{ formatDate(permission.granted_at) }}</span>
                  <span v-if="permission.expires_at" class="expires-at">
                    {{ $t('shareDialog.expires', { date: formatDate(permission.expires_at) }) }}
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
                  {{ $t('shareDialog.revoke') }}
                </el-button>
              </div>
            </div>
          </div>

          <!-- Bulk actions for directories -->
          <div
            v-if="file?.item_type === 'directory' && userPermissions.length > 1"
            class="bulk-actions"
          >
            <el-divider />
            <div class="bulk-actions-content">
              <el-text size="small" type="info">
                {{ $t('shareDialog.bulkActionsForDirectory') }}
              </el-text>
              <div class="bulk-buttons">
                <el-button
                  size="small"
                  type="danger"
                  @click="revokeAllPermissions"
                  :loading="revokingAll"
                >
                  <el-icon><Delete /></el-icon>
                  {{ $t('shareDialog.revokeAllPermissions') }}
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Add New Sharing -->
      <div class="add-sharing-section">
        <h4>{{ $t('shareDialog.shareWithUser') }}</h4>
        <el-form :model="shareForm" label-width="120px" class="share-form">
          <el-form-item :label="$t('shareDialog.selectUser')">
            <el-select
              v-model="shareForm.targetId"
              :placeholder="$t('shareDialog.selectUserPlaceholder')"
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
          </el-form-item>

          <el-form-item :label="$t('shareDialog.permissions')">
            <el-checkbox-group v-model="shareForm.permissions">
              <el-checkbox label="read">{{ $t('shareDialog.permissionTypes.read') }}</el-checkbox>
              <el-checkbox label="write">{{ $t('shareDialog.permissionTypes.write') }}</el-checkbox>
              <el-checkbox label="delete">{{ $t('shareDialog.permissionTypes.delete') }}</el-checkbox>
              <el-checkbox label="share">{{ $t('shareDialog.permissionTypes.share') }}</el-checkbox>
              <el-checkbox label="admin">{{ $t('shareDialog.permissionTypes.admin') }}</el-checkbox>
            </el-checkbox-group>
          </el-form-item>

          <el-form-item v-if="file?.item_type === 'directory'" :label="$t('shareDialog.note')">
            <el-text size="small" type="info" class="recursive-tip">
              {{ $t('shareDialog.recursiveTip') }}
            </el-text>
          </el-form-item>

          <el-form-item :label="$t('shareDialog.expiresAt')">
            <el-date-picker
              v-model="shareForm.expiresAt"
              type="datetime"
              :placeholder="$t('shareDialog.noExpiration')"
              style="width: 100%"
              :disabled-date="disabledDate"
            />
          </el-form-item>

          <el-form-item>
            <el-button type="primary" @click="shareFile" :loading="sharing" :disabled="!canShare">
              <el-icon><Share /></el-icon>
              {{ $t('shareDialog.shareFile') }}
            </el-button>
            <el-button @click="resetForm">{{ $t('shareDialog.reset') }}</el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessageBox } from 'element-plus'
import { toast } from 'vue3-toastify'
import { User, Share, Delete } from '@element-plus/icons-vue'
import { permissionsAPI, filesAPI } from '@/services/api'
import type { FileItem } from '@/stores/files'

interface Permission {
  id: string
  file: string
  user?: {
    id: string
    username: string
    email: string
  }
  group?: {
    id: string
    name: string
  }
  permission_type: string
  granted_by: {
    id: string
    username: string
  }
  granted_at: string
  expires_at?: string
  is_active: boolean
}

interface UserOption {
  id: string
  username: string
  email: string
  first_name: string
  last_name: string
}

interface ShareForm {
  targetId: string | null
  permissions: string[]
  expiresAt: string | null
}

const props = defineProps<{
  visible: boolean
  file: FileItem | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'permissions-updated': []
}>()

const { t, te } = useI18n()

const dialogVisible = ref(false)
const currentPermissions = ref<Permission[]>([])
const availableUsers = ref<UserOption[]>([])
const searchingUsers = ref(false)
const sharing = ref(false)
const revokingPermission = ref<string | null>(null)
const revokingAll = ref(false)

const shareForm = ref<ShareForm>({
  targetId: null,
  permissions: ['read'],
  expiresAt: null,
})

const userPermissions = computed(() =>
  currentPermissions.value.filter((permission) => !!permission.user),
)

const canShare = computed(() => {
  return shareForm.value.targetId && shareForm.value.permissions.length > 0
})

const permissionLabel = (permissionType: string) => {
  const key = `shareDialog.permissionTypes.${permissionType}`
  return te(key) ? t(key) : permissionType
}

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

const loadCurrentPermissions = async () => {
  if (!props.file) return

  try {
    const response = await permissionsAPI.list({ file: props.file.id })
    currentPermissions.value = response.data.results || response.data || []
  } catch (error) {
    console.error('Failed to load permissions:', error)
    toast.error(t('shareDialog.loadPermissionsFailed'))
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

const shareFile = async () => {
  if (!props.file || !shareForm.value.targetId) return

  sharing.value = true
  try {
    if (props.file.item_type === 'directory') {
      const response = await filesAPI.shareRecursively(props.file.id, {
        share_type: 'user',
        target_id: shareForm.value.targetId,
        permission_types: shareForm.value.permissions,
        expires_at: shareForm.value.expiresAt || undefined,
      })

      toast.success(
        t('shareDialog.directoryShared', { message: response.data.message }),
      )
      const failedItems = response.data.failed_items || []
      if (failedItems.length > 0) {
        toast.warning(t('shareDialog.partialShareFailed', { count: failedItems.length }))
        console.warn('Recursive share failed_items:', failedItems)
      }
    } else {
      const permissionPromises = shareForm.value.permissions.map((permissionType) =>
        permissionsAPI.create({
          file: props.file!.id,
          permission_type: permissionType,
          expires_at: shareForm.value.expiresAt || undefined,
          user: shareForm.value.targetId!,
          group: null,
        }),
      )

      await Promise.all(permissionPromises)
      toast.success(t('shareDialog.fileShared'))
    }

    await loadCurrentPermissions()
    emit('permissions-updated')
    resetForm()
  } catch (error) {
    console.error('Failed to share file:', error)
    toast.error(t('shareDialog.shareFailed'))
  } finally {
    sharing.value = false
  }
}

const revokePermission = async (permissionId: string) => {
  try {
    await ElMessageBox.confirm(
      t('shareDialog.confirmRevokeMessage'),
      t('shareDialog.confirmRevokeTitle'),
      {
        confirmButtonText: t('shareDialog.revoke'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
      },
    )

    revokingPermission.value = permissionId

    const permission = currentPermissions.value.find((p) => p.id === permissionId)
    if (!permission) {
      throw new Error('Permission not found')
    }

    if (props.file?.item_type === 'directory') {
      const shouldRecursive = await ElMessageBox.confirm(
        t('shareDialog.recursiveUnshareMessage'),
        t('shareDialog.recursiveUnshareTitle'),
        {
          confirmButtonText: t('shareDialog.revokeRecursively'),
          cancelButtonText: t('shareDialog.revokeDirectoryOnly'),
          type: 'warning',
        },
      )
        .then(() => true)
        .catch(() => false)

      if (shouldRecursive) {
        const targetId = permission.user?.id
        if (!targetId) {
          throw new Error('Invalid permission target')
        }

        await filesAPI.unshareRecursively(props.file.id, {
          share_type: 'user',
          target_id: targetId,
          permission_types: [permission.permission_type],
        })

        toast.success(t('shareDialog.directoryRevokedRecursively'))
      } else {
        await permissionsAPI.delete(permissionId)
        toast.success(t('shareDialog.permissionRevoked'))
      }
    } else {
      await permissionsAPI.delete(permissionId)
      toast.success(t('shareDialog.permissionRevoked'))
    }

    await loadCurrentPermissions()
    emit('permissions-updated')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to revoke permission:', error)
      toast.error(t('shareDialog.revokeFailed'))
    }
  } finally {
    revokingPermission.value = null
  }
}

const revokeAllPermissions = async () => {
  try {
    await ElMessageBox.confirm(
      t('shareDialog.confirmRevokeAllMessage'),
      t('shareDialog.confirmRevokeTitle'),
      {
        confirmButtonText: t('shareDialog.revokeAll'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
      },
    )

    for (const permission of userPermissions.value) {
      await permissionsAPI.delete(permission.id)
    }
    toast.success(t('shareDialog.allPermissionsRevoked'))
    await loadCurrentPermissions()
    emit('permissions-updated')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to revoke all permissions:', error)
      toast.error(t('shareDialog.revokeAllFailed'))
    }
  }
}

const resetForm = () => {
  shareForm.value = {
    targetId: null,
    permissions: ['read'],
    expiresAt: null,
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

.permission-item.inactive-permission {
  opacity: 0.6;
  background-color: #f5f5f5;
  border-color: #d9d9d9;
}

.inactive-indicator {
  color: #909399;
  font-size: 11px;
  font-style: italic;
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
  display: flex;
  align-items: center;
  padding: 12px;
  min-height: 44px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background-color: #fafafa;
  color: #909399;
  font-size: 14px;
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
