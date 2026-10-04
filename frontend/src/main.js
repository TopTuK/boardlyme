import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import SvgIcon from './components/SvgIcon.vue'
import Btn from './components/ui/Btn.vue'
import { applyLocale, i18n, readStoredLocale } from './i18n'
import './style.css'

applyLocale(readStoredLocale())

const app = createApp(App)
app.use(createPinia())
app.use(i18n)
app.use(router)
app.component('SvgIcon', SvgIcon)
app.component('Btn', Btn)
app.mount('#app')
