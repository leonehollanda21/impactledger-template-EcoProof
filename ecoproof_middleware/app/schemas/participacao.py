"""
app/schemas/participacao.py
────────────────────────────
Schemas Pydantic v2 para Participação em eventos.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from app.models.participacao import StatusParticipacao


# ── Responses ─────────────────────────────────────────────────────────────────

class ParticipacaoResponse(BaseModel):
    """Representação completa de uma participação."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    evento_id: uuid.UUID
    cidadao_id: uuid.UUID
    cidadao_nome: str          # enriquecido via join
    foto_url: Optional[str] = None
    status: StatusParticipacao
    checkin_at: datetime
    motivo_rejeicao: Optional[str] = None


class MinhaParticipacaoResponse(BaseModel):
    """Participação vista pelo cidadão (com info do evento)."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    evento_id: uuid.UUID
    evento_titulo: str         # enriquecido via join
    foto_url: Optional[str] = None
    status: StatusParticipacao
    checkin_at: datetime
    motivo_rejeicao: Optional[str] = None


# ── Requests de ação ─────────────────────────────────────────────────────────

class ParticipacaoStatusUpdate(BaseModel):
    """Payload para rejeitar uma participação com motivo."""
    motivo_rejeicao: str = Field(
        ...,
        min_length=10,
        max_length=500,
        examples=["A foto enviada não mostra claramente a participação no evento."],
        description="Motivo da rejeição (obrigatório, mínimo 10 caracteres).",
    )


class ParticipacaoListResponse(BaseModel):
    """Lista paginada de participações de um evento."""
    items: list[ParticipacaoResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


class MinhasParticipacoesPaginadas(BaseModel):
    """Lista paginada de participações do cidadão."""
    items: list[MinhaParticipacaoResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
