"""
app/models/educacao.py
──────────────────────
Model SQLAlchemy para ações de educação ambiental.
"""
import uuid
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Enum as SAEnum, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class AutorTipo(str, enum.Enum):
    cidadao = "cidadao"
    instituto = "instituto"


class TipoAcaoEducativa(str, enum.Enum):
    palestra = "palestra"
    oficina = "oficina"
    roda_conversa = "roda_conversa"
    mutirao_educativo = "mutirao_educativo"
    outro = "outro"


class StatusAcaoEducativa(str, enum.Enum):
    pendente = "pendente"
    aprovada = "aprovada"
    rejeitada = "rejeitada"


class AcaoEducacional(Base):
    __tablename__ = "acoes_educacionais"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    autor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    autor_tipo: Mapped[AutorTipo] = mapped_column(
        SAEnum(AutorTipo, name="autortipo", create_type=True),
        nullable=False,
    )
    tipo_acao: Mapped[TipoAcaoEducativa] = mapped_column(
        SAEnum(TipoAcaoEducativa, name="tipoacaoeducativa", create_type=True),
        nullable=False,
    )
    num_pessoas: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint("num_pessoas >= 1", name="check_num_pessoas_positive"),
        nullable=False,
    )
    foto_url: Mapped[str] = mapped_column(String(500), nullable=False)
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[StatusAcaoEducativa] = mapped_column(
        SAEnum(StatusAcaoEducativa, name="statusacaoeducativa", create_type=True),
        default=StatusAcaoEducativa.pendente,
        nullable=False,
    )
    validado_por: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    validado_por_tipo: Mapped[Optional[AutorTipo]] = mapped_column(
        SAEnum(AutorTipo, name="autortipo", create_type=False),
        nullable=True,
    )
    motivo_rejeicao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    registry_tx_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mint_tx_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    validated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Relacionamentos ──────────────────────────────────────
    autor: Mapped["User"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User",
        foreign_keys=[autor_id],
        back_populates="acoes_educacionais",
        lazy="selectin",
    )
    validador: Mapped[Optional["User"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User",
        foreign_keys=[validado_por],
        lazy="selectin",
    )
    nfts: Mapped[list["NFT"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "NFT",
        back_populates="educacao",
        foreign_keys="NFT.educacao_id",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<AcaoEducacional id={self.id} tipo={self.tipo_acao} status={self.status}>"
