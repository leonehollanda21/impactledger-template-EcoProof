<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { maskCNPJ } from '../utils/format'
import { useToast } from '../composables/useToast'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const toast = useToast()

const mode = ref('cidadao')
const form = ref({ name: '', email: '', password: '', confirmPassword: '', cnpj: '' })
const loading = ref(false)
const err = ref('')
const institutoPendente = ref(false) // sucesso do instituto

onMounted(() => {
  if (route.query.type === 'instituto') mode.value = 'instituto'
})

const cnpjMasked = computed({
  get: () => maskCNPJ(form.value.cnpj),
  set: (v) => (form.value.cnpj = v.replace(/\D/g, '').slice(0, 14)),
})

function switchMode(m) {
  mode.value = m
  err.value = ''
  institutoPendente.value = false
}

function validate() {
  if (form.value.name.trim().length < 2) return 'Nome muito curto (mínimo 2 caracteres).'
  if (!/^\S+@\S+\.\S+$/.test(form.value.email)) return 'E-mail inválido.'
  if (
    form.value.password.length < 8 ||
    !/[a-z]/i.test(form.value.password) ||
    !/\d/.test(form.value.password)
  )
    return 'Senha precisa ter 8+ caracteres com letras e números.'
  if (form.value.password !== form.value.confirmPassword) return 'As senhas não coincidem.'
  if (mode.value === 'instituto' && form.value.cnpj.length !== 14)
    return 'CNPJ deve ter 14 dígitos numéricos.'
  return ''
}

