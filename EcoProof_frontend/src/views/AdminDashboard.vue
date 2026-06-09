<script setup>
import { onMounted, ref, computed } from 'vue'
import { api, apiFormData } from '../utils/api'
import { formatDate, formatPoints } from '../utils/format'
import { useToast } from '../composables/useToast'

const toast = useToast()

// ── Estado ─────────────────────────────────────────────────────────────────
const stats       = ref({})
const loading     = ref(true)
const activeTab   = ref('institutos')

// Institutos
const institutos      = ref([])
const instPage        = ref(1)
const instTotal       = ref(0)
const instFilter      = ref(null) // null=todos, false=pendentes, true=verificados
const instLoading     = ref(false)

// Denúncias
const denuncias       = ref([])
const denPage         = ref(1)
const denTotal        = ref(0)
const denStatus       = ref(null)
const denLoading      = ref(false)
const resolucaoFoto   = ref({}) // { [id]: File }
const improcMotivo    = ref({}) // { [id]: string }

// Educação
const educacoes       = ref([])
const eduPage         = ref(1)
const eduTotal        = ref(0)
const eduStatus       = ref(null)
const eduLoading      = ref(false)
const eduMotivo       = ref({}) // { [id]: string }

// NFTs
const nfts            = ref([])
const nftPage         = ref(1)
const nftTotal        = ref(0)
const nftLoading      = ref(false)

// Validações
const validacoes      = ref([])
const valLoading      = ref(false)

// ── Helpers ────────────────────────────────────────────────────────────────
const tabLabels = {
  institutos: 'Institutos',
  denuncias:  'Denúncias',
  educacao:   'Educação',
  nfts:       'NFTs',
  validacoes: 'Validações',
}

const statusDenLabel = {
  registrada:    '🟡 Registrada',
  em_analise:    '🔵 Em análise',
  resolvida:     '🟢 Resolvida',
  improcedente:  '🔴 Improcedente',
}

const statusEduLabel = {
  pendente:  '🟡 Pendente',
  aprovada:  '🟢 Aprovada',
  rejeitada: '🔴 Rejeitada',
}

const tipoNftLabel = {
  limpeza:  '🧹 Limpeza',
  mutirao:  '🤝 Mutirão',
  educacao: '📚 Educação',
  outro:    '🏅 Outro',
}

// ── Carregamento ───────────────────────────────────────────────────────────
async function loadDashboard() {
  loading.value = true
  try {
    stats.value = await api.get('/admin/dashboard')
  } catch (e) { toast.error('Erro ao carregar dashboard: ' + e.message) }
  finally { loading.value = false }
}

async function loadInstitutos() {
  instLoading.value = true
  try {
    const params = new URLSearchParams({ page: instPage.value, page_size: 20 })
    if (instFilter.value !== null) params.set('verified', instFilter.value)
    const r = await api.get(`/admin/institutos?${params}`)
    institutos.value = r.items || []
    instTotal.value  = r.total || 0
  } catch (e) { toast.error(e.message) }
  finally { instLoading.value = false }
}

async function loadDenuncias() {
  denLoading.value = true
  try {
    const params = new URLSearchParams({ page: denPage.value, page_size: 20 })
    if (denStatus.value) params.set('status', denStatus.value)
    const r = await api.get(`/admin/denuncias?${params}`)
    denuncias.value = r.items || []
    denTotal.value  = r.total || 0
  } catch (e) { toast.error(e.message) }
  finally { denLoading.value = false }
}

async function loadEducacoes() {
  eduLoading.value = true
  try {
    const params = new URLSearchParams({ page: eduPage.value, page_size: 20 })
    if (eduStatus.value) params.set('status', eduStatus.value)
    const r = await api.get(`/admin/educacoes?${params}`)
    educacoes.value = r.items || []
    eduTotal.value  = r.total || 0
  } catch (e) { toast.error(e.message) }
  finally { eduLoading.value = false }
}

