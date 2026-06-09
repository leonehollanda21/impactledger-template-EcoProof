<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePontosVerdesStore } from '../stores/pontosVerdes'
import { useAuthStore } from '../stores/auth'
import ImageUpload from '../components/ImageUpload.vue'
import { useToast } from '../composables/useToast'

const route = useRoute()
const router = useRouter()
const store = usePontosVerdesStore()
const auth = useAuthStore()
const toast = useToast()

const step = ref(1)
const lat = ref(null)
const lng = ref(null)

const form = ref({
  nome: '',
  categoria: 'praca',
  foto_inicial: null
})

const aceitouTermos = ref(false)
const submitting = ref(false)
const mapRef = ref(null)
let miniMap = null

onMounted(() => {
  // Lê as coordenadas dos query params vindos do mapa geral
  const qLat = parseFloat(route.query.lat)
  const qLng = parseFloat(route.query.lng)

  if (isNaN(qLat) || isNaN(qLng)) {
    toast.error('Localização não selecionada. Retornando ao mapa.')
    router.push('/app/pontos-verdes')
    return
  }

  lat.value = qLat
  lng.value = qLng

  // Se veio pré-preenchido do mapa (ex: ponto sugerido)
  if (route.query.nome) form.value.nome = route.query.nome
  if (route.query.categoria) form.value.categoria = route.query.categoria
})

function initMiniMap() {
  if (!window.L || !mapRef.value) return
  if (miniMap) {
    miniMap.remove()
  }

  miniMap = window.L.map(mapRef.value, {
    zoomControl: false,
    attributionControl: false,
    dragging: false,
    scrollWheelZoom: false,
    doubleClickZoom: false,
    boxZoom: false
  }).setView([lat.value, lng.value], 16)

  window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(miniMap)

  const icon = window.L.divIcon({
    className: 'eco-marker',
    html: '📍',
    iconSize: [30, 30]
  })

  window.L.marker([lat.value, lng.value], { icon }).addTo(miniMap)
}

async function next() {
  if (step.value === 1) {
    if (!form.value.nome.trim()) {
      toast.warn('Dê um nome para a área adotada!')
      return
    }
    step.value = 2
    await nextTick()
    initMiniMap()
  } else if (step.value === 2) {
    step.value = 3
  } else if (step.value === 3) {
    if (!form.value.foto_inicial) {
      toast.warn('Envie a foto inicial da área.')
      return
    }
    step.value = 4
  } else if (step.value === 4) {
    if (!aceitouTermos.value) {
      toast.warn('Você precisa aceitar os termos de adoção.')
      return
    }
    submitAdocao()
  }
}

function prev() {
  if (step.value > 1) {
    step.value--
    if (step.value === 2) {
      nextTick(() => initMiniMap())
    }
  }
}

async function submitAdocao() {
  submitting.value = true
  try {
    const payload = {
      nome: form.value.nome.trim(),
      categoria: form.value.categoria,
      latitude: lat.value,
      longitude: lng.value,
      foto_inicial: form.value.foto_inicial
    }
    
    await store.adotarPonto(payload, auth.user)
    toast.success('Adoção registrada com sucesso! 🌱')
    step.value = 5
  } catch (err) {
    toast.error('Erro ao registrar adoção: ' + err.message)
  } finally {
    submitting.value = false
  }
}

function irParaDashboard() {
  router.push('/app/dashboard')
}

function formatCategoria(cat) {
  const map = {
    praca: 'Praça 🌳',
    canteiro: 'Canteiro 🌱',
    praia: 'Praia 🏖️',
    rio: 'Margem de Rio 🏞️',
    outro: 'Outro 🌿'
  }
  return map[cat] || cat
}
</script>

