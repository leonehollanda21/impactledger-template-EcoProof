"""
Schemas Pydantic v2 — Instituto
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class InstitutoCreate(BaseModel):
    cnpj: str = Field(..., max_length=20)


class InstitutoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cnpj: str
    verified: bool
    verified_at: Optional[datetime] = None


class InstitutoVerify(BaseModel):
    verified: bool