async function loadNFTs() {
  nftLoading.value = true
  try {
    const r = await api.get(`/admin/nfts?page=${nftPage.value}&page_size=20`)
    nfts.value    = r.items || []
    nftTotal.value = r.total || 0
  } catch (e) { toast.error(e.message) }
  finally { nftLoading.value = false }
}

async function loadValidacoes() {
  valLoading.value = true
  try {
    const r = await api.get('/admin/validacoes?page_size=30')
    validacoes.value = r.items || []
  } catch (e) { toast.error(e.message) }
  finally { valLoading.value = false }
}

function switchTab(tab) {
  activeTab.value = tab
  if (tab === 'institutos' && !institutos.value.length) loadInstitutos()
  if (tab === 'denuncias'  && !denuncias.value.length)  loadDenuncias()
  if (tab === 'educacao'   && !educacoes.value.length)  loadEducacoes()
  if (tab === 'nfts'       && !nfts.value.length)       loadNFTs()
  if (tab === 'validacoes' && !validacoes.value.length) loadValidacoes()
}

onMounted(async () => {
  await loadDashboard()
  await loadInstitutos()
})

// ── Ações — Institutos ─────────────────────────────────────────────────────
async function aprovar(i) {
  try {
    await api.patch(`/admin/institutos/${i.id}/aprovar`)
    toast.success(`Instituto "${i.nome}" aprovado!`)
    loadInstitutos()
    loadDashboard()
  } catch (e) { toast.error(e.message) }
}
async function suspender(i) {
  if (!confirm(`Suspender "${i.nome}"?`)) return
  try {
    await api.patch(`/admin/institutos/${i.id}/suspender`)
    toast.success(`Instituto "${i.nome}" suspenso.`)
    loadInstitutos()
    loadDashboard()
  } catch (e) { toast.error(e.message) }
}

// ── Ações — Denúncias ──────────────────────────────────────────────────────
async function emAnalise(d) {
  try {
    await api.patch(`/admin/denuncias/${d.id}/em-analise`)
    toast.success('Denúncia marcada como em análise.')
    loadDenuncias()
  } catch (e) { toast.error(e.message) }
}

async function resolverDenuncia(d) {
  const file = resolucaoFoto.value[d.id]
  if (!file) return toast.error('Selecione a foto de resolução primeiro.')
  try {
    const fd = new FormData()
    fd.append('foto_resolucao', file)
    await apiFormData(`/admin/denuncias/${d.id}/resolver`, fd)
    toast.success('Denúncia resolvida! NFT emitido.')
    resolucaoFoto.value[d.id] = null
    loadDenuncias()
    loadNFTs()
    loadDashboard()
  } catch (e) { toast.error(e.message) }
}

async function improcedente(d) {
  const motivo = improcMotivo.value[d.id]
  if (!motivo || motivo.length < 10) return toast.error('Informe um motivo com pelo menos 10 caracteres.')
  try {
    await api.patch(`/admin/denuncias/${d.id}/improcedente`, { motivo })
    toast.success('Denúncia marcada como improcedente.')
    improcMotivo.value[d.id] = ''
    loadDenuncias()
  } catch (e) { toast.error(e.message) }
}

// ── Ações — Educação ───────────────────────────────────────────────────────
async function aprovarEducacao(a) {
  try {
    await api.patch(`/admin/educacoes/${a.id}/validar`, { aprovado: true })
    toast.success('Ação educativa aprovada! NFT emitido.')
    loadEducacoes()
    loadNFTs()
    loadDashboard()
  } catch (e) { toast.error(e.message) }
}

async function rejeitarEducacao(a) {
  const motivo = eduMotivo.value[a.id]
  if (!motivo || motivo.length < 5) return toast.error('Informe um motivo com pelo menos 5 caracteres.')
  try {
    await api.patch(`/admin/educacoes/${a.id}/validar`, { aprovado: false, motivo_rejeicao: motivo })
    toast.success('Ação educativa rejeitada.')
    eduMotivo.value[a.id] = ''
    loadEducacoes()
  } catch (e) { toast.error(e.message) }
}
</script>

