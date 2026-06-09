"""
app/controllers/limpezas_router.py
────────────────────────────────────
Rotas de limpeza individual:
  POST /limpezas           → registrar limpeza (multipart)
  GET  /limpezas/me        → histórico paginado do cidadão
  GET  /limpezas/{id}      → detalhe de uma limpeza

Todas as rotas requerem autenticação de cidadão (CidadaoProfile).
"""
import uuid
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CidadaoProfile, DBSession
from app.models.evento import TipoAcao
from app.models.limpeza_individual import StatusLimpeza
from app.schemas.limpeza import (
    LimpezaResultResponse,
    LimpezaResponse,
    LimpezaHistoricoResponse,
)
from app.services import limpeza_service

router = APIRouter(prefix="/limpezas", tags=["Limpezas Individuais"])


# ── POST /limpezas ─────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=LimpezaResultResponse,
    status_code=201,
    summary="Registrar limpeza individual",
    description="""
Registra uma ação de limpeza individual com upload das fotos antes/depois.

**Pipeline executado:**
1. Upload das fotos para AWS S3
2. Análise das imagens com Google Vision AI
3. Validação automática (score 0–1, aprovado se ≥ 0.5)
4. Se aprovado: NFT mintado + **10 pontos** creditados ao cidadão
5. Retorna resultado completo com NFT (se gerado)

**Campos do form:**
- `foto_antes`: Imagem JPEG/PNG do local **antes** da limpeza *(obrigatório)*
- `foto_depois`: Imagem JPEG/PNG do local **depois** da limpeza *(obrigatório)*
- `tipo_acao`: Enum — `lixo_rua | praia | corrego | queimada | outro` *(obrigatório)*
""",
)
async def create_limpeza(
    cidadao: CidadaoProfile,
    db: DBSession,
    foto_antes: UploadFile = File(..., description="Foto ANTES da limpeza (JPEG/PNG/WebP)"),
    foto_depois: UploadFile = File(..., description="Foto DEPOIS da limpeza (JPEG/PNG/WebP)"),
    tipo_acao: TipoAcao = Form(..., description="Tipo de ação ambiental realizada"),
) -> LimpezaResultResponse:
    return await limpeza_service.create_limpeza(
        db=db,
        cidadao=cidadao,
        foto_antes=foto_antes,
        foto_depois=foto_depois,
        tipo_acao=tipo_acao,
    )


# ── GET /limpezas/me ───────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=LimpezaHistoricoResponse,
    summary="Histórico de limpezas do cidadão",
    description="""
Retorna o histórico paginado de limpezas do cidadão autenticado.

Suporta filtro por `status` (`pendente | aprovado | reprovado`) e paginação
via `page` e `page_size` (máx 100 itens por página).
""",
)
async def list_minhas_limpezas(
    cidadao: CidadaoProfile,
    db: DBSession,
    page: int = Query(default=1, ge=1, description="Página (começa em 1)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Itens por página"),
    status: Optional[StatusLimpeza] = Query(
        default=None,
        description="Filtrar por status: pendente | aprovado | reprovado",
    ),
) -> LimpezaHistoricoResponse:
    return await limpeza_service.list_limpezas_cidadao(
        db=db,
        cidadao_id=cidadao.id,
        page=page,
        page_size=page_size,
        status_filter=status,
    )


# ── GET /limpezas/{limpeza_id} ────────────────────────────────────────────────

@router.get(
    "/{limpeza_id}",
    response_model=LimpezaResponse,
    summary="Detalhe de uma limpeza",
    description="""
Retorna os dados completos de uma limpeza específica.

O cidadão autenticado só pode consultar suas próprias limpezas.
Retorna **403** se a limpeza pertencer a outro cidadão.
""",
)
async def get_limpeza(
    limpeza_id: uuid.UUID,
    cidadao: CidadaoProfile,
    db: DBSession,
) -> LimpezaResponse:
    return await limpeza_service.get_limpeza(
        db=db,
        limpeza_id=limpeza_id,
        cidadao_id=cidadao.id,
    )
