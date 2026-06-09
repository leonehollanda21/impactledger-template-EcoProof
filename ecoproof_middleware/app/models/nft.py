import uuid
import enum
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class AssinadoPor(str, enum.Enum):
    ecoproof = "ecoproof"
    instituto = "instituto"


class NFT(Base):
    __tablename__ = "nfts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    token_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    cidadao_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cidadaos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    limpeza_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("limpezas_individuais.id", ondelete="SET NULL"),
        nullable=True,
    )
    participacao_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("participacoes.id", ondelete="SET NULL"),
        nullable=True,
    )
    educacao_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("acoes_educacionais.id", ondelete="SET NULL"),
        nullable=True,
    )
    assinado_por: Mapped[AssinadoPor] = mapped_column(
        SAEnum(AssinadoPor, name="assinadopor", create_type=True),
        nullable=False,
    )
    instituto_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutos.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_url: Mapped[str] = mapped_column(String(500), nullable=False)
    tx_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # ── Relacionamentos ──────────────────────────────────────
    cidadao: Mapped["Cidadao"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Cidadao",
        back_populates="nfts",
        foreign_keys=[cidadao_id],
        lazy="selectin",
    )
    limpeza: Mapped["LimpezaIndividual | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "LimpezaIndividual",
        back_populates="nfts",
        foreign_keys=[limpeza_id],
        lazy="selectin",
    )
    participacao: Mapped["Participacao | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Participacao",
        back_populates="nfts",
        foreign_keys=[participacao_id],
        lazy="selectin",
    )
    educacao: Mapped["AcaoEducacional | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "AcaoEducacional",
        back_populates="nfts",
        foreign_keys=[educacao_id],
        lazy="selectin",
    )
    instituto: Mapped["Instituto | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Instituto",
        back_populates="nfts_emitidos",
        foreign_keys=[instituto_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<NFT id={self.id} token_id={self.token_id} assinado_por={self.assinado_por}>"
