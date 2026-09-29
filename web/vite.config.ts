import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// API_URL troca o alvo do proxy (teste da Ligação contra o servidor falso). O preview herda o proxy.
const API = process.env.API_URL ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  // Auth fica fora de /api (FastAPI-Users em /auth e /users). ws: o WebSocket da Ligação passa pelo /api.
  server: { proxy: { '/api': { target: API, ws: true }, '/auth': API, '/users': API } },
})
