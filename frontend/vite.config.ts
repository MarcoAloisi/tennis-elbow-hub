import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src'),
      },
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: env.VITE_API_URL || 'http://localhost:8000',
          changeOrigin: true,
          ws: true,
        },
        '/ws': {
          target: env.VITE_API_URL?.replace('https', 'wss').replace('http', 'ws') || 'ws://localhost:8000',
          ws: true,
        },
      },
    },
    define: {
      __API_URL__: JSON.stringify(env.VITE_API_URL || ''),
    },
    ssgOptions: {
      // Only prerender the public, indexable content routes — the ones in
      // the live sitemap that AdSense/search crawlers actually evaluate.
      // Everything else (auth, admin, profile, predictions) stays pure SPA,
      // rendered client-side exactly as before.
      includedRoutes(paths) {
        const prerendered = new Set([
          '/',
          '/live',
          '/analysis',
          '/guides',
          '/online-tours/xkt',
          '/online-tours/wtsl',
          '/outfit-gallery',
          '/privacy-policy',
          '/terms-of-service',
          '/contact',
        ])
        return paths.filter((p) => prerendered.has(p))
      },
    },
  }
})
