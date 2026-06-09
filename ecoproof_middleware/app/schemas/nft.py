"""
app/schemas/nft.py
───────────────────
Schemas Pydantic v2 para NFT.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.nft import AssinadoPor
from app.models.evento import TipoAcao


class NFTResponse(BaseModel):
    """Representação completa de um NFT mintado."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    token_id: str
    cidadao_id: uuid.UUID
    assinado_por: AssinadoPor
    metadata_url: str
    tx_hash: str
    created_at: datetime

    # Origem do NFT (um dos dois será preenchido)
    limpeza_id: Optional[uuid.UUID] = None
    participacao_id: Optional[uuid.UUID] = None
    educacao_id: Optional[uuid.UUID] = None
    instituto_id: Optional[uuid.UUID] = None

    # Campos enriquecidos (calculados no serviço, não mapeados do ORM)
    tipo_acao: Optional[TipoAcao] = None
    foto_url: Optional[str] = None  # foto_depois da limpeza ou foto da participação


class NFTMetadata(BaseModel):
    """
    Metadados do NFT no padrão ERC-721 (OpenSea compatible).
    Salvo como JSON no S3 e referenciado pelo metadata_url.
    """
    name: str
    description: str
    image: str  # foto_depois_url — imagem principal do NFT
    external_url: Optional[str] = None
    attributes: list[dict]
    # Campos extras EcoProof
    ecoproof_version: str = "1.0"
