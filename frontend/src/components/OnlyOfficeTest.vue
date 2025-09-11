<template>
  <div class="onlyoffice-test">
    <h2>OnlyOffice Script Loading Test</h2>
    <div v-if="loading" class="loading">Loading OnlyOffice script...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else class="success">OnlyOffice script loaded successfully!</div>

    <div class="debug-info">
      <h3>Debug Information:</h3>
      <p><strong>Script URL:</strong> {{ scriptUrl }}</p>
      <p><strong>DocsAPI Available:</strong> {{ docsApiAvailable }}</p>
      <p><strong>Loading State:</strong> {{ loading }}</p>
      <p><strong>Error:</strong> {{ error || 'None' }}</p>
    </div>

    <button @click="testLoad" :disabled="loading">Test Load Script</button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useOfficeConfig } from '@/services/officeConfig'

const officeConfig = useOfficeConfig()
const loading = ref(false)
const error = ref<string | null>(null)
const docsApiAvailable = ref(false)
const scriptUrl = ref('')

const testLoad = () => {
  loading.value = true
  error.value = null
  docsApiAvailable.value = false

  scriptUrl.value = `${officeConfig.documentServerUrl.value}/web-apps/apps/api/documents/api.js`

  console.log('Testing script load from:', scriptUrl.value)

  const script = document.createElement('script')
  script.src = scriptUrl.value

  const timeout = setTimeout(() => {
    console.error('Script loading timeout')
    error.value = 'Script loading timeout after 10 seconds'
    loading.value = false
  }, 10000)

  script.onload = () => {
    console.log('Script loaded successfully')
    clearTimeout(timeout)
    docsApiAvailable.value = typeof (window as any).DocsAPI !== 'undefined'
    loading.value = false
  }

  script.onerror = (err) => {
    console.error('Script loading error:', err)
    clearTimeout(timeout)
    error.value = 'Failed to load script. Check network connection and proxy settings.'
    loading.value = false
  }

  document.head.appendChild(script)
}

onMounted(() => {
  testLoad()
})
</script>

<style scoped>
.onlyoffice-test {
  padding: 20px;
  max-width: 600px;
  margin: 0 auto;
}

.loading {
  color: #409eff;
  font-weight: bold;
}

.error {
  color: #f56c6c;
  font-weight: bold;
}

.success {
  color: #67c23a;
  font-weight: bold;
}

.debug-info {
  margin-top: 20px;
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.debug-info p {
  margin: 5px 0;
}

button {
  margin-top: 15px;
  padding: 10px 20px;
  background-color: #409eff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

button:disabled {
  background-color: #c0c4cc;
  cursor: not-allowed;
}
</style>
