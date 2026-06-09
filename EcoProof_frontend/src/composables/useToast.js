import { reactive } from 'vue'
const state = reactive({ toasts: [] })
let id = 0
export function useToast() {
  function push(type, message, timeout = 4000) {
    const t = { id: ++id, type, message }
    state.toasts.push(t)
    setTimeout(() => { state.toasts = state.toasts.filter(x => x.id !== t.id) }, timeout)
  }
  return {
    state,
    success: (m) => push('success', m),
    error: (m) => push('error', m),
    info: (m) => push('info', m),
    warn: (m) => push('warn', m),
  }
}
