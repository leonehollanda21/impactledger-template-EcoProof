import { defineStore } from 'pinia'
import { api } from '../utils/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('ecoproof_token') || null,
    role: localStorage.getItem('ecoproof_role') || null,
    user: null,
  }),

  getters: {
    isAuthenticated: (s) => !!s.token,
    isCidadao: (s) => s.role === 'cidadao',
    isInstituto: (s) => s.role === 'instituto',
    isAdmin: (s) => s.role === 'admin',
  },

  actions: {
    _persist() {
      if (this.token) localStorage.setItem('ecoproof_token', this.token)
      else localStorage.removeItem('ecoproof_token')

      if (this.role) localStorage.setItem('ecoproof_role', this.role)
      else localStorage.removeItem('ecoproof_role')
    },

    /** Faz login e armazena token + role */
    async login(email, password) {
      const data = await api.post('/auth/login', { email, password })
      this.token = data.access_token
      this.role = data.role
      this._persist()
      await this.fetchMe()
    },

    /** Registra cidadão — retorna token diretamente e loga automaticamente */
    async registerCidadao(payload) {
      const data = await api.post('/auth/register/cidadao', payload)
      this.token = data.access_token
      this.role = data.role
      this._persist()
      await this.fetchMe()
    },

    /**
     * Registra instituto — NÃO retorna token (conta fica pendente).
     * Retorna { message, detail } do backend.
     */
    async registerInstituto(payload) {
      return api.post('/auth/register/instituto', payload)
    },

    /** Busca o perfil do usuário autenticado */
    async fetchMe() {
      try {
        this.user = await api.get('/users/me')
      } catch (e) {
        this.user = null
        throw e
      }
    },

    /**
     * Atualiza wallet e/ou nome via query params (conforme spec da API: PATCH /users/me?wallet_address=...)
     * @param {Object} params - { name?, wallet_address? }
     */
    async updateProfile(params = {}) {
      const qs = new URLSearchParams(
        Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ''))
      ).toString()
      this.user = await api.patch(`/users/me${qs ? `?${qs}` : ''}`)
    },

    /** Atalho para atualizar somente a wallet */
    async updateWallet(wallet_address) {
      return this.updateProfile({ wallet_address })
    },

    /** Renova o token sem precisar reautenticar */
    async refresh() {
      const data = await api.post('/auth/refresh')
      this.token = data.access_token
      this.role = data.role
      this._persist()
    },

    /** Desloga e limpa estado local */
    logout() {
      this.token = null
      this.role = null
      this.user = null
      this._persist()
    },
  },
})
