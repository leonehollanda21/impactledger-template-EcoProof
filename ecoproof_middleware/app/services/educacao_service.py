"""
app/services/educacao_service.py
─────────────────────────────────
Serviço para gerenciar o ciclo de vida das Ações de Educação Ambiental.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.educacao import AcaoEducacional, StatusAcaoEducativa, AutorTipo, TipoAcaoEducativa
from app.models.cidadao import Cidadao
from app.models.user import User, UserRole
from app.models.nft import NFT
from app.schemas.educacao import (
    EducacaoCreateRequest,
    EducacaoResponse,
    EducacaoListResponse,
    EducacaoValidarRequest,
)
from app.schemas.nft import NFTResponse
from app.services import storage_service, nft_service
from app.services.blockchain_service import get_blockchain_service

logger = logging.getLogger(__name__)
_ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


def _to_response(acao: AcaoEducacional, nft: Optional[NFTResponse] = None) -> EducacaoResponse:
    """Converte o model ORM AcaoEducacional para EducacaoResponse."""
    return EducacaoResponse(
        id=acao.id,
        tipo_acao=acao.tipo_acao,
        num_pessoas=acao.num_pessoas,
        descricao=acao.descricao,
        foto_url=acao.foto_url,
        status=acao.status,
        autor_id=acao.autor_id,
        autor_tipo=acao.autor_tipo,
        validado_por=acao.validado_por,
        validado_por_tipo=acao.validado_por_tipo,
        motivo_rejeicao=acao.motivo_rejeicao,
        registry_tx_hash=acao.registry_tx_hash,
        mint_tx_hash=acao.mint_tx_hash,
        created_at=acao.created_at,
        validated_at=acao.validated_at,
        nft=nft,
    )


async def _enrich_nft(db: AsyncSession, acao: AcaoEducacional) -> Optional[NFTResponse]:
    """Busca o NFT associado à ação e o converte para NFTResponse."""
    if not acao.nfts:
        return None
    nft_obj = acao.nfts[0]
    return NFTResponse(
        id=nft_obj.id,
        token_id=nft_obj.token_id,
        cidadao_id=nft_obj.cidadao_id,
        assinado_por=nft_obj.assinado_por,
        metadata_url=nft_obj.metadata_url,
        tx_hash=nft_obj.tx_hash,
        created_at=nft_obj.created_at,
        limpeza_id=None,
        participacao_id=None,
        educacao_id=nft_obj.educacao_id,
        instituto_id=nft_obj.instituto_id,
        tipo_acao=None,
        foto_url=acao.foto_url,
    )


# ── 1. Criar ação (cidadão ou instituto) ──────────────────────────────────────

async def criar_acao(
    db: AsyncSession,
    autor: User,
    foto: UploadFile,
    data: EducacaoCreateRequest,
) -> EducacaoResponse:
    """
    Registra uma ação de educação ambiental:
    1. Upload da foto para o Cloudinary (pasta 'educacoes/')
    2. Cria o registro no banco com status='pendente'
    3. Chama o registro de prova no EcoProofRegistry.sol
    4. Atualiza a transação do registry e retorna
    """
    logger.info("Criando ação de educação ambiental — autor=%s tipo=%s", autor.id, data.tipo_acao.value)

    # 1. Upload da foto
    foto_url = await storage_service.upload_file(foto, "educacoes")
    logger.info("Foto de ação educativa enviada: %s", foto_url)

    # Determinar tipo de autor
    autor_tipo = AutorTipo.cidadao if autor.role == UserRole.cidadao else AutorTipo.instituto

    # 2. Criar AcaoEducacional no banco
    acao_id = uuid.uuid4()
    acao = AcaoEducacional(
        id=acao_id,
        autor_id=autor.id,
        autor_tipo=autor_tipo,
        tipo_acao=TipoAcaoEducativa(data.tipo_acao),
        num_pessoas=data.num_pessoas,
        descricao=data.descricao,
        foto_url=foto_url,
        status=StatusAcaoEducativa.pendente,
        created_at=datetime.now(timezone.utc),
    )
    db.add(acao)
    await db.flush()

    # 3. Registrar no EcoProofRegistry on-chain
    registry_tx_hash: Optional[str] = None
    try:
        blockchain = get_blockchain_service()
        wallet = autor.wallet_address or _ZERO_ADDRESS
        registry_tx_hash = await blockchain.registrar_educacao_registry(
            offchain_id=str(acao.id),
            foto_url=foto_url,
            num_pessoas=data.num_pessoas,
            actor_wallet=wallet,
        )
        acao.registry_tx_hash = registry_tx_hash
        db.add(acao)
        await db.flush()
        logger.info("Ação educativa registrada no Registry — tx=%s", registry_tx_hash)
    except Exception as exc:
        logger.warning(
            "Falha ao registrar ação educativa no Registry (blockchain indisponível): %s. "
            "Ação salva sem registry_tx_hash.",
            exc,
        )

    return _to_response(acao)


# ── 2. Validar ação (instituto ou admin) ──────────────────────────────────────

async def validar_acao(
    db: AsyncSession,
    acao_id: uuid.UUID,
    validador: User,
    data: EducacaoValidarRequest,
) -> EducacaoResponse:
    """
    Valida uma ação de educação ambiental pendente:
    - Admin pode validar qualquer ação
    - Instituto só valida se for de cidadão OU se for dele mesmo
    """
    logger.info("Validando ação %s por validador %s (aprovado=%s)", acao_id, validador.id, data.aprovado)

    # Busca a ação
    result = await db.execute(select(AcaoEducacional).where(AcaoEducacional.id == acao_id))
    acao = result.scalar_one_or_none()
    if acao is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ação educacional não encontrada.",
        )

    # Garante que está pendente
    if acao.status != StatusAcaoEducativa.pendente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Esta ação já foi validada. Status atual: '{acao.status.value}'.",
        )

    # Valida restrições do instituto
    if validador.role == UserRole.instituto:
        if not (acao.autor_tipo == AutorTipo.cidadao or acao.autor_id == validador.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Institutos só podem validar ações de cidadãos ou suas próprias ações.",
            )

    # Determinar issued_by
    issued_by = "admin" if validador.role == UserRole.admin else "instituto"
    validador_tipo = AutorTipo.admin if validador.role == UserRole.admin else AutorTipo.instituto

    # Se reprovado
    if not data.aprovado:
        if not data.motivo_rejeicao or not data.motivo_rejeicao.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="É obrigatório informar o motivo da rejeição.",
            )
        acao.status = StatusAcaoEducativa.rejeitada
        acao.motivo_rejeicao = data.motivo_rejeicao.strip()
        acao.validated_at = datetime.now(timezone.utc)
        acao.validado_por = validador.id
        acao.validado_por_tipo = validador_tipo
        db.add(acao)
        await db.flush()
        return _to_response(acao)

    # Se aprovado
    acao.status = StatusAcaoEducativa.aprovada
    acao.validated_at = datetime.now(timezone.utc)
    acao.validado_por = validador.id
    acao.validado_por_tipo = validador_tipo
    db.add(acao)
    await db.flush()

    # Busca autor
    autor_result = await db.execute(select(User).where(User.id == acao.autor_id))
    autor = autor_result.scalar_one_or_none()
    if autor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Autor da ação não encontrado no banco.",
        )

    # Minta o NFT
    nft_response = None
    try:
        nft_obj = await nft_service.mint_nft_educacao(db, acao, autor, issued_by)
        nft_response = NFTResponse(
            id=nft_obj.id,
            token_id=nft_obj.token_id,
            cidadao_id=nft_obj.cidadao_id,
            assinado_por=nft_obj.assinado_por,
            metadata_url=nft_obj.metadata_url,
            tx_hash=nft_obj.tx_hash,
            created_at=nft_obj.created_at,
            limpeza_id=None,
            participacao_id=None,
            educacao_id=nft_obj.educacao_id,
            instituto_id=nft_obj.instituto_id,
            tipo_acao=None,
            foto_url=acao.foto_url,
        )
    except Exception as exc:
        logger.exception("Falha ao mintar NFT de educação %s: %s", acao.id, exc)

    return _to_response(acao, nft=nft_response)


# ── 3. Obter ação por ID ──────────────────────────────────────────────────────

async def get_acao(
    db: AsyncSession,
    acao_id: uuid.UUID,
    user: User,
) -> EducacaoResponse:
    """Retorna o detalhe de uma ação. Cidadão só vê a própria."""
    result = await db.execute(select(AcaoEducacional).where(AcaoEducacional.id == acao_id))
    acao = result.scalar_one_or_none()

    if acao is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ação educacional não encontrada.",
        )

    # Se for cidadão, só pode ver a própria
    if user.role == UserRole.cidadao and acao.autor_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar esta ação educacional.",
        )

    nft_response = await _enrich_nft(db, acao)
    return _to_response(acao, nft=nft_response)


# ── 4. Listar ações pendentes (admin/instituto) ────────────────────────────────

async def list_acoes_pendentes(
    db: AsyncSession,
    page: int = 1,
    size: int = 20,
) -> list[EducacaoListResponse]:
    """Lista ações pendentes de validação, ordenadas por data de criação antiga primeiro."""
    size = min(size, 100)
    offset = (page - 1) * size

    result = await db.execute(
        select(AcaoEducacional)
        .where(AcaoEducacional.status == StatusAcaoEducativa.pendente)
        .order_by(AcaoEducacional.created_at.asc())
        .offset(offset)
        .limit(size)
    )
    acoes = result.scalars().all()

    return [
        EducacaoListResponse(
            id=a.id,
            tipo_acao=a.tipo_acao,
            num_pessoas=a.num_pessoas,
            status=a.status,
            created_at=a.created_at,
        )
        for a in acoes
    ]


# ── 5. Listar minhas ações (cidadão/instituto logado) ─────────────────────────

async def list_minhas_acoes(
    db: AsyncSession,
    autor_id: uuid.UUID,
    status_filter: Optional[StatusAcaoEducativa] = None,
) -> list[EducacaoListResponse]:
    """Lista o histórico de ações criadas pelo usuário logado."""
    query = select(AcaoEducacional).where(AcaoEducacional.autor_id == autor_id)

    if status_filter is not None:
        query = query.where(AcaoEducacional.status == status_filter)

    result = await db.execute(query.order_by(AcaoEducacional.created_at.desc()))
    acoes = result.scalars().all()

    return [
        EducacaoListResponse(
            id=a.id,
            tipo_acao=a.tipo_acao,
            num_pessoas=a.num_pessoas,
            status=a.status,
            created_at=a.created_at,
        )
        for a in acoes
    ]
