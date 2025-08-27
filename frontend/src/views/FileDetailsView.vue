<template>
  <div class="file-details-view">
    <div class="page-header">
      <h1>File Details</h1>
      <el-button @click="$router.go(-1)">
        <el-icon><ArrowLeft /></el-icon>
        Back
      </el-button>
    </div>

    <el-card>
      <template #header>
        <div class="card-header">
          <span>File Information</span>
        </div>
      </template>

      <p>File details view - Coming soon!</p>
      <p>File ID: {{ $route.params.id }}</p>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ArrowLeft } from '@element-plus/icons-vue'
</script>

<style scoped>
.file-details-view {
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

.card-header {
  font-weight: 600;
  font-size: 16px;
}
</style>
