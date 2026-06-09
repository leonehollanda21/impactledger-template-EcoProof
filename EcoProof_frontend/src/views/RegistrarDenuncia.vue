<script setup>
import { ref } from 'vue'
import { apiFormData } from '../utils/api.js'
import ImageUpload from '../components/ImageUpload.vue'
import { useToast } from '../composables/useToast.js'

const toast = useToast()
const step = ref(1)
const tipo = ref('')
const localizacao = ref('')
const descricao = ref('')
const fotoFile = ref(null)

const submitting = ref(false)
const resultado = ref(null)
const loadingMsg = ref('')

const tipos = [
  { id:'descarte_ilegal', label:'Descarte Irregular', emoji:'🗑️' },
  { id:'esgoto', label:'Esgoto / Poluição', emoji:'☣️' },
  { id:'queimada', label:'Foco de Queimada', emoji:'🔥' },
  { id:'desmatamento', label:'Desmatamento', emoji:'🪓' },
  { id:'poluicao_agua', label:'Poluição da Água', emoji:'💧' },
  { id:'poluicao_ar', label:'Poluição do Ar', emoji:'🌫️' },
  { id:'outro', label:'Outro Problema', emoji:'⚠️' },
]

function next() {
  if (step.value === 1 && !tipo.value) return toast.warn('Selecione o tipo de ocorrência.')
  if (step.value === 2 && (!localizacao.value || !descricao.value || !fotoFile.value)) {
    return toast.warn('Preencha a localização, a descrição e envie a foto do problema.')
  }
  
  step.value++
  if (step.value === 3) submit()
}

async function submit() {
  submitting.value = true; resultado.value = null
  const fd = new FormData()
  fd.append('tipo_problema', tipo.value)
  fd.append('descricao', descricao.value ? `[${localizacao.value}] ${descricao.value}` : localizacao.value)
  fd.append('foto_problema', fotoFile.value)
  
  const msgs = ['Registrando evidências na blockchain…', 'Criptografando localização…', 'Notificando órgão ambiental competente…']
  let i = 0; loadingMsg.value = msgs[0]
  const t = setInterval(() => { i = (i+1) % msgs.length; loadingMsg.value = msgs[i] }, 1400)
  
  try {
    const r = await apiFormData('/denuncias', fd) 
    resultado.value = r
  } catch (e) { 
    toast.error(e.message)
    step.value = 2
  } finally { 
    clearInterval(t)
    submitting.value = false 
  }
}

function reiniciar() { 
  step.value = 1; tipo.value = ''; localizacao.value = ''; descricao.value = ''; fotoFile.value = null; resultado.value = null 
}
</script>

<template>
  <div class="container">
    <div style="margin-bottom: 1rem;">
      <RouterLink to="/app/dashboard" style="color: var(--color-muted); text-decoration: none; font-weight: 600; display: inline-flex; align-items: center; gap: 0.3rem;">
        <span>←</span> Voltar ao Dashboard
      </RouterLink>
    </div>

    <h1>Denúncia Ambiental</h1>
    <ol class="stepper">
      <li :class="{active: step>=1, done: step>1}">1. Tipo</li>
      <li :class="{active: step>=2, done: step>2}">2. Evidência</li>
      <li :class="{active: step>=3}">3. Status</li>
    </ol>

    <section v-if="step===1" class="card">
      <h3>Qual o problema ambiental encontrado?</h3>
      <div class="tipo-grid">
        <button v-for="t in tipos" :key="t.id" class="tipo-card" :class="{sel: tipo===t.id}" @click="tipo=t.id">
          <span class="emoji">{{ t.emoji }}</span>{{ t.label }}
        </button>
      </div>
      <button class="btn btn-primary" style="background: #d97706; border-color: #d97706;" @click="next">Continuar</button>
    </section>

    <section v-else-if="step===2" class="card">
      <h3>Registre a evidência do problema</h3>
      
      <div class="form-container">
        <div class="input-group">
          <label for="localizacao">Localização Exata:</label>
          <input 
            id="localizacao" 
            type="text" 
            v-model="localizacao" 
            placeholder="Ex: Rua das Flores, 123 - Terreno baldio" 
            class="input-text"
            autocomplete="off"
          >
        </div>

        <div class="input-group">
          <label for="descricao">Descrição:</label>
          <textarea 
            id="descricao" 
            v-model="descricao" 
            rows="3" 
            placeholder="Descreva o que está acontecendo no local..." 
            class="input-textarea"
          ></textarea>
        </div>
        
        <ImageUpload label="Foto do Problema (Antes)" @update:file="fotoFile = $event" />
      </div>

      <div style="margin-top:1.5rem; display:flex; gap:.5rem">
        <button class="btn btn-ghost" @click="step=1">Voltar</button>
        <button class="btn btn-primary" style="background: #d97706; border-color: #d97706;" @click="next">Enviar</button>
      </div>
    </section>

    <section v-else class="card">
      <div v-if="submitting" class="loading">
        <div class="ring"></div>
        <p>{{ loadingMsg }}</p>
      </div>
      <div v-else-if="resultado">
        <div class="confetti"></div>
        <h2>🚨 Denúncia Protocolada!</h2>
        <p>Sua ocorrência foi registrada com sucesso e encaminhada ao órgão competente.</p>
        
        <div class="nft-highlight">
          <span class="medal">⏳</span>
          <strong style="color: #333;">Aguardando Resolução</strong>
          <span>Quando o órgão resolver o problema, você receberá seu NFT de <strong>Fiscal Ambiental</strong>.</span>
        </div>

        <div style="display:flex; gap:.5rem; margin-top:1rem">
          <RouterLink to="/app/dashboard" class="btn btn-primary" style="background: #d97706; border-color: #d97706;">Voltar ao Dashboard</RouterLink>
          <button class="btn btn-ghost" @click="reiniciar">Fazer outra</button>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
