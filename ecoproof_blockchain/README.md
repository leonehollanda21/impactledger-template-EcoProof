# EcoProof — Contratos Blockchain (Polygon Amoy)

Guia para compilar, testar e fazer deploy do ecossistema de contratos do EcoProof (`EcoProofNFT`, `InstitutoNFT`, `EducacaoNFT` e `EcoProofRegistry`) localmente e na testnet oficial da Polygon (Amoy).

> **Aviso de Arquitetura ESG:** Este projeto utiliza a rede **Polygon** (Testnet Amoy para homologação e Mainnet para produção) devido ao seu baixo custo de transação (gás em centavos) e seu compromisso nativo com a neutralidade de carbono (Proof of Stake), alinhando a infraestrutura técnica com o propósito de impacto ambiental do sistema.

-----

## Pré-requisitos

- Node.js 18+
- Uma carteira (MetaMask) com **POL** de teste na rede Polygon Amoy (faucets abaixo)
- Conta no [Alchemy](https://alchemy.com) configurada para a rede Polygon Amoy
- Conta no [PolygonScan](https://polygonscan.com/) para gerar a API Key de verificação

-----

## Instalação

```bash
cd blockchain
npm install
```

-----

## Rodando localmente

### 1. Compilar os contratos

```bash
npx hardhat compile
```

Os artifacts (ABI + bytecode) são gerados em `artifacts/contracts/`.

### 2. Subir o nó local

```bash
npx hardhat node
```

Isso sobe um nó Hardhat em `http://127.0.0.1:8545` com 20 contas pré-financiadas. Deixe esse terminal aberto.

### 3. Fazer o deploy local

Em outro terminal:

```bash
npx hardhat run scripts/deploy.js --network localhost
```

O script imprime os endereços dos quatro contratos e já exporta automaticamente as ABIs para a pasta do backend (`app/abi/`). Anote os endereços.

### 4. Rodar os testes

```bash
npx hardhat test
```

Os testes rodam numa rede Hardhat isolada. Cada `it()` parte do zero, validando a máquina de estados, regras de Soulbound (EIP-5192) e a lógica de Merkle Trees.

Para ver o consumo de gás de cada função:

```bash
REPORT_GAS=true npx hardhat test
```

-----

## Deploy na Polygon Amoy (Testnet Oficial)

### 1. Conseguir POL de teste (Gás)

- [Alchemy Polygon Amoy Faucet](https://www.alchemy.com/faucets/polygon-amoy) — Requer conta no Alchemy.
- [Polygon Faucet Oficial](https://faucet.polygon.technology/) — Selecione “Polygon Amoy” e “POL”.

### 2. Preencher o `.env`

Crie um arquivo `.env` na raiz da pasta `blockchain` com as chaves abaixo:

```env
# URL do Alchemy para a Polygon Amoy
AMOY_RPC_URL="https://polygon-amoy.g.alchemy.com/v2/SUA_API_KEY"

# Chave privada da carteira MetaMask de DEV (sem o 0x)
PRIVATE_KEY="sua_chave_privada_aqui"

# Chave de API do Polygonscan para verificação do código
POLYGONSCAN_API_KEY="sua_api_key_aqui"
```

### 3. Fazer o deploy

```bash
npx hardhat run scripts/deploy.js --network polygonAmoy
```

O script vai compilar e enviar as transações para a Polygon, imprimindo o seguinte resultado:

```
✅ EcoProofRegistry deployed at: 0xABC...

✅ EcoProofNFT Proxy:            0xDEF...
   Implementation:               0x123...

✅ InstitutoNFT Proxy:           0xGHI...
   Implementation:               0x456...

✅ EducacaoNFT Proxy:            0xJKL...
   Implementation:               0x789...

══════════════════════════════════════════════════
   Deployment Complete — Backend .env values:     
══════════════════════════════════════════════════
NFT_CONTRACT_ADDRESS=0xDEF...
INSTITUTO_NFT_CONTRACT_ADDRESS=0xGHI...
EDUCACAO_NFT_CONTRACT_ADDRESS=0xJKL...
REGISTRY_CONTRACT_ADDRESS=0xABC...
BLOCKCHAIN_ENABLED=true
```

Copie esses endereços para o `.env` do backend.

### 4. Verificar os contratos no PolygonScan (Transparência)

Após o deploy, verifique o contrato principal para que o código-fonte fique público e auditável para os jurados:

```bash
npx hardhat verify --network polygonAmoy <REGISTRY_CONTRACT_ADDRESS>
```

🔗 **Acompanhamento Público (Block Explorer):**  
Os contratos, transações e códigos-fonte ficarão publicamente visíveis no explorador oficial da testnet:  
`https://amoy.polygonscan.com/address/<ENDERECO_DO_CONTRATO>`

-----

## Estrutura de Arquivos

```
blockchain/
├── contracts/
│   ├── EcoProofNFT.sol          # ECOI — Mint individual e adoções (Soulbound)
│   ├── InstitutoNFT.sol         # ECOE — Mint institucional em lote via Merkle Tree (Soulbound)
│   ├── EducacaoNFT.sol          # ECED — Mint para impacto educacional (Soulbound)
│   └── EcoProofRegistry.sol     # Âncora imutável de hashes (Proof of Existence) e Máquina de Estados
├── scripts/
│   └── deploy.js                # Orquestração do deploy dos 4 contratos e exportação de ABIs
├── test/
│   ├── EcoProofNFT.test.js      # Bateria de testes dos NFTs (EIP-5192, RBAC, etc)
│   └── EcoProofRegistry.test.js # Bateria de testes do Registry (Idempotência, hashes)
├── hardhat.config.js            # Configurações de rede, compilação (viaIR) e chaves
├── package.json
└── .env                         # Chaves de infraestrutura (Não enviar ao GitHub)
```

-----

## Fluxo de Atualização (Proxy UUPS)

Os contratos de NFT (`EcoProofNFT`, `InstitutoNFT`, `EducacaoNFT`) utilizam a arquitetura **Proxy UUPS**. Isso significa que as regras de negócio podem ser atualizadas no futuro sem que a coleção perca o histórico de tokens ou os donos originais.

Para fazer upgrade:

```bash
# 1. Desenvolva o contrato V2, implante a nova implementação e atualize o ponteiro do proxy
npx hardhat run scripts/upgrade.js --network polygonAmoy
```

> **Nota de Segurança:** Apenas a carteira com a `UPGRADER_ROLE` (definida no momento do deploy) pode executar uma atualização do ecossistema. Em ambiente de produção (Mainnet), essa função deve ser delegada a um contrato Multisig (ex: Gnosis Safe).
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
