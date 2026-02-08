import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current working directory.
  const env = loadEnv(mode, process.cwd(), '')
  const apiUrl = env.VITE_API_URL || 'http://localhost:8081'

  return {
    plugins: [vue()],
    server: {
      host: '0.0.0.0',
      port: 5173,
      proxy: {
        '/api': {
          target: apiUrl,
          changeOrigin: true
        },
        '/version': {
          target: apiUrl,
          changeOrigin: true
        },
        '/ws': {
          target: apiUrl,
          changeOrigin: true,
          ws: true
        }
      }
    },
    build: {
      outDir: 'dist',
      assetsDir: 'assets'
    }
  }
})
