"""
app/core/dependencies.py
────────────────────────
FastAPI dependencies reutilizáveis:
  - get_db         → sessão async do banco
  - get_current_user → extrai e valida o JWT, retorna o User
  - require_cidadao  → garante role == cidadao
  - require_instituto → garante role == instituto E verified == True
  - require_admin    → garante role == admin
"""
import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.core.security import decode_token
from app.models.user import User, UserRole
from app.models.cidadao import Cidadao
from app.models.instituto import Instituto

# ── Sessão do banco ──────────────────────────────────────────────────────────

async def get_db() -> AsyncSession:  # type: ignore[return]
    """Dependency que abre uma sessão AsyncSession e garante commit/rollback."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


DBSession = Annotated[AsyncSession, Depends(get_db)]

# ── OAuth2 bearer ────────────────────────────────────────────────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login/form")

TokenDep = Annotated[str, Depends(oauth2_scheme)]


# ── Usuário autenticado ───────────────────────────────────────────────────────
async def get_current_user(
    token: TokenDep,
    db: DBSession,
) -> User:
    """
    Decodifica o Bearer JWT e retorna o User correspondente.

    Raises:
        401: token inválido / expirado
        401: usuário não encontrado
        403: conta desativada
    """
    payload = decode_token(token)
    user_id_str: str | None = payload.get("sub")

    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sem identificador de usuário.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identificador de usuário inválido no token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta desativada. Entre em contato com o suporte.",
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


# ── Guards de role ────────────────────────────────────────────────────────────
async def require_cidadao(current_user: CurrentUser) -> Cidadao:
    """
    Valida que o usuário logado tem role ``cidadao`` e retorna o perfil Cidadao.

    Raises:
        403: usuário não é cidadão
        404: perfil Cidadao não encontrado (inconsistência de dados)
    """
    if current_user.role != UserRole.cidadao:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a cidadãos.",
        )
    # Cidadao.id == User.id (joined table)
    return current_user  # type: ignore[return-value]


async def _get_cidadao_profile(
    current_user: CurrentUser,
    db: DBSession,
) -> Cidadao:
    """Retorna o perfil Cidadao do usuário logado."""
    if current_user.role != UserRole.cidadao:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a cidadãos.",
        )
    result = await db.execute(select(Cidadao).where(Cidadao.id == current_user.id))
    cidadao = result.scalar_one_or_none()
    if cidadao is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil de cidadão não encontrado.",
        )
    return cidadao


CidadaoProfile = Annotated[Cidadao, Depends(_get_cidadao_profile)]


async def require_instituto(
    current_user: CurrentUser,
    db: DBSession,
) -> Instituto:
    """
    Valida role ``instituto`` E ``verified == True``.

    Raises:
        403: não é instituto
        403: instituto ainda não verificado
    """
    if current_user.role != UserRole.instituto:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a institutos.",
        )
    result = await db.execute(select(Instituto).where(Instituto.id == current_user.id))
    instituto = result.scalar_one_or_none()

    if instituto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil de instituto não encontrado.",
        )
    if not instituto.verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Instituto ainda não verificado. Aguarde a aprovação do administrador.",
        )
    return instituto


InstitutoProfile = Annotated[Instituto, Depends(require_instituto)]


async def require_admin(current_user: CurrentUser) -> User:
    """
    Valida que o usuário tem role ``admin``.

    Raises:
        403: não é admin
    """
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores.",
        )
    return current_user


AdminUser = Annotated[User, Depends(require_admin)]
