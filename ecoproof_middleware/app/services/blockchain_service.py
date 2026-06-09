"""
app/services/blockchain_service.py
───────────────────────────────────
Serviço de integração real com a blockchain via Web3.py.

Cobre:
  - Mint de NFTs individuais (EcoProofNFT.mintLimpeza)
  - Mint de NFTs de evento (EcoProofNFT.mintEvento)
  - Mint em lote (EcoProofNFT.mintBatch)
  - Registro de provas (EcoProofRegistry.registerLimpeza/registerParticipacao)
  - Verificação on-chain (verifyPhoto, verifyMetadata)

Fallback: Se BLOCKCHAIN_ENABLED=false ou provider indisponível, usa modo simulado
com log de aviso. Isso permite desenvolvimento local sem blockchain real.
"""
import hashlib
import json
import logging
import os
import secrets
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Tentativa de import do web3 ──────────────────────────────────────────────
try:
    from web3 import Web3
    from web3.middleware import ExtraDataToPOAMiddleware
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    logger.warning(
        "⚠️  web3 não instalado. Blockchain service rodará em modo SIMULADO. "
        "Instale com: pip install web3"
    )


# ── Helpers ──────────────────────────────────────────────────────────────────

def _load_abi(contract_name: str) -> list:
    """Carrega ABI de um contrato do diretório app/abi/."""
    abi_dir = Path(__file__).parent.parent / "abi"
    abi_file = abi_dir / f"{contract_name}.json"
    
    if not abi_file.exists():
        logger.warning("ABI não encontrada: %s", abi_file)
        return []
    
    with open(abi_file, "r") as f:
        data = json.load(f)
    
    return data.get("abi", data)


def compute_keccak256(data: bytes) -> str:
    """Calcula keccak256 hash e retorna como hex string 0x-prefixed."""
    if WEB3_AVAILABLE:
        return Web3.keccak(data).hex()
    # Fallback usando hashlib (menos preciso, mas funcional para dev)
    return "0x" + hashlib.sha256(data).hexdigest()


def uuid_to_bytes32(uuid_str: str) -> bytes:
    """Converte UUID string para bytes32 via keccak256."""
    if WEB3_AVAILABLE:
        return Web3.keccak(text=uuid_str)
    return bytes.fromhex(hashlib.sha256(uuid_str.encode()).hexdigest())


# ── Simulação (fallback) ────────────────────────────────────────────────────

def _generate_fake_token_id() -> str:
    """Gera um token_id numérico simulado."""
    return str(secrets.randbelow(9_999_998) + 1)


def _generate_fake_tx_hash() -> str:
    """Gera um transaction hash simulado no formato Ethereum."""
    return "0x" + secrets.token_hex(32)


# ── Action Type mapping ─────────────────────────────────────────────────────

ACTION_TYPE_MAP = {
    "lixo_rua": 0,
    "praia": 1,
    "corrego": 2,
    "queimada": 3,
    "outro": 4,
}

EDUCACAO_TYPE_MAP = {
    "palestra":          0,
    "oficina":           1,
    "roda_conversa":     2,
    "mutirao_educativo": 3,
    "outro":             4,
}

ISSUED_BY_MAP = { "admin": 0, "instituto": 1 }


