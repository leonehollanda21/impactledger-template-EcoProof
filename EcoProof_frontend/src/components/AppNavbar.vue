<script setup>
import { computed, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const showProfileMenu = ref(false)

const initials = computed(() => (auth.user?.name || '?').split(' ').map(s => s[0]).slice(0,2).join('').toUpperCase())

function logout() { 
  auth.logout()
  showProfileMenu.value = false 
  router.push('/') 
}
</script>

<template>
  <header class="nav">
    <div class="nav-inner">
      <RouterLink to="/" class="brand">🌿 EcoProof</RouterLink>
      <nav class="links">
        <template v-if="auth.isCidadao">
          <RouterLink to="/app/dashboard">Dashboard</RouterLink>
        </template>
        <RouterLink to="/app/pontos-verdes">Pontos Verdes</RouterLink>
        <RouterLink to="/app/eventos">Eventos</RouterLink>
        <template v-if="auth.isCidadao">
          <RouterLink to="/app/carteira">Carteira</RouterLink>
        </template>
        <RouterLink v-if="auth.isInstituto" to="/instituto/dashboard">Instituto</RouterLink>
        <RouterLink v-if="auth.isAdmin" to="/admin/dashboard">Admin</RouterLink>
      </nav>
      
      <div class="actions">
        <template v-if="auth.isAuthenticated">
          
          <div class="avatar-wrapper">
            <div 
              class="avatar" 
              @click="showProfileMenu = !showProfileMenu" 
              title="Ver meu perfil"
            >
              {{ initials }}
            </div>
            
            <div v-if="showProfileMenu" class="profile-dropdown">
              <div class="profile-info">
                <strong>{{ auth.user?.name }}</strong>
                <span class="text-muted">{{ auth.user?.email || 'Sem e-mail cadastrado' }}</span>
              </div>
            </div>
            
            <div v-if="showProfileMenu" class="dropdown-overlay" @click="showProfileMenu = false"></div>
          </div>
          <button class="btn btn-ghost" @click="logout">Sair</button>
        </template>
        
        <template v-else>
          <RouterLink to="/login" class="btn btn-ghost">Entrar</RouterLink>
          <RouterLink to="/register" class="btn btn-primary">Criar conta</RouterLink>
        </template>
      </div>
    </div>
  </header>
</template>

<style scoped>
.nav { background:#fff; border-bottom:1px solid var(--color-border); position:sticky; top:0; z-index:50; }
.nav-inner { max-width:1200px; margin:0 auto; padding: .8rem 1.25rem; display:flex; align-items:center; gap:1rem; }
.brand { font-family: var(--font-display); font-weight:800; font-size:1.25rem; color: var(--color-primary); text-decoration: none; }
.links { display:flex; gap:1.1rem; margin-left:1.5rem; flex:1; }
.links a { color: var(--color-text); font-weight:500; text-decoration: none; }
.links a.router-link-active { color: var(--color-secondary); }
.actions { display:flex; gap:.6rem; align-items:center; }

.avatar-wrapper { position: relative; }

.avatar { 
  width:36px; 
  height:36px; 
  border-radius:50%; 
  background: var(--color-tertiary); 
  color:#fff; 
  display:grid; 
  place-items:center; 
  font-weight:700; 
  cursor: pointer; 
  transition: transform 0.15s ease-in-out, box-shadow 0.15s ease;
  z-index: 51;
  position: relative;
}
.avatar:hover { 
  transform: scale(1.05); 
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

.profile-dropdown {
  position: absolute;
  top: calc(100% + 0.5rem);
  right: 0; 
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  padding: 1rem 1.25rem;
  min-width: 220px;
  z-index: 52;
  animation: fadeInDown 0.15s ease-out;
  cursor: default;
}

.profile-info { display: flex; flex-direction: column; gap: 0.2rem; }
.profile-info strong { color: var(--color-text); font-size: 0.95rem; line-height: 1.2; }
.profile-info .text-muted { color: var(--color-muted); font-size: 0.82rem; }

.dropdown-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  z-index: 50;
}

@keyframes fadeInDown {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width:768px){ .links { display:none; } }
</style>