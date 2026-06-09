<script setup>
import { ref } from 'vue'
const props = defineProps({ label: String, modelValue: File })
const emit = defineEmits(['update:file'])
const preview = ref(null)
const drag = ref(false)
function handle(file) {
  if (!file) return
  if (!/^image\/(jpeg|png|webp)$/.test(file.type)) { alert('Imagem JPEG, PNG ou WebP'); return }
  const reader = new FileReader()
  reader.onload = e => { preview.value = e.target.result }
  reader.readAsDataURL(file)
  emit('update:file', file)
}
function onDrop(e) { drag.value = false; handle(e.dataTransfer.files[0]) }
function onChange(e) { handle(e.target.files[0]) }
</script>
<template>
  <div class="up" :class="{ drag }"
    @dragover.prevent="drag=true" @dragleave="drag=false" @drop.prevent="onDrop">
    <label class="up-inner">
      <div v-if="preview" class="preview"><img :src="preview" /></div>
      <div v-else class="placeholder">
        <strong>{{ label || 'Enviar imagem' }}</strong>
        <span class="muted">Clique ou arraste aqui (JPEG/PNG/WebP)</span>
      </div>
      <input type="file" accept="image/jpeg,image/png,image/webp" @change="onChange" hidden />
    </label>
  </div>
</template>
<style scoped>
.up { border:2px dashed var(--color-border); border-radius: var(--radius-md); background:#fff; transition: border-color .15s, background .15s; }
.up.drag { border-color: var(--color-secondary); background:#f1f8f3; }
.up-inner { display:block; cursor:pointer; padding:1rem; min-height:180px; }
.placeholder { display:flex; flex-direction:column; align-items:center; justify-content:center; gap:.3rem; min-height:160px; color: var(--color-primary); text-align:center; }
.preview img { width:100%; max-height:280px; object-fit:cover; border-radius: var(--radius-sm); }
</style>
