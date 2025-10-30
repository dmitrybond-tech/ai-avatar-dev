import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/miniapp/',
  build: {
    target: ['es2019','chrome80','safari13'],
    cssTarget: 'chrome80',
  },
  server: {
    host: true,
    port: 5173,
  },
  preview: {
    host: true,
    port: 5173,
  },
})
