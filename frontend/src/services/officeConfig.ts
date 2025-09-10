import { ref, computed } from 'vue'

// Office document server configuration
const documentServerUrl = ref(import.meta.env.VITE_ONLYOFFICE_DOCUMENT_SERVER_URL || 'http://192.168.1.101')
const secretKey = ref(import.meta.env.VITE_ONLYOFFICE_SECRET_KEY || 'oyLbTv339qrQgW8uRUJ2N0lXuRtFh7qd')

// Office document types and their extensions
const officeDocumentTypes = {
  word: {
    name: 'Word Document',
    extensions: ['docx', 'doc', 'odt', 'rtf', 'txt'],
    mimeTypes: [
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/msword',
      'application/vnd.oasis.opendocument.text',
      'application/rtf',
      'text/plain'
    ]
  },
  excel: {
    name: 'Excel Spreadsheet',
    extensions: ['xlsx', 'xls', 'ods', 'csv'],
    mimeTypes: [
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.ms-excel',
      'application/vnd.oasis.opendocument.spreadsheet',
      'text/csv'
    ]
  },
  powerpoint: {
    name: 'PowerPoint Presentation',
    extensions: ['pptx', 'ppt', 'odp'],
    mimeTypes: [
      'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      'application/vnd.ms-powerpoint',
      'application/vnd.oasis.opendocument.presentation'
    ]
  }
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
    if (type.extensions.some(ext => 
      extension === ext || fileName.endsWith(`.${ext}`)
    )) {
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
    if (config.extensions.some(ext => 
      extension === ext || fileName.endsWith(`.${ext}`)
    )) {
      return type
    }
  }
  
  return null
}

// Get document type name
const getDocumentTypeName = (file: any): string => {
  const type = getDocumentType(file)
  return type ? officeDocumentTypes[type as keyof typeof officeDocumentTypes].name : 'Office Document'
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
  
  if (!documentServerUrl.value) {
    errors.push('Document server URL is required')
  }
  
  if (!secretKey.value) {
    errors.push('Secret key is required')
  }
  
  // Validate URL format
  try {
    new URL(documentServerUrl.value)
  } catch {
    errors.push('Document server URL is invalid')
  }
  
  return {
    valid: errors.length === 0,
    errors
  }
}

// Update configuration
const updateConfig = (newConfig: { documentServerUrl?: string; secretKey?: string }) => {
  if (newConfig.documentServerUrl !== undefined) {
    documentServerUrl.value = newConfig.documentServerUrl
  }
  if (newConfig.secretKey !== undefined) {
    secretKey.value = newConfig.secretKey
  }
}

// Computed properties
const config = computed(() => ({
  documentServerUrl: documentServerUrl.value,
  secretKey: secretKey.value
}))

const supportedExtensions = computed(() => getSupportedExtensions())
const supportedMimeTypes = computed(() => getSupportedMimeTypes())

// Export the composable
export function useOfficeConfig() {
  return {
    // Configuration
    documentServerUrl,
    secretKey,
    config,
    
    // Document detection
    isOfficeDocument,
    getDocumentType,
    getDocumentTypeName,
    
    // Supported formats
    supportedExtensions,
    supportedMimeTypes,
    
    // Configuration management
    validateConfig,
    updateConfig,
    
    // Document types
    officeDocumentTypes
  }
}

// Export types
export type OfficeDocumentType = 'word' | 'excel' | 'powerpoint'
export type OfficeConfig = {
  documentServerUrl: string
  secretKey: string
}
