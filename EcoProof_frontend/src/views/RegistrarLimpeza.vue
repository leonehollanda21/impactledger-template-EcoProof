<script setup>
import { ref } from 'vue'
import { apiFormData } from '../utils/api'
import { formatTipoAcao } from '../utils/format'
import ImageUpload from '../components/ImageUpload.vue'
import { useToast } from '../composables/useToast'

const toast = useToast()
const step = ref(1)
const tipo = ref('')
const fotoAntes = ref(null); const fotoDepois = ref(null)
const submitting = ref(false); const resultado = ref(null); const loadingMsg = ref('')

const tipos = [
  { id:'lixo_rua', label:'Lixo na rua', emoji:'🗑️' },
  { id:'praia', label:'Praia', emoji:'🏖️' },
  { id:'corrego', label:'Córrego', emoji:'🏞️' },
  { id:'queimada', label:'Queimada', emoji:'🔥' },
  { id:'outro', label:'Outro', emoji:'🌱' },
]

function next() {
  if (step.value === 1 && !tipo.value) return toast.warn('Selecione um tipo de ação.')
  if (step.value === 2 && (!fotoAntes.value || !fotoDepois.value)) return toast.warn('Envie as duas fotos.')
  step.value++
  if (step.value === 3) submit()
}

async function submit() {
  submitting.value = true; resultado.value = null
  const fd = new FormData()
  fd.append('tipo_acao', tipo.value)
  fd.append('foto_antes', fotoAntes.value)
  fd.append('foto_depois', fotoDepois.value)
  const msgs = ['Analisando imagens com IA…', 'Verificando limpeza…', 'Gerando NFT…']
  let i = 0; loadingMsg.value = msgs[0]
  const t = setInterval(() => { i = (i+1) % msgs.length; loadingMsg.value = msgs[i] }, 1400)
  try {
    const r = await apiFormData('/limpezas', fd)
    resultado.value = r
  } catch (e) { toast.error(e.message); step.value = 2 }
  finally { clearInterval(t); submitting.value = false }
}

function reiniciar() { step.value = 1; tipo.value=''; fotoAntes.value=null; fotoDepois.value=null; resultado.value=null }
</script>
<template>
  <div class="container">
      <div style="margin-bottom: 1rem;">
      <RouterLink to="/app/dashboard" style="color: var(--color-muted); text-decoration: none; font-weight: 600; display: inline-flex; align-items: center; gap: 0.3rem;">
        <span>←</span> Voltar ao Dashboard
      </RouterLink>
    </div>
    <h1>Registrar limpeza</h1>
    <ol class="stepper">
      <li :class="{active: step>=1, done: step>1}">1. Tipo</li>
      <li :class="{active: step>=2, done: step>2}">2. Fotos</li>
      <li :class="{active: step>=3}">3. Resultado</li>
    </ol>

    <section v-if="step===1" class="card">
      <h3>O que você limpou?</h3>
      <div class="tipo-grid">
        <button v-for="t in tipos" :key="t.id" class="tipo-card" :class="{sel: tipo===t.id}" @click="tipo=t.id">
          <span class="emoji">{{ t.emoji }}</span>{{ t.label }}
        </button>
      </div>
      <button class="btn btn-primary" @click="next">Continuar</button>
    </section>

    <section v-else-if="step===2" class="card">
      <h3>Envie as duas fotos</h3>
      <div class="grid two">
        <ImageUpload label="Foto ANTES" @update:file="fotoAntes = $event" />
        <ImageUpload label="Foto DEPOIS" @update:file="fotoDepois = $event" />
      </div>
      <div style="margin-top:1rem; display:flex; gap:.5rem">
        <button class="btn btn-ghost" @click="step=1">Voltar</button>
        <button class="btn btn-primary" @click="next">Enviar</button>
      </div>
    </section>

    <section v-else class="card">
      <div v-if="submitting" class="loading">
        <div class="ring"></div>
        <p>{{ loadingMsg }}</p>
      </div>
      <div v-else-if="resultado">
        <template v-if="resultado.status === 'aprovado' || resultado.nft">
          <div class="confetti"></div>
          <h2>✨ Aprovado!</h2>
          <p>Sua ação <strong>{{ formatTipoAcao(resultado.tipo_acao) }}</strong> foi validada com score {{ Math.round((resultado.score || 0)*100) }}%.</p>
          <p class="muted" v-if="resultado.motivo">{{ resultado.motivo }}</p>
          <div style="display:flex; gap:.5rem; margin-top:1rem">
            <RouterLink to="/app/carteira" class="btn btn-primary">Ver minha carteira</RouterLink>
            <button class="btn btn-ghost" @click="reiniciar">Registrar outra</button>
          </div>
        </template>
        <template v-else>
          <h2>Não foi dessa vez</h2>
          <p class="muted">{{ resultado.motivo || 'A IA não conseguiu validar a limpeza.' }}</p>
          <button class="btn btn-primary" @click="reiniciar">Tentar novamente</button>
        </template>
      </div>
    </section>
  </div>
</template>
<style scoped>
.stepper { list-style:none; padding:0; display:flex; gap:.5rem; margin: 1rem 0 1.5rem; flex-wrap:wrap; }
.stepper li { padding:.4rem .9rem; border-radius:999px; background:#eef3ee; color: var(--color-muted); font-weight:600; font-size:.9rem; }
.stepper li.active { background: var(--color-primary); color:#fff; }
.stepper li.done { background: var(--color-tertiary); color:#fff; }
.tipo-grid { display:grid; grid-template-columns: repeat(auto-fill,minmax(140px,1fr)); gap:.8rem; margin:1rem 0 1.5rem; }
.tipo-card { background:#fff; border:2px solid var(--color-border); border-radius: var(--radius-md); padding:1rem; cursor:pointer; display:flex; flex-direction:column; align-items:center; gap:.4rem; font-weight:600; color: var(--color-primary); transition: all .15s; }
.tipo-card:hover { border-color: var(--color-tertiary); }
.tipo-card.sel { border-color: var(--color-primary); background: #f1f8f3; }
.emoji { font-size:2rem; }
.two { grid-template-columns: 1fr 1fr; }
@media (max-width:768px){ .two { grid-template-columns:1fr; } }
.loading { text-align:center; padding:3rem 1rem; }
.ring { width:60px; height:60px; border:6px solid #eef3ee; border-top-color: var(--color-tertiary); border-radius:50%; animation: sp 1s linear infinite; margin:0 auto 1rem; }
.confetti { position:fixed; inset:0; pointer-events:none; background:
  radial-gradient(circle at 10% 20%, var(--color-accent) 2px, transparent 3px),
  radial-gradient(circle at 80% 30%, var(--color-tertiary) 2px, transparent 3px),
  radial-gradient(circle at 30% 70%, var(--color-secondary) 2px, transparent 3px),
  radial-gradient(circle at 70% 80%, var(--color-accent) 2px, transparent 3px);
  background-size: 100% 100%; animation: rain 2s linear; opacity:.8; }
@keyframes rain { from { background-position: 0 -100vh, 0 -100vh, 0 -100vh, 0 -100vh; } to { background-position: 0 100vh, 0 100vh, 0 100vh, 0 100vh; } }
@keyframes sp { to { transform: rotate(360deg); } }
</style>
