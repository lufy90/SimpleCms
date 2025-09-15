<template>
  <div class="register-container">
    <div class="register-card">
      <div class="register-header">
        <div class="logo">
          <el-icon size="48" color="#409eff"><Folder /></el-icon>
          <h1>{{ $t('register.title') }}</h1>
        </div>
        <p class="subtitle">{{ $t('register.subtitle') }}</p>
      </div>

      <el-form
        ref="registerFormRef"
        :model="registerForm"
        :rules="registerRules"
        @submit.prevent="handleRegister"
        class="register-form"
      >
        <el-form-item prop="username">
          <el-input
            v-model="registerForm.username"
            :placeholder="$t('register.username')"
            prefix-icon="User"
            size="large"
            clearable
          />
        </el-form-item>

        <el-form-item prop="email">
          <el-input
            v-model="registerForm.email"
            :placeholder="$t('register.email')"
            prefix-icon="Message"
            size="large"
            clearable
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="registerForm.password"
            type="password"
            :placeholder="$t('register.password')"
            prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>

        <el-form-item prop="confirmPassword">
          <el-input
            v-model="registerForm.confirmPassword"
            type="password"
            :placeholder="$t('register.confirmPassword')"
            prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>

        <el-form-item prop="firstName">
          <el-input
            v-model="registerForm.firstName"
            :placeholder="$t('register.firstName')"
            prefix-icon="User"
            size="large"
            clearable
          />
        </el-form-item>

        <el-form-item prop="lastName">
          <el-input
            v-model="registerForm.lastName"
            :placeholder="$t('register.lastName')"
            prefix-icon="User"
            size="large"
            clearable
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="isLoading"
            @click="handleRegister"
            class="register-button"
            block
          >
            {{ $t('register.createAccount') }}
          </el-button>
        </el-form-item>
      </el-form>

      <div class="register-footer">
        <p>
          {{ $t('register.alreadyHaveAccount') }}
          <router-link to="/login" class="login-link">{{ $t('register.signIn') }}</router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { Folder, User, Message, Lock } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'

const { t } = useI18n()
const router = useRouter()
const authStore = useAuthStore()

// Form refs
const registerFormRef = ref<FormInstance>()

// Form data
const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  firstName: '',
  lastName: '',
})

// Form validation rules
const registerRules: FormRules = {
  username: [
    { required: true, message: t('register.usernameRequired'), trigger: 'blur' },
    { min: 3, message: t('register.usernameMinLength'), trigger: 'blur' },
    {
      pattern: /^[a-zA-Z0-9_]+$/,
      message: t('register.usernamePattern'),
      trigger: 'blur',
    },
  ],
  email: [
    { required: true, message: t('register.emailRequired'), trigger: 'blur' },
    { type: 'email', message: t('register.emailInvalid'), trigger: 'blur' },
  ],
  password: [
    { required: true, message: t('register.passwordRequired'), trigger: 'blur' },
    { min: 6, message: t('register.passwordMinLength'), trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: t('register.confirmPasswordRequired'), trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== registerForm.password) {
          callback(new Error(t('register.passwordsDoNotMatch')))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}

// State
const isLoading = ref(false)

// Methods
const handleRegister = async () => {
  if (!registerFormRef.value) return

  try {
    await registerFormRef.value.validate()
    isLoading.value = true

    const success = await authStore.register({
      username: registerForm.username,
      email: registerForm.email,
      password: registerForm.password,
      first_name: registerForm.firstName || undefined,
      last_name: registerForm.lastName || undefined,
    })

    if (success) {
      router.push('/files')
    }
  } catch (error) {
    console.error('Registration validation error:', error)
  } finally {
    isLoading.value = false
  }
}

// Lifecycle
onMounted(() => {
  // Auto-focus username field
  setTimeout(() => {
    const usernameInput = document.querySelector(
      'input[placeholder="Username"]',
    ) as HTMLInputElement
    if (usernameInput) {
      usernameInput.focus()
    }
  }, 100)
})
</script>

<style scoped>
.register-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.register-card {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  padding: 48px;
  width: 100%;
  max-width: 450px;
  text-align: center;
}

.register-header {
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

.register-form {
  margin-bottom: 24px;
}

.register-form :deep(.el-form-item) {
  margin-bottom: 20px;
}

.register-form :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.register-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.register-button {
  border-radius: 8px;
  font-weight: 600;
  height: 48px;
  font-size: 16px;
}

.register-footer {
  margin-bottom: 24px;
}

.register-footer p {
  margin: 0;
  color: #606266;
}

.login-link {
  color: #409eff;
  text-decoration: none;
  font-weight: 600;
}

.login-link:hover {
  text-decoration: underline;
}

/* Responsive */
@media (max-width: 480px) {
  .register-card {
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
