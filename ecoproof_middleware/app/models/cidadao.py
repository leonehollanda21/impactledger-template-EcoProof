import uuid

from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class Cidadao(Base):
    __tablename__ = "cidadaos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    total_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Relacionamentos ──────────────────────────────────────
    user: Mapped["User"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User",
        foreign_keys=[id],
        lazy="selectin",
    )
    limpezas: Mapped[list["LimpezaIndividual"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "LimpezaIndividual",
        back_populates="cidadao",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    participacoes: Mapped[list["Participacao"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Participacao",
        back_populates="cidadao",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    nfts: Mapped[list["NFT"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "NFT",
        back_populates="cidadao",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    denuncias: Mapped[list["Denuncia"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Denuncia",
        back_populates="cidadao",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Cidadao id={self.id} points={self.total_points}>"
