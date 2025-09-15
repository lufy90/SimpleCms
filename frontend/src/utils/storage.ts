// Storage utility that works in both web and Electron contexts
import Cookies from 'js-cookie'

// Check if we're running in Electron
const isElectron = () => {
  // Multiple ways to detect Electron
  const hasElectronProcess = typeof window !== 'undefined' && 
         (window as any).process && 
         (window as any).process.type === 'renderer'
  
  const hasElectronAPI = typeof window !== 'undefined' && 
         (window as any).electronAPI
  
  const hasElectronEnv = typeof window !== 'undefined' && 
         (window as any).navigator && 
         (window as any).navigator.userAgent && 
         (window as any).navigator.userAgent.includes('Electron')
  
  const isElectronEnv = hasElectronProcess || hasElectronAPI || hasElectronEnv
  
  // Debug logging
  if (typeof window !== 'undefined') {
    console.log('Environment detection:', {
      hasWindow: typeof window !== 'undefined',
      hasProcess: !!(window as any).process,
      processType: (window as any).process?.type,
      hasElectronAPI: !!hasElectronAPI,
      hasElectronEnv: hasElectronEnv,
      userAgent: (window as any).navigator?.userAgent,
      isElectron: isElectronEnv
    })
  }
  
  return isElectronEnv
}

// Electron-safe storage interface
interface StorageInterface {
  get: (key: string) => string | undefined
  set: (key: string, value: string, options?: any) => void
  remove: (key: string) => void
}

// Web storage implementation (using cookies)
const webStorage: StorageInterface = {
  get: (key: string) => {
    const value = Cookies.get(key)
    console.log(`[Web Storage] GET ${key}:`, value ? '***' : 'undefined')
    return value
  },
  set: (key: string, value: string, options?: any) => {
    Cookies.set(key, value, options)
    console.log(`[Web Storage] SET ${key}:`, '***')
  },
  remove: (key: string) => {
    Cookies.remove(key)
    console.log(`[Web Storage] REMOVE ${key}`)
  }
}

// Electron storage implementation (using localStorage)
const electronStorage: StorageInterface = {
  get: (key: string) => {
    try {
      const value = localStorage.getItem(key) || undefined
      console.log(`[Electron Storage] GET ${key}:`, value ? '***' : 'undefined')
      return value
    } catch (error) {
      console.error('Failed to get item from localStorage:', error)
      return undefined
    }
  },
  set: (key: string, value: string, options?: any) => {
    try {
      localStorage.setItem(key, value)
      console.log(`[Electron Storage] SET ${key}:`, '***')
    } catch (error) {
      console.error('Failed to set item in localStorage:', error)
    }
  },
  remove: (key: string) => {
    try {
      localStorage.removeItem(key)
      console.log(`[Electron Storage] REMOVE ${key}`)
    } catch (error) {
      console.error('Failed to remove item from localStorage:', error)
    }
  }
}

// Choose the appropriate storage implementation
const storage: StorageInterface = (() => {
  const isElectronEnv = isElectron()
  console.log('[Storage] Using storage type:', isElectronEnv ? 'localStorage (Electron)' : 'cookies (Web)')
  
  // If we're in Electron, use localStorage
  if (isElectronEnv) {
    return electronStorage
  }
  
  // For web, try cookies first, but fallback to localStorage if cookies fail
  try {
    // Test if cookies work
    const testKey = '__storage_test__'
    webStorage.set(testKey, 'test')
    const testValue = webStorage.get(testKey)
    webStorage.remove(testKey)
    
    if (testValue === 'test') {
      console.log('[Storage] Cookies working, using web storage')
      return webStorage
    } else {
      console.log('[Storage] Cookies not working, falling back to localStorage')
      return electronStorage
    }
  } catch (error) {
    console.log('[Storage] Cookies failed, falling back to localStorage:', error)
    return electronStorage
  }
})()

// Export the storage interface
export const tokenStorage = {
  getAccessToken: () => storage.get('access_token'),
  setAccessToken: (token: string) => storage.set('access_token', token, { expires: 1 / 24 }), // 1 hour
  getRefreshToken: () => storage.get('refresh_token'),
  setRefreshToken: (token: string) => storage.set('refresh_token', token, { expires: 7 }), // 7 days
  removeAccessToken: () => storage.remove('access_token'),
  removeRefreshToken: () => storage.remove('refresh_token'),
  removeAllTokens: () => {
    storage.remove('access_token')
    storage.remove('refresh_token')
  }
}

// Export the storage instance for other uses
export { storage }
export default storage