/* Copiado e adaptado estritamente do padrão de Limpeza/Educação */
.stepper { list-style:none; padding:0; display:flex; gap:.5rem; margin: 1rem 0 1.5rem; flex-wrap:wrap; }
.stepper li { padding:.4rem .9rem; border-radius:999px; background:#eef3ee; color: var(--color-muted); font-weight:600; font-size:.9rem; }
.stepper li.active { background: #d97706; color:#fff; }
.stepper li.done { background: #b45309; color:#fff; }

.tipo-grid { display:grid; grid-template-columns: repeat(auto-fill,minmax(140px,1fr)); gap:.8rem; margin:1rem 0 1.5rem; }
.tipo-card { background:#fff; border:2px solid var(--color-border); border-radius: var(--radius-md); padding:1rem; cursor:pointer; display:flex; flex-direction:column; align-items:center; gap:.4rem; font-weight:600; color: #d97706; transition: all .15s; text-align: center;}
.tipo-card:hover { border-color: #b45309; }
.tipo-card.sel { border-color: #d97706; background: #fffbeb; }
.emoji { font-size:2rem; }

.form-container { display: flex; flex-direction: column; gap: 1.5rem; }
.input-group { display: flex; flex-direction: column; gap: 0.5rem; font-weight: 600; color: #d97706; }

/* Inputs idênticos aos padrões do projeto */
.input-text, .input-textarea { 
  padding: 0.8rem; 
  border: 2px solid var(--color-border); 
  border-radius: var(--radius-md); 
  font-size: 1.1rem; 
  outline: none; 
  transition: border-color 0.2s;
  background: #fff;
  font-family: inherit;
  width: 100%;
}
.input-text:focus, .input-textarea:focus { border-color: #d97706; }
.input-textarea { resize: vertical; min-height: 100px; }

.nft-highlight { background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%); border: 2px solid #f59e0b; border-radius: var(--radius-md); padding: 1.5rem; margin: 1.5rem 0; display: flex; flex-direction: column; align-items: center; gap: 0.5rem; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
.nft-highlight .medal { font-size: 3rem; }
.nft-highlight strong { font-size: 1.2rem; }

.loading { text-align:center; padding:3rem 1rem; }
.ring { width:60px; height:60px; border:6px solid #eef3ee; border-top-color: #d97706; border-radius:50%; animation: sp 1s linear infinite; margin:0 auto 1rem; }
.confetti { position:fixed; inset:0; pointer-events:none; background:
  radial-gradient(circle at 10% 20%, #fbbf24 2px, transparent 3px),
  radial-gradient(circle at 80% 30%, #d97706 2px, transparent 3px),
  radial-gradient(circle at 30% 70%, #f59e0b 2px, transparent 3px),
  radial-gradient(circle at 70% 80%, #b45309 2px, transparent 3px);
  background-size: 100% 100%; animation: rain 2s linear; opacity:.8; }
@keyframes rain { from { background-position: 0 -100vh, 0 -100vh, 0 -100vh, 0 -100vh; } to { background-position: 0 100vh, 0 100vh, 0 100vh, 0 100vh; } }
@keyframes sp { to { transform: rotate(360deg); } }
</style>