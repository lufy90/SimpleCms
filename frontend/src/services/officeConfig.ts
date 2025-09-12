import { ref, computed } from 'vue'
import api from './api'

// Office document server configuration - now fetched from backend API
const documentServerUrl = ref('')
const apiBaseUrl = ref('')
const frontendUrl = ref('')
const settingsLoaded = ref(false)
const settingsError = ref('')
const onlyOfficeAvailable = ref(false)

// Load OnlyOffice settings from backend API
const loadOnlyOfficeSettings = async () => {
  if (settingsLoaded.value) {
    return // Settings already loaded
  }

  try {
    const response = await api.get('/api/office/settings/')
    const settings = response.data

    documentServerUrl.value = settings.documentServerUrl
    apiBaseUrl.value = settings.apiBaseUrl
    frontendUrl.value = settings.frontendUrl
    onlyOfficeAvailable.value = settings.available || false
    settingsLoaded.value = true
    settingsError.value = ''
  } catch (error: any) {
    console.error('Failed to load OnlyOffice settings:', error)
    settingsError.value = error.response?.data?.error || 'Failed to load OnlyOffice settings'
    settingsLoaded.value = true
    onlyOfficeAvailable.value = false

    // Clear all settings on API failure - OnlyOffice will not be available
    documentServerUrl.value = ''
    apiBaseUrl.value = ''
    frontendUrl.value = ''
  }
}

// Ensure settings are loaded before use
const ensureSettingsLoaded = async () => {
  if (!settingsLoaded.value) {
    await loadOnlyOfficeSettings()
  }
}

// Check if OnlyOffice is available
const isOnlyOfficeAvailable = computed(() => {
  return (
    settingsLoaded.value &&
    !settingsError.value &&
    onlyOfficeAvailable.value &&
    documentServerUrl.value
  )
})

// Office document types and their extensions
const officeDocumentTypes = {
  word: {
    name: 'Word Document',
    extensions: ['docx', 'doc', 'odt', 'rtf'],
    mimeTypes: [
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/msword',
      'application/vnd.oasis.opendocument.text',
      'application/rtf',
      'text/plain',
    ],
  },
  excel: {
    name: 'Excel Spreadsheet',
    extensions: ['xlsx', 'xls', 'ods', 'csv'],
    mimeTypes: [
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.ms-excel',
      'application/vnd.oasis.opendocument.spreadsheet',
      'text/csv',
    ],
  },
  powerpoint: {
    name: 'PowerPoint Presentation',
    extensions: ['pptx', 'ppt', 'odp'],
    mimeTypes: [
      'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      'application/vnd.ms-powerpoint',
      'application/vnd.oasis.opendocument.presentation',
    ],
  },
}

// Office document detection
const isOfficeDocument = (file: any): boolean => {
  if (!file) return false

  const mimeType = file.storage?.mime_type || ''
  const extension = file.storage?.extension || ''
  const fileName = file.name.toLowerCase()

  // Check by MIME type
  for (const type of Object.values(officeDocumentTypes)) {
    if (type.mimeTypes.includes(mimeType)) {
      return true
    }
  }

  // Check by extension
  for (const type of Object.values(officeDocumentTypes)) {
    if (type.extensions.some((ext) => extension === ext || fileName.endsWith(`.${ext}`))) {
      return true
    }
  }

  return false
}

// Get document type
const getDocumentType = (file: any): string | null => {
  if (!file) return null

  const mimeType = file.storage?.mime_type || ''
  const extension = file.storage?.extension || ''
  const fileName = file.name.toLowerCase()

  // Check by MIME type first
  for (const [type, config] of Object.entries(officeDocumentTypes)) {
    if (config.mimeTypes.includes(mimeType)) {
      return type
    }
  }

  // Check by extension
  for (const [type, config] of Object.entries(officeDocumentTypes)) {
    if (config.extensions.some((ext) => extension === ext || fileName.endsWith(`.${ext}`))) {
      return type
    }
  }

  return null
}

// Get document type name
const getDocumentTypeName = (file: any): string => {
  const type = getDocumentType(file)
  return type
    ? officeDocumentTypes[type as keyof typeof officeDocumentTypes].name
    : 'Office Document'
}

// Get supported extensions
const getSupportedExtensions = (): string[] => {
  const extensions: string[] = []
  for (const type of Object.values(officeDocumentTypes)) {
    extensions.push(...type.extensions)
  }
  return [...new Set(extensions)]
}

// Get supported MIME types
const getSupportedMimeTypes = (): string[] => {
  const mimeTypes: string[] = []
  for (const type of Object.values(officeDocumentTypes)) {
    mimeTypes.push(...type.mimeTypes)
  }
  return [...new Set(mimeTypes)]
}

// Configuration validation
const validateConfig = (): { valid: boolean; errors: string[] } => {
  const errors: string[] = []

  if (settingsError.value) {
    errors.push(`OnlyOffice configuration error: ${settingsError.value}`)
    return {
      valid: false,
      errors,
    }
  }

  if (!onlyOfficeAvailable.value) {
    errors.push('OnlyOffice is not available')
  }

  if (!documentServerUrl.value) {
    errors.push('OnlyOffice document server is not available')
  }

  // Validate URL format if we have a URL
  if (documentServerUrl.value) {
    try {
      new URL(documentServerUrl.value)
    } catch {
      errors.push('Document server URL is invalid')
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  }
}

// Computed properties
const config = computed(() => ({
  documentServerUrl: documentServerUrl.value,
  apiBaseUrl: apiBaseUrl.value,
  frontendUrl: frontendUrl.value,
  available: onlyOfficeAvailable.value,
}))

const supportedExtensions = computed(() => getSupportedExtensions())
const supportedMimeTypes = computed(() => getSupportedMimeTypes())

// Export the composable
export function useOfficeConfig() {
  return {
    // Configuration
    documentServerUrl,
    apiBaseUrl,
    frontendUrl,
    config,
    settingsLoaded,
    settingsError,
    isOnlyOfficeAvailable,
    onlyOfficeAvailable,

    // Document detection
    isOfficeDocument,
    getDocumentType,
    getDocumentTypeName,

    // Supported formats
    supportedExtensions,
    supportedMimeTypes,

    // Configuration management
    validateConfig,
    loadOnlyOfficeSettings,
    ensureSettingsLoaded,

    // Document types
    officeDocumentTypes,
  }
}

// Export types
export type OfficeDocumentType = 'word' | 'excel' | 'powerpoint'
export type OfficeConfig = {
  documentServerUrl: string
  apiBaseUrl: string
  frontendUrl: string
  available: boolean
}
