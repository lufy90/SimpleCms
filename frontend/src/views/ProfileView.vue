<template>
  <div class="profile-view">
    <div class="page-header">
      <h1>User Profile</h1>
    </div>

    <el-card class="profile-card">
      <template #header>
        <div class="card-header">
          <span>Profile Information</span>
        </div>
      </template>

      <el-form :model="profileForm" label-width="120px">
        <el-form-item label="Username">
          <el-input v-model="profileForm.username" disabled />
        </el-form-item>

        <el-form-item label="Email">
          <el-input v-model="profileForm.email" disabled />
        </el-form-item>

        <el-form-item label="First Name">
          <el-input v-model="profileForm.firstName" />
        </el-form-item>

        <el-form-item label="Last Name">
          <el-input v-model="profileForm.lastName" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="updateProfile" :loading="isLoading">
            Update Profile
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="password-card">
      <template #header>
        <div class="card-header">
          <span>Change Password</span>
        </div>
      </template>

      <el-form :model="passwordForm" label-width="120px">
        <el-form-item label="Current Password">
          <el-input
            v-model="passwordForm.oldPassword"
            type="password"
            show-password
          />
        </el-form-item>

        <el-form-item label="New Password">
          <el-input
            v-model="passwordForm.newPassword"
            type="password"
            show-password
          />
        </el-form-item>

        <el-form-item label="Confirm Password">
          <el-input
            v-model="passwordForm.confirmPassword"
            type="password"
            show-password
          />
        </el-form-item>

        <el-form-item>
          <el-button type="warning" @click="changePassword" :loading="isChangingPassword">
            Change Password
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

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
    ElMessage.success('Profile updated successfully')
  } catch (error) {
    ElMessage.error('Failed to update profile')
  } finally {
    isLoading.value = false
  }
}

const changePassword = async () => {
  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    ElMessage.error('New passwords do not match')
    return
  }

  try {
    isChangingPassword.value = true
    await authStore.changePassword({
      old_password: passwordForm.oldPassword,
      new_password: passwordForm.newPassword,
    })
    ElMessage.success('Password changed successfully')
    
    // Clear form
    passwordForm.oldPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''
  } catch (error) {
    ElMessage.error('Failed to change password')
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
