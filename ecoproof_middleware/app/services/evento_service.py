"""
app/services/evento_service.py
────────────────────────────────
CRUD de eventos de mutirão e consultas enriquecidas.
"""
import logging
import uuid
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evento import Evento, StatusEvento, TipoAcao
from app.models.instituto import Instituto
from app.models.participacao import Participacao, StatusParticipacao
from app.models.user import User
from app.schemas.evento import (
    EventoCreateRequest,
    EventoUpdateRequest,
    EventoResponse,
    EventoDetalheResponse,
    EventoListResponse,
    ParticipacaoResumoResponse,
)
from app.services import storage_service

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_evento_or_404(db: AsyncSession, evento_id: uuid.UUID) -> Evento:
    result = await db.execute(select(Evento).where(Evento.id == evento_id))
    evento = result.scalar_one_or_none()
    if evento is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento não encontrado.",
        )
    return evento


async def _assert_evento_owner(
    db: AsyncSession,
    evento_id: uuid.UUID,
    instituto_id: uuid.UUID,
) -> Evento:
    """Busca o evento e valida que o instituto é o dono."""
    evento = await _get_evento_or_404(db, evento_id)
    if evento.instituto_id != instituto_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para modificar este evento.",
        )
    return evento


async def _count_participantes(db: AsyncSession, evento_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count(Participacao.id)).where(Participacao.evento_id == evento_id)
    )
    return result.scalar_one()


async def _build_evento_response(
    db: AsyncSession,
    evento: Evento,
    instituto_nome: str,
) -> EventoResponse:
    total = await _count_participantes(db, evento.id)
    return EventoResponse(
        id=evento.id,
        titulo=evento.titulo,
        descricao=evento.descricao,
        tipo_acao=evento.tipo_acao,
        local=evento.local,
        data_evento=evento.data_evento,
        status=evento.status,
        foto_capa_url=evento.foto_capa_url,
        created_at=evento.created_at,
        instituto_id=evento.instituto_id,
        instituto_nome=instituto_nome,
        total_participantes=total,
    )


# ── Create ────────────────────────────────────────────────────────────────────

async def create_evento(
    db: AsyncSession,
    instituto: Instituto,
    data: EventoCreateRequest,
    foto_capa: Optional[UploadFile] = None,
) -> EventoResponse:
    """
    Cria um novo evento de mutirão.

    Args:
        db: Sessão async do banco.
        instituto: Perfil do instituto autenticado.
        data: Dados do formulário (texto).
        foto_capa: Arquivo de imagem opcional para capa do evento.

    Returns:
        EventoResponse com dados completos.
    """
    foto_url: Optional[str] = None
    if foto_capa and foto_capa.filename:
        foto_url = await storage_service.upload_file(foto_capa, "eventos")

    evento = Evento(
        id=uuid.uuid4(),
        instituto_id=instituto.id,
        titulo=data.titulo,
        descricao=data.descricao,
        tipo_acao=data.tipo_acao,
        local=data.local,
        data_evento=data.data_evento,
        foto_capa_url=foto_url,
        status=StatusEvento.ativo,
    )
    db.add(evento)
    await db.flush()

    # Busca nome do instituto via User
    result = await db.execute(select(User).where(User.id == instituto.id))
    user = result.scalar_one_or_none()
    instituto_nome = user.name if user else "Instituto"

    logger.info("Evento criado: %s por instituto %s", evento.id, instituto.id)
    return await _build_evento_response(db, evento, instituto_nome)


# ── List (público) ────────────────────────────────────────────────────────────

async def list_eventos(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    status_filter: StatusEvento = StatusEvento.ativo,
    tipo_acao: Optional[TipoAcao] = None,
) -> EventoListResponse:
    """
    Lista eventos com filtros opcionais (público).

    Args:
        status_filter: Padrão = 'ativo'. Use None para todos.
        tipo_acao: Filtra por tipo de ação ambiental.
    """
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size

    query = select(Evento)
    if status_filter is not None:
        query = query.where(Evento.status == status_filter)
    if tipo_acao is not None:
        query = query.where(Evento.tipo_acao == tipo_acao)

    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar_one()

    items_result = await db.execute(
        query.order_by(Evento.data_evento.asc()).offset(offset).limit(page_size)
    )
    eventos = items_result.scalars().all()

    # Busca nomes dos institutos em lote
    instituto_ids = list({e.instituto_id for e in eventos})
    user_result = await db.execute(
        select(User).where(User.id.in_(instituto_ids))
    )
    user_map = {u.id: u.name for u in user_result.scalars().all()}

    items = []
    for evento in eventos:
        nome = user_map.get(evento.instituto_id, "Instituto")
        items.append(await _build_evento_response(db, evento, nome))

    return EventoListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(offset + page_size) < total,
    )


# ── Get (público) ─────────────────────────────────────────────────────────────

