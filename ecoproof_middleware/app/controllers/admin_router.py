"""
app/controllers/admin_router.py
────────────────────────────────
Rotas de administração — todas requerem role=admin.

  GET   /admin/dashboard
  GET   /admin/institutos           (filtro: verified=true/false)
  PATCH /admin/institutos/{id}/aprovar
  PATCH /admin/institutos/{id}/suspender
  GET   /admin/validacoes           (filtro: resultado=true/false)

  GET   /admin/nfts                 (lista todos NFTs emitidos)
  GET   /admin/denuncias            (filtro: status)
  PATCH /admin/denuncias/{id}/em-analise
  POST  /admin/denuncias/{id}/resolver
  PATCH /admin/denuncias/{id}/improcedente

  GET   /admin/educacoes            (filtro: status)
  PATCH /admin/educacoes/{id}/validar
"""
import uuid
from typing import Optional

from fastapi import APIRouter, File, Query, UploadFile

from app.core.dependencies import AdminUser, DBSession
from app.models.denuncia import StatusDenuncia
from app.models.educacao import StatusAcaoEducativa
from app.schemas.admin import (
    InstitutoAdminListResponse,
    AcaoAdminResponse,
    ValidacaoAdminListResponse,
    DashboardStats,
    NFTAdminListResponse,
    DenunciaAdminSummaryListResponse,
    EducacaoAdminListResponse,
)
from app.schemas.denuncia import DenunciaResponse, DenunciaImprocedenciaRequest
from app.schemas.educacao import EducacaoValidarRequest, EducacaoResponse
from app.services import admin_service, denuncia_service, educacao_service

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get(
    "/dashboard",
    response_model=DashboardStats,
    summary="Dashboard — estatísticas da plataforma",
)
async def dashboard(
    _admin: AdminUser,
    db: DBSession,
) -> DashboardStats:
    return await admin_service.get_dashboard_stats(db)


# ── Institutos ────────────────────────────────────────────────────────────────

