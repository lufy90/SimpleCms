<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <div class="logo">
          <el-icon size="48" color="#409eff"><Folder /></el-icon>
          <h1>File Manager</h1>
        </div>
        <p class="subtitle">Sign in to access your files</p>
      </div>

      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        @submit.prevent="handleLogin"
        class="login-form"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="Username"
            prefix-icon="User"
            size="large"
            clearable
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="Password"
            prefix-icon="Lock"
            size="large"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="isLoading"
            @click="handleLogin"
            class="login-button"
            block
          >
            Sign In
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-footer">
        <p>
          Don't have an account?
          <router-link to="/register" class="register-link">Sign up</router-link>
        </p>
      </div>

      <!-- Demo Credentials -->
      <div class="demo-credentials" v-if="showDemoCredentials">
        <el-divider>Demo Credentials</el-divider>
        <div class="demo-item">
          <strong>Admin:</strong> admin / admin123
        </div>
        <div class="demo-item">
          <strong>User:</strong> alice / password123
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { Folder, User, Lock } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()

// Form refs
const loginFormRef = ref<FormInstance>()

// Form data
const loginForm = reactive({
  username: '',
  password: '',
})

// Form validation rules
const loginRules: FormRules = {
  username: [
    { required: true, message: 'Please enter username', trigger: 'blur' },
    { min: 3, message: 'Username must be at least 3 characters', trigger: 'blur' },
  ],
  password: [
    { required: true, message: 'Please enter password', trigger: 'blur' },
    { min: 6, message: 'Password must be at least 6 characters', trigger: 'blur' },
  ],
}

// State
const isLoading = ref(false)
const showDemoCredentials = ref(true)

// Methods
const handleLogin = async () => {
  if (!loginFormRef.value) return

  try {
    await loginFormRef.value.validate()
    isLoading.value = true

    const success = await authStore.login({
      username: loginForm.username,
      password: loginForm.password,
    })

    if (success) {
      router.push('/files')
    }
  } catch (error) {
    console.error('Login validation error:', error)
  } finally {
    isLoading.value = false
  }
}

// Lifecycle
onMounted(() => {
  // Auto-focus username field
  setTimeout(() => {
    const usernameInput = document.querySelector('input[placeholder="Username"]') as HTMLInputElement
    if (usernameInput) {
      usernameInput.focus()
    }
  }, 100)
})
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.login-card {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  padding: 48px;
  width: 100%;
  max-width: 400px;
  text-align: center;
}

.login-header {
  margin-bottom: 32px;
}

.logo {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.logo h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: #303133;
}

.subtitle {
  margin: 0;
  color: #909399;
  font-size: 16px;
}

.login-form {
  margin-bottom: 24px;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 20px;
}

.login-form :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.login-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.login-button {
  border-radius: 8px;
  font-weight: 600;
  height: 48px;
  font-size: 16px;
}

.login-footer {
  margin-bottom: 24px;
}

.login-footer p {
  margin: 0;
  color: #606266;
}

.register-link {
  color: #409eff;
  text-decoration: none;
  font-weight: 600;
}

.register-link:hover {
  text-decoration: underline;
}

.demo-credentials {
  text-align: left;
  background: #f5f7fa;
  border-radius: 8px;
  padding: 16px;
}

.demo-credentials :deep(.el-divider__text) {
  background: #f5f7fa;
  color: #909399;
  font-size: 14px;
  font-weight: 600;
}

.demo-item {
  margin: 8px 0;
  font-size: 14px;
  color: #606266;
}

.demo-item strong {
  color: #303133;
}

/* Responsive */
@media (max-width: 480px) {
  .login-card {
    padding: 32px 24px;
    margin: 20px;
  }
  
  .logo h1 {
    font-size: 24px;
  }
  
  .subtitle {
    font-size: 14px;
  }
}
</style>
