"""
app/controllers/denuncias_router.py
────────────────────────────────────
Rotas de Denúncia Ambiental Verificada (apenas rotas do cidadão e pública).

  [Cidadão]
  POST   /denuncias              → criar denúncia (multipart: foto + texto)
  GET    /denuncias/me           → listar denúncias do cidadão logado
  GET    /denuncias/{id}         → detalhe de uma denúncia (própria)

  [Público — sem autenticação]
  GET    /denuncias/{id}/verificar → verifica dados on-chain vs banco

  [Admin] → ver admin_router.py
    GET   /admin/denuncias
    PATCH /admin/denuncias/{id}/em-analise
    POST  /admin/denuncias/{id}/resolver
    PATCH /admin/denuncias/{id}/improcedente
"""
import uuid
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile, Query, status as http_status

from app.core.dependencies import CidadaoProfile, DBSession
from app.models.denuncia import StatusDenuncia, TipoProblema
from app.schemas.denuncia import (
    DenunciaResponse,
    DenunciaListResponse,
    DenunciaCreateRequest,
)
from app.services import denuncia_service

router = APIRouter(tags=["Denúncias Ambientais"])


# ════════════════════════════════════════════════════════════════════════════
#  ROTAS DO CIDADÃO
# ════════════════════════════════════════════════════════════════════════════

@router.post(
    "/denuncias",
    response_model=DenunciaResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="Registrar denúncia ambiental",
    description="""
Registra uma denúncia ambiental com foto do problema.

**Pipeline executado:**
1. Upload da foto para Cloudinary (`denuncias/problemas/`)
2. Geração de `proof_hash` (keccak256 da foto + cidadão + timestamp)
3. Registro do proof no **ValidationRegistry.sol** (Proof of Existence)
4. Denúncia salva com `status = registrada`

> ⚠️ O NFT **não** é gerado agora. Ele só é emitido após o admin confirmar a resolução.

**Campos do form:**
- `foto_problema`: Imagem JPEG/PNG do problema *(obrigatório)*
- `tipo_problema`: `descarte_ilegal | esgoto | queimada | poluicao_agua | poluicao_ar | desmatamento | outro`
- `descricao`: Texto descritivo do problema (20–1000 caracteres)
""",
)
async def criar_denuncia(
    cidadao: CidadaoProfile,
    db: DBSession,
    foto_problema: UploadFile = File(
        ..., description="Foto do problema ambiental (JPEG/PNG/WebP)"
    ),
    tipo_problema: TipoProblema = Form(
        ..., description="Tipo de problema ambiental reportado"
    ),
    descricao: str = Form(
        ..., min_length=20, max_length=1000,
        description="Descrição detalhada do problema (20–1000 caracteres)"
    ),
) -> DenunciaResponse:
    data = DenunciaCreateRequest(tipo_problema=tipo_problema, descricao=descricao)
    return await denuncia_service.criar_denuncia(
        db=db,
        cidadao=cidadao,
        foto_problema=foto_problema,
        data=data,
    )


@router.get(
    "/denuncias/me",
    response_model=list[DenunciaListResponse],
    summary="Listar minhas denúncias",
    description="""
Retorna todas as denúncias do cidadão autenticado.

Filtro opcional por `status`:
- `registrada` — recém criada, aguardando análise
- `em_analise` — admin está investigando
- `resolvida` — problema resolvido, NFT emitido
- `improcedente` — denúncia rejeitada
""",
)
async def list_minhas_denuncias(
    cidadao: CidadaoProfile,
    db: DBSession,
    status: Optional[StatusDenuncia] = Query(
        default=None,
        description="Filtrar por status da denúncia",
    ),
) -> list[DenunciaListResponse]:
    return await denuncia_service.list_denuncias_cidadao(
        db=db,
        cidadao_id=cidadao.id,
        status_filter=status,
    )


@router.get(
    "/denuncias/{denuncia_id}",
    response_model=DenunciaResponse,
    summary="Detalhe de uma denúncia",
    description="""
Retorna os dados completos de uma denúncia específica.

O cidadão autenticado **só pode consultar suas próprias denúncias**.
Retorna **403** se a denúncia pertencer a outro cidadão.
Inclui o NFT emitido quando `status = resolvida`.
""",
)
async def get_denuncia(
    denuncia_id: uuid.UUID,
    cidadao: CidadaoProfile,
    db: DBSession,
) -> DenunciaResponse:
    return await denuncia_service.get_denuncia(
        db=db,
        denuncia_id=denuncia_id,
        cidadao_id=cidadao.id,
    )


# ════════════════════════════════════════════════════════════════════════════
#  ROTA PÚBLICA — sem autenticação
# ════════════════════════════════════════════════════════════════════════════

@router.get(
    "/denuncias/{denuncia_id}/verificar",
    summary="Verificar denúncia on-chain (público)",
    description="""
Verifica a autenticidade da denúncia cruzando dados do banco com dados da blockchain.

> **Sem autenticação** — qualquer pessoa pode consultar para auditorias públicas.

**Dados retornados:**
- Dados off-chain: foto, descrição, status do banco
- Dados on-chain: `citizen` (wallet), `status` (REPORTADA/RESOLVIDA), `token_id` do NFT
- `proof_hash` e `blockchain_tx_hash` para verificação independente

Ideal para integradores de **IPTU Verde**, ONGs e auditorias públicas.
""",
)
async def verificar_denuncia(
    denuncia_id: uuid.UUID,
    db: DBSession,
) -> dict:
    from fastapi import HTTPException
    try:
        return await denuncia_service.verificar_denuncia(
            db=db,
            denuncia_id=denuncia_id,
        )
    except Exception as exc:
        exc_str = str(exc)
        if "AlreadyRegistered" in exc_str:
            raise HTTPException(
                status_code=400,
                detail="Denúncia já registrada na blockchain (AlreadyRegistered).",
            )
        if "DenunciaNotRegistered" in exc_str:
            raise HTTPException(
                status_code=400,
                detail="Denúncia encontrada no banco mas não registrada on-chain (DenunciaNotRegistered). "
                       "Pode ser uma denúncia criada antes da integração blockchain.",
            )
        raise
