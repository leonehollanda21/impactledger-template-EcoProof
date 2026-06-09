import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.checkin_ponto_verde import CheckInPontoVerde, StatusCheckInPontoVerde
from app.models.cidadao import Cidadao
from app.models.ponto_verde import (
    PontoVerde,
    CategoriaPontoVerde,
    StatusPontoVerde,
)
from app.schemas.ponto_verde import (
    PontoVerdeResponse,
    CheckInPontoVerdeResponse,
)
from app.services import storage_service, nft_service


async def list_pontos(
    db: AsyncSession,
    status_filter: Optional[StatusPontoVerde] = None,
    categoria_filter: Optional[CategoriaPontoVerde] = None,
) -> list[PontoVerdeResponse]:
    query = select(PontoVerde)

    if status_filter is not None:
        query = query.where(PontoVerde.status == status_filter)
    if categoria_filter is not None:
        query = query.where(PontoVerde.categoria == categoria_filter)

    result = await db.execute(query.order_by(PontoVerde.created_at.desc()))
    pontos = result.scalars().all()
    return [PontoVerdeResponse.model_validate(p) for p in pontos]


async def list_meus_pontos(db: AsyncSession, cidadao_id: uuid.UUID) -> list[PontoVerdeResponse]:
    result = await db.execute(
        select(PontoVerde)
        .where(PontoVerde.guardiao_id == cidadao_id)
        .order_by(PontoVerde.created_at.desc())
    )
    pontos = result.scalars().all()
    return [PontoVerdeResponse.model_validate(p) for p in pontos]


async def create_ponto_verde(
    db: AsyncSession,
    cidadao: Cidadao,
    nome: str,
    categoria: CategoriaPontoVerde,
    latitude: float,
    longitude: float,
    foto_inicial: UploadFile,
) -> PontoVerdeResponse:
    foto_url = await storage_service.upload_file(foto_inicial, "pontos-verdes/iniciais")

    ponto = PontoVerde(
        id=uuid.uuid4(),
        nome=nome,
        categoria=categoria,
        latitude=latitude,
        longitude=longitude,
        guardiao_id=cidadao.id,
        guardiao_name=cidadao.user.name if cidadao.user else None,
        data_inicio=datetime.now(timezone.utc),
        status=StatusPontoVerde.ativo,
        meses_concluidos=0,
        proximo_checkin_limite=datetime.now(timezone.utc) + timedelta(days=30),
        foto_inicial_url=foto_url,
    )
    db.add(ponto)
    await db.flush()

    return PontoVerdeResponse.model_validate(ponto)


async def create_checkin(
    db: AsyncSession,
    cidadao_id: uuid.UUID,
    ponto_verde_id: uuid.UUID,
    foto: UploadFile,
) -> CheckInPontoVerdeResponse:
    ponto = await _get_ponto_verde(db, ponto_verde_id)

    if ponto.guardiao_id != cidadao_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode enviar check-in para pontos que você adotou.",
        )

    if ponto.status == StatusPontoVerde.concluido:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A adoção já foi concluída e não aceita novos check-ins.",
        )

    if ponto.status == StatusPontoVerde.disponivel:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O ponto ainda não foi adotado e não pode receber check-in.",
        )

    now = datetime.now(timezone.utc)
    if ponto.proximo_checkin_limite and now > ponto.proximo_checkin_limite:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Prazo para o próximo check-in expirado para este ponto.",
        )

    next_month = ponto.meses_concluidos + 1
    if next_month > 3:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Todos os check-ins já foram realizados para este ponto.",
        )
    pending_result = await db.execute(
        select(CheckInPontoVerde)
        .where(CheckInPontoVerde.ponto_verde_id == ponto.id)
        .where(CheckInPontoVerde.status == StatusCheckInPontoVerde.pendente)
        .where(CheckInPontoVerde.mes_referencia == next_month)
    )
    existing_pending = pending_result.scalar_one_or_none()
    if existing_pending is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um check-in pendente para este mês.",
        )

    foto_url = await storage_service.upload_file(foto, "pontos-verdes/checkins")

    checkin = CheckInPontoVerde(
        id=uuid.uuid4(),
        ponto_verde_id=ponto.id,
        mes_referencia=next_month,
        foto_url=foto_url,
        status=StatusCheckInPontoVerde.pendente,
    )
    db.add(checkin)
    await db.flush()

    return CheckInPontoVerdeResponse.model_validate(checkin)


async def validate_checkin(
    db: AsyncSession,
    checkin_id: uuid.UUID,
    aprovado: bool,
    motivo: Optional[str],
) -> CheckInPontoVerdeResponse:
    result = await db.execute(
        select(CheckInPontoVerde)
        .where(CheckInPontoVerde.id == checkin_id)
        .with_for_update()
    )
    checkin = result.scalar_one_or_none()
    if checkin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Check-in não encontrado.",
        )

    if checkin.status != StatusCheckInPontoVerde.pendente:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Apenas check-ins pendentes podem ser validados.",
        )

    ponto = await _get_ponto_verde(db, checkin.ponto_verde_id)

    if not aprovado:
        if not motivo or len(motivo.strip()) < 10:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Motivo obrigatório para rejeição e deve ter pelo menos 10 caracteres.",
            )
        checkin.status = StatusCheckInPontoVerde.rejeitado
        checkin.motivo = motivo.strip()
        ponto.status = StatusPontoVerde.alerta
        db.add(checkin)
        db.add(ponto)
        return CheckInPontoVerdeResponse.model_validate(checkin)

    checkin.status = StatusCheckInPontoVerde.aprovado
    checkin.motivo = motivo.strip() if motivo else None
    ponto.meses_concluidos += 1
    now = datetime.now(timezone.utc)

    if ponto.meses_concluidos >= 3:
        ponto.status = StatusPontoVerde.concluido
        ponto.proximo_checkin_limite = None

        nft_response = await nft_service.mint_nft_guardiao(db, ponto)
        if nft_response and nft_response.token_id.isdigit():
            ponto.nft_token_id = int(nft_response.token_id)
            ponto.nft_tx_hash = nft_response.tx_hash

        # Credita 80 pontos ao guardião
        cid_result = await db.execute(select(Cidadao).where(Cidadao.id == ponto.guardiao_id))
        guardiao = cid_result.scalar_one_or_none()
        if guardiao:
            guardiao.total_points += 80
            db.add(guardiao)
    else:
        ponto.status = StatusPontoVerde.ativo
        ponto.proximo_checkin_limite = now + timedelta(days=30)

    db.add(checkin)
    db.add(ponto)
    return CheckInPontoVerdeResponse.model_validate(checkin)


async def _get_ponto_verde(db: AsyncSession, ponto_verde_id: uuid.UUID) -> PontoVerde:
    result = await db.execute(select(PontoVerde).where(PontoVerde.id == ponto_verde_id))
    ponto = result.scalar_one_or_none()
    if ponto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ponto verde não encontrado.",
        )
    return ponto
