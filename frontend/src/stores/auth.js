import { defineStore } from 'pinia'
import api from '../api/client'
import { applyLocale } from '../i18n'
import { initTelegram, isTelegram, tg } from '../lib/telegram'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: JSON.parse(localStorage.getItem('bm_user') || 'null'),
    token: localStorage.getItem('bm_token'),
    refreshToken: localStorage.getItem('bm_refresh'),
    meta: null,
    initialized: false,
    loading: false,
  }),

  getters: {
    isAuthenticated: (s) => !!s.token,
    isTelegram: () => isTelegram(),
  },

  actions: {
    _persist() {
      const keys = { bm_token: this.token, bm_refresh: this.refreshToken, bm_user: JSON.stringify(this.user) }
      for (const [key, value] of Object.entries(keys)) {
        if (value) localStorage.setItem(key, value)
        else localStorage.removeItem(key)
      }
    },

    async fetchMeta() {
      if (!this.meta) {
        try {
          const { data } = await api.get('/meta')
          this.meta = data
        } catch {
          /* backend unreachable — views will show their own errors */
        }
      }
    },

    async ensureInit() {
      if (this.initialized) return
      this.loading = true
      try {
        initTelegram()
        await this.fetchMeta()
        if (isTelegram()) {
          try {
            await this.loginMiniApp()
          } catch (e) {
            console.warn('[auth] Telegram auto-login failed:', e?.response?.data?.detail || e?.message)
          }
        } else if (this.token) {
          try {
            const { data } = await api.get('/auth/me')
            this.user = data
            if (data.locale) applyLocale(data.locale)
            this._persist()
          } catch {
            this._clear()
          }
        }
      } finally {
        this.initialized = true
        this.loading = false
      }
    },

    _setSession(data) {
      this.token = data.access_token
      this.refreshToken = data.refresh_token
      this.user = data.user
      if (data.user?.locale) applyLocale(data.user.locale)
      this._persist()
    },

    async updateLocale(code) {
      const { data } = await api.patch('/auth/me', { locale: code })
      this.user = data
      applyLocale(data.locale)
      this._persist()
      return data
    },

    _clear() {
      this.token = null
      this.refreshToken = null
      this.user = null
      this._persist()
    },

    async loginMiniApp() {
      const t = tg()
      if (!t || !t.initData) throw new Error('errors.notTelegram')
      const { data } = await api.post('/auth/telegram/miniapp', { init_data: t.initData })
      this._setSession(data)
    },

    async loginWidget(dataStr) {
      const { data } = await api.post('/auth/telegram/widget', { data: dataStr })
      this._setSession(data)
    },

    async devLogin(username) {
      const { data } = await api.post('/auth/dev-login', { username })
      this._setSession(data)
    },

    logout() {
      this._clear()
      if (isTelegram()) {
        try {
          tg().close()
        } catch {
          /* ignore */
        }
      }
    },
  },
})
