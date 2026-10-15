import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In development the React app runs on :5173 and proxies API calls to FastAPI on :8000.
// `npm run build` writes dist/, which FastAPI serves directly on :8000.
// base './' emits relative asset URLs (./assets/...) so the build does not depend on being served from the
// site root. The app still needs the FastAPI backend: opening dist/index.html from disk (file://) cannot work.
export default defineConfig({
  base: './',
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