<template>
  <div class="container adocao-wizard-container">
        <div style="margin-bottom: 1rem;">
      <RouterLink to="/app/dashboard" style="color: var(--color-muted); text-decoration: none; font-weight: 600; display: inline-flex; align-items: center; gap: 0.3rem;">
        <span>←</span> Voltar ao Dashboard
      </RouterLink>
    </div>
    <h1>Adotar Ponto Verde</h1>
    
    <!-- Stepper Indicator -->
    <ol class="stepper">
      <li :class="{ active: step >= 1, done: step > 1 }">1. Detalhes</li>
      <li :class="{ active: step >= 2, done: step > 2 }">2. Localização</li>
      <li :class="{ active: step >= 3, done: step > 3 }">3. Foto Inicial</li>
      <li :class="{ active: step >= 4, done: step > 4 }">4. Termos</li>
      <li :class="{ active: step === 5 }">5. Concluído</li>
    </ol>

    <!-- STEP 1: Informações Básicas -->
    <section v-if="step === 1" class="card fade-in">
      <h3>Dê um nome à área que deseja adotar</h3>
      <p class="muted">Isso aparecerá publicamente no mapa de adoções da cidade.</p>

      <div class="field">
        <label class="label" for="nome-ponto">Nome do Ponto Verde *</label>
        <input 
          id="nome-ponto" 
          type="text" 
          class="input" 
          v-model="form.nome" 
          placeholder="Ex: Canteiro Florido da Av. Brasil, Praça da Paz..."
          maxlength="100" 
        />
      </div>

      <div class="field">
        <label class="label" for="categoria-ponto">Categoria da Área *</label>
        <select id="categoria-ponto" class="input select" v-model="form.categoria">
          <option value="praca">🌳 Praça Pública</option>
          <option value="canteiro">🌱 Canteiro / Rotatória</option>
          <option value="praia">🏖️ Trecho de Praia</option>
          <option value="rio">🏞️ Margem de Rio ou Córrego</option>
          <option value="outro">🌿 Outra área pública</option>
        </select>
      </div>

      <div class="wizard-actions">
        <RouterLink to="/app/pontos-verdes" class="btn btn-ghost">Cancelar</RouterLink>
        <button class="btn btn-primary" @click="next">Continuar</button>
      </div>
    </section>

    <!-- STEP 2: Confirmação de Localização -->
    <section v-else-if="step === 2" class="card fade-in">
      <h3>Confirmar Localização</h3>
      <p class="muted">Confirme visualmente se o marcador está apontando para o local correto.</p>

      <div class="mini-map-wrapper">
        <div ref="mapRef" class="mini-leaflet-map"></div>
      </div>
      
      <div class="coords-display">
        📍 <strong>Latitude:</strong> {{ lat?.toFixed(6) }} &nbsp;|&nbsp; <strong>Longitude:</strong> {{ lng?.toFixed(6) }}
      </div>

      <div class="wizard-actions">
        <button class="btn btn-ghost" @click="prev">Voltar</button>
        <button class="btn btn-primary" @click="next">Confirmar Local</button>
      </div>
    </section>

    <!-- STEP 3: Envio de Foto Inicial -->
    <section v-else-if="step === 3" class="card fade-in">
      <h3>Envie uma foto do local antes da adoção</h3>
      <p class="muted">Esta foto inicial será utilizada para comprovar o antes e depois ao longo dos 3 meses.</p>

      <div class="image-upload-wrapper">
        <ImageUpload label="Foto Inicial do Local" @update:file="form.foto_inicial = $event" />
      </div>

      <div class="wizard-actions">
        <button class="btn btn-ghost" @click="prev">Voltar</button>
        <button class="btn btn-primary" :disabled="!form.foto_inicial" @click="next">Continuar</button>
      </div>
    </section>

    <!-- STEP 4: Termo de Compromisso -->
    <section v-else-if="step === 4" class="card fade-in">
      <h3>Termo de Compromisso e Cuidado</h3>
      
      <div class="termo-box">
        <h4>🌿 Carta de Compromisso do Guardião Ecológico</h4>
        <p>Eu declaro para fins de adoção de área verde pública que me comprometo voluntariamente a cuidar do ponto denominado <strong>{{ form.nome }}</strong> (categoria: {{ formatCategoria(form.categoria) }}), situado sob as coordenadas geográficas <strong>{{ lat?.toFixed(5) }}, {{ lng?.toFixed(5) }}</strong>, sob as seguintes regras:</p>
        <ul>
          <li><strong>Cuidado contínuo:</strong> Promover a limpeza de resíduos, capina de mato invasor e, se cabível, irrigação periódica e plantio de mudas locais.</li>
          <li><strong>Check-ins Mensais:</strong> Enviar 1 foto mensal por 3 meses consecutivos mostrando o ponto em bom estado de conservação.</li>
          <li><strong>Consagração:</strong> Ao fim de 3 meses de validações bem-sucedidas, obterei em definitivo o título e o NFT de Guardião On-chain do local.</li>
          <li><strong>Tolerância de Abandono:</strong> Compreendo que o atraso de check-in mensal por mais de 30 dias mudará o status do ponto para "Alerta" e o mesmo poderá ser adotado por outro cidadão interessado.</li>
        </ul>
      </div>

      <div class="field check-field">
        <input type="checkbox" id="aceito" v-model="aceitouTermos" />
        <label for="aceito" class="label-inline">Eu li e concordo em cuidar desta área com responsabilidade.</label>
      </div>

      <div class="wizard-actions">
        <button class="btn btn-ghost" @click="prev" :disabled="submitting">Voltar</button>
        <button class="btn btn-primary" :disabled="!aceitouTermos || submitting" @click="next">
          <span v-if="submitting" class="spinner-sm"></span>
          {{ submitting ? 'Finalizando...' : 'Concluir Adoção!' }}
        </button>
      </div>
    </section>

    <!-- STEP 5: Sucesso / Concluído -->
    <section v-else class="card text-center fade-in">
      <div class="success-icon">🌱</div>
      <h2>Adoção Realizada com Sucesso!</h2>
      <p>Parabéns, você agora é oficialmente o protetor da área <strong>{{ form.nome }}</strong>!</p>
      <p class="muted text-sm">O primeiro check-in expira em 30 dias. Acompanhe os prazos diretamente no seu painel.</p>

      <div class="success-actions">
        <button class="btn btn-primary" @click="irParaDashboard">Ir para o Dashboard</button>
        <RouterLink to="/app/pontos-verdes" class="btn btn-ghost">Ver Mapa de Pontos</RouterLink>
      </div>
    </section>

  </div>
