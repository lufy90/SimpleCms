<template>
  <div class="upload-view">
    <div class="page-header">
      <h1>Upload Files</h1>
      <el-button @click="$router.go(-1)">
        <el-icon><ArrowLeft /></el-icon>
        Back
      </el-button>
    </div>

    <el-card class="upload-card">
      <template #header>
        <div class="card-header">
          <span>File Upload</span>
        </div>
      </template>

      <el-form :model="uploadForm" label-width="120px">
        <el-form-item label="Directory Path">
          <el-input
            v-model="uploadForm.path"
            placeholder="Optional: subdirectory within root (e.g., documents/work)"
            clearable
          />
        </el-form-item>

        <el-form-item label="Visibility">
          <el-select v-model="uploadForm.visibility" placeholder="Select visibility">
            <el-option label="Private" value="private" />
            <el-option label="User Shared" value="user" />
            <el-option label="Group Shared" value="group" />
            <el-option label="Public" value="public" />
          </el-select>
        </el-form-item>

        <el-form-item label="Files">
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
            <div class="el-upload__text">Drop file here or <em>click to upload</em></div>
          </el-upload>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            @click="handleUpload"
            :loading="isUploading"
            style="margin-right: 10px"
          >
            Upload Files
          </el-button>
          <el-button @click="handleClose" plain> Cancel </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Duplicate File Dialog -->
    <el-dialog
      v-model="duplicateDialogVisible"
      title="Duplicate File Detected"
      width="500px"
      :close-on-click-modal="false"
    >
      <div class="duplicate-dialog">
        <p>
          A file named <strong>{{ duplicateFile?.name }}</strong> already exists in this location.
        </p>
        <p>What would you like to do?</p>
        
        <div class="file-info" v-if="duplicateFile">
          <p><strong>Existing file:</strong></p>
          <ul>
            <li>Size: {{ formatFileSize(duplicateFile.size || 0) }}</li>
            <li>Modified: {{ formatDate(duplicateFile.updated_at) }}</li>
            <li>Owner: {{ duplicateFile.owner.username }}</li>
          </ul>
        </div>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="handleSkipFile">Skip</el-button>
          <el-button @click="handleRenameFile">Rename</el-button>
          <el-button type="primary" @click="handleOverwriteFile">Overwrite</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- Rename File Dialog -->
    <el-dialog
      v-model="renameDialogVisible"
      title="Rename File"
      width="400px"
      :close-on-click-modal="false"
    >
      <el-form :model="renameForm" label-width="80px">
        <el-form-item label="New Name">
          <el-input v-model="renameForm.name" placeholder="Enter new filename" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="renameDialogVisible = false">Cancel</el-button>
          <el-button type="primary" @click="handleConfirmRename">Confirm</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useFilesStore } from '@/stores/files'
import { ArrowLeft, UploadFilled, Close } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FileItem } from '@/stores/files'

const router = useRouter()
const authStore = useAuthStore()
const filesStore = useFilesStore()

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
  selectedFiles.value = fileList.map(f => f.raw)
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
    relativePath: uploadForm.value.path
  })

  // Check for duplicate file
  const duplicate = await filesStore.checkForDuplicateFile(
    file.name,
    undefined, // parentId - we'll handle this based on the path
    uploadForm.value.path
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
      uploadForm.value.path
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
      lastModified: currentFile.value.lastModified
    })
    
    // Upload the renamed file
    await filesStore.uploadFile(
      renamedFile,
      undefined,
      uploadForm.value.visibility,
      [],
      uploadForm.value.path
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
      fileSize: currentFile.value.size
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
