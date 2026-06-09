import { defineStore } from 'pinia'
import { api } from '../utils/api'
export const useEventosStore = defineStore('eventos', {
  state: () => ({ items: [], loading: false, page: 1, hasNext: false }),
  actions: {
    async fetchEventos(filters = {}) {
      this.loading = true
      try {
        const qs = new URLSearchParams({ page: this.page, ...filters }).toString()
        const data = await api.get(`/eventos?${qs}`)
        this.items = Array.isArray(data) ? data : (data.items || [])
        this.hasNext = !!(data.has_next ?? (this.items.length >= 20))
      } finally { this.loading = false }
    },
  },
})
