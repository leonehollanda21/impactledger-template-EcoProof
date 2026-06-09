<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from './stores/auth'
import AppNavbar from './components/AppNavbar.vue'
import AppFooter from './components/AppFooter.vue'
import ToastNotification from './components/ToastNotification.vue'

const auth = useAuthStore()
onMounted(() => { if (auth.token) auth.fetchMe().catch(() => auth.logout()) })
</script>

<template>
  <AppNavbar />
  <main class="app-main">
    <RouterView v-slot="{ Component }">
      <Transition name="fade" mode="out-in">
        <component :is="Component" />
      </Transition>
    </RouterView>
  </main>
  <AppFooter />
  <ToastNotification />
</template>

<style>
.app-main {
  min-height: 0 !important;   
}
</style>