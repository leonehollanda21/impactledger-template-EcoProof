"""
app/schemas/limpeza.py
───────────────────────
Schemas Pydantic v2 para LimpezaIndividual.
"""
import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from app.models.evento import TipoAcao
from app.models.limpeza_individual import StatusLimpeza

from app.schemas.nft import NFTResponse


# ── Request ───────────────────────────────────────────────────────────────────

class LimpezaCreateRequest(BaseModel):
    """
    Campos de texto do form multipart para criação de limpeza.
    As fotos (foto_antes, foto_depois) são enviadas como UploadFile
    diretamente na rota — não fazem parte deste schema.
    """
    tipo_acao: TipoAcao


# ── Responses ─────────────────────────────────────────────────────────────────

class LimpezaResponse(BaseModel):
    """Representação de uma LimpezaIndividual."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cidadao_id: uuid.UUID
    foto_antes_url: str
    foto_depois_url: str
    tipo_acao: TipoAcao
    status: StatusLimpeza
    created_at: datetime


class LimpezaListResponse(BaseModel):
    """Item resumido para listagem do histórico."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tipo_acao: TipoAcao
    status: StatusLimpeza
    foto_depois_url: str
    created_at: datetime


class LimpezaResultResponse(BaseModel):
    """
    Resposta completa após o processamento de uma limpeza:
    inclui a limpeza, o resultado da validação e o NFT gerado (se aprovado).
    """
    limpeza: LimpezaResponse
    nft: Optional[NFTResponse] = None
    aprovado: bool
    score: float
    motivo: str


# ── Paginação ─────────────────────────────────────────────────────────────────

class LimpezaHistoricoResponse(BaseModel):
    """Histórico paginado de limpezas do cidadão."""
    items: list[LimpezaListResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
