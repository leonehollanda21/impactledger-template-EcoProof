<script setup>
defineProps({ open: Boolean, title: String, confirmLabel: { type:String, default:'Confirmar' } })
defineEmits(['close','confirm'])
</script>
<template>
  <Transition name="fade">
    <div v-if="open" class="backdrop" @click.self="$emit('close')">
      <div class="modal card">
        <h3>{{ title }}</h3>
        <slot />
        <div class="actions">
          <button class="btn btn-ghost" @click="$emit('close')">Cancelar</button>
          <button class="btn btn-primary" @click="$emit('confirm')">{{ confirmLabel }}</button>
        </div>
      </div>
    </div>
  </Transition>
</template>
<style scoped>
.backdrop { position:fixed; inset:0; background:rgba(0,0,0,.45); display:grid; place-items:center; z-index:80; padding:1rem; }
.modal { max-width:520px; width:100%; }
.actions { display:flex; gap:.6rem; justify-content:flex-end; margin-top:1rem; }
</style>
