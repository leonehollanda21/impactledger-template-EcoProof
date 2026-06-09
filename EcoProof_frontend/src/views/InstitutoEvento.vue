<script setup>
import { onMounted, ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../utils/api'
import { formatDate } from '../utils/format'
import StatusBadge from '../components/StatusBadge.vue'
import { useToast } from '../composables/useToast'

const route  = useRoute()
const toast  = useToast()
const eventoId = route.params.id

// ── Estado principal ─────────────────────────────────────────────────────────
const evento      = ref(null)
const items       = ref([])      // participações
const nftStatus   = ref({})      // { [participacao_id]: { tem_nft, token_id, tx_hash } }
const loading     = ref(true)
const filter      = ref('')

// ── Estado de modais ─────────────────────────────────────────────────────────
const rejecting   = ref(null)
const motivo      = ref('')
const fotoModal   = ref(null)
const aprovando   = ref(null)

// ── Estado de emissão ─────────────────────────────────────────────────────────
const showConfirm = ref(false)     // modal de confirmação
const emitindo    = ref(false)     // loading durante mint
const resultado   = ref(null)      // MintLoteDetalheResponse após emissão

// ── Computed ────────────────────────────────────────────────────────────────
const filtered = computed(() =>
  filter.value ? items.value.filter(p => p.status === filter.value) : items.value
)
const pendentes  = computed(() => items.value.filter(p => p.status === 'foto_enviada').length)
const aprovados  = computed(() => items.value.filter(p => p.status === 'aprovado').length)
const total      = computed(() => items.value.length)

// Aprovados que ainda NÃO têm NFT (alvo real do botão emitir)
const aprovadosSemNFT = computed(() =>
  items.value.filter(p => p.status === 'aprovado' && !nftStatus.value[p.id]?.tem_nft).length
)

// ── Carregamento ─────────────────────────────────────────────────────────────
async function load() {
  loading.value = true
  try {
    const [evRes, partRes] = await Promise.all([
      api.get(`/eventos/${eventoId}`),
      api.get(`/eventos/${eventoId}/participacoes?page=1&page_size=100`),
    ])
    evento.value = evRes
    items.value = Array.isArray(partRes) ? partRes : (partRes.items ?? [])

    // Carrega status de NFT para participantes aprovados
    await loadNftStatus()
  } catch (e) {
    toast.error('Erro ao carregar dados: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function loadNftStatus() {
  try {
    const statusList = await api.get(`/eventos/${eventoId}/nfts-status`)
    const map = {}
    for (const s of statusList) {
      map[s.participacao_id] = s
    }
    nftStatus.value = map
  } catch {
    // Silencioso — o status de NFT é enriquecimento, não crítico
  }
}

onMounted(load)

// ── Aprovar participação ──────────────────────────────────────────────────────
async function aprovar(p) {
  aprovando.value = p.id
  try {
    await api.patch(`/participacoes/${p.id}/aprovar`)
    toast.success(`${p.cidadao_nome} aprovado!`)
    await load()
  } catch (e) {
    toast.error(e.message)
  } finally {
    aprovando.value = null
  }
}

// ── Rejeitar participação ─────────────────────────────────────────────────────
function abrirRejeicao(p) { rejecting.value = p; motivo.value = '' }

async function confirmReject() {
  if (motivo.value.trim().length < 10) {
    toast.warn('O motivo precisa ter ao menos 10 caracteres.')
    return
  }
  try {
    await api.patch(`/participacoes/${rejecting.value.id}/rejeitar`, {
      motivo_rejeicao: motivo.value.trim(),
    })
    toast.success('Participação rejeitada.')
    rejecting.value = null
    motivo.value = ''
    await load()
  } catch (e) {
    toast.error(e.message)
  }
}

// ── Emissão de NFTs ───────────────────────────────────────────────────────────
function abrirConfirmacao() {
  if (!aprovadosSemNFT.value) {
    toast.warn('Nenhum participante aprovado aguardando NFT.')
    return
  }
  showConfirm.value = true
}

async function confirmarEmissao() {
  showConfirm.value = false
  emitindo.value = true
  resultado.value = null
  try {
    const r = await api.post(`/eventos/${eventoId}/emitir-nfts`)
    resultado.value = r
    await load()
  } catch (e) {
    toast.error('Erro ao emitir NFTs: ' + e.message)
  } finally {
    emitindo.value = false
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function shortHash(hash) {
  if (!hash) return '—'
  return hash.slice(0, 8) + '…' + hash.slice(-6)
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text)
  toast.success('Copiado!')
}
</script>

<template>
  <div class="container evento-page">

    <!-- Cabeçalho -->
    <header class="dash-head">
      <div>
        <RouterLink to="/instituto/dashboard" class="back-link">← Voltar ao painel</RouterLink>
        <h1>{{ evento?.titulo || 'Carregando…' }}</h1>
        <p v-if="evento" class="muted">
          📍 {{ evento.local }} &nbsp;·&nbsp;
          📅 {{ formatDate(evento.data_evento) }}
          <StatusBadge :status="evento.status" style="margin-left:.5rem" />
        </p>
      </div>

      <button
        id="btn-emitir-nfts"
        class="btn btn-accent"
        :disabled="emitindo || aprovadosSemNFT === 0"
        :title="aprovadosSemNFT === 0 ? 'Nenhum aprovado aguardando NFT' : `Emitir NFTs para ${aprovadosSemNFT} participantes`"
        @click="abrirConfirmacao"
      >
        <span v-if="emitindo" class="spinner-sm"></span>
        {{ emitindo ? 'Emitindo na blockchain…' : `🎖️ Emitir NFTs (${aprovadosSemNFT})` }}
      </button>
    </header>

    <!-- Stats -->
    <div class="stats-row" v-if="!loading">
      <div class="stat-pill">
        <span class="stat-num">{{ total }}</span>
        <span class="stat-lbl">total</span>
      </div>
      <div class="stat-pill stat-pendente">
        <span class="stat-num">{{ pendentes }}</span>
        <span class="stat-lbl">foto enviada</span>
      </div>
      <div class="stat-pill stat-aprovado">
        <span class="stat-num">{{ aprovados }}</span>
        <span class="stat-lbl">aprovados</span>
      </div>
      <div class="stat-pill stat-nft" v-if="aprovados > 0">
        <span class="stat-num">{{ aprovados - aprovadosSemNFT }}</span>
        <span class="stat-lbl">NFTs emitidos</span>
      </div>
    </div>

    <!-- Banner: resultado da emissão ────────────────────────────────────────── -->
    <div v-if="resultado" class="resultado-banner card">
      <div class="resultado-header">
        <div class="resultado-icon">🎖️</div>
        <div>
          <strong>Emissão concluída!</strong>
          <p class="muted" style="margin:0">
            {{ resultado.total_emitido }} NFT(s) emitido(s) ·
            {{ resultado.pontos_distribuidos }} pontos distribuídos
            <span v-if="resultado.total_erros > 0" class="badge-erro">
              {{ resultado.total_erros }} erro(s)
            </span>
          </p>
        </div>
        <button class="btn-close" @click="resultado = null">✕</button>
      </div>

      <div class="resultado-lista">
        <div
          v-for="item in resultado.resultados"
          :key="item.participacao_id"
          class="resultado-item"
          :class="item.sucesso ? 'resultado-ok' : 'resultado-err'"
        >
          <span class="resultado-check">{{ item.sucesso ? '✅' : '❌' }}</span>
          <div class="resultado-info">
            <strong>{{ item.cidadao_nome }}</strong>
            <span v-if="item.sucesso" class="resultado-token">
              Token #{{ item.token_id }} ·
              <button class="link-btn" @click="copyToClipboard(item.tx_hash)" :title="item.tx_hash">
                {{ shortHash(item.tx_hash) }} 📋
              </button>
            </span>
            <span v-else class="resultado-erro-msg">{{ item.erro }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Filtro -->
    <div class="filter-bar">
      <button
        v-for="opt in [
          { v: '',             l: 'Todos' },
          { v: 'confirmado',   l: 'Confirmado' },
          { v: 'foto_enviada', l: 'Foto enviada' },
          { v: 'aprovado',     l: 'Aprovado' },
          { v: 'rejeitado',    l: 'Rejeitado' },
        ]"
        :key="opt.v"
        :class="['filter-btn', { active: filter === opt.v }]"
        @click="filter = opt.v"
        type="button"
      >
        {{ opt.l }}
        <span v-if="opt.v" class="filter-count">
          {{ items.filter(p => p.status === opt.v).length }}
        </span>
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="skeleton-list">
      <div class="skeleton" v-for="i in 4" :key="i"></div>
    </div>

    <!-- Sem participações -->
    <div v-else-if="!filtered.length" class="empty-card">
      <span class="empty-icon">👥</span>
      <div>
        <strong>{{ filter ? `Nenhum participante com status "${filter}".` : 'Nenhuma participação ainda.' }}</strong>
        <p v-if="!filter">Compartilhe o evento para que cidadãos possam se inscrever.</p>
      </div>
    </div>

    <!-- Tabela de participantes -->
    <div v-else class="table-wrap card">
      <table class="tbl">
        <thead>
          <tr>
            <th></th>
            <th>Cidadão</th>
            <th>Status</th>
            <th>Check-in</th>
            <th>Foto</th>
            <th>NFT 🎖️</th>
            <th>Ações</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="p in filtered"
            :key="p.id"
            :class="{ 'row-pendente': p.status === 'foto_enviada', 'row-nft': nftStatus[p.id]?.tem_nft }"
          >
            <!-- Avatar -->
            <td>
              <div class="avatar">{{ (p.cidadao_nome || '?')[0].toUpperCase() }}</div>
            </td>

            <!-- Nome -->
            <td>
              <strong>{{ p.cidadao_nome || '—' }}</strong>
              <div v-if="p.motivo_rejeicao" class="motivo-text">{{ p.motivo_rejeicao }}</div>
            </td>

            <!-- Status -->
            <td><StatusBadge :status="p.status" /></td>

            <!-- Check-in -->
            <td class="muted">{{ formatDate(p.checkin_at) }}</td>

            <!-- Foto -->
            <td>
              <img
                v-if="p.foto_url"
                :src="p.foto_url"
                class="thumb"
                alt="Foto de participação"
                @click="fotoModal = p.foto_url"
              />
              <span v-else class="muted" style="font-size:.8rem">—</span>
            </td>

            <!-- NFT Status -->
            <td>
              <div v-if="nftStatus[p.id]?.tem_nft" class="nft-badge">
                <span class="nft-icon">🎖️</span>
                <div>
                  <span class="nft-token">#{{ nftStatus[p.id].token_id }}</span>
                  <button
                    class="link-btn nft-hash"
                    @click="copyToClipboard(nftStatus[p.id].tx_hash)"
                    :title="nftStatus[p.id].tx_hash"
                  >
                    {{ shortHash(nftStatus[p.id].tx_hash) }} 📋
                  </button>
                </div>
              </div>
              <span v-else-if="p.status === 'aprovado'" class="badge-pendente-nft">⏳ Pendente</span>
              <span v-else class="muted" style="font-size:.8rem">—</span>
            </td>

            <!-- Ações -->
            <td>
              <div class="action-btns" v-if="p.status === 'foto_enviada'">
                <button
                  class="btn btn-sm btn-success"
                  :disabled="aprovando === p.id"
                  @click="aprovar(p)"
                >
                  <span v-if="aprovando === p.id" class="spinner-sm"></span>
                  {{ aprovando === p.id ? '…' : '✓ Aprovar' }}
                </button>
                <button
                  class="btn btn-sm btn-danger"
                  @click="abrirRejeicao(p)"
                >
                  ✗ Rejeitar
                </button>
              </div>
              <span v-else class="muted" style="font-size:.8rem">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ── Teleports ──────────────────────────────────────────────────────── -->
    <Teleport to="body">

      <!-- Modal: Confirmação de emissão -->
      <div v-if="showConfirm" class="backdrop" @click.self="showConfirm = false">
        <div class="modal card">
          <div class="modal-header">
            <h3>⛓️ Confirmar Emissão na Blockchain</h3>
            <button class="btn-close" @click="showConfirm = false">✕</button>
          </div>

          <div class="confirm-body">
            <div class="confirm-info-row">
              <span class="confirm-icon">🎖️</span>
              <div>
                <strong>{{ aprovadosSemNFT }} participante(s) irão receber NFTs Soulbound</strong>
                <p class="muted" style="margin:.3rem 0 0">
                  Esta ação emitirá tokens na blockchain local (Hardhat). Os NFTs são
                  <strong>intransferíveis (EIP-5192)</strong> e cada participante receberá
                  <strong>30 pontos</strong>.
                </p>
              </div>
            </div>

            <div class="confirm-warning">
              ⚠️ <strong>Esta operação é irreversível.</strong>
              Certifique-se de que todos os participantes aprovados realmente participaram do evento.
            </div>

            <!-- Lista dos que vão receber -->
            <div class="confirm-lista">
              <p class="confirm-lista-title">Participantes que receberão NFT:</p>
              <div
                v-for="p in items.filter(p => p.status === 'aprovado' && !nftStatus[p.id]?.tem_nft)"
                :key="p.id"
                class="confirm-item"
              >
                <div class="avatar avatar-sm">{{ (p.cidadao_nome || '?')[0].toUpperCase() }}</div>
                <span>{{ p.cidadao_nome }}</span>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn btn-ghost" @click="showConfirm = false">Cancelar</button>
            <button
              id="btn-confirmar-emissao"
              class="btn btn-accent"
              @click="confirmarEmissao"
            >
              🚀 Emitir NFTs na Blockchain
            </button>
          </div>
        </div>
      </div>

      <!-- Modal: Rejeitar participação -->
      <div v-if="rejecting" class="backdrop" @click.self="rejecting = null">
        <div class="modal card">
          <div class="modal-header">
            <h3>Rejeitar participação</h3>
            <button class="btn-close" @click="rejecting = null">✕</button>
          </div>
          <p class="muted" style="margin-bottom:1rem">
            Informe o motivo da rejeição de <strong>{{ rejecting.cidadao_nome }}</strong>.
          </p>
          <textarea
            id="textarea-motivo"
            class="input"
            v-model="motivo"
            rows="4"
            placeholder="Descreva o motivo (mínimo 10 caracteres)…"
            maxlength="500"
          ></textarea>
          <p class="char-count" :class="{ 'text-warn': motivo.length < 10 }">
            {{ motivo.length }}/500 caracteres
          </p>
          <div class="modal-footer">
            <button class="btn btn-ghost" @click="rejecting = null">Cancelar</button>
            <button
              id="btn-confirmar-rejeicao"
              class="btn btn-danger-solid"
              :disabled="motivo.trim().length < 10"
              @click="confirmReject"
            >
              Confirmar rejeição
            </button>
          </div>
        </div>
      </div>

      <!-- Modal: Foto ampliada -->
      <div v-if="fotoModal" class="backdrop foto-backdrop" @click.self="fotoModal = null">
        <img :src="fotoModal" class="foto-ampliada" alt="Foto de participação ampliada" />
        <button class="foto-close" @click="fotoModal = null">✕</button>
      </div>

    </Teleport>
  </div>
</template>

<style scoped>
.evento-page { padding-bottom: 3rem; }

.back-link {
  display: inline-block;
  color: var(--color-muted, #64748b);
  font-size: .9rem;
  text-decoration: none;
  margin-bottom: .5rem;
}
.back-link:hover { color: var(--color-primary, #22c55e); }

.dash-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 1.5rem;
}
.dash-head h1 { font-size: 1.75rem; margin: 0 0 .25rem; }

/* ── Stats ──────────────────────────────────────────────────────────── */
.stats-row {
  display: flex;
  gap: .75rem;
  margin-bottom: 1.25rem;
  flex-wrap: wrap;
}
.stat-pill {
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: var(--radius-md, 12px);
  padding: .6rem 1rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 72px;
}
.stat-pill.stat-pendente { background: #fffbeb; border-color: #fcd34d; }
.stat-pill.stat-aprovado { background: #f0fdf4; border-color: #86efac; }
.stat-pill.stat-nft      { background: #f5f3ff; border-color: #a78bfa; }
.stat-num { font-size: 1.4rem; font-weight: 800; color: var(--color-primary, #22c55e); }
.stat-lbl { font-size: .75rem; color: var(--color-muted, #64748b); font-weight: 500; }

/* ── Resultado Banner ────────────────────────────────────────────────── */
.resultado-banner {
  margin-bottom: 1.5rem;
  padding: 1.25rem;
  border-left: 4px solid #22c55e;
  animation: slideDown .3s ease;
}
@keyframes slideDown { from { opacity:0; transform:translateY(-8px); } to { opacity:1; transform:none; } }

.resultado-header {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1rem;
}
.resultado-icon { font-size: 1.8rem; flex-shrink: 0; }
.resultado-header > div { flex: 1; }
.badge-erro { background: #fef2f2; color: #dc2626; border-radius: 999px; padding: .15rem .6rem; font-size: .8rem; font-weight: 600; margin-left: .5rem; }

.resultado-lista {
  display: flex;
  flex-direction: column;
  gap: .4rem;
  max-height: 240px;
  overflow-y: auto;
}
.resultado-item {
  display: flex;
  align-items: center;
  gap: .75rem;
  padding: .5rem .75rem;
  border-radius: 8px;
  font-size: .88rem;
}
.resultado-ok  { background: #f0fdf4; }
.resultado-err { background: #fef2f2; }
.resultado-check { font-size: 1rem; flex-shrink: 0; }
.resultado-info { display: flex; flex-direction: column; gap: .1rem; }
.resultado-token { font-size: .8rem; color: #6d28d9; font-weight: 600; }
.resultado-erro-msg { font-size: .8rem; color: #dc2626; }

/* ── Filtros ─────────────────────────────────────────────────────────── */
.filter-bar {
  display: flex;
  gap: .4rem;
  flex-wrap: wrap;
  margin-bottom: 1.25rem;
}
.filter-btn {
  padding: .45rem .9rem;
  border: 1.5px solid var(--color-border, #e2e8f0);
  border-radius: 999px;
  background: var(--color-surface, #fff);
  color: var(--color-muted, #64748b);
  font-size: .85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all .15s;
  display: flex;
  align-items: center;
  gap: .3rem;
}
.filter-btn:hover { border-color: var(--color-primary, #22c55e); color: var(--color-primary, #22c55e); }
.filter-btn.active { background: var(--color-primary, #22c55e); border-color: var(--color-primary, #22c55e); color: #fff; }
.filter-count { background: rgba(0,0,0,.1); border-radius: 999px; padding: 0 .4em; font-size: .75em; }
.filter-btn.active .filter-count { background: rgba(255,255,255,.25); }

/* ── Skeleton ────────────────────────────────────────────────────────── */
.skeleton-list { display: flex; flex-direction: column; gap: .6rem; }
.skeleton { height: 60px; border-radius: var(--radius-sm, 8px); background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%); background-size: 200% 100%; animation: shimmer 1.4s infinite; }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

/* ── Empty ────────────────────────────────────────────────────────────── */
.empty-card { display: flex; align-items: flex-start; gap: 1rem; border: 1px dashed var(--color-border, #e2e8f0); border-radius: var(--radius-md, 12px); padding: 2rem; color: var(--color-muted, #64748b); }
.empty-icon { font-size: 2rem; flex-shrink: 0; }
.empty-card strong { display: block; color: var(--color-text, #1a1a1a); margin-bottom: .3rem; }

/* ── Tabela ───────────────────────────────────────────────────────────── */
.table-wrap { padding: 0; overflow: hidden; }
.tbl { width: 100%; border-collapse: collapse; }
.tbl th, .tbl td { text-align: left; padding: .8rem 1rem; border-bottom: 1px solid var(--color-border, #e2e8f0); }
.tbl th { background: #f6faf7; font-size: .82rem; color: var(--color-muted, #64748b); font-weight: 700; text-transform: uppercase; letter-spacing: .03em; }
.tbl tr:last-child td { border-bottom: none; }
.tbl tr.row-pendente { background: #fffef0; }
.tbl tr.row-nft { background: #faf5ff; }

.avatar { width: 34px; height: 34px; border-radius: 50%; background: var(--color-primary, #22c55e); color: #fff; display: grid; place-items: center; font-weight: 700; font-size: .9rem; flex-shrink: 0; }
.avatar-sm { width: 26px; height: 26px; font-size: .78rem; }
.thumb { width: 52px; height: 52px; object-fit: cover; border-radius: var(--radius-sm, 8px); cursor: pointer; transition: opacity .15s; }
.thumb:hover { opacity: .85; }
.motivo-text { font-size: .78rem; color: #dc2626; margin-top: .2rem; }

/* ── NFT badge na tabela ─────────────────────────────────────────────── */
.nft-badge { display: flex; align-items: center; gap: .4rem; }
.nft-icon { font-size: 1.1rem; }
.nft-token { display: block; font-size: .8rem; font-weight: 700; color: #6d28d9; }
.nft-hash { font-size: .72rem; color: #9333ea; }
.badge-pendente-nft { font-size: .78rem; color: #d97706; font-weight: 600; }
.link-btn { background: none; border: none; cursor: pointer; color: inherit; font-size: inherit; padding: 0; text-decoration: underline dotted; }
.link-btn:hover { opacity: .75; }

/* ── Ações ────────────────────────────────────────────────────────────── */
.action-btns { display: flex; gap: .35rem; flex-wrap: wrap; }
.btn-sm { padding: .35rem .7rem; font-size: .82rem; border-radius: var(--radius-sm, 8px); font-weight: 600; cursor: pointer; border: none; display: flex; align-items: center; gap: .3rem; }
.btn-success { background: #dcfce7; color: #166534; }
.btn-success:hover:not(:disabled) { background: #bbf7d0; }
.btn-danger  { background: #fef2f2; color: #dc2626; border: 1px solid #fca5a5; }
.btn-danger:hover { background: #fee2e2; }

/* ── Modal base ───────────────────────────────────────────────────────── */
.backdrop { position: fixed; inset: 0; background: rgba(0,0,0,.55); display: grid; place-items: center; padding: 1rem; z-index: 80; backdrop-filter: blur(2px); }
.modal { max-width: 520px; width: 100%; max-height: 90vh; overflow-y: auto; }
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.modal-header h3 { margin: 0; font-size: 1.1rem; }
.btn-close { background: none; border: none; font-size: 1.1rem; cursor: pointer; color: var(--color-muted, #64748b); padding: .25rem; }
.btn-close:hover { color: var(--color-text, #1a1a1a); }
.input { width: 100%; padding: .65rem .9rem; border: 1.5px solid var(--color-border, #e2e8f0); border-radius: var(--radius-sm, 8px); font-size: .95rem; background: var(--color-bg, #fff); color: var(--color-text, #1a1a1a); outline: none; box-sizing: border-box; }
.input:focus { border-color: var(--color-primary, #22c55e); box-shadow: 0 0 0 3px rgba(34,197,94,.15); }
textarea.input { resize: vertical; min-height: 80px; }
.char-count { font-size: .8rem; color: var(--color-muted, #64748b); text-align: right; margin: .3rem 0 0; }
.text-warn { color: #dc2626; }
.modal-footer { display: flex; justify-content: flex-end; gap: .5rem; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--color-border, #e2e8f0); }

/* ── Modal: Confirmação de emissão ───────────────────────────────────── */
.confirm-body { display: flex; flex-direction: column; gap: 1rem; }
.confirm-info-row { display: flex; align-items: flex-start; gap: 1rem; }
.confirm-icon { font-size: 2rem; flex-shrink: 0; }
.confirm-warning {
  background: #fffbeb;
  border: 1px solid #fcd34d;
  border-radius: 8px;
  padding: .75rem 1rem;
  font-size: .88rem;
  color: #92400e;
}
.confirm-lista { border: 1px solid var(--color-border, #e2e8f0); border-radius: 8px; overflow: hidden; }
.confirm-lista-title { margin: 0; padding: .6rem 1rem; background: #f8fafc; font-size: .82rem; font-weight: 700; color: var(--color-muted, #64748b); border-bottom: 1px solid var(--color-border, #e2e8f0); }
.confirm-item { display: flex; align-items: center; gap: .75rem; padding: .55rem 1rem; font-size: .9rem; border-bottom: 1px solid var(--color-border, #e2e8f0); }
.confirm-item:last-child { border-bottom: none; }

/* ── btn-danger-solid ───────────────────────────────────────────────── */
.btn-danger-solid { background: #dc2626; color: #fff; border: none; border-radius: var(--radius-sm, 8px); padding: .6rem 1.1rem; font-weight: 700; cursor: pointer; font-size: .9rem; }
.btn-danger-solid:hover:not(:disabled) { background: #b91c1c; }
.btn-danger-solid:disabled { opacity: .5; cursor: not-allowed; }

/* ── Foto ampliada ───────────────────────────────────────────────────── */
.foto-backdrop { background: rgba(0,0,0,.85); }
.foto-ampliada { max-width: 90vw; max-height: 85vh; border-radius: var(--radius-md, 12px); object-fit: contain; }
.foto-close { position: fixed; top: 1.25rem; right: 1.25rem; background: rgba(255,255,255,.15); border: none; color: #fff; font-size: 1.5rem; width: 40px; height: 40px; border-radius: 50%; cursor: pointer; display: grid; place-items: center; }
.foto-close:hover { background: rgba(255,255,255,.3); }

/* ── Spinner ────────────────────────────────────────────────────────── */
.spinner-sm { display: inline-block; width: 13px; height: 13px; border: 2px solid rgba(0,0,0,.2); border-top-color: currentColor; border-radius: 50%; animation: spin .7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
