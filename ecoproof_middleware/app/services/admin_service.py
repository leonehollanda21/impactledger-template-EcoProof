"""
app/services/admin_service.py
───────────────────────────────
Lógica de administração: gerenciar institutos, NFTs, denúncias e educação.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cidadao import Cidadao
from app.models.denuncia import Denuncia, StatusDenuncia
from app.models.educacao import AcaoEducacional, StatusAcaoEducativa
from app.models.evento import Evento
from app.models.instituto import Instituto
from app.models.nft import NFT
from app.models.user import User
from app.models.validacao import Validacao
from app.models.limpeza_individual import LimpezaIndividual
from app.schemas.admin import (
    InstitutoAdminResponse,
    InstitutoAdminListResponse,
    AcaoAdminResponse,
    ValidacaoAdminResponse,
    ValidacaoAdminListResponse,
    DashboardStats,
    NFTAdminResponse,
    NFTAdminListResponse,
    DenunciaAdminSummary,
    DenunciaAdminSummaryListResponse,
    EducacaoAdminSummary,
    EducacaoAdminListResponse,
)

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_instituto_or_404(
    db: AsyncSession,
    instituto_id: uuid.UUID,
) -> tuple[Instituto, User]:
    """Retorna (Instituto, User) ou lança 404."""
    result = await db.execute(
        select(Instituto, User)
        .join(User, User.id == Instituto.id)
        .where(Instituto.id == instituto_id)
    )
    row = result.first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instituto não encontrado.",
        )
    return row.Instituto, row.User


async def _build_instituto_response(
    db: AsyncSession,
    instituto: Instituto,
    user: User,
) -> InstitutoAdminResponse:
    """Enriquece com contagens de eventos e NFTs emitidos."""
    total_eventos_result = await db.execute(
        select(func.count(Evento.id)).where(Evento.instituto_id == instituto.id)
    )
    total_eventos = total_eventos_result.scalar_one()

    total_nfts_result = await db.execute(
        select(func.count(NFT.id)).where(NFT.instituto_id == instituto.id)
    )
    total_nfts = total_nfts_result.scalar_one()

    return InstitutoAdminResponse(
        id=instituto.id,
        nome=user.name,
        email=user.email,
        cnpj=instituto.cnpj,
        verified=instituto.verified,
        verified_at=instituto.verified_at,
        is_active=user.is_active,
        created_at=user.created_at,
        total_eventos=total_eventos,
        total_nfts_emitidos=total_nfts,
    )


# ── Listagem de institutos ────────────────────────────────────────────────────

async def list_institutos(
    db: AsyncSession,
    verified_filter: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
) -> InstitutoAdminListResponse:
    """
    Lista institutos com contagens.

    Args:
        verified_filter: True = só verificados, False = só pendentes, None = todos.
    """
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size

    query = select(Instituto, User).join(User, User.id == Instituto.id)
    if verified_filter is not None:
        query = query.where(Instituto.verified == verified_filter)

    count_result = await db.execute(
        select(func.count()).select_from(
            select(Instituto).where(
                Instituto.verified == verified_filter
                if verified_filter is not None
                else Instituto.id.isnot(None)
            ).subquery()
        )
    )
    total = count_result.scalar_one()

    items_result = await db.execute(
        query.order_by(User.created_at.desc()).offset(offset).limit(page_size)
    )
    rows = items_result.all()

    items = [
        await _build_instituto_response(db, row.Instituto, row.User)
        for row in rows
    ]

    return InstitutoAdminListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(offset + page_size) < total,
    )


# ── Aprovação de instituto ────────────────────────────────────────────────────

async def aprovar_instituto(
    db: AsyncSession,
    instituto_id: uuid.UUID,
) -> AcaoAdminResponse:
    """
    Aprova um instituto:
      - verified = True
      - verified_at = agora (UTC)
      - User.is_active = True

    Raises:
        404: Instituto não encontrado.
        422: Instituto já está verificado.
    """
    instituto, user = await _get_instituto_or_404(db, instituto_id)

    if instituto.verified:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Instituto já está verificado.",
        )

    instituto.verified = True
    instituto.verified_at = datetime.now(tz=timezone.utc)
    user.is_active = True

    db.add(instituto)
    db.add(user)
    await db.flush()

    logger.info("Instituto %s aprovado pelo admin.", instituto_id)

    return AcaoAdminResponse(
        success=True,
        message=f"Instituto '{user.name}' aprovado com sucesso.",
        instituto_id=instituto_id,
    )


# ── Suspensão de instituto ────────────────────────────────────────────────────

async def suspender_instituto(
    db: AsyncSession,
    instituto_id: uuid.UUID,
) -> AcaoAdminResponse:
    """
    Suspende um instituto:
      - verified = False
      - User.is_active = False (bloqueia login)

    Raises:
        404: Instituto não encontrado.
        422: Instituto já está suspenso.
    """
    instituto, user = await _get_instituto_or_404(db, instituto_id)

    if not instituto.verified and not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Instituto já está suspenso.",
        )

    instituto.verified = False
    user.is_active = False

    db.add(instituto)
    db.add(user)
    await db.flush()

    logger.warning("Instituto %s suspenso pelo admin.", instituto_id)

    return AcaoAdminResponse(
        success=True,
        message=f"Instituto '{user.name}' suspenso. Login bloqueado.",
        instituto_id=instituto_id,
    )


# ── Histórico de validações ───────────────────────────────────────────────────

async def list_validacoes(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    resultado_filter: Optional[bool] = None,
) -> ValidacaoAdminListResponse:
    """
    Retorna histórico paginado de todas as validações com dados do cidadão.

    Args:
        resultado_filter: True = só aprovadas, False = só reprovadas, None = todas.
    """
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size

    base_query = select(Validacao)
    if resultado_filter is not None:
        base_query = base_query.where(Validacao.resultado == resultado_filter)

    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar_one()

    items_result = await db.execute(
        base_query.order_by(Validacao.created_at.desc()).offset(offset).limit(page_size)
    )
    validacoes = items_result.scalars().all()

    # Coleta IDs de cidadãos para buscar em lote
    # Cada validação aponta para limpeza OU participacao — resolve o cidadão de ambos
    cidadao_map: dict[uuid.UUID, tuple[str, str | None]] = {}  # id → (nome, wallet)

    limpeza_ids = [v.limpeza_id for v in validacoes if v.limpeza_id]
    participacao_ids = [v.participacao_id for v in validacoes if v.participacao_id]

    # Limpezas → cidadao_id
    limpeza_to_cidadao: dict[uuid.UUID, uuid.UUID] = {}
    if limpeza_ids:
        lim_result = await db.execute(
            select(LimpezaIndividual.id, LimpezaIndividual.cidadao_id)
            .where(LimpezaIndividual.id.in_(limpeza_ids))
        )
        for row in lim_result.all():
            limpeza_to_cidadao[row.id] = row.cidadao_id

    # Participacoes → cidadao_id
    from app.models.participacao import Participacao
    participacao_to_cidadao: dict[uuid.UUID, uuid.UUID] = {}
    if participacao_ids:
        part_result = await db.execute(
            select(Participacao.id, Participacao.cidadao_id)
            .where(Participacao.id.in_(participacao_ids))
        )
        for row in part_result.all():
            participacao_to_cidadao[row.id] = row.cidadao_id

    # Coleta todos os cidadao_ids únicos
    all_cidadao_ids = set(limpeza_to_cidadao.values()) | set(participacao_to_cidadao.values())

    if all_cidadao_ids:
        user_result = await db.execute(
            select(User.id, User.name, User.wallet_address)
            .where(User.id.in_(all_cidadao_ids))
        )
        for row in user_result.all():
            cidadao_map[row.id] = (row.name, row.wallet_address)

    # Monta items
    items: list[ValidacaoAdminResponse] = []
    for v in validacoes:
        if v.limpeza_id:
            cidadao_id = limpeza_to_cidadao.get(v.limpeza_id)
            tipo = "limpeza"
        elif v.participacao_id:
            cidadao_id = participacao_to_cidadao.get(v.participacao_id)
            tipo = "participacao"
        else:
            continue  # validação órfã — ignora

        if cidadao_id is None:
            continue

        nome, wallet = cidadao_map.get(cidadao_id, ("Cidadão", None))

        items.append(ValidacaoAdminResponse(
            id=v.id,
            resultado=v.resultado,
            score=v.score,
            motivo=v.motivo,
            created_at=v.created_at,
            tipo=tipo,
            limpeza_id=v.limpeza_id,
            participacao_id=v.participacao_id,
            cidadao_id=cidadao_id,
            cidadao_nome=nome,
            cidadao_wallet=wallet,
        ))

    return ValidacaoAdminListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(offset + page_size) < total,
    )


# ── Dashboard ─────────────────────────────────────────────────────────────────

async def get_dashboard_stats(db: AsyncSession) -> DashboardStats:
    """Retorna contagens globais da plataforma para o dashboard admin."""

    async def count(stmt):
        r = await db.execute(stmt)
        return r.scalar_one()

    return DashboardStats(
        total_usuarios=await count(select(func.count(User.id))),
        total_cidadaos=await count(select(func.count(Cidadao.id))),
        total_institutos=await count(select(func.count(Instituto.id))),
        total_institutos_pendentes=await count(
            select(func.count(Instituto.id)).where(Instituto.verified == False)  # noqa: E712
        ),
        total_eventos=await count(select(func.count(Evento.id))),
        total_limpezas=await count(select(func.count(LimpezaIndividual.id))),
        total_nfts=await count(select(func.count(NFT.id))),
        total_validacoes_aprovadas=await count(
            select(func.count(Validacao.id)).where(Validacao.resultado == True)  # noqa: E712
        ),
        total_pontos_distribuidos=await count(
            select(func.coalesce(func.sum(Cidadao.total_points), 0))
        ),
        total_denuncias=await count(select(func.count(Denuncia.id))),
        total_educacoes=await count(select(func.count(AcaoEducacional.id))),
    )


# ── NFTs (admin) ──────────────────────────────────────────────────────────────

async def list_all_nfts(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> NFTAdminListResponse:
    """Lista todos os NFTs emitidos, enriquecidos com dados do cidadão."""
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size

    count_result = await db.execute(select(func.count(NFT.id)))
    total = count_result.scalar_one()

    nfts_result = await db.execute(
        select(NFT).order_by(NFT.created_at.desc()).offset(offset).limit(page_size)
    )
    nfts = nfts_result.scalars().all()

    # Coletar cidadao_ids para busca em lote
    cidadao_ids = list({n.cidadao_id for n in nfts})
    cidadao_map: dict[uuid.UUID, tuple[str, str | None]] = {}
    if cidadao_ids:
        user_result = await db.execute(
            select(User.id, User.name, User.wallet_address).where(User.id.in_(cidadao_ids))
        )
        for row in user_result.all():
            cidadao_map[row.id] = (row.name, row.wallet_address)

    items: list[NFTAdminResponse] = []
    for nft in nfts:
        nome, wallet = cidadao_map.get(nft.cidadao_id, ("Cidadão", None))

        # Deduz o tipo pelo campo de origem preenchido
        if nft.limpeza_id:
            tipo = "limpeza"
        elif nft.participacao_id:
            tipo = "mutirao"
        elif nft.educacao_id:
            tipo = "educacao"
        else:
            tipo = "outro"

        items.append(NFTAdminResponse(
            id=nft.id,
            token_id=nft.token_id,
            tx_hash=nft.tx_hash,
            metadata_url=nft.metadata_url,
            assinado_por=nft.assinado_por.value,
            created_at=nft.created_at,
            limpeza_id=nft.limpeza_id,
            participacao_id=nft.participacao_id,
            educacao_id=nft.educacao_id,
            instituto_id=nft.instituto_id,
            cidadao_id=nft.cidadao_id,
            cidadao_nome=nome,
            cidadao_wallet=wallet,
            tipo=tipo,
        ))

    return NFTAdminListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(offset + page_size) < total,
    )


# ── Denúncias (admin) ─────────────────────────────────────────────────────────

async def list_all_denuncias_admin(
    db: AsyncSession,
    status_filter: Optional[StatusDenuncia] = None,
    page: int = 1,
    page_size: int = 20,
) -> DenunciaAdminSummaryListResponse:
    """Lista todas as denúncias com filtro opcional por status e nome do cidadão."""
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size

    base_query = select(Denuncia)
    if status_filter is not None:
        base_query = base_query.where(Denuncia.status == status_filter)

    count_result = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total = count_result.scalar_one()

    denuncias_result = await db.execute(
        base_query.order_by(Denuncia.created_at.desc()).offset(offset).limit(page_size)
    )
    denuncias = denuncias_result.scalars().all()

    # Enriquecer com nomes dos cidadãos
    cidadao_ids = list({d.cidadao_id for d in denuncias})
    cidadao_map: dict[uuid.UUID, str] = {}
    if cidadao_ids:
        # Cidadao.id == User.id (herança de tabela)
        user_result = await db.execute(
            select(User.id, User.name).where(User.id.in_(cidadao_ids))
        )
        for row in user_result.all():
            cidadao_map[row.id] = row.name

    items = [
        DenunciaAdminSummary(
            id=d.id,
            tipo_problema=d.tipo_problema.value,
            status=d.status,
            foto_problema_url=d.foto_problema_url,
            created_at=d.created_at,
            resolved_at=d.resolved_at,
            cidadao_id=d.cidadao_id,
            cidadao_nome=cidadao_map.get(d.cidadao_id),
        )
        for d in denuncias
    ]

    return DenunciaAdminSummaryListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(offset + page_size) < total,
    )


# ── Educação (admin) ──────────────────────────────────────────────────────────

async def list_all_educacoes_admin(
    db: AsyncSession,
    status_filter: Optional[StatusAcaoEducativa] = None,
    page: int = 1,
    page_size: int = 20,
) -> EducacaoAdminListResponse:
    """Lista todas as ações educativas com filtro opcional por status."""
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size

    base_query = select(AcaoEducacional)
    if status_filter is not None:
        base_query = base_query.where(AcaoEducacional.status == status_filter)

    count_result = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total = count_result.scalar_one()

    acoes_result = await db.execute(
        base_query.order_by(AcaoEducacional.created_at.desc()).offset(offset).limit(page_size)
    )
    acoes = acoes_result.scalars().all()

    # Enriquecer com nomes dos autores
    autor_ids = list({a.autor_id for a in acoes})
    autor_map: dict[uuid.UUID, str] = {}
    if autor_ids:
        user_result = await db.execute(
            select(User.id, User.name).where(User.id.in_(autor_ids))
        )
        for row in user_result.all():
            autor_map[row.id] = row.name

    items = [
        EducacaoAdminSummary(
            id=a.id,
            tipo_acao=a.tipo_acao,
            num_pessoas=a.num_pessoas,
            status=a.status,
            foto_url=a.foto_url,
            descricao=a.descricao,
            created_at=a.created_at,
            autor_id=a.autor_id,
            autor_nome=autor_map.get(a.autor_id),
            autor_tipo=a.autor_tipo.value,
        )
        for a in acoes
    ]

    return EducacaoAdminListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(offset + page_size) < total,
    )
