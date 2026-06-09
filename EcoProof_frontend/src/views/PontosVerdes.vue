<script setup>
import { onMounted, ref, watch, nextTick, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { usePontosVerdesStore } from '../stores/pontosVerdes'
import { useAuthStore } from '../stores/auth'
import { formatDate } from '../utils/format'
import { useToast } from '../composables/useToast'
import StatusBadge from '../components/StatusBadge.vue'

const store = usePontosVerdesStore()
const auth = useAuthStore()
const toast = useToast()
const router = useRouter()

const viewMode = ref('mapa') // 'mapa' ou 'lista'
const filtroCategoria = ref('')
const filtroStatus = ref('')
const buscaQuery = ref('')

const mapRef = ref(null)
let map = null
let markers = []
let tempMarker = null

onMounted(async () => {
  await store.fetchPontos()
  if (viewMode.value === 'mapa') {
    await nextTick()
    renderMap()
  }
})

watch(viewMode, async (newVal) => {
  if (newVal === 'mapa') {
    await nextTick()
    renderMap()
  } else {
    destroyMap()
  }
})

// Recria os marcadores caso a lista de itens ou filtros mude
const filteredPoints = ref([])

function updateFilters() {
  let list = store.items || []
  if (filtroCategoria.value) {
    list = list.filter(p => p.categoria === filtroCategoria.value)
  }
  if (filtroStatus.value) {
    list = list.filter(p => p.status === filtroStatus.value)
  }
  if (buscaQuery.value.trim()) {
    const q = buscaQuery.value.toLowerCase()
    list = list.filter(p => p.nome.toLowerCase().includes(q) || (p.guardiao_name && p.guardiao_name.toLowerCase().includes(q)))
  }
  filteredPoints.value = list
}

watch([() => store.items, filtroCategoria, filtroStatus, buscaQuery], () => {
  updateFilters()
  if (map) {
    renderMarkers()
  }
}, { deep: true, immediate: true })

onBeforeUnmount(() => {
  destroyMap()
})

function destroyMap() {
  if (map) {
    map.remove()
    map = null
  }
  markers = []
  tempMarker = null
  window.iniciarAdocao = null
}

function renderMap() {
  if (!window.L || !mapRef.value) return
  if (map) return

  // Centraliza em São Paulo por padrão
  map = window.L.map(mapRef.value).setView([-23.55, -46.63], 12)
  window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
  }).addTo(map)

  renderMarkers()

  // Escuta cliques no mapa para propor adoções
  map.on('click', (e) => {
    if (!auth.isAuthenticated) {
      toast.warn('Faça login para adotar uma área!')
      return
    }
    if (!auth.isCidadao) {
      toast.warn('Apenas contas de Cidadão podem adotar áreas.')
      return
    }

    const { lat, lng } = e.latlng

    if (tempMarker) map.removeLayer(tempMarker)

    const tempIcon = window.L.divIcon({
      className: 'eco-marker marker-new-draft',
      html: '📍',
      iconSize: [32, 32]
    })

    tempMarker = window.L.marker([lat, lng], { icon: tempIcon }).addTo(map)
    
    // Configura função global temporária para ser chamada pelo HTML do popup
    window.iniciarAdocao = (latitude, longitude) => {
      router.push({
        path: '/app/adotar-area',
        query: { lat: latitude, lng: longitude }
      })
    }

    tempMarker.bindPopup(`
      <div class="popup-adocao">
        <h3>🌱 Adotar este Ponto?</h3>
        <p class="muted">Você pode adotar esta área e se comprometer a cuidar dela por 3 meses para ganhar um NFT de Guardião!</p>
        <button class="btn btn-primary btn-sm" onclick="window.iniciarAdocao(${lat}, ${lng})">
          Adotar Ponto
        </button>
      </div>
    `, { closeButton: false }).openPopup()
  })
}

