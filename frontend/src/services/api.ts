import axios from 'axios'
import Cookies from 'js-cookie'

// Create axios instance
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8002',
  timeout: 30000,
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = Cookies.get('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        const refreshToken = Cookies.get('refresh_token')
        if (refreshToken) {
          const response = await api.post('/api/auth/refresh/', {
            refresh_token: refreshToken,
          })
          
          const { access, refresh } = response.data
          Cookies.set('access_token', access, { expires: 1/24 }) // 1 hour
          Cookies.set('refresh_token', refresh, { expires: 7 }) // 7 days
          
          originalRequest.headers.Authorization = `Bearer ${access}`
          return api(originalRequest)
        }
      } catch (refreshError) {
        // Refresh failed, redirect to login
        Cookies.remove('access_token')
        Cookies.remove('refresh_token')
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

// Auth API
export const authAPI = {
  login: (credentials: { username: string; password: string }) =>
    api.post('/api/auth/login/', credentials),
  
  register: (userData: { username: string; email: string; password: string; first_name?: string; last_name?: string }) =>
    api.post('/api/auth/register/', userData),
  
  refresh: (refreshToken: string) =>
    api.post('/api/auth/refresh/', { refresh_token: refreshToken }),
  
  logout: (refreshToken: string) =>
    api.post('/api/auth/logout/', { refresh_token: refreshToken }),
  
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
  }) => api.get('/api/files/', { params }),
  
  get: (id: number) => api.get(`/api/files/${id}/`),
  
  create: (data: { name: string; path: string; item_type: string; parent?: number; visibility?: string }) =>
    api.post('/api/files/', data),
  
  update: (id: number, data: { name?: string; visibility?: string }) =>
    api.put(`/api/files/${id}/`, data),
  
  delete: (id: number) => api.delete(`/api/files/${id}/`),
  
  download: (id: number) => api.get(`/api/files/${id}/download/`, { responseType: 'blob' }),
  
  preview: (id: number) => api.get(`/api/files/${id}/preview/`),
  
  permissions: (id: number) => api.get(`/api/files/${id}/permissions/`),
  
  updateVisibility: (id: number, data: { visibility: string; shared_users?: number[]; shared_groups?: number[] }) =>
    api.put(`/api/files/${id}/update_visibility/`, data),
    
  listChildren: (parentId?: number) => 
    api.get('/api/files/list_children/', { params: { parent_id: parentId } }),
  
  createDirectory: (data: { name: string; parent_id?: number; visibility?: string }) =>
    api.post('/api/files/create_directory/', data),
  
  search: (query: string, params?: { type?: string; limit?: number }) =>
    api.get('/api/files/search/', { params: { q: query, ...params } }),
  
  scanDirectory: (path: string) => api.post('/api/files/scan_directory/', { path }),
}

// Upload API
export const uploadAPI = {
  upload: (formData: FormData) => api.post('/api/upload/', formData),
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
  hardDelete: (fileIds: number[]) => api.post('/api/deleted-files/hard-delete/', { file_ids: fileIds }),
}

// Permissions API
export const permissionsAPI = {
  list: (params?: { file?: number; user?: number; group?: number }) =>
    api.get('/api/permissions/', { params }),
  
  create: (data: { file: number; user?: number; group?: number; permission_type: string; expires_at?: string }) =>
    api.post('/api/permissions/', data),
  
  update: (id: number, data: { permission_type?: string; expires_at?: string; is_active?: boolean }) =>
    api.put(`/api/permissions/${id}/`, data),
  
  delete: (id: number) => api.delete(`/api/permissions/${id}/`),
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
  update: (id: number, data: { name?: string; color?: string }) => api.put(`/api/tags/${id}/`, data),
  delete: (id: number) => api.delete(`/api/tags/${id}/`),
}

// Access Logs API
export const accessLogsAPI = {
  list: (params?: { file?: number; user?: number; action?: string; start_date?: string; end_date?: string }) =>
    api.get('/api/access-logs/', { params }),
}

export default api
