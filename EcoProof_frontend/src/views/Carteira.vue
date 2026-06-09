<script setup>
import { onMounted, ref, computed } from 'vue'
import { useNFTStore } from '../stores/nfts'
import { useAuthStore } from '../stores/auth'
import NFTCard from '../components/NFTCard.vue'
import { formatDate, formatTipoAcao, formatPoints, truncateHash } from '../utils/format'

const nfts = useNFTStore(); const auth = useAuthStore()
const selected = ref(null)
onMounted(() => nfts.fetchMeusNFTs())
const total = computed(() => auth.user?.pontos || 0)
</script>
<template>
  <div class="container">
    <header class="head">
      <div>
        <h1>Minha Carteira</h1>
        <p class="muted">{{ nfts.items.length }} NFTs · {{ formatPoints(total) }} pontos</p>
      </div>
    </header>

    <div v-if="nfts.loading" class="grid grid-cards">
      <div class="skeleton" style="height:280px" v-for="i in 4" :key="i"></div>
    </div>
    <div v-else-if="!nfts.items.length" class="card muted">Você ainda não possui NFTs. Registre uma limpeza!</div>
    <div v-else class="grid grid-cards">
      <NFTCard v-for="n in nfts.items" :key="n.id" :nft="n" @click="selected = n" />
    </div>

    <Teleport to="body">
      <div v-if="selected" class="backdrop" @click.self="selected=null">
        <div class="modal card">
          <button class="close" @click="selected=null">✕</button>
          <img :src="selected.foto_url" />
          <h2>{{ formatTipoAcao(selected.tipo_acao) }}</h2>
          <p class="muted">{{ formatDate(selected.created_at) }}</p>
          <dl>
            <dt>Token ID</dt><dd>#{{ selected.token_id }}</dd>
            <dt>Assinado por</dt><dd>{{ selected.assinado_por }}</dd>
            <dt>Tx Hash</dt><dd><a :href="`https://etherscan.io/tx/${selected.tx_hash}`" target="_blank">{{ truncateHash(selected.tx_hash) }} ↗</a></dd>
            <dt>Metadata</dt><dd><a :href="selected.metadata_url" target="_blank">Ver JSON ↗</a></dd>
          </dl>
        </div>
      </div>
    </Teleport>
  </div>
</template>
<style scoped>
.head { margin-bottom:1.5rem; }
.backdrop { position:fixed; inset:0; background:rgba(0,0,0,.5); display:grid; place-items:center; padding:1rem; z-index:80; }
.modal { max-width:520px; width:100%; max-height:90vh; overflow:auto; position:relative; }
.modal img { width:100%; border-radius: var(--radius-sm); margin-bottom:1rem; }
.close { position:absolute; top:.6rem; right:.8rem; background:#fff; border:1px solid var(--color-border); border-radius:50%; width:32px; height:32px; cursor:pointer; }
dl { display:grid; grid-template-columns: auto 1fr; gap:.4rem .8rem; }
dt { color: var(--color-muted); }
dd { margin:0; }
</style>
