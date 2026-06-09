import { ref, computed } from 'vue'
export function usePagination(initial = 1) {
  const page = ref(initial)
  const hasNext = ref(false)
  const hasPrev = computed(() => page.value > 1)
  function next() { if (hasNext.value) page.value++ }
  function prev() { if (hasPrev.value) page.value-- }
  function reset() { page.value = 1 }
  return { page, hasNext, hasPrev, next, prev, reset }
}
