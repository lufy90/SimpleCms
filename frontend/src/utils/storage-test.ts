// Test utility to verify storage system works correctly
import { tokenStorage } from './storage'

export const testStorage = () => {
  console.log('Testing storage system...')

  // Test setting tokens
  tokenStorage.setAccessToken('test-access-token')
  tokenStorage.setRefreshToken('test-refresh-token')

  // Test getting tokens
  const accessToken = tokenStorage.getAccessToken()
  const refreshToken = tokenStorage.getRefreshToken()

  console.log('Access token:', accessToken)
  console.log('Refresh token:', refreshToken)

  // Test removing tokens
  tokenStorage.removeAllTokens()

  const accessTokenAfter = tokenStorage.getAccessToken()
  const refreshTokenAfter = tokenStorage.getRefreshToken()

  console.log('Access token after removal:', accessTokenAfter)
  console.log('Refresh token after removal:', refreshTokenAfter)

  console.log('Storage test completed!')
}

// Export for use in development
if (import.meta.env.DEV) {
  ;(window as any).testStorage = testStorage
}
