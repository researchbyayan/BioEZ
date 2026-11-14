const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('bioez', {
  platform: process.platform,
  appInfo: () => ipcRenderer.invoke('bioez:app-info'),
  credits: () => ipcRenderer.invoke('bioez:credits'),
  license: id => ipcRenderer.invoke('bioez:license',id),
  openCreditSource: id => ipcRenderer.invoke('bioez:credit-source',id),
  checkUpdates: () => ipcRenderer.invoke('bioez:updates'),
  downloadUpdate: () => ipcRenderer.invoke('bioez:update-download'),
  installUpdate: () => ipcRenderer.invoke('bioez:update-install'),
  onUpdate: (callback) => {
    const listener = (_event, value) => callback(value);
    ipcRenderer.on('bioez:update', listener);
    return () => ipcRenderer.removeListener('bioez:update', listener);
  },
  request: (command, payload) => ipcRenderer.invoke('bioez:request', command, payload),
  chat: (payload) => ipcRenderer.invoke('bioez:chat', payload),
  cancel: () => ipcRenderer.invoke('bioez:cancel'),
  appearance: () => ipcRenderer.invoke('bioez:appearance'),
  windowAction: action => ipcRenderer.invoke('bioez:window', action),
  pickImage: () => ipcRenderer.invoke('bioez:pick-image'),
  saveImage: (payload) => ipcRenderer.invoke('bioez:save-image', payload),
  saveText: text => ipcRenderer.invoke('bioez:save-text', text),
  openReference: url => ipcRenderer.invoke('bioez:open-reference', url),
  openLink: url => ipcRenderer.invoke('bioez:open-link', url),
  signInOpenRouter: () => ipcRenderer.invoke('bioez:openrouter-signin'),
  onBackdrop: (callback) => {
    const listener = (_event, value) => callback(value);
    ipcRenderer.on('bioez:backdrop', listener);
    return () => ipcRenderer.removeListener('bioez:backdrop', listener);
  },
  onEvent: (callback) => {
    const listener = (_event, value) => callback(value);
    ipcRenderer.on('bioez:event', listener);
    return () => ipcRenderer.removeListener('bioez:event', listener);
  }
});
