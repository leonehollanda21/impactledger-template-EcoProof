"""
Router placeholder — Auth
"""
from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", summary="Registrar novo usuário")
async def register():
    """TODO: implementar registro de usuário."""
    return {"message": "register placeholder"}


@router.post("/login", summary="Login e geração de JWT")
async def login():
    """TODO: implementar login e retorno de JWT."""
    return {"message": "login placeholder"}


@router.post("/refresh", summary="Renovar token JWT")
async def refresh_token():
    """TODO: implementar refresh token."""
    return {"message": "refresh placeholder"}
