import { defineConfig } from 'astro/config';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  base: '/miniapp/',
  output: 'static',
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
  },
  vite: {
    server: {
      allowedHosts: ['miniapp.dmitrybond.tech'],
      origin: 'https://miniapp.dmitrybond.tech',
      hmr: {
        host: 'miniapp.dmitrybond.tech',
        protocol: 'wss',
        clientPort: 443,
      },
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
      extensions: ['.mjs', '.js', '.ts', '.jsx', '.tsx', '.json'],
    },
  },
});

