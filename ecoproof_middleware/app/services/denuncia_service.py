"""
app/services/denuncia_service.py
──────────────────────────────────
Orquestra o fluxo completo de Denúncia Ambiental Verificada.

Fluxo de criação (cidadão):
  upload foto → chama DenunciaNFT.registrarDenuncia on-chain → salva DB

Fluxo de resolução (admin):
  upload foto_resolucao → gera metadata ERC-721 → chama DenunciaNFT.resolverDenuncia
  → obtém token_id do evento on-chain → salva NFT no banco → 50 pts

Fluxo de improcedência (admin):
  atualiza status → salva motivo

Diagrama de estados:
  registrada
    ├─[admin: em_analise]──► em_analise
    │                           │
    └─[admin: resolver]─────────┤
                                ├─[admin: resolver]──► resolvida (NFT)
                                └─[admin: improcedente]─► improcedente
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cidadao import Cidadao
from app.models.denuncia import Denuncia, StatusDenuncia, TipoProblema
from app.models.nft import NFT, AssinadoPor
from app.models.user import User
from app.schemas.denuncia import (
    DenunciaCreateRequest,
    DenunciaResponse,
    DenunciaListResponse,
    DenunciaAdminListItem,
    DenunciaAdminListResponse,
)
from app.schemas.nft import NFTResponse
from app.services import storage_service, nft_service
from app.services.blockchain_service import get_blockchain_service

logger = logging.getLogger(__name__)

# Pontos concedidos ao cidadão quando a denúncia é resolvida
POINTS_DENUNCIA = 50

# Wallet neutra usada quando o cidadão não tem wallet configurada
_ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


# ── Helpers internos ──────────────────────────────────────────────────────────

def _get_citizen_wallet(cidadao: Cidadao) -> str:
    """
    Retorna a wallet do cidadão ou o endereço zero caso não configurada.
    O contrato aceita 0x000...000 como sentinel apenas em modo simulado.
    Em modo real, o cidadão precisa ter wallet configurada.
    """
    wallet = getattr(cidadao, "wallet_address", None) or (
        cidadao.user.wallet_address if cidadao.user and hasattr(cidadao.user, "wallet_address") else None
    )
    return wallet or _ZERO_ADDRESS


async def _get_denuncia_ou_404(db: AsyncSession, denuncia_id: uuid.UUID) -> Denuncia:
    """Busca uma denúncia por ID. Lança 404 se não existir."""
    result = await db.execute(select(Denuncia).where(Denuncia.id == denuncia_id))
    denuncia = result.scalar_one_or_none()
    if denuncia is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Denúncia não encontrada.",
        )
    return denuncia


def _to_response(denuncia: Denuncia, nft: Optional[NFTResponse] = None) -> DenunciaResponse:
    """Constrói DenunciaResponse a partir do ORM model."""
    return DenunciaResponse(
        id=denuncia.id,
        cidadao_id=denuncia.cidadao_id,
        tipo_problema=denuncia.tipo_problema,
        descricao=denuncia.descricao,
        status=denuncia.status,
        foto_problema_url=denuncia.foto_problema_url,
        foto_resolucao_url=denuncia.foto_resolucao_url,
        proof_hash=denuncia.proof_hash,
        blockchain_tx_hash=denuncia.blockchain_tx_hash,
        resolucao_tx_hash=denuncia.resolucao_tx_hash,
        motivo_improcedencia=denuncia.motivo_improcedencia,
        created_at=denuncia.created_at,
        resolved_at=denuncia.resolved_at,
        nft=nft,
    )


# ── 1. Criar denúncia (cidadão) ───────────────────────────────────────────────

async def criar_denuncia(
    db: AsyncSession,
    cidadao: Cidadao,
    foto_problema: UploadFile,
    data: DenunciaCreateRequest,
) -> DenunciaResponse:
    """
    Pipeline completo de criação de denúncia:

    1. Upload da foto para Cloudinary (pasta denuncias/problemas)
    2. Chama DenunciaNFT.registrarDenuncia() on-chain
       → registra offchainId (UUID), photoBeforeHash, description
       → salva tx_hash e offchain_id_hex como proof_hash no banco
    3. Persiste Denuncia no banco com status='registrada'
    4. Retorna DenunciaResponse

    A chamada blockchain não bloqueia o fluxo: se falhar, a denúncia
    é salva mesmo assim (sem tx_hash) e o erro é logado para retry.

    Args:
        db: Sessão async do banco.
        cidadao: Perfil do cidadão autenticado.
        foto_problema: Arquivo de imagem do problema.
        data: Campos de texto validados (tipo_problema, descricao).

    Returns:
        DenunciaResponse com status='registrada'.
    """
    logger.info(
        "Criando denúncia — cidadao_id=%s tipo=%s",
        cidadao.id, data.tipo_problema.value,
    )

    # Etapa 1: Upload da foto
    foto_url = await storage_service.upload_file(foto_problema, "denuncias/problemas")
    logger.info("Foto da denúncia enviada: %s", foto_url)

    # Etapa 2: Registra on-chain no DenunciaNFT.sol
    blockchain_tx_hash: Optional[str] = None
    proof_hash: Optional[str] = None
    citizen_wallet = _get_citizen_wallet(cidadao)
    denuncia_id = uuid.uuid4()

    try:
        blockchain = get_blockchain_service()
        resultado = await blockchain.registrar_denuncia_blockchain(
            citizen_wallet=citizen_wallet,
            denuncia_id=str(denuncia_id),
            foto_url=foto_url,
            descricao=data.descricao,
        )
        blockchain_tx_hash = resultado["tx_hash"]
        proof_hash         = resultado["offchain_id_hex"]
        logger.info("Registrado on-chain — tx=%s proof=%s", blockchain_tx_hash, proof_hash)
    except Exception as exc:
        logger.warning(
            "Falha ao registrar denúncia on-chain (blockchain indisponível): %s. "
            "Denúncia será salva sem tx_hash.",
            exc,
        )

    # Etapa 3: Salva no banco
    denuncia = Denuncia(
        id=denuncia_id,
        cidadao_id=cidadao.id,
        tipo_problema=data.tipo_problema,
        descricao=data.descricao,
        foto_problema_url=foto_url,
        status=StatusDenuncia.registrada,
        proof_hash=proof_hash,
        blockchain_tx_hash=blockchain_tx_hash,
        created_at=datetime.now(timezone.utc),
    )
    db.add(denuncia)
    await db.flush()

    logger.info("Denúncia criada: id=%s", denuncia.id)
    return _to_response(denuncia)


# ── 2. Buscar denúncia (cidadão) ──────────────────────────────────────────────

async def get_denuncia(
    db: AsyncSession,
    denuncia_id: uuid.UUID,
    cidadao_id: uuid.UUID,
) -> DenunciaResponse:
    """
    Busca uma denúncia pelo ID e valida que pertence ao cidadão.

    Raises:
        404: Denúncia não encontrada.
        403: Denúncia pertence a outro cidadão.
    """
    denuncia = await _get_denuncia_ou_404(db, denuncia_id)

    if denuncia.cidadao_id != cidadao_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar esta denúncia.",
        )

    return _to_response(denuncia)


# ── 3. Listar denúncias do cidadão ────────────────────────────────────────────

async def list_denuncias_cidadao(
    db: AsyncSession,
    cidadao_id: uuid.UUID,
    status_filter: Optional[StatusDenuncia] = None,
) -> list[DenunciaListResponse]:
    """
    Lista todas as denúncias do cidadão com filtro opcional por status.

    Returns:
        Lista de DenunciaListResponse ordenada por data decrescente.
    """
    query = select(Denuncia).where(Denuncia.cidadao_id == cidadao_id)

    if status_filter is not None:
        query = query.where(Denuncia.status == status_filter)

    result = await db.execute(query.order_by(Denuncia.created_at.desc()))
    denuncias = result.scalars().all()

    return [
        DenunciaListResponse(
            id=d.id,
            tipo_problema=d.tipo_problema,
            status=d.status,
            foto_problema_url=d.foto_problema_url,
            created_at=d.created_at,
            resolved_at=d.resolved_at,
        )
        for d in denuncias
    ]


# ── 4. Listar todas as denúncias (admin) ──────────────────────────────────────

async def list_todas_denuncias(
    db: AsyncSession,
    status_filter: Optional[StatusDenuncia] = None,
    page: int = 1,
    page_size: int = 20,
) -> DenunciaAdminListResponse:
    """
    Lista todas as denúncias da plataforma com paginação (uso exclusivo do admin).
    Inclui o nome do cidadão em cada item.

    Returns:
        DenunciaAdminListResponse com items, total e metadados de paginação.
    """
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size

    base_query = select(Denuncia)
    if status_filter is not None:
        base_query = base_query.where(Denuncia.status == status_filter)

    # Contagem total
    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar_one()

    # Página de itens
    items_result = await db.execute(
        base_query
        .order_by(Denuncia.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    denuncias = items_result.scalars().all()

    # Enriquece com nome do cidadão (busca em lote via user_ids únicos)
    cidadao_ids = list({d.cidadao_id for d in denuncias})
    users_result = await db.execute(
        select(User).where(User.id.in_(cidadao_ids))
    )
    users_by_id = {u.id: u for u in users_result.scalars().all()}

    items = [
        DenunciaAdminListItem(
            id=d.id,
            tipo_problema=d.tipo_problema,
            status=d.status,
            foto_problema_url=d.foto_problema_url,
            created_at=d.created_at,
            resolved_at=d.resolved_at,
            cidadao_id=d.cidadao_id,
            cidadao_nome=users_by_id.get(d.cidadao_id, None) and users_by_id[d.cidadao_id].name,
        )
        for d in denuncias
    ]

    return DenunciaAdminListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(offset + page_size) < total,
    )


# ── 5. Marcar em análise (admin) ──────────────────────────────────────────────

async def marcar_em_analise(
    db: AsyncSession,
    denuncia_id: uuid.UUID,
    admin_id: uuid.UUID,
) -> DenunciaResponse:
    """
    Muda status de 'registrada' → 'em_analise'.

    Raises:
        404: Denúncia não encontrada.
        400: Status atual não é 'registrada'.
    """
    denuncia = await _get_denuncia_ou_404(db, denuncia_id)

    if denuncia.status != StatusDenuncia.registrada:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Só é possível iniciar análise de denúncias com status 'registrada'. "
                   f"Status atual: '{denuncia.status.value}'.",
        )

    denuncia.status = StatusDenuncia.em_analise
    db.add(denuncia)
    await db.flush()

    logger.info("Denúncia %s marcada como em_analise por admin %s", denuncia_id, admin_id)
    return _to_response(denuncia)


# ── 6. Confirmar resolução (admin) → gera NFT ────────────────────────────────

async def confirmar_resolucao(
    db: AsyncSession,
    denuncia_id: uuid.UUID,
    foto_resolucao: UploadFile,
    admin_id: uuid.UUID,
) -> DenunciaResponse:
    """
    Confirma que o problema foi resolvido:

    1. Valida status ('registrada' ou 'em_analise')
    2. Upload da foto de resolução
    3. Atualiza: foto_resolucao_url, status='resolvida', resolved_at=now
    4. Minta NFT (50 pts) via nft_service.mint_nft_denuncia
    5. Salva resolucao_tx_hash
    6. Retorna DenunciaResponse com NFT incluído

    Raises:
        404: Denúncia não encontrada.
        400: Status inválido para resolução (já resolvida ou improcedente).
    """
    denuncia = await _get_denuncia_ou_404(db, denuncia_id)

    if denuncia.status not in (StatusDenuncia.registrada, StatusDenuncia.em_analise):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Não é possível resolver uma denúncia com status '{denuncia.status.value}'. "
                   "Apenas denúncias 'registrada' ou 'em_analise' podem ser resolvidas.",
        )

    # Etapa 1: Upload da foto de resolução
    foto_res_url = await storage_service.upload_file(foto_resolucao, "denuncias/resolucoes")
    logger.info("Foto de resolução enviada: %s", foto_res_url)

    # Etapa 2: Atualiza a denúncia
    now = datetime.now(timezone.utc)
    denuncia.foto_resolucao_url = foto_res_url
    denuncia.status = StatusDenuncia.resolvida
    denuncia.resolved_at = now
    db.add(denuncia)
    await db.flush()

    # Etapa 3: Busca o cidadão para mintar o NFT
    cidadao_result = await db.execute(
        select(Cidadao).where(Cidadao.id == denuncia.cidadao_id)
    )
    cidadao = cidadao_result.scalar_one_or_none()
    if cidadao is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cidadão associado à denúncia não encontrado.",
        )

    # Etapa 4: Mint do NFT via DenunciaNFT.resolverDenuncia (on-chain + off-chain)
    nft_response: Optional[NFTResponse] = None
    try:
        # 4a. Gera metadata ERC-721 no Cloudinary
        nft_response = await nft_service.mint_nft_denuncia(db, denuncia, cidadao)
        denuncia.resolucao_tx_hash = nft_response.tx_hash
        db.add(denuncia)
        await db.flush()
        logger.info(
            "NFT de denúncia mintado — token_id=%s tx=%s denuncia_id=%s",
            nft_response.token_id, nft_response.tx_hash, denuncia_id,
        )
    except Exception as exc:
        logger.exception("Falha ao mintar NFT de denúncia %s: %s", denuncia_id, exc)
        # Não reverte a resolução — apenas loga o erro de mint

    logger.info(
        "Denúncia %s resolvida por admin %s", denuncia_id, admin_id
    )
    return _to_response(denuncia, nft=nft_response)


# ── 7. Marcar improcedente (admin) ────────────────────────────────────────────

async def marcar_improcedente(
    db: AsyncSession,
    denuncia_id: uuid.UUID,
    motivo: str,
    admin_id: uuid.UUID,
) -> DenunciaResponse:
    """
    Marca a denúncia como improcedente (denúncia falsa ou duplicada).

    Raises:
        404: Denúncia não encontrada.
        400: Tentativa de marcar como improcedente uma denúncia já resolvida.
    """
    denuncia = await _get_denuncia_ou_404(db, denuncia_id)

    if denuncia.status == StatusDenuncia.resolvida:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível marcar como improcedente uma denúncia que já foi resolvida.",
        )

    if denuncia.status == StatusDenuncia.improcedente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta denúncia já está marcada como improcedente.",
        )

    denuncia.status = StatusDenuncia.improcedente
    denuncia.motivo_improcedencia = motivo.strip()
    db.add(denuncia)
    await db.flush()

    logger.info(
        "Denúncia %s marcada como improcedente por admin %s. Motivo: %s",
        denuncia_id, admin_id, motivo,
    )
    return _to_response(denuncia)


# ── 8. Verificar denúncia on-chain (público) ───────────────────────────────────

async def verificar_denuncia(
    db: AsyncSession,
    denuncia_id: uuid.UUID,
) -> dict:
    """
    Busca dados on-chain via DenunciaNFT.getDenuncia() (sem gas, view function)
    e cruza com dados off-chain do banco.

    Qualquer pessoa pode chamar essa função sem autenticação — serve como
    verificador público para auditorias, integradores e IPTU Verde.

    Returns:
        dict com dados do banco (foto, descrição) + dados on-chain (status, citizen, token_id).

    Raises:
        404: Denúncia não encontrada no banco.
        400: Custom error do contrato (DenunciaNotRegistered) — não registrada on-chain.
    """
    # Busca no banco
    result = await db.execute(select(Denuncia).where(Denuncia.id == denuncia_id))
    denuncia = result.scalar_one_or_none()
    if denuncia is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Denúncia não encontrada.",
        )

    # Consulta on-chain (fallback amigável se blockchain desativada)
    chain_data: dict = {}
    try:
        blockchain = get_blockchain_service()
        chain_data = await blockchain.consultar_denuncia_blockchain(str(denuncia_id))
    except Exception as exc:
        # ContractLogicError: DenunciaNotRegistered ou provider indisponível
        logger.warning(
            "Consulta on-chain falhou para denúncia %s: %s", denuncia_id, exc
        )
        chain_data = {
            "citizen":     denuncia.blockchain_tx_hash and "N/A" or "Pendente",
            "status":      "NÃO VERIFICADO (blockchain indisponível)",
            "reported_at": 0,
            "resolved_at": 0,
            "token_id":    0,
            "on_chain":    False,
        }

    return {
        # Dados do banco
        "id":                str(denuncia_id),
        "tipo_problema":     denuncia.tipo_problema.value,
        "descricao":         denuncia.descricao,
        "status_offchain":   denuncia.status.value,
        "foto_problema_url": denuncia.foto_problema_url,
        "foto_resolucao_url": denuncia.foto_resolucao_url,
        "created_at":        denuncia.created_at.isoformat() if denuncia.created_at else None,
        "resolved_at":       denuncia.resolved_at.isoformat() if denuncia.resolved_at else None,
        # Identidade on-chain
        "proof_hash":         denuncia.proof_hash,
        "blockchain_tx_hash": denuncia.blockchain_tx_hash,
        "resolucao_tx_hash":  denuncia.resolucao_tx_hash,
        # Dados on-chain (do contrato)
        "on_chain": {
            "citizen":      chain_data.get("citizen"),
            "status":       chain_data.get("status"),
            "reported_at":  chain_data.get("reported_at"),
            "resolved_at":  chain_data.get("resolved_at"),
            "token_id":     chain_data.get("token_id"),
            "verified":     chain_data.get("on_chain", False),
        },
    }
