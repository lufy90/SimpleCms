<template>
  <div class="profile-view">
    <div class="page-header">
      <h1>{{ $t('profile.title') }}</h1>
    </div>

    <el-card class="profile-card">
      <template #header>
        <div class="card-header">
          <span>{{ $t('profile.profileInformation') }}</span>
        </div>
      </template>

      <el-form :model="profileForm" label-width="120px">
        <el-form-item :label="$t('profile.username')">
          <el-input v-model="profileForm.username" disabled />
        </el-form-item>

        <el-form-item :label="$t('profile.email')">
          <el-input v-model="profileForm.email" disabled />
        </el-form-item>

        <el-form-item :label="$t('profile.firstName')">
          <el-input v-model="profileForm.firstName" />
        </el-form-item>

        <el-form-item :label="$t('profile.lastName')">
          <el-input v-model="profileForm.lastName" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="updateProfile" :loading="isLoading">
            {{ $t('profile.updateProfile') }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="password-card">
      <template #header>
        <div class="card-header">
          <span>{{ $t('profile.changePassword') }}</span>
        </div>
      </template>

      <el-form :model="passwordForm" label-width="120px">
        <el-form-item :label="$t('profile.currentPassword')">
          <el-input v-model="passwordForm.oldPassword" type="password" show-password />
        </el-form-item>

        <el-form-item :label="$t('profile.newPassword')">
          <el-input v-model="passwordForm.newPassword" type="password" show-password />
        </el-form-item>

        <el-form-item :label="$t('profile.confirmPassword')">
          <el-input v-model="passwordForm.confirmPassword" type="password" show-password />
        </el-form-item>

        <el-form-item>
          <el-button type="warning" @click="changePassword" :loading="isChangingPassword">
            {{ $t('profile.changePasswordButton') }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

const { t } = useI18n()
const authStore = useAuthStore()

// State
const isLoading = ref(false)
const isChangingPassword = ref(false)

// Forms
const profileForm = reactive({
  username: '',
  email: '',
  firstName: '',
  lastName: '',
})

const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

// Methods
const updateProfile = async () => {
  try {
    isLoading.value = true
    await authStore.updateProfile({
      first_name: profileForm.firstName,
      last_name: profileForm.lastName,
    })
    ElMessage.success(t('profile.profileUpdatedSuccessfully'))
  } catch (error) {
    ElMessage.error(t('profile.failedToUpdateProfile'))
  } finally {
    isLoading.value = false
  }
}

const changePassword = async () => {
  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    ElMessage.error(t('profile.newPasswordsDoNotMatch'))
    return
  }

  try {
    isChangingPassword.value = true
    await authStore.changePassword({
      old_password: passwordForm.oldPassword,
      new_password: passwordForm.newPassword,
    })
    ElMessage.success(t('profile.passwordChangedSuccessfully'))

    // Clear form
    passwordForm.oldPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''
  } catch (error) {
    ElMessage.error(t('profile.failedToChangePassword'))
  } finally {
    isChangingPassword.value = false
  }
}

// Lifecycle
onMounted(() => {
  if (authStore.user) {
    profileForm.username = authStore.user.username
    profileForm.email = authStore.user.email
    profileForm.firstName = authStore.user.first_name
    profileForm.lastName = authStore.user.last_name
  }
})
</script>

<style scoped>
.profile-view {
  padding: 24px;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 600;
  color: #303133;
}

.profile-card,
.password-card {
  margin-bottom: 24px;
  max-width: 600px;
}

.card-header {
  font-weight: 600;
  font-size: 16px;
}
</style>
