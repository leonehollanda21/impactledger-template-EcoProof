"""
app/controllers/eventos_router.py
───────────────────────────────────
Rotas de eventos de mutirão e participações:

Eventos (CRUD):
  POST   /eventos                    → require_instituto
  GET    /eventos                    → público (com filtros)
  GET    /eventos/meus               → require_instituto
  GET    /eventos/{id}               → público
  PUT    /eventos/{id}               → require_instituto (dono)
  DELETE /eventos/{id}               → require_instituto (dono)

Participações (ações do cidadão):
  POST   /eventos/{id}/participar               → require_cidadao
  POST   /eventos/{id}/participacoes/{pid}/foto → require_cidadao

Gerenciamento (ações do instituto):
  GET    /eventos/{id}/participacoes            → require_instituto (dono)
  PATCH  /participacoes/{id}/aprovar            → require_instituto
  PATCH  /participacoes/{id}/rejeitar           → require_instituto

Emissão de NFTs em lote:
  POST   /eventos/{id}/emitir-nfts              → require_instituto (dono)

Histórico do cidadão:
  GET    /eventos/minhas-participacoes          → require_cidadao
"""
import uuid
from typing import Optional

from fastapi import APIRouter, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    CidadaoProfile,
    InstitutoProfile,
    DBSession,
)
from app.models.evento import TipoAcao, StatusEvento
from app.models.participacao import StatusParticipacao
from app.schemas.evento import (
    EventoCreateRequest,
    EventoUpdateRequest,
    EventoResponse,
    EventoDetalheResponse,
    EventoListResponse,
    MintLoteDetalheResponse,
    NFTStatusParticipacaoResponse,
)
from app.schemas.participacao import (
    ParticipacaoResponse,
    ParticipacaoStatusUpdate,
    ParticipacaoListResponse,
    MinhasParticipacoesPaginadas,
)
from app.services import evento_service, participacao_service, nft_service

router = APIRouter(tags=["Eventos & Participações"])


# ══════════════════════════════════════════════════════════════════════════════
#  EVENTOS — CRUD
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/eventos",
    response_model=EventoResponse,
    status_code=201,
    summary="Criar evento de mutirão (Instituto)",
    description="""
Cria um novo evento de mutirão ambiental.

**Acesso:** Instituto verificado.

O campo `foto_capa` é opcional. Todos os campos de texto são enviados
como partes do formulário multipart.
""",
)
async def create_evento(
    instituto: InstitutoProfile,
    db: DBSession,
    titulo: str = Form(..., min_length=3, max_length=200),
    tipo_acao: TipoAcao = Form(...),
    local: str = Form(..., min_length=3, max_length=300),
    data_evento: str = Form(..., description="Datetime ISO 8601, ex: 2026-06-15T09:00:00"),
    descricao: Optional[str] = Form(None, max_length=2000),
    foto_capa: Optional[UploadFile] = File(None, description="Imagem de capa (JPEG/PNG)"),
) -> EventoResponse:
    from datetime import datetime
    data = EventoCreateRequest(
        titulo=titulo,
        descricao=descricao,
        tipo_acao=tipo_acao,
        local=local,
        data_evento=datetime.fromisoformat(data_evento),
    )
    return await evento_service.create_evento(db, instituto, data, foto_capa)


@router.get(
    "/eventos",
    response_model=EventoListResponse,
    summary="Listar eventos (público)",
    description="Lista eventos com filtros opcionais por status e tipo de ação. Paginado.",
)
async def list_eventos(
    db: DBSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: StatusEvento = Query(default=StatusEvento.ativo),
    tipo_acao: Optional[TipoAcao] = Query(default=None),
) -> EventoListResponse:
    return await evento_service.list_eventos(
        db, page=page, page_size=page_size,
        status_filter=status, tipo_acao=tipo_acao,
    )


