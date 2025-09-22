import axios from 'axios'
import { tokenStorage } from '@/utils/storage'

// Create axios instance
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8002',
  timeout: 30000, // 30 seconds for regular requests
})

// Create separate axios instance for uploads with longer timeout
const uploadApi = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8002',
  timeout: 600000, // 5 minutes for upload requests
})

// Request interceptor to add auth token
const addAuthInterceptor = (axiosInstance: typeof api) => {
  axiosInstance.interceptors.request.use(
    (config) => {
      const token = tokenStorage.getAccessToken()
      console.log('[API Interceptor] Request to:', config.url)
      console.log('[API Interceptor] Token available:', !!token)
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
        console.log('[API Interceptor] Authorization header set')
      } else {
        console.log('[API Interceptor] No token available, request will be unauthenticated')
      }
      return config
    },
    (error) => {
      return Promise.reject(error)
    },
  )
}

// Add auth interceptor to both instances
addAuthInterceptor(api)
addAuthInterceptor(uploadApi)

// Response interceptor to handle token refresh
const addResponseInterceptor = (axiosInstance: typeof api) => {
  axiosInstance.interceptors.response.use(
    (response) => response,
    async (error) => {
      const originalRequest = error.config

      // Don't retry refresh token requests to avoid infinite loops
      if (originalRequest.url?.includes('/api/auth/refresh/')) {
        // If refresh token request fails, clear tokens and redirect to login
        tokenStorage.removeAllTokens()
        window.location.href = '/login'
        return Promise.reject(error)
      }

      if (error.response?.status === 401 && !originalRequest._retry) {
        originalRequest._retry = true

        try {
          const refreshToken = tokenStorage.getRefreshToken()
          if (refreshToken) {
            // Use a separate axios instance for refresh to avoid interceptor loops
            const refreshResponse = await axios.post(
              '/api/auth/refresh/',
              {
                refresh_token: refreshToken,
              },
              {
                baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8002',
                timeout: 10000,
              },
            )

            const { access, refresh } = refreshResponse.data
            tokenStorage.setAccessToken(access)
            tokenStorage.setRefreshToken(refresh)

            originalRequest.headers.Authorization = `Bearer ${access}`
            return axiosInstance(originalRequest)
          } else {
            // No refresh token available, redirect to login
            tokenStorage.removeAllTokens()
            window.location.href = '/login'
            return Promise.reject(error)
          }
        } catch (refreshError) {
          // Refresh failed, clear tokens and redirect to login
          console.error('Token refresh failed:', refreshError)
          tokenStorage.removeAllTokens()
          window.location.href = '/login'
          return Promise.reject(refreshError)
        }
      }

      return Promise.reject(error)
    },
  )
}

// Add response interceptor to both instances
addResponseInterceptor(api)
addResponseInterceptor(uploadApi)

// Utility function to check and clean up invalid tokens
export const cleanupInvalidTokens = () => {
  const accessToken = tokenStorage.getAccessToken()
  const refreshToken = tokenStorage.getRefreshToken()

  // If we have tokens, try to validate them
  if (accessToken || refreshToken) {
    // Check if tokens are expired or malformed
    try {
      if (accessToken) {
        const payload = JSON.parse(atob(accessToken.split('.')[1]))
        const now = Math.floor(Date.now() / 1000)
        if (payload.exp < now) {
          // Access token is expired, remove it
          tokenStorage.removeAccessToken()
        }
      }
    } catch (error) {
      // Token is malformed, remove it
      tokenStorage.removeAccessToken()
    }

    try {
      if (refreshToken) {
        const payload = JSON.parse(atob(refreshToken.split('.')[1]))
        const now = Math.floor(Date.now() / 1000)
        if (payload.exp < now) {
          // Refresh token is expired, remove it
          tokenStorage.removeRefreshToken()
        }
      }
    } catch (error) {
      // Token is malformed, remove it
      tokenStorage.removeRefreshToken()
    }
  }
}

// Clean up invalid tokens on module load
cleanupInvalidTokens()

