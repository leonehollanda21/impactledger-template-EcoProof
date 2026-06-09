"""
app/schemas/user.py
───────────────────
Schemas Pydantic v2 para perfil de usuário.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.models.user import UserRole


class UserBase(BaseModel):
    name: str = Field(..., max_length=100)
    email: EmailStr
    role: UserRole
    wallet_address: Optional[str] = Field(None, max_length=255)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    wallet_address: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    created_at: datetime


class UserOutPublic(BaseModel):
    """Versão pública sem e-mail (para listagens)."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    role: UserRole
    wallet_address: Optional[str] = None


# ── Perfil estendido (GET /users/me) ─────────────────────────────────────────

class CidadaoMeOut(BaseModel):
    """Perfil completo para cidadão autenticado."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    role: UserRole
    wallet_address: Optional[str] = None
    is_active: bool
    created_at: datetime
    # campos extras do perfil Cidadao
    total_points: int = 0


class InstitutoMeOut(BaseModel):
    """Perfil completo para instituto autenticado."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    role: UserRole
    wallet_address: Optional[str] = None
    is_active: bool
    created_at: datetime
    # campos extras do perfil Instituto
    cnpj: str
    verified: bool
    verified_at: Optional[datetime] = None


class AdminMeOut(BaseModel):
    """Perfil completo para admin autenticado."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