<template>
  <div class="admin-wrap">
    <!-- ── Header ───────────────────────────────────────────────────── -->
    <div class="admin-header">
      <div class="admin-header__text">
        <h1>⚙️ Painel Administrativo</h1>
        <p class="muted">Gerencie institutos, denúncias, educação e NFTs da plataforma.</p>
      </div>
    </div>

    <!-- ── Stats ────────────────────────────────────────────────────── -->
    <div class="stats-grid" v-if="!loading">
      <div class="stat-card">
        <span class="stat-icon">👥</span>
        <div>
          <div class="stat-value">{{ formatPoints(stats.total_usuarios) }}</div>
          <div class="stat-label">Usuários</div>
        </div>
      </div>
      <div class="stat-card">
        <span class="stat-icon">🏛️</span>
        <div>
          <div class="stat-value">{{ formatPoints(stats.total_institutos) }}</div>
          <div class="stat-label">Institutos</div>
        </div>
      </div>
      <div class="stat-card stat-card--warn">
        <span class="stat-icon">⏳</span>
        <div>
          <div class="stat-value">{{ formatPoints(stats.total_institutos_pendentes) }}</div>
          <div class="stat-label">Pendentes aprovação</div>
        </div>
      </div>
      <div class="stat-card">
        <span class="stat-icon">🧹</span>
        <div>
          <div class="stat-value">{{ formatPoints(stats.total_limpezas) }}</div>
          <div class="stat-label">Limpezas</div>
        </div>
      </div>
      <div class="stat-card">
        <span class="stat-icon">🚨</span>
        <div>
          <div class="stat-value">{{ formatPoints(stats.total_denuncias) }}</div>
          <div class="stat-label">Denúncias</div>
        </div>
      </div>
      <div class="stat-card">
        <span class="stat-icon">📚</span>
        <div>
          <div class="stat-value">{{ formatPoints(stats.total_educacoes) }}</div>
          <div class="stat-label">Ações Educativas</div>
        </div>
      </div>
      <div class="stat-card stat-card--green">
        <span class="stat-icon">🏅</span>
        <div>
          <div class="stat-value">{{ formatPoints(stats.total_nfts) }}</div>
          <div class="stat-label">NFTs emitidos</div>
        </div>
      </div>
      <div class="stat-card stat-card--green">
        <span class="stat-icon">⭐</span>
        <div>
          <div class="stat-value">{{ formatPoints(stats.total_pontos_distribuidos) }}</div>
          <div class="stat-label">Pontos distribuídos</div>
        </div>
      </div>
    </div>
    <div v-else class="loading-pulse">Carregando estatísticas...</div>

    <!-- ── Tabs ──────────────────────────────────────────────────────── -->
    <div class="tab-bar">
      <button
        v-for="(label, key) in tabLabels"
        :key="key"
        class="tab-btn"
        :class="{ active: activeTab === key }"
        @click="switchTab(key)"
      >{{ label }}</button>
    </div>

    <!-- ══════════════════════════════════════════════════════════════ -->
    <!-- TAB: INSTITUTOS                                              -->
    <!-- ══════════════════════════════════════════════════════════════ -->
    <section v-if="activeTab === 'institutos'" class="tab-panel">
      <div class="panel-toolbar">
        <h2>Institutos</h2>
        <div class="filter-btns">
          <button :class="['filter-btn', instFilter === null && 'active']" @click="instFilter = null; instPage = 1; loadInstitutos()">Todos</button>
          <button :class="['filter-btn', instFilter === false && 'active']" @click="instFilter = false; instPage = 1; loadInstitutos()">Pendentes</button>
          <button :class="['filter-btn', instFilter === true && 'active']" @click="instFilter = true; instPage = 1; loadInstitutos()">Verificados</button>
        </div>
      </div>

      <div v-if="instLoading" class="loading-pulse">Carregando institutos...</div>
      <div v-else-if="!institutos.length" class="empty-state">Nenhum instituto encontrado.</div>
      <div v-else class="card-list">
        <div v-for="i in institutos" :key="i.id" class="item-card">
          <div class="item-card__info">
            <div class="item-card__title">{{ i.nome }}</div>
            <div class="item-card__sub muted">{{ i.email }} · CNPJ: {{ i.cnpj }}</div>
            <div class="item-card__meta">
              <span class="badge" :class="i.verified ? 'badge--green' : 'badge--warn'">
                {{ i.verified ? '✅ Verificado' : '⏳ Pendente' }}
              </span>
              <span class="muted">{{ i.total_eventos }} eventos · {{ i.total_nfts_emitidos }} NFTs</span>
              <span class="muted">Cadastro: {{ formatDate(i.created_at) }}</span>
            </div>
          </div>
          <div class="item-card__actions">
            <button v-if="!i.verified" class="btn btn-primary btn-sm" @click="aprovar(i)">✅ Aprovar</button>
            <button v-if="i.verified" class="btn btn-danger btn-sm" @click="suspender(i)">🚫 Suspender</button>
            <button v-if="!i.verified" class="btn btn-ghost btn-sm" @click="suspender(i)">Suspender</button>
          </div>
        </div>
      </div>

      <div class="pagination" v-if="instTotal > 20">
        <button class="btn btn-ghost btn-sm" :disabled="instPage === 1" @click="instPage--; loadInstitutos()">← Anterior</button>
        <span class="muted">Página {{ instPage }}</span>
        <button class="btn btn-ghost btn-sm" :disabled="instPage * 20 >= instTotal" @click="instPage++; loadInstitutos()">Próxima →</button>
      </div>
    </section>

    <!-- ══════════════════════════════════════════════════════════════ -->
    <!-- TAB: DENÚNCIAS                                               -->
    <!-- ══════════════════════════════════════════════════════════════ -->
    <section v-if="activeTab === 'denuncias'" class="tab-panel">
      <div class="panel-toolbar">
        <h2>Denúncias Ambientais</h2>
        <div class="filter-btns">
          <button :class="['filter-btn', !denStatus && 'active']" @click="denStatus = null; denPage = 1; loadDenuncias()">Todas</button>
          <button :class="['filter-btn', denStatus === 'registrada' && 'active']" @click="denStatus = 'registrada'; denPage = 1; loadDenuncias()">Novas</button>
          <button :class="['filter-btn', denStatus === 'em_analise' && 'active']" @click="denStatus = 'em_analise'; denPage = 1; loadDenuncias()">Em análise</button>
          <button :class="['filter-btn', denStatus === 'resolvida' && 'active']" @click="denStatus = 'resolvida'; denPage = 1; loadDenuncias()">Resolvidas</button>
          <button :class="['filter-btn', denStatus === 'improcedente' && 'active']" @click="denStatus = 'improcedente'; denPage = 1; loadDenuncias()">Improcedentes</button>
        </div>
      </div>

      <div v-if="denLoading" class="loading-pulse">Carregando denúncias...</div>
      <div v-else-if="!denuncias.length" class="empty-state">Nenhuma denúncia encontrada.</div>
      <div v-else class="card-list">
        <div v-for="d in denuncias" :key="d.id" class="item-card item-card--denuncia">
          <div class="denuncia-main">
            <img :src="d.foto_problema_url" :alt="d.tipo_problema" class="thumb" />
            <div class="item-card__info">
              <div class="item-card__title">{{ d.tipo_problema?.replace('_', ' ').toUpperCase() }}</div>
              <div class="item-card__sub muted">Cidadão: {{ d.cidadao_nome || d.cidadao_id }}</div>
              <div class="item-card__meta">
                <span class="badge" :class="{
                  'badge--warn': d.status === 'registrada',
                  'badge--blue': d.status === 'em_analise',
                  'badge--green': d.status === 'resolvida',
                  'badge--red': d.status === 'improcedente',
                }">{{ statusDenLabel[d.status] }}</span>
                <span class="muted">{{ formatDate(d.created_at) }}</span>
              </div>
            </div>
          </div>

          <!-- Ações somente se não finalizada -->
          <div v-if="d.status !== 'resolvida' && d.status !== 'improcedente'" class="denuncia-actions">
            <!-- Botão: Em análise (só se registrada) -->
            <button v-if="d.status === 'registrada'" class="btn btn-ghost btn-sm" @click="emAnalise(d)">🔍 Iniciar análise</button>

            <!-- Resolver: upload foto + botão -->
            <div class="resolve-block">
              <label class="upload-label">
                <input type="file" accept="image/*" @change="e => resolucaoFoto[d.id] = e.target.files[0]" />
                {{ resolucaoFoto[d.id] ? '📷 ' + resolucaoFoto[d.id].name : '📷 Foto de resolução' }}
              </label>
              <button class="btn btn-primary btn-sm" @click="resolverDenuncia(d)">✅ Resolver + emitir NFT</button>
            </div>

            <!-- Improcedente: motivo + botão -->
            <div class="improcedente-block">
              <input
                class="input-sm"
                v-model="improcMotivo[d.id]"
                placeholder="Motivo da improcedência (mín. 10 chars)..."
              />
              <button class="btn btn-danger btn-sm" @click="improcedente(d)">🚫 Improcedente</button>
            </div>
          </div>
        </div>
      </div>

      <div class="pagination" v-if="denTotal > 20">
        <button class="btn btn-ghost btn-sm" :disabled="denPage === 1" @click="denPage--; loadDenuncias()">← Anterior</button>
        <span class="muted">Página {{ denPage }} · {{ denTotal }} total</span>
        <button class="btn btn-ghost btn-sm" :disabled="denPage * 20 >= denTotal" @click="denPage++; loadDenuncias()">Próxima →</button>
      </div>
    </section>

    <!-- ══════════════════════════════════════════════════════════════ -->
    <!-- TAB: EDUCAÇÃO                                                -->
    <!-- ══════════════════════════════════════════════════════════════ -->
    <section v-if="activeTab === 'educacao'" class="tab-panel">
      <div class="panel-toolbar">
        <h2>Ações Educativas</h2>
        <div class="filter-btns">
          <button :class="['filter-btn', !eduStatus && 'active']" @click="eduStatus = null; eduPage = 1; loadEducacoes()">Todas</button>
          <button :class="['filter-btn', eduStatus === 'pendente' && 'active']" @click="eduStatus = 'pendente'; eduPage = 1; loadEducacoes()">Pendentes</button>
          <button :class="['filter-btn', eduStatus === 'aprovada' && 'active']" @click="eduStatus = 'aprovada'; eduPage = 1; loadEducacoes()">Aprovadas</button>
          <button :class="['filter-btn', eduStatus === 'rejeitada' && 'active']" @click="eduStatus = 'rejeitada'; eduPage = 1; loadEducacoes()">Rejeitadas</button>
        </div>
      </div>

      <div v-if="eduLoading" class="loading-pulse">Carregando ações educativas...</div>
      <div v-else-if="!educacoes.length" class="empty-state">Nenhuma ação educativa encontrada.</div>
      <div v-else class="card-list">
        <div v-for="a in educacoes" :key="a.id" class="item-card item-card--edu">
          <div class="edu-main">
            <img :src="a.foto_url" :alt="a.tipo_acao" class="thumb" />
            <div class="item-card__info">
              <div class="item-card__title">{{ a.tipo_acao?.replace('_', ' ').toUpperCase() }}</div>
              <div class="item-card__sub muted">Por: {{ a.autor_nome || a.autor_id }} ({{ a.autor_tipo }})</div>
              <div class="item-card__sub muted" v-if="a.descricao">{{ a.descricao }}</div>
              <div class="item-card__meta">
                <span class="badge" :class="{
                  'badge--warn': a.status === 'pendente',
                  'badge--green': a.status === 'aprovada',
                  'badge--red': a.status === 'rejeitada',
                }">{{ statusEduLabel[a.status] }}</span>
                <span class="badge badge--blue">👥 {{ a.num_pessoas }} pessoas</span>
                <span class="muted">{{ formatDate(a.created_at) }}</span>
              </div>
            </div>
          </div>

          <!-- Ações somente para pendentes -->
          <div v-if="a.status === 'pendente'" class="edu-actions">
            <button class="btn btn-primary btn-sm" @click="aprovarEducacao(a)">✅ Aprovar + emitir NFT</button>
            <div class="rejeitar-block">
              <input
                class="input-sm"
                v-model="eduMotivo[a.id]"
                placeholder="Motivo de rejeição (mín. 5 chars)..."
              />
              <button class="btn btn-danger btn-sm" @click="rejeitarEducacao(a)">❌ Rejeitar</button>
            </div>
          </div>
        </div>
      </div>

      <div class="pagination" v-if="eduTotal > 20">
        <button class="btn btn-ghost btn-sm" :disabled="eduPage === 1" @click="eduPage--; loadEducacoes()">← Anterior</button>
        <span class="muted">Página {{ eduPage }} · {{ eduTotal }} total</span>
        <button class="btn btn-ghost btn-sm" :disabled="eduPage * 20 >= eduTotal" @click="eduPage++; loadEducacoes()">Próxima →</button>
      </div>
    </section>

    <!-- ══════════════════════════════════════════════════════════════ -->
    <!-- TAB: NFTs                                                    -->
    <!-- ══════════════════════════════════════════════════════════════ -->
    <section v-if="activeTab === 'nfts'" class="tab-panel">
      <div class="panel-toolbar">
        <h2>NFTs Emitidos</h2>
        <span class="muted">{{ formatPoints(nftTotal) }} total</span>
      </div>

      <div v-if="nftLoading" class="loading-pulse">Carregando NFTs...</div>
      <div v-else-if="!nfts.length" class="empty-state">Nenhum NFT emitido ainda.</div>
      <div v-else class="nft-table-wrap card">
        <table class="tbl">
          <thead>
            <tr>
              <th>Token ID</th>
              <th>Tipo</th>
              <th>Cidadão</th>
              <th>Wallet</th>
              <th>Data</th>
              <th>TX</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="n in nfts" :key="n.id">
              <td><code class="code-sm">{{ n.token_id }}</code></td>
              <td><span class="badge badge--blue">{{ tipoNftLabel[n.tipo] || n.tipo }}</span></td>
              <td>{{ n.cidadao_nome || '—' }}</td>
              <td class="muted font-mono">{{ n.cidadao_wallet ? n.cidadao_wallet.slice(0, 10) + '...' : '—' }}</td>
              <td class="muted">{{ formatDate(n.created_at) }}</td>
              <td>
                <a :href="`https://amoy.polygonscan.com/tx/${n.tx_hash}`" target="_blank" class="tx-link">
                  {{ n.tx_hash.slice(0, 10) }}...
                </a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="pagination" v-if="nftTotal > 20">
        <button class="btn btn-ghost btn-sm" :disabled="nftPage === 1" @click="nftPage--; loadNFTs()">← Anterior</button>
        <span class="muted">Página {{ nftPage }} · {{ nftTotal }} total</span>
        <button class="btn btn-ghost btn-sm" :disabled="nftPage * 20 >= nftTotal" @click="nftPage++; loadNFTs()">Próxima →</button>
      </div>
    </section>

    <!-- ══════════════════════════════════════════════════════════════ -->
    <!-- TAB: VALIDAÇÕES                                              -->
    <!-- ══════════════════════════════════════════════════════════════ -->
    <section v-if="activeTab === 'validacoes'" class="tab-panel">
      <div class="panel-toolbar">
        <h2>Histórico de Validações (Limpeza / Mutirão)</h2>
      </div>

      <div v-if="valLoading" class="loading-pulse">Carregando validações...</div>
      <div v-else-if="!validacoes.length" class="empty-state">Sem validações registradas.</div>
      <div v-else class="card">
        <table class="tbl">
          <thead>
            <tr>
              <th>Data</th>
              <th>Tipo</th>
              <th>Cidadão</th>
              <th>Resultado</th>
              <th>Score</th>
              <th>Motivo</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="v in validacoes" :key="v.id">
              <td class="muted">{{ formatDate(v.created_at) }}</td>
              <td>{{ v.tipo === 'limpeza' ? '🧹 Limpeza' : '🤝 Mutirão' }}</td>
              <td>{{ v.cidadao_nome }}</td>
              <td>
                <span class="badge" :class="v.resultado ? 'badge--green' : 'badge--red'">
                  {{ v.resultado ? '✅ Aprovada' : '❌ Reprovada' }}
                </span>
              </td>
              <td>
                <div class="score-bar">
                  <div class="score-fill"
                    :style="{
                      width: ((v.score||0)*100)+'%',
                      background: (v.score||0) > .7 ? 'var(--color-success)' : 'var(--color-warn)'
                    }"
                  ></div>
                </div>
                <span class="muted score-pct">{{ Math.round((v.score||0)*100) }}%</span>
              </td>
              <td class="muted">{{ v.motivo || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<style scoped>
/* ── Layout ──────────────────────────────────────────────────────────────── */
.admin-wrap {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1.5rem 1rem 3rem;
}

/* ── Header ──────────────────────────────────────────────────────────────── */
.admin-header {
  margin-bottom: 1.8rem;
}
.admin-header h1 {
  font-size: 1.8rem;
  font-weight: 700;
  margin: 0 0 .3rem;
}

/* ── Stats ───────────────────────────────────────────────────────────────── */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: .8rem;
  margin-bottom: 2rem;
}
.stat-card {
  display: flex;
  align-items: center;
  gap: .8rem;
  padding: 1rem 1.2rem;
  border-radius: var(--radius);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}
.stat-card--warn { border-color: var(--color-warn); }
.stat-card--green { border-color: var(--color-success); }
.stat-icon { font-size: 1.6rem; }
.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-primary);
  font-family: var(--font-display);
}
.stat-label { font-size: .78rem; color: var(--color-muted); }