// Auth API
export const authAPI = {
  login: (credentials: { username: string; password: string }) =>
    api.post('/api/auth/login/', credentials),

  register: (userData: {
    username: string
    email: string
    password: string
    first_name?: string
    last_name?: string
  }) => api.post('/api/auth/register/', userData),

  refresh: (refreshToken: string) =>
    api.post('/api/auth/refresh/', { refresh_token: refreshToken }),

  logout: (refreshToken: string) => api.post('/api/auth/logout/', { refresh_token: refreshToken }),

  profile: () => api.get('/api/auth/profile/'),

  changePassword: (passwords: { old_password: string; new_password: string }) =>
    api.put('/api/auth/change-password/', passwords),
}

// Files API
export const filesAPI = {
  list: (params?: {
    page?: number
    page_size?: number
    type?: string
    parent?: number
    owner?: number
    visibility?: string
    extension?: string
    shared_to_me?: boolean
    shared_to_my_groups?: boolean
  }) => api.get('/api/files/', { params }),

  get: (id: number) => api.get(`/api/files/${id}/`),

  create: (data: {
    name: string
    path: string
    item_type: string
    parent?: number
    visibility?: string
  }) => api.post('/api/files/', data),

  update: (id: number, data: { name?: string; visibility?: string }) =>
    api.put(`/api/files/${id}/`, data),

  patch: (id: number, data: { name?: string; visibility?: string }) =>
    api.patch(`/api/files/${id}/`, data),

  delete: (id: number) => api.delete(`/api/files/${id}/`),

  getFile: (id: number) => api.get(`/api/files/${id}/`),

  download: (id: number, params?: { download?: string }) =>
    api.get(`/api/files/${id}/download/`, { responseType: 'blob', params }),

  stream: (id: number, range?: string) => {
    const headers = range ? { Range: range } : {}
    return api.get(`/api/files/${id}/stream/`, { 
      responseType: 'blob', 
      headers,
      timeout: 0 // No timeout for streaming
    })
  },

  getThumbnail: (id: number) => api.get(`/api/files/${id}/thumbnail/`, { responseType: 'blob' }),

  preview: (id: number) => api.get(`/api/files/${id}/preview/`),

  permissions: (id: number) => api.get(`/api/files/${id}/permissions/`),

  updateVisibility: (
    id: number,
    data: { visibility: string; shared_users?: number[]; shared_groups?: number[] },
  ) => api.put(`/api/files/${id}/update_visibility/`, data),

  listChildren: (parentId?: number) =>
    api.get('/api/files/list_children/', { params: { parent_id: parentId } }),

  createDirectory: (data: { name: string; parent_id?: number; visibility?: string }) =>
    api.post('/api/files/create_directory/', data),

  search: (
    query: string,
    params?: {
      node_id?: number
      recursive?: boolean
      type?: string
      limit?: number
    },
  ) =>
    api.get('/api/files/search/', {
      params: {
        q: query,
        ...(params?.node_id && { node_id: params.node_id }),
        recursive: params?.recursive ?? true,
        ...(params?.type && { type: params.type }),
        ...(params?.limit && { limit: params.limit }),
      },
    }),

  scanDirectory: (path: string) => api.post('/api/files/scan_directory/', { path }),

  // Recursive directory sharing
  shareRecursively: (
    fileId: number,
    data: {
      share_type: 'user' | 'group'
      target_id: number
      permission_types: string[]
      expires_at?: string
    },
  ) => api.post(`/api/files/${fileId}/share_recursively/`, data),

  // Recursive directory unsharing
  unshareRecursively: (
    fileId: number,
    data: {
      share_type: 'user' | 'group'
      target_id: number
      permission_types?: string[]
    },
  ) => api.post(`/api/files/${fileId}/unshare_recursively/`, data),

  // Update file content
  updateContent: (fileId: number, formData: FormData, onProgress?: (progressEvent: any) => void) =>
    uploadApi.patch(`/api/files/${fileId}/update_content/`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: onProgress,
    }),

  // Create new files
  createTextFile: (data: {
    name: string
    content?: string
    parent_id?: number
    visibility?: string
  }) => api.post('/api/create-file/', { type: 'text', ...data }),

  createOfficeDocument: (data: {
    name: string
    document_type: 'docx' | 'xlsx' | 'pptx'
    parent_id?: number
    visibility?: string
  }) => api.post('/api/create-file/', { type: 'office', ...data }),
}

