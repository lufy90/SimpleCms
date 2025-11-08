<template>
  <div class="upload-view">
    <div class="page-header">
      <h1>{{ $t('upload.title') }}</h1>
      <el-button @click="$router.go(-1)">
        <el-icon><ArrowLeft /></el-icon>
        {{ $t('common.back') }}
      </el-button>
    </div>

    <el-card class="upload-card">
      <template #header>
        <div class="card-header">
          <span>{{ $t('upload.title') }}</span>
        </div>
      </template>

      <el-form :model="uploadForm" label-width="120px">
        <el-form-item :label="$t('upload.directoryPath')">
          <el-input
            v-model="uploadForm.path"
            :placeholder="$t('upload.directoryPathPlaceholder')"
            clearable
          />
        </el-form-item>

        <el-form-item :label="$t('upload.visibility')">
          <el-select
            v-model="uploadForm.visibility"
            :placeholder="$t('files.placeholders.selectVisibility')"
          >
            <el-option :label="$t('files.visibility.private')" value="private" />
            <el-option :label="$t('files.visibility.user')" value="user" />
            <el-option :label="$t('files.visibility.group')" value="group" />
            <el-option :label="$t('files.visibility.public')" value="public" />
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('upload.files')">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :on-change="handleFileChange"
            :before-upload="beforeUpload"
            multiple
            drag
            class="upload-area"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">{{ $t('files.upload.dropFilesHere') }}</div>
          </el-upload>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            @click="handleUpload"
            :loading="isUploading"
            style="margin-right: 10px"
          >
            {{ $t('upload.uploadFiles') }}
          </el-button>
          <el-button @click="handleClose" plain> {{ $t('common.cancel') }} </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Duplicate File Dialog -->
    <el-dialog
      v-model="duplicateDialogVisible"
      :title="$t('upload.duplicateFileDetected')"
      width="500px"
      :close-on-click-modal="false"
    >
      <div class="duplicate-dialog">
        <p>
          {{ $t('upload.fileAlreadyExists', { name: duplicateFile?.name }) }}
        </p>
        <p>{{ $t('upload.whatWouldYouLikeToDo') }}</p>

        <div class="file-info" v-if="duplicateFile">
          <p>
            <strong>{{ $t('upload.existingFile') }}</strong>
          </p>
          <ul>
            <li>{{ $t('upload.size') }} {{ formatFileSize(duplicateFile.size || 0) }}</li>
            <li>{{ $t('upload.modified') }} {{ formatDate(duplicateFile.updated_at) }}</li>
            <li>{{ $t('upload.owner') }} {{ duplicateFile.owner.username }}</li>
          </ul>
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="handleSkipFile">{{ $t('upload.skip') }}</el-button>
          <el-button @click="handleRenameFile">{{ $t('upload.rename') }}</el-button>
          <el-button type="primary" @click="handleOverwriteFile">{{
            $t('upload.overwrite')
          }}</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- Rename File Dialog -->
    <el-dialog
      v-model="renameDialogVisible"
      :title="$t('upload.renameFile')"
      width="400px"
      :close-on-click-modal="false"
    >
      <el-form :model="renameForm" label-width="80px">
        <el-form-item :label="$t('upload.newName')">
          <el-input v-model="renameForm.name" :placeholder="$t('upload.enterNewFilename')" />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="renameDialogVisible = false">{{ $t('common.cancel') }}</el-button>
          <el-button type="primary" @click="handleConfirmRename">{{
            $t('common.confirm')
          }}</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { useFilesStore } from '@/stores/files'
import { ArrowLeft, UploadFilled, Close } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FileItem } from '@/stores/files'

const router = useRouter()
const authStore = useAuthStore()
const filesStore = useFilesStore()
const { t } = useI18n()

// State
const uploadForm = ref({
  path: '',
  visibility: 'private',
})

const isUploading = ref(false)
const uploadRef = ref()
const selectedFiles = ref<File[]>([])
const duplicateDialogVisible = ref(false)
const renameDialogVisible = ref(false)
const duplicateFile = ref<FileItem | null>(null)
const currentFile = ref<File | null>(null)
const renameForm = ref({ name: '' })

// Methods
const handleFileChange = (file: any, fileList: any[]) => {
  selectedFiles.value = fileList.map((f) => f.raw)
}

