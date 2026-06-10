# 🐍 EcoProof — Middleware (Backend)

Bem-vindo ao módulo de Backend do **EcoProof**, uma solução desenvolvida para o desafio **ImpactLedger** no **Hackathon Web3 RESTIC 29**.

## 💻 Sobre o Módulo
O Middleware é o núcleo da plataforma EcoProof. É ele quem orquestra todos os fluxos: autentica usuários, valida evidências fotográficas com inteligência artificial (Google Gemini), faz upload das imagens para a nuvem (Cloudinary), persiste os dados no banco relacional (PostgreSQL) e assina as transações para emitir os NFTs Soulbound nos contratos inteligentes da rede **Polygon** via Web3.py.

A API expõe endpoints para três perfis: **Cidadão** (registra ações e recebe NFTs), **Instituto/ONG** (cria eventos e emite NFTs em lote) e **Administrador** (modera, aprova e audita toda a plataforma).

## 🛠 Tecnologias Utilizadas
- **Python 3.11+ & FastAPI**: Framework assíncrono de alta performance para a construção da API REST.
- **PostgreSQL 15 + SQLAlchemy 2.0 (async)**: Banco de dados relacional com ORM assíncrono.
- **Alembic**: Gerenciamento de migrations do banco de dados.
- **Pydantic v2**: Validação e serialização de schemas de dados.
- **Google Gemini 1.5 Flash**: Validação automática das imagens de evidência das ações ambientais (gratuito — 1500 req/dia).
- **Cloudinary**: Armazenamento em nuvem das fotos e metadados dos NFTs (plano gratuito — 25 GB).
- **Web3.py + Polygon Amoy**: Integração com a blockchain para mint de NFTs Soulbound e registro de provas on-chain.
- **JWT (python-jose) + bcrypt (passlib)**: Autenticação e segurança.

## 🚀 Como Executar Localmente

### Pré-requisitos
- Python 3.11+
- PostgreSQL 15 instalado e rodando
- Contratos do módulo `ecoproof_blockchain` já deployados (os endereços gerados serão necessários no `.env`)

### Passo a Passo

1. **Acesse a pasta do middleware:**
   ```bash
   cd ecoproof_middleware
   ```

2. **Crie e ative o ambiente virtual:**
   ```bash
   # Criar
   python -m venv venv

   # Ativar — Windows (PowerShell)
   venv\Scripts\activate

   # Ativar — Linux / macOS
   source venv/bin/activate
   ```

3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure as variáveis de ambiente:**
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

   # 🔗 Blockchain — endereços gerados no deploy do módulo ecoproof_blockchain
   # Defina BLOCKCHAIN_ENABLED=true para usar blockchain real.
   # Sem isso, o sistema opera em modo simulado (gera tx_hash fake).
   BLOCKCHAIN_ENABLED=false
   WEB3_PROVIDER_URL=https://rpc-amoy.polygon.technology/
   NFT_CONTRACT_ADDRESS=0x...
   INSTITUTO_NFT_CONTRACT_ADDRESS=0x...
   REGISTRY_CONTRACT_ADDRESS=0x...
   DENUNCIA_NFT_ADDRESS=0x...
   EDUCACAO_NFT_ADDRESS=0x...

   # ATENÇÃO: NUNCA commite a chave real. Use variável de ambiente em produção.
   MINTER_PRIVATE_KEY=0x...sua-chave-privada
   CHAIN_ID=80002
   ```

   > **Modo simulado:** com `BLOCKCHAIN_ENABLED=false`, token IDs e transaction hashes são gerados localmente. Isso permite desenvolver e testar sem nenhuma blockchain real.

5. **Crie o banco de dados:**
   ```bash
   psql -U postgres -c "CREATE DATABASE ecoproof;"
   ```

6. **Execute as migrations:**
   ```bash
   alembic upgrade head
   ```
   Isso cria todas as tabelas automaticamente (`users`, `cidadaos`, `institutos`, `eventos`, `participacoes`, `limpezas_individuais`, `denuncias`, `acoes_educativas`, `pontos_verdes`, `nfts`, `validacoes`).

7. **Inicie o servidor:**
   ```bash
   uvicorn app.main:app --reload
   ```
   A API estará disponível em **http://localhost:8000**.
   Acesse **http://localhost:8000/docs** para o Swagger UI e teste todos os endpoints interativamente.

---

## 🐳 Rodando com Docker (alternativa mais fácil)

Se preferir não instalar o PostgreSQL localmente:

```bash
# 1. Configure o .env
cp .env.example .env
# Preencha SECRET_KEY, Cloudinary e Gemini no .env

# 2. Suba tudo (API + banco + migrations automáticas)
docker compose up --build

