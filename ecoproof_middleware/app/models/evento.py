import uuid
import enum
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class TipoAcao(str, enum.Enum):
    lixo_rua = "lixo_rua"
    praia = "praia"
    corrego = "corrego"
    queimada = "queimada"
    outro = "outro"


class StatusEvento(str, enum.Enum):
    ativo = "ativo"
    encerrado = "encerrado"
    cancelado = "cancelado"


class Evento(Base):
    __tablename__ = "eventos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    instituto_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipo_acao: Mapped[TipoAcao] = mapped_column(
        SAEnum(TipoAcao, name="tipoacao", create_type=True),
        nullable=False,
    )
    local: Mapped[str] = mapped_column(String(300), nullable=False)
    data_evento: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    foto_capa_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[StatusEvento] = mapped_column(
        SAEnum(StatusEvento, name="statusevento", create_type=True),
        default=StatusEvento.ativo,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # ── Relacionamentos ──────────────────────────────────────
    instituto: Mapped["Instituto"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Instituto",
        back_populates="eventos",
        lazy="selectin",
    )
    participacoes: Mapped[list["Participacao"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Participacao",
        back_populates="evento",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Evento id={self.id} titulo={self.titulo} status={self.status}>"
