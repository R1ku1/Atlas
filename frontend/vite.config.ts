import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Proxies /api/* to the FastAPI backend during dev so the browser never
// needs CORS headers from the backend — requests to /api/v1/... on the
// Vite dev server (5173) are forwarded to uvicorn (8000).
// Adjust the target if your backend runs on a different port.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
