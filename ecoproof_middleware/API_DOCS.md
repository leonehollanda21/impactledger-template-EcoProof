# 🌿 EcoProof API — Documentação para o Frontend

> **Base URL:** `http://localhost:8000/api/v1`  
> **Docs interativas:** `http://localhost:8000/docs`  
> **Versão da API:** 1.0.0

---

## Índice

- [Autenticação](#autenticação)
- [Perfil do Usuário](#perfil-do-usuário)
- [Limpezas Individuais](#limpezas-individuais)
- [Eventos & Participações](#eventos--participações)
- [NFTs](#nfts)
- [Administração](#administração)
- [Referência de Tipos](#referência-de-tipos)
- [Tratamento de Erros](#tratamento-de-erros)
- [Guia de Integração](#guia-de-integração)

---

## Autenticação

Todas as rotas protegidas exigem o header:

```
Authorization: Bearer <token>
```

O token é obtido ao registrar ou fazer login.

---

### `POST /auth/register/cidadao`
Registra um novo cidadão e retorna o token JWT imediatamente.

**Acesso:** Público

**Body (JSON):**
```json
{
  "name": "João Silva",
  "email": "joao@example.com",
  "password": "Senha@123"
}
```

| Campo | Tipo | Regras |
|-------|------|--------|
| `name` | string | 2–100 caracteres |
| `email` | string | e-mail válido |
| `password` | string | 8–128 chars, mínimo 1 letra e 1 número |

**Resposta `201`:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "role": "cidadao"
}
```

**Erros comuns:**
- `409 Conflict` — e-mail já cadastrado
- `422 Unprocessable Entity` — campos inválidos

---

### `POST /auth/register/instituto`
Registra um instituto/ONG. O login só é liberado após aprovação admin.

**Acesso:** Público

**Body (JSON):**
```json
{
  "name": "ONG Verde Vivo",
  "email": "contato@verdevivo.org",
  "password": "Senha@123",
  "cnpj": "12.345.678/0001-90"
}
```

| Campo | Tipo | Regras |
|-------|------|--------|
| `cnpj` | string | 14 dígitos numéricos (com ou sem formatação) |

**Resposta `201`:**
```json
{
  "message": "Instituto registrado com sucesso.",
  "detail": "Aguarde a aprovação de um administrador para acessar a plataforma."
}
```

---

### `POST /auth/login`
Autentica com e-mail e senha via JSON.

**Acesso:** Público

**Body (JSON):**
```json
{
  "email": "joao@example.com",
  "password": "Senha@123"
}
```

**Resposta `200`:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "role": "cidadao"
}
```

**Erros comuns:**
- `401 Unauthorized` — credenciais inválidas
- `403 Forbidden` — conta desativada (instituto pendente)

---

### `POST /auth/login/form`
Endpoint OAuth2 compatível com Swagger UI (usa `form-data`).

> **⚠️ Atenção:** Use `POST /auth/login` (JSON) no frontend. Esta rota é para o Swagger.

---

### `POST /auth/refresh`
Renova o token JWT sem precisar reautenticar.

**Acesso:** 🔒 Autenticado (qualquer role)

**Headers:**
```
Authorization: Bearer <token_atual>
```

**Resposta `200`:** Igual ao login — novo `access_token`.

---

## Perfil do Usuário

### `GET /users/me`
Retorna o perfil completo do usuário autenticado. A estrutura da resposta varia por `role`.

**Acesso:** 🔒 Autenticado

#### Cidadão (`role: "cidadao"`)
```json
{
  "id": "uuid",
  "name": "João Silva",
  "email": "joao@example.com",
  "role": "cidadao",
  "wallet_address": "0xABC...",
  "is_active": true,
  "created_at": "2026-05-25T10:00:00",
  "total_points": 120
}
```

#### Instituto (`role: "instituto"`)
```json
{
  "id": "uuid",
  "name": "ONG Verde Vivo",
  "email": "contato@verdevivo.org",
  "role": "instituto",
  "wallet_address": null,
  "is_active": true,
  "created_at": "2026-05-25T10:00:00",
  "cnpj": "12.345.678/0001-90",
  "verified": true,
  "verified_at": "2026-05-26T09:00:00"
}
```

#### Admin (`role: "admin"`)
```json
{
  "id": "uuid",
  "name": "Admin",
  "email": "admin@ecoproof.io",
  "role": "admin",
  "is_active": true,
  "created_at": "2026-05-25T10:00:00"
}
```

---

### `PATCH /users/me`
Atualiza `name` e/ou `wallet_address` do usuário autenticado.

**Acesso:** 🔒 Autenticado

**Query params:**
| Param | Tipo | Descrição |
|-------|------|-----------|
| `name` | string (opcional) | Novo nome |
| `wallet_address` | string (opcional) | Novo endereço de wallet |

**Exemplo:**
```
PATCH /api/v1/users/me?name=João%20Santos&wallet_address=0xNEW...
```

**Resposta `200`:** Objeto de perfil atualizado (igual ao `GET /users/me`).

---

### `GET /users/me/nfts`
Lista todos os NFTs do cidadão autenticado.

**Acesso:** 🔒 Cidadão

**Resposta `200`:** Array de [`NFTResponse`](#nftresponse)

---

## Limpezas Individuais

> Limpeza individual é uma ação ambiental registrada pelo próprio cidadão com fotos antes/depois, validada por IA.

---

### `POST /limpezas`
Registra uma limpeza com upload de fotos. **O envio deve ser `multipart/form-data`.**

**Acesso:** 🔒 Cidadão

**Form fields:**
| Campo | Tipo | Obrigatório | Descrição |
|-------|------|:-----------:|-----------|
| `foto_antes` | File (JPEG/PNG/WebP) | ✅ | Foto do local ANTES da limpeza |
| `foto_depois` | File (JPEG/PNG/WebP) | ✅ | Foto do local DEPOIS da limpeza |
| `tipo_acao` | string (enum) | ✅ | Ver [`TipoAcao`](#tipoacao) |

**Pipeline executado:**
1. Upload das fotos para Cloudinary
2. Análise das imagens com Google Gemini AI
3. Se `score >= 0.5` → aprovado automaticamente
4. Se aprovado → NFT mintado + **10 pontos** creditados

**Resposta `201`:**
```json
{
  "limpeza": {
    "id": "uuid",
    "cidadao_id": "uuid",
    "foto_antes_url": "https://res.cloudinary.com/...",
    "foto_depois_url": "https://res.cloudinary.com/...",
    "tipo_acao": "praia",
    "status": "aprovado",
    "created_at": "2026-05-25T21:36:35"
  },
  "aprovado": true,
  "score": 0.87,
  "motivo": "O local antes apresentava lixo na areia. Após a limpeza, a área está livre de resíduos.",
  "nft": {
    "id": "uuid",
    "token_id": "42",
    "cidadao_id": "uuid",
    "assinado_por": "cidadao",
    "metadata_url": "https://...",
    "tx_hash": "0xabc...",
    "created_at": "2026-05-25T21:36:38",
    "tipo_acao": "praia",
    "foto_url": "https://res.cloudinary.com/..."
  }
}
```

> Se `aprovado: false`, o campo `nft` será `null`.

**Exemplo com `fetch`:**
```javascript
const formData = new FormData();
formData.append('foto_antes', fotoAntesFile);
formData.append('foto_depois', fotoDepoisFile);
formData.append('tipo_acao', 'praia');

const response = await fetch('/api/v1/limpezas', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` },
  body: formData,
});
```

---

### `GET /limpezas/me`
Histórico paginado de limpezas do cidadão autenticado.

**Acesso:** 🔒 Cidadão

**Query params:**
| Param | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `page` | int | `1` | Página (começa em 1) |
| `page_size` | int | `20` | Itens por página (máx 100) |
| `status` | string | `null` | Filtrar: `pendente \| aprovado \| reprovado` |

**Resposta `200`:**
```json
{
  "items": [
    {
      "id": "uuid",
      "tipo_acao": "praia",
      "status": "aprovado",
      "foto_depois_url": "https://res.cloudinary.com/...",
      "created_at": "2026-05-25T21:36:35"
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 20,
  "has_next": false
}
```

---

### `GET /limpezas/{limpeza_id}`
Detalhe completo de uma limpeza específica.

**Acesso:** 🔒 Cidadão (somente as próprias limpezas)

**Resposta `200`:** Objeto [`LimpezaResponse`](#limpezaresponse)

**Erros:**
- `403` — limpeza pertence a outro cidadão
- `404` — não encontrada

---

## Eventos & Participações

> Eventos são mutirões organizados por institutos. Cidadãos fazem check-in e enviam foto para comprovação.

---

### `GET /eventos`
Lista eventos públicos ativos. Sem autenticação.

**Acesso:** Público

**Query params:**
| Param | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `page` | int | `1` | Página |
| `page_size` | int | `20` | Itens por página (máx 100) |
| `status` | string | `ativo` | `ativo \| encerrado \| cancelado` |
| `tipo_acao` | string | `null` | Ver [`TipoAcao`](#tipoacao) |

**Resposta `200`:**
```json
{
  "items": [
    {
      "id": "uuid",
      "titulo": "Mutirão Praia Grande",
      "descricao": "Limpeza coletiva da orla.",
      "tipo_acao": "praia",
      "local": "Praia Grande, SP",
      "data_evento": "2026-06-15T09:00:00",
      "status": "ativo",
      "foto_capa_url": "https://res.cloudinary.com/...",
      "created_at": "2026-05-25T10:00:00",
      "instituto_id": "uuid",
      "instituto_nome": "ONG Verde Vivo",
      "total_participantes": 12
    }
  ],
  "total": 3,
  "page": 1,
  "page_size": 20,
  "has_next": false
}
```

---

### `GET /eventos/{evento_id}`
Detalhes públicos de um evento.

**Acesso:** Público

**Resposta `200`:** Objeto `EventoResponse` (igual ao item acima)

---

### `POST /eventos/{evento_id}/participar`
Cidadão faz check-in em um evento (status inicial = `confirmado`).

**Acesso:** 🔒 Cidadão

**Resposta `201`:**
```json
{
  "id": "uuid",
  "evento_id": "uuid",
  "cidadao_id": "uuid",
  "cidadao_nome": "João Silva",
  "foto_url": null,
  "status": "confirmado",
  "checkin_at": "2026-05-25T14:00:00",
  "motivo_rejeicao": null
}
```

**Erros:**
- `409` — cidadão já inscrito neste evento
- `422` — evento não está ativo

---

### `POST /eventos/{evento_id}/participacoes/{participacao_id}/foto`
Cidadão envia foto comprovando participação. Enviada como `multipart/form-data`.

**Acesso:** 🔒 Cidadão (somente a própria participação)

**Form fields:**
| Campo | Tipo | Obrigatório |
|-------|------|:-----------:|
| `foto` | File (JPEG/PNG/WebP) | ✅ |

**Resposta `200`:** Objeto `ParticipacaoResponse` com `status: "foto_enviada"`

**Erros:**
- `403` — participação de outro cidadão
- `422` — status atual não permite envio de foto

---

### `GET /eventos/minhas-participacoes`
Histórico paginado de participações do cidadão.

**Acesso:** 🔒 Cidadão

**Query params:** `page`, `page_size`

**Resposta `200`:**
```json
{
  "items": [
    {
      "id": "uuid",
      "evento_id": "uuid",
      "evento_titulo": "Mutirão Praia Grande",
      "foto_url": "https://res.cloudinary.com/...",
      "status": "aprovado",
      "checkin_at": "2026-05-25T14:00:00",
      "motivo_rejeicao": null
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 20,
  "has_next": false
}
```

---

### `POST /eventos` *(Instituto)*
Cria um evento de mutirão. Enviado como `multipart/form-data`.

**Acesso:** 🔒 Instituto (verificado)

**Form fields:**
| Campo | Tipo | Obrigatório | Regras |
|-------|------|:-----------:|--------|
| `titulo` | string | ✅ | 3–200 chars |
| `tipo_acao` | string (enum) | ✅ | Ver [`TipoAcao`](#tipoacao) |
| `local` | string | ✅ | 3–300 chars |
| `data_evento` | string (ISO 8601) | ✅ | Deve ser data futura |
| `descricao` | string | ❌ | Até 2000 chars |
| `foto_capa` | File (JPEG/PNG) | ❌ | Imagem de capa |

**Resposta `201`:** Objeto `EventoResponse`

---

### `PUT /eventos/{evento_id}` *(Instituto)*
Atualiza um evento existente (apenas o instituto dono).

**Acesso:** 🔒 Instituto (dono do evento)

**Form fields:** Todos opcionais — mesmos campos do `POST /eventos`.

**Resposta `200`:** Objeto `EventoResponse` atualizado.

---

### `DELETE /eventos/{evento_id}` *(Instituto)*
Cancela o evento (soft delete: `status → "cancelado"`).

**Acesso:** 🔒 Instituto (dono do evento)

**Resposta `200`:** Objeto `EventoResponse` com `status: "cancelado"`

---

### `GET /eventos/meus` *(Instituto)*
Lista todos os eventos do instituto autenticado (todos os status).

**Acesso:** 🔒 Instituto

**Query params:** `page`, `page_size`

**Resposta `200`:** Paginação de `EventoResponse`

---

### `GET /eventos/{evento_id}/participacoes` *(Instituto)*
Lista todos os participantes do evento com filtro opcional de status.

**Acesso:** 🔒 Instituto (dono do evento)

**Query params:**
| Param | Valores possíveis |
|-------|------------------|
| `status` | `confirmado \| foto_enviada \| aprovado \| rejeitado` |
| `page`, `page_size` | paginação |

**Resposta `200`:**
```json
{
  "items": [
    {
      "id": "uuid",
      "evento_id": "uuid",
      "cidadao_id": "uuid",
      "cidadao_nome": "João Silva",
      "foto_url": "https://res.cloudinary.com/...",
      "status": "foto_enviada",
      "checkin_at": "2026-05-25T14:00:00",
      "motivo_rejeicao": null
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 50,
  "has_next": false
}
```

---

### `GET /eventos/{evento_id}/detalhe` *(Instituto)*
Evento com lista completa de participantes e contadores por status.

**Acesso:** 🔒 Instituto (dono do evento)

**Resposta `200`:** `EventoResponse` + campos extras:
```json
{
  "...campos do EventoResponse...",
  "participantes": [ ... ],
  "total_confirmados": 3,
  "total_aprovados": 2,
  "total_rejeitados": 0,
  "total_foto_enviada": 1
}
```

---

### `PATCH /participacoes/{participacao_id}/aprovar` *(Instituto)*
Aprova a participação de um cidadão (pré-condição: `status == "foto_enviada"`).

**Acesso:** 🔒 Instituto (dono do evento)

**Resposta `200`:** Objeto `ParticipacaoResponse` com `status: "aprovado"`

---

### `PATCH /participacoes/{participacao_id}/rejeitar` *(Instituto)*
Rejeita a participação com um motivo obrigatório.

**Acesso:** 🔒 Instituto (dono do evento)

**Body (JSON):**
```json
{
  "motivo_rejeicao": "A foto enviada não mostra claramente a participação no evento."
}
```

| Campo | Regras |
|-------|--------|
| `motivo_rejeicao` | 10–500 caracteres |

**Resposta `200`:** Objeto `ParticipacaoResponse` com `status: "rejeitado"`

---

### `POST /eventos/{evento_id}/emitir-nfts` *(Instituto)*
Emite NFTs em lote para todos os participantes aprovados do evento.

**Acesso:** 🔒 Instituto (dono do evento)

**Resposta `200`:**
```json
{
  "evento_id": "uuid",
  "total_emitido": 5,
  "tx_hashes": ["0xabc...", "0xdef..."],
  "erros": [],
  "pontos_distribuidos": 150
}
```

> Cada cidadão aprovado recebe **30 pontos**. Idempotente: participações que já têm NFT são ignoradas.

---

## NFTs

### `GET /nfts/{token_id}`
Detalhe completo de um NFT pelo seu `token_id` numérico.

**Acesso:** Público

**Resposta `200`:**
```json
{
  "id": "uuid",
  "token_id": "42",
  "cidadao_id": "uuid",
  "assinado_por": "cidadao",
  "metadata_url": "https://res.cloudinary.com/.../metadata.json",
  "tx_hash": "0xabc...",
  "created_at": "2026-05-25T21:36:38",
  "limpeza_id": "uuid",
  "participacao_id": null,
  "instituto_id": null,
  "tipo_acao": "praia",
  "foto_url": "https://res.cloudinary.com/..."
}
```

---

### `GET /nfts/{token_id}/metadata.json`
Retorna o metadata ERC-721 puro (padrão OpenSea). Usado pela blockchain.

**Acesso:** Público

**Resposta `200` (JSON):**
```json
{
  "name": "EcoProof — Praia",
  "description": "NFT de comprovação de ação ambiental na plataforma EcoProof.",
  "image": "https://res.cloudinary.com/...",
  "external_url": "https://ecoproof.io/nft/42",
  "attributes": [
    { "trait_type": "Tipo de Ação", "value": "Praia" },
    { "trait_type": "Score", "value": 0.87 }
  ],
  "ecoproof_version": "1.0"
}
```

---

## Administração

> Todos os endpoints abaixo exigem `role: "admin"`.

---

### `GET /admin/dashboard`
Estatísticas globais da plataforma.

**Acesso:** 🔒 Admin

**Resposta `200`:**
```json
{
  "total_usuarios": 150,
  "total_cidadaos": 140,
  "total_institutos": 10,
  "total_institutos_pendentes": 2,
  "total_eventos": 25,
  "total_limpezas": 320,
  "total_nfts": 280,
  "total_validacoes_aprovadas": 275,
  "total_pontos_distribuidos": 8400
}
```

---

### `GET /admin/institutos`
Lista institutos com contagens de eventos e NFTs.

**Acesso:** 🔒 Admin

**Query params:**
| Param | Tipo | Descrição |
|-------|------|-----------|
| `verified` | bool (opcional) | `true` = só verificados, `false` = só pendentes, omitir = todos |
| `page`, `page_size` | int | Paginação |

**Resposta `200`:**
```json
{
  "items": [
    {
      "id": "uuid",
      "nome": "ONG Verde Vivo",
      "email": "contato@verdevivo.org",
      "cnpj": "12.345.678/0001-90",
      "verified": false,
      "verified_at": null,
      "is_active": false,
      "created_at": "2026-05-25T10:00:00",
      "total_eventos": 0,
      "total_nfts_emitidos": 0
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "has_next": false
}
```

---

### `PATCH /admin/institutos/{instituto_id}/aprovar`
Aprova um instituto pendente (libera o login).

**Acesso:** 🔒 Admin

**Resposta `200`:**
```json
{
  "success": true,
  "message": "Instituto aprovado com sucesso.",
  "instituto_id": "uuid"
}
```

---

### `PATCH /admin/institutos/{instituto_id}/suspender`
Suspende um instituto ativo (bloqueia o login imediatamente).

**Acesso:** 🔒 Admin

**Resposta `200`:** Igual ao aprovar, com mensagem diferente.

---

### `GET /admin/validacoes`
Lista todas as validações de limpezas e participações.

**Acesso:** 🔒 Admin

**Query params:**
| Param | Tipo | Descrição |
|-------|------|-----------|
| `resultado` | bool (opcional) | `true` = aprovadas, `false` = reprovadas, omitir = todas |
| `page`, `page_size` | int | Paginação |

**Resposta `200`:**
```json
{
  "items": [
    {
      "id": "uuid",
      "resultado": true,
      "score": 0.87,
      "motivo": "Melhoria real verificada.",
      "created_at": "2026-05-25T21:36:38",
      "tipo": "limpeza",
      "limpeza_id": "uuid",
      "participacao_id": null,
      "cidadao_id": "uuid",
      "cidadao_nome": "João Silva",
      "cidadao_wallet": "0xABC..."
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "has_next": true
}
```

---

## Referência de Tipos

### TipoAcao
```
lixo_rua | praia | corrego | queimada | outro
```

### StatusLimpeza
```
pendente | aprovado | reprovado
```

### StatusEvento
```
ativo | encerrado | cancelado
```

### StatusParticipacao
```
confirmado | foto_enviada | aprovado | rejeitado
```

### AssinadoPor (NFT)
```
cidadao | instituto
```

### UserRole
```
cidadao | instituto | admin
```

---

## Tratamento de Erros

Todos os erros seguem o formato padrão do FastAPI:

```json
{
  "detail": "Mensagem descritiva do erro."
}
```

| Código | Significado |
|--------|-------------|
| `400` | Requisição malformada |
| `401` | Token ausente, inválido ou expirado |
| `403` | Sem permissão (role errada ou recurso de outro usuário) |
| `404` | Recurso não encontrado |
| `409` | Conflito (e.g., e-mail já cadastrado, já inscrito no evento) |
| `422` | Validação falhou (campos inválidos) |
| `502` | Falha em serviço externo (Gemini AI, Cloudinary) |

---

## Guia de Integração

### Configuração de cliente HTTP (exemplo com `fetch`)

```javascript
// utils/api.js

const BASE_URL = 'http://localhost:8000/api/v1';

function getToken() {
  return localStorage.getItem('ecoproof_token');
}

export async function api(path, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Erro desconhecido' }));
    throw new Error(error.detail || 'Erro na requisição');
  }

  return response.json();
}
```

### Fluxo de autenticação

```javascript
// 1. Registrar
const { access_token, role } = await api('/auth/register/cidadao', {
  method: 'POST',
  body: JSON.stringify({ name, email, password }),
});
localStorage.setItem('ecoproof_token', access_token);
localStorage.setItem('ecoproof_role', role);

// 2. Login
const { access_token, role } = await api('/auth/login', {
  method: 'POST',
  body: JSON.stringify({ email, password }),
});

// 3. Pegar perfil
const profile = await api('/users/me');
```

### Upload de limpeza (multipart)

```javascript
async function registrarLimpeza(fotoAntes, fotoDepois, tipoAcao) {
  const token = getToken();
  const formData = new FormData();
  formData.append('foto_antes', fotoAntes);
  formData.append('foto_depois', fotoDepois);
  formData.append('tipo_acao', tipoAcao);

  const response = await fetch(`${BASE_URL}/limpezas`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    // NÃO definir Content-Type — o browser define automaticamente com boundary
    body: formData,
  });

  return response.json();
}
```

### Fluxo do cidadão em um evento

```javascript
// 1. Listar eventos disponíveis
const { items } = await api('/eventos?status=ativo');

// 2. Fazer check-in
const participacao = await api(`/eventos/${eventoId}/participar`, { method: 'POST' });

// 3. Enviar foto de comprovação
const formData = new FormData();
formData.append('foto', fotoFile);

await fetch(`${BASE_URL}/eventos/${eventoId}/participacoes/${participacao.id}/foto`, {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` },
  body: formData,
});
```

### Sistema de pontos

| Ação | Pontos |
|------|--------|
| Limpeza individual aprovada | **+10 pts** |
| Participação em evento aprovada (após emissão do NFT pelo instituto) | **+30 pts** |