/* ── Tabs ────────────────────────────────────────────────────────────────── */
.tab-bar {
  display: flex;
  gap: .4rem;
  flex-wrap: wrap;
  margin-bottom: 1.5rem;
  border-bottom: 2px solid var(--color-border);
  padding-bottom: .5rem;
}
.tab-btn {
  padding: .5rem 1.1rem;
  border-radius: var(--radius) var(--radius) 0 0;
  border: 1px solid transparent;
  background: transparent;
  color: var(--color-muted);
  cursor: pointer;
  font-size: .9rem;
  transition: all .2s;
}
.tab-btn:hover { color: var(--color-text); background: var(--color-surface); }
.tab-btn.active {
  color: var(--color-primary);
  background: var(--color-surface);
  border-color: var(--color-border);
  border-bottom-color: var(--color-surface);
  font-weight: 600;
}

/* ── Panel Toolbar ───────────────────────────────────────────────────────── */
.panel-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: .8rem;
  margin-bottom: 1rem;
}
.panel-toolbar h2 { margin: 0; font-size: 1.2rem; }

/* ── Filter buttons ──────────────────────────────────────────────────────── */
.filter-btns { display: flex; gap: .4rem; flex-wrap: wrap; }
.filter-btn {
  padding: .3rem .8rem;
  border-radius: 999px;
  border: 1px solid var(--color-border);
  background: transparent;
  color: var(--color-muted);
  font-size: .82rem;
  cursor: pointer;
  transition: all .15s;
}
.filter-btn:hover, .filter-btn.active {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

/* ── Card list ───────────────────────────────────────────────────────────── */
.card-list { display: flex; flex-direction: column; gap: .8rem; }
.item-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 1rem 1.2rem;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  flex-wrap: wrap;
  transition: border-color .2s;
}
.item-card:hover { border-color: var(--color-primary); }
.item-card__info { flex: 1; display: flex; flex-direction: column; gap: .25rem; }
.item-card__title { font-weight: 600; font-size: 1rem; }
.item-card__sub { font-size: .85rem; }
.item-card__meta { display: flex; gap: .6rem; flex-wrap: wrap; align-items: center; margin-top: .3rem; }
.item-card__actions { display: flex; gap: .5rem; flex-wrap: wrap; align-items: flex-start; }

