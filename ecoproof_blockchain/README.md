# EcoProof — Contratos Blockchain

Guia para compilar, testar e fazer deploy dos contratos `EcoProofNFT` e `EcoProofRegistry` localmente e na testnet Sepolia.

---

## Pré-requisitos

- Node.js 18+
- Uma carteira com ETH de teste na Sepolia (faucet abaixo)
- Conta no [Alchemy](https://alchemy.com) ou [Infura](https://infura.io) para o RPC

---

## Instalação

```bash
cd blockchain
npm install
```

---

## Rodando localmente

### 1. Compilar os contratos

```bash
npm run compile
```

Os artifacts (ABI + bytecode) são gerados em `artifacts/contracts/`.

### 2. Subir o nó local

```bash
npm run node
```

Isso sobe um nó Hardhat em `http://127.0.0.1:8545` com 20 contas pré-financiadas. Deixe esse terminal aberto.

### 3. Fazer o deploy local

Em outro terminal:

```bash
npm run deploy:local
```

O script imprime os endereços dos dois contratos e já copia os ABIs para `app/abi/`. Anote os endereços — você vai precisar deles no `.env` do backend.

### 4. Rodar os testes

```bash
npm test
```

Os testes rodam numa rede Hardhat isolada (sem precisar do nó local rodando). Cada `it()` parte do zero.

Para ver o consumo de gas de cada função:

```bash
REPORT_GAS=true npm test
```

---

## Deploy na Sepolia

### 1. Conseguir ETH de teste

- [Alchemy Sepolia Faucet](https://sepoliafaucet.com) — 0.5 ETH/dia
- [Infura Sepolia Faucet](https://www.infura.io/faucet/sepolia) — requer conta

### 2. Preencher o `.env`

```env
WEB3_PROVIDER_URL=https://eth-sepolia.g.alchemy.com/v2/SUA_API_KEY
MINTER_PRIVATE_KEY=0x_sua_chave_privada
ADMIN_WALLET=0x_seu_endereco
ETHERSCAN_API_KEY=sua_api_key
```

### 3. Fazer o deploy

```bash
npm run deploy:sepolia
```

O script vai imprimir algo assim:

```
✅ EcoProofRegistry: 0xABC...
✅ EcoProofNFT (proxy): 0xDEF...
   EcoProofNFT (implementation): 0x123...

══════════════════════════════════════
  Copie as linhas abaixo para o .env do backend:
══════════════════════════════════════
NFT_CONTRACT_ADDRESS=0xDEF...
REGISTRY_CONTRACT_ADDRESS=0xABC...
```

Copie esses dois endereços para o `.env` do backend FastAPI.

### 4. Verificar os contratos no Etherscan (opcional)

Após o deploy, verifique para que o código-fonte fique público:

```bash
npx hardhat verify --network sepolia <REGISTRY_ADDRESS> <ADMIN_WALLET> <MINTER_WALLET>
```

O proxy do NFT é verificado automaticamente pelo plugin `@openzeppelin/hardhat-upgrades`.

Os contratos ficam visíveis em: `https://sepolia.etherscan.io/address/<ENDERECO>`

---

## Estrutura de arquivos

```
blockchain/
├── contracts/
│   ├── EcoProofNFT.sol          # ERC-721 UUPS — mint individual e em lote
│   └── EcoProofRegistry.sol     # Âncora imutável de hashes das fotos
├── scripts/
│   └── deploy.js                # Deploy dos dois contratos + copia ABIs
├── test/
│   ├── EcoProofNFT.test.js      # Testes do NFT
│   └── EcoProofRegistry.test.js # Testes do Registry
├── hardhat.config.js
├── package.json
└── .env.example
```

---

## Fluxo de atualização do NFT (UUPS)

O `EcoProofNFT` usa proxy UUPS, então pode ser atualizado sem perder o histórico de tokens. Para fazer upgrade:

```bash
# 1. Implante a nova implementação e atualize o proxy
npx hardhat run scripts/upgrade.js --network sepolia
```

> Só a carteira com `UPGRADER_ROLE` pode executar o upgrade. Em produção, use uma multisig (Gnosis Safe).