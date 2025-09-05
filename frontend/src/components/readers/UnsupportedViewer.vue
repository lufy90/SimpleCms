<template>
  <div class="unsupported-viewer">
    <div class="unsupported-content">
      <div class="file-icon">
        <el-icon size="64" color="#909399">
          <Document />
        </el-icon>
      </div>
      
      <div class="file-info">
        <h3>{{ file?.name }}</h3>
        <p class="file-type">{{ getFileType() }}</p>
        <p class="file-size" v-if="file?.file_info?.size">
          {{ formatFileSize(file.file_info.size) }}
        </p>
      </div>
      
      <div class="message">
        <el-icon size="32" color="#e6a23c">
          <Warning />
        </el-icon>
        <p>This file type cannot be previewed in the browser.</p>
        <p class="sub-message">You can download the file to view it with an appropriate application.</p>
      </div>
      
      <div class="actions">
        <el-button type="primary" @click="$emit('download')">
          <el-icon><Download /></el-icon>
          Download File
        </el-button>
        <el-button @click="openInNewTab">
          <el-icon><Share /></el-icon>
          Open in New Tab
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Document, Warning, Download, Share } from '@element-plus/icons-vue'
import { filesAPI } from '@/services/api'
import { ElMessage } from 'element-plus'

interface FileItem {
  id: number
  name: string
  item_type: 'file' | 'directory'
  storage?: {
    mime_type?: string
  }
  file_info?: {
    size?: number
  }
}

interface Props {
  file: FileItem | null
}

const props = defineProps<Props>()

defineEmits<{
  download: []
}>()

// Methods
const getFileType = () => {
  if (!props.file) return 'Unknown'
  
  const mimeType = props.file.storage?.mime_type
  if (mimeType) {
    return mimeType
  }
  
  const extension = props.file.name.split('.').pop()?.toUpperCase()
  return extension ? `${extension} File` : 'Unknown File Type'
}

const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 Bytes'
  
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const openInNewTab = () => {
  if (!props.file) return
  
  // Open file in new tab using the dedicated file viewer route
  const fileViewerUrl = `/view/${props.file.id}`
  window.open(fileViewerUrl, '_blank')
}
</script>

<style scoped>
.unsupported-viewer {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.unsupported-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  max-width: 400px;
  gap: 24px;
}

.file-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 120px;
  height: 120px;
  background: #f5f7fa;
  border-radius: 50%;
  border: 2px dashed #dcdfe6;
}

.file-info h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  word-break: break-word;
}

.file-type {
  margin: 8px 0 0 0;
  font-size: 14px;
  color: #606266;
}

.file-size {
  margin: 4px 0 0 0;
  font-size: 12px;
  color: #909399;
}

.message {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 20px;
  background: #fdf6ec;
  border: 1px solid #f5dab1;
  border-radius: 8px;
  color: #b88230;
}

.message p {
  margin: 0;
  font-size: 14px;
}

.sub-message {
  font-size: 12px;
  opacity: 0.8;
}

.actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: center;
}

.actions .el-button {
  display: flex;
  align-items: center;
  gap: 6px;
}
</style>
