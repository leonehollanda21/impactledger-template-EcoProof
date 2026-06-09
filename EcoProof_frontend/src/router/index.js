import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/', component: () => import('../views/Landing.vue'), meta: { public: true } },
  { path: '/login', component: () => import('../views/Login.vue'), meta: { public: true } },
  { path: '/register', component: () => import('../views/Register.vue'), meta: { public: true } },

  { path: '/app/dashboard', component: () => import('../views/CidadaoDashboard.vue'), meta: { roles: ['cidadao'] } },
  { path: '/app/registrar-limpeza', component: () => import('../views/RegistrarLimpeza.vue'), meta: { roles: ['cidadao'] } },
  { path: '/app/registrar-educacao', component: () => import('../views/RegistrarEducacao.vue'), meta: { roles: ['cidadao', 'instituto'] } },
  { path: '/app/registrar-denuncia', component: () => import('../views/RegistrarDenuncia.vue'), meta: { roles: ['cidadao', 'instituto'] } },
  { path: '/app/pontos-verdes', component: () => import('../views/PontosVerdes.vue'), meta: { public: true } },
  { path: '/app/adotar-area', component: () => import('../views/RegistrarAdocao.vue'), meta: { roles: ['cidadao'] } },
  { path: '/app/eventos', component: () => import('../views/Eventos.vue'), meta: { public: true } },
  { path: '/app/carteira', component: () => import('../views/Carteira.vue'), meta: { roles: ['cidadao'] } },

  { path: '/instituto/dashboard', component: () => import('../views/InstitutoDashboard.vue'), meta: { roles: ['instituto'] } },
  { path: '/instituto/eventos/:id', component: () => import('../views/InstitutoEvento.vue'), meta: { roles: ['instituto'] } },

  { path: '/admin/dashboard', component: () => import('../views/AdminDashboard.vue'), meta: { roles: ['admin'] } },

  { path: '/nft/:token_id', component: () => import('../views/NFTPublico.vue'), meta: { public: true } },

  { path: '/:pathMatch(.*)*', component: () => import('../views/NotFound.vue'), meta: { public: true } },
]

const router = createRouter({ history: createWebHistory(), routes, scrollBehavior: () => ({ top: 0 }) })

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.public) return true
  if (!auth.isAuthenticated) return { path: '/login', query: { redirect: to.fullPath } }
  if (to.meta.roles && !to.meta.roles.includes(auth.role)) return { path: '/' }
  return true
})

export default router
