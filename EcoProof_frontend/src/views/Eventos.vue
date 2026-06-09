<script setup>
import { onMounted, ref, watch, nextTick, onBeforeUnmount } from 'vue'
import { useEventosStore } from '../stores/eventos'
import { useAuthStore } from '../stores/auth'
import { api, apiFormData } from '../utils/api'
import { formatDate, formatTipoAcao } from '../utils/format'
import StatusBadge from '../components/StatusBadge.vue'
import ImageUpload from '../components/ImageUpload.vue'
import { useToast } from '../composables/useToast'

const store = useEventosStore(); const auth = useAuthStore(); const toast = useToast()
const view = ref('lista')
const filtros = ref({ status:'', tipo_acao:'' })
const fotoModal = ref(null); const fotoFile = ref(null)
let map = null; const mapRef = ref(null)

onMounted(() => store.fetchEventos(cleanFilters()))
watch(filtros, () => { store.page = 1; store.fetchEventos(cleanFilters()) }, { deep:true })
watch([view, () => store.items], async () => {
  if (view.value === 'mapa') { await nextTick(); renderMap() }
})
onBeforeUnmount(() => { if (map) { map.remove(); map = null } })

function cleanFilters() {
  const o = {}; for (const k in filtros.value) if (filtros.value[k]) o[k] = filtros.value[k]; return o
}

function renderMap() {
  if (!window.L || !mapRef.value) return
  if (map) { map.remove(); map = null }
  map = window.L.map(mapRef.value).setView([-23.55, -46.63], 11)
  window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution:'© OSM' }).addTo(map)
  const icon = window.L.divIcon({ className:'eco-marker', html:'🌿', iconSize:[28,28] })
  store.items.forEach(e => {
    if (e.latitude && e.longitude) {
      window.L.marker([e.latitude, e.longitude], { icon }).addTo(map).bindPopup(`<b>${e.titulo}</b><br>${e.local}`)
    }
  })
}

async function participar(ev) {
  if (!auth.isAuthenticated) return toast.warn('Faça login para participar.')
  try { await api.post(`/eventos/${ev.id}/participar`); toast.success('Check-in realizado!'); store.fetchEventos(cleanFilters()) }
  catch (e) { toast.error(e.message) }
}
function abrirFoto(ev) { fotoModal.value = ev; fotoFile.value = null }
async function enviarFoto() {
  if (!fotoFile.value) return
  const fd = new FormData(); fd.append('foto', fotoFile.value)
  try {
    await apiFormData(`/eventos/${fotoModal.value.id}/participacoes/${fotoModal.value.minha_participacao_id}/foto`, fd)
    toast.success('Foto enviada!'); fotoModal.value = null
  } catch (e) { toast.error(e.message) }
}
</script>
<template>
  <div class="container">
        <div style="margin-bottom: 1rem;">
      <RouterLink to="/app/dashboard" style="color: var(--color-muted); text-decoration: none; font-weight: 600; display: inline-flex; align-items: center; gap: 0.3rem;">
        <span>←</span> Voltar ao Dashboard
      </RouterLink>
    </div>
    <header class="head">
      <div><h1>Eventos</h1><p class="muted">Participe de ações coletivas e ganhe NFTs.</p></div>
      <div class="toggle">
        <button :class="{active: view==='lista'}" @click="view='lista'">Lista</button>
        <button :class="{active: view==='mapa'}" @click="view='mapa'">Mapa</button>
      </div>
    </header>

    <div class="filters card">
      <select class="select" v-model="filtros.status">
        <option value="">Todos os status</option><option value="ativo">Ativo</option><option value="encerrado">Encerrado</option>
      </select>
      <select class="select" v-model="filtros.tipo_acao">
        <option value="">Todos os tipos</option>
        <option value="lixo_rua">Lixo na rua</option><option value="praia">Praia</option>
        <option value="corrego">Córrego</option><option value="queimada">Queimada</option><option value="outro">Outro</option>
      </select>
    </div>

    <div v-if="view==='lista'">
      <div v-if="store.loading" class="grid grid-cards">
        <div class="skeleton" style="height:160px" v-for="i in 3" :key="i"></div>
      </div>
      <div v-else-if="!store.items.length" class="card muted">Nenhum evento encontrado.</div>
      <div v-else class="grid grid-cards">
        <article v-for="e in store.items" :key="e.id" class="card evt">
          <div class="evt-head"><h3>{{ e.titulo }}</h3><StatusBadge :status="e.status" /></div>
          <p class="muted">{{ e.local }} · {{ formatDate(e.data_evento) }}</p>
          <p><span class="badge" style="background:#eef3ee;color:var(--color-primary)">{{ formatTipoAcao(e.tipo_acao) }}</span></p>
          <p v-if="e.instituto_nome" class="muted">por {{ e.instituto_nome }}</p>
          <div class="evt-actions">
            <button v-if="auth.isCidadao && e.minha_participacao_status === 'confirmado'" class="btn btn-accent" @click="abrirFoto(e)">Enviar foto</button>
            <button v-else-if="auth.isCidadao && !e.minha_participacao_status" class="btn btn-primary" @click="participar(e)">Participar</button>
            <StatusBadge v-else-if="e.minha_participacao_status" :status="e.minha_participacao_status" />
          </div>
        </article>
      </div>
    </div>
    <div v-else>
      <div ref="mapRef" class="map"></div>
    </div>

    <Teleport to="body">
      <div v-if="fotoModal" class="backdrop" @click.self="fotoModal=null">
        <div class="modal card">
          <h3>Enviar foto — {{ fotoModal.titulo }}</h3>
          <ImageUpload label="Foto da ação" @update:file="fotoFile = $event" />
          <div style="display:flex; gap:.5rem; justify-content:flex-end; margin-top:1rem">
            <button class="btn btn-ghost" @click="fotoModal=null">Cancelar</button>
            <button class="btn btn-primary" :disabled="!fotoFile" @click="enviarFoto">Enviar</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
<style scoped>
.head { display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem; flex-wrap:wrap; gap:1rem; }
.toggle { display:flex; background:#eef3ee; border-radius: var(--radius-md); padding:4px; }
.toggle button { padding:.5rem 1rem; border:none; background:transparent; border-radius: var(--radius-sm); cursor:pointer; font-weight:600; color: var(--color-muted); }
.toggle button.active { background:#fff; color: var(--color-primary); box-shadow: var(--shadow-card); }
.filters { display:flex; gap:.6rem; margin-bottom:1rem; flex-wrap:wrap; }
.filters .select { max-width:240px; }
.evt-head { display:flex; justify-content:space-between; align-items:flex-start; }
.evt-actions { margin-top:.8rem; }
.map { height:520px; border-radius: var(--radius-md); overflow:hidden; box-shadow: var(--shadow-card); }
.backdrop { position:fixed; inset:0; background:rgba(0,0,0,.5); display:grid; place-items:center; padding:1rem; z-index:80; }
.modal { max-width:520px; width:100%; }
:global(.eco-marker) { font-size:22px; text-align:center; }
</style>