</template>

<style scoped>
.adocao-wizard-container {
  max-width: 680px;
  padding-bottom: 4rem;
}

.stepper {
  list-style: none;
  padding: 0;
  display: flex;
  gap: 0.4rem;
  margin: 1rem 0 2rem;
  flex-wrap: wrap;
}
.stepper li {
  padding: 0.4rem 0.9rem;
  border-radius: 99px;
  background: var(--color-border, #e2ebe4);
  color: var(--color-muted);
  font-weight: 600;
  font-size: 0.85rem;
}
.stepper li.active {
  background: var(--color-primary);
  color: #fff;
}
.stepper li.done {
  background: var(--color-tertiary);
  color: #fff;
}

.wizard-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
  border-top: 1px solid var(--color-border);
  padding-top: 1rem;
}

/* Mini Mapa */
.mini-map-wrapper {
  height: 280px;
  border-radius: var(--radius-md);
  overflow: hidden;
  margin: 1rem 0;
  border: 1px solid var(--color-border);
}
.mini-leaflet-map {
  width: 100%;
  height: 100%;
}
.coords-display {
  background: var(--color-bg);
  padding: 0.6rem;
  border-radius: var(--radius-sm);
  font-size: 0.88rem;
  font-family: monospace;
  text-align: center;
}

.image-upload-wrapper {
  margin: 1.5rem 0;
}

/* Termo */
.termo-box {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 1.25rem;
  max-height: 250px;
  overflow-y: auto;
  font-size: 0.9rem;
  line-height: 1.5;
  margin: 1rem 0;
}
.termo-box h4 {
  margin-top: 0;
  font-size: 1rem;
}
.termo-box ul {
  padding-left: 1.2rem;
  margin-top: 0.5rem;
}
.termo-box li {
  margin-bottom: 0.4rem;
}

.check-field {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1rem;
}
.check-field input {
  width: 18px;
  height: 18px;
  cursor: pointer;
}
.label-inline {
  font-size: 0.92rem;
  font-weight: 500;
  cursor: pointer;
  user-select: none;
}

/* Sucesso */
.text-center {
  text-align: center;
  padding: 3rem 1.5rem;
}
.success-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
  animation: scale-up-bounce 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.success-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
  margin-top: 2rem;
}
.text-sm {
  font-size: 0.85rem;
}

.fade-in {
  animation: fadeIn 0.35s ease;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes scale-up-bounce {
  0% { transform: scale(0.5); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}

/* Spinner inline */
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
