import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/research': 'http://localhost:8000',
      '/status':   'http://localhost:8000',
      '/steps':    'http://localhost:8000',
      '/report':   'http://localhost:8000',
      '/reports':  'http://localhost:8000',
    },
  },
})