@router.get(
    "/institutos",
    response_model=InstitutoAdminListResponse,
    summary="Listar institutos",
    description="""
Lista institutos com contagens de eventos e NFTs emitidos.

**Filtro `verified`:**
- `true` → somente verificados
- `false` → somente pendentes de verificação
- *(omitir)* → todos
""",
)
async def list_institutos(
    _admin: AdminUser,
    db: DBSession,
    verified: Optional[bool] = Query(
        default=None,
        description="Filtrar por status de verificação (true/false/null=todos)",
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> InstitutoAdminListResponse:
    return await admin_service.list_institutos(
        db,
        verified_filter=verified,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/institutos/{instituto_id}/aprovar",
    response_model=AcaoAdminResponse,
    summary="Aprovar instituto",
    description="""
Aprova um instituto pendente:
- `verified = True`
- `verified_at = agora`
- `User.is_active = True` (desbloqueia o login)

Retorna 422 se o instituto já estiver verificado.
""",
)
async def aprovar_instituto(
    instituto_id: uuid.UUID,
    _admin: AdminUser,
    db: DBSession,
) -> AcaoAdminResponse:
    return await admin_service.aprovar_instituto(db, instituto_id)


@router.patch(
    "/institutos/{instituto_id}/suspender",
    response_model=AcaoAdminResponse,
    summary="Suspender instituto",
    description="""
Suspende um instituto ativo:
- `verified = False`
- `User.is_active = False` (bloqueia o login imediatamente)

Retorna 422 se o instituto já estiver suspenso.
""",
)
async def suspender_instituto(
    instituto_id: uuid.UUID,
    _admin: AdminUser,
    db: DBSession,
) -> AcaoAdminResponse:
    return await admin_service.suspender_instituto(db, instituto_id)


# ── Validações ────────────────────────────────────────────────────────────────

@router.get(
    "/validacoes",
    response_model=ValidacaoAdminListResponse,
    summary="Histórico de validações (limpeza/mutirão)",
    description="""
Lista todas as validações de limpezas e participações em eventos.

**Filtro `resultado`:**
- `true` → somente aprovadas
- `false` → somente reprovadas
- *(omitir)* → todas
""",
)
async def list_validacoes(
    _admin: AdminUser,
    db: DBSession,
    resultado: Optional[bool] = Query(
        default=None,
        description="Filtrar por resultado (true=aprovadas / false=reprovadas)",
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ValidacaoAdminListResponse:
    return await admin_service.list_validacoes(
        db,
        resultado_filter=resultado,
        page=page,
        page_size=page_size,
    )


# ── NFTs ──────────────────────────────────────────────────────────────────────

@router.get(
    "/nfts",
    response_model=NFTAdminListResponse,
    summary="Listar todos os NFTs emitidos",
    description="Visão centralizada de todos os NFTs com dados do cidadão dono.",
)
async def list_nfts(
    _admin: AdminUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> NFTAdminListResponse:
    return await admin_service.list_all_nfts(db, page=page, page_size=page_size)


# ── Denúncias ─────────────────────────────────────────────────────────────────

@router.get(
    "/denuncias",
    response_model=DenunciaAdminSummaryListResponse,
    summary="Listar todas as denúncias",
    description="""
Lista todas as denúncias com paginação e filtro opcional por status:
- `registrada` | `em_analise` | `resolvida` | `improcedente`
""",
)
async def list_denuncias(
    _admin: AdminUser,
    db: DBSession,
    status: Optional[StatusDenuncia] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> DenunciaAdminSummaryListResponse:
    return await admin_service.list_all_denuncias_admin(
        db, status_filter=status, page=page, page_size=page_size
    )


@router.patch(
    "/denuncias/{denuncia_id}/em-analise",
    response_model=DenunciaResponse,
    summary="Iniciar análise de denúncia",
    description="Muda o status de `registrada` → `em_analise`.",
)
async def admin_em_analise(
    denuncia_id: uuid.UUID,
    admin: AdminUser,
    db: DBSession,
) -> DenunciaResponse:
    return await denuncia_service.marcar_em_analise(
        db=db,
        denuncia_id=denuncia_id,
        admin_id=admin.id,
    )


@router.post(
    "/denuncias/{denuncia_id}/resolver",
    response_model=DenunciaResponse,
    summary="Confirmar resolução + emitir NFT",
    description="""
Confirma que o problema foi resolvido.
- Upload da foto de resolução
- Minta NFT Fiscal Ambiental Soulbound
- Credita 50 pontos ao cidadão
""",
)
async def admin_resolver_denuncia(
    denuncia_id: uuid.UUID,
    admin: AdminUser,
    db: DBSession,
    foto_resolucao: UploadFile = File(..., description="Foto comprovando a resolução do problema"),
) -> DenunciaResponse:
    return await denuncia_service.confirmar_resolucao(
        db=db,
        denuncia_id=denuncia_id,
        foto_resolucao=foto_resolucao,
        admin_id=admin.id,
    )


@router.patch(
    "/denuncias/{denuncia_id}/improcedente",
    response_model=DenunciaResponse,
    summary="Rejeitar denúncia (improcedente)",
    description="""
Marca a denúncia como improcedente (falsa, duplicada ou sem evidências suficientes).

**Body JSON:**
```json
{ "motivo": "Denúncia duplicada — problema já registrado em #abc123." }
```
""",
)
async def admin_improcedente(
    denuncia_id: uuid.UUID,
    admin: AdminUser,
    db: DBSession,
    body: DenunciaImprocedenciaRequest,
) -> DenunciaResponse:
    return await denuncia_service.marcar_improcedente(
        db=db,
        denuncia_id=denuncia_id,
        motivo=body.motivo,
        admin_id=admin.id,
    )


# ── Educação ──────────────────────────────────────────────────────────────────

@router.get(
    "/educacoes",
    response_model=EducacaoAdminListResponse,
    summary="Listar ações educativas",
    description="""
Lista todas as ações de educação ambiental.

**Filtro `status`:**
- `pendente` | `aprovada` | `rejeitada`
""",
)
async def list_educacoes(
    _admin: AdminUser,
    db: DBSession,
    status: Optional[StatusAcaoEducativa] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> EducacaoAdminListResponse:
    return await admin_service.list_all_educacoes_admin(
        db, status_filter=status, page=page, page_size=page_size
    )


@router.patch(
    "/educacoes/{acao_id}/validar",
    response_model=EducacaoResponse,
    summary="Aprovar ou rejeitar ação educativa",
    description="""
Admin valida uma ação de educação ambiental.

**Body JSON:**
```json
{ "aprovado": true }
{ "aprovado": false, "motivo_rejeicao": "Foto insuficiente." }
```

Se aprovado: minta o NFT ECED e credita pontos.
""",
)
async def admin_validar_educacao(
    acao_id: uuid.UUID,
    body: EducacaoValidarRequest,
    admin: AdminUser,
    db: DBSession,
) -> EducacaoResponse:
    return await educacao_service.validar_acao(
        db=db,
        acao_id=acao_id,
        validador=admin,
        data=body,
    )
