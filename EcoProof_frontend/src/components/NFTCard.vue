<script setup>
import { formatDate, formatTipoAcao } from '../utils/format'
defineProps({ nft: Object })
defineEmits(['click'])
</script>
<template>
  <article class="nft-card" @click="$emit('click', nft)">
    <div class="img" :style="{ backgroundImage: `url(${nft.foto_url})` }">
      <div class="card-badges">
        <span class="seal" :class="nft.assinado_por">
          {{ nft.assinado_por === 'instituto' ? '🏛️ Instituto' : '✅ EcoProof' }}
        </span>
        <span class="soulbound-tag">🔒 Soulbound</span>
      </div>
    </div>
    <div class="body">
      <div class="tipo">{{ formatTipoAcao(nft.tipo_acao) }}</div>
      <div class="muted date-row">
        <span>{{ formatDate(nft.created_at) }}</span>
        <span class="token-id">#{{ nft.token_id }}</span>
      </div>
      <slot />
    </div>
  </article>
</template>
<style scoped>
.nft-card {
  background: #fff;
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-card);
  cursor: pointer;
  transition: transform .15s, box-shadow .15s;
}
.nft-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-lg);
}
.img {
  height: 180px;
  background-size: cover;
  background-position: center;
  background-color: #dde6df;
  position: relative;
}
.card-badges {
  position: absolute;
  top: .6rem;
  left: .6rem;
  right: .6rem;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
.seal {
  padding: .3rem .6rem;
  border-radius: 999px;
  font-size: .72rem;
  font-weight: 700;
  backdrop-filter: blur(4px);
}
.seal.ecoproof { background: rgba(74, 222, 128, .9); color: #fff; }
.seal.instituto { background: rgba(134, 239, 172, .9); color: #1a2620; }
.soulbound-tag {
  padding: .25rem .5rem;
  border-radius: 999px;
  font-size: .65rem;
  font-weight: 700;
  background: linear-gradient(135deg, rgba(102, 126, 234, .9), rgba(118, 75, 162, .9));
  color: #fff;
  backdrop-filter: blur(4px);
}
.body { padding: .9rem 1rem 1rem; }
.tipo { font-weight: 700; color: var(--color-primary); margin-bottom: .2rem; }
.date-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.token-id {
  font-family: ui-monospace, monospace;
  font-size: .75rem;
  color: var(--color-muted, #64748b);
  font-weight: 600;
}
</style>
