<script setup>
import { onMounted, ref, watchEffect } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../utils/api'
import { formatDate, formatTipoAcao, truncateHash } from '../utils/format'

const route = useRoute()
const nft = ref(null); const metadata = ref(null); const verification = ref(null)
const loading = ref(true); const err = ref('')
const verifying = ref(false)

onMounted(async () => {
  try {
    nft.value = await api.get(`/nfts/${route.params.token_id}`)
    try { metadata.value = await api.get(`/nfts/${route.params.token_id}/metadata.json`) } catch {}
  } catch (e) { err.value = e.message } finally { loading.value = false }
})

async function verifyOnchain() {
  verifying.value = true
  try {
    verification.value = await api.get(`/nfts/${route.params.token_id}/verify`)
  } catch (e) {
    verification.value = { message: 'Erro na verificação: ' + e.message }
  } finally {
    verifying.value = false
  }
}

watchEffect(() => {
  if (!nft.value) return
  document.title = `NFT #${nft.value.token_id} — EcoProof`
  setMeta('og:title', `EcoProof NFT #${nft.value.token_id}`)
  setMeta('og:description', `Ação verificada: ${formatTipoAcao(nft.value.tipo_acao)}`)
  setMeta('og:image', nft.value.foto_url)
  setMeta('og:type', 'article')
})
function setMeta(prop, content) {
  let el = document.querySelector(`meta[property="${prop}"]`)
  if (!el) { el = document.createElement('meta'); el.setAttribute('property', prop); document.head.appendChild(el) }
  el.setAttribute('content', content || '')
}

function getExplorerUrl(txHash) {
  // Determina explorer baseado na chain (default: Polygonscan Amoy testnet)
  return `https://amoy.polygonscan.com/tx/${txHash}`
}
</script>
<template>
  <div class="container">
    <div v-if="loading" class="skeleton" style="height:400px"></div>
    <div v-else-if="err" class="card muted">{{ err }}</div>
    <article v-else class="card nft-detail">

      <!-- Imagem -->
      <div class="nft-image-wrap">
        <img :src="nft.foto_url" :alt="metadata?.name || 'EcoProof NFT'" />
        <div class="soulbound-overlay">
          <span class="soulbound-badge">🔒 Soulbound — Intransferível</span>
        </div>
      </div>

      <!-- Info -->
      <div class="nft-info">
        <!-- Badge assinado por -->
        <div class="badges-row">
          <span class="badge soulbound">🔒 EIP-5192</span>
          <span v-if="nft.assinado_por==='instituto'" class="badge instituto">
            🏛️ Assinado por Instituto
          </span>
          <span v-else class="badge ecoproof">✅ EcoProof</span>
        </div>

        <h1>{{ metadata?.name || `NFT #${nft.token_id}` }}</h1>
        <p class="muted tipo-data">
          {{ formatTipoAcao(nft.tipo_acao) }} · {{ formatDate(nft.created_at) }}
        </p>

        <p v-if="metadata?.description" class="description">{{ metadata.description }}</p>

        <!-- Atributos -->
        <div v-if="metadata?.attributes" class="attributes">
          <div v-for="a in metadata.attributes" :key="a.trait_type" class="attr-item">
            <span class="attr-label">{{ a.trait_type }}</span>
            <span class="attr-value">{{ a.value }}</span>
          </div>
        </div>

        <!-- Blockchain Info -->
        <div class="chain-info">
          <h3>📋 Informações Blockchain</h3>
          <div class="chain-row">
            <span class="chain-label">Token ID:</span>
            <span class="chain-value mono">#{{ nft.token_id }}</span>
          </div>
          <div class="chain-row">
            <span class="chain-label">Tx Hash:</span>
            <span class="chain-value mono">{{ truncateHash(nft.tx_hash) }}</span>
          </div>
          <div class="chain-row">
            <span class="chain-label">Status:</span>
            <span class="chain-value">
              <span class="locked-badge">🔒 Locked (Soulbound)</span>
            </span>
          </div>
          <div class="chain-row">
            <span class="chain-label">Rede:</span>
            <span class="chain-value">Polygon (EIP-5192)</span>
          </div>
        </div>

        <!-- Actions -->
        <div class="actions">
          <a
            class="btn btn-primary"
            :href="getExplorerUrl(nft.tx_hash)"
            target="_blank"
            rel="noopener"
          >
            Verificar no Polygonscan ↗
          </a>
          <button
            class="btn btn-ghost"
            :disabled="verifying"
            @click="verifyOnchain"
          >
            <span v-if="verifying" class="spinner-sm"></span>
            {{ verifying ? 'Verificando…' : '🔍 Verificar On-Chain' }}
          </button>
        </div>

        <!-- Resultado da verificação -->
        <div v-if="verification" class="verify-result" :class="{ success: verification.proof_registered_onchain }">
          <p>{{ verification.message }}</p>
          <p v-if="verification.explorer_url" class="muted" style="font-size:.85rem; margin-top:.4rem">
            <a :href="verification.explorer_url" target="_blank" rel="noopener">
              Ver transação no explorer ↗
            </a>
          </p>
        </div>

      </div>
    </article>
  </div>
