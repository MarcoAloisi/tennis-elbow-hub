// One table drives three outputs of the prerender build: which pages become
// static HTML, which URLs the sitemap lists, and which routes still need an SPA
// rewrite on Cloudflare Pages.

export const SITE_URL = 'https://tenniselbowhub.live'
export const NOT_FOUND_PATH = '/404'
const GUIDE_DETAIL_ROUTE = '/guides/:slug'

interface SitemapEntry {
  path: string
  changefreq: 'always' | 'weekly' | 'monthly' | 'yearly'
  priority: number
}

export const PRERENDERED_ROUTES: SitemapEntry[] = [
  { path: '/', changefreq: 'monthly', priority: 1.0 },
  { path: '/live', changefreq: 'always', priority: 0.9 },
  { path: '/analysis', changefreq: 'weekly', priority: 0.8 },
  { path: '/online-tours/xkt', changefreq: 'weekly', priority: 0.6 },
  { path: '/online-tours/wtsl', changefreq: 'weekly', priority: 0.6 },
  { path: '/guides', changefreq: 'monthly', priority: 0.7 },
  { path: '/outfit-gallery', changefreq: 'weekly', priority: 0.6 },
  { path: '/about', changefreq: 'yearly', priority: 0.5 },
  { path: '/privacy-policy', changefreq: 'yearly', priority: 0.3 },
  { path: '/terms-of-service', changefreq: 'yearly', priority: 0.3 },
  { path: '/contact', changefreq: 'yearly', priority: 0.4 },
]

export const GUIDE_ENTRY = { changefreq: 'monthly', priority: 0.6 } as const

// The public API caps page_size at 50 and rate limits at 60 requests/minute per
// IP. A build makes one request per guide plus a few, so past ~55 guides the
// build needs a bulk endpoint.
export async function fetchGuideSlugs(apiBase: string): Promise<string[]> {
  if (!apiBase) throw new Error('VITE_API_URL must be set to prerender guide pages')
  const slugs: string[] = []
  let totalPages = 1
  for (let page = 1; page <= totalPages; page++) {
    const res = await fetch(`${apiBase}/api/guides?page=${page}&page_size=50`)
    if (!res.ok) throw new Error(`Guide list request failed with HTTP ${res.status}`)
    const data = await res.json()
    slugs.push(...data.items.map((g: { slug: string }) => g.slug))
    totalPages = data.total_pages
  }
  return slugs
}

export function renderSitemap(entries: SitemapEntry[]): string {
  const urls = entries
    .map(
      (e) =>
        `  <url>\n    <loc>${SITE_URL}${e.path}</loc>\n    <changefreq>${e.changefreq}</changefreq>\n    <priority>${e.priority.toFixed(1)}</priority>\n  </url>`,
    )
    .join('\n')
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`
}

// A top-level 404.html switches off the SPA fallback on Cloudflare Pages, so any
// route the browser renders itself (login, profile, admin, ...) needs an explicit
// rewrite to the app shell. Derived from the router so a new route cannot be
// left out and silently 404 on a direct load.
export function spaRewrites(
  paths: string[],
  routes: readonly { path: string; redirect?: unknown }[],
): string[] {
  const prerendered = new Set(PRERENDERED_ROUTES.map((r) => r.path))
  const redirected = new Set(routes.filter((r) => r.redirect).map((r) => r.path))
  // `paths` also lists dynamic routes (/guides/:slug, the catch-all). Those are
  // handled below, or deliberately left to 404.
  const staticPaths = paths.filter((p) => !p.includes(':') && !prerendered.has(p) && !redirected.has(p))
  const dynamicPaths = routes
    .filter((r) => r.path.includes('/:') && r.path !== GUIDE_DETAIL_ROUTE && !r.path.includes('(.*)'))
    .map((r) => r.path.replace(/\/:.*$/, '/*'))
  // The target is `/`, not `/index.html`: Pages rejects the latter as a redirect loop.
  return [...staticPaths, ...dynamicPaths].map((p) => `${p} / 200`)
}
