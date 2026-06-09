"""
Router placeholder — Participações
"""
from fastapi import APIRouter

router = APIRouter(prefix="/participacoes", tags=["Participações"])


@router.post("/", summary="Fazer check-in em evento")
async def checkin():
    """TODO: registrar participação (check-in) em evento."""
    return {"message": "checkin placeholder"}


@router.patch("/{participacao_id}/foto", summary="Enviar foto de participação")
async def upload_foto(participacao_id: str):
    """TODO: upload de foto de participação."""
    return {"message": "upload_foto placeholder", "id": participacao_id}


@router.patch("/{participacao_id}/review", summary="Aprovar/reprovar participação (Instituto)")
async def review_participacao(participacao_id: str):
    """TODO: review de participação pelo instituto."""
    return {"message": "review placeholder", "id": participacao_id}


@router.get("/", summary="Minhas participações")
async def list_participacoes():
    """TODO: listar participações do cidadão autenticado."""
    return {"message": "list_participacoes placeholder"}
