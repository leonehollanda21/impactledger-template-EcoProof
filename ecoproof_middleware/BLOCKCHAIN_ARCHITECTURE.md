# 🔗 EcoProof — Arquitetura Blockchain

> Documento de design técnico para a camada blockchain do EcoProof.
> Descreve a escolha de rede, os contratos planejados, as interações com o backend e as decisões de arquitetura.

---

## Índice

1. [Contexto e Estado Atual](#1-contexto-e-estado-atual)
2. [Escolha da Rede](#2-escolha-da-rede)
3. [Visão Geral da Arquitetura](#3-visão-geral-da-arquitetura)
4. [Contratos Planejados](#4-contratos-planejados)
   - [EcoProofNFT.sol](#41-ecoproofnftsol--contrato-principal)
   - [EcoProofRegistry.sol](#42-ecoproofregistrysol--registro-de-evidências)
   - [EcoPoints.sol](#43-ecopointssol--roadmap)
5. [Fluxos de Interação](#5-fluxos-de-interação)
6. [Integração com o Backend](#6-integração-com-o-backend)
7. [Segurança e Mitigações](#7-segurança-e-mitigações)
8. [Roadmap de Evolução](#8-roadmap-de-evolução)

---

## 1. Contexto e Estado Atual

O backend (`app/services/nft_service.py`) já implementa toda a lógica de NFTs, mas **de forma simulada**: token IDs e transaction hashes são gerados localmente com `secrets`, sem nenhuma chamada real à blockchain.

```
# Hoje — simulado
def _generate_fake_token_id() -> str:
    return str(secrets.randbelow(9_999_998) + 1)

def _generate_fake_tx_hash() -> str:
    return "0x" + secrets.token_hex(32)
```

O README confirma isso:
> *"Blockchain / NFT: Simulado — hashes e token IDs gerados localmente"*
> *"as variáveis `WEB3_PROVIDER_URL`, `NFT_CONTRACT_ADDRESS` e `MINTER_PRIVATE_KEY` são completamente ignoradas"*

**Objetivo deste documento:** especificar a arquitetura real que substituirá essa simulação, mantendo compatibilidade total com o restante do sistema (FastAPI, PostgreSQL, Cloudinary, Gemini AI).

---

## 2. Escolha da Rede

### Opções avaliadas

| Critério | Ethereum Mainnet | **Polygon PoS** | Celo | Arbitrum |
|---|---|---|---|---|
| Gas fee médio por tx | ~$5–30 | **< $0,01** | ~$0,001 | ~$0,10 |
| Throughput | ~15 TPS | ~65 TPS | ~1000 TPS | ~40 TPS |
| Tempo de bloco | ~12s | **~2s** | ~5s | ~0,25s |
| EVM-compatible | ✅ | ✅ | ✅ | ✅ |
| Suporte OpenSea nativo | ✅ | ✅ | ❌ | ✅ |
| MetaMask plug-and-play | ✅ | **✅** | parcial | ✅ |
| Foco em sustentabilidade | ❌ | ❌ | ✅ | ❌ |
| Testnet pública gratuita | Sepolia | **Amoy** | Alfajores | Sepolia |

### Decisão: **Polygon PoS**

**Razões:**

- **Gas ultrabaixo** — emitir centenas de NFTs para participantes de mutirão custa frações de centavo, viabilizando o modelo de plataforma.
- **Ecossistema consolidado** — suporte nativo no OpenSea, MetaMask, Alchemy e Infura sem configuração extra do usuário.
- **Velocidade** — bloco confirmado em ~2s, compatível com a experiência síncrona esperada pela API (`wait_for_transaction_receipt`).
- **Proof of Stake** — footprint de carbono drasticamente menor que Proof of Work, alinhado com o propósito ambiental do EcoProof.

**Alternativa viável:** Celo — seu foco em impacto social e pagamento de gas com stablecoins (CUSD) é filosoficamente alinhado, mas o ecossistema de wallets/marketplaces é menor.

**Rede de testes:** Polygon Amoy (substitui Mumbai desde 2024).

---

## 3. Visão Geral da Arquitetura

```
┌──────────────────────────────────────────────────────────────────┐
│                       ECOPROOF PLATFORM                          │
│                                                                  │
│   ┌─────────────┐      ┌──────────────────────────────────────┐  │
│   │  Frontend   │─────▶│         FastAPI Backend              │  │
│   │  (Web/App)  │      │                                      │  │
│   └─────────────┘      │  ┌────────────────────────────────┐  │  │
│                        │  │       nft_service.py           │  │  │
│                        │  │  (hoje: simulado)              │  │  │
│                        │  │  (produção: chama web3.py)     │  │  │
│                        │  └────────────────┬───────────────┘  │  │
│                        └───────────────────┼──────────────────┘  │
│                                            │ JSON-RPC / WebSocket │
│                                            ▼                     │
│                   ┌────────────────────────────────────────┐     │
│                   │         Polygon PoS                    │     │
│                   │                                        │     │
│                   │  ┌──────────────────────────────────┐  │     │
│                   │  │        EcoProofNFT.sol           │  │     │
│                   │  │        (ERC-721 principal)       │  │     │
│                   │  │  • mintLimpeza(wallet, uri, ...)  │  │     │
│                   │  │  • mintEvento(wallet, uri, ...)   │  │     │
│                   │  │  • mintLote([...params])          │  │     │
│                   │  └──────────────────────────────────┘  │     │
│                   │                                        │     │
│                   │  ┌──────────────────────────────────┐  │     │
│                   │  │     EcoProofRegistry.sol         │  │     │
│                   │  │     (Evidências imutáveis)       │  │     │
│                   │  │  • registerLimpeza(hash, score)  │  │     │
│                   │  │  • registerParticipacao(hash)    │  │     │
│                   │  │  • verifyPhoto(id, hash) → bool  │  │     │
│                   │  └──────────────────────────────────┘  │     │
│                   │                                        │     │
│                   │  ┌──────────────────────────────────┐  │     │
│                   │  │   EcoPoints.sol  [roadmap]       │  │     │
│                   │  │   (ERC-20 Soulbound de pontos)   │  │     │
│                   │  └──────────────────────────────────┘  │     │
│                   └────────────────────────────────────────┘     │
│                                                                  │
│   Armazenamento off-chain:                                       │
│   ├── Cloudinary → fotos (antes/depois, capa de evento)          │
│   └── Cloudinary/S3 → metadata JSON (ERC-721 padrão OpenSea)    │
└──────────────────────────────────────────────────────────────────┘
```

### Princípios de design

| Princípio | Decisão |
|---|---|
| **Backend como intermediário** | Cidadãos e institutos nunca interagem diretamente com o contrato. O backend detém a `MINTER_ROLE`. |
| **Dados sensíveis off-chain** | Apenas hashes e metadados mínimos vão on-chain. Fotos ficam no Cloudinary. |
| **Idempotência garantida** | O contrato mapeia `offchainId → tokenId` e rejeita re-mint do mesmo UUID. |
| **Upgradeabilidade controlada** | `EcoProofNFT` usa proxy UUPS; `EcoProofRegistry` é imutável por design. |
| **Separação de responsabilidades** | NFT = posse/colecionável. Registry = âncora de auditoria. Points = reputação. |

---

## 4. Contratos Planejados

### 4.1 `EcoProofNFT.sol` — Contrato Principal

**Padrão:** ERC-721 com URI por token
**Upgradeabilidade:** UUPS (OpenZeppelin)
**Controle de acesso:** AccessControl com roles

#### Escolhas de design e justificativas

**Por que ERC-721 e não ERC-1155?**
Cada ação ambiental é um evento único e não-replicável. ERC-721 reflete isso semanticamente — cada NFT é distinto. ERC-1155 é ideal para itens fungíveis em edições (ex: "10 cópias do badge Praia"), o que não se aplica aqui.

**Por que UUPS e não Transparent Proxy?**
UUPS é mais eficiente em gas (a lógica de upgrade fica no implementation, não no proxy) e mais seguro contra ataques de colisão de storage. Para um hackathon, também é mais simples de operar.

**Por que `tokenURI` aponta para a API e não IPFS?**
Para o hackathon, a API (`/api/v1/nfts/{token_id}/metadata.json`) já existe e funciona. IPFS exige pinning permanente pago. Em produção, migrar para IPFS ou Arweave é o passo natural.

**Por que o instituto não minta diretamente?**
Segurança e UX. O instituto aprovaria participações via dashboard e o backend orquestraria tudo. Não exige que o instituto tenha MATIC ou saiba usar MetaMask. O backend é a conta confiável com gas pré-carregado.

#### Enums que espelham o modelo Python

```
ActionType:  LIXO_RUA=0 | PRAIA=1 | CORREGO=2 | QUEIMADA=3 | OUTRO=4
IssuedBy:    ECOPROOF=0 | INSTITUTO=1
```

#### Struct `NFTRecord` (dados armazenados on-chain por token)

| Campo | Tipo | Descrição |
|---|---|---|
| `actionType` | `ActionType` | Tipo de ação ambiental |
| `issuedBy` | `IssuedBy` | Origem: plataforma ou instituto |
| `citizen` | `address` | Wallet do cidadão no momento do mint |
| `offchainId` | `bytes32` | `keccak256(UUID)` do registro no Postgres |
| `issuedAt` | `uint256` | Timestamp Unix do bloco de mint |
| `aiScore` | `uint256` | Score Gemini AI × 100 (0 para mutirões) |
| `institutionWallet` | `address` | Wallet do instituto (zero para limpezas) |

#### Funções principais

| Função | Acesso | Descrição |
|---|---|---|
| `mintLimpeza(to, uri, offchainId, actionType, aiScore)` | `MINTER_ROLE` | Minta NFT para limpeza individual aprovada pela IA |
| `mintEvento(to, uri, offchainId, actionType, institutionWallet)` | `MINTER_ROLE` | Minta NFT para participante de mutirão aprovado |
| `mintLote([MintBatchParams], eventHash)` | `MINTER_ROLE` | Mint em lote otimizado para emissão coletiva pós-evento |
| `isMinted(offchainId)` | público | Verifica se UUID já foi mintado |
| `getRecord(tokenId)` | público | Retorna o `NFTRecord` on-chain do token |
| `totalSupply()` | público | Total de NFTs emitidos |

#### Eventos emitidos

| Evento | Quando |
|---|---|
| `ActionMinted(tokenId, citizen, actionType, issuedBy, offchainId, aiScore)` | A cada NFT mintado |
| `BatchMinted(eventHash, institution, count)` | Ao final de um `mintLote` |

#### Garanias de idempotência

O mapeamento `offchainToToken[bytes32 offchainId] → uint256 tokenId` garante que o mesmo UUID do Postgres nunca gere dois tokens. O `mintLote` pula silenciosamente os já mintados em vez de reverter, permitindo re-execução segura.

---

### 4.2 `EcoProofRegistry.sol` — Registro de Evidências

**Padrão:** Contrato simples (não-upgradeable)
**Controle de acesso:** AccessControl com `REGISTRAR_ROLE`

#### Por que esse contrato existe separado do NFT?

O NFT prova **posse** de uma conquista. O Registry prova **autenticidade** da evidência física. São garantias diferentes:

- O NFT pode ser transferido (colecionável).
- O hash da foto nunca muda — é uma âncora criptográfica permanente.
- Cidadãos sem wallet ainda têm sua ação registrada aqui.
- Qualquer auditor externo pode verificar se uma foto foi adulterada sem depender do Cloudinary.

> ⚠️ **Por design, este contrato NÃO é upgradeable.** Imutabilidade é seu principal valor.

#### Struct `Proof`

| Campo | Tipo | Descrição |
|---|---|---|
| `photoAfterHash` | `bytes32` | `keccak256` dos bytes da foto "depois" |
| `photoBeforeHash` | `bytes32` | `keccak256` dos bytes da foto "antes" (zero para eventos) |
| `aiScore` | `uint256` | Score Gemini × 100 (zero para eventos) |
| `timestamp` | `uint256` | Bloco em que a prova foi registrada |
| `actionType` | `uint8` | Índice do tipo de ação |
| `exists` | `bool` | Flag de existência (evita valor-zero ambíguo) |

#### Funções principais

| Função | Acesso | Descrição |
|---|---|---|
| `registerLimpeza(offchainId, photoAfterHash, photoBeforeHash, aiScore, actionType)` | `REGISTRAR_ROLE` | Registra hashes de uma limpeza individual após aprovação IA |
| `registerParticipacao(offchainId, photoHash, actionType)` | `REGISTRAR_ROLE` | Registra hash da foto de participação em mutirão |
| `verifyPhoto(offchainId, photoHash) → bool` | público | Verifica se o hash de uma foto bate com o registrado |
| `getProof(offchainId) → Proof` | público | Retorna a prova completa de um registro |

#### Ordem de execução no backend

```
Recebe fotos → Upload Cloudinary → Gemini AI (score)
     ↓
Registry.registerLimpeza(offchainId, keccak256(fotoDepois), keccak256(fotoAntes), score)
     ↓
NFT.mintLimpeza(wallet, tokenURI, offchainId, actionType, score)
     ↓
Salva tx_hash e token_id no Postgres
```

O registro de evidência acontece **antes** do mint do NFT. Mesmo que o mint falhe, a prova já está na blockchain.

---

### 4.3 `EcoPoints.sol` — Roadmap

**Padrão:** ERC-20 Soulbound (não-transferível)
**Status:** Roadmap — não necessário para o MVP

#### Motivação

Hoje os pontos vivem apenas no Postgres (`cidadaos.total_points`). Tokenizá-los abre possibilidades futuras:

- **Marketplace de recompensas:** trocar pontos por benefícios oferecidos por patrocinadores ambientais.
- **Governança:** cidadãos com mais pontos têm mais peso em votações da DAO EcoProof.
- **Staking de causas:** "apostar" pontos para priorizar quais tipos de mutirão recebem mais visibilidade.

#### Por que Soulbound?

Os pontos representam **reputação ambiental**, não riqueza. Torná-los transferíveis abriria mercado secundário de compra de reputação, corrompendo o sistema de incentivos.

A implementação Soulbound bloqueia `transfer()` e `transferFrom()` para qualquer origem que não seja o endereço zero (mint), permitindo apenas mint e burn.

---

## 5. Fluxos de Interação

### 5.1 Limpeza Individual

```
Cidadão                 Backend FastAPI              Polygon PoS
   │                         │                            │
   │  POST /limpezas          │                            │
   │  (foto_antes, foto_depois, tipo_acao)                │
   │────────────────────────▶│                            │
   │                         │                            │
   │                         │ 1. Upload → Cloudinary     │
   │                         │    ↳ foto_antes_url        │
   │                         │    ↳ foto_depois_url       │
   │                         │                            │
   │                         │ 2. Gemini AI analysis      │
   │                         │    ↳ score = 0.87          │
   │                         │    ↳ aprovado = true       │
   │                         │                            │
   │                         │ 3. Registry.registerLimpeza│
   │                         │    (offchainId, hashes,    │
   │                         │     score, actionType)     │
   │                         │───────────────────────────▶│
   │                         │    ← tx_hash_registry      │
   │                         │                            │
   │                         │ 4. NFT.mintLimpeza         │
   │                         │    (wallet, tokenURI,      │
   │                         │     offchainId, type, score│
   │                         │───────────────────────────▶│
   │                         │    ← token_id, tx_hash_nft │
   │                         │                            │
   │                         │ 5. Postgres:               │
   │                         │    nft.token_id = token_id │
   │                         │    nft.tx_hash = tx_hash   │
   │                         │    cidadao.points += 10    │
   │                         │                            │
   │  201 { limpeza, nft }   │                            │
   │◀────────────────────────│                            │
```

### 5.2 Emissão em Lote (Evento de Mutirão)

```
Instituto              Backend FastAPI              Polygon PoS
   │                         │                            │
   │  POST /eventos/{id}     │                            │
   │  /emitir-nfts           │                            │
   │────────────────────────▶│                            │
   │                         │                            │
   │                         │ 1. Busca participações     │
   │                         │    aprovadas sem NFT       │
   │                         │                            │
   │                         │ 2. Para cada participação: │
   │                         │    Registry.register       │
   │                         │    Participacao(...)       │
   │                         │───────────────────────────▶│
   │                         │                            │
   │                         │ 3. NFT.mintLote([          │
   │                         │    {wallet, uri, id}×N     │
   │                         │    ], eventHash)           │
   │                         │───────────────────────────▶│
   │                         │   ← [tokenId×N], tx_hash   │
   │                         │                            │
   │                         │ 4. Postgres:               │
   │                         │    Salva cada NFT          │
   │                         │    cidadao.points += 30×N  │
   │                         │                            │
   │  200 { total_emitido,   │                            │
   │        tx_hashes,       │                            │
   │        pontos_distr. }  │                            │
   │◀────────────────────────│                            │
```

### 5.3 Cidadão sem Wallet

```
Cidadão sem wallet        Backend
         │                    │
         │  POST /limpezas    │
         │──────────────────▶ │
         │                    │ score >= 0.5 ✓
         │                    │
         │                    │ → Registry.registerLimpeza() ✓
         │                    │   (prova imutável registrada)
         │                    │
         │                    │ → NFT.mintLimpeza() ✗ PULA
         │                    │   (wallet_address == null)
         │                    │
         │                    │ → Postgres: limpeza.status = aprovado
         │                    │             nft = null (pendente)
         │                    │             cidadao.points += 10
         │                    │
         │  201 { aprovado: true, nft: null }
         │◀───────────────────│
         │
         │  PATCH /users/me?wallet_address=0xABC...
         │──────────────────▶ │
         │                    │ → Retroativamente minta NFTs pendentes
         │                    │   (job agendado ou lazy mint no próximo login)
```

---

## 6. Integração com o Backend

### 6.1 O que muda no `nft_service.py`

As duas funções simuladas são substituídas por chamadas reais:

| Antes (simulado) | Depois (produção) |
|---|---|
| `_generate_fake_token_id()` | Lê o `tokenId` emitido pelo evento `ActionMinted` do receipt |
| `_generate_fake_tx_hash()` | Usa o `transactionHash` do receipt retornado pelo RPC |

O restante do fluxo (geração de metadata, upload para Cloudinary, criação do registro `NFT` no Postgres, crédito de pontos) permanece **idêntico**.

### 6.2 Variáveis de ambiente necessárias

```env
# Hoje ignoradas, em produção obrigatórias
WEB3_PROVIDER_URL=https://polygon-amoy.g.alchemy.com/v2/<API_KEY>
NFT_CONTRACT_ADDRESS=0x...
REGISTRY_CONTRACT_ADDRESS=0x...
MINTER_PRIVATE_KEY=0x...   # Nunca commitar; usar Secrets Manager
ADMIN_WALLET=0x...
```

### 6.3 Dependências Python a adicionar

```
web3==6.15.0
eth-account==0.11.0
```

### 6.4 Conversão UUID → bytes32

O Postgres usa UUIDs (ex: `"550e8400-e29b-41d4-a716-446655440000"`). O Solidity usa `bytes32`. A conversão é:

```python
import uuid
from web3 import Web3

def uuid_to_bytes32(uuid_str: str) -> bytes:
    uid = uuid.UUID(str(uuid_str))
    return Web3.keccak(uid.bytes)  # 32 bytes determinísticos
```

Isso garante que o mesmo UUID sempre gera o mesmo `offchainId` na blockchain.

---

## 7. Segurança e Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| **Private key do minter vazada** | Alto — invasor pode mintar NFTs falsos | Usar AWS Secrets Manager ou Vault; rotacionar via `grantRole`/`revokeRole` sem re-deploy |
| **Reentrância no mint** | Médio | `_safeMint` do OpenZeppelin já protege via `_checkOnERC721Received` |
| **Duplo-mint do mesmo cidadão** | Alto — inflação de pontos | Mapeamento `offchainToToken` no contrato rejeita re-mint; verificado antes de qualquer estado do Postgres ser alterado |
| **Upgrade malicioso do NFT** | Alto — pode alterar lógica de posse | `UPGRADER_ROLE` separado do `MINTER_ROLE`; recomendado multisig (Gnosis Safe) para UPGRADER em mainnet |
| **Gas spike na Polygon** | Médio — txs falham se `maxFeePerGas` muito baixo | Backend usa `gas_price * 2` + 20% de buffer no estimate |
| **Batch muito grande → gas limit** | Médio — `mintLote` reverte o batch inteiro | Limite de 500 itens por chamada no contrato; backend divide em chunks se necessário |
| **Cidadão sem wallet — NFT pendente** | Baixo — experiência degradada | Pontos são creditados imediatamente no Postgres; NFT emitido retroativamente quando wallet for cadastrada |
| **Metadata URL quebrada** | Baixo — NFT aparece sem imagem em marketplaces | `tokenURI` pode ser atualizado via função admin no contrato (ERC721URIStorage permite isso) |

---

## 8. Roadmap de Evolução

```
📍 AGORA — Hackathon MVP
├── nft_service.py com mint simulado (estado atual)
└── Documento de arquitetura (este arquivo)

🔨 FASE 1 — Deploy Real
├── EcoProofNFT.sol deployado na Amoy (testnet)
├── EcoProofRegistry.sol deployado
├── blockchain_service.py substituindo o simulado
└── Testes end-to-end com carteiras reais

🚀 FASE 2 — Produção Polygon
├── Deploy na mainnet Polygon
├── Verificação dos contratos no Polygonscan
├── Wallet do minter em HSM ou KMS
└── Monitoramento de eventos via The Graph

🌱 FASE 3 — EcoPoints
├── EcoPoints.sol (ERC-20 Soulbound)
├── Leaderboard on-chain por tipo de ação
└── Integração do total_points do Postgres ↔ saldo ERC-20

🏛️ FASE 4 — Governança
├── DAO para aprovação de novos tipos de ação ambiental
├── Marketplace de recompensas com patrocinadores
└── Migração de metadata para IPFS/Filecoin
```

---

## Referências

- [OpenZeppelin ERC-721 Docs](https://docs.openzeppelin.com/contracts/5.x/erc721)
- [OpenZeppelin UUPS Upgrades](https://docs.openzeppelin.com/contracts/5.x/api/proxy#UUPSUpgradeable)
- [Polygon PoS Architecture](https://docs.polygon.technology/pos/architecture/)
- [ERC-721 Metadata Standard (OpenSea)](https://docs.opensea.io/docs/metadata-standards)
- [web3.py Documentation](https://web3py.readthedocs.io/)
- [EIP-4973 — Account-bound Tokens (Soulbound)](https://eips.ethereum.org/EIPS/eip-4973)