async def get_evento(
    db: AsyncSession,
    evento_id: uuid.UUID,
) -> EventoResponse:
    """Retorna um evento público com total de participantes."""
    evento = await _get_evento_or_404(db, evento_id)

    result = await db.execute(select(User).where(User.id == evento.instituto_id))
    user = result.scalar_one_or_none()
    instituto_nome = user.name if user else "Instituto"

    return await _build_evento_response(db, evento, instituto_nome)


# ── Detalhe (instituto dono) ──────────────────────────────────────────────────

async def get_evento_detalhe(
    db: AsyncSession,
    evento_id: uuid.UUID,
    instituto_id: uuid.UUID,
) -> EventoDetalheResponse:
    """
    Retorna detalhe completo do evento com lista de participantes.
    Restrito ao instituto dono do evento.
    """
    evento = await _assert_evento_owner(db, evento_id, instituto_id)

    result_user = await db.execute(select(User).where(User.id == evento.instituto_id))
    user = result_user.scalar_one_or_none()
    instituto_nome = user.name if user else "Instituto"

    # Busca participações com dados do cidadão
    part_result = await db.execute(
        select(Participacao, User)
        .join(User, User.id == Participacao.cidadao_id)
        .where(Participacao.evento_id == evento_id)
        .order_by(Participacao.checkin_at.desc())
    )
    rows = part_result.all()

    participantes = []
    contadores = {s: 0 for s in StatusParticipacao}

    for participacao, user_cid in rows:
        contadores[participacao.status] += 1
        participantes.append(
            ParticipacaoResumoResponse(
                id=participacao.id,
                cidadao_id=participacao.cidadao_id,
                cidadao_nome=user_cid.name,
                foto_url=participacao.foto_url,
                status=participacao.status.value,
                checkin_at=participacao.checkin_at,
                motivo_rejeicao=participacao.motivo_rejeicao,
            )
        )

    base = await _build_evento_response(db, evento, instituto_nome)
    return EventoDetalheResponse(
        **base.model_dump(),
        participantes=participantes,
        total_confirmados=contadores[StatusParticipacao.confirmado],
        total_aprovados=contadores[StatusParticipacao.aprovado],
        total_rejeitados=contadores[StatusParticipacao.rejeitado],
        total_foto_enviada=contadores[StatusParticipacao.foto_enviada],
    )


# ── Update ────────────────────────────────────────────────────────────────────

async def update_evento(
    db: AsyncSession,
    evento_id: uuid.UUID,
    instituto_id: uuid.UUID,
    data: EventoUpdateRequest,
    foto_capa: Optional[UploadFile] = None,
) -> EventoResponse:
    """Atualiza campos de um evento. Valida que o instituto é dono."""
    evento = await _assert_evento_owner(db, evento_id, instituto_id)

    if evento.status == StatusEvento.cancelado:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Não é possível editar um evento cancelado.",
        )

    if data.titulo is not None:
        evento.titulo = data.titulo
    if data.descricao is not None:
        evento.descricao = data.descricao
    if data.local is not None:
        evento.local = data.local
    if data.data_evento is not None:
        evento.data_evento = data.data_evento
    if data.status is not None:
        evento.status = data.status

    if foto_capa and foto_capa.filename:
        evento.foto_capa_url = await storage_service.upload_file(foto_capa, "eventos")

    db.add(evento)
    await db.flush()

    result = await db.execute(select(User).where(User.id == evento.instituto_id))
    user = result.scalar_one_or_none()
    return await _build_evento_response(db, evento, user.name if user else "Instituto")


# ── Delete (soft: status=cancelado) ──────────────────────────────────────────

async def delete_evento(
    db: AsyncSession,
    evento_id: uuid.UUID,
    instituto_id: uuid.UUID,
) -> EventoResponse:
    """
    Cancela um evento (soft delete: status → 'cancelado').
    Eventos com participantes confirmados não podem ser deletados diretamente;
    use status='cancelado' via update.
    """
    evento = await _assert_evento_owner(db, evento_id, instituto_id)

    if evento.status == StatusEvento.cancelado:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Evento já está cancelado.",
        )

    evento.status = StatusEvento.cancelado
    db.add(evento)
    await db.flush()

    result = await db.execute(select(User).where(User.id == evento.instituto_id))
    user = result.scalar_one_or_none()
    return await _build_evento_response(db, evento, user.name if user else "Instituto")


# ── Eventos do instituto logado ───────────────────────────────────────────────

async def list_eventos_instituto(
    db: AsyncSession,
    instituto_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> EventoListResponse:
    """
    Lista todos os eventos do instituto (todos os status).
    Inclui contagem de participantes pendentes em cada evento.
    """
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size

    query = select(Evento).where(Evento.instituto_id == instituto_id)

    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar_one()

    items_result = await db.execute(
        query.order_by(Evento.created_at.desc()).offset(offset).limit(page_size)
    )
    eventos = items_result.scalars().all()

    result_user = await db.execute(select(User).where(User.id == instituto_id))
    user = result_user.scalar_one_or_none()
    instituto_nome = user.name if user else "Instituto"

    items = [
        await _build_evento_response(db, evento, instituto_nome)
        for evento in eventos
    ]

    return EventoListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(offset + page_size) < total,
    )
