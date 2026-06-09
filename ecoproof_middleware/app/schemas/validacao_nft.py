"""
Schemas Pydantic v2 — Validação e NFT
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from app.models.nft import AssinadoPor


# ── Validacao ────────────────────────────────────────────────
class ValidacaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    limpeza_id: Optional[uuid.UUID] = None
    participacao_id: Optional[uuid.UUID] = None
    resultado: bool
    score: Optional[float] = None
    motivo: Optional[str] = None
    created_at: datetime


# ── NFT ─────────────────────────────────────────────────────
class NFTOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    token_id: str
    cidadao_id: uuid.UUID
    limpeza_id: Optional[uuid.UUID] = None
    participacao_id: Optional[uuid.UUID] = None
    assinado_por: AssinadoPor
    instituto_id: Optional[uuid.UUID] = None
    metadata_url: str
    tx_hash: str
    created_at: datetime


class NFTMintRequest(BaseModel):
    """Payload para solicitar a mintagem de um NFT."""
    cidadao_id: uuid.UUID
    limpeza_id: Optional[uuid.UUID] = None
    participacao_id: Optional[uuid.UUID] = None
    assinado_por: AssinadoPor
    instituto_id: Optional[uuid.UUID] = None
    metadata_url: str = Field(..., max_length=500)
