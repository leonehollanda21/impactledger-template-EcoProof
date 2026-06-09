"""
app/services/participacao_service.py
──────────────────────────────────────
Gerencia check-in, envio de foto, aprovação/rejeição de participações
e listagem com filtros.
"""
import logging
import uuid
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evento import Evento, StatusEvento
from app.models.participacao import Participacao, StatusParticipacao
from app.models.validacao import Validacao
from app.models.user import User
from app.schemas.participacao import (
    ParticipacaoResponse,
    MinhaParticipacaoResponse,
    ParticipacaoListResponse,
    MinhasParticipacoesPaginadas,
)
from app.services import storage_service, vision_service

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_participacao_or_404(
    db: AsyncSession,
    participacao_id: uuid.UUID,
) -> Participacao:
    result = await db.execute(
        select(Participacao).where(Participacao.id == participacao_id)
    )
    p = result.scalar_one_or_none()
    if p is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participação não encontrada.",
        )
    return p


async def _assert_participacao_cidadao(
    db: AsyncSession,
    participacao_id: uuid.UUID,
    cidadao_id: uuid.UUID,
) -> Participacao:
    """Busca participação e valida que é do cidadão logado."""
    p = await _get_participacao_or_404(db, participacao_id)
    if p.cidadao_id != cidadao_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar esta participação.",
        )
    return p


async def _assert_participacao_instituto(
    db: AsyncSession,
    participacao_id: uuid.UUID,
    instituto_id: uuid.UUID,
) -> tuple[Participacao, Evento]:
    """Busca participação e valida que o instituto é dono do evento."""
    p = await _get_participacao_or_404(db, participacao_id)

    result = await db.execute(select(Evento).where(Evento.id == p.evento_id))
    evento = result.scalar_one_or_none()

    if evento is None or evento.instituto_id != instituto_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para gerenciar esta participação.",
        )
    return p, evento


async def _enrich_participacao(
    db: AsyncSession,
    p: Participacao,
) -> ParticipacaoResponse:
    """Enriquece a participação com o nome do cidadão."""
    result = await db.execute(select(User).where(User.id == p.cidadao_id))
    user = result.scalar_one_or_none()
    return ParticipacaoResponse(
        id=p.id,
        evento_id=p.evento_id,
        cidadao_id=p.cidadao_id,
        cidadao_nome=user.name if user else "Cidadão",
        foto_url=p.foto_url,
        status=p.status,
        checkin_at=p.checkin_at,
        motivo_rejeicao=p.motivo_rejeicao,
    )


# ── Confirmar presença (check-in) ─────────────────────────────────────────────

async def confirmar_presenca(
    db: AsyncSession,
    cidadao_id: uuid.UUID,
    evento_id: uuid.UUID,
) -> ParticipacaoResponse:
    """
    Realiza o check-in do cidadão em um evento.

    Valida:
    - Evento existe e está ativo
    - Cidadão não está já inscrito (UniqueConstraint)

    Returns:
        ParticipacaoResponse com status='confirmado'.
    """
    # Valida evento
    result = await db.execute(select(Evento).where(Evento.id == evento_id))
    evento = result.scalar_one_or_none()

    if evento is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento não encontrado.",
        )
    if evento.status != StatusEvento.ativo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Não é possível participar de um evento com status '{evento.status.value}'.",
        )

    # Verifica inscrição duplicada antes de tentar inserir
    dup = await db.execute(
        select(Participacao).where(
            Participacao.evento_id == evento_id,
            Participacao.cidadao_id == cidadao_id,
        )
    )
    if dup.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Você já está inscrito neste evento.",
        )

    participacao = Participacao(
        id=uuid.uuid4(),
        evento_id=evento_id,
        cidadao_id=cidadao_id,
        status=StatusParticipacao.confirmado,
    )
    db.add(participacao)

    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Você já está inscrito neste evento.",
        )

    logger.info("Check-in: cidadão %s no evento %s", cidadao_id, evento_id)
    return await _enrich_participacao(db, participacao)


# ── Enviar foto de participação ───────────────────────────────────────────────

async def enviar_foto(
    db: AsyncSession,
    participacao_id: uuid.UUID,
    cidadao_id: uuid.UUID,
    foto: UploadFile,
) -> ParticipacaoResponse:
    """
    Cidadão envia foto comprovando presença no evento.

    Fluxo:
    1. Valida dono e status atual (deve ser 'confirmado' ou 'foto_enviada')
    2. Upload S3
    3. Análise Vision (verifica presença de ação ambiental na foto)
    4. Salva Validacao
    5. Atualiza status para 'foto_enviada'

    Returns:
        ParticipacaoResponse com status='foto_enviada'.
    """
    p = await _assert_participacao_cidadao(db, participacao_id, cidadao_id)

    if p.status not in (StatusParticipacao.confirmado, StatusParticipacao.foto_enviada):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Não é possível enviar foto para participação com status '{p.status.value}'. "
                "Apenas participações 'confirmado' ou 'foto_enviada' aceitam novas fotos."
            ),
        )

    # Upload da foto
    foto_url = await storage_service.upload_file(foto, "eventos")

    # Análise Vision para validar presença de ação ambiental na foto única
    # (usa a mesma foto como antes e depois — verifica conteúdo ambiental)
    vision_result = await vision_service.analyze_cleanup(foto_url, foto_url)

    # Salva Validacao da participação
    validacao = Validacao(
        id=uuid.uuid4(),
        limpeza_id=None,
        participacao_id=p.id,
        resultado=vision_result.approved,
        score=vision_result.score,
        motivo=vision_result.motivo,
    )
    db.add(validacao)

    # Atualiza participação
    p.foto_url = foto_url
    p.status = StatusParticipacao.foto_enviada
    db.add(p)
    await db.flush()

    logger.info(
        "Foto enviada para participação %s — Vision score=%.2f",
        p.id, vision_result.score,
    )
    return await _enrich_participacao(db, p)


