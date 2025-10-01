# Electron Setup for Download and New Tab Functionality

This document explains how to set up the Electron main process to support the download and new tab functionality.

## Main Process Setup

Add the following to your main process file (e.g., `main.js` or `main.ts`):

```javascript
const { ipcMain, dialog, shell, webContents } = require('electron')
const { download } = require('electron-dl')

// Handle download requests
ipcMain.handle('download-file', async (event, url, filename) => {
  try {
    const win = BrowserWindow.fromWebContents(event.sender)
    await download(win, url, {
      filename: filename,
      directory: require('os').homedir() + '/Downloads'
    })
    return { success: true }
  } catch (error) {
    console.error('Download failed:', error)
    throw error
  }
})

// Handle new tab requests
ipcMain.handle('open-new-tab', async (event, url) => {
  try {
    await shell.openExternal(url)
    return { success: true }
  } catch (error) {
    console.error('Failed to open URL:', error)
    throw error
  }
})

// Handle save dialog
ipcMain.handle('show-save-dialog', async (event, filename) => {
  try {
    const result = await dialog.showSaveDialog({
      defaultPath: filename,
      properties: ['createDirectory', 'showOverwriteConfirmation']
    })
    return result.canceled ? null : result.filePath
  } catch (error) {
    console.error('Save dialog failed:', error)
    throw error
  }
})
```

## Preload Script Setup

Add the following to your preload script (e.g., `preload.js`):

```javascript
const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  downloadFile: (url, filename) => ipcRenderer.invoke('download-file', url, filename),
  openInNewTab: (url) => ipcRenderer.invoke('open-new-tab', url),
  showSaveDialog: (filename) => ipcRenderer.invoke('show-save-dialog', filename)
})
```

## Dependencies

Install the required dependency:

```bash
npm install electron-dl
```

## Features

### Download Functionality
- Downloads files directly to the user's Downloads folder
- Shows native download progress
- Handles errors gracefully
- Uses the system's default download behavior

### New Tab Functionality
- Opens URLs in the system's default browser
- Works with both web URLs and file URLs
- Handles authentication tokens properly

### Save Dialog
- Shows native save dialog for choosing download location
- Supports creating new directories
- Shows overwrite confirmation

## Usage in Frontend

The frontend automatically detects if it's running in Electron and uses the appropriate methods:

```typescript
import { electronUtils } from '@/utils/electron'

// Download a file
await electronUtils.downloadFile(fileId, filename, true)

// Open in new tab
await electronUtils.openInNewTab(fileId, false)

// Show save dialog and download
await electronUtils.showSaveDialogAndDownload(fileId, filename)
```

## Environment Detection

The utility automatically detects the environment:

- **Web**: Uses standard web APIs (fetch, window.open, etc.)
- **Electron**: Uses the exposed Electron APIs from the main process

## Error Handling

All methods include proper error handling and will fall back to web implementations if Electron APIs are not available.
