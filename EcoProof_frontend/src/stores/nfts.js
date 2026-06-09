import { defineStore } from 'pinia'
import { api } from '../utils/api'
export const useNFTStore = defineStore('nfts', {
  state: () => ({ items: [], loading: false }),
  actions: {
    async fetchMeusNFTs() {
      this.loading = true
      try { this.items = await api.get('/users/me/nfts') }
      finally { this.loading = false }
    },
  },
})
