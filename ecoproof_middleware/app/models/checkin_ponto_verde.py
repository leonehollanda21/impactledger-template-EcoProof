import enum
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Integer, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class StatusCheckInPontoVerde(str, enum.Enum):
    pendente = "pendente"
    aprovado = "aprovado"
    rejeitado = "rejeitado"


class CheckInPontoVerde(Base):
    __tablename__ = "checkins_pontos_verdes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    ponto_verde_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pontos_verdes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mes_referencia: Mapped[int] = mapped_column(Integer, nullable=False)
    data_envio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    foto_url: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[StatusCheckInPontoVerde] = mapped_column(
        SAEnum(StatusCheckInPontoVerde, name="statuscheckinpontoverde", create_type=True),
        default=StatusCheckInPontoVerde.pendente,
        nullable=False,
    )
    motivo: Mapped[str | None] = mapped_column(String(500), nullable=True)

    ponto_verde: Mapped["PontoVerde"] = relationship(
        "PontoVerde",
        back_populates="checkins",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<CheckInPontoVerde id={self.id} mes={self.mes_referencia} status={self.status}>"
