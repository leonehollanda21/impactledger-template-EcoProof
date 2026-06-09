"""
Schemas Pydantic v2 — Cidadão
"""
import uuid
from pydantic import BaseModel, ConfigDict


class CidadaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    total_points: int


class CidadaoRanking(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    total_points: int
    wallet_address: str | None = None