// Upload API
export const uploadAPI = {
  upload: (formData: FormData, onProgress?: (progressEvent: any) => void) =>
    uploadApi.post('/api/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: onProgress,
    }),
}

// Operations API
export const operationsAPI = {
  execute: (operation: 'copy' | 'move' | 'delete', fileIds: number[], destinationId?: number) =>
    api.post('/api/operations/', { operation, file_ids: fileIds, destination_id: destinationId }),
}

// Deleted Files API
export const deletedFilesAPI = {
  list: () => api.get('/api/deleted-files/'),
  restore: (fileIds: number[]) => api.post('/api/deleted-files/restore/', { file_ids: fileIds }),
  hardDelete: (fileIds: number[]) =>
    api.post('/api/deleted-files/hard-delete/', { file_ids: fileIds }),
}

// Permissions API
export const permissionsAPI = {
  list: (params?: { file?: number; user?: number; group?: number }) =>
    api.get('/api/permissions/', { params }),

  create: (data: {
    file: number
    user: number | null
    group: number | null
    permission_type: string
    expires_at?: string
  }) => api.post('/api/permissions/', data),

  update: (
    id: number,
    data: { permission_type?: string; expires_at?: string; is_active?: boolean },
  ) => api.put(`/api/permissions/${id}/`, data),

  delete: (id: number) => api.delete(`/api/permissions/${id}/`),

  // Search methods for user and group selection
  searchUsers: (params: { query: string }) =>
    api.get('/api/search/users/', { params: { q: params.query } }),

  searchGroups: (params: { query: string }) =>
    api.get('/api/search/groups/', { params: { q: params.query } }),
}

// Users API
export const usersAPI = {
  list: (params?: { search?: string; page?: number; page_size?: number }) =>
    api.get('/api/users/', { params }),

  get: (id: number) => api.get(`/api/users/${id}/`),

  create: (data: {
    username: string
    email: string
    first_name?: string
    last_name?: string
    password: string
    groups?: number[]
  }) => api.post('/api/users/', data),

  update: (
    id: number,
    data: {
      username?: string
      email?: string
      first_name?: string
      last_name?: string
      password?: string
      groups?: number[]
    },
  ) => api.put(`/api/users/${id}/`, data),

  delete: (id: number) => api.delete(`/api/users/${id}/`),

  // Search method (existing)
  search: (params: { query: string }) =>
    api.get('/api/search/users/', { params: { q: params.query } }),
}

// Groups API
export const groupsAPI = {
  list: (params?: { search?: string; page?: number; page_size?: number }) =>
    api.get('/api/groups/', { params }),

  get: (id: number) => api.get(`/api/groups/${id}/`),

  create: (data: { name: string; description?: string; members?: number[] }) =>
    api.post('/api/groups/', data),

  update: (
    id: number,
    data: {
      name?: string
      description?: string
      members?: number[]
    },
  ) => api.put(`/api/groups/${id}/`, data),

  delete: (id: number) => api.delete(`/api/groups/${id}/`),

  // Search method (existing)
  search: (params: { query: string }) =>
    api.get('/api/groups/search/', { params: { q: params.query } }),
}

// Permission Requests API
export const permissionRequestsAPI = {
  list: (params?: { file?: number; requester?: number; status?: string }) =>
    api.get('/api/permission-requests/', { params }),

  create: (data: { file: number; requested_permissions: string; reason?: string }) =>
    api.post('/api/permission-requests/', data),

  update: (id: number, data: { status: string; review_notes?: string }) =>
    api.put(`/api/permission-requests/${id}/`, data),
}

// Tags API
export const tagsAPI = {
  list: () => api.get('/api/tags/'),
  create: (data: { name: string; color?: string }) => api.post('/api/tags/', data),
  update: (id: number, data: { name?: string; color?: string }) =>
    api.put(`/api/tags/${id}/`, data),
  delete: (id: number) => api.delete(`/api/tags/${id}/`),
}

// Access Logs API
export const accessLogsAPI = {
  list: (params?: {
    file?: number
    user?: number
    action?: string
    start_date?: string
    end_date?: string
  }) => api.get('/api/access-logs/', { params }),
}

export default api
