"""
Router placeholder — Institutos
"""
from fastapi import APIRouter

router = APIRouter(prefix="/institutos", tags=["Institutos"])


@router.get("/", summary="Listar institutos verificados")
async def list_institutos():
    """TODO: listar institutos."""
    return {"message": "list_institutos placeholder"}


@router.get("/{instituto_id}", summary="Detalhe do instituto")
async def get_instituto(instituto_id: str):
    """TODO: retornar perfil do instituto."""
    return {"message": "get_instituto placeholder", "id": instituto_id}


@router.patch("/{instituto_id}/verify", summary="Verificar instituto (Admin)")
async def verify_instituto(instituto_id: str):
    """TODO: verificar instituto (aprovação admin)."""
    return {"message": "verify_instituto placeholder", "id": instituto_id}
