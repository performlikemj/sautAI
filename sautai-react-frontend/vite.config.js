import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // Use the monorepo root for .env files, e.g., /sautAI/.env
  envDir: '..',
  server: {
    // Align with user's running port (e.g., 5174) to keep origin consistent
    port: 5174,
    host: true,
    proxy: {
      // Dev-time proxy to avoid CORS. Frontend can call relative paths like /auth/... /meals/... etc.
      '/auth': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/customer_dashboard': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/meals': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/chefs': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/reviews': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  },
  preview: {
    port: 5174
  }
})
