<script setup>
import { onMounted, ref, computed } from 'vue'
import { useAuthStore } from '../stores/auth'
import { api, apiFormData } from '../utils/api'
import { formatDate, formatTipoAcao } from '../utils/format'
import StatusBadge from '../components/StatusBadge.vue'
import { useToast } from '../composables/useToast'

const auth = useAuthStore()
const toast = useToast()

// ── Estado ─────────────────────────────────────────────────────────────────
const eventos  = ref([])
const loading  = ref(true)
const showForm = ref(false)
const saving   = ref(false)

const form = ref({
  titulo: '', descricao: '', local: '',
  data_evento: '', tipo_acao: 'lixo_rua',
})

// ── Computed ────────────────────────────────────────────────────────────────
const totalAtivos    = computed(() => eventos.value.filter(e => e.status === 'ativo').length)
const totalParticip  = computed(() => eventos.value.reduce((s, e) => s + (e.total_participantes || 0), 0))
const temAprovados   = (ev) => ev.status === 'ativo' // heurística básica

// ── Carregamento ────────────────────────────────────────────────────────────
async function load() {
  loading.value = true
  try {
    // ✅ Rota correta: GET /eventos/meus (não /eventos/me)
    const res = await api.get('/eventos/meus?page=1&page_size=50')
    eventos.value = Array.isArray(res) ? res : (res.items ?? [])
  } catch (e) {
    toast.error('Erro ao carregar eventos: ' + e.message)
  } finally {
    loading.value = false
  }
}

onMounted(load)

// ── Criar evento ─────────────────────────────────────────────────────────
async function criar() {
  // Validação básica
  if (!form.value.titulo.trim()) { toast.warn('Informe o título do evento.'); return }
  if (!form.value.local.trim())  { toast.warn('Informe o local do evento.'); return }
  if (!form.value.data_evento)   { toast.warn('Informe a data e hora do evento.'); return }

  saving.value = true
  try {
    // ✅ POST /eventos usa multipart/form-data (não JSON)
    const fd = new FormData()
    fd.append('titulo',      form.value.titulo.trim())
    fd.append('local',       form.value.local.trim())
    fd.append('tipo_acao',   form.value.tipo_acao)
    // datetime-local retorna "2026-06-15T09:00" — backend espera ISO 8601
    fd.append('data_evento', form.value.data_evento + ':00')
    if (form.value.descricao.trim()) fd.append('descricao', form.value.descricao.trim())

    await apiFormData('/eventos', fd, 'POST')
    toast.success('Evento criado com sucesso!')
    showForm.value = false
    form.value = { titulo: '', descricao: '', local: '', data_evento: '', tipo_acao: 'lixo_rua' }
    await load()
  } catch (e) {
    toast.error(e.message)
  } finally {
    saving.value = false
  }
}

// ── Cancelar evento ─────────────────────────────────────────────────────
async function cancelarEvento(ev) {
  if (!confirm(`Cancelar o evento "${ev.titulo}"?`)) return
  try {
    await api.del(`/eventos/${ev.id}`)
    toast.success('Evento cancelado.')
    await load()
  } catch (e) {
    toast.error(e.message)
  }
}

</script>

