import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    CurrentUser,
    DBSession,
    CidadaoProfile,
)
from app.models.instituto import Instituto
from app.models.user import User, UserRole
from app.schemas.ponto_verde import (
    CheckInPontoVerdeResponse,
    CheckInValidationRequest,
    PontoVerdeResponse,
)
from app.services import pontos_verdes_service

router = APIRouter(prefix="/pontos-verdes", tags=["Pontos Verdes"])


async def _require_instituto_or_admin(
    current_user: CurrentUser,
    db: DBSession,
) -> User:
    if current_user.role == UserRole.admin:
        return current_user

    if current_user.role == UserRole.instituto:
        result = await db.execute(select(Instituto).where(Instituto.id == current_user.id))
        instituto = result.scalar_one_or_none()
        if instituto is None or not instituto.verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso restrito a institutos verificados ou administradores.",
            )
        return current_user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Acesso restrito a institutos verificados ou administradores.",
    )


# ── GET /pontos-verdes ─────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=list[PontoVerdeResponse],
    summary="Listar pontos verdes públicos",
    description="Retorna todos os pontos verdes para plotar no mapa. Suporta filtro por status e categoria.",
)
async def list_pontos_verdes(
    db: DBSession,
    status_filter: Optional[str] = Query(default=None, description="Filtrar por status"),
    categoria: Optional[str] = Query(default=None, description="Filtrar por categoria"),
) -> list[PontoVerdeResponse]:
    parsed_status = None
    categoria_filter = None
    from app.models.ponto_verde import StatusPontoVerde, CategoriaPontoVerde

    if status_filter is not None:
        try:
            parsed_status = StatusPontoVerde(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Status inválido: {status_filter}",
            )

    if categoria is not None:
        try:
            categoria_filter = CategoriaPontoVerde(categoria)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Categoria inválida: {categoria}",
            )

    return await pontos_verdes_service.list_pontos(
        db=db,
        status_filter=parsed_status,
        categoria_filter=categoria_filter,
    )


# ── POST /pontos-verdes ────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=PontoVerdeResponse,
    status_code=201,
    summary="Criar nova adoção de ponto verde",
    description="Cria uma adoção de área pública pelo cidadão autenticado com foto inicial.",
)
async def create_ponto_verde(
    cidadao: CidadaoProfile,
    db: DBSession,
    nome: str = Form(..., description="Nome do ponto verde"),
    categoria: str = Form(..., description="Categoria da área"),
    latitude: float = Form(..., description="Latitude da área"),
    longitude: float = Form(..., description="Longitude da área"),
    foto_inicial: UploadFile = File(..., description="Foto inicial do ponto verde"),
) -> PontoVerdeResponse:
    from app.models.ponto_verde import CategoriaPontoVerde

    try:
        categoria_enum = CategoriaPontoVerde(categoria)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Categoria inválida: {categoria}",
        )

    return await pontos_verdes_service.create_ponto_verde(
        db=db,
        cidadao=cidadao,
        nome=nome,
        categoria=categoria_enum,
        latitude=latitude,
        longitude=longitude,
        foto_inicial=foto_inicial,
    )


# ── GET /pontos-verdes/me ─────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=list[PontoVerdeResponse],
    summary="Meus pontos verdes adotados",
    description="Retorna os pontos verdes adotados pelo cidadão autenticado.",
)
async def list_meus_pontos(
    cidadao: CidadaoProfile,
    db: DBSession,
) -> list[PontoVerdeResponse]:
    return await pontos_verdes_service.list_meus_pontos(db, cidadao.id)


# ── POST /pontos-verdes/{id}/checkin ───────────────────────────────────────────

@router.post(
    "/{ponto_id}/checkin",
    response_model=CheckInPontoVerdeResponse,
    status_code=201,
    summary="Enviar foto de check-in mensal",
    description="Cidadão envia um check-in mensal para um ponto verde adotado.",
)
async def create_checkin(
    ponto_id: uuid.UUID,
    cidadao: CidadaoProfile,
    db: DBSession,
    foto: UploadFile = File(..., description="Foto do check-in mensal"),
) -> CheckInPontoVerdeResponse:
    return await pontos_verdes_service.create_checkin(
        db=db,
        cidadao_id=cidadao.id,
        ponto_verde_id=ponto_id,
        foto=foto,
    )


# ── PATCH /pontos-verdes/checkins/{checkin_id}/validar ────────────────────────

@router.patch(
    "/checkins/{checkin_id}/validar",
    response_model=CheckInPontoVerdeResponse,
    summary="Validar ou rejeitar check-in de ponto verde",
    description="Instituto ou admin valida/rejeita um check-in mensal de adoção.",
)
async def validar_checkin(
    checkin_id: uuid.UUID,
    body: CheckInValidationRequest,
    db: DBSession,
    validator: User = Depends(_require_instituto_or_admin),
) -> CheckInPontoVerdeResponse:
    return await pontos_verdes_service.validate_checkin(
        db=db,
        checkin_id=checkin_id,
        aprovado=body.aprovado,
        motivo=body.motivo,
    )
