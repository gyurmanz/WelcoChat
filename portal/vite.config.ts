import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  base: '/portal/',
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000', // itt fut most a FastAPI
        changeOrigin: true,
        // ha a backend nem várja az /api prefixet, akkor:
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },  
})
