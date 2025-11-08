// Frontend configuration

type ApiHostType = 'static' | 'dynamic'
const API_HOST_TYPE: ApiHostType = 'dynamic' // 'static' or 'dynamic'
var API_HOST = 'localhost' // Only used if API_HOST_TYPE is 'static' (hostname only, no protocol/port)
var API_PROTOCOL = 'http' // 'http' or 'https', only used if API_HOST_TYPE is 'static'
const API_PORT = '8001'

/**
 * Get the API base URL based on the frontend URL
 * If API_HOST_TYPE is 'static', uses the configured API_HOST
 * Otherwise, auto-detects from current frontend URL
 */
const getApiBaseUrl = (): string => {
  // Priority 1: Use static configuration if set
  if ((API_HOST_TYPE as ApiHostType) === 'static' && API_HOST) {
    return `${API_PROTOCOL}://${API_HOST}:${API_PORT}`
  }

  // Priority 2: Auto-detect from current frontend URL
  if (typeof window !== 'undefined') {
    API_HOST = window.location.hostname
    API_PROTOCOL = window.location.protocol
    const port = API_PORT // Default API port

    // Use the same protocol and hostname as the frontend
    return `${API_PROTOCOL}//${API_HOST}:${API_PORT}`
  }

  // Fallback: localhost for SSR or when window is not available
  return 'http://localhost:8001'
}

export const config = {
  API_BASE_URL: getApiBaseUrl(),
  API_HOST_TYPE: API_HOST_TYPE,
  API_HOST: API_HOST,
  API_PROTOCOL: API_PROTOCOL,
  API_PORT: API_PORT,
}
