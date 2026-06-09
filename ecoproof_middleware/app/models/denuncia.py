"""
app/models/denuncia.py
──────────────────────
Model SQLAlchemy para denúncias ambientais verificadas.

Fluxo de status:
  registrada → em_analise → resolvida   (NFT gerado)
                          → improcedente (sem NFT)
"""
import uuid
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class TipoProblema(str, enum.Enum):
    descarte_ilegal = "descarte_ilegal"
    esgoto          = "esgoto"
    queimada        = "queimada"
    poluicao_agua   = "poluicao_agua"
    poluicao_ar     = "poluicao_ar"
    desmatamento    = "desmatamento"
    outro           = "outro"


class StatusDenuncia(str, enum.Enum):
    registrada    = "registrada"
    em_analise    = "em_analise"
    resolvida     = "resolvida"
    improcedente  = "improcedente"


class Denuncia(Base):
    __tablename__ = "denuncias"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    cidadao_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cidadaos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo_problema: Mapped[TipoProblema] = mapped_column(
        SAEnum(TipoProblema, name="tipoproblema", create_type=True),
        nullable=False,
    )
    descricao: Mapped[str] = mapped_column(Text, nullable=False)

    # Fotos
    foto_problema_url: Mapped[str] = mapped_column(String(500), nullable=False)
    foto_resolucao_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Status da denúncia
    status: Mapped[StatusDenuncia] = mapped_column(
        SAEnum(StatusDenuncia, name="statusdenuncia", create_type=True),
        default=StatusDenuncia.registrada,
        nullable=False,
    )

    # Proof of Existence — registrado no ValidationRegistry.sol no momento da criação
    proof_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    blockchain_tx_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Mint do NFT — preenchido quando status → 'resolvida'
    resolucao_tx_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Rejeição
    motivo_improcedencia: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Relacionamentos ──────────────────────────────────────
    cidadao: Mapped["Cidadao"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Cidadao",
        back_populates="denuncias",
        foreign_keys=[cidadao_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Denuncia id={self.id} tipo={self.tipo_problema} status={self.status}>"