@router.get(
    "/eventos/meus",
    response_model=EventoListResponse,
    summary="Meus eventos (Instituto)",
    description="Lista todos os eventos do instituto autenticado (todos os status). Paginado.",
)
async def list_meus_eventos(
    instituto: InstitutoProfile,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> EventoListResponse:
    return await evento_service.list_eventos_instituto(
        db, instituto_id=instituto.id, page=page, page_size=page_size,
    )


@router.get(
    "/eventos/minhas-participacoes",
    response_model=MinhasParticipacoesPaginadas,
    summary="Minhas participações (Cidadão)",
    description="Histórico paginado de participações do cidadão autenticado.",
)
async def minhas_participacoes(
    cidadao: CidadaoProfile,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> MinhasParticipacoesPaginadas:
    return await participacao_service.list_minhas_participacoes(
        db, cidadao_id=cidadao.id, page=page, page_size=page_size,
    )


@router.get(
    "/eventos/{evento_id}",
    response_model=EventoResponse,
    summary="Detalhe de evento (público)",
    description="Retorna dados públicos de um evento com total de participantes.",
)
async def get_evento(
    evento_id: uuid.UUID,
    db: DBSession,
) -> EventoResponse:
    return await evento_service.get_evento(db, evento_id)


@router.put(
    "/eventos/{evento_id}",
    response_model=EventoResponse,
    summary="Atualizar evento (Instituto dono)",
    description="""
Atualiza campos de um evento. Apenas o instituto dono pode editar.
Todos os campos são opcionais. A foto de capa pode ser substituída.
""",
)
async def update_evento(
    evento_id: uuid.UUID,
    instituto: InstitutoProfile,
    db: DBSession,
    titulo: Optional[str] = Form(None, min_length=3, max_length=200),
    descricao: Optional[str] = Form(None, max_length=2000),
    local: Optional[str] = Form(None, min_length=3, max_length=300),
    data_evento: Optional[str] = Form(None),
    status: Optional[StatusEvento] = Form(None),
    foto_capa: Optional[UploadFile] = File(None),
) -> EventoResponse:
    from datetime import datetime
    data = EventoUpdateRequest(
        titulo=titulo,
        descricao=descricao,
        local=local,
        data_evento=datetime.fromisoformat(data_evento) if data_evento else None,
        status=status,
    )
    return await evento_service.update_evento(db, evento_id, instituto.id, data, foto_capa)


@router.delete(
    "/eventos/{evento_id}",
    response_model=EventoResponse,
    summary="Cancelar evento (Instituto dono)",
    description="Cancela um evento (soft delete: status → 'cancelado'). Apenas o instituto dono.",
)
async def delete_evento(
    evento_id: uuid.UUID,
    instituto: InstitutoProfile,
    db: DBSession,
) -> EventoResponse:
    return await evento_service.delete_evento(db, evento_id, instituto.id)


# ══════════════════════════════════════════════════════════════════════════════
#  PARTICIPAÇÕES — AÇÕES DO CIDADÃO
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/eventos/{evento_id}/participar",
    response_model=ParticipacaoResponse,
    status_code=201,
    summary="Fazer check-in em evento (Cidadão)",
    description="""
Registra a presença do cidadão em um evento (status = **confirmado**).

Retorna 409 se o cidadão já estiver inscrito.
Retorna 422 se o evento não estiver ativo.
""",
)
async def confirmar_presenca(
    evento_id: uuid.UUID,
    cidadao: CidadaoProfile,
    db: DBSession,
) -> ParticipacaoResponse:
    return await participacao_service.confirmar_presenca(db, cidadao.id, evento_id)


@router.post(
    "/eventos/{evento_id}/participacoes/{participacao_id}/foto",
    response_model=ParticipacaoResponse,
    summary="Enviar foto de participação (Cidadão)",
    description="""
Cidadão envia foto comprovando sua participação no evento.

O status muda para **foto_enviada** após o upload.
A foto é analisada pelo Google Vision para verificar ação ambiental.

Retorna 403 se a participação não pertencer ao cidadão.
Retorna 422 se o status atual não for `confirmado` ou `foto_enviada`.
""",
)
async def enviar_foto_participacao(
    evento_id: uuid.UUID,
    participacao_id: uuid.UUID,
    cidadao: CidadaoProfile,
    db: DBSession,
    foto: UploadFile = File(..., description="Foto da participação no evento (JPEG/PNG/WebP)"),
) -> ParticipacaoResponse:
    return await participacao_service.enviar_foto(db, participacao_id, cidadao.id, foto)


# ── rota movida acima de /eventos/{evento_id} para evitar conflito de rota ──


# ══════════════════════════════════════════════════════════════════════════════
#  PARTICIPAÇÕES — GERENCIAMENTO PELO INSTITUTO
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/eventos/{evento_id}/participacoes",
    response_model=ParticipacaoListResponse,
    summary="Listar participantes do evento (Instituto dono)",
    description="""
Lista todos os participantes de um evento, com filtro opcional por status.

**Acesso:** Somente o instituto dono do evento.

Filtros de status: `confirmado | foto_enviada | aprovado | rejeitado`
""",
)
async def list_participacoes_evento(
    evento_id: uuid.UUID,
    instituto: InstitutoProfile,
    db: DBSession,
    status: Optional[StatusParticipacao] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> ParticipacaoListResponse:
    return await participacao_service.list_participacoes_evento(
        db, evento_id=evento_id, instituto_id=instituto.id,
        status_filter=status, page=page, page_size=page_size,
    )


@router.get(
    "/eventos/{evento_id}/detalhe",
    response_model=EventoDetalheResponse,
    summary="Detalhe completo do evento (Instituto dono)",
    description="""
Retorna o evento com lista completa de participantes e contadores por status.

**Acesso:** Somente o instituto dono do evento.
""",
)
async def get_evento_detalhe(
    evento_id: uuid.UUID,
    instituto: InstitutoProfile,
    db: DBSession,
) -> EventoDetalheResponse:
    return await evento_service.get_evento_detalhe(db, evento_id, instituto.id)


@router.patch(
    "/participacoes/{participacao_id}/aprovar",
    response_model=ParticipacaoResponse,
    summary="Aprovar participação (Instituto)",
    description="""
Instituto aprova a participação de um cidadão.

**Pré-condição:** Status deve ser `foto_enviada`.

Retorna 403 se o instituto não for dono do evento da participação.
Retorna 422 se o status atual não for `foto_enviada`.
""",
)
async def aprovar_participacao(
    participacao_id: uuid.UUID,
    instituto: InstitutoProfile,
    db: DBSession,
) -> ParticipacaoResponse:
    return await participacao_service.aprovar_participacao(
        db, participacao_id=participacao_id, instituto_id=instituto.id,
    )


@router.patch(
    "/participacoes/{participacao_id}/rejeitar",
    response_model=ParticipacaoResponse,
    summary="Rejeitar participação (Instituto)",
    description="""
Instituto rejeita a participação com um motivo obrigatório (mínimo 10 caracteres).

Retorna 403 se o instituto não for dono do evento.
Retorna 422 se o status já for `aprovado` ou `rejeitado`.
""",
)
async def rejeitar_participacao(
    participacao_id: uuid.UUID,
    instituto: InstitutoProfile,
    db: DBSession,
    body: ParticipacaoStatusUpdate,
) -> ParticipacaoResponse:
    return await participacao_service.rejeitar_participacao(
        db,
        participacao_id=participacao_id,
        instituto_id=instituto.id,
        motivo=body.motivo_rejeicao,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  EMISSÃO DE NFTs EM LOTE
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/eventos/{evento_id}/emitir-nfts",
    response_model=MintLoteDetalheResponse,
    summary="Emitir NFTs em lote (Instituto dono)",
    description="""
Emite NFTs Soulbound para **todos os participantes aprovados** do evento que ainda não possuem NFT.

**Acesso:** Somente o instituto dono do evento.

**Processo:**
1. Busca participações com status `aprovado` sem NFT
2. Para cada uma: gera metadata ERC-721, salva no Cloudinary, minta on-chain (blockchain real ou simulado)
3. Credita **30 pontos** por cidadão
4. Erros individuais não interrompem o lote
5. Retorna resultado detalhado por participante: `token_id`, `tx_hash`, ou `erro`

**Idempotente:** Participações que já possuem NFT são incluídas no resultado como sucesso sem re-mintar.
""",
)
async def emitir_nfts_lote(
    evento_id: uuid.UUID,
    instituto: InstitutoProfile,
    db: DBSession,
) -> MintLoteDetalheResponse:
    from sqlalchemy import select
    from app.models.evento import Evento
    from fastapi import HTTPException, status

    ev_result = await db.execute(select(Evento).where(Evento.id == evento_id))
    evento = ev_result.scalar_one_or_none()
    if evento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado.")
    if evento.instituto_id != instituto.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para emitir NFTs neste evento.",
        )

    return await nft_service.mint_lote_evento(db, evento_id, instituto)


