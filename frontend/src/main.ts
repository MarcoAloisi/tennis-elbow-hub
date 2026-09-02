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
  ({ app, router }) => {
    app.use(createPinia())
    setupGuards(router)
  },
)
