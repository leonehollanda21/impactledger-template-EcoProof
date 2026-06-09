import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Float, Integer, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class CategoriaPontoVerde(str, enum.Enum):
    praca = "praca"
    canteiro = "canteiro"
    praia = "praia"
    rio = "rio"
    outro = "outro"


class StatusPontoVerde(str, enum.Enum):
    disponivel = "disponivel"
    ativo = "ativo"
    alerta = "alerta"
    concluido = "concluido"


class PontoVerde(Base):
    __tablename__ = "pontos_verdes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    categoria: Mapped[CategoriaPontoVerde] = mapped_column(
        SAEnum(CategoriaPontoVerde, name="categoriapontoverde", create_type=True),
        nullable=False,
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    guardiao_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    guardiao_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    data_inicio: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[StatusPontoVerde] = mapped_column(
        SAEnum(StatusPontoVerde, name="statuspontoverde", create_type=True),
        default=StatusPontoVerde.disponivel,
        nullable=False,
    )
    meses_concluidos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    proximo_checkin_limite: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    foto_inicial_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    nft_token_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nft_tx_hash: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    guardiao: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[guardiao_id],
        lazy="selectin",
    )
    checkins: Mapped[list["CheckInPontoVerde"]] = relationship(
        "CheckInPontoVerde",
        back_populates="ponto_verde",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<PontoVerde id={self.id} status={self.status} meses_concluidos={self.meses_concluidos}>"
