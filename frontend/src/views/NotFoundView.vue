<template>
  <div class="not-found">
    <div class="not-found-content">
      <h1>404</h1>
      <h2>Page Not Found</h2>
      <p>The page you're looking for doesn't exist.</p>
      <el-button type="primary" @click="$router.push('/files')"> Go to Files </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
// No additional logic needed
</script>

<style scoped>
.not-found {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
}

.not-found-content {
  text-align: center;
  padding: 48px;
}

.not-found-content h1 {
  font-size: 120px;
  margin: 0;
  color: #409eff;
  font-weight: 700;
}

.not-found-content h2 {
  font-size: 32px;
  margin: 16px 0;
  color: #303133;
}

.not-found-content p {
  font-size: 18px;
  color: #606266;
  margin-bottom: 32px;
}
</style>
