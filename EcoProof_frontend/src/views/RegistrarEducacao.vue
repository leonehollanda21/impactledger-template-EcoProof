<script setup>
import { ref } from 'vue'
import { apiFormData } from '../utils/api.js'
import { formatTipoAcao } from '../utils/format.js'
import ImageUpload from '../components/ImageUpload.vue'
import { useToast } from '../composables/useToast.js'

const toast = useToast()
const step = ref(1)
const tipo = ref('')
const fotoEvento = ref(null)
const numParticipantes = ref('')
const submitting = ref(false); const resultado = ref(null); const loadingMsg = ref('')

const tipos = [
  { id:'palestra', label:'Palestra em Escola', emoji:'🏫' },
  { id:'oficina', label:'Oficina de Reciclagem', emoji:'♻️' },
  { id:'roda_conversa', label:'Roda de Conversa', emoji:'🗣️' },
  { id:'mutirao_educativo', label:'Mutirão Educativo', emoji:'🤝' },
  { id:'outro', label:'Outro', emoji:'🌱' },
]

function next() {
  if (step.value === 1 && !tipo.value) return toast.warn('Selecione um tipo de ação educativa.')
  if (step.value === 2 && (!fotoEvento.value || !numParticipantes.value)) return toast.warn('Envie a foto do evento e informe o número de participantes.')
  if (step.value === 2 && numParticipantes.value < 1) return toast.warn('O número de participantes deve ser maior que zero.')
  
  step.value++
  if (step.value === 3) submit()
}

async function submit() {
  submitting.value = true; resultado.value = null
  const fd = new FormData()
  fd.append('tipo_acao', tipo.value)
  fd.append('foto', fotoEvento.value)
  fd.append('num_pessoas', numParticipantes.value)
  
  const msgs = ['Registrando evento…', 'Aguardando validação…', 'Gerando NFT de Impacto…']
  let i = 0; loadingMsg.value = msgs[0]
  const t = setInterval(() => { i = (i+1) % msgs.length; loadingMsg.value = msgs[i] }, 1400)
  
  try {
    const r = await apiFormData('/educacao', fd) 
    
    resultado.value = r
  } catch (e) { 
    toast.error(e.message); step.value = 2 
  }
  finally { clearInterval(t); submitting.value = false }
}

function reiniciar() { step.value = 1; tipo.value=''; fotoEvento.value=null; numParticipantes.value=''; resultado.value=null }
</script>

<template>
  <div class="container">
    <div style="margin-bottom: 1rem;">
      <RouterLink to="/app/dashboard" style="color: var(--color-muted); text-decoration: none; font-weight: 600; display: inline-flex; align-items: center; gap: 0.3rem;">
        <span>←</span> Voltar ao Dashboard
      </RouterLink>
    </div>

    <h1>Educação Ambiental</h1>
    <ol class="stepper">
      <li :class="{active: step>=1, done: step>1}">1. Tipo</li>
      <li :class="{active: step>=2, done: step>2}">2. Impacto</li>
      <li :class="{active: step>=3}">3. Resultado</li>
    </ol>

    <section v-if="step===1" class="card">
      <h3>Qual ação educativa você realizou?</h3>
      <div class="tipo-grid">
        <button v-for="t in tipos" :key="t.id" class="tipo-card" :class="{sel: tipo===t.id}" @click="tipo=t.id">
          <span class="emoji">{{ t.emoji }}</span>{{ t.label }}
        </button>
      </div>
      <button class="btn btn-primary" @click="next">Continuar</button>
    </section>

    <section v-else-if="step===2" class="card">
      <h3>Comprove o evento e o impacto</h3>
      
      <div class="impacto-container">
        <div class="input-group">
          <label for="participantes">Número de Pessoas Impactadas:</label>
          <input 
            id="participantes" 
            type="number" 
            v-model="numParticipantes" 
            min="1" 
            placeholder="Ex: 45" 
            class="input-number"
          >
        </div>
        
        <ImageUpload label="Foto do Evento (Público)" @update:file="fotoEvento = $event" />
      </div>

      <div style="margin-top:1.5rem; display:flex; gap:.5rem">
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
          <h2>✨ Impacto Registrado!</h2>
          <p>Sua ação foi validada com sucesso.</p>
          
          <div class="nft-highlight">
            <span class="medal">🏅</span>
            <strong>Educador Ambiental</strong>
            <span>{{ numParticipantes }} pessoas impactadas</span>
          </div>

          <p class="muted" v-if="resultado.motivo">{{ resultado.motivo }}</p>
          <div style="display:flex; gap:.5rem; margin-top:1rem">
            <RouterLink to="/app/carteira" class="btn btn-primary">Ver minha carteira</RouterLink>
            <button class="btn btn-ghost" @click="reiniciar">Registrar outra</button>
          </div>
        </template>
        <template v-else>
          <h2>Pendente de Validação</h2>
          <p class="muted">{{ resultado.motivo || 'Aguardando aprovação do Instituto ou Administrador.' }}</p>
          <button class="btn btn-primary" @click="reiniciar">Voltar</button>
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
.tipo-card { background:#fff; border:2px solid var(--color-border); border-radius: var(--radius-md); padding:1rem; cursor:pointer; display:flex; flex-direction:column; align-items:center; gap:.4rem; font-weight:600; color: var(--color-primary); transition: all .15s; text-align: center;}
.tipo-card:hover { border-color: var(--color-tertiary); }
.tipo-card.sel { border-color: var(--color-primary); background: #f1f8f3; }
.emoji { font-size:2rem; }

.impacto-container { display: flex; flex-direction: column; gap: 1.5rem; }
.input-group { display: flex; flex-direction: column; gap: 0.5rem; font-weight: 600; color: var(--color-primary); }
.input-number { padding: 0.8rem; border: 2px solid var(--color-border); border-radius: var(--radius-md); font-size: 1.1rem; max-width: 200px; outline: none; transition: border-color 0.2s;}
.input-number:focus { border-color: var(--color-primary); }
.nft-highlight { background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%); border: 2px solid #ffd700; border-radius: var(--radius-md); padding: 1.5rem; margin: 1.5rem 0; display: flex; flex-direction: column; align-items: center; gap: 0.5rem; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
.nft-highlight .medal { font-size: 3rem; }
.nft-highlight strong { font-size: 1.2rem; color: #333; }

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