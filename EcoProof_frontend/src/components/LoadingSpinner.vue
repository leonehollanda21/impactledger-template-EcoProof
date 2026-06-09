<script setup>
defineProps({ message: String, dark: Boolean })
</script>
<template>
  <div class="ls">
    <span class="spinner" :class="{ dark }"></span>
    <span v-if="message">{{ message }}</span>
  </div>
</template>
<style scoped>
.ls { display:inline-flex; gap:.6rem; align-items:center; color: var(--color-primary); }
</style>