const handleUpload = async () => {
  if (selectedFiles.value.length === 0) {
    ElMessage.warning('Please select files to upload')
    return
  }

  isUploading.value = true

  try {
    for (const file of selectedFiles.value) {
      await processFileUpload(file)
    }

    ElMessage.success('All files processed successfully')
    selectedFiles.value = []
    if (uploadRef.value) {
      uploadRef.value.clearFiles()
    }
  } catch (error) {
    console.error('Upload error:', error)
  } finally {
    isUploading.value = false
  }
}

const processFileUpload = async (file: File) => {
  console.log('Processing file upload:', {
    fileName: file.name,
    fileSize: file.size,
    relativePath: uploadForm.value.path,
  })

  // Check for duplicate file
  const duplicate = await filesStore.checkForDuplicateFile(
    file.name,
    undefined, // parentId - we'll handle this based on the path
    uploadForm.value.path,
  )

  if (duplicate) {
    console.log('Duplicate found, showing dialog')
    // Show duplicate dialog
    duplicateFile.value = duplicate
    currentFile.value = file
    duplicateDialogVisible.value = true

    // Wait for user decision
    return new Promise<void>((resolve) => {
      const checkDialog = () => {
        if (!duplicateDialogVisible.value) {
          resolve()
        } else {
          setTimeout(checkDialog, 100)
        }
      }
      checkDialog()
    })
  } else {
    console.log('No duplicate found, proceeding with normal upload')
    // No duplicate, proceed with normal upload
    await filesStore.uploadFile(
      file,
      undefined, // parentId
      uploadForm.value.visibility,
      [], // tags
      uploadForm.value.path,
    )
  }
}

const handleSkipFile = () => {
  ElMessage.info(`Skipped ${currentFile.value?.name}`)
  duplicateDialogVisible.value = false
}

const handleRenameFile = () => {
  renameForm.value.name = currentFile.value?.name || ''
  renameDialogVisible.value = true
}

const handleConfirmRename = async () => {
  if (!currentFile.value || !renameForm.value.name) return

  try {
    // Create a new file with the renamed name
    const renamedFile = new File([currentFile.value], renameForm.value.name, {
      type: currentFile.value.type,
      lastModified: currentFile.value.lastModified,
    })

    // Upload the renamed file
    await filesStore.uploadFile(
      renamedFile,
      undefined,
      uploadForm.value.visibility,
      [],
      uploadForm.value.path,
    )

    ElMessage.success(`${renameForm.value.name} uploaded successfully`)
  } catch (error) {
    ElMessage.error(`Failed to upload ${renameForm.value.name}`)
  }

  renameDialogVisible.value = false
  duplicateDialogVisible.value = false
}

const handleOverwriteFile = async () => {
  if (!currentFile.value || !duplicateFile.value) return

  try {
    console.log('Overwriting file:', {
      fileId: duplicateFile.value.id,
      fileName: currentFile.value.name,
      fileSize: currentFile.value.size,
    })

    // Update the existing file's content using PATCH request
    await filesStore.updateFileContent(duplicateFile.value.id, currentFile.value)
    ElMessage.success(`${currentFile.value.name} overwritten successfully`)
  } catch (error) {
    console.error('Overwrite error:', error)
    ElMessage.error(`Failed to overwrite ${currentFile.value.name}`)
  }

  duplicateDialogVisible.value = false
}

const beforeUpload = (file: any) => {
  return true
}

const handleClose = () => {
  router.go(-1)
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleString()
}
</script>

<style scoped>
.upload-view {
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

.upload-card {
  max-width: 600px;
}

.card-header {
  font-weight: 600;
  font-size: 16px;
}

.upload-area {
  width: 100%;
}

.duplicate-dialog {
  margin-bottom: 20px;
}

.duplicate-dialog p {
  margin-bottom: 15px;
  line-height: 1.5;
}

.file-info {
  background-color: #f5f7fa;
  padding: 15px;
  border-radius: 6px;
  margin-top: 15px;
}

.file-info p {
  margin-bottom: 10px;
  font-weight: 600;
}

.file-info ul {
  margin: 0;
  padding-left: 20px;
}

.file-info li {
  margin-bottom: 5px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
