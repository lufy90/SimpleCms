// Electron utilities for download and new tab functionality
import { tokenStorage } from './storage'
import { config } from '@/config'

// Check if we're running in Electron
const isElectron = () => {
  const hasElectronProcess =
    typeof window !== 'undefined' &&
    (window as any).process &&
    (window as any).process.type === 'renderer'

  const hasElectronAPI = typeof window !== 'undefined' && (window as any).electronAPI

  const hasElectronEnv =
    typeof window !== 'undefined' &&
    (window as any).navigator &&
    (window as any).navigator.userAgent &&
    (window as any).navigator.userAgent.includes('Electron')

  return hasElectronProcess || hasElectronAPI || hasElectronEnv
}

// Electron API interface
interface ElectronAPI {
  downloadFile: (url: string, filename: string) => Promise<void>
  openInNewTab: (url: string) => Promise<void>
  showSaveDialog: (filename: string) => Promise<string | null>
}

// Web fallback implementations
const webDownloadFile = async (url: string, filename: string) => {
  try {
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const blob = await response.blob()
    const downloadUrl = window.URL.createObjectURL(blob)

    const link = document.createElement('a')
    link.href = downloadUrl
    link.download = filename
    link.style.display = 'none'

    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    window.URL.revokeObjectURL(downloadUrl)
  } catch (error) {
    console.error('Web download failed:', error)
    throw error
  }
}

const webOpenInNewTab = async (url: string) => {
  window.open(url, '_blank')
}

const webShowSaveDialog = async (filename: string): Promise<string | null> => {
  // For web, we can't show a native save dialog, so return the filename
  return filename
}

// Electron implementations (these would need to be implemented in the main process)
const electronDownloadFile = async (url: string, filename: string) => {
  if ((window as any).electronAPI?.downloadFile) {
    return (window as any).electronAPI.downloadFile(url, filename)
  } else {
    // Fallback to web implementation if Electron API not available
    return webDownloadFile(url, filename)
  }
}

const electronOpenInNewTab = async (url: string) => {
  if ((window as any).electronAPI?.openInNewTab) {
    return (window as any).electronAPI.openInNewTab(url)
  } else {
    // Fallback to web implementation
    return webOpenInNewTab(url)
  }
}

const electronShowSaveDialog = async (filename: string): Promise<string | null> => {
  if ((window as any).electronAPI?.showSaveDialog) {
    return (window as any).electronAPI.showSaveDialog(filename)
  } else {
    // Fallback to web implementation
    return webShowSaveDialog(filename)
  }
}

// Main API functions
export const electronUtils = {
  /**
   * Download a file using the appropriate method for the current environment
   * @param fileId - The file ID to download
   * @param filename - The filename for the download
   * @param forceDownload - Whether to force download (vs inline display)
   */
  downloadFile: async (fileId: number, filename: string, forceDownload: boolean = true) => {
    const token = tokenStorage.getAccessToken()
    if (!token) {
      throw new Error('Authentication required for download')
    }

    const downloadUrl = `${config.API_BASE_URL}/api/files/${fileId}/download_with_token/?token=${encodeURIComponent(token)}&download=${forceDownload}`

    if (isElectron()) {
      return electronDownloadFile(downloadUrl, filename)
    } else {
      return webDownloadFile(downloadUrl, filename)
    }
  },

  /**
   * Open a URL in a new tab using the appropriate method for the current environment
   * @param fileId - The file ID to open
   * @param forceDownload - Whether to force download (vs inline display)
   */
  openInNewTab: async (fileId: number, forceDownload: boolean = true) => {
    const token = tokenStorage.getAccessToken()
    if (!token) {
      throw new Error('Authentication required')
    }

    const url = `${config.API_BASE_URL}/api/files/${fileId}/download_with_token/?token=${encodeURIComponent(token)}&download=${forceDownload}`

    if (isElectron()) {
      return electronOpenInNewTab(url)
    } else {
      return webOpenInNewTab(url)
    }
  },

  /**
   * Show a save dialog and download a file (Electron only)
   * @param fileId - The file ID to download
   * @param filename - The suggested filename
   */
  showSaveDialogAndDownload: async (fileId: number, filename: string) => {
    if (!isElectron()) {
      // For web, just use regular download
      return electronUtils.downloadFile(fileId, filename, true)
    }

    const token = tokenStorage.getAccessToken()
    if (!token) {
      throw new Error('Authentication required for download')
    }

    const downloadUrl = `${config.API_BASE_URL}/api/files/${fileId}/download_with_token/?token=${encodeURIComponent(token)}&download=true`

    const savePath = await electronShowSaveDialog(filename)
    if (savePath) {
      // If user selected a path, download to that location
      // This would need to be implemented in the main process
      return electronDownloadFile(downloadUrl, savePath)
    }
  },

  /**
   * Check if we're running in Electron
   */
  isElectron: () => isElectron(),
}

// Type definitions for the Electron API that should be exposed from the main process
export interface ElectronMainAPI {
  downloadFile: (url: string, filename: string) => Promise<void>
  openInNewTab: (url: string) => Promise<void>
  showSaveDialog: (filename: string) => Promise<string | null>
}

// Example of how to expose these APIs from the main process:
/*
// In your main process (main.js or main.ts):
const { ipcMain, dialog } = require('electron')

// Handle download requests
ipcMain.handle('download-file', async (event, url, filename) => {
  const { download } = require('electron')
  await download(webContents, url, { filename })
})

// Handle new tab requests
ipcMain.handle('open-new-tab', async (event, url) => {
  const { shell } = require('electron')
  await shell.openExternal(url)
})

// Handle save dialog
ipcMain.handle('show-save-dialog', async (event, filename) => {
  const result = await dialog.showSaveDialog({
    defaultPath: filename,
    properties: ['createDirectory']
  })
  return result.canceled ? null : result.filePath
})

// In your preload script:
const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  downloadFile: (url, filename) => ipcRenderer.invoke('download-file', url, filename),
  openInNewTab: (url) => ipcRenderer.invoke('open-new-tab', url),
  showSaveDialog: (filename) => ipcRenderer.invoke('show-save-dialog', filename)
})
*/
