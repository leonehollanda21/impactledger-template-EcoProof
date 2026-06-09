"""
app/schemas/admin.py
─────────────────────
Schemas Pydantic v2 para endpoints de administração.
"""
import uuid
from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, ConfigDict

from app.models.denuncia import StatusDenuncia
from app.models.educacao import StatusAcaoEducativa, TipoAcaoEducativa


# ── Instituto ─────────────────────────────────────────────────────────────────

class InstitutoAdminResponse(BaseModel):
    """Visão administrativa de um instituto com contagens."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    email: str
    cnpj: str
    verified: bool
    verified_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime

    # Contagens enriquecidas
    total_eventos: int = 0
    total_nfts_emitidos: int = 0


class InstitutoAdminListResponse(BaseModel):
    """Lista paginada de institutos para o admin."""
    items: list[InstitutoAdminResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


class AcaoAdminResponse(BaseModel):
    """Resposta genérica de ação administrativa."""
    success: bool
    message: str
    instituto_id: uuid.UUID


# ── Validações ────────────────────────────────────────────────────────────────

class ValidacaoAdminResponse(BaseModel):
    """Visão administrativa de uma validação com dados do cidadão."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    resultado: bool
    score: Optional[float] = None
    motivo: Optional[str] = None
    created_at: datetime

    # Tipo de origem
    tipo: Literal["limpeza", "participacao"]

    # Origem
    limpeza_id: Optional[uuid.UUID] = None
    participacao_id: Optional[uuid.UUID] = None

    # Dados do cidadão
    cidadao_id: uuid.UUID
    cidadao_nome: str
    cidadao_wallet: Optional[str] = None


class ValidacaoAdminListResponse(BaseModel):
    """Lista paginada de validações."""
    items: list[ValidacaoAdminResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


# ── NFTs ──────────────────────────────────────────────────────────────────────

class NFTAdminResponse(BaseModel):
    """NFT com dados do dono para o painel admin."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    token_id: str
    tx_hash: str
    metadata_url: str
    assinado_por: str
    created_at: datetime

    # Origem
    limpeza_id: Optional[uuid.UUID] = None
    participacao_id: Optional[uuid.UUID] = None
    educacao_id: Optional[uuid.UUID] = None
    instituto_id: Optional[uuid.UUID] = None

    # Dados do cidadão (enriquecidos)
    cidadao_id: uuid.UUID
    cidadao_nome: Optional[str] = None
    cidadao_wallet: Optional[str] = None

    # Tipo deduzido
    tipo: Optional[str] = None  # "limpeza", "mutirao", "denuncia", "educacao", "adocao"


class NFTAdminListResponse(BaseModel):
    """Lista paginada de NFTs para o admin."""
    items: list[NFTAdminResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


# ── Denúncias (visão admin) ───────────────────────────────────────────────────

class DenunciaAdminSummary(BaseModel):
    """Item resumido de denúncia para o painel admin."""
    id: uuid.UUID
    tipo_problema: str
    status: StatusDenuncia
    foto_problema_url: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
    cidadao_id: uuid.UUID
    cidadao_nome: Optional[str] = None


class DenunciaAdminSummaryListResponse(BaseModel):
    """Lista paginada de denúncias para o admin."""
    items: list[DenunciaAdminSummary]
    total: int
    page: int
    page_size: int
    has_next: bool


# ── Educação (visão admin) ────────────────────────────────────────────────────

class EducacaoAdminSummary(BaseModel):
    """Item resumido de ação educativa para o painel admin."""
    id: uuid.UUID
    tipo_acao: TipoAcaoEducativa
    num_pessoas: int
    status: StatusAcaoEducativa
    foto_url: str
    descricao: Optional[str] = None
    created_at: datetime
    autor_id: uuid.UUID
    autor_nome: Optional[str] = None
    autor_tipo: str


class EducacaoAdminListResponse(BaseModel):
    """Lista paginada de ações educativas para o admin."""
    items: list[EducacaoAdminSummary]
    total: int
    page: int
    page_size: int
    has_next: bool


# ── Dashboard ─────────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    """Estatísticas gerais da plataforma para o dashboard admin."""
    total_usuarios: int
    total_cidadaos: int
    total_institutos: int
    total_institutos_pendentes: int
    total_eventos: int
    total_limpezas: int
    total_nfts: int
    total_validacoes_aprovadas: int
    total_pontos_distribuidos: int
    total_denuncias: int
    total_educacoes: int
