"""
app/services/limpeza_service.py
────────────────────────────────
Orquestra o fluxo completo de limpeza individual:
  upload S3 → salvar LimpezaIndividual → analisar com Vision AI
  → salvar Validacao → (se aprovado) mintar NFT → retornar resultado

Fluxo completo (create_limpeza):
  ┌─────────────┐
  │ Upload S3   │  foto_antes + foto_depois → URLs públicas
  └──────┬──────┘
         │
  ┌──────▼──────┐
  │ Salva BD    │  LimpezaIndividual(status='pendente')
  └──────┬──────┘
         │
  ┌──────▼──────┐
  │ Vision AI   │  analyze_cleanup(url_antes, url_depois)
  └──────┬──────┘
         │
  ┌──────▼──────┐
  │ Salva Valida│  Validacao(resultado, score, motivo)
  └──────┬──────┘
         │
    aprovado?
    ├── SIM ──► mint_nft_individual() → NFT no banco
    │            Limpeza.status = 'aprovado'
    └── NÃO ──► Limpeza.status = 'reprovado'
"""
import logging
import uuid
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cidadao import Cidadao
from app.models.limpeza_individual import LimpezaIndividual, StatusLimpeza
from app.models.validacao import Validacao
from app.models.evento import TipoAcao
from app.schemas.limpeza import (
    LimpezaResponse,
    LimpezaListResponse,
    LimpezaResultResponse,
    LimpezaHistoricoResponse,
)
from app.schemas.nft import NFTResponse
from app.services import storage_service, vision_service, nft_service

logger = logging.getLogger(__name__)


# ── Criação + pipeline completo ───────────────────────────────────────────────

async def create_limpeza(
    db: AsyncSession,
    cidadao: Cidadao,
    foto_antes: UploadFile,
    foto_depois: UploadFile,
    tipo_acao: TipoAcao,
) -> LimpezaResultResponse:
    """
    Executa o pipeline completo de limpeza individual.

    Args:
        db: Sessão async do banco.
        cidadao: Perfil do cidadão autenticado.
        foto_antes: Arquivo de imagem do local ANTES da limpeza.
        foto_depois: Arquivo de imagem do local DEPOIS da limpeza.
        tipo_acao: Tipo de ação ambiental realizada.

    Returns:
        LimpezaResultResponse com limpeza, NFT (se aprovado), score e motivo.
    """
    # ── ETAPA 1: Upload das fotos no S3 ──────────────────────────────────────
    logger.info(
        "Iniciando pipeline de limpeza para cidadão %s (tipo=%s)",
        cidadao.id, tipo_acao.value,
    )

    url_antes, url_depois = await _upload_fotos(foto_antes, foto_depois)

    # ── ETAPA 2: Persistir LimpezaIndividual (status = pendente) ─────────────
    limpeza = LimpezaIndividual(
        id=uuid.uuid4(),
        cidadao_id=cidadao.id,
        foto_antes_url=url_antes,
        foto_depois_url=url_depois,
        tipo_acao=tipo_acao,
        status=StatusLimpeza.pendente,
    )
    db.add(limpeza)
    await db.flush()  # obtém limpeza.id antes de continuar

    logger.info("LimpezaIndividual criada: %s", limpeza.id)

    # ── ETAPA 3: Análise com Google Vision ────────────────────────────────────
    vision_result = await vision_service.analyze_cleanup(url_antes, url_depois)

    logger.info(
        "Vision resultado — approved=%s score=%.4f",
        vision_result.approved, vision_result.score,
    )

    # ── ETAPA 4: Salvar Validacao ──────────────────────────────────────────────
    validacao = Validacao(
        id=uuid.uuid4(),
        limpeza_id=limpeza.id,
        participacao_id=None,
        resultado=vision_result.approved,
        score=vision_result.score,
        motivo=vision_result.motivo,
    )
    db.add(validacao)

    # ── ETAPA 5: Aprovar ou reprovar + (opcional) mintar NFT ─────────────────
    nft_response: Optional[NFTResponse] = None

    if vision_result.approved:
        limpeza.status = StatusLimpeza.aprovado
        db.add(limpeza)

        # Busca o cidadão fresco do banco para garantir total_points atualizado
        result = await db.execute(select(Cidadao).where(Cidadao.id == cidadao.id))
        cidadao_fresh = result.scalar_one_or_none() or cidadao

        nft_response = await nft_service.mint_nft_individual(db, limpeza, cidadao_fresh)
        logger.info(
            "NFT gerado para limpeza %s — token_id=%s",
            limpeza.id, nft_response.token_id,
        )
    else:
        limpeza.status = StatusLimpeza.reprovado
        db.add(limpeza)
        logger.info("Limpeza %s reprovada. Motivo: %s", limpeza.id, vision_result.motivo)

    # O commit final é feito pelo dependency get_db
    return LimpezaResultResponse(
        limpeza=LimpezaResponse.model_validate(limpeza),
        nft=nft_response,
        aprovado=vision_result.approved,
        score=vision_result.score,
        motivo=vision_result.motivo,
    )


async def _upload_fotos(
    foto_antes: UploadFile,
    foto_depois: UploadFile,
) -> tuple[str, str]:
    """Faz upload das duas fotos e retorna (url_antes, url_depois)."""
    import asyncio

    url_antes, url_depois = await asyncio.gather(
        storage_service.upload_file(foto_antes, "limpezas/antes"),
        storage_service.upload_file(foto_depois, "limpezas/depois"),
    )
    return url_antes, url_depois


# ── Consultas ─────────────────────────────────────────────────────────────────

async def get_limpeza(
    db: AsyncSession,
    limpeza_id: uuid.UUID,
    cidadao_id: uuid.UUID,
) -> LimpezaResponse:
    """
    Busca uma limpeza específica e valida que pertence ao cidadão.

    Raises:
        404: Limpeza não encontrada.
        403: Limpeza pertence a outro cidadão.
    """
    result = await db.execute(
        select(LimpezaIndividual).where(LimpezaIndividual.id == limpeza_id)
    )
    limpeza = result.scalar_one_or_none()

    if limpeza is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Limpeza não encontrada.",
        )

    if limpeza.cidadao_id != cidadao_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar esta limpeza.",
        )

    return LimpezaResponse.model_validate(limpeza)


async def list_limpezas_cidadao(
    db: AsyncSession,
    cidadao_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    status_filter: Optional[StatusLimpeza] = None,
) -> LimpezaHistoricoResponse:
    """
    Retorna o histórico paginado de limpezas do cidadão.

    Args:
        db: Sessão async do banco.
        cidadao_id: ID do cidadão.
        page: Página atual (começa em 1).
        page_size: Itens por página (máx 100).
        status_filter: Filtra por status (pendente/aprovado/reprovado).

    Returns:
        LimpezaHistoricoResponse com items, total e metadados de paginação.
    """
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size

    base_query = select(LimpezaIndividual).where(
        LimpezaIndividual.cidadao_id == cidadao_id
    )

    if status_filter is not None:
        base_query = base_query.where(LimpezaIndividual.status == status_filter)

    # Conta o total
    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar_one()

    # Busca a página
    items_result = await db.execute(
        base_query
        .order_by(LimpezaIndividual.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    limpezas = items_result.scalars().all()

    return LimpezaHistoricoResponse(
        items=[LimpezaListResponse.model_validate(l) for l in limpezas],
        total=total,
        page=page,
        page_size=page_size,
        has_next=(offset + page_size) < total,
    )
