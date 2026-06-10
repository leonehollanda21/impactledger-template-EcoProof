# 🔍 EcoProof — Artefatos Web3

Bem-vindo à pasta de artefatos do **EcoProof**, uma solução desenvolvida para o desafio **ImpactLedger** no **Hackathon Web3 RESTIC 29**.

## 💻 Sobre o Módulo
Esta pasta reúne as evidências concretas da integração blockchain do EcoProof. Aqui estão registradas as provas públicas e verificáveis de que o sistema funciona de ponta a ponta: desde o cadastro de uma ação ambiental pelo cidadão até a emissão do NFT Soulbound na rede **Polygon Amoy**.

O conteúdo está organizado em duas frentes:

- **Demonstração Auditável** — links e prints de transações reais no PolygonScan, disponíveis publicamente para qualquer pessoa verificar.
- **Demonstração Funcional** — vídeo e/ou GIFs gravados com o sistema rodando, mostrando o fluxo completo da plataforma.

---

## 🔗 Demonstração Auditável

Todas as transações abaixo foram realizadas na **Sepolia Testnet** e estão publicamente verificáveis no explorador de blocos oficial.

> 🌐 Block explorer: https://amoy.polygonscan.com

### Contratos Deployados

| Contrato | Endereço (Proxy) | PolygonScan |
|----------|-----------------|-------------|
| `EcoProofNFT` | `0x...` | [Ver contrato]([https://sepolia.etherscan.io/address/0xc4B55DB7315FA16610cb4a517720ab08E028684E#code]) |
| `InstitutoNFT` | `0x...` | [Ver contrato](https://amoy.polygonscan.com/address/0x...) |
| `EducacaoNFT` | `0x...` | [Ver contrato](https://amoy.polygonscan.com/address/0x...) |
| `DenunciaNFT` | `0x...` | [Ver contrato](https://amoy.polygonscan.com/address/0x...) |
| `EcoProofRegistry` | `0x...` | [Ver contrato](https://amoy.polygonscan.com/address/0x...) |

> Os contratos foram verificados no PolygonScan — o código-fonte Solidity é público e auditável diretamente pelo explorador.

### Transações de Referência

| Ação | Transaction Hash | PolygonScan |
|------|-----------------|-------------|
| Mint NFT — Limpeza Individual | `0x...` | [Ver transação](https://amoy.polygonscan.com/tx/0x...) |
| Mint NFT — Evento/Mutirão | `0x...` | [Ver transação](https://amoy.polygonscan.com/tx/0x...) |
| Mint NFT — Denúncia Resolvida | `0x...` | [Ver transação](https://amoy.polygonscan.com/tx/0x...) |
| Mint NFT — Educação Ambiental | `0x...` | [Ver transação](https://amoy.polygonscan.com/tx/0x...) |
| Registry — Proof of Existence | `0x...` | [Ver transação](https://amoy.polygonscan.com/tx/0x...) |

### Prints

Os prints das transações e dos contratos verificados estão na subpasta `auditavel/`:

```
auditavel/
├── contratos/
│   ├── ecoproofnft_polygonscan.png
│   ├── institutonfts_polygonscan.png
│   ├── educacaonft_polygonscan.png
│   ├── denuncianft_polygonscan.png
│   └── registry_polygonscan.png
└── transacoes/
    ├── mint_limpeza.png
    ├── mint_evento.png
    ├── mint_denuncia.png
    ├── mint_educacao.png
    └── registry_proof.png
```

---

## 🎥 Demonstração Funcional

Os vídeos e GIFs da plataforma em funcionamento estão na subpasta `funcional/`.

### Fluxos gravados

| Fluxo | Arquivo |
|-------|---------|
| Cadastro e login de cidadão | `funcional/01_cadastro_login.mp4` |
| Registro de limpeza individual com validação por IA | `funcional/02_limpeza_individual.mp4` |
| Recebimento do NFT Soulbound após aprovação | `funcional/03_nft_emitido.mp4` |
| Instituto criando evento e emitindo NFTs em lote | `funcional/04_evento_mint_lote.mp4` |
| Cidadão realizando denúncia ambiental | `funcional/05_denuncia.mp4` |
| Admin resolvendo denúncia e emitindo NFT de fiscal | `funcional/06_admin_resolve_denuncia.mp4` |
| Verificação pública de denúncia on-chain | `funcional/07_verificacao_onchain.mp4` |

### Estrutura da pasta

```
funcional/
├── 01_cadastro_login.mp4
├── 02_limpeza_individual.mp4
├── 03_nft_emitido.mp4
├── 04_evento_mint_lote.mp4
├── 05_denuncia.mp4
├── 06_admin_resolve_denuncia.mp4
└── 07_verificacao_onchain.mp4
```

---

## Estrutura Completa da Pasta

```
artefatos_web3/
├── auditavel/
│   ├── contratos/          # Prints dos contratos verificados no PolygonScan
│   └── transacoes/         # Prints das transações de mint e registry
├── funcional/              # Vídeos e GIFs do sistema em funcionamento
└── README.md               # Este arquivo
```

---

*Este módulo é uma parte integrante da arquitetura do EcoProof, concebido a partir do [Template Oficial do ImpactLedger](https://github.com/Web3irede/impactledger-template).*  
*Uso de IA para ajuda no código, porém tudo revisado e devidamente alterado pelos programadores.*
