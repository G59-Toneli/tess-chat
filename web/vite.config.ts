import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  // Auth fica fora de /api (FastAPI-Users em /auth e /users).
  server: { proxy: { '/api': 'http://localhost:8000', '/auth': 'http://localhost:8000', '/users': 'http://localhost:8000' } },
})
