// Debug utilities for Electron development
import { tokenStorage } from './storage'

export const debugStorage = () => {
  console.log('=== Storage Debug Information ===')
  
  // Check environment
  console.log('Environment:', {
    hasWindow: typeof window !== 'undefined',
    hasProcess: !!(window as any).process,
    processType: (window as any).process?.type,
    hasElectronAPI: !!(window as any).electronAPI,
    userAgent: (window as any).navigator?.userAgent
  })
  
  // Check current tokens
  const accessToken = tokenStorage.getAccessToken()
  const refreshToken = tokenStorage.getRefreshToken()
  
  console.log('Current tokens:', {
    accessToken: accessToken ? 'Present' : 'Missing',
    refreshToken: refreshToken ? 'Present' : 'Missing',
    accessTokenLength: accessToken?.length || 0,
    refreshTokenLength: refreshToken?.length || 0
  })
  
  // Test storage operations
  console.log('Testing storage operations...')
  const testKey = '__debug_test__'
  const testValue = 'debug_test_value'
  
  tokenStorage.setAccessToken(testValue)
  const retrieved = tokenStorage.getAccessToken()
  console.log('Storage test:', {
    set: testValue,
    retrieved: retrieved,
    match: retrieved === testValue
  })
  
  // Clean up test
  tokenStorage.removeAccessToken()
  const afterCleanup = tokenStorage.getAccessToken()
  console.log('After cleanup:', afterCleanup || 'undefined')
  
  console.log('=== End Debug Information ===')
}

// Make it available globally in development
if (import.meta.env.DEV) {
  (window as any).debugStorage = debugStorage
  ;(window as any).tokenStorage = tokenStorage
}