function renderMarkers() {
  if (!map) return
  
  // Limpa marcadores existentes
  markers.forEach(m => map.removeLayer(m))
  markers = []
  if (tempMarker) {
    map.removeLayer(tempMarker)
    tempMarker = null
  }

  filteredPoints.value.forEach(p => {
    if (!p.latitude || !p.longitude) return

    let emoji = '📍'
    let statusClass = 'marker-disponivel'

    if (p.status === 'ativo') {
      emoji = '🌱'
      statusClass = 'marker-ativo'
    } else if (p.status === 'alerta') {
      emoji = '🍂'
      statusClass = 'marker-alerta'
    } else if (p.status === 'concluido') {
      emoji = '👑'
      statusClass = 'marker-concluido'
    }

    const icon = window.L.divIcon({
      className: `eco-marker ${statusClass}`,
      html: `<div class="marker-emoji-wrapper">${emoji}</div>`,
      iconSize: [34, 34],
      iconAnchor: [17, 34],
      popupAnchor: [0, -30]
    })

    const m = window.L.marker([p.latitude, p.longitude], { icon }).addTo(map)

    const popupHtml = `
      <div class="ponto-popup">
        <span class="ponto-tag ${p.categoria}">${formatCategoria(p.categoria)}</span>
        <h4>${p.nome}</h4>
        <div class="ponto-meta">
          ${p.guardiao_name 
            ? `<span>👤 Adotado por <strong>${p.guardiao_name}</strong></span>` 
            : '<span class="disponivel-lbl">✨ Disponível para adoção</span>'}
        </div>
        ${p.status === 'concluido' 
          ? `<div class="badge-concluido">👑 Guardião Consagrado (NFT #${p.nft_token_id || ''})</div>`
          : ''}
        ${p.status === 'alerta' 
          ? '<div class="badge-alerta">⚠️ Check-in mensal em atraso!</div>'
          : ''}
        
        <div class="popup-footer">
          ${p.guardiao_id === auth.user?.id && p.status !== 'concluido'
            ? `<button class="btn btn-accent btn-sm" onclick="window.location.href='/app/dashboard'">Fazer Check-in</button>`
            : p.status === 'disponivel' && auth.isCidadao
              ? `<button class="btn btn-primary btn-sm" onclick="window.iniciarAdocao(${p.latitude}, ${p.longitude})">Adotar agora</button>`
              : ''}
        </div>
      </div>
    `

    // Se o botão de adotar estiver no popup de um ponto disponível já pré-cadastrado
    window.iniciarAdocao = (latitude, longitude) => {
      router.push({
        path: '/app/adotar-area',
        query: { lat: latitude, lng: longitude, nome: p.nome, categoria: p.categoria }
      })
    }

    m.bindPopup(popupHtml)
    markers.push(m)
  })
}

function flyToPoint(p) {
  if (viewMode.value !== 'mapa') {
    viewMode.value = 'mapa'
    nextTick(() => {
      if (map) {
        map.setView([p.latitude, p.longitude], 16)
        renderMarkers()
      }
    })
  } else if (map) {
    map.setView([p.latitude, p.longitude], 16)
  }
}

function formatCategoria(cat) {
  const map = {
    praca: 'Praça 🌳',
    canteiro: 'Canteiro 🌱',
    praia: 'Praia 🏖️',
    rio: 'Margem de Rio 🏞️',
    outro: 'Outro 🌿'
  }
  return map[cat] || cat
}
</script>

<template>
  <div class="container pontos-verdes-container">
    
    <header class="page-header">
      <div>
            <div style="margin-bottom: 1rem;">
      <RouterLink to="/app/dashboard" style="color: var(--color-muted); text-decoration: none; font-weight: 600; display: inline-flex; align-items: center; gap: 0.3rem;">
        <span>←</span> Voltar ao Dashboard
      </RouterLink>
    </div>
        <h1>Adoção de Pontos Verdes 🌿</h1>
        <p class="muted">Adote e cuide de áreas verdes públicas por 3 meses para conquistar seu NFT de Guardião.</p>
      </div>
      <div class="toggle-view">
        <button :class="{ active: viewMode === 'mapa' }" @click="viewMode = 'mapa'">🗺️ Mapa</button>
        <button :class="{ active: viewMode === 'lista' }" @click="viewMode = 'lista'">📋 Lista</button>
      </div>
    </header>

    <!-- Barra de Filtros -->
    <div class="filters-card card">
      <div class="search-input">
        🔍 <input type="text" v-model="buscaQuery" placeholder="Pesquisar por nome do local ou guardião..." />
      </div>
      <div class="filter-selects">
        <select v-model="filtroCategoria" class="select-filter">
          <option value="">Todas as categorias</option>
          <option value="praca">🌳 Praças</option>
          <option value="canteiro">🌱 Canteiros</option>
          <option value="praia">🏖️ Praias</option>
          <option value="rio">🏞️ Margens de Rio</option>
          <option value="outro">🌿 Outros</option>
        </select>
        <select v-model="filtroStatus" class="select-filter">
          <option value="">Todos os status</option>
          <option value="disponivel">✨ Disponível</option>
          <option value="ativo">🟢 Ativo/Cuidado</option>
          <option value="alerta">🔴 Abandonado/Em Alerta</option>
          <option value="concluido">🏆 Consagrado (NFT)</option>
        </select>
      </div>
    </div>

    <!-- Conteúdo Principal -->
    <div class="main-layout">
      
      <!-- Seção Lateral: Lista de Pontos para clique fácil e "Fly To" -->
      <aside class="sidebar-list card" v-if="viewMode === 'mapa'">
        <h3>Áreas Registradas</h3>
        <p class="muted hint" v-if="auth.isCidadao">💡 Clique em qualquer lugar vazio do mapa para propor uma nova adoção!</p>
        <div class="points-scroll">
          <div v-if="store.loading" class="skeleton-pill" v-for="i in 3" :key="i"></div>
          <div v-else-if="!filteredPoints.length" class="empty-sidebar">Nenhum ponto verde encontrado.</div>
          <div 
            v-else 
            v-for="p in filteredPoints" 
            :key="p.id" 
            class="point-sidebar-card"
            @click="flyToPoint(p)"
          >
            <div class="card-info">
              <strong>{{ p.nome }}</strong>
              <span class="category-tag">{{ formatCategoria(p.categoria) }}</span>
              <span class="owner" v-if="p.guardiao_name">👤 {{ p.guardiao_name }}</span>
              <span class="owner green" v-else>✨ Disponível</span>
            </div>
            <div class="card-badge-status">
              <span class="status-indicator" :class="p.status"></span>
            </div>
          </div>
        </div>
      </aside>

      <!-- Área do Mapa -->
      <main class="map-view-wrapper" :class="{ 'full-width': viewMode === 'lista' }">
        <div v-show="viewMode === 'mapa'" ref="mapRef" class="leaflet-map-element"></div>

        <!-- Visão em Grid/Lista Alternativa -->
        <div v-if="viewMode === 'lista'" class="list-grid">
          <div v-if="store.loading" class="grid grid-cards">
            <div class="skeleton" style="height: 180px" v-for="i in 3" :key="i"></div>
          </div>
          <div v-else-if="!filteredPoints.length" class="card empty-state">
            Nenhuma área pública cadastrada com estes filtros.
          </div>
          <div v-else class="grid grid-cards">
            <div v-for="p in filteredPoints" :key="p.id" class="card point-grid-card">
              <div class="grid-header">
                <span class="ponto-tag" :class="p.categoria">{{ formatCategoria(p.categoria) }}</span>
                <span class="status-dot" :class="p.status" :title="p.status"></span>
              </div>
              <h3>{{ p.nome }}</h3>
              <p class="muted coords">📍 Lat: {{ p.latitude.toFixed(4) }} · Lng: {{ p.longitude.toFixed(4) }}</p>
              
              <div class="grid-body">
                <p v-if="p.guardiao_name">Adotado por: <strong>{{ p.guardiao_name }}</strong></p>
                <p v-else class="green-text">✨ Disponível para adoção!</p>
                
                <p v-if="p.data_inicio" class="muted small-text">Adotado em: {{ formatDate(p.data_inicio) }}</p>
              </div>

              <div class="grid-footer">
                <button 
                  v-if="p.status === 'disponivel' && auth.isCidadao" 
                  class="btn btn-primary btn-sm"
                  @click="flyToPoint(p)"
                >
                  Adotar Área
                </button>
                <button v-else class="btn btn-ghost btn-sm" @click="flyToPoint(p)">
                  Ver no Mapa
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>

    </div>
  </div>
</template>

<style scoped>
.pontos-verdes-container {
  padding-bottom: 3rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.toggle-view {
  display: flex;
  background: var(--color-border, #e2ebe4);
  padding: 4px;
  border-radius: var(--radius-md);
}
.toggle-view button {
  padding: 0.5rem 1.1rem;
  border: none;
  background: transparent;
  cursor: pointer;
  font-weight: 600;
  border-radius: var(--radius-sm);
  color: var(--color-muted);
  transition: all 0.15s ease;
}
.toggle-view button.active {
  background: #fff;
  color: var(--color-primary);
  box-shadow: var(--shadow-card);
}

/* Filtros */
.filters-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}
.search-input {
  flex: 1;
  min-width: 280px;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  border: 1px solid var(--color-border);
  padding: 0.6rem 0.9rem;
  border-radius: var(--radius-sm);
  background: #fff;
}
.search-input input {
  border: none;
  outline: none;
  width: 100%;
  font-size: 0.95rem;
}
.filter-selects {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.select-filter {
  padding: 0.6rem 0.9rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
  background: #fff;
  cursor: pointer;
}

/* Layout */
.main-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 1.5rem;
  height: 560px;
}
@media (max-width: 900px) {
  .main-layout {
    grid-template-columns: 1fr;
    height: auto;
  }
  .sidebar-list {
    display: none; /* Esconde lista lateral em telas pequenas */
  }
}

.sidebar-list {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 1.25rem;
}
.sidebar-list h3 {
  font-size: 1.15rem;
  margin-bottom: 0.5rem;
}
.hint {
  font-size: 0.78rem;
  margin-bottom: 1rem;
  line-height: 1.3;
}
.points-scroll {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding-right: 4px;
}

.point-sidebar-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.15s ease;
  background: var(--color-bg);
}
.point-sidebar-card:hover {
  border-color: var(--color-secondary);
  background: #fff;
  transform: translateX(2px);
}
.card-info {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.card-info strong {
  font-size: 0.9rem;
  color: var(--color-primary);
}
.category-tag {
  font-size: 0.72rem;
  color: var(--color-muted);
  font-weight: 500;
}
.owner {
  font-size: 0.75rem;
  color: var(--color-text);
}
.owner.green {
  color: var(--color-secondary);
  font-weight: 600;
}

.status-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}
.status-indicator.disponivel { background: #cbd5e1; }
.status-indicator.ativo { background: #22c55e; }
.status-indicator.alerta { background: #dc2626; }
.status-indicator.concluido { background: #c9a84c; }

/* Mapa */
.map-view-wrapper {
  position: relative;
  height: 100%;
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-card);
}
.map-view-wrapper.full-width {
  height: auto;
}
.leaflet-map-element {
  width: 100%;
  height: 100%;
  z-index: 10;
}

/* List Grid View */
.list-grid {
  padding-bottom: 2rem;
}
.point-grid-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 0.75rem;
}
.grid-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.coords {
  font-size: 0.8rem;
  font-family: monospace;
}
.grid-body {
  font-size: 0.9rem;
}
.green-text {
  color: var(--color-secondary);
  font-weight: 700;
}
.small-text {
  font-size: 0.75rem;
}
.grid-footer {
  margin-top: 0.5rem;
}
.status-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}
.status-dot.disponivel { background: #94a3b8; }
.status-dot.ativo { background: #22c55e; }
.status-dot.alerta { background: #ef4444; }
.status-dot.concluido { background: #eab308; }

.empty-state {
  text-align: center;
  padding: 3rem 1rem;
  color: var(--color-muted);
}

/* Skeletons */
.skeleton-pill {
  height: 64px;
  border-radius: var(--radius-sm);
  background: linear-gradient(90deg, #f0f3f1 25%, #e1e9e3 50%, #f0f3f1 75%);
  background-size: 200% 100%;
  animation: sk 1.2s infinite;
}

/* Estilos de Popups e Marcadores */
:global(.eco-marker) {
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 20px;
  background: #fff;
  border-radius: 50%;
  border: 2px solid #fff;
  box-shadow: 0 2px 6px rgba(0,0,0,0.15);
  transition: transform 0.2s ease;
}

:global(.eco-marker:hover) {
  transform: scale(1.15) translateY(-3px);
  z-index: 1000 !important;
}

:global(.marker-disponivel) {
  border-color: #cbd5e1;
  background: #f8fafc;
}

:global(.marker-ativo) {
  border-color: #22c55e;
  background: #f0fdf4;
}

:global(.marker-alerta) {
  border-color: #ef4444;
  background: #fef2f2;
  animation: marker-pulse-danger 2s infinite;
}

:global(.marker-concluido) {
  border-color: #eab308;
  background: #fef9c3;
  box-shadow: 0 0 10px rgba(234, 179, 8, 0.4);
}

:global(.marker-new-draft) {
  border-color: #2e7d52;
  background: #e8f5e9;
  animation: draft-bounce 0.8s ease infinite alternate;
}

@keyframes marker-pulse-danger {
  0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
  70% { box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); }
  100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
}

@keyframes draft-bounce {
  from { transform: translateY(0); }
  to { transform: translateY(-6px); }
}

:global(.ponto-popup) {
  min-width: 200px;
  font-family: var(--font-body), sans-serif;
}
:global(.ponto-popup h4) {
  margin: 0.4rem 0;
  font-size: 1rem;
  color: var(--color-primary);
}
:global(.ponto-tag) {
  font-size: 0.65rem;
  font-weight: 700;
  padding: 0.15rem 0.45rem;
  border-radius: 99px;
  display: inline-block;
}
:global(.ponto-tag.praca) { background: #e2f0e6; color: #1e4620; }
:global(.ponto-tag.canteiro) { background: #e8f5e9; color: #2e7d52; }
:global(.ponto-tag.praia) { background: #fff8e1; color: #f57f17; }
:global(.ponto-tag.rio) { background: #e3f2fd; color: #0d47a1; }
:global(.ponto-tag.outro) { background: #eceff1; color: #37474f; }

:global(.ponto-meta) {
  font-size: 0.8rem;
  margin-bottom: 0.5rem;
  color: #555;
}
:global(.disponivel-lbl) {
  color: var(--color-secondary);
  font-weight: 600;
}
:global(.badge-concluido) {
  background: #fef9c3;
  color: #854d0e;
  border: 1px solid #fde047;
  padding: 0.3rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  margin: 0.4rem 0;
}
:global(.badge-alerta) {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fee2e2;
  padding: 0.3rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  margin: 0.4rem 0;
}
:global(.popup-footer) {
  display: flex;
  justify-content: flex-end;
  margin-top: 0.5rem;
  border-top: 1px solid #eee;
  padding-top: 0.5rem;
}

:global(.popup-adocao) {
  text-align: center;
  max-width: 220px;
}
:global(.popup-adocao h3) {
  margin: 0 0 0.3rem;
  font-size: 0.95rem;
}
:global(.popup-adocao p) {
  font-size: 0.78rem;
  margin: 0 0 0.6rem;
  line-height: 1.3;
}
</style>
