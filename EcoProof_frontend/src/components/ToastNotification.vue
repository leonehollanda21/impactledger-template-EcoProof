<script setup>
import { useToast } from '../composables/useToast'
const { state } = useToast()
</script>
<template>
  <div class="toasts">
    <div v-for="t in state.toasts" :key="t.id" class="toast" :class="t.type">{{ t.message }}</div>
  </div>
</template>

<style scoped>
.toasts { 
  position: fixed; 
  top: 5rem;
  left: 50%; 
  transform: translateX(-50%); 
  display: flex; 
  flex-direction: column; 
  gap: .5rem; 
  z-index: 9999; 
  align-items: center; 
  pointer-events: none; 
}

.toast { 
  padding: .8rem 1rem; 
  border-radius: var(--radius-md); 
  color: #fff; 
  box-shadow: var(--shadow-lg); 
  min-width: 240px; 
  text-align: center;
}

.toast.success { background: var(--color-success); }
.toast.error { background: var(--color-danger); }
.toast.warn { background: var(--color-warn); }
.toast.info { background: var(--color-secondary); }
</style>