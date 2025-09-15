import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import Vue3Toastify from 'vue3-toastify'
import 'vue3-toastify/dist/index.css'

import App from './App.vue'
import router from './router'
import i18n from './i18n'
import { useThemeStore } from './stores/theme'

const app = createApp(App)

// Register Element Plus icons
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component as any)
}

const pinia = createPinia()
app.use(pinia)
app.use(router)
app.use(i18n)
app.use(ElementPlus)
app.use(Vue3Toastify, {
  autoClose: 3000,
  position: 'top-right',
  theme: 'colored',
})

// Initialize theme after pinia is set up
const themeStore = useThemeStore()
themeStore.initializeTheme()

app.mount('#app')
