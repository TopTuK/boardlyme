import { defineStore } from 'pinia'
import api from '../api/client'

export const useProjectsStore = defineStore('projects', {
  state: () => ({
    list: [],
    loading: false,
    error: '',
  }),

  actions: {
    async fetch() {
      this.loading = true
      try {
        const { data } = await api.get('/projects')
        this.list = data
      } catch (e) {
        this.error = e.response?.data?.detail || 'errors.loadProjects'
      } finally {
        this.loading = false
      }
    },

    async create(name) {
      const { data } = await api.post('/projects', { name })
      this.list.unshift(data)
      return data
    },
  },
})
