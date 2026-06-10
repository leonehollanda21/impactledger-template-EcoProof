# 🔍 EcoProof — Artefatos Web3

Bem-vindo à pasta de artefatos do **EcoProof**, uma solução desenvolvida para o desafio **ImpactLedger** no **Hackathon Web3 RESTIC 29**.

## 💻 Sobre o Módulo
Esta pasta reúne as evidências concretas da integração blockchain do EcoProof. Aqui estão registradas as provas públicas e verificáveis de que o sistema funciona de ponta a ponta: desde o cadastro de uma ação ambiental pelo cidadão até a emissão do NFT Soulbound na rede **Ethereum Sepolia**. 

Link de Acesso : https://eco-proof-blond.vercel.app

O conteúdo está organizado em duas frentes:

- **Demonstração Auditável** — links e prints de transações reais no Etherscan, disponíveis publicamente para qualquer pessoa verificar.
- **Demonstração Funcional** — vídeo e/ou GIFs gravados com o sistema rodando, mostrando o fluxo completo da plataforma.

> ⚠️ **Nota sobre a escolha da rede:** O deploy dos contratos foi realizado na **Ethereum Sepolia Testnet** em vez da Polygon Amoy originalmente planejada. A migração ocorreu por indisponibilidade de fundos de teste (POL) na Amoy para a realização das demonstrações no prazo do hackathon. A Sepolia oferece faucets mais acessíveis e estáveis para ETH de teste, viabilizando o deploy completo dos 5 contratos sem custo. A arquitetura do código permanece idêntica — apenas o `CHAIN_ID` e o `WEB3_PROVIDER_URL` foram atualizados no backend.

---

## 🔗 Demonstração Auditável

Todos os contratos abaixo foram deployados na **Ethereum Sepolia Testnet** e estão publicamente verificáveis no Etherscan com código-fonte Solidity publicado.

> 🌐 Block explorer: https://sepolia.etherscan.io

### Contratos Deployados

| # | Contrato | Endereço (Proxy) | Etherscan |
|---|----------|-----------------|-----------|
| 1 | `EcoProofRegistry` | `0xc4B55DB7315FA16610cb4a517720ab08E028684E` | [Ver contrato](https://sepolia.etherscan.io/address/0xc4B55DB7315FA16610cb4a517720ab08E028684E#code) |
| 2 | `EcoProofNFT` | `0x9d57C629e6c4fb4cCB7769A246275498C0524245` | [Ver contrato](https://sepolia.etherscan.io/address/0x9d57C629e6c4fb4cCB7769A246275498C0524245#code) |
| 3 | `InstitutoNFT` | `0xD1Fe82Cfcb2b02B25C18B968c8a5ABF123D4b77E` | [Ver contrato](https://sepolia.etherscan.io/address/0xD1Fe82Cfcb2b02B25C18B968c8a5ABF123D4b77E#code) |
| 4 | `EducacaoNFT` | `0x757d474931b6eF4aeE988BD121359b3c9c4695e9` | [Ver contrato](https://sepolia.etherscan.io/address/0x757d474931b6eF4aeE988BD121359b3c9c4695e9#code) |
| 5 | `DenunciaNFT` | `0x9A4419888CEa4B43134f4AF3580f63fEC850E86f` | [Ver contrato](https://sepolia.etherscan.io/address/0x9A4419888CEa4B43134f4AF3580f63fEC850E86f#code) |

> Os contratos foram verificados no Etherscan — o código-fonte Solidity é público e auditável diretamente pelo explorador.

### Transações de Referência

| Ação | Transaction Hash | Etherscan |
|------|-----------------|-----------|
| Mint NFT — Limpeza Individual | `0x...` | [Ver transação](https://sepolia.etherscan.io/tx/0x...) |
| Mint NFT — Evento/Mutirão | `0x...` | [Ver transação](https://sepolia.etherscan.io/tx/0x...) |
| Mint NFT — Denúncia Resolvida | `0x...` | [Ver transação](https://sepolia.etherscan.io/tx/0x...) |
| Mint NFT — Educação Ambiental | `0x...` | [Ver transação](https://sepolia.etherscan.io/tx/0x...) |
| Registry — Proof of Existence | `0x...` | [Ver transação](https://sepolia.etherscan.io/tx/0x...) |

---

## 🎥 Demonstração Funcional

Os vídeos e GIFs da plataforma em funcionamento estão na subpasta `funcional/`.

---

*Este módulo é uma parte integrante da arquitetura do EcoProof, concebido a partir do [Template Oficial do ImpactLedger](https://github.com/Web3irede/impactledger-template).*  
*Uso de IA para ajuda no código, porém tudo revisado e devidamente alterado pelos programadores.*
