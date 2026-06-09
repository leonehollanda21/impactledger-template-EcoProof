"""
Router placeholder — Users
"""
from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", summary="Listar usuários")
async def list_users():
    """TODO: listar usuários (admin)."""
    return {"message": "list_users placeholder"}


@router.get("/me", summary="Perfil do usuário autenticado")
async def get_me():
    """TODO: retornar perfil do usuário logado."""
    return {"message": "get_me placeholder"}


@router.patch("/me", summary="Atualizar perfil")
async def update_me():
    """TODO: atualizar dados do usuário logado."""
    return {"message": "update_me placeholder"}
