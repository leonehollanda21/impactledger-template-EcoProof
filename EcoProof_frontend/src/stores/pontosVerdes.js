import { defineStore } from 'pinia'
import { api, apiFormData } from '../utils/api'

// Pontos de partida sugeridos (mock padrão) se não houver dados salvos
const DEFAULT_MOCKS = [
  {
    id: 'mock-ponto-1',
    nome: 'Praça da Paz',
    categoria: 'praca',
    latitude: -23.55052,
    longitude: -46.633308,
    guardiao_id: 'mock-user-1',
    guardiao_name: 'Mariana Costa',
    data_inicio: '2026-05-01T10:00:00Z',
    status: 'ativo',
    meses_concluidos: 1,
    proximo_checkin_limite: new Date(Date.now() + 15 * 24 * 60 * 60 * 1000).toISOString(), // +15 dias
    foto_inicial_url: 'https://images.unsplash.com/photo-1597430342284-60139d480c05?auto=format&fit=crop&w=600&q=80',
    checkins: [
      { id: 'ck-1', mes_referencia: 1, data_envio: '2026-05-30T14:00:00Z', foto_url: 'https://images.unsplash.com/photo-1597430342284-60139d480c05?auto=format&fit=crop&w=600&q=80', status: 'aprovado' }
    ],
    nft_token_id: null
  },
  {
    id: 'mock-ponto-2',
    nome: 'Canteiro da Av. Paulista',
    categoria: 'canteiro',
    latitude: -23.5615,
    longitude: -46.656,
    guardiao_id: 'mock-user-2',
    guardiao_name: 'Carlos Ramos',
    data_inicio: '2026-04-10T12:00:00Z',
    status: 'alerta',
    meses_concluidos: 1,
    proximo_checkin_limite: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(), // -2 dias (Atrasado!)
    foto_inicial_url: 'https://images.unsplash.com/photo-1582407947304-fd86f028f716?auto=format&fit=crop&w=600&q=80',
    checkins: [
      { id: 'ck-2', mes_referencia: 1, data_envio: '2026-05-10T09:00:00Z', foto_url: 'https://images.unsplash.com/photo-1582407947304-fd86f028f716?auto=format&fit=crop&w=600&q=80', status: 'aprovado' }
    ],
    nft_token_id: null
  },
  {
    id: 'mock-ponto-3',
    nome: 'Margem do Rio Pinheiros',
    categoria: 'rio',
    latitude: -23.5709,
    longitude: -46.7025,
    guardiao_id: 'mock-user-3',
    guardiao_name: 'Beatriz Lima',
    data_inicio: '2026-03-01T08:00:00Z',
    status: 'concluido',
    meses_concluidos: 3,
    proximo_checkin_limite: null,
    foto_inicial_url: 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=600&q=80',
    checkins: [
      { id: 'ck-3', mes_referencia: 1, data_envio: '2026-04-01T10:00:00Z', foto_url: 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=600&q=80', status: 'aprovado' },
      { id: 'ck-4', mes_referencia: 2, data_envio: '2026-05-01T11:00:00Z', foto_url: 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=600&q=80', status: 'aprovado' },
      { id: 'ck-5', mes_referencia: 3, data_envio: '2026-06-01T12:00:00Z', foto_url: 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=600&q=80', status: 'aprovado' }
    ],
    nft_token_id: 1205
  },
  {
    id: 'mock-ponto-4',
    nome: 'Canteiro Central Rebouças',
    categoria: 'canteiro',
    latitude: -23.565,
    longitude: -46.680,
    guardiao_id: null,
    guardiao_name: null,
    status: 'disponivel',
    meses_concluidos: 0,
    proximo_checkin_limite: null,
    foto_inicial_url: null,
    checkins: [],
    nft_token_id: null
  }
]

function getLocalData() {
  const data = localStorage.getItem('ecoproof_pontos_verdes')
  if (!data) {
    localStorage.setItem('ecoproof_pontos_verdes', JSON.stringify(DEFAULT_MOCKS))
    return DEFAULT_MOCKS
  }
  return JSON.parse(data)
}

function saveLocalData(data) {
  localStorage.setItem('ecoproof_pontos_verdes', JSON.stringify(data))
}

export const usePontosVerdesStore = defineStore('pontosVerdes', {
  state: () => ({
    items: [],
    loading: false,
    meusItems: []
  }),

  actions: {
    // Carrega todos os pontos verdes cadastrados
    async fetchPontos() {
      this.loading = true
      try {
        const data = await api.get('/pontos-verdes')
        this.items = Array.isArray(data) ? data : (data.items || [])
      } catch (err) {
        console.warn('Backend API `/pontos-verdes` não disponível. Usando fallback de simulação local.', err.message)
        this.items = getLocalData()
      } finally {
        this.loading = false
      }
    },

    // Carrega pontos adotados pelo usuário autenticado
    async fetchMeusPontos(userId) {
      this.loading = true
      try {
        const data = await api.get('/pontos-verdes/me')
        this.meusItems = Array.isArray(data) ? data : (data.items || [])
      } catch (err) {
        console.warn('Backend API `/pontos-verdes/me` não disponível. Usando fallback de simulação local.', err.message)
        const local = getLocalData()
        // Filtra por guardiao_id do usuário atual
        // Para mock, assumiremos o id passado ou um padrão
        const uid = userId || 'mock-user-atual'
        this.meusItems = local.filter(p => p.guardiao_id === uid)
      } finally {
        this.loading = false
      }
    },

    // Cadastra uma nova adoção
    async adotarPonto(payload, user) {
      this.loading = true
      try {
        const fd = new FormData()
        fd.append('nome', payload.nome)
        fd.append('categoria', payload.categoria)
        fd.append('latitude', payload.latitude)
        fd.append('longitude', payload.longitude)
        fd.append('foto_inicial', payload.foto_inicial)

        const res = await apiFormData('/pontos-verdes', fd)
        await this.fetchPontos()
        return res
      } catch (err) {
        console.warn('Falha ao salvar no backend. Salvando localmente para simulação.', err.message)
        
        // Simulação de salvamento local
        const local = getLocalData()
        const uid = user?.id || 'mock-user-atual'
        const uname = user?.name || 'Cidadão EcoProof'
        
        // Gera URL local fictícia para a imagem
        const fotoUrl = payload.foto_inicial ? URL.createObjectURL(payload.foto_inicial) : 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?auto=format&fit=crop&w=600&q=80'

        // Se o ponto já existia como disponível, atualiza. Senão, cria novo.
        const index = local.findIndex(p => 
          Math.abs(p.latitude - payload.latitude) < 0.0001 && 
          Math.abs(p.longitude - payload.longitude) < 0.0001
        )

        const novoPonto = {
          id: index !== -1 ? local[index].id : `ponto-${Date.now()}`,
          nome: payload.nome,
          categoria: payload.categoria,
          latitude: payload.latitude,
          longitude: payload.longitude,
          guardiao_id: uid,
          guardiao_name: uname,
          data_inicio: new Date().toISOString(),
          status: 'ativo',
          meses_concluidos: 0,
          proximo_checkin_limite: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
          foto_inicial_url: fotoUrl,
          checkins: [],
          nft_token_id: null
        }

        if (index !== -1) {
          local[index] = novoPonto
        } else {
          local.push(novoPonto)
        }

        saveLocalData(local)
        this.items = local
        return novoPonto
      } finally {
        this.loading = false
      }
    },

    // Envia um check-in de foto mensal
    async enviarCheckin(pontoId, fotoFile, user) {
      this.loading = true
      try {
        const fd = new FormData()
        fd.append('foto', fotoFile)
        const res = await apiFormData(`/pontos-verdes/${pontoId}/checkin`, fd)
        await this.fetchPontos()
        return res
      } catch (err) {
        console.warn('Falha no check-in no backend. Atualizando localmente para simulação.', err.message)

        const local = getLocalData()
        const ponto = local.find(p => p.id === pontoId)
        if (!ponto) throw new Error('Ponto verde não encontrado.')

        const fotoUrl = URL.createObjectURL(fotoFile)
        const proxMes = ponto.meses_concluidos + 1

        const novoCheckin = {
          id: `ck-${Date.now()}`,
          mes_referencia: proxMes,
          data_envio: new Date().toISOString(),
          foto_url: fotoUrl,
          status: 'aprovado' // auto-aprovação na simulação de frontend
        }

        ponto.checkins.push(novoCheckin)
        ponto.meses_concluidos = proxMes

        if (proxMes >= 3) {
          ponto.status = 'concluido'
          ponto.proximo_checkin_limite = null
          ponto.nft_token_id = Math.floor(Math.random() * 8000) + 1000 // gera ID token on-chain simulado
        } else {
          ponto.status = 'ativo'
          ponto.proximo_checkin_limite = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString()
        }

        saveLocalData(local)
        this.items = local
        return { message: 'Check-in simulado com sucesso!', ponto }
      } finally {
        this.loading = false
      }
    }
  }
})
