const { contextBridge, ipcRenderer } = require('electron')

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // App information
  getAppVersion: () => ipcRenderer.invoke('app-version'),
  getPlatform: () => ipcRenderer.invoke('platform'),
  
  // Window controls
  minimizeWindow: () => ipcRenderer.send('window-minimize'),
  maximizeWindow: () => ipcRenderer.send('window-maximize'),
  closeWindow: () => ipcRenderer.send('window-close'),
  
  // File operations (if needed)
  selectFile: (options) => ipcRenderer.invoke('dialog-open-file', options),
  selectDirectory: (options) => ipcRenderer.invoke('dialog-open-directory', options),
  saveFile: (options) => ipcRenderer.invoke('dialog-save-file', options),
  
  // App events
  onAppReady: (callback) => ipcRenderer.on('app-ready', callback),
  onAppUpdate: (callback) => ipcRenderer.on('app-update', callback),
  
  // Remove listeners
  removeAllListeners: (channel) => ipcRenderer.removeAllListeners(channel)
})

// Expose environment variables
contextBridge.exposeInMainWorld('env', {
  NODE_ENV: process.env.NODE_ENV,
  IS_ELECTRON: true
})
