# EcoProof Backend

Backend da plataforma **EcoProof** — cidadãos registram ações ambientais (limpar praias, córregos, ruas) e recebem NFTs como recompensa. Institutos/ONGs criam eventos de mutirão e emitem NFTs para participantes.

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Framework | Python 3.11+ + FastAPI |
| Banco de dados | PostgreSQL 15 + SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Schemas | Pydantic v2 |
| Armazenamento de fotos | Cloudinary (plano gratuito — 25 GB) |
| Validação de imagens | Google Gemini 1.5 Flash (gratuito — 1500 req/dia) |
| Blockchain / NFT | **Simulado** — hashes e token IDs gerados localmente |
| Auth | JWT (python-jose) + bcrypt (passlib) |

---

## Rodando localmente

### Pré-requisitos

- Python 3.11+
- PostgreSQL 15 instalado e rodando
- Git

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/ecoproof-backend.git
cd ecoproof-backend
```

### 2. Crie e ative o ambiente virtual

```bash
# Criar
python -m venv venv

# Ativar — Windows (PowerShell)
venv\Scripts\activate

# Ativar — Linux / macOS
source venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente

```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Abra o `.env` e preencha os campos obrigatórios:

```env
# 🔑 Obrigatório — gere com o comando abaixo:
# python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=cole-aqui-uma-chave-aleatoria-forte

# 🗄️ Obrigatório — ajuste usuário/senha/porta se necessário
DATABASE_URL=postgresql+asyncpg://postgres:root@localhost:5432/ecoproof
DATABASE_URL_SYNC=postgresql://postgres:root@localhost:5432/ecoproof

# 📸 Obrigatório para upload de fotos
# Crie conta grátis em https://cloudinary.com → Dashboard → Settings → API Keys
CLOUDINARY_CLOUD_NAME=seu-cloud-name
CLOUDINARY_API_KEY=seu-api-key
CLOUDINARY_API_SECRET=seu-api-secret

# 🤖 Opcional — sem isso, o Vision entra em modo simulado (aprova tudo)
# Obtenha grátis em https://ai.google.dev → Get API key
GEMINI_API_KEY=sua-gemini-api-key
```

> **Blockchain:** as variáveis `WEB3_PROVIDER_URL`, `NFT_CONTRACT_ADDRESS` e `MINTER_PRIVATE_KEY` são completamente ignoradas — o mint é simulado localmente sem nenhuma integração real.

### 5. Crie o banco de dados

```bash
# Conecte ao PostgreSQL e crie o banco
psql -U postgres -c "CREATE DATABASE ecoproof;"
```

> Se o seu PostgreSQL usa usuário/senha diferentes, ajuste o comando acima e o `DATABASE_URL` no `.env`.

### 6. Execute as migrations

```bash
alembic upgrade head
```

Isso cria todas as tabelas automaticamente (`users`, `cidadaos`, `institutos`, `eventos`, `participacoes`, `limpezas_individuais`, `nfts`, `validacoes`).

### 7. Inicie o servidor

```bash
uvicorn app.main:app --reload
```

A API estará disponível em **http://localhost:8000**

---

## Verificando se está tudo certo

| URL | O que faz |
|-----|-----------|
| http://localhost:8000/health | Health check — mostra status da API e do banco |
| http://localhost:8000/docs | Swagger UI — teste todos os endpoints interativamente |
| http://localhost:8000/redoc | Documentação ReDoc |

---

## Rodando com Docker (alternativa mais fácil)

Se preferir não instalar PostgreSQL localmente:

```bash
# 1. Configure o .env
copy .env.example .env
# Preencha SECRET_KEY, Cloudinary e Gemini no .env

# 2. Suba tudo (API + banco + migrations automáticas)
docker compose up --build

# Rodar em background
docker compose up -d --build
```

O Docker já cuida de:
- Subir o PostgreSQL 15
- Rodar `alembic upgrade head` automaticamente
- Iniciar a API com hot-reload

---

## Estrutura do projeto

```
ecoproof-backend/
├── app/
│   ├── controllers/     # Routers FastAPI (endpoints)
│   ├── core/
│   │   ├── config.py    # Settings via pydantic-settings
│   │   ├── security.py  # JWT + bcrypt
│   │   └── dependencies.py  # get_db, CurrentUser, roles
│   ├── db/              # Engine assíncrono, Base, Session
│   ├── models/          # Models SQLAlchemy
│   ├── schemas/         # Schemas Pydantic v2
│   ├── services/        # Lógica de negócio e integrações
│   └── main.py          # Entry point FastAPI
├── alembic/
│   └── versions/        # Scripts de migration gerados
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Endpoints principais

| Método | Rota | Descrição | Auth |
|--------|------|-----------|------|
| `POST` | `/api/v1/auth/register` | Registrar cidadão | — |
| `POST` | `/api/v1/auth/register/instituto` | Registrar instituto | — |
| `POST` | `/api/v1/auth/login` | Login — retorna JWT | — |
| `GET` | `/api/v1/users/me` | Perfil do usuário autenticado | ✅ |
| `POST` | `/api/v1/limpezas` | Registrar limpeza individual (fotos + IA) | Cidadão |
| `GET` | `/api/v1/limpezas` | Listar minhas limpezas | Cidadão |
| `GET` | `/api/v1/eventos` | Listar eventos ativos | ✅ |
| `POST` | `/api/v1/eventos` | Criar evento de mutirão | Instituto |
| `POST` | `/api/v1/eventos/{id}/participacoes` | Check-in em evento | Cidadão |
| `POST` | `/api/v1/eventos/{id}/mint-lote` | Emitir NFTs em lote | Instituto |
| `GET` | `/api/v1/nfts` | Meus NFTs | Cidadão |
| `GET` | `/api/v1/admin/institutos` | Listar institutos | Admin |
| `PATCH` | `/api/v1/admin/institutos/{id}/aprovar` | Aprovar instituto | Admin |

---

## Models

| Model | Descrição |
|-------|-----------|
| `User` | Base de autenticação — cidadão, instituto ou admin |
| `Cidadao` | Perfil extendido: pontos, wallet, total de NFTs |
| `Instituto` | ONG/empresa com CNPJ, verificação pelo admin |
| `Evento` | Mutirão de limpeza criado por instituto |
| `Participacao` | Check-in de cidadão em evento com foto |
| `LimpezaIndividual` | Ação autônoma com fotos antes/depois + validação IA |
| `Validacao` | Resultado da análise (Gemini AI ou manual) |
| `NFT` | Token mintado como recompensa (simulado) |
