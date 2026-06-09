# 🌿 EcoProof — Certificação de Ações Ambientais em Blockchain

O **EcoProof** é uma plataforma descentralizada de incentivo, registro e auditoria de ações socioambientais (coletas de lixo, adorações de áreas verdes, educação ambiental e denúncias de infrações). Ele foi construído no modelo **Dual-Ledger** para unir a flexibilidade de um backend moderno com a auditabilidade e transparência da rede **Polygon**.

Esta é a pasta principal unificada com as três partes do projeto:
1. **Blockchain**: Smart contracts desenvolvidos com Solidity e Hardhat.
2. **Middleware (Backend)**: API construída com Python + FastAPI que orquestra a inteligência artificial (Gemini) e a integração com a blockchain.
3. **Frontend**: Aplicação interativa em Vue 3 + Vite para o Cidadão, Instituto (ONG) e Administrador.

---

## 📁 Estrutura do Repositório

O projeto está organizado nas seguintes pastas:

*   **`ecoproof_blockchain/`**: Contratos inteligentes Solidity, testes automatizados e scripts de deploy Hardhat.
*   **`ecoproof_middleware/`**: Backend FastAPI. Contém a lógica de negócio, persistência no banco relacional PostgreSQL, processamento de imagens com Google Gemini AI, upload para Cloudinary e chamadas RPC para a blockchain via Web3.py.
*   **`EcoProof_frontend/`**: Painel do usuário e interface web do projeto desenvolvida em Vue 3.

---

## ⚙️ Como Executar o Projeto Inteiro

Para rodar o projeto localmente por completo, você precisará de **3 terminais abertos** simultaneamente.

---

### 🌐 Passo 1: Inicializar a Blockchain Local (Terminal 1)

## Pré-requisitos

- Node.js 18+
- Uma carteira (MetaMask) com *POL* de teste na rede Polygon Amoy (faucets abaixo)
- Conta no [Alchemy](https://alchemy.com) configurada para a rede Polygon Amoy
- Conta no [PolygonScan](https://polygonscan.com/) para gerar a API Key de verificação

O smart contract precisa de uma rede para rodar. Usaremos a rede de testes local fornecida pelo Hardhat.

1.  Abra o primeiro terminal e acesse a pasta da blockchain:
    ```bash
    cd ecoproof_blockchain
    ```
2.  Instale as dependências:
    ```bash
    npm install
    ```
3.  Crie a configuração de ambiente para a blockchain:
    ```bash
    cp .env.example .env
    ```
4.  Inicie o nó local (simulador de blockchain):
    ```bash
    npx hardhat node
    ```
    *Deixe este terminal aberto rodando a rede.*

---

### 📜 Passo 2: Fazer Deploy dos Smart Contracts (Terminal 2 Temporário)

Com a rede local rodando no Terminal 1, precisamos compilar e publicar os contratos.

1.  Abra um terminal temporário e acesse a pasta da blockchain:
    ```bash
    cd ecoproof_blockchain
    ```
2.  Faça o deploy dos 5 contratos na rede local:
    ```bash
    npx hardhat run scripts/deploy.js --network localhost
    ```
3.  O console imprimirá os endereços de deploy dos contratos:
    *   `EcoProofRegistry`
    *   `EcoProofNFT` (Proxy)
    *   `InstitutoNFT` (Proxy)
    *   `EducacaoNFT` (Proxy)
    *   `DenunciaNFT` (Proxy)
    
    **Guarde estes endereços!** Você precisará configurá-los no arquivo `.env` do backend (middleware).

---

### 🐍 Passo 3: Executar o Middleware/Backend (Terminal 2)

O backend do EcoProof gerencia o banco de dados PostgreSQL, a validação de imagens com IA e interage com os contratos inteligentes criados no passo anterior.

1.  Acesse a pasta do middleware:
    ```bash
    cd ecoproof_middleware
    ```
2.  Crie e ative um ambiente virtual Python:
    *   **Windows (PowerShell):**
        ```powershell
        python -m venv venv
        .\venv\Scripts\Activate.ps1
        ```
    *   **Linux/macOS:**
        ```bash
        python -m venv venv
        source venv/bin/activate
        ```
3.  Instale as dependências Python:
    ```bash
    pip install -r requirements.txt
    ```
4.  Crie o arquivo de configuração `.env` na pasta `ecoproof_middleware/`:
    ```bash
    cp .env.example .env
    ```
5.  Abra o arquivo `.env` gerado e configure:
    *   **`DATABASE_URL`** e **`DATABASE_URL_SYNC`**: Credenciais de conexão do seu PostgreSQL local.
    *   **API Keys** (opcionais para testes locais simulação): `CLOUDINARY_*` e `GEMINI_API_KEY`.
    *   **Endereços dos contratos**: Atualize `NFT_CONTRACT_ADDRESS`, `INSTITUTO_NFT_CONTRACT_ADDRESS`, etc., com os endereços de deploy gerados no **Passo 2**.
    *   **`BLOCKCHAIN_ENABLED`**: Altere para `true` para integrar com a blockchain local.
    *   **`MINTER_PRIVATE_KEY`**: Chave privada de uma das contas geradas pelo Hardhat no Terminal 1 (geralmente a primeira chave listada no log do nó local).
6.  Execute as migrações do banco de dados:
    ```bash
    alembic upgrade head
    ```
7.  Inicie a API FastAPI:
    ```bash
    uvicorn app.main:app --reload
    ```
    *A API estará ativa em `http://localhost:8000`. Você pode testar e ler sobre todos os endpoints e payloads abrindo o Swagger da documentação em `http://localhost:8000/docs`.*

---

### 💻 Passo 4: Executar o Frontend Vue 3 (Terminal 3)

O frontend interage com a API do middleware para realizar autenticação, uploads de imagens, e renderizar o dashboard interativo.

1.  Abra o terceiro terminal e acesse a pasta do frontend:
    ```bash
    cd EcoProof_frontend
    ```
2.  Instale as dependências:
    ```bash
    npm install
    ```
3.  Execute o servidor de desenvolvimento do Vite:
    ```bash
    npm run dev
    ```
4.  Acesse a aplicação no navegador em `http://localhost:5173`.

---

## 🧪 Rodando os Testes Automatizados

### Smart Contracts (Solidity)
Você pode executar toda a suíte de testes unitários que valida a segurança de autoria (roles), cunhagem (mints), registro de duplicidade e regras de Soulbound rodando na pasta da blockchain:
```bash
cd ecoproof_blockchain
npx hardhat test
```

### Middleware (Python)
Para testar a lógica do backend FastAPI e os fluxos de validação de dados:
```bash
cd ecoproof_middleware
pytest
```

---

## 📖 Documentações Complementares
*   Para detalhes das rotas, payloads de requisição e respostas da API, consulte: [API Docs (ecoproof_middleware/API_DOCS.md)](file:///E:/codes/hackathon_web3_fork/impactledger-template-EcoProof/ecoproof_middleware/API_DOCS.md)
*   Para detalhes do fluxo on-chain, eventos Solidity e estrutura de segurança, consulte: [Blockchain Architecture (ecoproof_middleware/BLOCKCHAIN_ARCHITECTURE.md)](file:///E:/codes/hackathon_web3_fork/impactledger-template-EcoProof/ecoproof_middleware/BLOCKCHAIN_ARCHITECTURE.md)