# Rodar em background
docker compose up -d --build
```

O Docker já cuida de subir o PostgreSQL 15, rodar `alembic upgrade head` automaticamente e iniciar a API com hot-reload.

---

## Estrutura de Arquivos

```
ecoproof_middleware/
├── app/
│   ├── abi/                       # ABIs exportadas pelo deploy do ecoproof_blockchain
│   │   ├── EcoProofNFT.json
│   │   ├── InstitutoNFT.json
│   │   ├── EducacaoNFT.json
│   │   ├── DenunciaNFT.json
│   │   └── EcoProofRegistry.json
│   ├── controllers/               # Routers FastAPI (endpoints por domínio)
│   │   ├── auth_router.py
│   │   ├── limpezas_router.py
│   │   ├── eventos_router.py
│   │   ├── denuncias_router.py
│   │   ├── educacao_router.py
│   │   ├── pontos_verdes_router.py
│   │   ├── nfts_router.py
│   │   ├── users_router.py
│   │   └── admin_router.py
│   ├── core/
│   │   ├── config.py              # Settings via pydantic-settings
│   │   ├── security.py            # JWT + bcrypt
│   │   └── dependencies.py        # get_db, CurrentUser, roles
│   ├── db/                        # Engine assíncrono, Base, Session
│   ├── models/                    # Models SQLAlchemy
│   ├── schemas/                   # Schemas Pydantic v2
│   ├── services/                  # Lógica de negócio e integrações externas
│   │   ├── blockchain_service.py  # Web3.py — mint e registry on-chain (com fallback simulado)
│   │   ├── vision_service.py      # Validação de imagens via Google Gemini
│   │   ├── storage_service.py     # Upload para Cloudinary
│   │   └── ...                    # Demais services por domínio
│   └── main.py                    # Entry point FastAPI
├── alembic/
│   └── versions/                  # Scripts de migration gerados
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── API_DOCS.md                    # Documentação completa de payloads e respostas
├── BLOCKCHAIN_ARCHITECTURE.md    # Arquitetura da integração on-chain e decisões de design
└── .env.example
```

---

## Endpoints Principais

| Método | Rota | Descrição | Auth |
|--------|------|-----------|------|
| `POST` | `/api/v1/auth/register` | Registrar cidadão | — |
| `POST` | `/api/v1/auth/register/instituto` | Registrar instituto | — |
| `POST` | `/api/v1/auth/login` | Login — retorna JWT | — |
| `GET` | `/api/v1/users/me` | Perfil do usuário autenticado | ✅ |
| `POST` | `/api/v1/limpezas` | Registrar limpeza individual (fotos + IA) | Cidadão |
| `GET` | `/api/v1/limpezas/me` | Histórico paginado de limpezas | Cidadão |
| `GET` | `/api/v1/eventos` | Listar eventos ativos | ✅ |
| `POST` | `/api/v1/eventos` | Criar evento de mutirão | Instituto |
| `POST` | `/api/v1/eventos/{id}/participacoes` | Check-in em evento | Cidadão |
| `POST` | `/api/v1/eventos/{id}/mint-lote` | Emitir NFTs em lote via Merkle Tree | Instituto |
| `POST` | `/api/v1/denuncias` | Registrar denúncia ambiental (foto + texto) | Cidadão |
| `GET` | `/api/v1/denuncias/me` | Listar minhas denúncias | Cidadão |
| `GET` | `/api/v1/denuncias/{id}/verificar` | Verificar denúncia on-chain (auditoria pública) | — |
| `POST` | `/api/v1/educacao` | Registrar ação de educação ambiental | Cidadão / Instituto |
| `GET` | `/api/v1/educacao/me` | Listar minhas ações educativas | Cidadão / Instituto |
| `PATCH` | `/api/v1/educacao/{id}/validar` | Aprovar ou rejeitar ação educativa | Admin / Instituto |
| `GET` | `/api/v1/educacao/impacto/total` | Total de pessoas impactadas on-chain | — |
| `GET` | `/api/v1/nfts` | Meus NFTs | Cidadão |
| `GET` | `/api/v1/admin/dashboard` | Estatísticas gerais da plataforma | Admin |
| `GET` | `/api/v1/admin/institutos` | Listar institutos | Admin |
| `PATCH` | `/api/v1/admin/institutos/{id}/aprovar` | Aprovar instituto | Admin |
| `POST` | `/api/v1/admin/denuncias/{id}/resolver` | Resolver denúncia e emitir NFT | Admin |

> Para a documentação completa com todos os payloads, consulte [API_DOCS.md](./API_DOCS.md).

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
| `Denuncia` | Denúncia ambiental com foto, proof_hash on-chain e status de resolução |
| `AcaoEducativa` | Palestra ou oficina de educação ambiental com número de pessoas impactadas |
| `PontoVerde` | Ponto de coleta seletiva cadastrado na plataforma |
| `Validacao` | Resultado da análise (Gemini AI ou manual) |
| `NFT` | Token Soulbound mintado como recompensa (on-chain ou simulado) |

---

*Este módulo é uma parte integrante da arquitetura do EcoProof, concebido a partir do [Template Oficial do ImpactLedger](https://github.com/Web3irede/impactledger-template).*  
*Uso de IA para ajuda no código, porém tudo revisado e devidamente alterado pelos programadores.*
