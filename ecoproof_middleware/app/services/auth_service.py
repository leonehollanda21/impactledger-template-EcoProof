"""
app/services/auth_service.py
─────────────────────────────
Lógica de negócio de autenticação:
  - register_cidadao
  - register_instituto
  - login
  - refresh_token
"""
import secrets
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password, create_access_token, decode_token
from app.models.user import User, UserRole
from app.models.cidadao import Cidadao
from app.models.instituto import Instituto
from app.schemas.auth import (
    RegisterCidadaoRequest,
    RegisterInstitutoRequest,
    LoginRequest,
    TokenResponse,
    MessageResponse,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _generate_wallet_address() -> str:
    """
    Gera um endereço Ethereum simulado de 42 caracteres (prefixo '0x' + 40 hex).
    Em produção, isso seria substituído pela wallet real do usuário.
    """
    hex_part = secrets.token_hex(20)  # 20 bytes = 40 caracteres hex
    return f"0x{hex_part}"


async def _get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


def _build_token(user: User) -> TokenResponse:
    """Monta o TokenResponse com o JWT assinado."""
    payload = {"sub": str(user.id), "role": user.role.value}
    token = create_access_token(data=payload)
    return TokenResponse(access_token=token, token_type="bearer", role=user.role)


# ── Registro de Cidadão ───────────────────────────────────────────────────────

async def register_cidadao(
    db: AsyncSession,
    data: RegisterCidadaoRequest,
) -> TokenResponse:
    """
    Cria User (role=cidadao) + Cidadao, gera wallet simulada e retorna JWT.

    Raises:
        409: e-mail já cadastrado
    """
    # Verifica duplicidade de e-mail
    existing = await _get_user_by_email(db, data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail já cadastrado. Tente fazer login ou use outro e-mail.",
        )

    # Cria User
    new_user = User(
        id=uuid.uuid4(),
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=UserRole.cidadao,
        wallet_address=_generate_wallet_address(),
        is_active=True,
    )
    db.add(new_user)
    await db.flush()  # obtém o ID antes do commit

    # Cria perfil Cidadao
    cidadao = Cidadao(id=new_user.id, total_points=0)
    db.add(cidadao)

    # commit é feito pelo get_db dependency
    return _build_token(new_user)


# ── Registro de Instituto ─────────────────────────────────────────────────────

async def register_instituto(
    db: AsyncSession,
    data: RegisterInstitutoRequest,
) -> MessageResponse:
    """
    Cria User (role=instituto) + Instituto (verified=False).
    Retorna mensagem de aguardo de verificação — sem JWT, pois precisa de aprovação.

    Raises:
        409: e-mail já cadastrado
        409: CNPJ já cadastrado
    """
    # Verifica duplicidade de e-mail
    existing_email = await _get_user_by_email(db, data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail já cadastrado.",
        )

    # Verifica duplicidade de CNPJ
    result = await db.execute(select(Instituto).where(Instituto.cnpj == data.cnpj))
    existing_cnpj = result.scalar_one_or_none()
    if existing_cnpj:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="CNPJ já cadastrado. Entre em contato com o suporte.",
        )

    # Cria User
    new_user = User(
        id=uuid.uuid4(),
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=UserRole.instituto,
        is_active=True,
    )
    db.add(new_user)
    await db.flush()

    # Cria perfil Instituto (não verificado)
    instituto = Instituto(
        id=new_user.id,
        cnpj=data.cnpj,
        verified=False,
        verified_at=None,
    )
    db.add(instituto)

    return MessageResponse(
        message="Instituto cadastrado com sucesso!",
        detail=(
            "Seu cadastro foi recebido e está aguardando verificação pela equipe EcoProof. "
            "Você receberá uma notificação por e-mail após a aprovação."
        ),
    )


# ── Login ─────────────────────────────────────────────────────────────────────

async def login(
    db: AsyncSession,
    data: LoginRequest,
) -> TokenResponse:
    """
    Valida credenciais e retorna JWT com role no payload.

    Raises:
        401: credenciais inválidas
        403: conta desativada
        403: instituto não verificado
    """
    # Busca usuário
    user = await _get_user_by_email(db, data.email)

    # Mensagem genérica para não revelar se o e-mail existe
    invalid_credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="E-mail ou senha incorretos.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if user is None:
        raise invalid_credentials_exc

    if not verify_password(data.password, user.password_hash):
        raise invalid_credentials_exc

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta desativada. Entre em contato com o suporte.",
        )

    # Institutos precisam estar verificados para logar
    if user.role == UserRole.instituto:
        result = await db.execute(select(Instituto).where(Instituto.id == user.id))
        instituto = result.scalar_one_or_none()
        if instituto and not instituto.verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Instituto ainda não verificado. "
                    "Aguarde a aprovação do administrador EcoProof."
                ),
            )

    return _build_token(user)


# ── Refresh Token ─────────────────────────────────────────────────────────────

async def refresh_token(
    db: AsyncSession,
    token: str,
) -> TokenResponse:
    """
    Recebe um token JWT válido e retorna um novo token com prazo renovado.

    Raises:
        401: token inválido / expirado
        401: usuário não encontrado
    """
    payload = decode_token(token)
    user_id_str: str = payload.get("sub", "")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id_str)))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou inativo.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _build_token(user)