# ── Aprovação pelo instituto ──────────────────────────────────────────────────

async def aprovar_participacao(
    db: AsyncSession,
    participacao_id: uuid.UUID,
    instituto_id: uuid.UUID,
) -> ParticipacaoResponse:
    """
    Instituto aprova a participação de um cidadão.

    Valida:
    - Instituto é dono do evento
    - Status atual é 'foto_enviada' (precisa de foto para aprovar)

    Returns:
        ParticipacaoResponse com status='aprovado'.
    """
    p, evento = await _assert_participacao_instituto(db, participacao_id, instituto_id)

    if p.status != StatusParticipacao.foto_enviada:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Não é possível aprovar participação com status '{p.status.value}'. "
                "Apenas participações 'foto_enviada' podem ser aprovadas."
            ),
        )

    p.status = StatusParticipacao.aprovado
    p.motivo_rejeicao = None
    db.add(p)
    await db.flush()

    logger.info("Participação %s aprovada pelo instituto %s", p.id, instituto_id)
    return await _enrich_participacao(db, p)


# ── Rejeição pelo instituto ───────────────────────────────────────────────────

async def rejeitar_participacao(
    db: AsyncSession,
    participacao_id: uuid.UUID,
    instituto_id: uuid.UUID,
    motivo: str,
) -> ParticipacaoResponse:
    """
    Instituto rejeita a participação com motivo obrigatório.

    Valida:
    - Instituto é dono do evento
    - Status atual não é já 'aprovado' ou 'rejeitado'

    Returns:
        ParticipacaoResponse com status='rejeitado' e motivo_rejeicao.
    """
    p, evento = await _assert_participacao_instituto(db, participacao_id, instituto_id)

    if p.status in (StatusParticipacao.aprovado, StatusParticipacao.rejeitado):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Não é possível rejeitar participação já '{p.status.value}'."
            ),
        )

    p.status = StatusParticipacao.rejeitado
    p.motivo_rejeicao = motivo
    db.add(p)
    await db.flush()

    logger.info(
        "Participação %s rejeitada pelo instituto %s. Motivo: %s",
        p.id, instituto_id, motivo,
    )
    return await _enrich_participacao(db, p)


# ── Listagem para o instituto ─────────────────────────────────────────────────

async def list_participacoes_evento(
    db: AsyncSession,
    evento_id: uuid.UUID,
    instituto_id: uuid.UUID,
    status_filter: Optional[StatusParticipacao] = None,
    page: int = 1,
    page_size: int = 50,
) -> ParticipacaoListResponse:
    """
    Lista participantes de um evento (restrito ao instituto dono).

    Args:
        status_filter: Filtra por status específico.
    """
    # Valida dono do evento
    result = await db.execute(select(Evento).where(Evento.id == evento_id))
    evento = result.scalar_one_or_none()

    if evento is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento não encontrado.",
        )
    if evento.instituto_id != instituto_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para listar participantes deste evento.",
        )

    page_size = min(page_size, 100)
    offset = (page - 1) * page_size

    base_query = select(Participacao).where(Participacao.evento_id == evento_id)
    if status_filter is not None:
        base_query = base_query.where(Participacao.status == status_filter)

    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar_one()

    items_result = await db.execute(
        base_query.order_by(Participacao.checkin_at.desc()).offset(offset).limit(page_size)
    )
    participacoes = items_result.scalars().all()

    # Enriquece com nomes em lote
    cidadao_ids = [p.cidadao_id for p in participacoes]
    user_result = await db.execute(select(User).where(User.id.in_(cidadao_ids)))
    user_map = {u.id: u.name for u in user_result.scalars().all()}

    items = [
        ParticipacaoResponse(
            id=p.id,
            evento_id=p.evento_id,
            cidadao_id=p.cidadao_id,
            cidadao_nome=user_map.get(p.cidadao_id, "Cidadão"),
            foto_url=p.foto_url,
            status=p.status,
            checkin_at=p.checkin_at,
            motivo_rejeicao=p.motivo_rejeicao,
        )
        for p in participacoes
    ]

    return ParticipacaoListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(offset + page_size) < total,
    )


# ── Participações do cidadão ──────────────────────────────────────────────────

async def list_minhas_participacoes(
    db: AsyncSession,
    cidadao_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> MinhasParticipacoesPaginadas:
    """Lista histórico de participações do cidadão autenticado."""
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size

    base_query = select(Participacao).where(Participacao.cidadao_id == cidadao_id)

    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar_one()

    items_result = await db.execute(
        base_query.order_by(Participacao.checkin_at.desc()).offset(offset).limit(page_size)
    )
    participacoes = items_result.scalars().all()

    # Busca títulos dos eventos em lote
    evento_ids = [p.evento_id for p in participacoes]
    ev_result = await db.execute(select(Evento).where(Evento.id.in_(evento_ids)))
    evento_map = {e.id: e.titulo for e in ev_result.scalars().all()}

    items = [
        MinhaParticipacaoResponse(
            id=p.id,
            evento_id=p.evento_id,
            evento_titulo=evento_map.get(p.evento_id, "Evento"),
            foto_url=p.foto_url,
            status=p.status,
            checkin_at=p.checkin_at,
            motivo_rejeicao=p.motivo_rejeicao,
        )
        for p in participacoes
    ]

    return MinhasParticipacoesPaginadas(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(offset + page_size) < total,
    )
