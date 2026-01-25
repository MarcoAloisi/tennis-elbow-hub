import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

// Import styles
import './assets/styles/variables.css'
import './assets/styles/base.css'
import './assets/styles/components.css'

// Create and mount app
const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