@router.get(
    "/eventos/{evento_id}/nfts-status",
    response_model=list[NFTStatusParticipacaoResponse],
    summary="Status de NFT por participante aprovado (Instituto dono)",
    description="""
Retorna quais participantes aprovados do evento já possuem NFT emitido e quais ainda não possuem.

**Acesso:** Somente o instituto dono do evento.
""",
)
async def get_nfts_status(
    evento_id: uuid.UUID,
    instituto: InstitutoProfile,
    db: DBSession,
) -> list[NFTStatusParticipacaoResponse]:
    from sqlalchemy import select
    from app.models.evento import Evento
    from app.models.participacao import Participacao, StatusParticipacao
    from app.models.nft import NFT
    from app.models.cidadao import Cidadao
    from app.models.user import User
    from fastapi import HTTPException, status

    ev_result = await db.execute(select(Evento).where(Evento.id == evento_id))
    evento = ev_result.scalar_one_or_none()
    if evento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado.")
    if evento.instituto_id != instituto.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar este evento.",
        )

    # Todas as participações aprovadas
    part_result = await db.execute(
        select(Participacao).where(
            Participacao.evento_id == evento_id,
            Participacao.status == StatusParticipacao.aprovado,
        )
    )
    participacoes = part_result.scalars().all()

    if not participacoes:
        return []

    # NFTs existentes para essas participações
    participacao_ids = [p.id for p in participacoes]
    nfts_result = await db.execute(
        select(NFT).where(NFT.participacao_id.in_(participacao_ids))
    )
    nfts_map = {nft.participacao_id: nft for nft in nfts_result.scalars().all()}

    resposta = []
    for participacao in participacoes:
        # Busca nome do cidadão
        cid_result = await db.execute(
            select(Cidadao).where(Cidadao.id == participacao.cidadao_id)
        )
        cidadao = cid_result.scalar_one_or_none()
        cidadao_nome = "—"
        if cidadao and cidadao.user:
            cidadao_nome = cidadao.user.name or "—"

        nft = nfts_map.get(participacao.id)
        resposta.append(NFTStatusParticipacaoResponse(
            participacao_id=participacao.id,
            cidadao_id=participacao.cidadao_id,
            cidadao_nome=cidadao_nome,
            tem_nft=nft is not None,
            token_id=nft.token_id if nft else None,
            tx_hash=nft.tx_hash if nft else None,
            nft_emitido_em=nft.created_at.isoformat() if nft else None,
        ))

    return resposta
