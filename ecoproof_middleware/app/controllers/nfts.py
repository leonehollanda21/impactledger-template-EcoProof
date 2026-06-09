"""
Router placeholder — NFTs
"""
from fastapi import APIRouter

router = APIRouter(prefix="/nfts", tags=["NFTs"])


@router.get("/", summary="Listar meus NFTs")
async def list_nfts():
    """TODO: listar NFTs do cidadão autenticado."""
    return {"message": "list_nfts placeholder"}


@router.post("/mint", summary="Mintar NFT (interno)")
async def mint_nft():
    """TODO: mintar NFT na blockchain (Polygon)."""
    return {"message": "mint_nft placeholder"}


@router.get("/{nft_id}", summary="Detalhe do NFT")
async def get_nft(nft_id: str):
    """TODO: retornar detalhe de um NFT."""
    return {"message": "get_nft placeholder", "id": nft_id}
