import { defineConfig } from 'astro/config';

export default defineConfig({
  output: 'static',
  server: {
    port: 3000,
    host: true,
  },
  vite: {
    resolve: {
      alias: {
        '@': '/src',
      },
    },
  },
});

