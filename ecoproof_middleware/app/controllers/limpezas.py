"""
Router placeholder — Limpezas Individuais
"""
from fastapi import APIRouter

router = APIRouter(prefix="/limpezas", tags=["Limpezas Individuais"])


@router.post("/", summary="Registrar limpeza individual")
async def create_limpeza():
    """TODO: registrar limpeza individual com fotos antes/depois."""
    return {"message": "create_limpeza placeholder"}


@router.get("/", summary="Listar minhas limpezas")
async def list_limpezas():
    """TODO: listar limpezas do cidadão autenticado."""
    return {"message": "list_limpezas placeholder"}


@router.get("/{limpeza_id}", summary="Detalhe da limpeza")
async def get_limpeza(limpeza_id: str):
    """TODO: detalhe de uma limpeza específica."""
    return {"message": "get_limpeza placeholder", "id": limpeza_id}


@router.patch("/{limpeza_id}/review", summary="Validar limpeza (Admin/IA)")
async def review_limpeza(limpeza_id: str):
    """TODO: validação manual ou via IA (Google Vision)."""
    return {"message": "review_limpeza placeholder", "id": limpeza_id}
