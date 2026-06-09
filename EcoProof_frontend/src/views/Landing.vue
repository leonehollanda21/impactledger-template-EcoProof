<script setup>
import { onMounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()

const stats = ref({ kg: 0, acoes: 0, cidadaos: 0 })
const targets = { kg: 12480, acoes: 3210, cidadaos: 1875 }

onMounted(() => {
  const start = performance.now(); const dur = 1500
  function tick(t) {
    const p = Math.min(1, (t - start)/dur)
    stats.value = { kg: Math.round(targets.kg*p), acoes: Math.round(targets.acoes*p), cidadaos: Math.round(targets.cidadaos*p) }
    if (p < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
})
</script>

<template>
  <div class="landing-page">
    <section class="hero">
      <div class="container hero-grid">
        <div>
          <span class="tag">IPTU Verde · Blockchain</span>
          <h1>Ações ambientais comprovadas <em>on-chain</em>.</h1>
          <p class="lead">EcoProof conecta cidadãos e institutos para registrar limpezas, gerar NFTs como prova e desbloquear benefícios reais no IPTU Verde da sua cidade.</p>
          
          <div class="cta">
            <template v-if="auth.isAuthenticated">
              <RouterLink 
                :to="auth.isCidadao ? '/app/dashboard' : auth.isInstituto ? '/instituto/dashboard' : '/admin/dashboard'" 
                class="btn btn-primary"
                style="padding: 1rem 2rem; font-size: 1.1rem; border-radius: 99px;"
              >
                Ir para o meu Dashboard →
              </RouterLink>
            </template>
            
            <template v-else>
              <RouterLink to="/register?type=cidadao" class="btn btn-primary">Sou Cidadão</RouterLink>
              <RouterLink to="/register?type=instituto" class="btn btn-accent">Sou Instituto</RouterLink>
            </template>
          </div>
          </div>
        <div class="hero-art" aria-hidden="true">
          <div class="orb"></div>
          <div class="leaf">🌿</div>
        </div>
      </div>
    </section>

    <section class="container">
      <h2>Como funciona</h2>
      <div class="grid grid-cards steps">
        <div class="card">
          <div class="step-n">1</div>
          <h3>Registre a ação</h3>
          <p class="muted">Tire fotos do antes e depois da limpeza no app.</p>
        </div>
        <div class="card">
          <div class="step-n">2</div>
          <h3>Valide com IA</h3>
          <p class="muted">Nossa IA analisa as imagens e aprova a evidência.</p>
        </div>
        <div class="card">
          <div class="step-n">3</div>
          <h3>Receba seu NFT</h3>
          <p class="muted">A prova vira NFT e pontos para o IPTU Verde.</p>
        </div>
      </div>
    </section>

    <section class="impact">
      <div class="container impact-grid">
        <div><strong>{{ stats.kg.toLocaleString('pt-BR') }}</strong><span>kg de resíduos retirados</span></div>
        <div><strong>{{ stats.acoes.toLocaleString('pt-BR') }}</strong><span>ações verificadas</span></div>
        <div><strong>{{ stats.cidadaos.toLocaleString('pt-BR') }}</strong><span>cidadãos engajados</span></div>
      </div>
    </section>

    </div>
</template>

<style scoped>
.hero { background: linear-gradient(135deg, #1a3d2b, #2e7d52); color:#fff; padding: 4rem 0; }
.hero-grid { display:grid; grid-template-columns: 1.3fr 1fr; gap:2rem; align-items:center; }
.tag { background: rgba(255,255,255,.15); padding:.35rem .7rem; border-radius:999px; font-size:.8rem; font-weight:600; }
.hero h1 { color:#fff; font-size:clamp(2rem, 4vw, 3.2rem); line-height:1.1; margin: 1rem 0; }
.hero h1 em { color: var(--color-accent); font-style:normal; }
.lead { font-size:1.1rem; max-width:520px; color:#e6f0ea; }
.cta { display:flex; gap:.8rem; margin-top:1.5rem; flex-wrap:wrap; }
.hero-art { position:relative; height:280px; }
.orb { position:absolute; inset:auto 0 0 0; margin:auto; width:240px; height:240px; border-radius:50%; background: radial-gradient(circle at 30% 30%, #52b788, #1a3d2b); box-shadow: 0 30px 80px rgba(0,0,0,.4); }
.leaf { position:absolute; inset:0; display:grid; place-items:center; font-size:7rem; }
.steps .step-n { width:36px; height:36px; border-radius:50%; background: var(--color-tertiary); color:#fff; display:grid; place-items:center; font-weight:700; margin-bottom:.5rem; }
.impact { background:#fff; border-top:1px solid var(--color-border); border-bottom:1px solid var(--color-border); margin-top:2rem; }
.impact-grid { display:grid; grid-template-columns: repeat(3,1fr); gap:1rem; padding:2rem 1.25rem; text-align:center; }
.impact-grid strong { display:block; font-family: var(--font-display); font-size:2.2rem; color: var(--color-primary); }
.impact-grid span { color: var(--color-muted); }
@media (max-width: 768px) { .hero-grid, .impact-grid { grid-template-columns: 1fr; } .hero-art{ display:none; } }
</style>