"""
app/schemas/auth.py
───────────────────
Schemas Pydantic v2 para autenticação e registro de usuários.
"""
import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict

from app.models.user import UserRole


# ── Registro ─────────────────────────────────────────────────────────────────

class RegisterCidadaoRequest(BaseModel):
    """Payload para registro de um cidadão."""
    name: str = Field(..., min_length=2, max_length=100, examples=["João Silva"])
    email: EmailStr = Field(..., examples=["joao@example.com"])
    password: str = Field(..., min_length=8, max_length=128, examples=["Senha@123"])

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("A senha deve conter pelo menos uma letra.")
        if not re.search(r"\d", v):
            raise ValueError("A senha deve conter pelo menos um número.")
        return v


class RegisterInstitutoRequest(BaseModel):
    """Payload para registro de um instituto/ONG."""
    name: str = Field(..., min_length=2, max_length=100, examples=["ONG Verde Vivo"])
    email: EmailStr = Field(..., examples=["contato@verdevivo.org"])
    password: str = Field(..., min_length=8, max_length=128, examples=["Senha@123"])
    cnpj: str = Field(
        ...,
        min_length=14,
        max_length=20,
        examples=["12.345.678/0001-90"],
        description="CNPJ com ou sem formatação.",
    )

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("A senha deve conter pelo menos uma letra.")
        if not re.search(r"\d", v):
            raise ValueError("A senha deve conter pelo menos um número.")
        return v

    @field_validator("cnpj")
    @classmethod
    def clean_cnpj(cls, v: str) -> str:
        """Remove pontuação e valida comprimento numérico."""
        digits = re.sub(r"\D", "", v)
        if len(digits) != 14:
            raise ValueError("CNPJ deve ter exatamente 14 dígitos numéricos.")
        return v  # mantém o formato original enviado


# ── Login ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """Payload para login."""
    email: EmailStr = Field(..., examples=["joao@example.com"])
    password: str = Field(..., min_length=1, examples=["Senha@123"])


# ── Respostas de token ────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    """Resposta de autenticação bem-sucedida."""
    access_token: str
    token_type: str = "bearer"
    role: UserRole

    model_config = ConfigDict(from_attributes=True)


class TokenPayload(BaseModel):
    """Estrutura do payload interno do JWT."""
    sub: str          # user id como string (UUID)
    role: str
    exp: int
    iat: int


# ── Mensagens de resposta genéricas ──────────────────────────────────────────

class MessageResponse(BaseModel):
    """Resposta com mensagem simples."""
    message: str
    detail: Optional[str] = None