/* ── Denuncia card ───────────────────────────────────────────────────────── */
.denuncia-main, .edu-main {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  flex: 1;
  flex-wrap: wrap;
}
.thumb {
  width: 72px;
  height: 72px;
  object-fit: cover;
  border-radius: .5rem;
  flex-shrink: 0;
  border: 1px solid var(--color-border);
}
.item-card--denuncia, .item-card--edu { flex-direction: column; }
.denuncia-actions, .edu-actions {
  display: flex;
  flex-wrap: wrap;
  gap: .7rem;
  align-items: flex-start;
  width: 100%;
  padding-top: .7rem;
  border-top: 1px solid var(--color-border);
}
.resolve-block, .improcedente-block, .rejeitar-block {
  display: flex;
  gap: .5rem;
  align-items: center;
  flex-wrap: wrap;
}
.upload-label {
  display: inline-flex;
  align-items: center;
  gap: .4rem;
  padding: .3rem .8rem;
  background: var(--color-border);
  border-radius: .5rem;
  font-size: .82rem;
  cursor: pointer;
  transition: background .15s;
}
.upload-label:hover { background: var(--color-primary-light, #c7f0c7); }
.upload-label input { display: none; }
.input-sm {
  padding: .3rem .7rem;
  border: 1px solid var(--color-border);
  border-radius: .5rem;
  font-size: .82rem;
  background: var(--color-bg);
  color: var(--color-text);
  min-width: 200px;
}
.input-sm:focus { outline: none; border-color: var(--color-primary); }

/* ── NFT Table ───────────────────────────────────────────────────────────── */
.nft-table-wrap { overflow-x: auto; }
.tbl { width: 100%; border-collapse: collapse; }
.tbl th, .tbl td {
  padding: .65rem 1rem;
  text-align: left;
  border-bottom: 1px solid var(--color-border);
  font-size: .88rem;
}
.tbl th { color: var(--color-muted); font-weight: 500; font-size: .82rem; }
.code-sm { font-family: monospace; font-size: .8rem; background: var(--color-border); padding: .1rem .4rem; border-radius: .3rem; }
.tx-link { color: var(--color-primary); text-decoration: none; font-family: monospace; font-size: .82rem; }
.tx-link:hover { text-decoration: underline; }
.font-mono { font-family: monospace; font-size: .82rem; }

/* ── Score bar ───────────────────────────────────────────────────────────── */
.score-bar { width: 100px; height: 6px; background: var(--color-border); border-radius: 999px; overflow: hidden; display: inline-block; vertical-align: middle; margin-right: .4rem; }
.score-fill { height: 100%; border-radius: 999px; }
.score-pct { font-size: .78rem; }

/* ── Badges ──────────────────────────────────────────────────────────────── */
.badge {
  display: inline-flex;
  align-items: center;
  padding: .18rem .65rem;
  border-radius: 999px;
  font-size: .78rem;
  font-weight: 500;
}
.badge--green { background: #dcfce7; color: #166534; }
.badge--warn  { background: #fef9c3; color: #854d0e; }
.badge--red   { background: #fee2e2; color: #991b1b; }
.badge--blue  { background: #dbeafe; color: #1e40af; }

/* ── Pagination ──────────────────────────────────────────────────────────── */
.pagination { display: flex; align-items: center; justify-content: center; gap: 1rem; margin-top: 1rem; }

/* ── Misc ────────────────────────────────────────────────────────────────── */
.empty-state {
  text-align: center;
  padding: 2.5rem;
  color: var(--color-muted);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
}
.loading-pulse {
  color: var(--color-muted);
  font-style: italic;
  padding: 1rem;
  text-align: center;
}
.btn-sm { padding: .3rem .85rem; font-size: .83rem; }
.btn-danger {
  background: #ef4444;
  color: #fff;
  border: none;
}
.btn-danger:hover { background: #dc2626; }
.tab-panel { animation: fadeIn .2s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
</style>
