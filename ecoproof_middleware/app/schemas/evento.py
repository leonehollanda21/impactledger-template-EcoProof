"""
app/schemas/evento.py
──────────────────────
Schemas Pydantic v2 para Evento de mutirão.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.models.evento import TipoAcao, StatusEvento


# ── Requests ──────────────────────────────────────────────────────────────────

class EventoCreateRequest(BaseModel):
    """
    Payload para criação de evento (campos texto do form multipart).
    A foto_capa é enviada separadamente como UploadFile na rota.
    """
    titulo: str = Field(..., min_length=3, max_length=200, examples=["Mutirão Praia Grande"])
    descricao: Optional[str] = Field(
        None,
        max_length=2000,
        examples=["Limpeza coletiva da orla. Traga luvas e sacos de lixo."],
    )
    tipo_acao: TipoAcao
    local: str = Field(..., min_length=3, max_length=300, examples=["Praia Grande, SP"])
    data_evento: datetime = Field(..., examples=["2026-06-15T09:00:00"])

    @field_validator("data_evento")
    @classmethod
    def data_no_futuro(cls, v: datetime) -> datetime:
        from datetime import timezone
        now = datetime.now(tz=timezone.utc)
        # Remove tz para comparação homogênea se vier naive
        v_aware = v if v.tzinfo else v.replace(tzinfo=timezone.utc)
        if v_aware <= now:
            raise ValueError("A data do evento deve ser futura.")
        return v


class EventoUpdateRequest(BaseModel):
    """Campos opcionais para atualização parcial de um evento."""
    titulo: Optional[str] = Field(None, min_length=3, max_length=200)
    descricao: Optional[str] = Field(None, max_length=2000)
    local: Optional[str] = Field(None, min_length=3, max_length=300)
    data_evento: Optional[datetime] = None
    status: Optional[StatusEvento] = None

    @field_validator("data_evento")
    @classmethod
    def data_no_futuro(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is None:
            return v
        from datetime import timezone
        now = datetime.now(tz=timezone.utc)
        v_aware = v if v.tzinfo else v.replace(tzinfo=timezone.utc)
        if v_aware <= now:
            raise ValueError("A data do evento deve ser futura.")
        return v


# ── Responses ─────────────────────────────────────────────────────────────────

class EventoResponse(BaseModel):
    """Resposta pública de um evento (listagens e detalhe público)."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    titulo: str
    descricao: Optional[str] = None
    tipo_acao: TipoAcao
    local: str
    data_evento: datetime
    status: StatusEvento
    foto_capa_url: Optional[str] = None
    created_at: datetime

    # Campos enriquecidos (calculados no serviço)
    instituto_id: uuid.UUID
    instituto_nome: str
    total_participantes: int = 0


class ParticipacaoResumoResponse(BaseModel):
    """Item resumido de participante (para listagem dentro do evento)."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cidadao_id: uuid.UUID
    cidadao_nome: str
    foto_url: Optional[str] = None
    status: str
    checkin_at: datetime
    motivo_rejeicao: Optional[str] = None


class EventoDetalheResponse(EventoResponse):
    """
    Resposta detalhada (exclusiva para o instituto dono do evento).
    Inclui lista completa de participantes com seus status.
    """
    participantes: list[ParticipacaoResumoResponse] = []
    total_confirmados: int = 0
    total_aprovados: int = 0
    total_rejeitados: int = 0
    total_foto_enviada: int = 0


class EventoListResponse(BaseModel):
    """Histórico paginado de eventos."""
    items: list[EventoResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


class MintLoteResponse(BaseModel):
    """Resultado da emissão em lote de NFTs para participantes aprovados."""
    evento_id: uuid.UUID
    total_emitido: int
    tx_hashes: list[str]
    erros: list[dict] = []
    pontos_distribuidos: int


class MintResultadoItem(BaseModel):
    """Resultado individual de um mint dentro do lote."""
    participacao_id: uuid.UUID
    cidadao_id: uuid.UUID
    cidadao_nome: str
    sucesso: bool
    token_id: Optional[str] = None
    tx_hash: Optional[str] = None
    erro: Optional[str] = None


class MintLoteDetalheResponse(BaseModel):
    """Resultado detalhado (por participante) da emissão em lote de NFTs."""
    evento_id: uuid.UUID
    total_emitido: int
    total_erros: int
    pontos_distribuidos: int
    resultados: list[MintResultadoItem] = []


class NFTStatusParticipacaoResponse(BaseModel):
    """Status de NFT por participação aprovada (para o instituto ver quem já tem NFT)."""
    participacao_id: uuid.UUID
    cidadao_id: uuid.UUID
    cidadao_nome: str
    tem_nft: bool
    token_id: Optional[str] = None
    tx_hash: Optional[str] = None
    nft_emitido_em: Optional[str] = None  # ISO datetime string
