"""
app/controllers/auth_router.py
───────────────────────────────
Rotas de autenticação:
  POST /auth/register/cidadao   → registrar cidadão
  POST /auth/register/instituto → registrar instituto
  POST /auth/login              → login JWT
  POST /auth/refresh            → renovar token
"""
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, oauth2_scheme
from app.schemas.auth import (
    RegisterCidadaoRequest,
    RegisterInstitutoRequest,
    LoginRequest,
    TokenResponse,
    MessageResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])

DBDep = Depends(get_db)


@router.post(
    "/register/cidadao",
    response_model=TokenResponse,
    status_code=201,
    summary="Registrar cidadão",
    description=(
        "Cria uma conta de cidadão. Gera automaticamente uma wallet Ethereum simulada "
        "e retorna um JWT pronto para uso."
    ),
)
async def register_cidadao(
    data: RegisterCidadaoRequest,
    db: AsyncSession = DBDep,
) -> TokenResponse:
    return await auth_service.register_cidadao(db, data)


@router.post(
    "/register/instituto",
    response_model=MessageResponse,
    status_code=201,
    summary="Registrar instituto / ONG",
    description=(
        "Cria uma conta de instituto com status *não verificado*. "
        "O login só é liberado após aprovação de um administrador EcoProof."
    ),
)
async def register_instituto(
    data: RegisterInstitutoRequest,
    db: AsyncSession = DBDep,
) -> MessageResponse:
    return await auth_service.register_instituto(db, data)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login (e-mail + senha)",
    description="Autentica com e-mail e senha. Retorna JWT Bearer com role no payload.",
)
async def login(
    data: LoginRequest,
    db: AsyncSession = DBDep,
) -> TokenResponse:
    return await auth_service.login(db, data)


@router.post(
    "/login/form",
    response_model=TokenResponse,
    summary="Login via OAuth2 form (compatível com /docs)",
    include_in_schema=True,
    description="Endpoint compatível com o formulário OAuth2 do Swagger UI (`/docs`).",
)
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = DBDep,
) -> TokenResponse:
    """Adapta o form OAuth2 (username = email) para o login padrão."""
    data = LoginRequest(email=form_data.username, password=form_data.password)
    return await auth_service.login(db, data)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renovar token JWT",
    description=(
        "Recebe um token Bearer válido no header ``Authorization`` e retorna "
        "um novo token com prazo renovado."
    ),
)
async def refresh(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = DBDep,
) -> TokenResponse:
    return await auth_service.refresh_token(db, token)
