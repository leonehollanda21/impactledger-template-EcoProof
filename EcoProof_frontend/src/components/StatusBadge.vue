<script setup>
const props = defineProps({ status: String })
const map = {
  pendente: { label:'Pendente', bg:'#fdf3d8', fg:'#8a6d1f' },
  aprovado: { label:'Aprovado', bg:'#d8f0e0', fg:'#1a3d2b' },
  reprovado: { label:'Reprovado', bg:'#fadbd8', fg:'#922b21' },
  confirmado: { label:'Confirmado', bg:'#d6eafc', fg:'#1f4e79' },
  foto_enviada: { label:'Foto enviada', bg:'#e8def6', fg:'#553c8b' },
  rejeitado: { label:'Rejeitado', bg:'#fadbd8', fg:'#922b21' },
  ativo: { label:'Ativo', bg:'#d8f0e0', fg:'#1a3d2b' },
  encerrado: { label:'Encerrado', bg:'#e6e6e6', fg:'#444' },
}
const s = map[props.status] || { label: props.status || '—', bg:'#eee', fg:'#333' }
</script>
<template><span class="badge" :style="{ background:s.bg, color:s.fg }">{{ s.label }}</span></template>
