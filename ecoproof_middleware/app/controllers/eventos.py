"""
Router placeholder — Eventos
"""
from fastapi import APIRouter

router = APIRouter(prefix="/eventos", tags=["Eventos"])


@router.get("/", summary="Listar eventos")
async def list_eventos():
    """TODO: listar eventos com filtros (tipo, status, localização)."""
    return {"message": "list_eventos placeholder"}


@router.post("/", summary="Criar evento (Instituto)")
async def create_evento():
    """TODO: criar evento de mutirão."""
    return {"message": "create_evento placeholder"}


@router.get("/{evento_id}", summary="Detalhe do evento")
async def get_evento(evento_id: str):
    """TODO: retornar detalhe do evento."""
    return {"message": "get_evento placeholder", "id": evento_id}


@router.patch("/{evento_id}", summary="Atualizar evento")
async def update_evento(evento_id: str):
    """TODO: atualizar evento."""
    return {"message": "update_evento placeholder", "id": evento_id}


@router.delete("/{evento_id}", summary="Cancelar evento")
async def delete_evento(evento_id: str):
    """TODO: cancelar/deletar evento."""
    return {"message": "delete_evento placeholder", "id": evento_id}
