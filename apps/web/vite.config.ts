import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const nodeEnv = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process
  ?.env;
const API_TARGET = nodeEnv?.VITE_API_PROXY_TARGET ?? 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined;
          if (id.includes('recharts') || id.includes('d3-') || id.includes('victory')) {
            return 'charts';
          }
          return 'vendor';
        },
      },
    },
  },
});
