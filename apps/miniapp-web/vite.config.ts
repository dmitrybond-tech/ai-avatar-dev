import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/',
  build: {
    target: ['es2019','chrome80','safari13'],
    cssTarget: 'chrome80',
    outDir: 'dist',
    assetsDir: 'assets',
    manifest: true,
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
