export function formatDate(iso) {
  if (!iso) return '—'
  try { return new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) }
  catch { return iso }
}
const TIPOS = {
  lixo_rua: '🗑️ Lixo na rua',
  praia: '🏖️ Praia',
  corrego: '🏞️ Córrego',
  queimada: '🔥 Queimada',
  outro: '🌱 Outro',
}
export function formatTipoAcao(t) { return TIPOS[t] || t }
export function formatPoints(n) { return new Intl.NumberFormat('pt-BR').format(n || 0) }
export function truncateHash(h) { if (!h) return ''; return h.length > 12 ? `${h.slice(0,6)}…${h.slice(-4)}` : h }
export function maskCNPJ(v) {
  const d = (v || '').replace(/\D/g, '').slice(0, 14)
  return d
    .replace(/^(\d{2})(\d)/, '$1.$2')
    .replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3')
    .replace(/\.(\d{3})(\d)/, '.$1/$2')
    .replace(/(\d{4})(\d)/, '$1-$2')
}
