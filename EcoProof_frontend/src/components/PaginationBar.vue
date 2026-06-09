<script setup>
defineProps({ page: Number, hasNext: Boolean })
defineEmits(['update:page'])
</script>
<template>
  <div class="pg">
    <button class="btn btn-ghost" :disabled="page <= 1" @click="$emit('update:page', page - 1)">← Anterior</button>
    <span class="muted">Página {{ page }}</span>
    <button class="btn btn-ghost" :disabled="!hasNext" @click="$emit('update:page', page + 1)">Próxima →</button>
  </div>
</template>
<style scoped>.pg { display:flex; gap:.6rem; align-items:center; justify-content:center; padding:1rem; }</style>
