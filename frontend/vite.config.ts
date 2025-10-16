import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 3000,
    host: '0.0.0.0',  // Listen on all network interfaces for Docker
    strictPort: true,
    watch: {
      usePolling: true,  // Enable polling for file changes in Docker
      interval: 1000,    // Poll every 1000ms
    },
    hmr: {
      port: 3000,        // Use the same port for HMR
    },
    proxy: {
      '/api': {
        target: 'http://backend:8000',  // Use Docker service name
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
})