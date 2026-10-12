import DOMPurify from 'dompurify'

// DOMPurify needs a DOM. Browsers have one. Node does not, so prerendering
// builds one from jsdom. The SSR guard lets the client bundle drop jsdom.
let purify: typeof DOMPurify | null = typeof window === 'undefined' ? null : DOMPurify

export async function ensureSanitizer(): Promise<void> {
  if (import.meta.env.SSR && !purify) {
    const { JSDOM } = await import('jsdom')
    purify = DOMPurify(new JSDOM('').window as unknown as Parameters<typeof DOMPurify>[0])
  }
}

export function sanitizeHtml(html: string): string {
  if (!purify) throw new Error('ensureSanitizer() must finish before sanitizeHtml() runs while prerendering')
  return purify.sanitize(html)
}
