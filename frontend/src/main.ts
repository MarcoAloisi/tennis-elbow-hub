import { ViteSSG } from 'vite-ssg'
import { createPinia } from 'pinia'
import App from './App.vue'
import { routes, setupGuards } from './router'

// Import styles
import './assets/styles/variables.css'
import './assets/styles/base.css'
import './assets/styles/components.css'

export const createApp = ViteSSG(
  App,
  {
    routes,
    scrollBehavior() {
      return { top: 0 }
    },
  },
  ({ app, router, initialState }) => {
    const pinia = createPinia()
    app.use(pinia)
    // Ship the store state fetched during prerender to the browser, so
    // hydration starts from the same data the static HTML was rendered with.
    if (import.meta.env.SSR) initialState.pinia = pinia.state.value
    else pinia.state.value = initialState.pinia || {}
    setupGuards(router)
  },
)