async function submit() {
  err.value = ''
  institutoPendente.value = false
  const v = validate()
  if (v) { err.value = v; return }
  loading.value = true
  try {
    if (mode.value === 'cidadao') {
      await auth.registerCidadao({
        name: form.value.name.trim(),
        email: form.value.email.trim(),
        password: form.value.password,
      })
      toast.success('Bem-vindo ao EcoProof! Conta criada com sucesso. 🌱')
      router.push('/app/dashboard')
    } else {
      await auth.registerInstituto({
        name: form.value.name.trim(),
        email: form.value.email.trim(),
        password: form.value.password,
        cnpj: form.value.cnpj,
      })
      institutoPendente.value = true
      toast.success('Instituto registrado! Aguarde aprovação do administrador.')
      // Limpa o formulário após sucesso
      form.value = { name: '', email: '', password: '', confirmPassword: '', cnpj: '' }
    }
  } catch (e) {
    err.value = e.message || 'Ocorreu um erro inesperado. Tente novamente.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page-wrapper">
    <div class="register-card">
      <!-- Cabeçalho -->
      <div class="card-header">
        <div class="logo-icon">🌿</div>
        <h1>Criar conta</h1>
        <p class="subtitle">Junte-se à revolução sustentável com blockchain.</p>
      </div>

      <!-- Seletor de tipo de conta -->
      <div class="mode-toggle" role="tablist" aria-label="Tipo de conta">
        <button
          id="tab-cidadao"
          role="tab"
          :aria-selected="mode === 'cidadao'"
          :class="{ active: mode === 'cidadao' }"
          @click="switchMode('cidadao')"
          type="button"
        >
          <span class="tab-icon">👤</span> Cidadão
        </button>
        <button
          id="tab-instituto"
          role="tab"
          :aria-selected="mode === 'instituto'"
          :class="{ active: mode === 'instituto' }"
          @click="switchMode('instituto')"
          type="button"
        >
          <span class="tab-icon">🏛️</span> Instituto / ONG
        </button>
      </div>

      <!-- Banner de sucesso para instituto -->
      <Transition name="slide-fade">
        <div v-if="institutoPendente" class="success-banner" role="alert">
          <div class="success-icon">✅</div>
          <div>
            <strong>Instituto registrado com sucesso!</strong>
            <p>Sua solicitação foi enviada. Aguarde a aprovação de um administrador para acessar a plataforma.</p>
            <RouterLink to="/login" class="btn-link">Ir para o login →</RouterLink>
          </div>
        </div>
      </Transition>

      <!-- Formulário -->
      <form v-if="!institutoPendente" @submit.prevent="submit" novalidate>
        <!-- Nome -->
        <div class="field">
          <label class="label" :for="`field-name-${mode}`">
            {{ mode === 'instituto' ? 'Nome da instituição' : 'Nome completo' }}
          </label>
          <input
            :id="`field-name-${mode}`"
            class="input"
            v-model="form.name"
            required
            autocomplete="name"
            :placeholder="mode === 'instituto' ? 'Ex: ONG Verde Vivo' : 'Ex: João Silva'"
          />
        </div>

        <!-- E-mail -->
        <div class="field">
          <label class="label" for="field-email">E-mail</label>
          <input
            id="field-email"
            class="input"
            type="email"
            v-model="form.email"
            required
            autocomplete="email"
            placeholder="Ex: joao@exemplo.com"
          />
        </div>

        <!-- CNPJ (somente instituto) -->
        <Transition name="slide-fade">
          <div v-if="mode === 'instituto'" class="field">
            <label class="label" for="field-cnpj">CNPJ</label>
            <input
              id="field-cnpj"
              class="input"
              v-model="cnpjMasked"
              required
              inputmode="numeric"
              placeholder="XX.XXX.XXX/XXXX-XX"
              maxlength="18"
            />
            <span class="field-hint">Somente os 14 dígitos numéricos (com ou sem formatação)</span>
          </div>
        </Transition>

        <!-- Senha -->
        <div class="field">
          <label class="label" for="field-password">Senha</label>
          <input
            id="field-password"
            class="input"
            type="password"
            v-model="form.password"
            required
            autocomplete="new-password"
            placeholder="Mínimo 8 caracteres, com letras e números"
          />
        </div>

        <!-- Confirmar senha -->
        <div class="field">
          <label class="label" for="field-confirm">Confirmar senha</label>
          <input
            id="field-confirm"
            class="input"
            type="password"
            v-model="form.confirmPassword"
            required
            autocomplete="new-password"
            placeholder="Repita a senha"
          />
        </div>

        <!-- Erro -->
        <Transition name="slide-fade">
          <div v-if="err" class="error-banner" role="alert">
            <span class="error-icon">⚠️</span>
            <span>{{ err }}</span>
          </div>
        </Transition>

        <!-- Info extra para instituto -->
        <div v-if="mode === 'instituto'" class="info-box">
          <span>ℹ️</span>
          <span>Após o cadastro, sua conta aguardará aprovação de um administrador antes de ser liberada.</span>
        </div>

        <!-- Botão de submit -->
        <button
          id="btn-register-submit"
          class="btn btn-primary submit-btn"
          :disabled="loading"
          type="submit"
        >
          <span v-if="loading" class="spinner"></span>
          <span>{{ loading ? 'Criando conta…' : (mode === 'cidadao' ? 'Criar conta de cidadão' : 'Registrar instituto') }}</span>
        </button>
      </form>

      <!-- Rodapé -->
      <p class="footer-link">
        Já tem conta? <RouterLink to="/login">Fazer login</RouterLink>
      </p>
    </div>
  </div>
</template>

<style scoped>
.page-wrapper {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
}

.register-card {
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: var(--radius-lg, 16px);
  box-shadow: var(--shadow-card, 0 4px 24px rgba(0,0,0,0.08));
  padding: 2.5rem 2rem;
  width: 100%;
  max-width: 500px;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

/* Cabeçalho */
.card-header {
  text-align: center;
  margin-bottom: 0.5rem;
}
.logo-icon {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
  display: block;
}
h1 {
  font-size: 1.9rem;
  margin: 0 0 0.3rem;
  font-weight: 700;
  color: var(--color-text, #1a1a1a);
}
.subtitle {
  color: var(--color-muted, #64748b);
  font-size: 0.95rem;
  margin: 0;
}

/* Toggle de modo */
.mode-toggle {
  display: flex;
  background: var(--color-surface-alt, #f1f5f9);
  border-radius: var(--radius-md, 12px);
  padding: 4px;
  gap: 4px;
}
.mode-toggle button {
  flex: 1;
  padding: 0.65rem 0.75rem;
  border: none;
  background: transparent;
  cursor: pointer;
  border-radius: calc(var(--radius-md, 12px) - 4px);
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--color-muted, #64748b);
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
.mode-toggle button.active {
  background: #fff;
  color: var(--color-primary, #22c55e);
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
.tab-icon {
  font-size: 1rem;
}

/* Formulário */
form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text, #1a1a1a);
}
.input {
  padding: 0.65rem 0.9rem;
  border: 1.5px solid var(--color-border, #e2e8f0);
  border-radius: var(--radius-sm, 8px);
  font-size: 0.95rem;
  background: var(--color-bg, #fff);
  color: var(--color-text, #1a1a1a);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  outline: none;
}
.input:focus {
  border-color: var(--color-primary, #22c55e);
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.15);
}
.field-hint {
  font-size: 0.78rem;
  color: var(--color-muted, #94a3b8);
}

/* Banners */
.error-banner {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  background: #fef2f2;
  border: 1.5px solid #fca5a5;
  border-radius: var(--radius-sm, 8px);
  padding: 0.75rem 1rem;
  color: #dc2626;
  font-size: 0.9rem;
  font-weight: 500;
}
.error-icon { flex-shrink: 0; }

.success-banner {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  background: #f0fdf4;
  border: 1.5px solid #86efac;
  border-radius: var(--radius-sm, 8px);
  padding: 1rem;
  color: #166534;
  font-size: 0.9rem;
}
.success-banner strong { display: block; margin-bottom: 0.3rem; font-size: 1rem; }
.success-banner p { margin: 0 0 0.6rem; }
.success-icon { font-size: 1.4rem; flex-shrink: 0; }
.btn-link {
  color: var(--color-primary, #22c55e);
  font-weight: 600;
  text-decoration: none;
}
.btn-link:hover { text-decoration: underline; }

.info-box {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: var(--radius-sm, 8px);
  padding: 0.7rem 0.9rem;
  color: #1e40af;
  font-size: 0.85rem;
}

/* Botão */
.submit-btn {
  width: 100%;
  justify-content: center;
  height: 48px;
  font-size: 1rem;
  margin-top: 0.25rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* Rodapé */
.footer-link {
  text-align: center;
  color: var(--color-muted, #64748b);
  font-size: 0.9rem;
  margin: 0;
}
.footer-link a {
  color: var(--color-primary, #22c55e);
  font-weight: 600;
  text-decoration: none;
}
.footer-link a:hover { text-decoration: underline; }

/* Animações */
.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.25s ease;
}
.slide-fade-enter-from,
.slide-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.spinner {
  display: inline-block;
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
