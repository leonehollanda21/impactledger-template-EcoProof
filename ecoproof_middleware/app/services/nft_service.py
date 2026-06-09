"""
app/services/nft_service.py
─────────────────────────────
Geração de metadata ERC-721, upload e mint de NFTs com integração blockchain.

Cobre dois fluxos:
  - mint_nft_individual: limpeza autônoma (assinado_por='ecoproof', +10 pts)
  - mint_nft_evento:     participação em mutirão (assinado_por='instituto', +30 pts)
  - mint_lote_evento:    emissão em lote para todos aprovados de um evento

Integração blockchain:
  - Se BLOCKCHAIN_ENABLED=true: usa Web3.py para mint real + registro de proof
  - Se BLOCKCHAIN_ENABLED=false: fallback para modo simulado (desenvolvimento local)
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cidadao import Cidadao
from app.models.instituto import Instituto
from app.models.limpeza_individual import LimpezaIndividual
from app.models.nft import NFT, AssinadoPor
from app.models.participacao import Participacao, StatusParticipacao
from app.models.ponto_verde import PontoVerde
from app.models.user import User
from app.models.denuncia import Denuncia
from app.models.educacao import AcaoEducacional
from app.schemas.nft import NFTMetadata, NFTResponse
from app.services.storage_service import upload_json
from app.services.blockchain_service import (
    get_blockchain_service,
    compute_keccak256,
)

logger = logging.getLogger(__name__)

# ── Constantes de pontos ──────────────────────────────────────────────────────
POINTS_PER_LIMPEZA = 10   # limpeza individual autônoma
POINTS_PER_EVENTO = 30    # participação em mutirão de instituto


# ── Metadata: limpeza individual ──────────────────────────────────────────────

def generate_metadata(
    limpeza: LimpezaIndividual,
    cidadao: Cidadao,
) -> NFTMetadata:
    """Gera NFTMetadata no padrão ERC-721 / OpenSea para limpeza individual."""
    tipo_label = limpeza.tipo_acao.value.replace("_", " ").title()
    data_formatada = limpeza.created_at.strftime("%d/%m/%Y") if limpeza.created_at else "—"

    return NFTMetadata(
        name=f"EcoProof — {tipo_label} #{str(limpeza.id)[:8].upper()}",
        description=(
            f"NFT Soulbound (intransferível) de comprovação de ação ambiental "
            f"emitido pela plataforma EcoProof. "
            f"Tipo: {tipo_label}. Data: {data_formatada}. "
            f"Esta ação foi validada por IA e registrada na blockchain."
        ),
        image=limpeza.foto_depois_url,
        external_url=f"https://ecoproof.io/nft/{limpeza.id}",
        attributes=[
            {"trait_type": "Tipo de Ação", "value": tipo_label},
            {"trait_type": "Data", "value": data_formatada, "display_type": "date"},
            {"trait_type": "Assinado por", "value": "EcoProof"},
            {"trait_type": "Validação", "value": "Google Vision AI"},
            {"trait_type": "Token Type", "value": "Soulbound (EIP-5192)"},
            {
                "trait_type": "Pontos Concedidos",
                "value": POINTS_PER_LIMPEZA,
                "display_type": "number",
            },
        ],
        ecoproof_version="1.0",
    )


async def save_metadata_s3(metadata: NFTMetadata, limpeza_id: uuid.UUID) -> str:
    """Serializa metadata JSON e faz upload para o S3. Retorna URL pública."""
    key = f"nfts/metadata/{limpeza_id}.json"
    content = json.dumps(metadata.model_dump(), ensure_ascii=False, indent=2).encode("utf-8")
    url = await upload_json(content, key)
    logger.info("NFT metadata salva: %s", url)
    return url


# ── Mint: limpeza individual ──────────────────────────────────────────────────

async def mint_nft_individual(
    db: AsyncSession,
    limpeza: LimpezaIndividual,
    cidadao: Cidadao,
) -> NFTResponse:
    """
    Minta NFT Soulbound para limpeza individual aprovada.
      assinado_por = 'ecoproof' | pontos = POINTS_PER_LIMPEZA (10)

    Integração blockchain:
      1. Gera metadata e salva no S3
      2. Minta NFT on-chain via blockchain_service (ou simulado)
      3. Registra proof no ValidationRegistry on-chain
      4. Salva NFT no banco de dados
      5. Credita pontos ao cidadão
    """
    blockchain = get_blockchain_service()

    # Gera e salva metadata
    metadata = generate_metadata(limpeza, cidadao)
    metadata_url = await save_metadata_s3(metadata, limpeza.id)

    # Calcula hashes para o Registry (Proof of Existence)
    metadata_json = json.dumps(metadata.model_dump(), ensure_ascii=False).encode("utf-8")
    metadata_hash = compute_keccak256(metadata_json)

    # Mint on-chain (ou simulado)
    wallet_address = (cidadao.user.wallet_address if cidadao.user else None) or "0x0000000000000000000000000000000000000000"
    
    token_id, tx_hash = await blockchain.mint_limpeza(
        to_address=wallet_address,
        uri=metadata_url,
        offchain_id=str(limpeza.id),
        action_type=limpeza.tipo_acao.value,
        ai_score=int(limpeza.validacoes[0].score * 100) if limpeza.validacoes else 0,
    )

    # Registra proof on-chain (Proof of Existence)
    # Usa URL da foto como proxy para hash (em produção: hash do conteúdo real da foto)
    photo_after_hash = compute_keccak256(
        (limpeza.foto_depois_url or "").encode("utf-8")
    )
    photo_before_hash = compute_keccak256(
        (limpeza.foto_antes_url or "").encode("utf-8")
    )

    await blockchain.register_limpeza_proof(
        offchain_id=str(limpeza.id),
        photo_after_hash=photo_after_hash,
        photo_before_hash=photo_before_hash,
        metadata_hash=metadata_hash,
        ai_score=int(limpeza.validacoes[0].score * 100) if limpeza.validacoes else 0,
        action_type=limpeza.tipo_acao.value,
        aprovado=True,
    )

    logger.info(
        "NFT limpeza mintado — token_id=%s tx_hash=%s limpeza_id=%s",
        token_id, tx_hash, limpeza.id,
    )

    # Salva no banco de dados
    nft = NFT(
        id=uuid.uuid4(),
        token_id=token_id,
        cidadao_id=cidadao.id,
        limpeza_id=limpeza.id,
        participacao_id=None,
        assinado_por=AssinadoPor.ecoproof,
        instituto_id=None,
        metadata_url=metadata_url,
        tx_hash=tx_hash,
        created_at=datetime.now(tz=timezone.utc),
    )
    db.add(nft)

    cidadao.total_points += POINTS_PER_LIMPEZA
    db.add(cidadao)
    await db.flush()

    logger.info(
        "Cidadão %s recebeu %d pontos. Total: %d",
        cidadao.id, POINTS_PER_LIMPEZA, cidadao.total_points,
    )

    return NFTResponse(
        id=nft.id,
        token_id=nft.token_id,
        cidadao_id=nft.cidadao_id,
        assinado_por=nft.assinado_por,
        metadata_url=nft.metadata_url,
        tx_hash=nft.tx_hash,
        created_at=nft.created_at,
        limpeza_id=nft.limpeza_id,
        participacao_id=None,
        instituto_id=None,
        tipo_acao=limpeza.tipo_acao,
        foto_url=limpeza.foto_depois_url,
    )


def generate_metadata_guardiao(
    ponto: PontoVerde,
    cidadao: Cidadao,
) -> NFTMetadata:
    data_formatada = ponto.data_inicio.strftime("%d/%m/%Y") if ponto.data_inicio else "—"
    return NFTMetadata(
        name=f"EcoProof — Guardião {cidadao.user.name if cidadao.user else 'Cidadão'} #{str(ponto.id)[:8].upper()}",
        description=(
            f"NFT Soulbound de Guardião emitido para {cidadao.user.name if cidadao.user else 'um cidadão'} "
            f"pela adoção do ponto verde '{ponto.nome}'. "
            f"Adoção iniciada em {data_formatada} e concluída após 3 check-ins mensais."
        ),
        image=ponto.foto_inicial_url or "https://ecoproof.io/default-guardiao.png",
        external_url=f"https://ecoproof.io/pontos-verdes/{ponto.id}",
        attributes=[
            {"trait_type": "Ponto Verde", "value": ponto.nome},
            {"trait_type": "Categoria", "value": ponto.categoria.value.replace("_", " ").title()},
            {"trait_type": "Guardião", "value": cidadao.user.name if cidadao.user else "—"},
            {"trait_type": "Data de Início", "value": data_formatada, "display_type": "date"},
            {"trait_type": "Token Type", "value": "Soulbound (EIP-5192)"},
            {"trait_type": "Adoção Concluída", "value": "3 meses"},
            {
                "trait_type": "Pontos Concedidos",
                "value": 80,
                "display_type": "number",
            },
        ],
        ecoproof_version="1.0",
    )


async def mint_nft_guardiao(
    db: AsyncSession,
    ponto: PontoVerde,
) -> NFTResponse:
    """
    Minta NFT de guardião para a conclusão de 3 check-ins no ponto verde.

    Usa o mesmo contrato de mint genérico do fluxo de limpeza quando em modo simulado.
    """
    blockchain = get_blockchain_service()
    result = await db.execute(select(Cidadao).where(Cidadao.id == ponto.guardiao_id))
    cidadao = result.scalar_one_or_none()

    if cidadao is None:
        raise RuntimeError("Cidadão guardião não encontrado para mint de NFT de guardião.")

    metadata = generate_metadata_guardiao(ponto, cidadao)
    key = f"nfts/metadata/guardiao_{ponto.id}.json"
    content = json.dumps(metadata.model_dump(), ensure_ascii=False, indent=2).encode("utf-8")
    metadata_url = await upload_json(content, key)
    metadata_hash = compute_keccak256(content)

    wallet_address = (cidadao.user.wallet_address if cidadao.user else None) or "0x0000000000000000000000000000000000000000"
    token_id, tx_hash = await blockchain.mint_limpeza(
        to_address=wallet_address,
        uri=metadata_url,
        offchain_id=str(ponto.id),
        action_type="outro",
        ai_score=0,
    )

    photo_hash = compute_keccak256((ponto.foto_inicial_url or "").encode("utf-8"))
    await blockchain.register_limpeza_proof(
        offchain_id=str(ponto.id),
        photo_after_hash=photo_hash,
        photo_before_hash=photo_hash,
        metadata_hash=metadata_hash,
        ai_score=0,
        action_type="outro",
        aprovado=True,
    )

    nft = NFT(
        id=uuid.uuid4(),
        token_id=token_id,
        cidadao_id=cidadao.id,
        limpeza_id=None,
        participacao_id=None,
        assinado_por=AssinadoPor.ecoproof,
        instituto_id=None,
        metadata_url=metadata_url,
        tx_hash=tx_hash,
        created_at=datetime.now(tz=timezone.utc),
    )
    db.add(nft)
    await db.flush()

    return NFTResponse(
        id=nft.id,
        token_id=nft.token_id,
        cidadao_id=nft.cidadao_id,
        assinado_por=nft.assinado_por,
        metadata_url=nft.metadata_url,
        tx_hash=nft.tx_hash,
        created_at=nft.created_at,
        limpeza_id=None,
        participacao_id=None,
        instituto_id=None,
        tipo_acao=None,
        foto_url=ponto.foto_inicial_url,
    )


# ── Metadata: evento de mutirão ───────────────────────────────────────────────

def _build_metadata_evento(
    participacao: Participacao,
    evento_titulo: str,
    evento_tipo: str,
    evento_local: str,
    instituto_nome: str,
    data_evento: str,
) -> NFTMetadata:
    """Gera NFTMetadata ERC-721 para participação em evento de mutirão."""
    tipo_label = evento_tipo.replace("_", " ").title()
    return NFTMetadata(
        name=f"EcoProof — {evento_titulo} #{str(participacao.id)[:8].upper()}",
        description=(
            f"NFT Soulbound (intransferível) de participação no evento de mutirão "
            f"'{evento_titulo}', realizado em {evento_local} em {data_evento}. "
            f"Emitido por {instituto_nome} via plataforma EcoProof."
        ),
        image=participacao.foto_url or "https://ecoproof.io/default-event.png",
        external_url=f"https://ecoproof.io/eventos/{participacao.evento_id}",
        attributes=[
            {"trait_type": "Tipo de Ação", "value": tipo_label},
            {"trait_type": "Evento", "value": evento_titulo},
            {"trait_type": "Local", "value": evento_local},
            {"trait_type": "Data", "value": data_evento, "display_type": "date"},
            {"trait_type": "Assinado por", "value": instituto_nome},
            {"trait_type": "Emitido via", "value": "EcoProof Instituto"},
            {"trait_type": "Token Type", "value": "Soulbound (EIP-5192)"},
            {
                "trait_type": "Pontos Concedidos",
                "value": POINTS_PER_EVENTO,
                "display_type": "number",
            },
        ],
        ecoproof_version="1.0",
    )


# ── Mint: participação em evento ──────────────────────────────────────────────

async def mint_nft_evento(
    db: AsyncSession,
    participacao: Participacao,
    cidadao: Cidadao,
    instituto: Instituto,
) -> NFTResponse:
    """
    Minta NFT Soulbound para participante aprovado em evento de mutirão.
      assinado_por = 'instituto' | pontos = POINTS_PER_EVENTO (30)
      instituto_id e participacao_id preenchidos.
    """
    from app.models.evento import Evento

    blockchain = get_blockchain_service()

    ev_result = await db.execute(select(Evento).where(Evento.id == participacao.evento_id))
    evento = ev_result.scalar_one_or_none()

    user_inst_result = await db.execute(select(User).where(User.id == instituto.id))
    user_inst = user_inst_result.scalar_one_or_none()
    instituto_nome = user_inst.name if user_inst else "Instituto"

    evento_titulo = evento.titulo if evento else "Mutirão"
    evento_local = evento.local if evento else "Local"
    evento_tipo = evento.tipo_acao.value if evento else "outro"
    data_formatada = (
        evento.data_evento.strftime("%d/%m/%Y")
        if evento and evento.data_evento
        else "—"
    )

    metadata = _build_metadata_evento(
        participacao=participacao,
        evento_titulo=evento_titulo,
        evento_tipo=evento_tipo,
        evento_local=evento_local,
        instituto_nome=instituto_nome,
        data_evento=data_formatada,
    )

    key = f"nfts/metadata/evento_{participacao.id}.json"
    content = json.dumps(metadata.model_dump(), ensure_ascii=False, indent=2).encode("utf-8")
    metadata_url = await upload_json(content, key)

    # Calcula hash do metadata para o Registry
    metadata_hash = compute_keccak256(content)

    # Wallet do cidadão ou zero address
    wallet_address = (cidadao.user.wallet_address if cidadao.user else None) or "0x0000000000000000000000000000000000000000"

    # Busca wallet do instituto
    instituto_wallet = (instituto.user.wallet_address if (instituto and instituto.user) else None) or "0x0000000000000000000000000000000000000000"

    # Mint on-chain
    token_id, tx_hash = await blockchain.mint_evento(
        to_address=wallet_address,
        uri=metadata_url,
        offchain_id=str(participacao.id),
        action_type=evento_tipo,
        institution_wallet=instituto_wallet,
    )

    # Registra proof de participação on-chain
    photo_hash = compute_keccak256(
        (participacao.foto_url or "").encode("utf-8")
    )
    await blockchain.register_participacao_proof(
        offchain_id=str(participacao.id),
        photo_hash=photo_hash,
        metadata_hash=metadata_hash,
        action_type=evento_tipo,
    )

    logger.info(
        "NFT evento mintado — token_id=%s tx_hash=%s participacao_id=%s",
        token_id, tx_hash, participacao.id,
    )

    nft = NFT(
        id=uuid.uuid4(),
        token_id=token_id,
        cidadao_id=cidadao.id,
        limpeza_id=None,
        participacao_id=participacao.id,
        assinado_por=AssinadoPor.instituto,
        instituto_id=instituto.id,
        metadata_url=metadata_url,
        tx_hash=tx_hash,
        created_at=datetime.now(tz=timezone.utc),
    )
    db.add(nft)

    cidadao.total_points += POINTS_PER_EVENTO
    db.add(cidadao)
    await db.flush()

    logger.info(
        "Cidadão %s recebeu %d pts pelo evento. Total: %d",
        cidadao.id, POINTS_PER_EVENTO, cidadao.total_points,
    )

    return NFTResponse(
        id=nft.id,
        token_id=nft.token_id,
        cidadao_id=nft.cidadao_id,
        assinado_por=nft.assinado_por,
        metadata_url=nft.metadata_url,
        tx_hash=nft.tx_hash,
        created_at=nft.created_at,
        limpeza_id=None,
        participacao_id=nft.participacao_id,
        instituto_id=nft.instituto_id,
        tipo_acao=evento.tipo_acao if evento else None,
        foto_url=participacao.foto_url,
    )


# ── Mint: denúncia ambiental verificada ─────────────────────────────────────

POINTS_PER_DENUNCIA = 50   # NFT Fiscal Ambiental — emitido quando denúncia é resolvida


def generate_metadata_denuncia(
    denuncia: Denuncia,
    cidadao: Cidadao,
) -> NFTMetadata:
    """Gera NFTMetadata ERC-721 para denúncia ambiental verificada e resolvida."""
    tipo_label = denuncia.tipo_problema.value.replace("_", " ").title()
    data_denuncia = denuncia.created_at.strftime("%d/%m/%Y") if denuncia.created_at else "—"
    data_resolucao = denuncia.resolved_at.strftime("%d/%m/%Y") if denuncia.resolved_at else "—"
    dias_para_resolver = (
        (denuncia.resolved_at - denuncia.created_at).days
        if denuncia.resolved_at and denuncia.created_at
        else 0
    )

    return NFTMetadata(
        name=f"Fiscal Ambiental — Denúncia #{str(denuncia.id)[:8].upper()} Resolvida",
        description=(
            f"NFT Soulbound (intransferível) de denúncia ambiental verificada e resolvida "
            f"pela plataforma EcoProof. "
            f"Tipo de problema: {tipo_label}. "
            f"Denúncia registrada em {data_denuncia} e resolvida em {data_resolucao}."
        ),
        image=denuncia.foto_resolucao_url or denuncia.foto_problema_url,
        external_url=f"https://ecoproof.io/denuncias/{denuncia.id}",
        attributes=[
            {"trait_type": "Tipo de Problema", "value": tipo_label},
            {"trait_type": "Assinado por",     "value": "EcoProof"},
            {"trait_type": "Data Denúncia",    "value": data_denuncia, "display_type": "date"},
            {"trait_type": "Data Resolução",   "value": data_resolucao, "display_type": "date"},
            {"trait_type": "Dias para Resolver", "value": dias_para_resolver, "display_type": "number"},
            {"trait_type": "Proof Hash",       "value": denuncia.proof_hash or "—"},
            {"trait_type": "Token Type",       "value": "Soulbound (EIP-5192)"},
            {
                "trait_type": "Pontos Concedidos",
                "value": POINTS_PER_DENUNCIA,
                "display_type": "number",
            },
        ],
        ecoproof_version="1.0",
    )


async def mint_nft_denuncia(
    db: AsyncSession,
    denuncia: Denuncia,
    cidadao: Cidadao,
) -> NFTResponse:
    """
    Minta NFT Soulbound para denúncia ambiental verificada e resolvida.
      assinado_por = 'ecoproof' | pontos = POINTS_PER_DENUNCIA (50)

    Integração blockchain:
      1. Gera metadata ERC-721 e salva no Cloudinary
      2. Minta NFT on-chain via EcoProofNFT.sol (mintLimpeza reutilizado)
      3. Registra proof no ValidationRegistry on-chain
      4. Salva NFT no banco e credita 50 pts ao cidadão
    """
    blockchain = get_blockchain_service()

    # Gera e salva metadata
    metadata = generate_metadata_denuncia(denuncia, cidadao)
    key = f"nfts/metadata/denuncia_{denuncia.id}.json"
    content = json.dumps(metadata.model_dump(), ensure_ascii=False, indent=2).encode("utf-8")
    metadata_url = await upload_json(content, key)
    metadata_hash = compute_keccak256(content)

    logger.info("NFT denuncia metadata salva: %s", metadata_url)

    # Wallet do cidadão
    wallet_address = (
        (cidadao.user.wallet_address if cidadao.user else None)
        or "0x0000000000000000000000000000000000000000"
    )

    # Mint on-chain (usa mintLimpeza pois a denúncia é uma ação individual do cidadão)
    token_id, tx_hash = await blockchain.mint_limpeza(
        to_address=wallet_address,
        uri=metadata_url,
        offchain_id=str(denuncia.id),
        action_type="outro",   # ActionType.OUTRO no contrato
        ai_score=0,
    )

    # Registra proof de existência on-chain (prova da foto do problema)
    photo_hash = compute_keccak256((denuncia.foto_problema_url or "").encode("utf-8"))
    await blockchain.register_limpeza_proof(
        offchain_id=str(denuncia.id),
        photo_after_hash=photo_hash,
        photo_before_hash=photo_hash,
        metadata_hash=metadata_hash,
        ai_score=0,
        action_type="outro",
        aprovado=True,
    )

    logger.info(
        "NFT denuncia mintado — token_id=%s tx_hash=%s denuncia_id=%s",
        token_id, tx_hash, denuncia.id,
    )

    # Salva no banco
    nft = NFT(
        id=uuid.uuid4(),
        token_id=token_id,
        cidadao_id=cidadao.id,
        limpeza_id=None,
        participacao_id=None,
        assinado_por=AssinadoPor.ecoproof,
        instituto_id=None,
        metadata_url=metadata_url,
        tx_hash=tx_hash,
        created_at=datetime.now(tz=timezone.utc),
    )
    db.add(nft)

    # Credita pontos ao cidadão
    cidadao.total_points += POINTS_PER_DENUNCIA
    db.add(cidadao)
    await db.flush()

    logger.info(
        "Cidadão %s recebeu %d pts pela denúncia. Total: %d",
        cidadao.id, POINTS_PER_DENUNCIA, cidadao.total_points,
    )

    return NFTResponse(
        id=nft.id,
        token_id=nft.token_id,
        cidadao_id=nft.cidadao_id,
        assinado_por=nft.assinado_por,
        metadata_url=nft.metadata_url,
        tx_hash=nft.tx_hash,
        created_at=nft.created_at,
        limpeza_id=None,
        participacao_id=None,
        instituto_id=None,
        tipo_acao=None,
        foto_url=denuncia.foto_resolucao_url or denuncia.foto_problema_url,
    )


# ── Mint em lote ──────────────────────────────────────────────────────────────

async def mint_lote_evento(
    db: AsyncSession,
    evento_id: uuid.UUID,
    instituto: Instituto,
) -> "MintLoteDetalheResponse":
    """
    Emite NFTs em lote para todos participantes aprovados de um evento sem NFT.

    Fluxo:
    1. Busca participações aprovadas do evento
    2. Filtra as que já possuem NFT (idempotente)
    3. Para cada uma: chama mint_nft_evento individualmente
    4. Erros individuais não interrompem o lote
    5. Retorna resultado detalhado por participante.
    """
    from app.models.evento import Evento
    from app.schemas.evento import MintLoteDetalheResponse, MintResultadoItem

    ev_result = await db.execute(select(Evento).where(Evento.id == evento_id))
    evento = ev_result.scalar_one_or_none()
    if evento is None:
        from fastapi import HTTPException, status as http_status
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Evento não encontrado.",
        )

    # Participações aprovadas
    part_result = await db.execute(
        select(Participacao).where(
            Participacao.evento_id == evento_id,
            Participacao.status == StatusParticipacao.aprovado,
        )
    )
    participacoes = part_result.scalars().all()

    if not participacoes:
        return MintLoteDetalheResponse(
            evento_id=evento_id,
            total_emitido=0,
            total_erros=0,
            pontos_distribuidos=0,
            resultados=[],
        )

    # Filtra as que já possuem NFT (idempotência)
    participacao_ids = [p.id for p in participacoes]
    nfts_result = await db.execute(
        select(NFT).where(NFT.participacao_id.in_(participacao_ids))
    )
    nfts_existentes = {nft.participacao_id: nft for nft in nfts_result.scalars().all()}
    sem_nft = [p for p in participacoes if p.id not in nfts_existentes]

    logger.info(
        "Lote evento %s: %d aprovados | %d sem NFT | %d já com NFT",
        evento_id, len(participacoes), len(sem_nft), len(nfts_existentes),
    )

    resultados: list[MintResultadoItem] = []
    total_emitido = 0

    # Registra participações que já tinham NFT como sucesso (idempotente)
    for participacao_id, nft_existente in nfts_existentes.items():
        part_com_nft = next((p for p in participacoes if p.id == participacao_id), None)
        cidadao_nome = "—"
        cidadao_id_val = None
        if part_com_nft:
            cid_r = await db.execute(select(Cidadao).where(Cidadao.id == part_com_nft.cidadao_id))
            cid = cid_r.scalar_one_or_none()
            if cid and cid.user:
                cidadao_nome = cid.user.name or "—"
            cidadao_id_val = part_com_nft.cidadao_id
        resultados.append(MintResultadoItem(
            participacao_id=participacao_id,
            cidadao_id=cidadao_id_val or participacao_id,
            cidadao_nome=cidadao_nome,
            sucesso=True,
            token_id=nft_existente.token_id,
            tx_hash=nft_existente.tx_hash,
            erro=None,
        ))

    # Minta as participações sem NFT
    for participacao in sem_nft:
        cid_result = await db.execute(
            select(Cidadao).where(Cidadao.id == participacao.cidadao_id)
        )
        cidadao = cid_result.scalar_one_or_none()

        cidadao_nome = "—"
        if cidadao and cidadao.user:
            cidadao_nome = cidadao.user.name or "—"

        if cidadao is None:
            resultados.append(MintResultadoItem(
                participacao_id=participacao.id,
                cidadao_id=participacao.cidadao_id,
                cidadao_nome=cidadao_nome,
                sucesso=False,
                erro="Perfil de cidadão não encontrado.",
            ))
            continue

        try:
            nft_resp = await mint_nft_evento(db, participacao, cidadao, instituto)
            resultados.append(MintResultadoItem(
                participacao_id=participacao.id,
                cidadao_id=cidadao.id,
                cidadao_nome=cidadao_nome,
                sucesso=True,
                token_id=nft_resp.token_id,
                tx_hash=nft_resp.tx_hash,
            ))
            total_emitido += 1
        except Exception as exc:
            logger.exception(
                "Erro ao mintar NFT para participação %s: %s",
                participacao.id, exc,
            )
            resultados.append(MintResultadoItem(
                participacao_id=participacao.id,
                cidadao_id=cidadao.id,
                cidadao_nome=cidadao_nome,
                sucesso=False,
                erro=str(exc),
            ))

    total_erros = sum(1 for r in resultados if not r.sucesso)
    logger.info(
        "Lote concluído: %d emitidos | %d erros | %d pontos distribuídos",
        total_emitido, total_erros, total_emitido * POINTS_PER_EVENTO,
    )

    return MintLoteDetalheResponse(
        evento_id=evento_id,
        total_emitido=total_emitido,
        total_erros=total_erros,
        pontos_distribuidos=total_emitido * POINTS_PER_EVENTO,
        resultados=resultados,
    )


async def mint_nft_educacao(
    db: AsyncSession,
    acao: AcaoEducacional,
    autor: User,
    issued_by: str,
) -> NFT:
    """
    Gera os metadados, chama o mint no contrato e salva o NFT no banco.
    issued_by: "admin" ou "instituto"
    """
    blockchain = get_blockchain_service()

    # Determinar nome e wallet do validador
    validador_name = "EcoProof"
    validator_wallet = "0x0000000000000000000000000000000000000000"
    
    if acao.validado_por:
        validador_result = await db.execute(select(User).where(User.id == acao.validado_por))
        validador_user = validador_result.scalar_one_or_none()
        if validador_user:
            validador_name = validador_user.name
            validator_wallet = validador_user.wallet_address or validator_wallet

    assinado_label = "EcoProof" if issued_by == "admin" else validador_name

    metadata = {
        "name": f"Educador Ambiental — {acao.num_pessoas} pessoas impactadas",
        "description": (
            f"Certificado de ação de educação ambiental verificada. "
            f"Tipo: {acao.tipo_acao.value if hasattr(acao.tipo_acao, 'value') else acao.tipo_acao}. "
            f"{acao.num_pessoas} pessoas alcançadas."
        ),
        "image": acao.foto_url,
        "attributes": [
            {"trait_type": "Tipo de Ação",         "value": acao.tipo_acao.value if hasattr(acao.tipo_acao, 'value') else acao.tipo_acao},
            {"trait_type": "Pessoas Impactadas",    "value": acao.num_pessoas},
            {"trait_type": "Assinado por",          "value": assinado_label},
            {"trait_type": "Validado por tipo",     "value": issued_by},
            {"trait_type": "Data",                  "value": str(acao.created_at.date())},
            {"trait_type": "Pontos",                "value": 45},
            {"trait_type": "Categoria",             "value": "Impacto Social"},
        ]
    }

    # Salva metadata no Cloudinary
    key = f"nfts/metadata/educacao_{acao.id}.json"
    content = json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8")
    metadata_url = await upload_json(content, key)

    # Minta no contrato EducacaoNFT.sol
    dest_wallet = autor.wallet_address or "0x0000000000000000000000000000000000000000"
    
    resultado = await blockchain.mint_educacao_individual(
        destinatario=dest_wallet,
        metadata_uri=metadata_url,
        offchain_id=str(acao.id),
        tipo_acao=acao.tipo_acao.value if hasattr(acao.tipo_acao, 'value') else acao.tipo_acao,
        validator_wallet=validator_wallet,
        num_pessoas=acao.num_pessoas,
        issued_by=issued_by,
    )

    # Salva NFT no banco
    assinado_por_enum = AssinadoPor.ecoproof if issued_by == "admin" else AssinadoPor.instituto
    instituto_id_val = acao.validado_por if issued_by == "instituto" else None

    nft = NFT(
        id=uuid.uuid4(),
        token_id=resultado["token_id"],
        cidadao_id=acao.autor_id,
        educacao_id=acao.id,   # nova FK na tabela nfts
        assinado_por=assinado_por_enum,
        instituto_id=instituto_id_val,
        metadata_url=metadata_url,
        tx_hash=resultado["tx_hash"],
        created_at=datetime.now(tz=timezone.utc),
    )
    db.add(nft)

    # Soma 45 pontos ao autor (se for cidadão)
    from app.models.educacao import AutorTipo as _AutorTipo
    if acao.autor_tipo == _AutorTipo.cidadao:
        cid_result = await db.execute(select(Cidadao).where(Cidadao.id == acao.autor_id))
        cidadao = cid_result.scalar_one_or_none()
        if cidadao:
            cidadao.total_points += 45
            db.add(cidadao)

    acao.mint_tx_hash = resultado["tx_hash"]
    db.add(acao)
    await db.flush()
    return nft