</template>
<style scoped>
.nft-detail {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
  align-items: start;
  padding: 0;
  overflow: hidden;
}

/* Imagem */
.nft-image-wrap {
  position: relative;
  overflow: hidden;
}
.nft-image-wrap img {
  width: 100%;
  display: block;
  border-radius: var(--radius-md, 12px) 0 0 var(--radius-md, 12px);
}
.soulbound-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: .75rem 1rem;
  background: linear-gradient(transparent, rgba(0,0,0,.7));
}
.soulbound-badge {
  color: #fff;
  font-size: .85rem;
  font-weight: 700;
  text-shadow: 0 1px 3px rgba(0,0,0,.5);
}

/* Info */
.nft-info {
  padding: 1.75rem 1.75rem 1.75rem 0;
}

.badges-row {
  display: flex;
  gap: .5rem;
  flex-wrap: wrap;
  margin-bottom: .75rem;
}
.badge {
  font-size: .75rem;
  font-weight: 700;
  padding: .3rem .7rem;
  border-radius: 999px;
}
.badge.soulbound {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
}
.badge.instituto {
  background: var(--color-accent, #86efac);
  color: #1a2620;
}
.badge.ecoproof {
  background: var(--color-tertiary, #4ade80);
  color: #fff;
}

h1 {
  font-size: 1.5rem;
  margin: 0 0 .3rem;
}
.tipo-data {
  font-size: .9rem;
  margin-bottom: 1rem;
}
.description {
  font-size: .92rem;
  line-height: 1.7;
  color: var(--color-text, #1a1a1a);
  margin-bottom: 1.25rem;
}

/* Atributos */
.attributes {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: .5rem;
  margin-bottom: 1.5rem;
}
.attr-item {
  background: var(--color-surface, #f8faf8);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: var(--radius-sm, 8px);
  padding: .6rem .8rem;
}
.attr-label {
  display: block;
  font-size: .7rem;
  font-weight: 600;
  color: var(--color-muted, #64748b);
  text-transform: uppercase;
  letter-spacing: .04em;
  margin-bottom: .15rem;
}
.attr-value {
  font-size: .88rem;
  font-weight: 600;
  color: var(--color-text, #1a1a1a);
}

/* Chain info */
.chain-info {
  background: #f0f4f8;
  border-radius: var(--radius-sm, 8px);
  padding: 1rem;
  margin-bottom: 1.25rem;
}
.chain-info h3 {
  font-size: .95rem;
  margin: 0 0 .6rem;
}
.chain-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: .3rem 0;
  border-bottom: 1px solid rgba(0,0,0,.06);
}
.chain-row:last-child { border-bottom: none; }
.chain-label {
  font-size: .82rem;
  color: var(--color-muted, #64748b);
  font-weight: 500;
}
.chain-value {
  font-size: .85rem;
  font-weight: 600;
}
.mono { font-family: ui-monospace, monospace; font-size: .82rem; }
.locked-badge {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
  font-size: .72rem;
  padding: .2rem .5rem;
  border-radius: 999px;
  font-weight: 700;
}

/* Actions */
.actions {
  display: flex;
  gap: .75rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}

/* Verify result */
.verify-result {
  padding: .9rem 1rem;
  border-radius: var(--radius-sm, 8px);
  font-size: .88rem;
  background: #fef3c7;
  border-left: 3px solid #f59e0b;
}
.verify-result.success {
  background: #ecfdf5;
  border-left-color: #10b981;
}
.verify-result p { margin: 0; }
.verify-result a {
  color: var(--color-primary, #22c55e);
  text-decoration: underline;
}

/* Spinner inline */
.spinner-sm {
  display: inline-block;
  width: 14px; height: 14px;
  border: 2px solid rgba(0,0,0,.2);
  border-top-color: var(--color-primary, #22c55e);
  border-radius: 50%;
  animation: spin .7s linear infinite;
  margin-right: 4px;
  vertical-align: middle;
}
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width:768px) {
  .nft-detail { grid-template-columns: 1fr; }
  .nft-image-wrap img { border-radius: var(--radius-md, 12px) var(--radius-md, 12px) 0 0; }
  .nft-info { padding: 1.25rem; }
  .attributes { grid-template-columns: 1fr; }
}
</style>
