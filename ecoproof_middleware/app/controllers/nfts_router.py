"""
app/controllers/nfts_router.py
────────────────────────────────
Endpoints públicos de NFT:

  GET /nfts/{token_id}              → NFTResponse completo com dados enriquecidos
  GET /nfts/{token_id}/metadata.json → JSON ERC-721 puro (para blockchain consultar)
  GET /nfts/{token_id}/verify       → Verifica NFT on-chain
  GET /nfts/stats                   → Estatísticas on-chain
  GET /nfts/verify-proof/{offchain_id} → Verifica proof on-chain
"""
import httpx
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import DBSession
from app.models.nft import NFT
from app.models.user import User
from app.models.limpeza_individual import LimpezaIndividual
from app.models.participacao import Participacao
from app.models.evento import Evento
from app.schemas.nft import NFTResponse
from app.services.blockchain_service import get_blockchain_service

router = APIRouter(prefix="/nfts", tags=["NFTs"])


async def _get_nft_or_404(db: AsyncSession, token_id: str) -> NFT:
    result = await db.execute(select(NFT).where(NFT.token_id == token_id))
    nft = result.scalar_one_or_none()
    if nft is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NFT com token_id '{token_id}' não encontrado.",
        )
    return nft


# ── GET /nfts/stats ───────────────────────────────────────────────────────────

@router.get(
    "/stats",
    summary="Estatísticas on-chain (público)",
    description="""
Retorna estatísticas agregadas dos contratos EcoProof na blockchain:
- Total supply de NFTs
- Total de provas registradas no ValidationRegistry

Endpoint **público** — não requer autenticação.
""",
)
async def get_blockchain_stats():
    blockchain = get_blockchain_service()
    
    total_supply = await blockchain.get_total_supply()
    total_proofs = await blockchain.get_total_proofs()

    return {
        "total_nfts_onchain": total_supply,
        "total_proofs_onchain": total_proofs,
        "blockchain_enabled": blockchain.enabled,
        "network": "polygon" if blockchain.enabled else "simulated",
    }


# ── GET /nfts/verify-proof/{offchain_id} ──────────────────────────────────────

@router.get(
    "/verify-proof/{offchain_id}",
    summary="Verificar prova on-chain (público)",
    description="""
Verifica se uma ação ambiental tem prova registrada na blockchain.

O `offchain_id` é o UUID da limpeza ou participação.
Retorna se a prova existe on-chain no ValidationRegistry.

Endpoint **público** — qualquer auditor pode verificar.
""",
)
async def verify_proof_onchain(offchain_id: str):
    blockchain = get_blockchain_service()
    
    is_registered = await blockchain.is_registered(offchain_id)

    return {
        "offchain_id": offchain_id,
        "registered_onchain": is_registered,
        "blockchain_enabled": blockchain.enabled,
        "message": (
            "✅ Prova registrada na blockchain. A ação ambiental é verificável."
            if is_registered
            else "❌ Prova não encontrada na blockchain."
        ),
    }


# ── GET /nfts/{token_id} ──────────────────────────────────────────────────────

@router.get(
    "/{token_id}",
    response_model=NFTResponse,
    summary="Detalhe de NFT por token_id (público)",
    description="""
Retorna os dados completos de um NFT dado seu `token_id` numérico.

Inclui:
- Dados do cidadão dono
- Evento ou limpeza associada
- Tipo de ação e foto comprobatória
- tx_hash da transação na blockchain
- Status: **Soulbound (intransferível)** — EIP-5192

Endpoint **público** — não requer autenticação.
""",
)
async def get_nft(
    token_id: str,
    db: DBSession,
) -> NFTResponse:
    nft = await _get_nft_or_404(db, token_id)

    tipo_acao = None
    foto_url = None

    # Enriquece com dados da origem
    if nft.limpeza_id:
        lim_result = await db.execute(
            select(LimpezaIndividual).where(LimpezaIndividual.id == nft.limpeza_id)
        )
        limpeza = lim_result.scalar_one_or_none()
        if limpeza:
            tipo_acao = limpeza.tipo_acao
            foto_url = limpeza.foto_depois_url

    elif nft.participacao_id:
        part_result = await db.execute(
            select(Participacao).where(Participacao.id == nft.participacao_id)
        )
        participacao = part_result.scalar_one_or_none()
        if participacao:
            foto_url = participacao.foto_url
            # Busca tipo_acao via evento
            ev_result = await db.execute(
                select(Evento).where(Evento.id == participacao.evento_id)
            )
            evento = ev_result.scalar_one_or_none()
            if evento:
                tipo_acao = evento.tipo_acao

    return NFTResponse(
        id=nft.id,
        token_id=nft.token_id,
        cidadao_id=nft.cidadao_id,
        assinado_por=nft.assinado_por,
        metadata_url=nft.metadata_url,
        tx_hash=nft.tx_hash,
        created_at=nft.created_at,
        limpeza_id=nft.limpeza_id,
        participacao_id=nft.participacao_id,
        instituto_id=nft.instituto_id,
        tipo_acao=tipo_acao,
        foto_url=foto_url,
    )


