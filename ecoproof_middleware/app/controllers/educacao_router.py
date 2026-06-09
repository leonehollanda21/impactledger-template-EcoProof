"""
app/controllers/educacao_router.py
───────────────────────────────────
Controller/Router FastAPI para as ações de Educação Ambiental.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile, Query, Depends, HTTPException, status as http_status
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DBSession
from app.models.user import UserRole
from app.models.instituto import Instituto
from app.models.educacao import StatusAcaoEducativa
from app.schemas.educacao import (
    TipoEducacaoEnum,
    EducacaoCreateRequest,
    EducacaoResponse,
    EducacaoListResponse,
    EducacaoValidarRequest,
)
from app.services import educacao_service
from app.services.blockchain_service import get_blockchain_service

router = APIRouter(prefix="/educacao", tags=["Educação"])


async def _verificar_instituto_ou_admin(current_user: CurrentUser, db: DBSession) -> None:
    """Valida se o usuário logado é admin ou um instituto verificado."""
    if current_user.role == UserRole.instituto:
        result = await db.execute(select(Instituto).where(Instituto.id == current_user.id))
        instituto = result.scalar_one_or_none()
        if not instituto or not instituto.verified:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Acesso restrito a institutos verificados.",
            )
    elif current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a institutos e administradores.",
        )


# ── 1. Registrar Ação Educacional ─────────────────────────────────────────────

@router.post(
    "",
    response_model=EducacaoResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="Registrar ação de educação ambiental",
    description="""
    Registra uma palestra, oficina ou atividade de educação ambiental.
    Ambos cidadãos e institutos podem registrar ações.
    A ação inicia como 'pendente' aguardando validação para posterior mint de NFT.
    """,
)
async def registrar_acao(
    current_user: CurrentUser,
    db: DBSession,
    foto: UploadFile = File(..., description="Foto do evento comprovando a ação"),
    tipo_acao: TipoEducacaoEnum = Form(..., description="Tipo da ação realizada"),
    num_pessoas: int = Form(..., description="Número de pessoas impactadas (min 1)"),
    descricao: Optional[str] = Form(None, description="Descrição opcional da ação"),
) -> EducacaoResponse:
    # Validar papel do usuário
    if current_user.role not in (UserRole.cidadao, UserRole.instituto):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Apenas cidadãos e institutos podem registrar ações educativas.",
        )

    # Validar num_pessoas
    if num_pessoas <= 0:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O número de pessoas deve ser maior que zero.",
        )

    data = EducacaoCreateRequest(
        tipo_acao=tipo_acao,
        num_pessoas=num_pessoas,
        descricao=descricao,
    )

    return await educacao_service.criar_acao(
        db=db,
        autor=current_user,
        foto=foto,
        data=data,
    )


# ── 2. Listar minhas ações ────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=list[EducacaoListResponse],
    summary="Listar minhas ações educativas",
    description="Retorna o histórico de ações educativas do cidadão ou instituto autenticado.",
)
async def list_minhas_acoes(
    current_user: CurrentUser,
    db: DBSession,
    status: Optional[StatusAcaoEducativa] = Query(default=None, description="Filtrar por status"),
) -> list[EducacaoListResponse]:
    if current_user.role not in (UserRole.cidadao, UserRole.instituto):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a cidadãos e institutos.",
        )

    return await educacao_service.list_minhas_acoes(
        db=db,
        autor_id=current_user.id,
        status_filter=status,
    )


# ── 3. Listar ações pendentes (admin/instituto) ───────────────────────────────

@router.get(
    "/pendentes",
    response_model=list[EducacaoListResponse],
    summary="Listar ações educativas pendentes de validação",
    description="Lista de uso exclusivo para admin e institutos verificados.",
)
async def list_acoes_pendentes(
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(default=1, ge=1, description="Número da página"),
    size: int = Query(default=20, ge=1, le=100, description="Tamanho da página"),
) -> list[EducacaoListResponse]:
    await _verificar_instituto_ou_admin(current_user, db)

    return await educacao_service.list_acoes_pendentes(
        db=db,
        page=page,
        size=size,
    )


# ── 4. Obter detalhe de uma ação ──────────────────────────────────────────────

@router.get(
    "/{acao_id}",
    response_model=EducacaoResponse,
    summary="Obter detalhe de uma ação educativa",
    description="Retorna a ação com metadados e NFT se houver. Cidadãos só veem as suas próprias.",
)
async def get_acao_detalhe(
    acao_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> EducacaoResponse:
    return await educacao_service.get_acao(
        db=db,
        acao_id=acao_id,
        user=current_user,
    )


# ── 5. Validar Ação (Aprovar/Rejeitar) ────────────────────────────────────────

@router.patch(
    "/{acao_id}/validar",
    response_model=EducacaoResponse,
    summary="Validar (aprovar ou rejeitar) ação educativa",
    description="De uso exclusivo para admin e institutos verificados. Se aprovado, minta o NFT.",
)
async def validar_acao(
    acao_id: uuid.UUID,
    body: EducacaoValidarRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> EducacaoResponse:
    await _verificar_instituto_ou_admin(current_user, db)

    return await educacao_service.validar_acao(
        db=db,
        acao_id=acao_id,
        validador=current_user,
        data=body,
    )


# ── 6. Obter impacto acumulado on-chain (público) ──────────────────────────────

@router.get(
    "/impacto/total",
    summary="Obter impacto total acumulado on-chain",
    description="Retorna a soma global de pessoas impactadas registrada no contrato de Educação Ambiental.",
)
def get_impacto_total() -> dict:
    blockchain = get_blockchain_service()
    total = blockchain.get_total_pessoas_impactadas()
    return {
        "total_pessoas_impactadas": total,
        "fonte": "blockchain",
    }
