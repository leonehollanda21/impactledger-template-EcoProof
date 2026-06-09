import uuid
import enum
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, UniqueConstraint, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class StatusParticipacao(str, enum.Enum):
    confirmado = "confirmado"
    foto_enviada = "foto_enviada"
    aprovado = "aprovado"
    rejeitado = "rejeitado"


class Participacao(Base):
    __tablename__ = "participacoes"
    __table_args__ = (
        UniqueConstraint("evento_id", "cidadao_id", name="uq_participacao_evento_cidadao"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    evento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("eventos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cidadao_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cidadaos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    foto_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[StatusParticipacao] = mapped_column(
        SAEnum(StatusParticipacao, name="statusparticipacao", create_type=True),
        default=StatusParticipacao.confirmado,
        nullable=False,
    )
    checkin_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    motivo_rejeicao: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relacionamentos ──────────────────────────────────────
    evento: Mapped["Evento"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Evento",
        back_populates="participacoes",
        lazy="selectin",
    )
    cidadao: Mapped["Cidadao"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Cidadao",
        back_populates="participacoes",
        lazy="selectin",
    )
    validacoes: Mapped[list["Validacao"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Validacao",
        back_populates="participacao",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    nfts: Mapped[list["NFT"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "NFT",
        back_populates="participacao",
        foreign_keys="NFT.participacao_id",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Participacao id={self.id} status={self.status}>"
