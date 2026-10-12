import { describe, expect, it } from 'vitest'
import { renderSitemap, spaRewrites } from './routes'

describe('spaRewrites', () => {
  it('rewrites only routes the browser renders itself', () => {
    const paths = ['/', '/login', '/live', '/online-tours', '/profile/:userId', '/guides/:slug', '/:pathMatch(.*)*']
    const routes = [
      { path: '/' },
      { path: '/login' },
      { path: '/live' },
      { path: '/online-tours', redirect: '/online-tours/xkt' },
      { path: '/profile/:userId' },
      { path: '/guides/:slug' },
      { path: '/:pathMatch(.*)*' },
    ]
    expect(spaRewrites(paths, routes)).toEqual(['/login / 200', '/profile/* / 200'])
  })
})

describe('renderSitemap', () => {
  it('lists each entry with its absolute URL', () => {
    expect(renderSitemap([{ path: '/guides', changefreq: 'monthly', priority: 0.7 }])).toBe(
      '<?xml version="1.0" encoding="UTF-8"?>\n' +
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        '  <url>\n' +
        '    <loc>https://tenniselbowhub.live/guides</loc>\n' +
        '    <changefreq>monthly</changefreq>\n' +
        '    <priority>0.7</priority>\n' +
        '  </url>\n' +
        '</urlset>\n',
    )
  })
})
