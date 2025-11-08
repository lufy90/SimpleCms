// Frontend configuration

/**
 * Get the API base URL based on the frontend URL
 * If VITE_API_BASE_URL is set, it takes priority
 * Otherwise, uses the current hostname with port 8002
 */
const getApiBaseUrl = (): string => {
  // Priority 1: Use environment variable if set
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL
  }

  // Priority 2: Auto-detect from current frontend URL
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname
    const protocol = window.location.protocol
    const port = '8002' // Default API port
    
    // Use the same protocol and hostname as the frontend
    return `${protocol}//${hostname}:${port}`
  }

  // Fallback: localhost for SSR or when window is not available
  return 'http://localhost:8002'
}

export const config = {
  API_BASE_URL: getApiBaseUrl(),
}

