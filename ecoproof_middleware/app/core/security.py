"""
app/core/security.py
────────────────────
Funções de segurança: hashing de senha e geração/decodificação de JWT.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
import bcrypt
from fastapi import HTTPException, status

from app.core.config import settings

# ── Contexto bcrypt ──────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Gera o hash bcrypt de uma senha em texto plano."""
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode('ascii')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha em texto plano bate com o hash armazenado."""
    pwd_bytes = plain_password.encode('utf-8')
    hash_bytes = hashed_password.encode('ascii')
    try:
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except ValueError:
        return False


# ── JWT ──────────────────────────────────────────────────────────────────────
def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Gera um JWT assinado com SECRET_KEY.

    Args:
        data: Payload base (deve conter pelo menos ``sub`` e ``role``).
        expires_delta: Tempo de expiração customizado. Se None, usa
                       ``ACCESS_TOKEN_EXPIRE_MINUTES`` do settings (padrão 7 dias).

    Returns:
        Token JWT como string.
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = data.copy()
    expire = datetime.now(tz=timezone.utc) + expires_delta
    payload.update({"exp": expire, "iat": datetime.now(tz=timezone.utc)})

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """
    Decodifica e valida um JWT.

    Returns:
        Payload do token como dicionário.

    Raises:
        HTTPException 401: token inválido, expirado ou mal-formado.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        # Garante que ``sub`` existe no payload
        if payload.get("sub") is None:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception
