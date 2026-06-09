"""
app/schemas/educacao.py
───────────────────────
Schemas Pydantic v2 para Ações de Educação Ambiental.
"""
import uuid
import enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.educacao import TipoAcaoEducativa, StatusAcaoEducativa, AutorTipo
from app.schemas.nft import NFTResponse


class TipoEducacaoEnum(str, enum.Enum):
    palestra = "palestra"
    oficina = "oficina"
    roda_conversa = "roda_conversa"
    mutirao_educativo = "mutirao_educativo"
    outro = "outro"


# ── Requests ──────────────────────────────────────────────────────────────────

class EducacaoCreateRequest(BaseModel):
    """
    Parâmetros enviados para criar uma AcaoEducacional.
    Note que a foto vem como UploadFile separado no form-data.
    """
    tipo_acao: TipoEducacaoEnum = Field(..., description="Tipo de ação educativa realizada")
    num_pessoas: int = Field(..., ge=1, le=10000, description="Número de pessoas impactadas (1 a 10.000)")
    descricao: Optional[str] = Field(None, max_length=500, description="Descrição opcional (máx 500 caracteres)")


class EducacaoValidarRequest(BaseModel):
    """Usado por instituto ou admin para validar a ação."""
    aprovado: bool = Field(..., description="True para aprovar, False para rejeitar")
    motivo_rejeicao: Optional[str] = Field(None, min_length=5, max_length=500, description="Obrigatório se aprovado=False")


# ── Responses ─────────────────────────────────────────────────────────────────

class EducacaoResponse(BaseModel):
    """Representação detalhada da AcaoEducacional."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tipo_acao: TipoAcaoEducativa
    num_pessoas: int
    descricao: Optional[str] = None
    foto_url: str
    status: StatusAcaoEducativa
    autor_id: uuid.UUID
    autor_tipo: AutorTipo
    validado_por: Optional[uuid.UUID] = None
    validado_por_tipo: Optional[AutorTipo] = None
    motivo_rejeicao: Optional[str] = None
    registry_tx_hash: Optional[str] = None
    mint_tx_hash: Optional[str] = None
    created_at: datetime
    validated_at: Optional[datetime] = None
    nft: Optional[NFTResponse] = None


class EducacaoListResponse(BaseModel):
    """Item simplificado para listagens."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tipo_acao: TipoAcaoEducativa
    num_pessoas: int
    status: StatusAcaoEducativa
    created_at: datetime
