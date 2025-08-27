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
            :action="uploadAction"
            :headers="uploadHeaders"
            :data="uploadData"
            :on-success="handleUploadSuccess"
            :on-error="handleUploadError"
            :before-upload="beforeUpload"
            multiple
            drag
            class="upload-area"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              Drop file here or <em>click to upload</em>
            </div>
          </el-upload>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleUpload" :loading="isUploading">
            Upload Files
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ArrowLeft, UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()

// State
const uploadForm = ref({
  path: '',
  visibility: 'private',
})

const isUploading = ref(false)
const uploadRef = ref()

// Upload configuration
const uploadAction = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8002'}/api/upload/`
const uploadHeaders = computed(() => {
  const token = document.cookie.split('; ').find(row => row.startsWith('access_token='))?.split('=')[1]
  return {
    Authorization: `Bearer ${token}`
  }
})
const uploadData = computed(() => ({
  path: uploadForm.value.path,
  visibility: uploadForm.value.visibility
}))

// Methods
const handleUpload = () => {
  if (uploadRef.value) {
    uploadRef.value.submit()
  }
}

const handleUploadSuccess = (response: any, file: any) => {
  ElMessage.success(`${file.name} uploaded successfully`)
}

const handleUploadError = (error: any, file: any) => {
  ElMessage.error(`${file.name} upload failed`)
}

const beforeUpload = (file: any) => {
  return true
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
</style>
