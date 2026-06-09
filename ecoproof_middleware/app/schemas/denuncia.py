"""
app/schemas/denuncia.py
────────────────────────
Schemas Pydantic v2 para Denuncia Ambiental.

Fluxo:
  cidadão cria com DenunciaCreateRequest (+ UploadFile no router)
  admin gerencia com DenunciaResolucaoRequest / DenunciaImprocedenciaRequest
  respostas em DenunciaResponse (detalhe) ou DenunciaListResponse (listagem)
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.denuncia import TipoProblema, StatusDenuncia
from app.schemas.nft import NFTResponse


# ── Requests ──────────────────────────────────────────────────────────────────

class DenunciaCreateRequest(BaseModel):
    """
    Campos de texto do form multipart para criação de denúncia.
    A foto (foto_problema) é enviada como UploadFile diretamente na rota.
    """
    tipo_problema: TipoProblema
    descricao: str = Field(
        ...,
        min_length=20,
        max_length=1000,
        description="Descrição detalhada do problema (20–1000 caracteres)",
    )


class DenunciaResolucaoRequest(BaseModel):
    """
    Usado pelo admin ao confirmar resolução.
    A foto de resolução é enviada como UploadFile diretamente na rota.
    """
    pass  # corpo vazio — foto vem como UploadFile no multipart


class DenunciaImprocedenciaRequest(BaseModel):
    """Usado pelo admin ao rejeitar uma denúncia."""
    motivo: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Motivo da rejeição (mín. 10 caracteres)",
    )


# ── Responses ─────────────────────────────────────────────────────────────────

class DenunciaResponse(BaseModel):
    """Representação completa de uma denúncia ambiental."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cidadao_id: uuid.UUID
    tipo_problema: TipoProblema
    descricao: str
    status: StatusDenuncia

    foto_problema_url: str
    foto_resolucao_url: Optional[str] = None

    proof_hash: Optional[str] = None
    blockchain_tx_hash: Optional[str] = None
    resolucao_tx_hash: Optional[str] = None

    motivo_improcedencia: Optional[str] = None

    created_at: datetime
    resolved_at: Optional[datetime] = None

    # NFT emitido após resolução (None enquanto pendente)
    nft: Optional[NFTResponse] = None


class DenunciaListResponse(BaseModel):
    """Item resumido para listagem (cidadão e admin)."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tipo_problema: TipoProblema
    status: StatusDenuncia
    foto_problema_url: str
    created_at: datetime
    resolved_at: Optional[datetime] = None


class DenunciaAdminListItem(BaseModel):
    """Item de listagem para admin — inclui nome do cidadão."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tipo_problema: TipoProblema
    status: StatusDenuncia
    foto_problema_url: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
    cidadao_id: uuid.UUID
    cidadao_nome: Optional[str] = None   # enriquecido no service


class DenunciaAdminListResponse(BaseModel):
    """Listagem paginada de todas as denúncias para o admin."""
    items: list[DenunciaAdminListItem]
    total: int
    page: int
    page_size: int
    has_next: bool
