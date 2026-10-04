import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import LandingView from '../views/LandingView.vue'
import LoginView from '../views/LoginView.vue'
import BoardsView from '../views/BoardsView.vue'
import BoardView from '../views/BoardView.vue'
import SettingsView from '../views/SettingsView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'landing', component: LandingView },
    { path: '/login', name: 'login', component: LoginView },
    { path: '/boards', name: 'boards', component: BoardsView, meta: { app: true, auth: true } },
    { path: '/board/:id', name: 'board', component: BoardView, meta: { app: true, auth: true } },
    { path: '/settings', name: 'settings', component: SettingsView, meta: { app: true, auth: true } },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.ensureInit()
  if (to.meta.auth && !auth.isAuthenticated) {
    return { name: 'login', query: to.fullPath !== '/' ? { redirect: to.fullPath } : {} }
  }
})

export default router
