import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class Instituto(Base):
    __tablename__ = "institutos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    cnpj: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relacionamentos ──────────────────────────────────────
    user: Mapped["User"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User",
        foreign_keys=[id],
        lazy="selectin",
    )
    eventos: Mapped[list["Evento"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Evento",
        back_populates="instituto",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    nfts_emitidos: Mapped[list["NFT"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "NFT",
        back_populates="instituto",
        foreign_keys="NFT.instituto_id",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Instituto id={self.id} cnpj={self.cnpj} verified={self.verified}>"
