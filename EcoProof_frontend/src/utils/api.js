/**
 * Utilitário de chamadas HTTP para a EcoProof API.
 *
 * Em desenvolvimento, o Vite proxy encaminha /api/* → http://localhost:8000/api/*,
 * evitando CORS. Em produção, defina a variável de ambiente VITE_API_BASE_URL.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

function getToken() {
  return localStorage.getItem('ecoproof_token')
}

/**
 * Extrai uma mensagem de erro legível da resposta da API.
 * Suporta os formatos:
 *   - { detail: "string" }
 *   - { message: "string" }      ← formato padronizado do nosso exception handler
 *   - { detail: [{ msg, loc }] } ← validação Pydantic raw (fallback)
 */
function extractErrorMessage(data, statusText) {
  if (!data) return statusText || 'Erro de rede'

  // Nosso exception handler retorna { error: true, message: "..." }
  if (typeof data.message === 'string' && data.message) return data.message

  // FastAPI padrão retorna { detail: "..." } ou { detail: [...] }
  if (typeof data.detail === 'string' && data.detail) return data.detail

  if (Array.isArray(data.detail)) {
    return data.detail
      .map((e) => {
        const loc = (e.loc || []).filter((l) => l !== 'body').join(' → ')
        return loc ? `${loc}: ${e.msg}` : e.msg
      })
      .join(' | ')
  }

  return statusText || 'Erro desconhecido'
}

async function handle(res) {
  const ct = res.headers.get('content-type') || ''
  const data = ct.includes('application/json')
    ? await res.json().catch(() => ({}))
    : await res.text()

  if (!res.ok) {
    const message = extractErrorMessage(
      typeof data === 'object' ? data : null,
      res.statusText,
    )

    // Mapeia códigos HTTP para mensagens amigáveis em PT-BR
    const friendlyMessages = {
      409: 'Este e-mail já está cadastrado. Tente fazer login ou use outro e-mail.',
      403: 'Sua conta ainda não foi aprovada pelo administrador.',
      401: 'Credenciais inválidas. Verifique seu e-mail e senha.',
      422: message, // usa a mensagem detalhada de validação
      500: 'Erro interno do servidor. Tente novamente mais tarde.',
    }

    const finalMessage = friendlyMessages[res.status] ?? message

    const err = new Error(finalMessage)
    err.status = res.status
    err.data = data
    throw err
  }

  return data
}

function authHeaders(extra = {}) {
  const t = getToken()
  return t ? { Authorization: `Bearer ${t}`, ...extra } : { ...extra }
}

export const api = {
  get: (path) =>
    fetch(`${BASE_URL}${path}`, { headers: authHeaders() }).then(handle),

  post: (path, body) =>
    fetch(`${BASE_URL}${path}`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: body ? JSON.stringify(body) : undefined,
    }).then(handle),

  patch: (path, body) =>
    fetch(`${BASE_URL}${path}`, {
      method: 'PATCH',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: body ? JSON.stringify(body) : undefined,
    }).then(handle),

  put: (path, body) =>
    fetch(`${BASE_URL}${path}`, {
      method: 'PUT',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: body ? JSON.stringify(body) : undefined,
    }).then(handle),

  del: (path) =>
    fetch(`${BASE_URL}${path}`, {
      method: 'DELETE',
      headers: authHeaders(),
    }).then(handle),
}

/**
 * Envia multipart/form-data (upload de fotos, etc.).
 * NÃO defina Content-Type manualmente — o browser injeta o boundary correto.
 */
export function apiFormData(path, formData, method = 'POST') {
  return fetch(`${BASE_URL}${path}`, {
    method,
    headers: authHeaders(),
    body: formData,
  }).then(handle)
}