class BlockchainService:
    """
    Serviço para interação com smart contracts EcoProof.
    
    Modos:
    - REAL: Envia transações reais para a blockchain
    - SIMULADO: Gera IDs e hashes fake (para desenvolvimento local)
    """

    def __init__(self):
        self.enabled = getattr(settings, "BLOCKCHAIN_ENABLED", False)
        self.w3: Optional["Web3"] = None
        self.account = None
        self.nft_contract = None
        self.instituto_nft_contract = None
        self.registry_contract = None
        self.denuncia_nft_contract = None    # DenunciaNFT.sol (ECFD)
        self.educacao_nft_contract = None    # EducacaoNFT.sol (ECED)
        self._nonce: Optional[int] = None

        if self.enabled and WEB3_AVAILABLE:
            self._initialize_web3()
        elif self.enabled and not WEB3_AVAILABLE:
            logger.error(
                "❌ BLOCKCHAIN_ENABLED=true mas web3 não está instalado! "
                "Rodando em modo simulado."
            )
            self.enabled = False
        else:
            logger.info(
                "🔧 Blockchain service em modo SIMULADO. "
                "Defina BLOCKCHAIN_ENABLED=true no .env para usar blockchain real."
            )

    def _initialize_web3(self):
        """Inicializa conexão Web3 e carrega contratos."""
        try:
            provider_url = settings.WEB3_PROVIDER_URL
            self.w3 = Web3(Web3.HTTPProvider(provider_url))

            # Middleware para redes PoA (Polygon)
            self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

            if not self.w3.is_connected():
                logger.error("❌ Não foi possível conectar ao provider: %s", provider_url)
                self.enabled = False
                return

            # Configurar account do minter
            private_key = settings.MINTER_PRIVATE_KEY
            if not private_key or private_key == "your-minter-wallet-private-key":
                logger.error(
                    "❌ MINTER_PRIVATE_KEY não configurada. "
                    "Blockchain service rodando em modo SIMULADO."
                )
                self.enabled = False
                return

            self.account = self.w3.eth.account.from_key(private_key)
            logger.info("✅ Blockchain conectado: %s", provider_url)
            logger.info("   Minter wallet: %s", self.account.address)

            # Carregar contratos
            self._load_contracts()

        except Exception as e:
            logger.error("❌ Erro ao inicializar Web3: %s", e)
            self.enabled = False

    def _load_contracts(self):
        """Carrega instâncias dos contratos com ABIs."""
        # EcoProofNFT
        nft_address = getattr(settings, "NFT_CONTRACT_ADDRESS", "")
        if nft_address and nft_address != "0x" + "0" * 40:
            nft_abi = _load_abi("EcoProofNFT")
            if nft_abi:
                self.nft_contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address(nft_address),
                    abi=nft_abi,
                )
                logger.info("   EcoProofNFT: %s", nft_address)

        # InstitutoNFT
        instituto_address = getattr(settings, "INSTITUTO_NFT_CONTRACT_ADDRESS", "")
        if instituto_address and instituto_address != "0x" + "0" * 40:
            instituto_abi = _load_abi("InstitutoNFT")
            if instituto_abi:
                self.instituto_nft_contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address(instituto_address),
                    abi=instituto_abi,
                )
                logger.info("   InstitutoNFT: %s", instituto_address)

        # EcoProofRegistry
        registry_address = getattr(settings, "REGISTRY_ADDRESS", "") or getattr(settings, "REGISTRY_CONTRACT_ADDRESS", "")
        if registry_address and registry_address != "0x" + "0" * 40:
            abi_registry = []
            for path in [
                "blockchain/artifacts/contracts/EcoProofRegistry.sol/EcoProofRegistry.json",
                "../ecoproof_blockchain/artifacts/contracts/EcoProofRegistry.sol/EcoProofRegistry.json",
                "app/abi/EcoProofRegistry.json"
            ]:
                try:
                    if "app/abi/" in path:
                        abi_registry = _load_abi("EcoProofRegistry")
                        if abi_registry:
                            break
                    else:
                        with open(path) as f:
                            data = json.load(f)
                            abi_registry = data.get("abi", data)
                            break
                except Exception:
                    continue
            
            if not abi_registry:
                abi_registry = _load_abi("EcoProofRegistry")

            if abi_registry:
                self.registry_contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address(registry_address),
                    abi=abi_registry,
                )
                logger.info("   EcoProofRegistry: %s", registry_address)

        # DenunciaNFT (ECFD) — contrato dedicado a denúncias ambientais verificadas
        denuncia_address = getattr(settings, "DENUNCIA_NFT_ADDRESS", "")
        if denuncia_address and denuncia_address != "0x" + "0" * 40:
            denuncia_abi = _load_abi("DenunciaNFT")
            if denuncia_abi:
                self.denuncia_nft_contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address(denuncia_address),
                    abi=denuncia_abi,
                )
                logger.info("   DenunciaNFT: %s", denuncia_address)
            else:
                logger.warning(
                    "ABI do DenunciaNFT não encontrada em app/abi/DenunciaNFT.json. "
                    "Execute: npx hardhat compile && copie o ABI gerado."
                )

        # EducacaoNFT (ECED) — contrato dedicado a ações de educação ambiental
        educacao_address = getattr(settings, "EDUCACAO_NFT_ADDRESS", "")
        if educacao_address and educacao_address != "0x" + "0" * 40:
            abi_educacao = []
            for path in [
                "blockchain/artifacts/contracts/EducacaoNFT.sol/EducacaoNFT.json",
                "../ecoproof_blockchain/artifacts/contracts/EducacaoNFT.sol/EducacaoNFT.json",
                "app/abi/EducacaoNFT.json"
            ]:
                try:
                    if "app/abi/" in path:
                        abi_educacao = _load_abi("EducacaoNFT")
                        if abi_educacao:
                            break
                    else:
                        with open(path) as f:
                            data = json.load(f)
                            abi_educacao = data.get("abi", data)
                            break
                except Exception:
                    continue

            if not abi_educacao:
                abi_educacao = _load_abi("EducacaoNFT")

            if abi_educacao:
                self.educacao_nft_contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address(educacao_address),
                    abi=abi_educacao,
                )
                logger.info("   EducacaoNFT: %s", educacao_address)
            else:
                logger.warning("Não foi possível carregar ABI do EducacaoNFT.")

    def _get_nonce(self) -> int:
        """Obtém o próximo nonce para a conta minter."""
        return self.w3.eth.get_transaction_count(self.account.address)

    def _send_transaction(self, tx_func) -> tuple[str, dict]:
        """
        Constrói, assina e envia uma transação.
        
        Returns:
            Tuple (tx_hash_hex, receipt_dict)
        """
        chain_id = getattr(settings, "CHAIN_ID", 11155111)
        nonce = self._get_nonce()

        tx = tx_func.build_transaction({
            "from": self.account.address,
            "nonce": nonce,
            "chainId": chain_id,
            "gas": 500_000,  # Será estimado abaixo
        })

        # Estimar gas
        try:
            estimated_gas = self.w3.eth.estimate_gas(tx)
            tx["gas"] = int(estimated_gas * 1.2)  # 20% margem
        except Exception as e:
            logger.warning("Não foi possível estimar gas: %s. Usando 500k.", e)

        # Assinar e enviar
        signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        
        logger.info("Transação enviada: %s", tx_hash.hex())
        
        # Aguardar confirmação
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        if receipt["status"] != 1:
            logger.error("❌ Transação falhou: %s", tx_hash.hex())
            raise RuntimeError(f"Transação blockchain falhou: {tx_hash.hex()}")
        
        logger.info("✅ Transação confirmada: %s (gas: %d)", tx_hash.hex(), receipt["gasUsed"])
        return tx_hash.hex(), dict(receipt)

    # ═════════════════════════════════════════════════════════════════════════
    #  NFT Minting
    # ═════════════════════════════════════════════════════════════════════════

    async def mint_limpeza(
        self,
        to_address: str,
        uri: str,
        offchain_id: str,
        action_type: str,
        ai_score: int,
    ) -> tuple[str, str]:
        """
        Minta NFT de limpeza individual no contrato EcoProofNFT.
        
        Returns:
            Tuple (token_id, tx_hash)
        """
        if not self.enabled or not self.nft_contract:
            logger.info("[SIMULADO] mint_limpeza — offchain_id=%s", offchain_id)
            return _generate_fake_token_id(), _generate_fake_tx_hash()

        offchain_bytes = uuid_to_bytes32(offchain_id)
        action_enum = ACTION_TYPE_MAP.get(action_type, 4)

        tx_func = self.nft_contract.functions.mintLimpeza(
            Web3.to_checksum_address(to_address),
            uri,
            offchain_bytes,
            action_enum,
            ai_score,
        )

        tx_hash, receipt = self._send_transaction(tx_func)

        # Extrair tokenId do evento ActionMinted
        token_id = self._extract_token_id_from_receipt(receipt, "ActionMinted")
        
        logger.info(
            "NFT limpeza mintado — token_id=%s tx_hash=%s",
            token_id, tx_hash,
        )
        return str(token_id), tx_hash

    async def mint_evento(
        self,
        to_address: str,
        uri: str,
        offchain_id: str,
        action_type: str,
        institution_wallet: str,
    ) -> tuple[str, str]:
        """
        Minta NFT de evento no contrato EcoProofNFT.
        
        Returns:
            Tuple (token_id, tx_hash)
        """
        if not self.enabled or not self.nft_contract:
            logger.info("[SIMULADO] mint_evento — offchain_id=%s", offchain_id)
            return _generate_fake_token_id(), _generate_fake_tx_hash()

        offchain_bytes = uuid_to_bytes32(offchain_id)
        action_enum = ACTION_TYPE_MAP.get(action_type, 4)

        tx_func = self.nft_contract.functions.mintEvento(
            Web3.to_checksum_address(to_address),
            uri,
            offchain_bytes,
            action_enum,
            Web3.to_checksum_address(institution_wallet),
        )

        tx_hash, receipt = self._send_transaction(tx_func)
        token_id = self._extract_token_id_from_receipt(receipt, "ActionMinted")
        
        logger.info(
            "NFT evento mintado — token_id=%s tx_hash=%s",
            token_id, tx_hash,
        )
        return str(token_id), tx_hash

    async def mint_batch(
        self,
        params: list[dict],
        event_hash: str,
    ) -> tuple[list[str], str]:
        """
        Minta NFTs em lote no contrato EcoProofNFT.
        
        Args:
            params: Lista de dicts com {to, uri, offchain_id, action_type, institution_wallet}
            event_hash: Hash do evento (UUID do evento)
        
        Returns:
            Tuple (token_ids, tx_hash)
        """
        if not self.enabled or not self.nft_contract:
            logger.info("[SIMULADO] mint_batch — %d items", len(params))
            token_ids = [_generate_fake_token_id() for _ in params]
            tx_hash = _generate_fake_tx_hash()
            return token_ids, tx_hash

        batch_params = []
        for p in params:
            batch_params.append({
                "to": Web3.to_checksum_address(p["to"]),
                "uri": p["uri"],
                "offchainId": uuid_to_bytes32(p["offchain_id"]),
                "actionType": ACTION_TYPE_MAP.get(p["action_type"], 4),
                "institutionWallet": Web3.to_checksum_address(p["institution_wallet"]),
            })

        event_bytes = uuid_to_bytes32(event_hash)
        tx_func = self.nft_contract.functions.mintBatch(batch_params, event_bytes)

        tx_hash, receipt = self._send_transaction(tx_func)
        
        # Extrair todos os tokenIds dos eventos
        token_ids = self._extract_batch_token_ids(receipt)
        
        logger.info(
            "Batch mintado — %d tokens, tx_hash=%s",
            len(token_ids), tx_hash,
        )
        return [str(t) for t in token_ids], tx_hash

    # ═════════════════════════════════════════════════════════════════════════
    #  Registry (Proof of Existence)
    # ═════════════════════════════════════════════════════════════════════════

    async def register_limpeza_proof(
        self,
        offchain_id: str,
        photo_after_hash: str,
        photo_before_hash: str,
        metadata_hash: str,
        ai_score: int,
        action_type: str,
        aprovado: bool,
    ) -> Optional[str]:
        """
        Registra prova de limpeza no ValidationRegistry.
        
        Returns:
            tx_hash ou None em modo simulado.
        """
        if not self.enabled or not self.registry_contract:
            logger.info("[SIMULADO] register_limpeza_proof — offchain_id=%s", offchain_id)
            return _generate_fake_tx_hash()

        offchain_bytes = uuid_to_bytes32(offchain_id)
        action_enum = ACTION_TYPE_MAP.get(action_type, 4)

        # Converter hex strings para bytes32
        after_bytes = bytes.fromhex(photo_after_hash.replace("0x", ""))
        before_bytes = bytes.fromhex(photo_before_hash.replace("0x", ""))
        meta_bytes = bytes.fromhex(metadata_hash.replace("0x", ""))

        tx_func = self.registry_contract.functions.registerLimpeza(
            offchain_bytes,
            after_bytes,
            before_bytes,
            meta_bytes,
            ai_score,
            action_enum,
            aprovado,
        )

        tx_hash, _ = self._send_transaction(tx_func)
        logger.info("Proof registrado — offchain_id=%s tx=%s", offchain_id, tx_hash)
        return tx_hash

    async def register_participacao_proof(
        self,
        offchain_id: str,
        photo_hash: str,
        metadata_hash: str,
        action_type: str,
    ) -> Optional[str]:
        """Registra prova de participação em evento no Registry."""
        if not self.enabled or not self.registry_contract:
            logger.info("[SIMULADO] register_participacao_proof — offchain_id=%s", offchain_id)
            return _generate_fake_tx_hash()

        offchain_bytes = uuid_to_bytes32(offchain_id)
        action_enum = ACTION_TYPE_MAP.get(action_type, 4)
        photo_bytes = bytes.fromhex(photo_hash.replace("0x", ""))
        meta_bytes = bytes.fromhex(metadata_hash.replace("0x", ""))

        tx_func = self.registry_contract.functions.registerParticipacao(
            offchain_bytes,
            photo_bytes,
            meta_bytes,
            action_enum,
        )

        tx_hash, _ = self._send_transaction(tx_func)
        return tx_hash

    async def registrar_denuncia_blockchain(
        self,
        citizen_wallet: str,
        denuncia_id: str,
        foto_url: str,
        descricao: str,
    ) -> dict:
        """
        Chama DenunciaNFT.registrarDenuncia() — registra o problema on-chain.

        Esta chamada não minta NFT, apenas grava o proof de existência:
          - offchainId   = UUID da denúncia → bytes32
          - photoBeforeHash = keccak256(foto_url) → bytes32
          - description  = texto truncado em 200 chars (segurança de gas)

        Args:
            citizen_wallet: Endereço da wallet do cidadão.
            denuncia_id:    UUID string da denúncia no banco (ex: "550e8400-...").
            foto_url:       URL pública da foto do problema no Cloudinary.
            descricao:      Descrição textual do problema.

        Returns:
            dict com tx_hash, offchain_id_hex e block_number.

        Raises:
            ContractLogicError: Se o contrato rejeitar (AlreadyRegistered, InvalidAddress, etc.)
            RuntimeError: Se a transação falhar (status != 1).
        """
        if not self.enabled or not self.denuncia_nft_contract:
            logger.info("[SIMULADO] registrar_denuncia_blockchain — denuncia_id=%s", denuncia_id)
            offchain_hex = "0x" + uuid_to_bytes32(denuncia_id).hex()
            return {
                "tx_hash":         _generate_fake_tx_hash(),
                "offchain_id_hex": offchain_hex,
                "block_number":    0,
            }

        import uuid as _uuid

        # Conversões de tipo: Python → Solidity bytes32
        uid       = _uuid.UUID(denuncia_id)
        offchain  = uid.bytes.ljust(32, b"\x00")          # 16 bytes UUID + 16 zeros
        photo_bef = self.w3.keccak(text=foto_url)          # keccak256 da URL da foto
        checksum  = Web3.to_checksum_address(citizen_wallet)
        desc_trunc = descricao[:200]                       # limita gas

        tx_func = self.denuncia_nft_contract.functions.registrarDenuncia(
            checksum,
            offchain,
            photo_bef,
            desc_trunc,
        )

        tx_hash_hex, receipt = self._send_transaction(tx_func)
        logger.info(
            "DenunciaNFT.registrarDenuncia — denuncia_id=%s tx=%s bloco=%s",
            denuncia_id, tx_hash_hex, receipt["blockNumber"],
        )
        return {
            "tx_hash":         tx_hash_hex,
            "offchain_id_hex": "0x" + offchain.hex(),
            "block_number":    receipt["blockNumber"],
        }

    async def resolver_denuncia_blockchain(
        self,
        denuncia_id: str,
        foto_resolucao_url: str,
        metadata_uri: str,
    ) -> dict:
        """
        Chama DenunciaNFT.resolverDenuncia() — confirma resolução e minta o NFT Soulbound.

        Args:
            denuncia_id:        UUID string da denúncia (mesmo usado no registro).
            foto_resolucao_url: URL pública da foto de resolução no Cloudinary.
            metadata_uri:       URL do JSON ERC-721 no Cloudinary (gerado pelo nft_service).

        Returns:
            dict com tx_hash, token_id (str) e block_number.

        Raises:
            ContractLogicError: DenunciaNotRegistered, DenunciaAlreadyResolved, InvalidHash, InvalidURI.
            RuntimeError: Se a transação falhar.
        """
        if not self.enabled or not self.denuncia_nft_contract:
            logger.info("[SIMULADO] resolver_denuncia_blockchain — denuncia_id=%s", denuncia_id)
            fake_token = str(secrets.randbelow(9_999_998) + 1)
            return {
                "tx_hash":    _generate_fake_tx_hash(),
                "token_id":   fake_token,
                "block_number": 0,
            }

        import uuid as _uuid

        uid        = _uuid.UUID(denuncia_id)
        offchain   = uid.bytes.ljust(32, b"\x00")
        photo_aft  = self.w3.keccak(text=foto_resolucao_url)

        tx_func = self.denuncia_nft_contract.functions.resolverDenuncia(
            offchain,
            photo_aft,
            metadata_uri,
        )

        tx_hash_hex, receipt = self._send_transaction(tx_func)

        # Extrai tokenId do evento DenunciaResolvida(offchainId, tokenId, photoAfterHash)
        token_id: Optional[int] = None
        try:
            logs = self.denuncia_nft_contract.events.DenunciaResolvida().process_receipt(receipt)
            if logs:
                token_id = logs[0]["args"]["tokenId"]
        except Exception as exc:
            logger.warning(
                "Não foi possível extrair tokenId do evento DenunciaResolvida: %s. "
                "Usando totalSupply como fallback.",
                exc,
            )
            try:
                token_id = self.denuncia_nft_contract.functions.totalSupply().call()
            except Exception:
                token_id = 0

        logger.info(
            "DenunciaNFT.resolverDenuncia — denuncia_id=%s token_id=%s tx=%s bloco=%s",
            denuncia_id, token_id, tx_hash_hex, receipt["blockNumber"],
        )
        return {
            "tx_hash":    tx_hash_hex,
            "token_id":   str(token_id),
            "block_number": receipt["blockNumber"],
        }

    async def consultar_denuncia_blockchain(self, denuncia_id: str) -> dict:
        """
        Chama DenunciaNFT.getDenuncia() — view function, sem gas, sem transação.

        Útil para auditorias públicas e verificador da plataforma.

        Args:
            denuncia_id: UUID string da denúncia.

        Returns:
            dict com citizen, status ("REPORTADA"/"RESOLVIDA"), timestamps e token_id.
            Em modo simulado, retorna dict com valores padrão.

        Raises:
            ContractLogicError: DenunciaNotRegistered se o UUID não foi registrado on-chain.
        """
        if not self.enabled or not self.denuncia_nft_contract:
            logger.info("[SIMULADO] consultar_denuncia_blockchain — denuncia_id=%s", denuncia_id)
            return {
                "citizen":      "0x0000000000000000000000000000000000000000",
                "status":       "SIMULADO",
                "reported_at":  0,
                "resolved_at":  0,
                "token_id":     0,
                "on_chain":     False,
            }

        import uuid as _uuid
        uid      = _uuid.UUID(denuncia_id)
        offchain = uid.bytes.ljust(32, b"\x00")

        # getDenuncia retorna DenunciaRecord struct:
        # (citizen, offchainId, photoBeforeHash, photoAfterHash,
        #  description, status, reportedAt, resolvedAt, tokenId)
        try:
            record = self.denuncia_nft_contract.functions.getDenuncia(offchain).call()
        except Exception as exc:
            # ContractLogicError com DenunciaNotRegistered
            logger.warning("getDenuncia retornou erro para denuncia_id=%s: %s", denuncia_id, exc)
            raise

        return {
            "citizen":      record[0],                           # address
            "status":       "RESOLVIDA" if record[5] == 1 else "REPORTADA",  # Status enum
            "reported_at":  record[6],                           # uint64 timestamp
            "resolved_at":  record[7],                           # uint64 timestamp (0 se pendente)
            "token_id":     record[8],                           # uint256 (0 se pendente)
            "on_chain":     True,
        }

    # ═══════════════════════════════════════════════════════════════════════════
    #  [LEGADO] register_denuncia_proof — mantido por compatibilidade
    #  Usar registrar_denuncia_blockchain para novo código.
    # ═══════════════════════════════════════════════════════════════════════════

    async def register_denuncia_proof(self, proof_hash: str) -> str:
        """
        [LEGADO] Registra proof genérico no ValidationRegistry.
        Mantido para compatibilidade com calls anteriores.
        Novo código deve usar registrar_denuncia_blockchain().
        """
        logger.warning(
            "register_denuncia_proof está obsoleto. "
            "Use registrar_denuncia_blockchain() para integração com DenunciaNFT.sol."
        )
        if not self.enabled or not self.registry_contract:
            return _generate_fake_tx_hash()

        if WEB3_AVAILABLE:
            offchain_bytes = Web3.keccak(text=proof_hash)
            photo_bytes    = Web3.keccak(text=proof_hash)
        else:
            import hashlib
            raw = bytes.fromhex(hashlib.sha256(proof_hash.encode()).hexdigest())
            offchain_bytes = raw
            photo_bytes    = raw

        meta_bytes = bytes(32)
        tx_func = self.registry_contract.functions.registerLimpeza(
            offchain_bytes, photo_bytes, photo_bytes, meta_bytes, 0, 4, True,
        )
        tx_hash, _ = self._send_transaction(tx_func)
        return tx_hash

    # ── Educação Ambiental ───────────────────────────────────────────────────

    async def registrar_educacao_registry(
        self,
        offchain_id: str,
        foto_url: str,
        num_pessoas: int,
        actor_wallet: str,
    ) -> str:
        """
        Chama EcoProofRegistry.registerEducacao().
        Retorna tx_hash.
        """
        if not self.enabled or not self.registry_contract:
            logger.info("[SIMULADO] registrar_educacao_registry — offchain_id=%s", offchain_id)
            return _generate_fake_tx_hash()

        offchain_bytes = uuid_to_bytes32(offchain_id)
        photo_hash = bytes.fromhex(compute_keccak256(foto_url.encode("utf-8")).replace("0x", ""))
        checksum = Web3.to_checksum_address(actor_wallet)

        tx_func = self.registry_contract.functions.registerEducacao(
            offchain_bytes, photo_hash, num_pessoas, checksum
        )

        tx_hash, _ = self._send_transaction(tx_func)
        return tx_hash

    async def mint_educacao_individual(
        self,
        destinatario: str,
        metadata_uri: str,
        offchain_id: str,
        tipo_acao: str,
        validator_wallet: str,
        num_pessoas: int,
        issued_by: str,
    ) -> dict:
        """
        Chama EducacaoNFT.mintEducacao().
        Minta NFT Soulbound para o autor da ação.
        Retorna tx_hash e token_id.
        """
        if not self.enabled or not self.educacao_nft_contract:
            logger.info("[SIMULADO] mint_educacao_individual — destinatario=%s", destinatario)
            return {
                "tx_hash": _generate_fake_tx_hash(),
                "token_id": _generate_fake_token_id(),
            }

        tipo_uint = EDUCACAO_TYPE_MAP.get(tipo_acao, 4)
        issued_uint = ISSUED_BY_MAP.get(issued_by.lower(), 0)
        checksum_dest = Web3.to_checksum_address(destinatario)
        checksum_validator = Web3.to_checksum_address(validator_wallet)
        offchain_bytes = uuid_to_bytes32(offchain_id)

        tx_func = self.educacao_nft_contract.functions.mintEducacao(
            checksum_dest,
            metadata_uri,
            offchain_bytes,
            tipo_uint,
            checksum_validator,
            num_pessoas,
            issued_uint,
        )

        tx_hash, receipt = self._send_transaction(tx_func)

        # Extrair tokenId do evento EducacaoMinted
        token_id = None
        try:
            logs = self.educacao_nft_contract.events.EducacaoMinted().process_receipt(receipt)
            if logs:
                token_id = logs[0]["args"]["tokenId"]
        except Exception as e:
            logger.warning(
                "Não foi possível extrair tokenId do evento EducacaoMinted: %s. "
                "Usando totalSupply como fallback.",
                e,
            )
            try:
                token_id = self.educacao_nft_contract.functions.totalSupply().call()
            except Exception:
                token_id = 0

        return {"tx_hash": tx_hash, "token_id": str(token_id)}

    def get_total_pessoas_impactadas(self) -> int:
        """View function — sem gas. Retorna o contador global on-chain."""
        if not self.enabled or not self.educacao_nft_contract:
            logger.info("[SIMULADO] get_total_pessoas_impactadas")
            return 100
        return self.educacao_nft_contract.functions.totalPeopleImpacted().call()

    # ═════════════════════════════════════════════════════════════════════════
    #  Verificação On-Chain (view functions — sem gas)
    # ═════════════════════════════════════════════════════════════════════════

    async def verify_photo(self, offchain_id: str, photo_hash: str) -> bool:
        """Verifica se o hash de foto bate com o registrado on-chain."""
        if not self.enabled or not self.registry_contract:
            return False

        offchain_bytes = uuid_to_bytes32(offchain_id)
        photo_bytes = bytes.fromhex(photo_hash.replace("0x", ""))

        return self.registry_contract.functions.verifyPhoto(
            offchain_bytes, photo_bytes
        ).call()

    async def get_total_supply(self) -> int:
        """Retorna total supply do contrato EcoProofNFT."""
        if not self.enabled or not self.nft_contract:
            return 0
        return self.nft_contract.functions.totalSupply().call()

    async def get_total_proofs(self) -> int:
        """Retorna total de provas no Registry."""
        if not self.enabled or not self.registry_contract:
            return 0
        return self.registry_contract.functions.totalProofs().call()

    async def is_registered(self, offchain_id: str) -> bool:
        """Verifica se uma prova está registrada on-chain."""
        if not self.enabled or not self.registry_contract:
            return False
        offchain_bytes = uuid_to_bytes32(offchain_id)
        return self.registry_contract.functions.isRegistered(offchain_bytes).call()

    # ═════════════════════════════════════════════════════════════════════════
    #  Helpers internos
    # ═════════════════════════════════════════════════════════════════════════

    def _extract_token_id_from_receipt(self, receipt: dict, event_name: str) -> int:
        """Extrai tokenId do primeiro evento ActionMinted/NFTEventoMintado."""
        try:
            if self.nft_contract:
                logs = self.nft_contract.events[event_name]().process_receipt(receipt)
                if logs:
                    return logs[0]["args"]["tokenId"]
        except Exception as e:
            logger.warning("Não foi possível extrair tokenId do evento: %s", e)
        
        # Fallback: buscar totalSupply
        try:
            return self.nft_contract.functions.totalSupply().call()
        except Exception:
            return 0

    def _extract_batch_token_ids(self, receipt: dict) -> list[int]:
        """Extrai todos os tokenIds dos eventos ActionMinted no batch."""
        token_ids = []
        try:
            if self.nft_contract:
                logs = self.nft_contract.events.ActionMinted().process_receipt(receipt)
                token_ids = [log["args"]["tokenId"] for log in logs]
        except Exception as e:
            logger.warning("Não foi possível extrair tokenIds do batch: %s", e)
        return token_ids


# ── Singleton ────────────────────────────────────────────────────────────────

_blockchain_service: Optional[BlockchainService] = None


def get_blockchain_service() -> BlockchainService:
    """Retorna instância singleton do BlockchainService."""
    global _blockchain_service
    if _blockchain_service is None:
        _blockchain_service = BlockchainService()
    return _blockchain_service
