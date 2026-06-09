<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useToast } from '../composables/useToast'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const toast = useToast()

const email = ref('')
const password = ref('')
const loading = ref(false)
const err = ref('')
const errType = ref('') // 'pending' | 'invalid' | 'generic'

async function submit() {
  err.value = ''
  errType.value = ''

  if (!email.value || !password.value) {
    err.value = 'Preencha seu e-mail e senha para continuar.'
    errType.value = 'generic'
    return
  }

  loading.value = true
  try {
    await auth.login(email.value.trim(), password.value)
    const dest =
      route.query.redirect ||
      (auth.isAdmin
        ? '/admin/dashboard'
        : auth.isInstituto
          ? '/instituto/dashboard'
          : '/app/dashboard')
    toast.success('Login realizado com sucesso! 🌱')
    router.push(dest)
  } catch (e) {
    if (e.status === 403) {
      errType.value = 'pending'
      err.value =
        'Sua conta de instituto ainda aguarda aprovação do administrador. Você será notificado quando estiver liberada.'
    } else if (e.status === 401) {
      errType.value = 'invalid'
      err.value = 'E-mail ou senha incorretos. Verifique seus dados e tente novamente.'
    } else {
      errType.value = 'generic'
      err.value = e.message || 'Ocorreu um erro inesperado. Tente novamente.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page-wrapper">
    <div class="login-card">
      <!-- Cabeçalho -->
      <div class="card-header">
        <div class="logo-icon">🌿</div>
        <h1>Entrar</h1>
        <p class="subtitle">Acesse sua conta EcoProof.</p>
      </div>

      <form @submit.prevent="submit" novalidate>
        <!-- E-mail -->
        <div class="field">
          <label class="label" for="login-email">E-mail</label>
          <input
            id="login-email"
            class="input"
            type="email"
            v-model="email"
            required
            autocomplete="email"
            placeholder="seu@email.com"
          />
        </div>

        <!-- Senha -->
        <div class="field">
          <label class="label" for="login-password">Senha</label>
          <input
            id="login-password"
            class="input"
            type="password"
            v-model="password"
            required
            autocomplete="current-password"
            placeholder="Sua senha"
          />
        </div>

        <!-- Banner de erro -->
        <Transition name="slide-fade">
          <div
            v-if="err"
            :class="['error-banner', { 'error-warning': errType === 'pending' }]"
            role="alert"
          >
            <span class="error-icon">{{ errType === 'pending' ? '⏳' : '⚠️' }}</span>
            <span>{{ err }}</span>
          </div>
        </Transition>

        <!-- Botão de submit -->
        <button
          id="btn-login-submit"
          class="btn btn-primary submit-btn"
          :disabled="loading"
          type="submit"
        >
          <span v-if="loading" class="spinner"></span>
          <span>{{ loading ? 'Entrando…' : 'Entrar' }}</span>
        </button>
      </form>

      <!-- Rodapé -->
      <p class="footer-link">
        Novo aqui? <RouterLink to="/register">Criar conta</RouterLink>
      </p>
      <p class="footer-link">
        É uma ONG? <RouterLink to="/register?type=instituto">Registrar instituto</RouterLink>
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

.login-card {
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: var(--radius-lg, 16px);
  box-shadow: var(--shadow-card, 0 4px 24px rgba(0,0,0,0.08));
  padding: 2.5rem 2rem;
  width: 100%;
  max-width: 440px;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.card-header {
  text-align: center;
  margin-bottom: 0.25rem;
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
.error-banner.error-warning {
  background: #fffbeb;
  border-color: #fcd34d;
  color: #92400e;
}
.error-icon { flex-shrink: 0; }

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
