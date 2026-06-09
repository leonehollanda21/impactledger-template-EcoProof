"""
app/schemas/ponto_verde.py
──────────────────────────
Schemas para os endpoints de adoção de pontos verdes.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.checkin_ponto_verde import StatusCheckInPontoVerde
from app.models.ponto_verde import CategoriaPontoVerde, StatusPontoVerde


class PontoVerdeCreateRequest(BaseModel):
    nome: str
    categoria: CategoriaPontoVerde
    latitude: float
    longitude: float


class CheckInValidationRequest(BaseModel):
    aprovado: bool
    motivo: Optional[str] = None


class CheckInPontoVerdeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ponto_verde_id: uuid.UUID
    mes_referencia: int
    data_envio: datetime
    foto_url: str
    status: StatusCheckInPontoVerde
    motivo: Optional[str] = None


class PontoVerdeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    categoria: CategoriaPontoVerde
    latitude: float
    longitude: float
    guardiao_id: Optional[uuid.UUID] = None
    guardiao_name: Optional[str] = None
    data_inicio: Optional[datetime] = None
    status: StatusPontoVerde
    meses_concluidos: int
    proximo_checkin_limite: Optional[datetime] = None
    foto_inicial_url: Optional[str] = None
    nft_token_id: Optional[int] = None
    nft_tx_hash: Optional[str] = None
