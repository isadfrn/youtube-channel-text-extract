import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('ytapi', {
  // ── One-shot queries ─────────────────────────────────────────────────────────
  checkSetup: () => ipcRenderer.invoke('check-setup'),
  getDesktopPath: () => ipcRenderer.invoke('get-desktop-path'),
  selectDirectory: (defaultPath) => ipcRenderer.invoke('select-directory', defaultPath),
  openFolder: (path) => ipcRenderer.invoke('open-folder', path),

  // ── Extraction control ───────────────────────────────────────────────────────
  startExtraction: (options) => ipcRenderer.send('start-extraction', options),
  stopExtraction: () => ipcRenderer.send('stop-extraction'),

  // ── Event subscriptions (return cleanup function) ────────────────────────────
  onLog: (callback) => {
    const handler = (_, line) => callback(line)
    ipcRenderer.on('extract:log', handler)
    return () => ipcRenderer.off('extract:log', handler)
  },

  onDone: (callback) => {
    const handler = (_, code) => callback(code)
    ipcRenderer.on('extract:done', handler)
    return () => ipcRenderer.off('extract:done', handler)
  },
})