# ── GET /nfts/{token_id}/verify ───────────────────────────────────────────────

@router.get(
    "/{token_id}/verify",
    summary="Verificar NFT on-chain (público)",
    description="""
Verifica a existência e autenticidade de um NFT na blockchain.

Retorna:
- Se o NFT existe no banco de dados
- Se a prova correspondente está registrada on-chain
- Status Soulbound (intransferível)
- Link para verificação no blockchain explorer

Endpoint **público** — não requer autenticação.
""",
)
async def verify_nft_onchain(
    token_id: str,
    db: DBSession,
):
    nft = await _get_nft_or_404(db, token_id)
    blockchain = get_blockchain_service()

    # Determina offchain_id para verificar proof
    offchain_id = None
    if nft.limpeza_id:
        offchain_id = str(nft.limpeza_id)
    elif nft.participacao_id:
        offchain_id = str(nft.participacao_id)

    proof_registered = False
    if offchain_id:
        proof_registered = await blockchain.is_registered(offchain_id)

    # Determina o explorer URL baseado na chain
    from app.core.config import settings
    chain_id = getattr(settings, "CHAIN_ID", 11155111)
    
    explorer_urls = {
        11155111: "https://sepolia.etherscan.io",
        137: "https://polygonscan.com",
        80002: "https://amoy.polygonscan.com",
        1: "https://etherscan.io",
    }
    explorer_base = explorer_urls.get(chain_id, "https://etherscan.io")

    return {
        "token_id": nft.token_id,
        "exists_in_db": True,
        "tx_hash": nft.tx_hash,
        "proof_registered_onchain": proof_registered,
        "soulbound": True,  # EIP-5192 — sempre Soulbound
        "blockchain_enabled": blockchain.enabled,
        "explorer_url": f"{explorer_base}/tx/{nft.tx_hash}",
        "message": (
            "✅ NFT verificado. Soulbound (intransferível) — registrado na blockchain."
            if proof_registered
            else "⚠️ NFT encontrado no banco. Verificação on-chain indisponível."
        ),
    }


# ── GET /nfts/{token_id}/metadata.json ────────────────────────────────────────

@router.get(
    "/{token_id}/metadata.json",
    summary="Metadata ERC-721 do NFT (público, para blockchain)",
    description="""
Retorna o JSON de metadata no padrão ERC-721 / OpenSea exato.

Este endpoint é o **token URI** que contratos ERC-721 consultam para
exibir o NFT em marketplaces (OpenSea, Rarible, etc.).

Formato retornado:
```json
{
  "name": "EcoProof — Praia ...",
  "description": "NFT Soulbound ...",
  "image": "https://s3.url/foto.jpg",
  "external_url": "https://ecoproof.io/nft/...",
  "attributes": [...],
  "ecoproof_version": "1.0"
}
```

Endpoint **público** — não requer autenticação.
""",
    response_class=JSONResponse,
)
async def get_nft_metadata(
    token_id: str,
    db: DBSession,
) -> JSONResponse:
    """
    Proxy para o JSON de metadata salvo no S3.
    Retorna o conteúdo bruto do arquivo JSON de metadata ERC-721.
    """
    nft = await _get_nft_or_404(db, token_id)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(nft.metadata_url)
            response.raise_for_status()
            metadata = response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha ao buscar metadata do NFT: HTTP {exc.response.status_code}",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível acessar o metadata do NFT. Tente novamente.",
        )

    return JSONResponse(
        content=metadata,
        headers={
            "Cache-Control": "public, max-age=86400",  # 24h cache para a blockchain
            "Content-Type": "application/json",
        },
    )