<template>
  <div class="container instituto-dash">

    <!-- Cabeçalho -->
    <header class="dash-head">
      <div>
        <h1>Painel do Instituto 🏛️</h1>
        <p class="muted">Gerencie seus eventos e participantes.</p>
      </div>
      <button id="btn-criar-evento" class="btn btn-primary" @click="showForm = true">
        + Criar evento
      </button>
    </header>

    <!-- Stats rápidas -->
    <div class="stats-row" v-if="!loading && eventos.length">
      <div class="stat-pill">
        <span class="stat-num">{{ eventos.length }}</span>
        <span class="stat-lbl">eventos</span>
      </div>
      <div class="stat-pill">
        <span class="stat-num">{{ totalAtivos }}</span>
        <span class="stat-lbl">ativos</span>
      </div>
      <div class="stat-pill">
        <span class="stat-num">{{ totalParticip }}</span>
        <span class="stat-lbl">participantes</span>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="skeleton-list">
      <div class="skeleton" v-for="i in 3" :key="i"></div>
    </div>

    <!-- Sem eventos -->
    <div v-else-if="!eventos.length" class="empty-card">
      <span class="empty-icon">📅</span>
      <div>
        <strong>Nenhum evento criado ainda.</strong>
        <p>Crie um mutirão de limpeza e convide cidadãos para participar.</p>
        <button class="btn btn-primary" style="margin-top:.75rem" @click="showForm = true">
          Criar primeiro evento
        </button>
      </div>
    </div>

    <!-- Lista de eventos -->
    <ul v-else class="evento-list">
      <li v-for="ev in eventos" :key="ev.id" class="evento-card">

        <!-- Foto de capa -->
        <div class="evento-capa" :style="ev.foto_capa_url ? `background-image:url(${ev.foto_capa_url})` : ''">
          <span v-if="!ev.foto_capa_url" class="capa-placeholder">🌿</span>
        </div>

        <!-- Conteúdo -->
        <div class="evento-body">
          <div class="evento-top">
            <div>
              <div class="evento-title-row">
                <strong>{{ ev.titulo }}</strong>
                <StatusBadge :status="ev.status" />
              </div>
              <p class="muted evento-meta">
                📍 {{ ev.local }} &nbsp;·&nbsp;
                📅 {{ formatDate(ev.data_evento) }} &nbsp;·&nbsp;
                {{ formatTipoAcao(ev.tipo_acao) }}
              </p>
              <p class="muted evento-meta">
                👥 {{ ev.total_participantes || 0 }} participantes
              </p>
            </div>
          </div>

          <!-- Ações -->
          <div class="evento-actions">
            <RouterLink
              :to="`/instituto/eventos/${ev.id}`"
              class="btn btn-ghost"
              :id="`btn-gerenciar-${ev.id}`"
            >
              Gerenciar participantes
            </RouterLink>

            <!-- Badge: aprovados aguardando NFT (leva para a página do evento) -->
            <RouterLink
              v-if="ev.status === 'ativo' && (ev.total_participantes || 0) > 0"
              :to="`/instituto/eventos/${ev.id}`"
              class="badge-nft-link"
              :title="`Acesse o evento para emitir NFTs`"
            >
              🎖️ Emitir NFTs
            </RouterLink>

            <button
              v-if="ev.status === 'ativo'"
              class="btn btn-danger"
              @click="cancelarEvento(ev)"
            >
              Cancelar
            </button>
          </div>
        </div>
      </li>
    </ul>

    <!-- ── Modal: Criar evento ─────────────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="showForm" class="backdrop" @click.self="showForm = false">
        <div class="modal card">
          <div class="modal-header">
            <h2>Novo evento de mutirão</h2>
            <button class="btn-close" @click="showForm = false" aria-label="Fechar">✕</button>
          </div>

          <form id="form-criar-evento" @submit.prevent="criar">
            <div class="field">
              <label class="label" for="ev-titulo">Título *</label>
              <input id="ev-titulo" class="input" v-model="form.titulo" required
                     placeholder="Ex: Mutirão Praia Grande" maxlength="200" />
            </div>

            <div class="field">
              <label class="label" for="ev-local">Local *</label>
              <input id="ev-local" class="input" v-model="form.local" required
                     placeholder="Ex: Praia Grande, SP" maxlength="300" />
            </div>

            <div class="field-row">
              <div class="field">
                <label class="label" for="ev-data">Data e hora *</label>
                <input id="ev-data" class="input" type="datetime-local"
                       v-model="form.data_evento" required />
              </div>
              <div class="field">
                <label class="label" for="ev-tipo">Tipo de ação *</label>
                <select id="ev-tipo" class="input select" v-model="form.tipo_acao">
                  <option value="lixo_rua">🗑️ Lixo na rua</option>
                  <option value="praia">🏖️ Praia</option>
                  <option value="corrego">🏞️ Córrego</option>
                  <option value="queimada">🔥 Queimada</option>
                  <option value="outro">🌱 Outro</option>
                </select>
              </div>
            </div>

            <div class="field">
              <label class="label" for="ev-desc">Descrição</label>
              <textarea id="ev-desc" class="input" v-model="form.descricao"
                        rows="3" placeholder="Descreva o evento (opcional)" maxlength="2000"></textarea>
            </div>

            <div class="modal-footer">
              <button type="button" class="btn btn-ghost" @click="showForm = false">Cancelar</button>
              <button id="btn-salvar-evento" class="btn btn-primary" :disabled="saving">
                <span v-if="saving" class="spinner-sm"></span>
                {{ saving ? 'Criando…' : 'Criar evento' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

  </div>
</template>

<style scoped>
.instituto-dash { padding-bottom: 3rem; }

.dash-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 1.5rem;
}
.dash-head h1 { font-size: 1.9rem; margin: 0 0 .25rem; }

/* Stats row */
.stats-row {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}
.stat-pill {
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: var(--radius-md, 12px);
  padding: .75rem 1.25rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 80px;
}
.stat-num { font-size: 1.5rem; font-weight: 800; color: var(--color-primary, #22c55e); }
.stat-lbl { font-size: .78rem; color: var(--color-muted, #64748b); font-weight: 500; }

/* Skeleton */
.skeleton-list { display: flex; flex-direction: column; gap: .8rem; }
.skeleton {
  height: 120px;
  border-radius: var(--radius-md, 12px);
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite;
}
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

/* Empty state */
.empty-card {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  border: 1px dashed var(--color-border, #e2e8f0);
  border-radius: var(--radius-md, 12px);
  padding: 2rem;
  color: var(--color-muted, #64748b);
}
.empty-icon { font-size: 2.5rem; flex-shrink: 0; }
.empty-card strong { display: block; color: var(--color-text, #1a1a1a); margin-bottom: .3rem; }
.empty-card p { margin: 0; font-size: .9rem; }

/* Lista de eventos */
.evento-list { list-style: none; padding: 0; display: flex; flex-direction: column; gap: 1rem; }
.evento-card {
  display: flex;
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: var(--radius-md, 12px);
  overflow: hidden;
  transition: box-shadow .15s;
}
.evento-card:hover { box-shadow: var(--shadow-card, 0 4px 16px rgba(0,0,0,.08)); }

.evento-capa {
  width: 140px;
  min-height: 120px;
  flex-shrink: 0;
  background: #f0fdf4 center/cover no-repeat;
  display: flex;
  align-items: center;
  justify-content: center;
}
.capa-placeholder { font-size: 2.5rem; }

.evento-body {
  flex: 1;
  padding: 1rem 1.25rem;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: .75rem;
}
.evento-title-row {
  display: flex;
  align-items: center;
  gap: .6rem;
  flex-wrap: wrap;
  margin-bottom: .3rem;
}
.evento-title-row strong { font-size: 1.05rem; }
.evento-meta { font-size: .85rem; margin: .15rem 0 0; }

.evento-actions {
  display: flex;
  gap: .5rem;
  flex-wrap: wrap;
  align-items: center;
}

/* Botão vermelho */
.btn-danger {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fca5a5;
  border-radius: var(--radius-sm, 8px);
  padding: .5rem .9rem;
  font-weight: 600;
  font-size: .875rem;
  cursor: pointer;
  transition: background .15s;
}
.btn-danger:hover { background: #fee2e2; }

/* Badge/link NFT */
.badge-nft-link {
  display: inline-flex;
  align-items: center;
  gap: .3rem;
  padding: .5rem .9rem;
  background: #f5f3ff;
  color: #6d28d9;
  border: 1px solid #c4b5fd;
  border-radius: var(--radius-sm, 8px);
  font-weight: 600;
  font-size: .875rem;
  text-decoration: none;
  transition: background .15s;
}
.badge-nft-link:hover { background: #ede9fe; }

/* Modal */
.backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.55);
  display: grid;
  place-items: center;
  padding: 1rem;
  z-index: 80;
  backdrop-filter: blur(2px);
}
.modal {
  max-width: 580px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}
.modal-header h2 { margin: 0; font-size: 1.3rem; }
.btn-close {
  background: none;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  color: var(--color-muted, #64748b);
  line-height: 1;
  padding: .25rem;
}
.btn-close:hover { color: var(--color-text, #1a1a1a); }

.field { display: flex; flex-direction: column; gap: .35rem; margin-bottom: 1rem; }
.field-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
@media (max-width: 480px) { .field-row { grid-template-columns: 1fr; } }
.label { font-size: .875rem; font-weight: 600; color: var(--color-text, #1a1a1a); }
.input { padding: .65rem .9rem; border: 1.5px solid var(--color-border, #e2e8f0); border-radius: var(--radius-sm, 8px); font-size: .95rem; background: var(--color-bg, #fff); color: var(--color-text, #1a1a1a); outline: none; width: 100%; box-sizing: border-box; }
.input:focus { border-color: var(--color-primary, #22c55e); box-shadow: 0 0 0 3px rgba(34,197,94,.15); }
textarea.input { resize: vertical; min-height: 80px; }

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: .5rem;
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border, #e2e8f0);
}

/* Spinner */
.spinner-sm {
  display: inline-block;
  width: 14px; height: 14px;
  border: 2px solid rgba(255,255,255,.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin .7s linear infinite;
  margin-right: 4px;
  vertical-align: middle;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
