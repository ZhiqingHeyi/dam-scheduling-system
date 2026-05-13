import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export default {
  database: {
    testConnection: (config: any) => 
      api.post('/database/test-connection', config),
    
    getConfig: () => 
      api.get('/database/config'),
    
    saveConfig: (config: any) => 
      api.post('/database/save-config', config),
    
    getTables: () => 
      api.get('/database/tables'),
    
    queryTable: (tableName: string, limit?: number) => 
      api.get(`/database/query/${tableName}`, { params: { limit } }),
    
    syncData: () => 
      api.post('/database/sync-data', {}, { timeout: 60000 })
  },
  
  scheduling: {
    run: (params: any) => 
      api.post('/scheduling/run', params, { timeout: 120000 }),
    
    getStatus: () => 
      api.get('/scheduling/status')
  },
  
  files: {
    upload: (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      return api.post('/files/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    },
    
    uploadMultiple: (files: File[]) => {
      const formData = new FormData()
      files.forEach(file => formData.append('files', file))
      return api.post('/files/upload-multiple', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    },
    
    listUploaded: () => 
      api.get('/files/list-uploaded'),
    
    download: (filename: string) =>
      api.get(`/files/download/${filename}`, { responseType: 'blob' }),

    downloadRunFile: (runFolder: string, filename: string) =>
      api.get(`/files/download/${runFolder}/${filename}`, { responseType: 'blob' }),

    deleteFile: (filename: string) =>
      api.delete(`/files/delete/${filename}`),

    getOutputFiles: () =>
      api.get('/files/output-files'),

    previewFile: (filename: string) =>
      api.get(`/files/preview/${filename}`),

    previewRunFile: (runFolder: string, filename: string) =>
      api.get(`/files/preview/${runFolder}/${filename}`),

    downloadRunFolder: (runFolder: string) =>
      api.get(`/files/download-run/${runFolder}`, { responseType: 'blob' }),

    openOutputDir: () =>
      api.post('/files/open-output-dir')
  },

  getDatabaseConfig: () => api.get('/database/config'),
  saveDatabaseConfig: (config: any) => api.post('/database/save-config', config),
  testDatabaseConnection: (config: any) => api.post('/database/test-connection', config),
  runScheduling: (params: any) => api.post('/scheduling/run', params, { timeout: 120000 }),
  getOutputFiles: () => api.get('/files/output-files'),
  previewFile: (filename: string) => api.get(`/files/preview/${filename}`)
}
