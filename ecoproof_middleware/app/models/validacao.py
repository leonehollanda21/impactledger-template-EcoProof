import uuid
from datetime import datetime

from sqlalchemy import Boolean, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class Validacao(Base):
    __tablename__ = "validacoes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    limpeza_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("limpezas_individuais.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    participacao_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("participacoes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resultado: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # ── Relacionamentos ──────────────────────────────────────
    limpeza: Mapped["LimpezaIndividual | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "LimpezaIndividual",
        back_populates="validacoes",
        lazy="selectin",
    )
    participacao: Mapped["Participacao | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Participacao",
        back_populates="validacoes",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Validacao id={self.id} resultado={self.resultado} score={self.score}>"
