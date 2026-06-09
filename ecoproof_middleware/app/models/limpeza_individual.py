import uuid
import enum
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base
from app.models.evento import TipoAcao  # reutiliza o enum já criado


class StatusLimpeza(str, enum.Enum):
    pendente = "pendente"
    aprovado = "aprovado"
    reprovado = "reprovado"


class LimpezaIndividual(Base):
    __tablename__ = "limpezas_individuais"

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
    foto_antes_url: Mapped[str] = mapped_column(String(500), nullable=False)
    foto_depois_url: Mapped[str] = mapped_column(String(500), nullable=False)
    tipo_acao: Mapped[TipoAcao] = mapped_column(
        SAEnum(TipoAcao, name="tipoacao", create_type=False),  # type já existe
        nullable=False,
    )
    status: Mapped[StatusLimpeza] = mapped_column(
        SAEnum(StatusLimpeza, name="statuslimpeza", create_type=True),
        default=StatusLimpeza.pendente,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # ── Relacionamentos ──────────────────────────────────────
    cidadao: Mapped["Cidadao"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Cidadao",
        back_populates="limpezas",
        lazy="selectin",
    )
    validacoes: Mapped[list["Validacao"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Validacao",
        back_populates="limpeza",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    nfts: Mapped[list["NFT"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "NFT",
        back_populates="limpeza",
        foreign_keys="NFT.limpeza_id",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<LimpezaIndividual id={self.id} status={self.status}>"
