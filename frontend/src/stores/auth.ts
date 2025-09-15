import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { tokenStorage } from '@/utils/storage'
import { authAPI, cleanupInvalidTokens } from '@/services/api'
import { toast } from 'vue3-toastify'

export interface Group {
  id: number
  name: string
}

export interface User {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  groups: Group[]
}

export interface AuthTokens {
  access: string
  refresh: string
}

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null)
  const isAuthenticated = ref(false)
  const isLoading = ref(false)

  // Getters
  const isAdmin = computed(() => user.value?.username === 'admin')
  const displayName = computed(() => {
    if (!user.value) return ''
    if (user.value.first_name && user.value.last_name) {
      return `${user.value.first_name} ${user.value.last_name}`
    }
    return user.value.username
  })

  // Actions
  const login = async (credentials: { username: string; password: string }) => {
    try {
      isLoading.value = true
      const response = await authAPI.login(credentials)
      const { access, refresh, user: userData } = response.data

      // Store tokens
      console.log('[Auth Store] Storing tokens after login')
      tokenStorage.setAccessToken(access)
      tokenStorage.setRefreshToken(refresh)
      console.log('[Auth Store] Tokens stored successfully')

      // Update state
      user.value = userData
      isAuthenticated.value = true

      toast.success('Login successful!')
      return true
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Login failed'
      toast.error(message)
      return false
    } finally {
      isLoading.value = false
    }
  }

  const register = async (userData: {
    username: string
    email: string
    password: string
    first_name?: string
    last_name?: string
  }) => {
    try {
      isLoading.value = true
      const response = await authAPI.register(userData)
      const { access, refresh, user: newUser } = response.data

      // Store tokens
      tokenStorage.setAccessToken(access)
      tokenStorage.setRefreshToken(refresh)

      // Update state
      user.value = newUser
      isAuthenticated.value = true

      toast.success('Registration successful!')
      return true
    } catch (error: any) {
      const message = error.response?.data?.error || 'Registration failed'
      toast.error(message)
      return false
    } finally {
      isLoading.value = false
    }
  }

  const logout = async () => {
    try {
      const refreshToken = tokenStorage.getRefreshToken()
      if (refreshToken) {
        await authAPI.logout(refreshToken)
      }
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      // Clear state and tokens
      user.value = null
      isAuthenticated.value = false
      tokenStorage.removeAllTokens()
      toast.success('Logged out successfully')
    }
  }

  const checkAuth = async () => {
    try {
      // Clean up any invalid tokens first
      cleanupInvalidTokens()

      const accessToken = tokenStorage.getAccessToken()
      if (!accessToken) {
        return false
      }

      const response = await authAPI.profile()
      user.value = response.data
      isAuthenticated.value = true
      return true
    } catch (error) {
      // Token is invalid, clear everything
      console.error('Auth check failed:', error)
      user.value = null
      isAuthenticated.value = false
      tokenStorage.removeAllTokens()
      return false
    }
  }

  const changePassword = async (passwords: { old_password: string; new_password: string }) => {
    try {
      isLoading.value = true
      await authAPI.changePassword(passwords)
      toast.success('Password changed successfully')

      // Logout after password change
      await logout()
      return true
    } catch (error: any) {
      const message = error.response?.data?.error || 'Password change failed'
      toast.error(message)
      return false
    } finally {
      isLoading.value = false
    }
  }

  const updateProfile = async (profileData: Partial<User>) => {
    try {
      isLoading.value = true
      const response = await authAPI.profile()
      user.value = user.value ? { ...user.value, ...profileData } : null
      toast.success('Profile updated successfully')
      return true
    } catch (error: any) {
      const message = error.response?.data?.error || 'Profile update failed'
      toast.error(message)
      return false
    } finally {
      isLoading.value = false
    }
  }

  // Initialize auth state
  const init = async () => {
    await checkAuth()
  }

  // Force cleanup of invalid tokens
  const forceCleanup = () => {
    cleanupInvalidTokens()
    user.value = null
    isAuthenticated.value = false
  }

  return {
    // State
    user,
    isAuthenticated,
    isLoading,

    // Getters
    isAdmin,
    displayName,

    // Actions
    login,
    register,
    logout,
    checkAuth,
    changePassword,
    updateProfile,
    init,
    forceCleanup,
  }
})
