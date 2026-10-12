import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import { appendFileSync, writeFileSync } from 'node:fs'
import {
  GUIDE_ENTRY,
  NOT_FOUND_PATH,
  PRERENDERED_ROUTES,
  fetchGuideSlugs,
  renderSitemap,
  spaRewrites,
} from './ssg/routes'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  // Filled by includedRoutes, written out by onFinished.
  let sitemap: Parameters<typeof renderSitemap>[0] = []
  let rewrites: string[] = []

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
      // Prerender the public, indexable routes, one page per guide fetched from
      // the API, and the 404 page. Everything else (auth, admin, profile,
      // predictions) stays pure SPA, rendered client-side.
      async includedRoutes(paths, routes) {
        const guidePaths = (await fetchGuideSlugs(env.VITE_API_URL)).map((slug) => `/guides/${slug}`)
        sitemap = [...PRERENDERED_ROUTES, ...guidePaths.map((path) => ({ path, ...GUIDE_ENTRY }))]
        rewrites = spaRewrites(paths, routes)
        return [...PRERENDERED_ROUTES.map((r) => r.path), ...guidePaths, NOT_FOUND_PATH]
      },
      onFinished() {
        const dist = resolve(__dirname, 'dist')
        writeFileSync(resolve(dist, 'sitemap.xml'), renderSitemap(sitemap))
        appendFileSync(resolve(dist, '_redirects'), ['', ...rewrites, ''].join('\n'))
      },
    },
  }
})
